"""Export every Témakör's content_blocks to content/snapshot/<nat_id>.json for offline QA.

The fact-check session has no DB access, so it reads lessons from this snapshot. Findings
reference `block_id` + card index — fixes go back through the edit_content_card RPC, which
indexes `content` directly, so `content` is exported exactly as stored (all modes, inactive
blocks too, with their `is_active` flag).

Usage (from content/generators):
  PYTHONPATH=. python export_snapshot.py                 # all bands
  PYTHONPATH=. python export_snapshot.py HIST-56 HIST-78 # only these bands

INDEX.json is rebuilt from every snapshot file on disk, so exporting band by band keeps it complete.
"""
import os, sys, json, glob, datetime, httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SVC, "Authorization": f"Bearer {SVC}"}
OUT = os.path.join(os.path.dirname(__file__), "../snapshot")
BANDS = ["HIST-56", "HIST-78", "PHYS-78", "HIST-910", "PHYS-910", "HIST-1112"]   # audit order
MODE_ORDER = ["text", "story", "visual", "world", "experiment", "deep", "quiz"]


def band_of(nat_id):
    return nat_id.rsplit("-", 1)[0]


def get(c, path):
    r = c.get(f"{SB}/rest/v1/{path}", headers=H, timeout=7.0)
    r.raise_for_status()
    return r.json()


def block_json(b):
    if not isinstance(b["content"], list):
        print(f"   ⚠ block {b['id']} ({b['mode']}): content is not a card array")
    return {"block_id": b["id"], "mode": b["mode"], "scope": b["scope"], "level": b["level"],
            "is_active": b["is_active"], "content": b["content"]}


def sort_key(b):
    m = b["mode"]
    return (MODE_ORDER.index(m) if m in MODE_ORDER else len(MODE_ORDER), m, b["level"] or "", b["id"])


def export_topic(c, t):
    lessons = get(c, f"curriculum_lessons?topic_id=eq.{t['id']}&select=id,title_hu,order_index&order=order_index")
    blocks = get(c, f"content_blocks?topic_id=eq.{t['id']}&select=id,lesson_id,mode,scope,level,is_active,content")
    blocks.sort(key=sort_key)
    snap = {"nat_id": t["nat_id"], "topic_id": t["id"], "title_hu": t["title_hu"], "grade": t["grade"],
            "lessons": [{"lesson_id": L["id"], "title_hu": L["title_hu"], "order_index": L["order_index"],
                         "blocks": [block_json(b) for b in blocks
                                    if b["scope"] == "lesson" and b["lesson_id"] == L["id"]]}
                        for L in lessons],
            "topic_blocks": [block_json(b) for b in blocks if b["scope"] == "topic"]}
    known = {L["id"] for L in lessons}
    orphans = [b for b in blocks if b["scope"] == "lesson" and b["lesson_id"] not in known]
    if orphans:
        print(f"   ⚠ {t['nat_id']}: {len(orphans)} lesson-scope block(s) with no matching lesson — not exported")
    with open(os.path.join(OUT, f"{t['nat_id']}.json"), "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
        f.write("\n")
    n_blocks = sum(len(L["blocks"]) for L in snap["lessons"]) + len(snap["topic_blocks"])
    print(f"   ✓ {t['nat_id']}: {len(lessons)} Téma, {n_blocks} blokk")


def write_index():
    rows = []
    for path in glob.glob(os.path.join(OUT, "*.json")):
        if os.path.basename(path) == "INDEX.json":
            continue
        with open(path, encoding="utf-8") as f:
            s = json.load(f)
        band = band_of(s["nat_id"])
        rows.append({"nat_id": s["nat_id"], "band": band, "lessons": len(s["lessons"]),
                     "has_deep_all": bool(s["lessons"]) and all(
                         any(b["mode"] == "deep" for b in L["blocks"]) for L in s["lessons"])})
    rows.sort(key=lambda r: (BANDS.index(r["band"]) if r["band"] in BANDS else len(BANDS), r["nat_id"]))
    index = {"exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "topics": rows}
    with open(os.path.join(OUT, "INDEX.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"📇 INDEX.json: {len(rows)} Témakör")


def main():
    bands = sys.argv[1:] or BANDS
    os.makedirs(OUT, exist_ok=True)
    with httpx.Client() as c:
        topics = get(c, "curriculum_topics?select=id,nat_id,title_hu,grade&order=nat_id")
        for band in bands:
            todo = [t for t in topics if band_of(t["nat_id"]) == band]
            print(f"\n📦 {band} — {len(todo)} Témakör")
            for t in todo:
                export_topic(c, t)
    write_index()


if __name__ == "__main__":
    main()
