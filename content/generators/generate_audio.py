"""
Turns lesson cards into mp3 files for „Felolvasás” (read aloud / audiobook mode).

Why files: a phone that locks its screen stops the browser's own voice (speechSynthesis) but keeps
playing an ordinary audio file, so the app plays these with <audio> + the Media Session API and the
lesson keeps going on the lock screen. Without a file a card is still read aloud by the browser's voice,
just not in the background (see frontend/src/lib/narration.js).

What gets spoken is decided in ONE place, backend/core/speech.py (the API imports it too). Files are
content-addressed by the hash of that text: edit a card → new hash → stale audio is never matched.
Apply database/migrations/v11_narration_audio.sql first (table + public bucket `content-audio`).

Nothing is spent unless --apply is given, and a run stops at --max-chars (default 250 000) so a typo
can't turn into a whole-library bill. Voice quality for Hungarian differs a lot between providers: run
`sample` first and listen.

  python generate_audio.py status [--nat-id PHYS-78-03 | --all]          # what exists, what is missing, rough size
  python generate_audio.py sample --nat-id PHYS-78-03 [--n 3]              # a few cards → ./audio_sample/*.mp3, no upload
  python generate_audio.py run    --nat-id PHYS-78-03 [--apply]            # synthesise + upload what is missing
  python generate_audio.py run    --all --apply --max-chars 3000000        # the whole library (explicit budget)
  python generate_audio.py prune  [--apply]                                # drop audio nobody references any more

Provider (first one with a key wins, or --provider):
  azure   AZURE_SPEECH_KEY + AZURE_SPEECH_REGION   voice hu-HU-NoemiNeural (native Hungarian neural voice)
  openai  OPENAI_API_KEY                           model gpt-4o-mini-tts, voice alloy (multilingual; accent not native)
Keys are read from backend/.env or the environment — never written anywhere.
"""
import os
import re
import sys
import time
import argparse
from xml.sax.saxutils import escape

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../../backend"))
from core import speech as S  # noqa: E402  (stdlib-only; the same text rules the API uses)

load_dotenv(os.path.join(HERE, "../../backend/.env"))

BUCKET = "content-audio"
DEFAULT_MAX_CHARS = 250_000
CHUNK_CHARS = 3000                 # per TTS request (providers cap input at ~4000 chars / a few minutes)
PRICE_PER_M_CHARS = 16.0           # USD — an assumption (typical neural-TTS list price); check your provider
CHARS_PER_MINUTE = 850             # rough Hungarian speaking rate, only for the size estimate
AZURE_FORMAT = "audio-16khz-32kbitrate-mono-mp3"   # 4 kB/s: plenty for speech, ~0.25 MB per minute
BYTES_PER_MINUTE = 240_000


# ─── text → request chunks ────────────────────────────────────────────────────

