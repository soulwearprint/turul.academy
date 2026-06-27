"""
Full generation run across all NAT History Témakörök, with the guard rail +
auto-fix-and-recheck loop on each (see generate_temakor.generate_topic).

By default only generates topics that have NO content yet (skips the already-done
slices). Use --regen-all to regenerate everything, or --nat-ids a,b,c to target.

    python run_all_nat.py                 # generate all empty NAT topics
    python run_all_nat.py --regen-all     # regenerate every NAT topic
    python run_all_nat.py --nat-ids HIST-78-01,HIST-910-03

Writes a verdict summary to content/exports/_full_run_summary.md.
"""
import os, sys, json, asyncio, httpx
import generate_temakor as G

SB, H_SB = G.SB, G.H_SB
SUMMARY = os.path.join(os.path.dirname(__file__), "../exports/_full_run_summary.md")


async def main():
    regen_all = "--regen-all" in sys.argv
    target = None
    for a in sys.argv:
        if a.startswith("--nat-ids"):
            target = set((a.split("=", 1)[1] if "=" in a else sys.argv[sys.argv.index(a) + 1]).split(","))

    async with httpx.AsyncClient() as c:
        lessons = (await c.get(f"{SB}/rest/v1/curriculum_lessons?select=topic_id", headers=H_SB)).json()
        nat_topic_ids = {l["topic_id"] for l in lessons}
        topics = (await c.get(f"{SB}/rest/v1/curriculum_topics?select=id,nat_id,title_hu,grade,order_index&order=order_index", headers=H_SB)).json()
        topics = [t for t in topics if t["id"] in nat_topic_ids]
        blocks = (await c.get(f"{SB}/rest/v1/content_blocks?select=topic_id", headers=H_SB)).json()
        has_content = {b["topic_id"] for b in blocks}

        if target:
            todo = [t for t in topics if t["nat_id"] in target]
        elif regen_all:
            todo = topics
        else:
            todo = [t for t in topics if t["id"] not in has_content]

        print(f"NAT topics: {len(topics)}  ·  to generate: {len(todo)}"
              f"{' (regen-all)' if regen_all else ''}\n")

        results = []
        for i, t in enumerate(todo, 1):
            print("\n" + "#" * 70 + f"\n# [{i}/{len(todo)}] {t['nat_id']}  {t['title_hu']}\n" + "#" * 70)
            try:
                rep = await G.generate_topic(c, t["nat_id"], validate=True, autofix=True)
                verdict = rep["verdict"] if rep else "ERROR"
                facts = len(rep["fact"]) if rep else 0
                appro = len(rep["appropriateness"]) if rep else 0
                comp = sum(1 for x in rep["completeness"] if x[0] == "FAIL") if rep else -1
                cov = rep["coverage"] if rep else "?"
            except Exception as e:
                verdict, facts, appro, comp, cov = "ERROR", 0, 0, -1, str(e)[:40]
            results.append((t["nat_id"], t["title_hu"], verdict, cov, comp, facts, appro))

        # summary
        lines = ["# Teljes generálási futás — összegzés\n",
                 "| nat_id | Témakör | verdict | lefedettség | comp-FAIL | tény-jelölés | megfelelőség |",
                 "|---|---|---|---|---|---|---|"]
        for nat, title, v, cov, comp, f, a in results:
            lines.append(f"| {nat} | {title} | **{v}** | {cov} | {comp} | {f} | {a} |")
        from collections import Counter
        tally = Counter(r[2] for r in results)
        lines.append(f"\n**Összesítés:** {dict(tally)}  ·  összesen {len(results)} témakör.")
        open(SUMMARY, "w", encoding="utf-8").write("\n".join(lines))
        print("\n" + "\n".join(lines))
        print(f"\n→ {SUMMARY}")


if __name__ == "__main__":
    asyncio.run(main())
