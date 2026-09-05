"""
Commits pre-generated Physics topic content (produced by a Claude agent, NOT
generate_temakor_physics.py's OpenRouter path) to Supabase. Exists so agents write
JSON to a file and call this script — safe REST/JSON writes, no hand-built SQL
against Hungarian text full of quotes/apostrophes.

Input JSON shape:
{
  "temak": {
    "<Téma cím, EXACTLY matching physics_nat2020_temak.json>": {
      "text": {"title": "...", "cards": [...]},
      "story": {...}, "visual": {...}, "quiz": {...}, "experiment": {...}
    }, ...
  },
  "topic_quiz": {"title": "Témazáró kvíz", "cards": [...]}
}

Usage:
    python ingest_topic_content.py --nat-id PHYS-78-01 --file /path/to/content.json
"""
import os, json, argparse, sys
import httpx
from dotenv import load_dotenv
from generate_temakor import cards_from

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H_SB = {"apikey": SVC, "Authorization": f"Bearer {SVC}", "Content-Type": "application/json"}
TEMAK_MAP = os.path.join(os.path.dirname(__file__), "../nat_curriculum/physics_nat2020_temak.json")
ALL_MODES = ["text", "story", "visual", "quiz", "experiment"]


def school_of_grade(grade):
    return "F" if (grade or 0) <= 8 else "K"


def lookup_temakor(title_hu, grade):
    m = json.load(open(TEMAK_MAP, encoding="utf-8"))
    sc = school_of_grade(grade)
    key = f"{sc}::{title_hu.strip()}"
    if key in m:
        return m[key]
    cands = [v for v in m.values() if v["title"].strip().lower() == title_hu.strip().lower()]
    return cands[0] if cands else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nat-id", required=True)
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    payload = json.load(open(args.file, encoding="utf-8"))
    temak_content = payload["temak"]
    topic_quiz = payload.get("topic_quiz")

    with httpx.Client(timeout=60) as c:
        t = c.get(f"{SB}/rest/v1/curriculum_topics?nat_id=eq.{args.nat_id}&select=id,title_hu,grade", headers=H_SB).json()
        if not t:
            print(f"⚠ topic {args.nat_id} not found"); sys.exit(1)
        t = t[0]; topic_id, temakor, grade = t["id"], t["title_hu"], t.get("grade")

        nat = lookup_temakor(temakor, grade)
        if not nat:
            print(f"⚠ no physics NAT map entry for „{temakor}” (grade {grade})"); sys.exit(1)
        expected_titles = {tm["title"].strip() for tm in nat["temak"]}
        got_titles = {k.strip() for k in temak_content.keys()}
        if expected_titles != got_titles:
            print(f"⚠ Téma title mismatch.\n  expected: {sorted(expected_titles)}\n  got: {sorted(got_titles)}")
            sys.exit(1)

        # ensure lessons exist
        existing = c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{topic_id}&select=id,title_hu&order=order_index", headers=H_SB).json()
        have = {L["title_hu"].strip() for L in existing}
        for i, tm in enumerate(nat["temak"], start=1):
            if tm["title"].strip() in have:
                continue
            lp = {"topic_id": topic_id, "nat_id": f"{args.nat_id}-T{i}", "title": tm["title"],
                  "title_hu": tm["title"], "order_index": i, "is_active": False}
            c.post(f"{SB}/rest/v1/curriculum_lessons", headers={**H_SB, "Prefer": "return=minimal"}, json=lp).raise_for_status()
        lessons = c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{topic_id}&select=id,title_hu", headers=H_SB).json()
        by_title = {L["title_hu"].strip(): L for L in lessons}

        # wipe existing content for a clean re-ingest (idempotent)
        for L in lessons:
            c.request("DELETE", f"{SB}/rest/v1/content_blocks?lesson_id=eq.{L['id']}", headers=H_SB)
        c.request("DELETE", f"{SB}/rest/v1/content_blocks?topic_id=eq.{topic_id}&lesson_id=is.null", headers=H_SB)

        n_blocks = 0
        for title, modes in temak_content.items():
            L = by_title.get(title.strip())
            if not L:
                print(f"⚠ lesson not found after ensure: {title}"); continue
            for mode in ALL_MODES:
                obj = modes.get(mode)
                if not obj:
                    print(f"⚠ missing mode {mode} for „{title}”"); continue
                block = {"lesson_id": L["id"], "topic_id": topic_id, "mode": mode, "level": "alap",
                         "scope": "lesson", "content": cards_from(obj), "review_status": "approved", "is_active": True}
                c.post(f"{SB}/rest/v1/content_blocks", headers={**H_SB, "Prefer": "return=minimal"}, json=block).raise_for_status()
                n_blocks += 1

        if topic_quiz:
            block = {"lesson_id": None, "topic_id": topic_id, "mode": "quiz", "level": "alap",
                     "scope": "topic", "content": cards_from(topic_quiz), "review_status": "approved", "is_active": True}
            c.post(f"{SB}/rest/v1/content_blocks", headers={**H_SB, "Prefer": "return=minimal"}, json=block).raise_for_status()
            n_blocks += 1

        print(f"✅ {args.nat_id}: {n_blocks} blocks ingested ({len(temak_content)} Téma).")


if __name__ == "__main__":
    main()
