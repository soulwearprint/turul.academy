"""
Per-Témakör content guard rail — Physics. Parallel to validate_temakor.py (History),
reusing its subject-agnostic string-matching helpers (_norm/_fold/_covered/_ai_json)
rather than duplicating them.

Three checks, same shape as History's guard rail:
  1. COMPLETENESS (deterministic) — every mandatory `feladat` (fact) and `fogalom`
     (concept) is taught in the non-experiment lesson blocks; every Téma has all
     expected modes + a topic quiz.
  2. FACT          (LLM) — flags physics/factual inaccuracies.
  3. APPROPRIATENESS (LLM) — grade-fit, brand voice, Hungarian-only (reuses History's
     APPRO_SYS as-is — it's already subject-agnostic).
Plus an EXPERIMENT-layer relevance check (mirrors History's world-relevance check):
flags cards that invent a discovery/sketch/today when the lesson doesn't genuinely
support it, instead of honestly saying so.

Usage:
    python validate_temakor_physics.py PHYS-78-01
Exit code: 0 = PASS (no FAIL-level issues), 1 = FAIL.
"""
import os, json, sys, asyncio, httpx
from dotenv import load_dotenv
from validate_temakor import _norm, _fold, _covered, _ai_json, APPRO_SYS

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
RK = os.getenv("OPENROUTER_API_KEY")
CHECK_MODEL = "openai/gpt-4o"
OR = "https://openrouter.ai/api/v1/chat/completions"
H_OR = {"Authorization": f"Bearer {RK}", "Content-Type": "application/json",
        "HTTP-Referer": "https://turul.academy", "X-Title": "Turul"}
H_SB = {"apikey": SVC, "Authorization": f"Bearer {SVC}"}
NAT_JSON = os.path.join(os.path.dirname(__file__), "../nat_curriculum/physics_nat2020_temak.json")
EXPECTED_MODES = ["text", "story", "visual", "quiz", "experiment"]


def _band_label(grade):
    g = grade or 0
    return {7: "7–8", 8: "7–8", 9: "9–10", 10: "9–10"}.get(g, "7–8")


def _load_nat_elements(title_hu, grade):
    d = json.load(open(NAT_JSON, encoding="utf-8"))
    sc = "F" if (grade or 0) <= 8 else "K"
    key = f"{sc}::{title_hu.strip()}"
    if key in d:
        return d[key]
    cands = [v for v in d.values() if v["title"].strip().lower() == title_hu.strip().lower()]
    return cands[0] if cands else None


# ---------- feladatok coverage: LLM-judged (see _completeness docstring) ----------
FELADAT_COVERAGE_SYS = ("Te tapasztalt magyar fizikatanár vagy, aki azt ellenőrzi, hogy egy tananyag "
    "ÉRDEMBEN lefedi-e a kötelező feladatokat/ismereteket. Egy feladat LEFEDETTNEK számít, ha a "
    "tananyag a diák számára érthetően tanítja a benne lévő fizikai tartalmat/készséget — NEM kell "
    "szó szerint egyeznie a megfogalmazásnak, parafrázis és eltérő szórend rendben van, és a forrás "
    "olykor helyesírási hibát vagy pontatlan szóalakot tartalmazhat (ez sem hiány). CSAK azt jelöld "
    "hiányzónak, aminek TARTALMILAG tényleg nincs nyoma a tananyagban. CSAK érvényes JSON-t adsz vissza.")


FELADAT_CONFIRM_SYS = ("Te vezető magyar fizikatanár vagy, aki egy kollégád „hiányzik” jelöléseit "
    "BÍRÁLOD FELÜL, mielőtt egy tananyagot hiányosnak minősítenétek. Mindegyik jelölt feladatnál "
    "keresd meg ÚJRA, alaposan a tananyagban — gyakran előfordul, hogy a tartalom más megfogalmazással, "
    "más kártyán, vagy a cím/heading mezőben mégis lefedi. CSAK azt tartsd meg hiányzóként, amiről "
    "biztos vagy, hogy tényleg nincs nyoma. CSAK érvényes JSON-t adsz vissza.")


