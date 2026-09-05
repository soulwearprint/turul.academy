"""
Per-Témakör content guard rail. Runs three checks on a topic's content_blocks:

  1. COMPLETENESS  (deterministic) — every NAT-mandatory element is taught in the
     non-world lesson blocks, and every Téma has all expected modes + a topic quiz.
  2. FACT          (LLM)           — flags historical / factual inaccuracies.
  3. APPROPRIATENESS (LLM)         — grade-fit, brand voice (intelligent, friendly,
     encouraging, calm — NOT nationalistic / corporate / childish), Hungarian-only.

Usage:
    python validate_temakor.py HIST-78-VH1            # validate + write report
    python validate_temakor.py HIST-78-VH1 --quiet    # report only on issues
Exit code: 0 = PASS (no FAIL-level issues), 1 = FAIL.

Importable: `from validate_temakor import validate; report = validate("HIST-78-VH1")`
"""
import os, re, json, sys, asyncio, httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
RK = os.getenv("OPENROUTER_API_KEY")
# Validation runs only a few calls per topic, so it uses a STRONGER model than bulk
# generation (gpt-4o-mini) for higher-precision fact/appropriateness judging.
CHECK_MODEL = "openai/gpt-4o"
OR = "https://openrouter.ai/api/v1/chat/completions"
H_OR = {"Authorization": f"Bearer {RK}", "Content-Type": "application/json",
        "HTTP-Referer": "https://turul.academy", "X-Title": "Turul"}
H_SB = {"apikey": SVC, "Authorization": f"Bearer {SVC}"}
NAT_JSON = os.path.join(os.path.dirname(__file__), "../nat_curriculum/history_nat2020.json")
EXPECTED_MODES = ["text", "story", "visual", "quiz", "world"]

# grade band per general-iskola / gimnázium for appropriateness framing
def _band_label(grade):
    g = grade or 0
    return {5: "5–6", 6: "5–6", 7: "7–8", 8: "7–8",
            9: "9–10", 10: "9–10", 11: "11–12", 12: "11–12"}.get(g, "7–8")


# ---------- NAT mandatory elements (generic lookup by topic title) ----------
def _load_nat_elements(title_hu):
    d = json.load(open(NAT_JSON, encoding="utf-8"))
    best = None
    for school in ("altalanos_iskola", "gimnazium"):
        for band, arr in d[school].items():
            for t in arr:
                if t["temakor"].strip().lower() == title_hu.strip().lower():
                    return t, band
                if best is None and title_hu.strip().lower() in t["temakor"].strip().lower():
                    best = (t, band)
    return best if best else (None, None)


_QUOTES = {0x201e, 0x201c, 0x201d, 0x2018, 0x2019, 0x201a, 0x201b, 0x60, 0x22, 0x27}

def _norm(s):
    """Lowercase and strip typographic/ascii quotes so matching is robust."""
    s = "".join("" if ord(ch) in _QUOTES else ch for ch in s)
    return " ".join(s.lower().split())


import unicodedata

