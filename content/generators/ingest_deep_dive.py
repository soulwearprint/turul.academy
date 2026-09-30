"""
Commits pre-written „Mesélj még!" deep-dive cards to Supabase — the no-OpenRouter path.

The cards are written by a Claude session straight from the snapshot
(content/snapshot/<nat_id>.json) into content/deep/<nat_id>.json; this script only checks
and saves them. Same block shape as generate_deep_dive.py: one content_blocks row per
lesson, mode='deep', level='emelt', scope='lesson', one card per text card (`anchor`).

Input (content/deep/<nat_id>.json):
{
  "nat_id": "PHYS-78-01",
  "snapshot_exported_at": "<copied from the snapshot>",
  "lessons": [
    {"lesson_id": "…", "title_hu": "…", "text_block_id": "…", "n_text": 7,
     "cards": [{"type": "deep", "anchor": 0, "heading": "", "body": "", "did_you_know": "",
                "think": "", "think_answer": ""}, …]}
  ]
}

Safety: the anchors point at text cards by index, so a lesson is skipped when its live
active text block is not the one the cards were written for (different block id or card
count). A lesson that already has a deep block is skipped unless --replace.

Usage:
    python ingest_deep_dive.py --check [NAT_ID …]          # offline structure/language check
    python ingest_deep_dive.py --nat-id PHYS-78-01 --dry-run
    python ingest_deep_dive.py --nat-id PHYS-78-01 [--replace] [--inactive]
    python ingest_deep_dive.py --all [--dry-run]            # every file in content/deep/
"""
import os, re, sys, json, glob, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
DEEP = os.path.join(HERE, "../deep")
SNAP = os.path.join(HERE, "../snapshot")
KEYS = ("heading", "body", "think", "think_answer")          # did_you_know may be empty
_AZ_CONS = re.compile(r"(?<![^\W\d_])[Aa]z (?=[bcdfghjklmnprstvzBCDFGHJKLMNPRSTVZ])")
_A_CONS = re.compile(r"(?<![^\W\d_])[Aa] (?=[bcdfghjklmnprstvzBCDFGHJKLMNPRSTVZ])")
_A_VOWEL = re.compile(r"(?<![^\W\d_])(?<![-–])[Aa] (?=[aáeéiíoóöőuúüűAÁEÉIÍOÓÖŐUÚÜŰ])")
_DOT_DECIMAL = re.compile(r"\d\.\d+ ?(?:m|km|kg|s|N|J|W|V|A|Ω|°C|%|m/s)")


def load(nat_id):
    return json.load(open(os.path.join(DEEP, f"{nat_id}.json"), encoding="utf-8"))


def snapshot_text(nat_id):
    """lesson_id -> (text block id, number of text cards) from the snapshot."""
    s = json.load(open(os.path.join(SNAP, f"{nat_id}.json"), encoding="utf-8"))
    out = {}
    for L in s["lessons"]:
        tx = [b for b in L["blocks"] if b["mode"] == "text" and b.get("is_active", True)]
        if tx:
            out[L["lesson_id"]] = (tx[0]["block_id"], len(tx[0]["content"]))
    return s, out