async def _feladatok_missing(c, feladatok, text):
    """Which mandatory `feladatok` (full prose sentences from the kerettanterv docx) have
    no substantive coverage in the generated content. LLM-judged rather than the deterministic
    token-matcher validate_temakor.py uses for History's atomic fogalmak/szemelyek/kronologia —
    Physics's feladatok are full sentences, so literal/token matching false-negatives on
    genuinely-covered, paraphrased content (and on the source docx's own typos) far more than
    it catches real gaps. A second confirm pass (mirrors _confirm_facts) catches the first pass's
    occasional over-strict misses, e.g. flagging a topic as uncovered when a card's own heading
    states it almost verbatim."""
    if not feladatok:
        return set()
    numbered = "\n".join(f"{i+1}. {f}" for i, f in enumerate(feladatok))
    out = await _ai_json(c, FELADAT_COVERAGE_SYS,
        f"KÖTELEZŐ FELADATOK (számozva):\n{numbered}\n\nTANANYAG (a lecke-kártyák tartalma):\n{text}\n\n"
        'Add vissza AZOKNAK a sorszámát, amik TARTALMILAG nincsenek lefedve:\n{"missing":[1,3]}\n'
        "Ha minden feladat le van fedve, üres tömb.", model=CHECK_MODEL, maxtok=800)
    idx = sorted({n for n in out.get("missing", []) if isinstance(n, int) and 1 <= n <= len(feladatok)})
    if not idx:
        return set()

    cand = "\n".join(f"{n}. {feladatok[n - 1]}" for n in idx)
    confirm = await _ai_json(c, FELADAT_CONFIRM_SYS,
        f"JELÖLT HIÁNYZÓ FELADATOK:\n{cand}\n\nTANANYAG (a lecke-kártyák tartalma):\n{text}\n\n"
        'Add vissza a VALÓBAN hiányzók sorszámát:\n{"missing":[1,3]}\nHa egyik sem igazán hiányzik, üres tömb.',
        model=CHECK_MODEL, maxtok=600)
    confirmed = {n for n in confirm.get("missing", []) if isinstance(n, int) and 1 <= n <= len(feladatok)}
    return {feladatok[n - 1] for n in confirmed}


# ---------- check 1: completeness (deterministic structure + fogalmak, LLM-judged feladatok) ----------
async def _completeness(c, lessons, blocks_by_lesson, topic_quiz, nat_entry):
    issues = []
    missing = []
    for L in lessons:
        present = {b["mode"] for b in blocks_by_lesson.get(L["id"], [])}
        for m in EXPECTED_MODES:
            if m not in present:
                issues.append(("FAIL", f"„{L['title_hu']}”: hiányzó mód: {m}"))
        for b in blocks_by_lesson.get(L["id"], []):
            n = len(b["content"]) if isinstance(b["content"], list) else 0
            if n < 4 and not (b["mode"] == "experiment" and n == 1):
                issues.append(("WARN", f"„{L['title_hu']}” / {b['mode']}: csak {n} kártya (<4)"))
    if not topic_quiz:
        issues.append(("FAIL", "Hiányzik a témazáró kvíz (scope=topic)."))

    if nat_entry:
        taught = []
        for L in lessons:
            for b in blocks_by_lesson.get(L["id"], []):
                if b["mode"] != "experiment":
                    taught.append(json.dumps(b["content"], ensure_ascii=False))
        text = _norm(" ".join(taught))

        # feladatok: per-Téma, but checked against the WHOLE topic's taught text (a fact
        # can legitimately be reinforced/covered from an adjacent Téma too).
        all_feladatok = [f for tm in nat_entry["temak"] for f in tm["feladatok"]]
        not_covered = await _feladatok_missing(c, all_feladatok, text)
        total = hit = 0
        for el in all_feladatok:
            total += 1
            if el in not_covered:
                issues.append(("FAIL", f"Feladat nincs lefedve: {el}"))
                missing.append({"cat": "feladatok", "element": el})
            else:
                hit += 1
        for el in nat_entry.get("fogalmak", []):
            total += 1
            if _covered(el, "fogalmak", text):
                hit += 1
            else:
                issues.append(("FAIL", f"Fogalom nincs lefedve: {el}"))
                missing.append({"cat": "fogalmak", "element": el})
        cov = f"{hit}/{total} = {round(100*hit/total) if total else 0}%"
    else:
        cov = "n/a (NAT témakör nem található a physics_nat2020_temak.json-ban)"
        issues.append(("WARN", "Nem található a NAT témakör — kötelező lefedettség nem auditálható."))
    return issues, cov, missing