def split_chunks(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Pack paragraphs (then sentences, for an over-long paragraph) into pieces of <= limit chars."""
    pieces: list[str] = []
    for para in text.split("\n\n"):
        if len(para) <= limit:
            pieces.append(para)
            continue
        cur = ""
        for sent in re.split(r"(?<=[.!?])\s+", para):
            if cur and len(cur) + 1 + len(sent) > limit:
                pieces.append(cur)
                cur = ""
            cur = f"{cur} {sent}".strip()
            while len(cur) > limit:                      # one monster sentence: hard cut at a space
                cut = cur.rfind(" ", 0, limit)
                if cut <= 0:
                    cut = limit
                pieces.append(cur[:cut])
                cur = cur[cut:].strip()
        if cur:
            pieces.append(cur)
    out, cur = [], ""
    for p in pieces:
        if cur and len(cur) + 2 + len(p) > limit:
            out.append(cur)
            cur = ""
        cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        out.append(cur)
    return out


# ─── providers (request builders are pure → unit-tested; synth() does the HTTP) ─────────────

class Azure:
    name = "azure"

    def __init__(self, key, region, voice="hu-HU-NoemiNeural"):
        self.key, self.region, self.voice = key, region, voice

    def request(self, chunk: str) -> dict:
        lines = [escape(l.strip()) for l in chunk.split("\n") if l.strip()]   # heading / paragraph / timeline row
        body = "<break time=\"450ms\"/>".join(lines)
        ssml = (f"<speak version='1.0' xml:lang='hu-HU'><voice name='{self.voice}'>{body}</voice></speak>")
        return {"url": f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1",
                "headers": {"Ocp-Apim-Subscription-Key": self.key, "Content-Type": "application/ssml+xml",
                            "X-Microsoft-OutputFormat": AZURE_FORMAT, "User-Agent": "turul-academy-audio"},
                "content": ssml.encode("utf-8")}


class OpenAI:
    name = "openai"

    def __init__(self, key, voice="alloy", model="gpt-4o-mini-tts"):
        self.key, self.voice, self.model = key, voice, model

    def request(self, chunk: str) -> dict:
        body = {"model": self.model, "voice": self.voice, "input": chunk, "response_format": "mp3"}
        if self.model.startswith("gpt-4o"):
            body["instructions"] = ("Read this Hungarian school lesson aloud in clear, natural Hungarian, "
                                    "at a calm, even pace, like a good teacher. Say every number and date in Hungarian.")
        return {"url": "https://api.openai.com/v1/audio/speech",
                "headers": {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                "json": body}


def pick_provider(name=None, env=os.environ):
    name = name or ("azure" if env.get("AZURE_SPEECH_KEY") else "openai" if env.get("OPENAI_API_KEY") else None)
    if name == "azure" and env.get("AZURE_SPEECH_KEY") and env.get("AZURE_SPEECH_REGION"):
        return Azure(env["AZURE_SPEECH_KEY"], env["AZURE_SPEECH_REGION"], env.get("AZURE_SPEECH_VOICE", "hu-HU-NoemiNeural"))
    if name == "openai" and env.get("OPENAI_API_KEY"):
        return OpenAI(env["OPENAI_API_KEY"], env.get("OPENAI_TTS_VOICE", "alloy"), env.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"))
    raise SystemExit("No TTS provider configured: set AZURE_SPEECH_KEY + AZURE_SPEECH_REGION, or OPENAI_API_KEY "
                     "(backend/.env), or pick one with --provider.")


def synth(client: httpx.Client, provider, text: str, sleep=time.sleep) -> bytes:
    """mp3 bytes for `text` (chunked, retried on 429/5xx; plain concatenation of mp3 frames plays fine)."""
    audio = b""
    for chunk in split_chunks(text):
        req = provider.request(chunk)
        for attempt in range(5):
            r = client.post(req["url"], headers=req["headers"], content=req.get("content"), json=req.get("json"), timeout=60.0)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 4:
                sleep(min(60, float(r.headers.get("Retry-After") or 2 ** (attempt + 1))))
                continue
            r.raise_for_status()
            audio += r.content
            break
    return audio


# ─── Supabase ─────────────────────────────────────────────────────────────────

class Supa:
    def __init__(self, client: httpx.Client, url: str, key: str):
        self.c, self.url = client, url.rstrip("/")
        self.h = {"apikey": key, "Authorization": f"Bearer {key}"}

    def get(self, table, params):
        r = self.c.get(f"{self.url}/rest/v1/{table}", headers=self.h, params=params, timeout=7.0)
        if r.status_code == 404 and table == "narration_audio":
            raise SystemExit("Table narration_audio not found — apply database/migrations/v11_narration_audio.sql first.")
        r.raise_for_status()
        return r.json()

    def get_all(self, table, params, page=1000):
        out, offset = [], 0
        while True:
            rows = self.get(table, {**params, "limit": str(page), "offset": str(offset)})
            out += rows
            if len(rows) < page:
                return out
            offset += page

    def upload(self, path, data):
        r = self.c.post(f"{self.url}/storage/v1/object/{BUCKET}/{path}", content=data, timeout=30.0,
                        headers={**self.h, "Content-Type": "audio/mpeg", "x-upsert": "true",
                                 "cache-control": "max-age=31536000"})   # content-addressed → immutable
        r.raise_for_status()

    def upsert_row(self, row):
        r = self.c.post(f"{self.url}/rest/v1/narration_audio", json=row, timeout=7.0,
                        headers={**self.h, "Content-Type": "application/json",
                                 "Prefer": "resolution=merge-duplicates,return=minimal"})
        r.raise_for_status()

    def delete_files(self, paths):
        r = self.c.request("DELETE", f"{self.url}/storage/v1/object/{BUCKET}", json={"prefixes": paths},
                           headers={**self.h, "Content-Type": "application/json"}, timeout=30.0)
        r.raise_for_status()

    def delete_row(self, text_hash):
        r = self.c.request("DELETE", f"{self.url}/rest/v1/narration_audio", params={"text_hash": f"eq.{text_hash}"},
                           headers=self.h, timeout=7.0)
        r.raise_for_status()


def in_list(values):
    return "in.(" + ",".join(values) + ")"


def collect(db: Supa, nat_ids=None, modes=S.AUDIO_MODES) -> dict:
    """{text_hash: {"text", "mode", "title"}} for every active card of the chosen Témakörök, in reading order.
    Topic by topic, so no request comes near PostgREST's 1000-row page."""
    params = {"select": "id,nat_id", "order": "nat_id"}
    if nat_ids:
        params["nat_id"] = in_list(nat_ids)
    found: dict = {}
    for topic in db.get_all("curriculum_topics", params):
        lessons = db.get("curriculum_lessons", {"topic_id": f"eq.{topic['id']}", "select": "id", "order": "order_index"})
        if not lessons:
            continue
        ids = [l["id"] for l in lessons]
        blocks = db.get_all("content_blocks", {"lesson_id": in_list(ids), "scope": "eq.lesson", "is_active": "eq.true",
                                               "mode": in_list(list(modes)), "select": "lesson_id,mode,content"})
        blocks = [b for b in blocks if b["mode"] in modes]
        order = {lid: i for i, lid in enumerate(ids)}
        blocks.sort(key=lambda b: (order.get(b["lesson_id"], 0), modes.index(b["mode"])))
        for b in blocks:
            for card in b["content"] or []:
                e = S.narration_entry(b["mode"], card)
                if e and e["hash"] not in found:
                    found[e["hash"]] = {"text": e["text"], "mode": b["mode"], "title": e["title"], "nat_id": topic["nat_id"]}
    return found


def existing(db: Supa, hashes) -> set:
    have, hashes = set(), list(hashes)
    for i in range(0, len(hashes), 80):
        have |= {r["text_hash"] for r in db.get("narration_audio", {"text_hash": in_list(hashes[i:i + 80]), "select": "text_hash"})}
    return have


def audio_path(text_hash: str) -> str:
    return f"{text_hash[:2]}/{text_hash}.mp3"


def size_line(chars: int) -> str:
    minutes = chars / CHARS_PER_MINUTE
    return (f"{chars:,} characters ≈ {minutes / 60:.1f} h of audio ≈ {minutes * BYTES_PER_MINUTE / 1e6:,.0f} MB "
            f"(~${chars / 1e6 * PRICE_PER_M_CHARS:.2f} at an assumed ${PRICE_PER_M_CHARS:.0f} per million characters)")


# ─── commands ─────────────────────────────────────────────────────────────────

def cmd_status(db, a):
    found = collect(db, targets(a), tuple(a.modes))
    have = existing(db, found)
    todo = [h for h in found if h not in have]
    print(f"{len(found)} distinct narrated texts, {len(have)} with audio, {len(todo)} missing")
    print("missing: " + size_line(sum(len(found[h]["text"]) for h in todo)))


def cmd_sample(db, client, a):
    found = collect(db, targets(a), tuple(a.modes))
    provider = pick_provider(a.provider)
    out = os.path.join(os.getcwd(), "audio_sample")
    os.makedirs(out, exist_ok=True)
    for h, it in list(found.items())[:a.n]:
        data = synth(client, provider, it["text"])
        with open(os.path.join(out, f"{h[:8]}.mp3"), "wb") as f:
            f.write(data)
        with open(os.path.join(out, f"{h[:8]}.txt"), "w", encoding="utf-8") as f:
            f.write(it["text"])
        print(f"{h[:8]}.mp3  {len(it['text'])} chars  {len(data) / 1000:.0f} kB  [{it['mode']}] {it['title']}")
    print(f"→ {out} (nothing uploaded, nothing written to the database)")


def cmd_run(db, client, a):
    found = collect(db, targets(a), tuple(a.modes))
    have = existing(db, found)
    todo = [h for h in found if h not in have]
    budget, batch, spent = a.max_chars, [], 0
    for h in todo:
        n = len(found[h]["text"])
        if spent + n > budget:
            break
        batch.append(h)
        spent += n
    print(f"{len(found)} texts, {len(have)} already have audio, {len(todo)} missing; this run: {len(batch)} ({size_line(spent)})")
    if len(batch) < len(todo):
        print(f"  {len(todo) - len(batch)} more are left because of --max-chars {budget:,} (raise it to do them)")
    if not a.apply:
        print("dry run — add --apply to synthesise and upload")
        return
    provider = pick_provider(a.provider)
    done = failed = streak = 0
    for i, h in enumerate(batch, 1):
        it = found[h]
        try:
            data = synth(client, provider, it["text"])
            if not data:
                raise RuntimeError("empty audio")
            path = audio_path(h)
            db.upload(path, data)
            db.upsert_row({"text_hash": h, "path": path, "provider": provider.name, "voice": provider.voice,
                           "chars": len(it["text"]), "bytes": len(data)})
            done += 1
            streak = 0
            print(f"  [{i}/{len(batch)}] ✓ {it['nat_id']} [{it['mode']}] {it['title'][:50]}")
        except (httpx.HTTPError, RuntimeError) as e:
            failed += 1
            streak += 1
            print(f"  [{i}/{len(batch)}] ✗ {it['title'][:50]}: {e}")
            if streak >= 5:
                print("5 failures in a row — stopping (bad key, quota or network?).")
                break
    print(f"{done} saved, {failed} failed")


def cmd_prune(db, a):
    in_use = set(collect(db, None, S.AUDIO_MODES))
    rows = db.get_all("narration_audio", {"select": "text_hash,path"})
    stale = [r for r in rows if r["text_hash"] not in in_use]
    print(f"{len(rows)} audio files, {len(rows) - len(stale)} still referenced, {len(stale)} stale")
    if not a.apply or not stale:
        if stale:
            print("dry run — add --apply to delete them")
        return
    for i in range(0, len(stale), 100):
        db.delete_files([r["path"] for r in stale[i:i + 100]])
    for r in stale:
        db.delete_row(r["text_hash"])
    print(f"deleted {len(stale)}")


def targets(a):
    if a.all:
        return None
    if a.nat_id:
        return [a.nat_id]
    raise SystemExit("Pick one Témakör with --nat-id, or everything with --all.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["status", "sample", "run", "prune"])
    ap.add_argument("--nat-id")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--modes", default=",".join(S.AUDIO_MODES), type=lambda s: [m for m in s.split(",") if m])
    ap.add_argument("--provider", choices=["azure", "openai"])
    ap.add_argument("--n", type=int, default=3, help="sample: how many cards")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS, help="run: stop after this many characters")
    ap.add_argument("--apply", action="store_true", help="run/prune: actually spend money and write (default is a dry run)")
    a = ap.parse_args(argv)
    bad = [m for m in a.modes if m not in S.AUDIO_MODES]
    if bad:
        raise SystemExit(f"Unknown or non-audio mode(s): {bad} (allowed: {', '.join(S.AUDIO_MODES)})")
    sb, svc = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not sb or not svc:
        raise SystemExit("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing (backend/.env).")
    with httpx.Client() as client:
        db = Supa(client, sb, svc)
        {"status": lambda: cmd_status(db, a), "sample": lambda: cmd_sample(db, client, a),
         "run": lambda: cmd_run(db, client, a), "prune": lambda: cmd_prune(db, a)}[a.cmd]()


if __name__ == "__main__":
    main()
