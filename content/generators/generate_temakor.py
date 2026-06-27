"""
Témakör generator (NAT 3-tier model) — generalized for ANY History Témakör.

For one Témakör (Topic) it generates, per Téma (Lesson), the 4 modes + a
"Világ ekkor" global layer, plus an end-of-topic comprehensive quiz. Content is
driven by the official NAT mandatory elements, Hungary-centered. Level = alap.

Témák + Altémák come from content/nat_curriculum/history_nat2020_temak.json
(parsed from the docx by parse_nat_temak.py). The Témakör's mandatory elements
are distributed across its Témák by an LLM pass (replaces the old hardcoded DIST).

Usage:
    python generate_temakor.py --nat-id HIST-78-VH1     # one topic
    python generate_temakor.py --nat-id HIST-78-VH1 --no-validate
"""
import os, json, asyncio, argparse, httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
RK = os.getenv("OPENROUTER_API_KEY")
MODEL = "openai/gpt-4o-mini"            # bulk generation (cheap)
DIST_MODEL = "openai/gpt-4o"           # element distribution (precision matters)
OR = "https://openrouter.ai/api/v1/chat/completions"
H_OR = {"Authorization": f"Bearer {RK}", "Content-Type": "application/json",
        "HTTP-Referer": "https://turul.academy", "X-Title": "Turul"}
H_SB = {"apikey": SVC, "Authorization": f"Bearer {SVC}", "Content-Type": "application/json"}
TEMAK_MAP = os.path.join(os.path.dirname(__file__), "../nat_curriculum/history_nat2020_temak.json")

SYS = ("Te egy tapasztalt magyar történelemtanár és tananyagfejlesztő vagy. A magyar nemzet és "
       "Magyarország története áll a középpontban; az egyetemes történelmet ehhez kapcsolva, magyar "
       "nézőpontból mutatod be (NAT 2020). Minden szöveg KIZÁRÓLAG magyar nyelven, idegen szavak nélkül, "
       "tényszerűen pontos. CSAK érvényes JSON-t adsz vissza.")

CATS = ("fogalmak", "szemelyek", "kronologia", "topografia")


def school_of_grade(grade):
    return "F" if (grade or 0) <= 8 else "K"


def lookup_temakor(title_hu, grade):
    """Find the parsed Témakör entry for a DB topic (by school + title)."""
    m = json.load(open(TEMAK_MAP, encoding="utf-8"))
    sc = school_of_grade(grade)
    key = f"{sc}::{title_hu.strip()}"
    if key in m:
        return m[key]
    # fallback: unique title match ignoring school
    cands = [v for v in m.values() if v["title"].strip().lower() == title_hu.strip().lower()]
    return cands[0] if cands else None


async def distribute_elements(c, temakor, temak, elements):
    """LLM assigns each mandatory element to the Téma(s) it best fits.
    Returns {tema_title: {fogalmak,szemelyek,kronologia,topografia}} covering ALL elements."""
    temak_desc = "\n".join(f'- „{t["title"]}” (altémák: {"; ".join(t["altemak"]) or "—"})' for t in temak)
    el_desc = elem_block(elements)
    out = await ai(c,
        f"Témakör: „{temakor}”.\nA témakör Témái (leckéi):\n{temak_desc}\n\n"
        f"A témakör kötelező NAT-elemei:\n{el_desc}\n\n"
        "Oszd szét MINDEN kötelező elemet a Témák között: minden elem ahhoz a Témához kerüljön, "
        "amelyikbe történelmileg/tematikailag a legjobban illik. MINDEN elemet pontosan egy Témához rendelj, "
        "és EGYETLEN elem se maradjon ki. CSAK a megadott Téma-címeket használd kulcsként.\n"
        'JSON: {"<Téma cím>": {"fogalmak":[],"szemelyek":[],"kronologia":[],"topografia":[]}}',
        temp=0, maxtok=2000, sys="Magyar történelem tananyagfejlesztő vagy. Csak JSON-t adsz vissza.",
        model=DIST_MODEL)
    # ensure completeness: any unassigned element -> first Téma
    assigned = {cat: set() for cat in CATS}
    for v in out.values():
        for cat in CATS:
            assigned[cat].update(v.get(cat, []) or [])
    first = temak[0]["title"]
    out.setdefault(first, {cat: [] for cat in CATS})
    for cat in CATS:
        for el in elements.get(cat, []):
            if el not in assigned[cat]:
                out[first].setdefault(cat, []).append(el)
    return out