# ---------- LLM checks ----------
FACT_SYS = ("Te tapasztalt magyar fizikatanár és tényellenőr vagy. KIZÁRÓLAG EGYÉRTELMŰ, TÁRGYI "
    "tévedéseket jelölsz: bizonyíthatóan rossz képlet, mértékegység, fizikai törvény, évszám vagy "
    "felfedező. NE jelöld: a megszokott tankönyvi egyszerűsítéseket, a fogalmazás/hangsúly kérdéseit, "
    "az értelmezést, vagy azt, hogy valami KIMARADT (a hiányt nem te ellenőrzöd). Inkább engedj el egy "
    "bizonytalan esetet, mint hogy téves riasztást adj. Minden találatnál adj `severity` mezőt: "
    "\"sulyos\" (valódi, érdemi tévedés) vagy \"csekely\" (apró pontatlanság). CSAK érvényes JSON-t adsz vissza.")

EXPERIMENT_SYS = ("Te tapasztalt magyar fizikatanár vagy, aki egy „Kísérlet és felfedezés” réteget bírál el. "
    "Ez a réteg NEM azt ellenőrzi, hogy a felfedezéstörténet MAGA igaz-e, hanem hogy VALÓBAN, KONKRÉTAN "
    "kapcsolódik-e EHHEZ a leckéhez, és hogy nem erőltetett/kitalált-e. Jelöld azokat a kártyákat, ahol: "
    "(a) a lecke túl elvont/matematikai ehhez (pl. csak mértékegység-átváltás), DE a kártya MÉGIS kitalált "
    "vagy erőltetett felfedezéstörténetet/kísérletet állít, ahelyett hogy ezt őszintén jelezné; vagy "
    "(b) a discovery/sketch/today mezők tárgyilag pontatlanok (rossz tudós, rossz évszám). "
    "FONTOS KIVÉTEL — NE jelöld hibásnak: ha a kártya üres discovery/sketch/today mezőkkel őszintén jelzi, "
    "hogy nincs jellegzetes felfedezéstörténet — ez a HELYES, kívánt viselkedés egy elvont leckénél. "
    "CSAK érvényes JSON-t adsz vissza.")

CONFIRM_SYS = ("Te vezető magyar fizikatanár vagy, aki egy tényellenőr jelöléseit BÍRÁLOD FELÜL. "
    "Egy 7–8. vagy 9–10. osztályos magyar fizika tananyagról van szó. CSAK érvényes JSON-t adsz vissza.")


def _is_honest_no_anchor_card(card):
    sketch = card.get("sketch")
    sketch_has_content = isinstance(sketch, dict) and bool(sketch.get("shapes"))
    text_fields_filled = any((card.get(f) or "").strip() for f in
                              ("discovery", "today", "try_basic", "try_advanced"))
    return not sketch_has_content and not text_fields_filled


async def _experiment_relevance_check(c, tema, other_blocks, exp_blocks):
    if not exp_blocks:
        return []
    all_cards = exp_blocks[0]["content"] or []
    judge_cards = [card for card in all_cards if not _is_honest_no_anchor_card(card)]
    if not judge_cards:
        return []
    context = json.dumps([{"mode": b["mode"], "content": b["content"]} for b in other_blocks], ensure_ascii=False)
    cards = json.dumps(judge_cards, ensure_ascii=False)
    out = await _ai_json(c, EXPERIMENT_SYS,
        f"Lecke: „{tema}”.\n\nA LECKE SAJÁT TARTALMA:\n{context}\n\n"
        f"A LECKE „KÍSÉRLET ÉS FELFEDEZÉS” KÁRTYÁI:\n{cards}\n\n"
        'Add vissza: {"issues":[{"heading":"az érintett kártya heading mezője","problem":"mi a gond",'
        '"suggestion":"mit kellene tenni"}]}\nHa minden kártya érdemi és pontos, üres issues tömb.',
        model=CHECK_MODEL)
    return out.get("issues", [])


async def _fact_check(c, tema, blocks):
    payload = json.dumps([{"mode": b["mode"], "content": b["content"]} for b in blocks], ensure_ascii=False)
    out = await _ai_json(c, FACT_SYS,
        f"Lecke: „{tema}”. Ellenőrizd a tárgyi pontosságot a fenti szigorú szabályok szerint. Add vissza:\n"
        '{"issues":[{"mode":"","severity":"sulyos|csekely","claim":"a hibás állítás röviden","why":"miért téves","fix":"helyes adat"}]}\n'
        f"Ha nincs egyértelmű tárgyi hiba, üres issues tömb.\n\nTANANYAG:\n{payload}", model=CHECK_MODEL)
    return out.get("issues", [])


