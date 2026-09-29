"""
Attaches visuals to „visual” cards of one topic, from a reviewed manifest, and records each in
media_refs (licence/review trail — see database/migrations/v10_media_refs.sql).

Manifest items (content/media/<NAT-ID>_*.json):
  {"tema": "<curriculum_lessons.title_hu>", "match": ["kulcsszó", ...], "title": "...", "alt": "...",
   "diagram": {viewBox, shapes}}                      -> in-house SVG, stored as card.diagram
  {..., "media": {"src": "/media/<NAT-ID>/x.jpg", "source_url", "author", "license", "license_url",
                  "credit", "status": "approved"}}   -> sourced photo, stored as card.media
A card is matched when its heading/description contains any `match` keyword; the first
not-yet-visualised card wins, so one manifest item never overwrites another's card. Photo items
are applied ONLY when media.status == "approved" (the curator sets that by hand after checking
the licence — source_media.py never does).

Usage (dry-run by default; prints the card each item would land on):
    python apply_media.py --nat-id PHYS-78-03 --file ../media/PHYS-78-03_diagrams.json [--apply]
"""
import os, sys, json, argparse
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SVC, "Authorization": f"Bearer {SVC}", "Content-Type": "application/json"}


def find_card(cards, keywords, taken):
    kws = [k.lower() for k in keywords]
    for i, c in enumerate(cards):
        if i in taken:
            continue
        hay = f"{c.get('heading', '')} {c.get('description', '')}".lower()
        if any(k in hay for k in kws):
            return i
    return None


def plan(cards, items):
    """[(item, card_index|None)] — pure, no I/O."""
    taken, out = set(), []
    for it in items:
        i = find_card(cards, it["match"], taken)
        if i is not None:
            taken.add(i)
        out.append((it, i))
    return out


def ref_row(it):
    m = it.get("media")
    if m:
        return {"kind": "photo", "title": it.get("title"), "source_url": m.get("source_url"), "asset_path": m["src"],
                "author": m.get("author"), "license": m["license"], "license_url": m.get("license_url"),
                "attribution": m["credit"], "status": "approved", "verified_at": m.get("verified_at")}
    return {"kind": "diagram", "title": it.get("title"), "license": "in-house", "attribution": "Turul Academy",
            "status": "approved"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nat-id", required=True); ap.add_argument("--file", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    items = json.load(open(a.file, encoding="utf-8"))["items"]
    with httpx.Client(timeout=30) as c:
        t = c.get(f"{SB}/rest/v1/curriculum_topics?nat_id=eq.{a.nat_id}&select=id", headers=H).json()
        if not t:
            print(f"topic {a.nat_id} not found"); sys.exit(1)
        tid = t[0]["id"]
        lessons = {l["title_hu"]: l["id"] for l in c.get(
            f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{tid}&select=id,title_hu", headers=H).json()}
        for tema in sorted({i["tema"] for i in items}):
            lid = lessons.get(tema)
            if not lid:
                print(f"✗ Téma not found: {tema}"); continue
            blk = c.get(f"{SB}/rest/v1/content_blocks?lesson_id=eq.{lid}&mode=eq.visual&level=eq.alap&select=id,content",
                        headers=H).json()
            if not blk:
                print(f"✗ no visual block: {tema}"); continue
            cards = blk[0]["content"]
            mine = [i for i in items if i["tema"] == tema]
            for it, idx in plan(cards, mine):
                if idx is None:
                    print(f"  ✗ no card matches {it['match']} ({it['title']})"); continue
                if it.get("media") and it["media"].get("status") != "approved":
                    print(f"  ⏸ {it['title']}: media not approved, skipped"); continue
                print(f"  ✓ {it['title']}  →  card {idx}: {cards[idx].get('heading')}")
                if it.get("media"):
                    cards[idx]["media"] = {k: it["media"][k] for k in ("src", "credit", "license", "license_url", "source_url") if it["media"].get(k)} | {"alt": it["alt"]}
                else:
                    cards[idx]["diagram"] = it["diagram"]
                if a.apply:
                    row = ref_row(it) | {"topic_id": tid, "lesson_id": lid, "card_heading": cards[idx].get("heading", "")}
                    r = c.post(f"{SB}/rest/v1/media_refs", headers=H | {"Prefer": "return=minimal"}, json=row); r.raise_for_status()
            if a.apply:
                r = c.patch(f"{SB}/rest/v1/content_blocks?id=eq.{blk[0]['id']}", headers=H | {"Prefer": "return=minimal"},
                            json={"content": cards}); r.raise_for_status()
    print("applied" if a.apply else "dry-run (no writes) — re-run with --apply")


if __name__ == "__main__":
    main()