def elem_block(d):
    def fmt(k, label): return f"{label}: {', '.join(d[k])}" if d[k] else ""
    return "\n".join(x for x in [fmt('fogalmak','Fogalmak'), fmt('szemelyek','Személyek'),
                                 fmt('kronologia','Kronológia'), fmt('topografia','Topográfia')] if x)

async def ai(c, prompt, temp=0.55, maxtok=3200, sys=SYS, model=MODEL):
    r = await c.post(OR, headers=H_OR, json={"model":model,"max_tokens":maxtok,"temperature":temp,
        "messages":[{"role":"system","content":sys},{"role":"user","content":prompt}]}, timeout=120)
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"): raw = "\n".join(raw.splitlines()[1:-1])
    return json.loads(raw)

async def proof(c, obj):
    try:
        return await ai(c, "Javítsd ki az alábbi JSON szöveges mezőiben a helyesírási, nyelvtani és "
            "központozási hibákat. NE változtasd a tartalmat, szerkezetet vagy kulcsokat. CSAK a javított JSON-t add vissza.\n\n"
            + json.dumps(obj, ensure_ascii=False), temp=0, sys="Gondos magyar korrektor vagy. Csak JSON-t adsz vissza.")
    except Exception:
        return obj

def prompt(mode, temakor, tema, altemak, eb):
    head = (f"Témakör: „{temakor}”\nLecke (Téma): „{tema}”\nAltémák: {altemak}\n\n"
            f"A leckének NÉV SZERINT le KELL fednie és kontextusban el kell magyaráznia az alábbi kötelező NAT-elemeket "
            f"(ki/mi/mikor/hol és miért fontos a magyar történelem szempontjából):\n{eb}\n")
    if mode == "text":
        return head + ('\nKészíts strukturált SZÖVEGES leckét magyar-központú nézőpontból. Annyi kártya, amennyi a fenti '
            'elemek értelmes lefedéséhez kell (kb. 5-8). Minden kötelező elem jelenjen meg legalább egy kártyában. '
            '4-6 tartalmas, tényszerű mondat kártyánként.\nJSON: {"title":"","cards":[{"type":"text","heading":"","body":"","key_term":""}]}')
    if mode == "story":
        return head + ('\nKészíts TÖRTÉNET-leckét HÉTKÖZNAPI, ALULNÉZETI perspektívából, HARMADIK SZEMÉLYBEN (ne én-elbeszélés). '
            'FONTOS: NE a politikát, a diplomáciát vagy a hadi ok-okozati láncot meséld el — az a szöveges réteg dolga, és itt '
            'KERÜLENDŐ az ismétlése. Ehelyett azt mutasd be, MILYEN VOLT és MIT JELENTETT a kor hétköznapja a korabeli egyszerű '
            'magyar emberek számára. '
            'LÉNYEG: minden kártya az élet EGY MÁS TERÜLETÉT mutassa be — NE ugyanazt a jelenetet meséld el több szereplő '
            'szemszögéből, hanem a mindennapi élet KÜLÖNBÖZŐ ÁGAIT járd körül. Példák a lefedhető, EGYMÁSTÓL ELTÉRŐ '
            'életterületekre (a KORSZAKHOZ igazítva válassz, ne ismételd): a munka és megélhetés mindennapjai (földművelés, '
            'mesterség, kereskedelem vagy gyári munka — a kor szerint); a család, az otthon és a táplálkozás; a hatalom, a '
            'hivatalok és a helyi közösség viszonya; a hit, az ünnepek és a szokások; a gyermekek, a nevelés és az iskola; a '
            'betegség, a járvány és a gyógyítás; válság vagy háború hatása a hétköznapokra, ha a téma ezt indokolja. '
            'KRITIKUS SZABÁLY: SOHA ne adj NEVET egyetlen szereplőnek sem — sem kitalált, sem valós keresztnevet vagy '
            'teljes nevet (TILOS pl. „Mária”, „János és László”, „Kovács úr”). A szereplők MINDIG névtelenek és általánosak, '
            'foglalkozással/szereppel megnevezve (pl. „egy falusi asszony”, „a kézművesek”, „a gyermekek”, „egy katona”). '
            'Egyetlen kivétel: a kötelező NAT-elemként megadott valós történelmi személyek (lásd fent) — őket néven nevezheted, '
            'de őket se tedd kitalált jelenet szereplőjévé. Érzékletes, anyagi és érzelmi valóság. '
            'Ahol természetes, kösd a kötelező fogalmakat az ÁTÉLT valóságukhoz. 5-8 kártya, mindegyik MÁS életterületről.\n'
            'JSON: {"title":"","cards":[{"type":"story","heading":"","body":"","mood":"melyik életterületet mutatja be (pl. front, hátország, gazdaság)"}]}')
    if mode == "visual":
        return head + ('\nKészíts VIZUÁLIS leckét: minden fő elemhez egy szemléltető elem (idővonal/térkép/diagram/arckép) leírása, '
            'amely a kötelező adatokat (évszámok, helyszínek, személyek) mutatja. 5-8 kártya.\n'
            'JSON: {"title":"","cards":[{"type":"visual","heading":"","visual_type":"","description":"","caption":""}]}')
    if mode == "quiz":
        return head + ('\nKészíts 5 kérdéses KVÍZT, amely KIZÁRÓLAG a fenti kötelező elemeket kéri számon. Minden kérdéshez rövid magyarázat.\n'
            'JSON: {"title":"","cards":[{"type":"quiz","question_type":"multiple_choice","question":"","options":["A) ","B) ","C) ","D) "],"correct":"A","explanation":""}]}')
    if mode == "world":
        return (f"Lecke: „{tema}” (Témakör: „{temakor}”).\n\nKészíts egy „VILÁG EKKOR” réteget: mi zajlott EKKOR a "
            "nagyvilágban, miközben a fenti magyar/európai események történtek? Párhuzamos globális események, szereplők, okok. "
            "Kártyánként 3-4 TARTALMAS, tényszerűen pontos mondat a globális eseményről (ne csak egy odavetett mondat). "
            "A `year` mezőbe MINDIG az ADOTT esemény saját évszáma kerüljön (pl. „1917”), NE a témakör teljes időtartama. "
            "MINDEN kártyához adj egy KONKRÉT, OK-OKOZATI visszacsatolást a lecke magyar témájához (link_hu mező): nevezz meg egy "
            "konkrét következményt vagy mechanizmust, amely a globális eseménytől EZEN LECKE magyar tárgyáig vezet — valódi okozati "
            "vagy összefüggés-láncot. "
            "Ha hatásról írsz, MINDIG mondd meg, MI volt az a konkrét hatás — ne állj meg ott, hogy „jelentős hatással volt” vagy "
            "„befolyásolta a helyzetet”, hanem nevezd meg a konkrét következményt vagy mechanizmust (mi, hol, hogyan). "
            "Felső szintű tények kellenek, nem mély elbeszélés. "
            "TILOS az általános, sablonos megfogalmazás (pl. „alapvetően formálta Magyarország jövőjét”, „közvetlenül érintett volt”, "
            "„meghatározta a helyzetét”). "
            "Ügyelj a tárgyi pontosságra (helyes évszámok, békeszerződések, személyek — ne keverd össze őket). "
            "Ez kiegészítő, érdeklődő tanulóknak szóló réteg, nem kötelező tananyag. 4-6 kártya.\n"
            'JSON: {"title":"Világ ekkor","cards":[{"type":"world","year":"az adott esemény saját évszáma","heading":"","body":"","link_hu":"konkrét ok-okozati kapcsolat e lecke magyar anyagához"}]}')