def _fold(s):
    """Drop combining marks so edge diacritics match (e.g. 'ȩ' vs 'ę' → 'e')."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def _covered(element, category, text):
    """True if this mandatory element is taught in `text` (already _norm'd).
    Handles: parentheticals (stripped), '/' = alternatives (any), ' és '/',' = conjunction (all),
    diacritic edge cases (folded fallback), chronology keyed on its date or concept."""
    text_f = _fold(text)
    raw = _norm(element)

    def has(p):
        return bool(p) and (p in text or _fold(p) in text_f)

    def variants(s):
        """A parenthetical is an alternate/optional name form ('I. (Szent) István'):
        try without it, with it inline, and the paren-content + trailing tokens."""
        m = re.search(r"\(([^)]*)\)", s)
        if not m:
            return [" ".join(s.split())]
        before, paren, after = s[:m.start()], m.group(1), s[m.end():]
        return [" ".join((before + after).split()),
                " ".join((before + paren + after).split()),
                " ".join((paren + after).split())]

    def all_tokens(s):
        """Fallback: every significant word (len>3) of the element appears somewhere.
        Handles concatenated/reordered entries ('Recsk Hortobágy', 'választás Magyarországon')."""
        toks = [t for t in re.split(r"[^0-9a-záéíóöőúüű]+", _fold(s)) if len(t) > 3]
        return bool(toks) and all(t in text_f for t in toks)

    for alt in re.split(r"\s*/\s*", raw):            # slash = alternatives → any covers it
        alt = alt.strip()
        if not alt:
            continue
        if category == "kronologia":
            nums = re.findall(r"\d{1,4}", alt)
            if any(n in text for n in nums):         # any date in the entry/range appears
                return True
            desc = re.sub(r"\([^)]*\)", " ", alt)
            for w in ("kr. e.", "kr. u.", "körül", "–", "-"):
                desc = desc.replace(w, " ")
            desc = " ".join(re.sub(r"\d+", " ", desc).split())   # strip date noise → concept
            if has(desc) or all_tokens(desc):
                return True
            continue
        if "(" in alt and any(has(v) for v in variants(alt)):    # parenthetical name forms
            return True
        parts = [p.strip() for p in re.split(r" és |,", alt) if p.strip()]   # conjunction → all
        if parts and all(has(p) for p in parts):
            return True
        if all_tokens(re.sub(r"\([^)]*\)", " ", alt)):           # token-subset fallback
            return True
    return False


# ---------- check 1: completeness (deterministic) ----------
def _completeness(topic, lessons, blocks_by_lesson, topic_quiz, nat_elem):
    issues = []
    missing = []  # structured list of {cat, element} for the auto-fixer
    # structural: modes present per Téma
    for L in lessons:
        present = {b["mode"] for b in blocks_by_lesson.get(L["id"], [])}
        for m in EXPECTED_MODES:
            if m not in present:
                issues.append(("FAIL", f"„{L['title_hu']}”: hiányzó mód: {m}"))
        for b in blocks_by_lesson.get(L["id"], []):
            n = len(b["content"]) if isinstance(b["content"], list) else 0
            # world mode: a single honest "no genuine parallel" card is a valid, expected
            # outcome for lessons with no real temporal anchor — not a completeness gap.
            if n < 4 and not (b["mode"] == "world" and n == 1):
                issues.append(("WARN", f"„{L['title_hu']}” / {b['mode']}: csak {n} kártya (<4)"))
    if not topic_quiz:
        issues.append(("FAIL", "Hiányzik a témazáró kvíz (scope=topic)."))

    # mandatory NAT coverage across non-world lesson blocks
    if nat_elem:
        taught = []
        for L in lessons:
            for b in blocks_by_lesson.get(L["id"], []):
                if b["mode"] != "world":
                    taught.append(json.dumps(b["content"], ensure_ascii=False))
        text = _norm(" ".join(taught))
        total = hit = 0
        for cat in ("fogalmak", "szemelyek", "kronologia", "topografia"):
            for el in nat_elem.get(cat, []):
                total += 1
                if _covered(el, cat, text):
                    hit += 1
                else:
                    issues.append(("FAIL", f"NAT elem nincs lefedve ({cat}): {el}"))
                    missing.append({"cat": cat, "element": el})
        cov = f"{hit}/{total} = {round(100*hit/total) if total else 0}%"
    else:
        cov = "n/a (NAT témakör nem található a JSON-ban)"
        issues.append(("WARN", "Nem található a NAT témakör a history_nat2020.json-ban — kötelező lefedettség nem auditálható."))
    return issues, cov, missing


# ---------- LLM checks ----------
async def _ai_json(c, sys, user, maxtok=1500, model=CHECK_MODEL):
    r = await c.post(OR, headers=H_OR, json={"model": model, "max_tokens": maxtok,
        "temperature": 0, "messages": [{"role": "system", "content": sys},
        {"role": "user", "content": user}]}, timeout=120)
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.splitlines()[1:-1])
    try:
        return json.loads(raw)
    except Exception:
        return {"issues": [], "_parse_error": raw[:300]}

FACT_SYS = ("Te tapasztalt magyar történelemtanár és tényellenőr vagy. KIZÁRÓLAG EGYÉRTELMŰ, TÁRGYI "
    "tévedéseket jelölsz: bizonyíthatóan rossz évszám, hely, személy, vagy a tényekkel ellentétes ok-okozat / "
    "anakronizmus / összekevert fogalom. "
    "NE jelöld: a megszokott tankönyvi egyszerűsítéseket (pl. „kétharmad” a kb. 72% területvesztésre), "
    "a fogalmazás/hangsúly kérdéseit, az értelmezést, vagy azt, hogy valami KIMARADT (a hiányt nem te ellenőrzöd). "
    "Inkább engedj el egy bizonytalan esetet, mint hogy téves riasztást adj. "
    "Minden találatnál adj `severity` mezőt: \"sulyos\" (valódi, érdemi tévedés) vagy \"csekely\" (apró pontatlanság). "
    "CSAK érvényes JSON-t adsz vissza.")

APPRO_SYS = ("Te a Turul Academy tartalmi lektora vagy. A márkahang: intelligens, barátságos, bátorító, "
    "nyugodt. KERÜLENDŐ: nacionalista/uszító hangnem, vállalati közhely, gyerekes/lekezelő stílus, "
    "idegen (nem magyar) szavak, korosztálynak nem megfelelő tartalom. CSAK érvényes JSON-t adsz vissza.")

WORLD_SYS = ("Te tapasztalt magyar történelemtanár vagy, aki egy „Világ ekkor” (globális párhuzam) réteget "
    "bírál el. Ez a réteg NEM azt ellenőrzi, hogy a globális esemény MAGA igaz-e, hanem hogy VALÓBAN, "
    "KONKRÉTAN kapcsolódik-e EHHEZ a leckéhez — nem csak egy általános korszakhoz vagy általános "
    "„nemzeti mozgalom”/„modernizáció” hívószóhoz. Jelöld azokat a kártyákat, ahol: (a) a globális esemény "
    "időben/tartalmilag nincs érdemi, konkrét kapcsolatban a lecke tárgyával, csak egy laza, sablonos "
    "asszociáció (pl. „mindkettő a nemzeti öntudatot erősítette”); vagy (b) a lecke egyáltalán nem egy "
    "konkrét történelmi eseményhez/időponthoz kötött (pl. fogalmakat, készségeket vagy általános "
    "áttekintést tanít), ÉS a kártya MÉGIS konkrét, kitalált egyidejű világeseményt/ok-okozatot állít párhuzamba, "
    "ahelyett hogy ezt őszintén jelezné. "
    "FONTOS KIVÉTEL — NE jelöld hibásnak: ha a lecke nincs konkrét eseményhez kötve, és a kártya EZT ŐSZINTÉN "
    "elismeri (üres/hiányzó `year` és `link_hu` mező, vagy a szöveg kimondja, hogy nincs egyértelmű globális "
    "párhuzam, csak általános kulturális összevetést tesz konkrét ok-okozat kitalálása nélkül) — ez a HELYES, "
    "kívánt viselkedés egy horgony nélküli leckénél, nem hiba. "
    "CSAK érvényes JSON-t adsz vissza.")

def _is_honest_no_anchor_card(card):
    """A card with no year/link_hu is the deliberate 'no genuine global parallel' output
    (see generate_temakor.py's world prompt) — always compliant, never sent to the LLM judge."""
    return not (card.get("year") or "").strip() and not (card.get("link_hu") or "").strip()


async def _world_relevance_check(c, tema, other_blocks, world_blocks):
    if not world_blocks:
        return []
    all_cards = world_blocks[0]["content"] or []
    judge_cards = [card for card in all_cards if not _is_honest_no_anchor_card(card)]
    if not judge_cards:
        return []  # every card is an honest no-anchor disclaimer — nothing to judge
    context = json.dumps([{"mode": b["mode"], "content": b["content"]} for b in other_blocks], ensure_ascii=False)
    cards = json.dumps(judge_cards, ensure_ascii=False)
    out = await _ai_json(c, WORLD_SYS,
        f"Lecke: „{tema}”.\n\nA LECKE SAJÁT TARTALMA (ez adja meg, miről is szól valójában):\n{context}\n\n"
        f"A LECKE „VILÁG EKKOR” KÁRTYÁI (ezt kell elbírálnod):\n{cards}\n\n"
        "Add vissza:\n"
        '{"issues":[{"heading":"az érintett kártya heading mezője, vagy \\"(egész réteg)\\" ha a lecke '
        'egyáltalán nem eseményhez kötött","problem":"miért nincs érdemi/konkrét kapcsolat","suggestion":"mit '
        'kellene tenni (pl. törölni, vagy \\"nincs egyértelmű globális párhuzam\\" jellegű őszinte kártyára cserélni)"}]}\n'
        "Ha minden kártya érdemi, konkrét kapcsolatban áll a lecke tárgyával, üres issues tömb.")
    return out.get("issues", [])

async def _fact_check(c, tema, blocks):
    payload = json.dumps([{"mode": b["mode"], "content": b["content"]} for b in blocks], ensure_ascii=False)
    out = await _ai_json(c, FACT_SYS,
        f"Lecke: „{tema}”. Ellenőrizd a tárgyi pontosságot a fenti szigorú szabályok szerint. Add vissza:\n"
        '{"issues":[{"mode":"","severity":"sulyos|csekely","claim":"a hibás állítás röviden","why":"miért téves","fix":"helyes adat"}]}\n'
        f"Ha nincs egyértelmű tárgyi hiba, üres issues tömb.\n\nTANANYAG:\n{payload}")
    return out.get("issues", [])

CONFIRM_SYS = ("Te vezető magyar történész vagy, aki egy tényellenőr jelöléseit BÍRÁLOD FELÜL. "
    "Egy 7–8. vagy 9–12. osztályos magyar történelem tananyagról van szó. CSAK érvényes JSON-t adsz vissza.")

async def _confirm_facts(c, issues):
    """Second pass: keep only genuine, fixable factual errors; drop false alarms."""
    if not issues:
        return []
    cand = [{"i": n, "claim": x.get("claim", ""), "why": x.get("why", ""), "fix": x.get("fix", "")}
            for n, x in enumerate(issues)]
    out = await _ai_json(c, CONFIRM_SYS,
        "Az alábbi jelölt tárgyi hibákat egy tényellenőr jelölte. Döntsd el MINDEGYIKRŐL, hogy "
        "VALÓDI, érdemi tárgyi tévedés-e, amit javítani KELL, VAGY téves riasztás "
        "(megszokott tankönyvi egyszerűsítés mint „kétharmad” ~72%-ra, fogalmazás, hangsúly, értelmezés, "
        "vagy hiány — ezek NEM hibák). Add vissza a MEGTARTANDÓ, valódi hibák indexeit:\n"
        '{"keep":[{"i":0,"severity":"sulyos|csekely"}]}\n\n'
        f"JELÖLTEK:\n{json.dumps(cand, ensure_ascii=False)}", maxtok=600)
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
        f"Ha minden rendben, üres issues tömb.\n\nTANANYAG:\n{payload}")
    return out.get("issues", [])


# Deterministic story-mode invented-name check (LLM judges parroted prompt examples → false positives).
# Common Hungarian given names; flagged only in story mode and only if not part of an allowed NAT figure.
GIVEN_NAMES = {
    "Anna", "András", "Antal", "Balázs", "Béla", "Dániel", "Dóra", "Erzsébet", "Eszter", "Éva",
    "Ferenc", "Gábor", "Gergely", "György", "Ilona", "Imre", "István", "János", "József", "Júlia",
    "Katalin", "Klára", "Lajos", "László", "Margit", "Mária", "Márton", "Mihály", "Miklós", "Pál",
    "Péter", "Rozália", "Sándor", "Tamás", "Teréz", "Zoltán", "Zsófia", "Zsuzsanna", "Erzsi", "Kata",
}

def _story_name_scan(by_lesson, lessons, allowed_names):
    """Flag invented personal names in story blocks (allowed NAT figures excluded)."""
    issues = []
    allowed_low = [a.lower() for a in (allowed_names or [])]
    for L in lessons:
        for b in by_lesson.get(L["id"], []):
            if b["mode"] != "story":
                continue
            text = json.dumps(b["content"], ensure_ascii=False)
            low = text.lower()
            for full in allowed_low:       # strip allowed full names so their parts don't trip
                low = low.replace(full, " ")
            found = sorted({n for n in GIVEN_NAMES if re.search(r"\b" + n.lower() + r"\b", low)})
            if found:
                issues.append({"tema": L["title_hu"], "mode": "story", "kind": "nev",
                               "detail": f"kitalált személynév(ek) a történetben: {', '.join(found)}",
                               "suggestion": "cseréld névtelen, általános szereplőre (pl. „egy falusi asszony”)"})
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

        nat_elem, nat_band = _load_nat_elements(topic["title_hu"])
        comp_issues, cov, missing = _completeness(topic, lessons, by_lesson, topic_quiz, nat_elem)
        allowed_names = (nat_elem or {}).get("szemelyek", [])

        fact, appro, world = [], [], []
        active = [L for L in lessons if by_lesson.get(L["id"])]

        async def check_lesson(L):
            lb = by_lesson[L["id"]]
            non_world = [b for b in lb if b["mode"] != "world"]
            world_b = [b for b in lb if b["mode"] == "world"]
            return L["title_hu"], await asyncio.gather(
                _fact_check(c, L["title_hu"], lb), _appro_check(c, L["title_hu"], lb, band),
                _world_relevance_check(c, L["title_hu"], non_world, world_b))

        for title, (f, a, w) in await asyncio.gather(*(check_lesson(L) for L in active)):
            # defensive: an LLM check occasionally returns a malformed "issues" entry
            # (e.g. a bare string instead of an object) — skip rather than crash the run.
            for x in f:
                if isinstance(x, dict): x["tema"] = title; fact.append(x)
            for x in a:
                if isinstance(x, dict): x["tema"] = title; appro.append(x)
            for x in w:
                if isinstance(x, dict): x["tema"] = title; world.append(x)

        fact = await _confirm_facts(c, fact)  # precision pass: drop false alarms
        appro += _story_name_scan(by_lesson, lessons, allowed_names)  # deterministic name integrity

        return {"topic": topic, "band": band, "coverage": cov, "missing": missing,
                "completeness": comp_issues, "fact": fact, "appropriateness": appro, "world": world}


def _verdict(rep):
    # Only completeness is a hard gate (deterministic). Fact + appropriateness are
    # ADVISORY: they surface a review list for the human teacher, never auto-block.
    if any(i[0] == "FAIL" for i in rep["completeness"]):
        return "FAIL"
    if rep["fact"] or rep["appropriateness"] or rep["world"] or any(i[0] == "WARN" for i in rep["completeness"]):
        return "REVIEW"
    return "PASS"


def _report_md(rep):
    t = rep["topic"]
    L = [f"# Validáció — {t['title_hu']} ({t['nat_id'] if 'nat_id' in t else ''})",
         f"\n**Összesített eredmény: {_verdict(rep)}**  ·  NAT lefedettség: {rep['coverage']}  ·  korosztály: {rep['band']}\n", "---\n"]
    L.append("## 1. Teljesség (completeness)")
    if rep["completeness"]:
        for sev, msg in rep["completeness"]:
            L.append(f"- **{sev}** — {msg}")
    else:
        L.append("- ✅ Minden mód megvan, minden kötelező NAT-elem lefedve.")
    L.append("\n## 2. Tárgyi pontosság (fact check) — tanári felülvizsgálatra")
    if rep["fact"]:
        for i in rep["fact"]:
            sev = "súlyos" if i.get("severity", "sulyos") == "sulyos" else "csekély"
            L.append(f"- **FELÜLVIZSGÁLAT [{sev}]** — „{i.get('tema','')}” / {i.get('mode','')}: {i.get('claim','')}")
            L.append(f"    - miért: {i.get('why','')}  →  javasolt: {i.get('fix','')}")
    else:
        L.append("- ✅ Nem talált tárgyi hibát.")
    L.append("\n## 3. Megfelelőség (appropriateness / márkahang) — tanári felülvizsgálatra")
    if rep["appropriateness"]:
        for i in rep["appropriateness"]:
            L.append(f"- **WARN** [{i.get('kind','')}] — „{i.get('tema','')}” / {i.get('mode','')}: {i.get('detail','')}")
            if i.get("suggestion"): L.append(f"    - javaslat: {i['suggestion']}")
    else:
        L.append("- ✅ Korosztályi megfelelés és márkahang rendben.")
    L.append("\n## 4. Világ ekkor — relevancia — tanári felülvizsgálatra")
    if rep["world"]:
        for i in rep["world"]:
            L.append(f"- **FELÜLVIZSGÁLAT** — „{i.get('tema','')}” / {i.get('heading','')}: {i.get('problem','')}")
            if i.get("suggestion"): L.append(f"    - javaslat: {i['suggestion']}")
    else:
        L.append("- ✅ A világ ekkor kártyák érdemi, konkrét kapcsolatban állnak a leckékkel.")
    return "\n".join(L)


def validate(topic_nat):
    rep = asyncio.run(_run(topic_nat))
    rep["topic"]["nat_id"] = topic_nat
    rep["verdict"] = _verdict(rep)
    return rep


if __name__ == "__main__":
    nat = sys.argv[1] if len(sys.argv) > 1 else "HIST-78-VH1"
    quiet = "--quiet" in sys.argv
    rep = validate(nat)
    md = _report_md(rep)
    out = os.path.join(os.path.dirname(__file__), f"../exports/{nat}_validation.md")
    open(out, "w", encoding="utf-8").write(md)
    if not quiet or rep["verdict"] != "PASS":
        print(md)
    print(f"\n→ {rep['verdict']}  ·  report: {out}")
    sys.exit(0 if rep["verdict"] != "FAIL" else 1)
