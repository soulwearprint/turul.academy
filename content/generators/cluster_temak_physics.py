"""
Second parse pass — Physics. Derives the missing Téma (sub-lesson) tier.

Physics's kerettanterv docx has no Téma breakdown (unlike History's table rows) —
just a flat list of Fejlesztési feladatok bullets per Témakör (see
parse_nat_physics.py). Per the user's confirmed direction (2026-07-08), an LLM
clusters each Témakör's bullets into 2-4 coherent Témák with sensible titles.
Runs ONCE; output is meant to be reviewed before seeding, then reused as a static
map (mirrors history_nat2020_temak.json), not re-clustered on every generation run.

Input:  content/nat_curriculum/physics_nat2020.json (parse_nat_physics.py output)
Output: content/nat_curriculum/physics_nat2020_temak.json
  { "<school>::<title>": {
        "school": "F"|"K", "band": "7-8"|"9-10", "title": "...", "oraszam": int,
        "temak": [ {"title": "...", "feladatok": ["...", ...]} ],
        "fogalmak": [...], "tevekenysegek": [...]   # NOT yet distributed to Témák —
                                                     # that's generate_temakor.py's job,
                                                     # same as History's distribute_elements
  }, ... }

Usage:
    python cluster_temak_physics.py
    python cluster_temak_physics.py --dry-run    # print only, don't write
"""
import os, sys, json, asyncio, httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
RK = os.getenv("OPENROUTER_API_KEY")
MODEL = "openai/gpt-4o"   # precision matters — this defines the DB lesson structure permanently
OR = "https://openrouter.ai/api/v1/chat/completions"
H_OR = {"Authorization": f"Bearer {RK}", "Content-Type": "application/json",
        "HTTP-Referer": "https://turul.academy", "X-Title": "Turul"}

HERE = os.path.dirname(__file__)
IN = os.path.join(HERE, "../nat_curriculum/physics_nat2020.json")
OUT = os.path.join(HERE, "../nat_curriculum/physics_nat2020_temak.json")
DRY = "--dry-run" in sys.argv

SYS = ("Te egy tapasztalt magyar fizikatanár és tananyagfejlesztő vagy. Feladatod a NAT 2020 "
       "fizika kerettanterv egy témakörének fejlesztési feladatait koherens leckékbe (Témákba) "
       "csoportosítani. CSAK érvényes JSON-t adsz vissza.")


async def ai(c, prompt, temp=0):
    r = await c.post(OR, headers=H_OR, json={
        "model": MODEL, "max_tokens": 2000, "temperature": temp,
        "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": prompt}],
    }, timeout=120)
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.splitlines()[1:-1])
    return json.loads(raw)


def build_prompt(topic):
    feladatok = topic["fejlesztesi_feladatok"]
    numbered = "\n".join(f"{i+1}. {f}" for i, f in enumerate(feladatok))
    return (
        f"Témakör: „{topic['temakor']}” ({topic['oraszam']} óra)\n\n"
        f"Fejlesztési feladatok és ismeretek (mindet EGY Témához kell rendelni, egyet se hagyj ki):\n"
        f"{numbered}\n\n"
        "Csoportosítsd ezeket a feladatokat 2-4 koherens Témába (leckébe) — minden Témának legyen "
        "rövid, tartalmat jól kifejező címe, és a hozzá tartozó feladatok logikailag összetartozzanak "
        "(pl. közös jelenség, közös mérési/számítási készség, közös eszköz). A csoportosítás kövesse a "
        "feladatok EREDETI SORRENDJÉT (ne keverd össze a tananyag felépítését) — egy Téma mindig egy "
        "ÖSSZEFÜGGŐ szakaszt fedjen le a listából, ne szórtan válogass. MINDEN feladatot pontosan egy "
        "Témához rendelj, szó szerint (ne írd át, ne rövidítsd).\n"
        'JSON: {"temak": [{"title": "...", "feladat_szamok": [1,2,3]}, ...]}'
    )


async def cluster_topic(c, topic):
    out = await ai(c, build_prompt(topic))
    feladatok = topic["fejlesztesi_feladatok"]
    temak = []
    covered = set()
    for tm in out.get("temak", []):
        nums = [n - 1 for n in tm.get("feladat_szamok", []) if 0 <= n - 1 < len(feladatok)]
        covered.update(nums)
        temak.append({"title": tm["title"].strip(), "feladatok": [feladatok[i] for i in sorted(nums)]})
    # completeness guard: any bullet the LLM missed goes into the last Téma, in order
    missing = [i for i in range(len(feladatok)) if i not in covered]
    if missing and temak:
        temak[-1]["feladatok"].extend(feladatok[i] for i in missing)
    elif missing:  # LLM returned nothing usable — one Téma, everything in it
        temak = [{"title": topic["temakor"], "feladatok": feladatok}]
    return temak


async def main():
    data = json.load(open(IN, encoding="utf-8"))
    result = {}
    async with httpx.AsyncClient() as c:
        for section, sc in (("altalanos_iskola", "F"), ("gimnazium", "K")):
            for band, topics in data[section].items():
                for topic in topics:
                    title = topic["temakor"].strip()
                    print(f"🗂️  [{sc}] {title} ({len(topic['fejlesztesi_feladatok'])} feladat)…")
                    temak = await cluster_topic(c, topic)
                    for tm in temak:
                        print(f"   - {tm['title']}  ({len(tm['feladatok'])} feladat)")
                    result[f"{sc}::{title}"] = {
                        "school": sc, "band": band, "title": title, "oraszam": topic["oraszam"],
                        "temak": temak,
                        "fogalmak": topic["fogalmak"], "tevekenysegek": topic["tevekenysegek"],
                    }

    n_temak = sum(len(v["temak"]) for v in result.values())
    print(f"\nTémakörök: {len(result)}  Témák total: {n_temak}")
    if DRY:
        print("(dry-run — not writing)")
        return
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"→ {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