async def _confirm_facts(c, issues):
    if not issues:
        return []
    cand = [{"i": n, "claim": x.get("claim", ""), "why": x.get("why", ""), "fix": x.get("fix", "")}
            for n, x in enumerate(issues)]
    out = await _ai_json(c, CONFIRM_SYS,
        "Az alábbi jelölt tárgyi hibákat egy tényellenőr jelölte. Döntsd el MINDEGYIKRŐL, hogy VALÓDI, "
        "érdemi tárgyi tévedés-e, amit javítani KELL, VAGY téves riasztás (fogalmazás, hangsúly, "
        "értelmezés, vagy hiány — ezek NEM hibák). Add vissza a MEGTARTANDÓ, valódi hibák indexeit:\n"
        '{"keep":[{"i":0,"severity":"sulyos|csekely"}]}\n\n'
        f"JELÖLTEK:\n{json.dumps(cand, ensure_ascii=False)}", maxtok=600, model=CHECK_MODEL)
    keep = {k["i"]: k.get("severity", "sulyos") for k in out.get("keep", [])}
    res = []
    for n, x in enumerate(issues):
        if n in keep:
            x["severity"] = keep[n]
            res.append(x)
    return res


async def _appro_check(c, tema, blocks, band):
    payload = json.dumps([{"mode": b["mode"], "content": b["content"]} for b in blocks], ensure_ascii=False)
    out = await _ai_json(c, APPRO_SYS,
        f"Lecke: „{tema}”. Célkorosztály (NAT évfolyam-sáv): {band}. Ellenőrizd a korosztályi "
        "megfelelést, a márkahangot, az idegen szavakat és a hangnemet. Add vissza:\n"
        '{"issues":[{"mode":"","kind":"korosztaly|markahang|idegen_szo|hangnem|tartalom","detail":"mi a gond","suggestion":"javaslat"}]}\n'
        f"Ha minden rendben, üres issues tömb.\n\nTANANYAG:\n{payload}", model=CHECK_MODEL)
    return out.get("issues", [])


GIVEN_NAMES = {
    "Anna", "András", "Antal", "Balázs", "Béla", "Dániel", "Dóra", "Erzsébet", "Eszter", "Éva",
    "Ferenc", "Gábor", "Gergely", "György", "Ilona", "Imre", "István", "János", "József", "Júlia",
    "Katalin", "Klára", "Lajos", "László", "Margit", "Mária", "Márton", "Mihály", "Miklós", "Pál",
    "Péter", "Rozália", "Sándor", "Tamás", "Teréz", "Zoltán", "Zsófia", "Zsuzsanna", "Erzsi", "Kata",
}


def _story_name_scan(by_lesson, lessons):
    """Flag invented Hungarian personal names in story blocks — real scientist names
    (Newton, Cavendish, ...) don't trip this since it only matches Hungarian given names."""
    issues = []
    for L in lessons:
        for b in by_lesson.get(L["id"], []):
            if b["mode"] != "story":
                continue
            low = json.dumps(b["content"], ensure_ascii=False).lower()
            found = sorted({n for n in GIVEN_NAMES if f" {n.lower()} " in f" {low} "})
            if found:
                issues.append({"tema": L["title_hu"], "mode": "story", "kind": "nev",
                               "detail": f"kitalált személynév(ek) a történetben: {', '.join(found)}",
                               "suggestion": "cseréld névtelen, általános szereplőre (pl. „egy biciklis”)"})
    return issues