def check(nat_id):
    """Returns a list of error strings (empty = OK)."""
    errs = []
    d = load(nat_id)
    s, texts = snapshot_text(nat_id)
    if d.get("nat_id") != nat_id:
        errs.append(f"nat_id mismatch: {d.get('nat_id')}")
    for L in d["lessons"]:
        lid, tag = L.get("lesson_id"), (L.get("title_hu") or "")[:30]
        if lid not in texts:
            errs.append(f"{tag}: lesson/text block not in snapshot"); continue
        bid, n = texts[lid]
        if L.get("text_block_id") != bid or L.get("n_text") != n:
            errs.append(f"{tag}: text block {L.get('text_block_id')}/{L.get('n_text')} ≠ snapshot {bid}/{n}")
        anchors = [c.get("anchor") for c in L["cards"]]
        if anchors != list(range(n)):
            errs.append(f"{tag}: anchors {anchors} ≠ 0..{n - 1}")
        for c in L["cards"]:
            if c.get("type") != "deep":
                errs.append(f"{tag}[{c.get('anchor')}]: type ≠ deep")
            for k in KEYS:
                if not (c.get(k) or "").strip():
                    errs.append(f"{tag}[{c.get('anchor')}]: empty {k}")
            blob = " ".join(str(c.get(k) or "") for k in KEYS + ("did_you_know",))
            for m in _A_VOWEL.findall(blob):
                errs.append(f"{tag}[{c.get('anchor')}]: „{m.strip()}” before a vowel")
            for m in _DOT_DECIMAL.findall(blob):
                errs.append(f"{tag}[{c.get('anchor')}]: decimal point „{m}” (use tizedesvessző)")
        text = json.dumps(L["cards"], ensure_ascii=False)
        az, a = len(_AZ_CONS.findall(text)), len(_A_CONS.findall(text))
        if az >= 4 and az > a:
            errs.append(f"{tag}: „az” before consonants {az}× (articles broken?)")
    missing = set(texts) - {L["lesson_id"] for L in d["lessons"]}
    for lid in missing:
        if not any(b["mode"] == "deep" and b.get("is_active", True)
                   for L in s["lessons"] if L["lesson_id"] == lid for b in L["blocks"]):
            errs.append(f"lesson {lid} has no deep block and none is written here")
    return errs


def ingest(nat_id, dry_run=False, replace=False, inactive=False):
    import httpx
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, "../../backend/.env"))
    SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    H = {"apikey": SVC, "Authorization": f"Bearer {SVC}", "Content-Type": "application/json"}
    d = load(nat_id)
    done = skipped = 0
    with httpx.Client(timeout=7.0) as c:
        for L in d["lessons"]:
            lid, tag = L["lesson_id"], L["title_hu"][:34]
            rows = c.get(f"{SB}/rest/v1/content_blocks?lesson_id=eq.{lid}&mode=in.(text,deep)"
                         f"&select=id,mode,topic_id,content,is_active", headers=H).json()
            text = [r for r in rows if r["mode"] == "text" and r["is_active"]]
            deep = [r for r in rows if r["mode"] == "deep"]
            if not text or text[0]["id"] != L["text_block_id"] or len(text[0]["content"]) != L["n_text"]:
                print(f"   ⚠ {tag}: live text block differs from the one the cards were written for — skipped")
                skipped += 1; continue
            if deep and not replace:
                print(f"   · {tag}: already has a deep block — skipped (use --replace)")
                skipped += 1; continue
            if dry_run:
                print(f"   ✓ {tag}: {len(L['cards'])} cards would be saved"); done += 1; continue
            c.request("DELETE", f"{SB}/rest/v1/content_blocks?lesson_id=eq.{lid}&mode=eq.deep",
                      headers=H).raise_for_status()
            c.post(f"{SB}/rest/v1/content_blocks", headers={**H, "Prefer": "return=minimal"}, json={
                "lesson_id": lid, "topic_id": text[0]["topic_id"], "mode": "deep", "level": "emelt",
                "scope": "lesson", "content": L["cards"],
                "review_status": "pending" if inactive else "approved", "is_active": not inactive,
            }).raise_for_status()
            print(f"   ✓ {tag}: {len(L['cards'])} cards saved"); done += 1
    print(f"{nat_id}: {done} saved, {skipped} skipped{' (dry run)' if dry_run else ''}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", nargs="*", metavar="NAT_ID", help="offline check (no NAT_ID = all files)")
    ap.add_argument("--nat-id")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--replace", action="store_true", help="overwrite an existing deep block")
    ap.add_argument("--inactive", action="store_true", help="save as pending/inactive for teacher review")
    a = ap.parse_args()
    files = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(DEEP, "*.json")))
    if a.check is not None:
        bad = 0
        for nat in a.check or files:
            errs = check(nat)
            print(("✗ " if errs else "✓ ") + nat)
            for e in errs:
                print("   " + e)
            bad += bool(errs)
        sys.exit(1 if bad else 0)
    for nat in (files if a.all else [a.nat_id] if a.nat_id else []):
        errs = check(nat)
        if errs:
            print(f"✗ {nat}: {len(errs)} check errors — not ingested (run --check {nat})"); continue
        ingest(nat, a.dry_run, a.replace, a.inactive)


if __name__ == "__main__":
    main()