async def ensure_lessons(c, topic_id, topic_nat, temak):
    """Idempotently create curriculum_lessons (Témák) from the parsed map, matched by title."""
    existing = (await c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{topic_id}&select=id,nat_id,title_hu&order=order_index", headers=H_SB)).json()
    have = {L["title_hu"].strip() for L in existing}
    for i, tm in enumerate(temak, start=1):
        if tm["title"].strip() in have:
            continue
        payload = {"topic_id": topic_id, "nat_id": f"{topic_nat}-T{i}", "title": tm["title"],
                   "title_hu": tm["title"], "order_index": i, "is_active": False}
        await c.post(f"{SB}/rest/v1/curriculum_lessons", headers={**H_SB, "Prefer": "return=minimal"}, json=payload)
    return (await c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{topic_id}&select=id,nat_id,title_hu&order=order_index", headers=H_SB)).json()


ALL_MODES = ["text", "story", "visual", "quiz", "world"]
FIX_SYS = "Gondos magyar történelem-szerkesztő vagy. CSAK a javított JSON kártyatömböt adod vissza, azonos szerkezettel."


async def apply_fixes(c, lessons, allowed_names, rep):
    """Auto-fix the machine-correctable issues the guard rail found:
    invented names in story (targeted rewrite) + súlyos fact errors (targeted correction).
    Returns the number of blocks patched."""
    by_title = {L["title_hu"].strip(): L for L in lessons}
    allow = ", ".join(allowed_names or []) or "(egy sem)"
    fixes = 0

    async def get_block(lesson_id, mode):
        r = (await c.get(f"{SB}/rest/v1/content_blocks?lesson_id=eq.{lesson_id}&mode=eq.{mode}&select=id,content", headers=H_SB)).json()
        return r[0] if r else None

    async def patch(bid, obj):
        cards = obj.get("cards", obj) if isinstance(obj, dict) else obj
        await c.patch(f"{SB}/rest/v1/content_blocks?id=eq.{bid}", headers={**H_SB, "Prefer": "return=minimal"}, json={"content": cards})

    # 1) invented names in story → rewrite to anonymous subjects
    for iss in rep.get("appropriateness", []):
        if iss.get("kind") != "nev":
            continue
        L = by_title.get((iss.get("tema") or "").strip())
        blk = await get_block(L["id"], "story") if L else None
        if not blk:
            continue
        try:
            new = await ai(c, "Írd át az alábbi TÖRTÉNET-kártyákat úgy, hogy MINDEN kitalált személynevet általános, "
                "névtelen szereplőre cserélsz (pl. „egy falusi asszony”, „a gyermekek”, „egy katona”). A KÖTELEZŐ valós "
                f"történelmi személyek neve maradhat: {allow}. A tartalmat, a sorrendet és a JSON-szerkezetet tartsd meg, "
                "csak a neveket cseréld.\n\nKÁRTYÁK:\n" + json.dumps(blk["content"], ensure_ascii=False),
                temp=0, model=DIST_MODEL, sys=FIX_SYS)
            await patch(blk["id"], new); fixes += 1
            print(f"   🔧 nevek cseréje: „{iss['tema']}” / story")
        except Exception as e:
            print(f"   ⚠ név-javítás sikertelen ({iss.get('tema')}): {e}")

    # 2) súlyos fact errors → targeted correction
    for iss in rep.get("fact", []):
        if iss.get("severity", "sulyos") != "sulyos":
            continue
        L = by_title.get((iss.get("tema") or "").strip()); mode = iss.get("mode")
        blk = await get_block(L["id"], mode) if (L and mode) else None
        if not blk:
            continue
        try:
            new = await ai(c, "Az alábbi kártyákban javítsd ki KIZÁRÓLAG ezt a tárgyi hibát:\n"
                f"Hibás állítás: {iss.get('claim')}\nHelyesen: {iss.get('fix')}\n"
                "Csak az érintett szöveget módosítsd, a többi tartalmat és a JSON-szerkezetet hagyd változatlanul.\n\n"
                "KÁRTYÁK:\n" + json.dumps(blk["content"], ensure_ascii=False),
                temp=0, model=DIST_MODEL, sys=FIX_SYS)
            await patch(blk["id"], new); fixes += 1
            print(f"   🔧 tényjavítás: „{iss['tema']}” / {mode}")
        except Exception as e:
            print(f"   ⚠ tényjavítás sikertelen ({iss.get('tema')}): {e}")

    # 3) missing mandatory NAT elements → inject into the best-fitting Téma's text block
    titles = [L["title_hu"].strip() for L in lessons]
    for miss in rep.get("missing", []):
        el, cat = miss.get("element"), miss.get("cat")
        try:
            new = await ai(c, "Egy kötelező NAT-elem hiányzik a tananyagból; pótold. Válaszd ki, melyik Témához "
                f"illik a legjobban, és írj hozzá EGY szöveges kártyát, amely NÉV SZERINT és kontextusban lefedi.\n"
                f"Kötelező elem ({cat}): {el}\nVálasztható Témák: {json.dumps(titles, ensure_ascii=False)}\n"
                '4-6 tartalmas, tényszerű magyar mondat.\n'
                'JSON: {"tema":"<a választott Téma cím>","card":{"type":"text","heading":"","body":"","key_term":""}}',
                temp=0.3, model=DIST_MODEL, sys=SYS)
            tema = (new.get("tema") or titles[0]).strip()
            L = by_title.get(tema) or by_title.get(titles[0])
            blk = await get_block(L["id"], "text")
            if not blk:
                continue
            cards = blk["content"] if isinstance(blk["content"], list) else blk["content"].get("cards", [])
            cards.append(new["card"])
            await patch(blk["id"], cards); fixes += 1
            print(f"   🔧 hiányzó elem pótolva: {el} → „{tema}” / text")
        except Exception as e:
            print(f"   ⚠ elempótlás sikertelen ({el}): {e}")

    return fixes


async def generate_topic(c, topic_nat, validate=True, modes=None, autofix=True, max_rounds=2):
    modes = modes or ALL_MODES
    partial = set(modes) != set(ALL_MODES)
    t = (await c.get(f"{SB}/rest/v1/curriculum_topics?nat_id=eq.{topic_nat}&select=id,title_hu,grade", headers=H_SB)).json()
    if not t:
        print(f"⚠ topic {topic_nat} not found in curriculum_topics"); return
    t = t[0]; topic_id, temakor = t["id"], t["title_hu"]
    nat = lookup_temakor(temakor, t.get("grade"))
    if not nat:
        print(f"⚠ no NAT map entry for „{temakor}” (grade {t.get('grade')})"); return
    temak = nat["temak"]; elements = nat["elements"]

    lessons = await ensure_lessons(c, topic_id, topic_nat, temak)
    by_title = {L["title_hu"].strip(): L for L in lessons}

    print(f"\n🗂️  {temakor}  ({len(temak)} Téma)")
    dist = await distribute_elements(c, temakor, temak, elements)
    print("   ✓ elemszétosztás kész")

    # clean slate: only for the modes we're (re)generating, so a partial run keeps the rest
    mode_filter = "&mode=in.(" + ",".join(modes) + ")"
    for L in lessons:
        await c.request("DELETE", f"{SB}/rest/v1/content_blocks?lesson_id=eq.{L['id']}{mode_filter}", headers=H_SB)
    if not partial:  # topic-scope quiz only wiped on a full run
        await c.request("DELETE", f"{SB}/rest/v1/content_blocks?topic_id=eq.{topic_id}&lesson_id=is.null", headers=H_SB)

    async def save(lesson_id, mode, scope, obj):
        cards = obj.get("cards", obj) if isinstance(obj, dict) else obj
        payload = {"lesson_id": lesson_id, "topic_id": topic_id, "mode": mode, "level": "alap",
                   "scope": scope, "content": cards, "review_status": "approved", "is_active": True}
        await c.post(f"{SB}/rest/v1/content_blocks", headers={**H_SB, "Prefer": "return=minimal"}, json=payload)

    for tm in temak:
        L = by_title.get(tm["title"].strip())
        if not L:
            print(f"   ⚠ lecke nem található: {tm['title']}"); continue
        d = dist.get(tm["title"].strip(), dist.get(tm["title"], {cat: [] for cat in CATS}))
        eb = elem_block(d)
        altemak = "; ".join(tm["altemak"]) or "—"
        print(f"\n📘 {tm['title']}")
        for mode in modes:
            for attempt in (1, 2):  # retry once on transient LLM/JSON failures
                try:
                    obj = await ai(c, prompt(mode, temakor, tm["title"], altemak, eb))
                    obj = await proof(c, obj)
                    await save(L["id"], mode, "lesson", obj)
                    print(f"   ✓ {mode} ({len(obj.get('cards',[]))} kártya)")
                    break
                except Exception as e:
                    print(f"   ⚠ {mode} (próba {attempt}): {e}")

    # end-of-topic comprehensive quiz (all elements) — only on a full run
    if not partial:
        all_eb = elem_block(elements)
        print("\n🎯 Témazáró kvíz")
        for attempt in (1, 2):
            try:
                q = await ai(c, f"Témakör: „{temakor}”.\nKészíts 8 kérdéses ÁTFOGÓ TÉMAZÁRÓ kvízt, amely az egész témakör "
                    f"alábbi kötelező NAT-elemeit kéri számon, vegyesen:\n{all_eb}\nMinden kérdéshez rövid magyarázat.\n"
                    'JSON: {"title":"Témazáró kvíz","cards":[{"type":"quiz","question_type":"multiple_choice","question":"","options":["A) ","B) ","C) ","D) "],"correct":"A","explanation":""}]}',
                    maxtok=3500)
                q = await proof(c, q)
                await save(None, "quiz", "topic", q)
                print(f"   ✓ témazáró kvíz ({len(q.get('cards',[]))} kérdés)")
                break
            except Exception as e:
                print(f"   ⚠ témazáró (próba {attempt}): {e}")
    print("\n✅ Done.")

    if not validate:
        return None
    try:
        import validate_temakor as V
        allowed_names = (elements or {}).get("szemelyek", [])
        rep = await V._run(topic_nat)
        rep["topic"]["nat_id"] = topic_nat
        rep["verdict"] = V._verdict(rep)

        # auto-fix-and-recheck loop: fix names + súlyos facts, then re-validate
        rounds = 0
        while autofix and rounds < max_rounds and (rep["fact"] or rep.get("missing") or any(
                i.get("kind") == "nev" for i in rep["appropriateness"])):
            print(f"\n🔁 auto-fix kör {rounds + 1}…")
            applied = await apply_fixes(c, lessons, allowed_names, rep)
            if not applied:
                break
            rep = await V._run(topic_nat)
            rep["topic"]["nat_id"] = topic_nat
            rep["verdict"] = V._verdict(rep)
            rounds += 1

        print("\n" + "=" * 60 + "\n🛡️  GUARD RAIL\n" + "=" * 60)
        print(V._report_md(rep))
        print(f"\n→ GUARD RAIL: {rep['verdict']}  (auto-fix körök: {rounds})")
        return rep
    except Exception as e:
        print(f"⚠ validáció kihagyva: {e}")
        return None


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nat-id", required=True, help="curriculum_topics.nat_id, e.g. HIST-78-VH1")
    ap.add_argument("--no-validate", action="store_true")
    ap.add_argument("--no-autofix", action="store_true", help="validate but don't auto-fix found issues")
    ap.add_argument("--modes", help="comma-separated subset to (re)generate, e.g. story (default: all)")
    args = ap.parse_args()
    modes = [m.strip() for m in args.modes.split(",")] if args.modes else None
    async with httpx.AsyncClient() as c:
        await generate_topic(c, args.nat_id, validate=not args.no_validate,
                             modes=modes, autofix=not args.no_autofix)

if __name__ == "__main__":
    asyncio.run(main())