# ---------- orchestrator ----------
async def _run(topic_nat):
    async with httpx.AsyncClient() as c:
        t = (await c.get(f"{SB}/rest/v1/curriculum_topics?nat_id=eq.{topic_nat}&select=id,title_hu,grade", headers=H_SB)).json()
        if not t:
            raise SystemExit(f"Topic {topic_nat} not found.")
        topic = t[0]; tid = topic["id"]; band = _band_label(topic.get("grade"))
        lessons = (await c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{tid}&select=id,nat_id,title_hu&order=order_index", headers=H_SB)).json()
        blocks = (await c.get(f"{SB}/rest/v1/content_blocks?topic_id=eq.{tid}&select=lesson_id,mode,scope,content", headers=H_SB)).json()
        by_lesson = {}
        topic_quiz = None
        for b in blocks:
            if b["scope"] == "topic":
                topic_quiz = b
            else:
                by_lesson.setdefault(b["lesson_id"], []).append(b)

        nat_entry = _load_nat_elements(topic["title_hu"], topic.get("grade"))
        comp_issues, cov, missing = await _completeness(c, lessons, by_lesson, topic_quiz, nat_entry)

        fact, appro, experiment = [], [], []
        active = [L for L in lessons if by_lesson.get(L["id"])]

        async def check_lesson(L):
            lb = by_lesson[L["id"]]
            non_exp = [b for b in lb if b["mode"] != "experiment"]
            exp_b = [b for b in lb if b["mode"] == "experiment"]
            return L["title_hu"], await asyncio.gather(
                _fact_check(c, L["title_hu"], lb), _appro_check(c, L["title_hu"], lb, band),
                _experiment_relevance_check(c, L["title_hu"], non_exp, exp_b))

        for title, (f, a, e) in await asyncio.gather(*(check_lesson(L) for L in active)):
            # defensive: an LLM check occasionally returns a malformed "issues" entry
            # (e.g. a bare string instead of an object) — skip rather than crash the run.
            for x in f:
                if isinstance(x, dict): x["tema"] = title; fact.append(x)
            for x in a:
                if isinstance(x, dict): x["tema"] = title; appro.append(x)
            for x in e:
                if isinstance(x, dict): x["tema"] = title; experiment.append(x)

        fact = await _confirm_facts(c, fact)
        appro += _story_name_scan(by_lesson, lessons)

        return {"topic": topic, "band": band, "coverage": cov, "missing": missing,
                "completeness": comp_issues, "fact": fact, "appropriateness": appro, "experiment": experiment}


def _verdict(rep):
    if any(i[0] == "FAIL" for i in rep["completeness"]):
        return "FAIL"
    if rep["fact"] or rep["appropriateness"] or rep["experiment"] or any(i[0] == "WARN" for i in rep["completeness"]):
        return "REVIEW"
    return "PASS"


def _report_md(rep):
    t = rep["topic"]
    L = [f"# Validáció — {t['title_hu']} ({t.get('nat_id', '')})",
         f"\n**Összesített eredmény: {_verdict(rep)}**  ·  NAT lefedettség: {rep['coverage']}  ·  korosztály: {rep['band']}\n", "---\n"]
    L.append("## 1. Teljesség (completeness)")
    if rep["completeness"]:
        for sev, msg in rep["completeness"]:
            L.append(f"- **{sev}** — {msg}")
    else:
        L.append("- ✅ Minden mód megvan, minden kötelező feladat/fogalom lefedve.")
    L.append("\n## 2. Tárgyi pontosság (fact check) — tanári felülvizsgálatra")
    if rep["fact"]:
        for i in rep["fact"]:
            sev = "súlyos" if i.get("severity", "sulyos") == "sulyos" else "csekély"
            L.append(f"- **FELÜLVIZSGÁLAT [{sev}]** — „{i.get('tema', '')}” / {i.get('mode', '')}: {i.get('claim', '')}")
            L.append(f"    - miért: {i.get('why', '')}  →  javasolt: {i.get('fix', '')}")
    else:
        L.append("- ✅ Nem talált tárgyi hibát.")
    L.append("\n## 3. Megfelelőség (appropriateness / márkahang) — tanári felülvizsgálatra")
    if rep["appropriateness"]:
        for i in rep["appropriateness"]:
            L.append(f"- **WARN** [{i.get('kind', '')}] — „{i.get('tema', '')}” / {i.get('mode', '')}: {i.get('detail', '')}")
            if i.get("suggestion"): L.append(f"    - javaslat: {i['suggestion']}")
    else:
        L.append("- ✅ Korosztályi megfelelés és márkahang rendben.")
    L.append("\n## 4. Kísérlet és felfedezés — relevancia — tanári felülvizsgálatra")
    if rep["experiment"]:
        for i in rep["experiment"]:
            L.append(f"- **FELÜLVIZSGÁLAT** — „{i.get('tema', '')}” / {i.get('heading', '')}: {i.get('problem', '')}")
            if i.get("suggestion"): L.append(f"    - javaslat: {i['suggestion']}")
    else:
        L.append("- ✅ A kísérlet-kártyák érdemi, konkrét kapcsolatban állnak a leckékkel.")
    return "\n".join(L)


def validate(topic_nat):
    rep = asyncio.run(_run(topic_nat))
    rep["topic"]["nat_id"] = topic_nat
    rep["verdict"] = _verdict(rep)
    return rep


if __name__ == "__main__":
    nat = sys.argv[1] if len(sys.argv) > 1 else "PHYS-78-01"
    quiet = "--quiet" in sys.argv
    rep = validate(nat)
    md = _report_md(rep)
    out = os.path.join(os.path.dirname(__file__), f"../exports/{nat}_validation.md")
    open(out, "w", encoding="utf-8").write(md)
    if not quiet or rep["verdict"] != "PASS":
        print(md)
    print(f"\n→ {rep['verdict']}  ·  report: {out}")
    sys.exit(0 if rep["verdict"] != "FAIL" else 1)
