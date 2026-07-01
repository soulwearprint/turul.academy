"""
Advisory-flag sweep: run the guard rail (fact + appropriateness, advisory) across
all NAT topics, write per-topic reports, and aggregate the flags for teacher review.

Resumable + time-budgeted (foreground chunks survive this environment's teardown):
  python sweep_validate.py --minutes 8      # do as many as fit, then stop
Progress tracked in exports/_sweep_done.txt; aggregate in exports/_advisory_sweep.md.
Completeness is already 100% everywhere, so this is purely the advisory layer.
"""
import os, sys, time, json, httpx
import validate_temakor as V

HERE = os.path.dirname(__file__)
EXPORTS = os.path.join(HERE, "../exports")
DONE = os.path.join(EXPORTS, "_sweep_done.txt")
AGG = os.path.join(EXPORTS, "_advisory_sweep.md")
SB, H = V.SB, V.H_SB


def _argval(name, default=None):
    for a in sys.argv:
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
        if a == name:
            i = sys.argv.index(a)
            return sys.argv[i + 1] if i + 1 < len(sys.argv) else default
    return default


def main():
    minutes = float(_argval("--minutes", "0") or 0)
    deadline = time.time() + minutes * 60 if minutes else None
    done = set(open(DONE).read().split()) if os.path.exists(DONE) else set()

    with httpx.Client() as c:
        les = {l["topic_id"] for l in c.get(f"{SB}/rest/v1/curriculum_lessons?select=topic_id", headers=H).json()}
        topics = [t for t in c.get(f"{SB}/rest/v1/curriculum_topics?select=nat_id,title_hu,grade,id&order=grade,order_index", headers=H).json() if t["id"] in les]

    todo = [t for t in topics if t["nat_id"] not in done]
    print(f"NAT topics: {len(topics)} · done: {len(done)} · to sweep: {len(todo)}"
          f"{f' · budget {minutes}m' if minutes else ''}")

    for i, t in enumerate(todo, 1):
        if deadline and time.time() > deadline:
            print(f"⏱️  időkeret elérve — {i-1} feldolgozva ebben a futásban."); break
        nat = t["nat_id"]
        try:
            rep = V.validate(nat)
            open(os.path.join(EXPORTS, f"{nat}_validation.md"), "w", encoding="utf-8").write(V._report_md(rep))
            facts = len(rep["fact"]); appro = len(rep["appropriateness"])
            print(f"  [{i}/{len(todo)}] {nat} → {rep['verdict']} · tény {facts} · megfelelőség {appro}")
        except Exception as e:
            print(f"  [{i}/{len(todo)}] {nat} → ERROR {str(e)[:60]}")
        with open(DONE, "a") as f:
            f.write(nat + "\n")

    _aggregate()


def _aggregate():
    """Build the aggregate advisory report from the per-topic _validation.md files."""
    done = open(DONE).read().split() if os.path.exists(DONE) else []
    lines = ["# Tanári felülvizsgálati lista — összegzés (advisory)",
             f"\n_{len(done)} témakör átnézve. A teljesség (NAT-lefedettség) máshol 100%; ez a tény- és "
             "megfelelőségi jelölések gyűjtése._\n"]
    for nat in done:
        p = os.path.join(EXPORTS, f"{nat}_validation.md")
        if not os.path.exists(p):
            continue
        body = open(p, encoding="utf-8").read()
        # keep only the fact + appropriateness sections' flagged bullets
        flags = [ln for ln in body.splitlines() if ln.startswith("- **FELÜLVIZSGÁLAT") or ln.startswith("- **WARN")]
        if flags:
            title = body.splitlines()[0].replace("# Validáció — ", "")
            lines.append(f"\n### {title}")
            lines += flags
    open(AGG, "w", encoding="utf-8").write("\n".join(lines))
    print(f"→ aggregate: {AGG}")


if __name__ == "__main__":
    main()
