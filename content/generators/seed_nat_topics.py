"""
Seed all 54 NAT History Témakörök as NEW curriculum_topics (is_active=false) plus
their Témák (curriculum_lessons), from history_nat2020_temak.json. Additive: the
legacy `lessons` table + old topics that the live app uses are untouched.

Idempotent: a Témakör already present (matched by title_hu + school F/K) is skipped,
so the existing WWI (HIST-78-VH1) and medieval (HIST-56-MA1) slices are preserved.
No content is generated here — that's generate_temakor.py's job.

    python seed_nat_topics.py          # seed
    python seed_nat_topics.py --dry-run

NOTE on grade assignment: the NAT curriculum only specifies topics at the BAND level
(5-6, 7-8, 9-10, 11-12) — the source docx never assigns a Témakör to one specific
grade; that's local/teacher planning. A within-band split is computed here, balanced
by each topic's recommended teaching hours (`javasolt óraszám`) in curriculum order —
first half of the band's hours -> the lower grade, rest -> the upper grade. (An earlier
version hardcoded a single representative grade for the whole band, which put every
topic on the band's lower grade and left the upper grade empty — fixed 2026-07-07.)
"""
import os, json, sys, httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SVC, "Authorization": f"Bearer {SVC}", "Content-Type": "application/json"}
MAP = os.path.join(os.path.dirname(__file__), "../nat_curriculum/history_nat2020_temak.json")
NAT_JSON = os.path.join(os.path.dirname(__file__), "../nat_curriculum/history_nat2020.json")
SUBJECT_HISTORY = "b5122740-fbd9-4c78-b3dd-c36172565e07"
DRY = "--dry-run" in sys.argv

# band -> (nat_id code, (lower_grade, upper_grade), order_index base)
BAND = {"5-6": ("56", (5, 6), 0), "7-8": ("78", (7, 8), 100),
        "9-10": ("910", (9, 10), 200), "11-12": ("1112", (11, 12), 300)}

def school_of_grade(g): return "F" if (g or 0) <= 8 else "K"


def _compute_grade_map(m):
    """Hours-balanced within-band split: walk each band's Témakörök in curriculum
    order, accumulate recommended hours, and switch from the lower to the upper
    grade once cumulative hours cross the band's 50% mark. Returns
    {(school, band, title): grade}."""
    nat = json.load(open(NAT_JSON, encoding="utf-8"))
    hours = {}
    for section, sc in (("altalanos_iskola", "F"), ("gimnazium", "K")):
        for band, arr in nat[section].items():
            for t in arr:
                hours[(sc, band, t["temakor"].strip().lower())] = t.get("oraszam", 0)

    by_band = {}
    for entry in m.values():
        by_band.setdefault((entry["school"], entry["band"]), []).append(entry["title"].strip())

    grade_map = {}
    for (sc, band), titles in by_band.items():
        lo, hi = BAND[band][1]
        hs = [hours.get((sc, band, t.lower()), 0) for t in titles]
        total = sum(hs)
        cum, split_i = 0, len(titles)
        for i, h in enumerate(hs):
            cum += h
            if cum >= total / 2:
                split_i = i + 1
                break
        for i, t in enumerate(titles):
            grade_map[(sc, band, t)] = lo if i < split_i else hi
    return grade_map


def main():
    m = json.load(open(MAP, encoding="utf-8"))
    grade_map = _compute_grade_map(m)
    with httpx.Client() as c:
        existing = c.get(f"{SB}/rest/v1/curriculum_topics?select=id,title_hu,grade,nat_id", headers=H).json()
        used_nat = {t["nat_id"] for t in existing if t["nat_id"]}
        # Only topics that ALREADY have curriculum_lessons are NAT 3-tier topics (mine).
        # Old/legacy topics share some titles but have no lessons — never reuse them.
        nat_topic_ids = {l["topic_id"] for l in
                         c.get(f"{SB}/rest/v1/curriculum_lessons?select=topic_id", headers=H).json()}
        have = {(t["title_hu"].strip(), school_of_grade(t["grade"])): t
                for t in existing if t["id"] in nat_topic_ids}

        seq = {b: 0 for b in BAND}
        created_t = created_l = skipped = 0
        for entry in m.values():
            band = entry["band"]; school = entry["school"]; title = entry["title"].strip()
            code, _, base = BAND[band]
            grade = grade_map[(school, band, title)]
            seq[band] += 1
            key = (title, school)
            if key in have:
                skipped += 1
                topic = have[key]
                topic_id = topic["id"]
            else:
                nat_id = f"HIST-{code}-{seq[band]:02d}"
                while nat_id in used_nat:
                    seq[band] += 1; nat_id = f"HIST-{code}-{seq[band]:02d}"
                used_nat.add(nat_id)
                payload = {"subject_id": SUBJECT_HISTORY, "nat_id": nat_id,
                           "title": title, "title_hu": title, "grade": grade,
                           "order_index": base + seq[band], "is_active": False}
                print(f"+ TOPIC {nat_id} [{band}] {title}")
                if DRY:
                    topic_id = None
                else:
                    r = c.post(f"{SB}/rest/v1/curriculum_topics", headers={**H, "Prefer": "return=representation"}, json=payload)
                    r.raise_for_status(); topic_id = r.json()[0]["id"]
                    nat_for_lessons = nat_id
                created_t += 1
                topic = {"id": topic_id, "nat_id": nat_id}

            # ensure Témák (lessons)
            nat_for_lessons = topic["nat_id"]
            existing_l = [] if (DRY and topic_id is None) else \
                c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{topic_id}&select=title_hu", headers=H).json()
            have_l = {l["title_hu"].strip() for l in existing_l}
            for i, tm in enumerate(entry["temak"], start=1):
                if tm["title"].strip() in have_l:
                    continue
                lp = {"topic_id": topic_id, "nat_id": f"{nat_for_lessons}-T{i}",
                      "title": tm["title"], "title_hu": tm["title"], "order_index": i, "is_active": False}
                if not DRY:
                    c.post(f"{SB}/rest/v1/curriculum_lessons", headers={**H, "Prefer": "return=minimal"}, json=lp).raise_for_status()
                created_l += 1

        print(f"\n{'(dry) ' if DRY else ''}topics created: {created_t}  skipped(existing): {skipped}  Témák created: {created_l}")


if __name__ == "__main__":
    main()
