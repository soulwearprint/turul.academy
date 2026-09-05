"""
Témakör generator (NAT 3-tier model) — Physics.

Parallel to generate_temakor.py (History), NOT a shared/parametrized version —
the taxonomy and prompts are different enough (see docs/HANDOFF_PHYSICS.md) that
forcing one generic script would obscure more than it'd save.

Key structural difference from History: Témák (lessons) and their mandatory
`feladatok` (facts) are ALREADY assigned per-Téma by cluster_temak_physics.py
(History has to LLM-distribute its elements at generation time because its
source docx only names Témák, not which facts belong to which). Physics only
needs a distribution pass for `fogalmak` (concepts) and `tevekenysegek`
(suggested activities) — both are still Témakör-level lists in the source.

Content direction (locked, user 2026-07-07/08): less academic, more hands-on/
anecdotal than History. `text`/`story`/`visual`/`quiz` cover the mandatory
feladatok+fogalmak (rigorous, exam-relevant) but in an engaging tone; the new
`experiment` mode (replaces History's `world` layer for Physics) carries the
optional enrichment: invention/discovery-era anecdote, a sketch description,
and modern-day usage/reproduction — sourced loosely from `tevekenysegek`.
Same honesty rule as History's world layer: if a Téma doesn't genuinely support
these (too abstract/mathematical), say so in one card rather than forcing it.

Usage:
    python generate_temakor_physics.py --nat-id PHYS-78-01
    python generate_temakor_physics.py --nat-id PHYS-78-01 --no-validate
"""
import os, json, asyncio, argparse, httpx
from dotenv import load_dotenv
from generate_temakor import cards_from

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
RK = os.getenv("OPENROUTER_API_KEY")
MODEL = "openai/gpt-4o-mini"
DIST_MODEL = "openai/gpt-4o"
GEN_CONCURRENCY = int(os.getenv("GEN_CONCURRENCY", "8"))
OR = "https://openrouter.ai/api/v1/chat/completions"
H_OR = {"Authorization": f"Bearer {RK}", "Content-Type": "application/json",
        "HTTP-Referer": "https://turul.academy", "X-Title": "Turul"}
H_SB = {"apikey": SVC, "Authorization": f"Bearer {SVC}", "Content-Type": "application/json"}
TEMAK_MAP = os.path.join(os.path.dirname(__file__), "../nat_curriculum/physics_nat2020_temak.json")

SYS = ("Te egy tapasztalt magyar fizikatanár és tananyagfejlesztő vagy (NAT 2020). Stílusod nem "
       "száraz-akadémikus, hanem GYAKORLATIAS és ÉLETSZERŰ — a kötelező definíciókat és szabályokat "
       "mindig hétköznapi példákkal, jelenségekkel kötöd össze. Minden szöveg KIZÁRÓLAG magyar nyelven, "
       "idegen szavak nélkül, tényszerűen pontos. KIVÉTEL: a NEMZETKÖZILEG SZABVÁNYOS fizikai rövidítéseket "
       "és jelöléseket (pl. AC, DC, és a mértékegység-jelek: V, A, W, Hz) MINDIG az eredeti, nemzetközi "
       "formájukban használd — SOSE alkoss hozzájuk saját magyar rövidítést (pl. NE „VA” a váltakozó áramra, "
       "hanem „AC”). Egy fogalom első előfordulásakor add meg zárójelben a magyar nevet/jelentést is, "
       "konzisztens stílusban (pl. „AC (váltakozó áram)” vagy „váltakozó áram (AC)” — válassz egy sorrendet "
       "és tartsd magad hozzá a leckén belül). CSAK érvényes JSON-t adsz vissza.")

DIST_CATS = ("fogalmak", "tevekenysegek")


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


async def distribute_elements(c, temakor, temak, fogalmak, tevekenysegek):
    """LLM assigns each fogalom/tevékenység to the Téma it best fits (feladatok are
    already pre-assigned per Téma by cluster_temak_physics.py — nothing to do there).
    Returns {tema_title: {fogalmak:[...], tevekenysegek:[...]}} covering ALL elements."""
    temak_desc = "\n".join(f'- „{t["title"]}” (feladatok: {"; ".join(t["feladatok"])})' for t in temak)
    out = await ai(c,
        f"Témakör: „{temakor}”.\nA témakör Témái (leckéi) és feladataik:\n{temak_desc}\n\n"
        f"Fogalmak (mind kötelező): {', '.join(fogalmak)}\n"
        f"Javasolt tevékenységek: {', '.join(tevekenysegek)}\n\n"
        "Oszd szét MINDEN fogalmat és MINDEN tevékenységet a Témák között: amelyikhez tematikailag "
        "a legjobban illik. Minden elemet pontosan egy Témához rendelj, egyik se maradjon ki. "
        "CSAK a megadott Téma-címeket használd kulcsként.\n"
        'JSON: {"<Téma cím>": {"fogalmak":[],"tevekenysegek":[]}}',
        temp=0, maxtok=2000, sys="Magyar fizika tananyagfejlesztő vagy. Csak JSON-t adsz vissza.",
        model=DIST_MODEL)
    assigned = {cat: set() for cat in DIST_CATS}
    for v in out.values():
        for cat in DIST_CATS:
            assigned[cat].update(v.get(cat, []) or [])
    first = temak[0]["title"]
    out.setdefault(first, {cat: [] for cat in DIST_CATS})
    for cat, all_els in (("fogalmak", fogalmak), ("tevekenysegek", tevekenysegek)):
        for el in all_els:
            if el not in assigned[cat]:
                out[first].setdefault(cat, []).append(el)
    return out


def elem_block(feladatok, fogalmak, tevekenysegek):
    parts = []
    if feladatok:
        parts.append("Kötelező feladatok/ismeretek: " + "; ".join(feladatok))
    if fogalmak:
        parts.append("Fogalmak: " + ", ".join(fogalmak))
    if tevekenysegek:
        parts.append("Javasolt tevékenységek: " + "; ".join(tevekenysegek))
    return "\n".join(parts)


async def ai(c, prompt, temp=0.55, maxtok=3200, sys=SYS, model=MODEL):
    r = await c.post(OR, headers=H_OR, json={"model": model, "max_tokens": maxtok, "temperature": temp,
        "messages": [{"role": "system", "content": sys}, {"role": "user", "content": prompt}]}, timeout=120)
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.splitlines()[1:-1])
    return json.loads(raw)


async def proof(c, obj):
    try:
        return await ai(c, "Javítsd ki az alábbi JSON szöveges mezőiben a helyesírási, nyelvtani és "
            "központozási hibákat. NE változtasd a tartalmat, szerkezetet vagy kulcsokat. CSAK a javított JSON-t add vissza.\n\n"
            + json.dumps(obj, ensure_ascii=False), temp=0, sys="Gondos magyar korrektor vagy. Csak JSON-t adsz vissza.")
    except Exception:
        return obj


SKETCH_VOCAB = (
    "A `sketch` mező NEM szöveg, hanem egy STRUKTURÁLT rajz-leírás, amit egy renderer alakít SVG-vé — "
    "ezért NE ábra-leírást írj, hanem konkrét alakzatokat sorolj fel a megadott vázlatnyelven. Vászon: "
    "400×300 egység (x: 0-400, y: 0-300, origó bal-felül). Formátum: "
    '{"viewBox":"0 0 400 300","shapes":[...]}. Ha nincs értelmes vázlat, adj vissza {"shapes":[]}-t.\n'
    "Elérhető alakzat-típusok (`type` mező), csak ezeket használd:\n"
    "  - box: {\"type\":\"box\",\"x\",\"y\",\"w\",\"h\"} — téglalap (test, tok, mágnesrúd, tábla)\n"
    "  - circle: {\"type\":\"circle\",\"x\",\"y\",\"r\"} — kör (izzó, kerék, részecske, súly)\n"
    "  - line: {\"type\":\"line\",\"x1\",\"y1\",\"x2\",\"y2\",\"dashed\":true|false} — egyenes (vezeték, "
    "tengely, mezővonal; dashed=true a szaggatott/láthatatlan vonalakhoz)\n"
    "  - arrow: {\"type\":\"arrow\",\"x1\",\"y1\",\"x2\",\"y2\"} — nyíl (erő, irány, áramlás iránya)\n"
    "  - coil: {\"type\":\"coil\",\"x\",\"y\",\"w\",\"h\",\"turns\"} — tekercs oldalnézetből (induktor, "
    "szolenoid)\n"
    "  - spring: {\"type\":\"spring\",\"x1\",\"y1\",\"x2\",\"y2\",\"coils\"} — rugó (cikkcakk vonal)\n"
    "  - dot: {\"type\":\"dot\",\"x\",\"y\"} — pont (forgáspont, rögzített pont, tömegpont)\n"
    "  - triangle: {\"type\":\"triangle\",\"x\",\"y\",\"size\"} — háromszög (támasz, föld-jel, mutató)\n"
    "  - wave: {\"type\":\"wave\",\"x1\",\"y1\",\"x2\",\"y2\",\"amplitude\",\"cycles\"} — hullámvonal "
    "(fényhullám, rezgés)\n"
    "  - battery: {\"type\":\"battery\",\"x\",\"y\",\"w\",\"h\"} — elemszimbólum (hosszú/rövid vonal)\n"
    "  - label: {\"type\":\"label\",\"x\",\"y\",\"text\"} — rövid felirat (pl. „N”, „S”, „F”, „v”, „I”)\n"
    "Csak azt a néhány (3-8) alakzatot add meg, ami a jelenséget/kísérleti elrendezést valóban szemlélteti — "
    "egyszerű, táblarajz-szerű kompozíció, ne túlzsúfolt. Használj `label` alakzatokat a kulcs-elemek "
    "megjelöléséhez (pólusok, mennyiségek, irányok).\n"
    'Példa (mágnes mozgatása tekercsben): {"viewBox":"0 0 400 300","shapes":['
    '{"type":"coil","x":150,"y":100,"w":120,"h":80,"turns":6},'
    '{"type":"box","x":40,"y":120,"w":70,"h":40},'
    '{"type":"label","x":55,"y":145,"text":"N"},{"type":"label","x":95,"y":145,"text":"S"},'
    '{"type":"arrow","x1":120,"y1":140,"x2":150,"y2":140},'
    '{"type":"line","x1":270,"y1":140,"x2":360,"y2":140},'
    '{"type":"label","x":300,"y":170,"text":"I"}]}'
)

MODERN_EXAMPLE_GUIDANCE = (
    "PÉLDÁK VÁLASZTÁSA: ha mai gyakorlati alkalmazást vagy hétköznapi példát említesz, azt válaszd, ami egy "
    "MAI magyar tizenéves számára VALÓBAN ismerős és gyakori — pl. vezeték nélküli (Qi) telefontöltés, "
    "indukciós főzőlap, érintés nélküli bankkártyás fizetés, elektromos autók rekuperációs fékezése, "
    "szélerőmű/naperőmű, mobilinternet/wifi. KERÜLD az elavult vagy ritka példákat (pl. kerékpár-dinamó — "
    "ma már alig van ilyen kerékpár), és NE ismételd ugyanazt a példát több kártyán vagy több módban "
    "(text/story/experiment) belül — válassz minden alkalommal más, változatos példát."
)


def prompt(mode, temakor, tema, feladatok, fogalmak, tevekenysegek):
    eb = elem_block(feladatok, fogalmak, tevekenysegek)
    head = (f"Témakör: „{temakor}”\nLecke (Téma): „{tema}”\n\n"
            f"A leckének le KELL fednie és érthetően el kell magyaráznia az alábbiakat:\n{eb}\n")

    if mode == "text":
        return head + ('\nKészíts strukturált SZÖVEGES leckét: gyakorlatias, hétköznapi példákkal élénkített '
            '(NE száraz-akadémikus felsorolás). Annyi kártya, amennyi a fenti feladatok/fogalmak értelmes '
            'lefedéséhez kell (kb. 5-8). Minden kötelező feladat és fogalom jelenjen meg legalább egy kártyában. '
            '4-6 tartalmas, tényszerű mondat kártyánként.\n'
            f'{MODERN_EXAMPLE_GUIDANCE}\n'
            'JSON: {"title":"","cards":[{"type":"text","heading":"","body":"","key_term":""}]}')
    if mode == "story":
        return head + ('\nKészíts RENDSZER-NYOMKÖVETÉS leckét — ez NEM különálló hétköznapi jelenetek sorozata '
            '(sok fizikai jelenség itt nem egy tárgy, amit valaki HASZNÁL, hanem egy láthatatlan MECHANIZMUS/'
            'INFRASTRUKTÚRA, ami MŰKÖDTET valamit a háttérben — ezt hamisítja meg egy „valaki használja a '
            'kütyüt” jelenet). Ehelyett kövesd VÉGIG, EGYETLEN FOLYAMATOS TÖRTÉNETSZÁLKÉNT, hogyan jut el a '
            'jelenség/hatás az egyik végponttól a másikig — minden kártya a FOLYAMAT KÖVETKEZŐ ÁLLOMÁSA, nem '
            'egy új, független jelenet. Nyiss egy IDŐTLEN, univerzálisan ismerős emberi mozzanattal (pl. '
            '„felkapcsolod a villanyt”, „bedugod a töltőt”, „elindul a vonat”), majd kövesd a folyamatot '
            'VISSZAFELÉ vagy ELŐRE a fizikai mechanizmuson át — ki/mi mozgatja, mi alakul át, mi jut el hova. '
            'HARMADIK SZEMÉLYBEN, névtelen szereplőkkel, ha egyáltalán szerepel ember — SOSE adj kitalált '
            'személynevet. Kösd össze az állomásokat a fenti kötelező feladatokkal/fogalmakkal. 4-6 kártya, '
            'EGY összefüggő történetszál (ne 4-6 különböző, egymástól független jelenet).\n'
            f'{MODERN_EXAMPLE_GUIDANCE}\n'
            'JSON: {"title":"","cards":[{"type":"story","heading":"","body":""}]}')
    if mode == "visual":
        return head + ('\nKészíts VIZUÁLIS leckét: minden fő fogalomhoz/feladathoz egy szemléltető elem '
            '(diagram/vázlat/grafikon/keresztmetszet) leírása, amely a jelenséget/mennyiséget szemlélteti. '
            '5-8 kártya.\n'
            'JSON: {"title":"","cards":[{"type":"visual","heading":"","visual_type":"","description":"","caption":""}]}')
    if mode == "quiz":
        return head + ('\nKészíts 5 kérdéses KVÍZT, amely KIZÁRÓLAG a fenti kötelező feladatokat/fogalmakat kéri '
            'számon — NE kérdezz vissza javasolt tevékenységet vagy projektötletet, csak fizikai tartalmat. '
            'Minden kérdéshez az `explanation` mezőbe ÍRJ egy rövid, 1-2 mondatos magyarázatot (ez a mező SOSE '
            'lehet üres). KRITIKUS: a helyes opció SZÖVEGE önmagában — a magyarázat elolvasása nélkül is — '
            'legyen fizikailag PONTOS és EGYÉRTELMŰ (ha a helyes opció megfogalmazása pontatlan/félrevezető, '
            'javítsd, mielőtt visszaadod), ÉS az explanation ne mondjon neki ellent.\n'
            'JSON: {"title":"","cards":[{"type":"quiz","question_type":"multiple_choice","question":"",'
            '"options":["A) ","B) ","C) ","D) "],"correct":"A","explanation":"1-2 mondatos indoklás"}]}')
    if mode == "experiment":
        return (f"Lecke: „{tema}” (Témakör: „{temakor}”).\n"
            f"Javasolt tevékenységek erre a leckére (inspirációként használd, nem kell mindet felhasználnod): "
            f"{'; '.join(tevekenysegek) or '(nincs megadva)'}\n\n"
            "ELSŐ LÉPÉS — dönts: van-e ennek a leckének VALÓS, KONKRÉT felfedezés-/találmány-történeti "
            "háttere, illetve reprodukálható kísérlete vagy mai gyakorlati alkalmazása? Ha a lecke túl "
            "elvont/matematikai ehhez (pl. csak egy mértékegység-átváltás vagy definíció) — NE találj ki "
            "hozzá erőltetett felfedezéstörténetet vagy kísérletet. Ehelyett adj vissza PONTOSAN EGY kártyát "
            "ÜRES `discovery`, `sketch` ({\"shapes\":[]}), `try_basic` és `try_advanced` mezőkkel, de A "
            "KÁRTYA `heading` MEZŐJÉT (nem csak a blokk `title` mezőjét — MINDKETTŐT) EKKOR IS töltsd ki "
            "(rövid, a lecke tárgyára utaló cím, pl. „Mozgás a mindennapokban”), és a `today` mezőben 1-2 "
            "mondatban említsd meg, hol találkozhat vele a diák a gyakorlatban.\n"
            "Csak ha VAN valós anyag: Készíts egy kártyát az alábbi (opcionális) részekkel:\n"
            "  - `discovery`: felfedezés/találmány-történeti anekdota — ki, mikor, milyen körülmények között "
            "jött rá erre, milyen problémát próbált megoldani. Konkrét, tényszerű, NE kitalált.\n"
            f"  - `sketch`: {SKETCH_VOCAB}\n"
            "  - `today`: hol találkozunk a jelenséggel a mai technológiában/gyakorlatban.\n"
            "  - `try_basic`: EGYSZERŰ, alacsony erőforrás-igényű kísérlet vagy megfigyelés, amit BÁRKI el "
            "tud végezni otthon/osztályteremben, hétköznapi eszközökkel, felnőtt felügyelet nélkül is "
            "biztonságos — ha a jelenség ezen a szinten nem reprodukálható biztonságosan/egyszerűen "
            "(pl. veszélyes áram, nagy energiák, speciális eszköz kell), hagyd üresen.\n"
            "  - `try_advanced`: HALADÓ szintű kísérlet/projekt azoknak, akiket jobban érdekel a téma vagy "
            "több eszköz áll rendelkezésükre — igényelhet iskolai labort, tanári felügyeletet, speciális "
            "eszközt vagy mélyebb utánajárást; ha nincs ilyen értelmes szint (a `try_basic` már a plafon), "
            "hagyd üresen.\n"
            "Bármelyik szöveges mező kihagyható (üres string), a `sketch` pedig {\"shapes\":[]}-ként, ha az "
            "adott lecke tartalmához nem illik erőltetve — NE tölts ki mezőt gyenge/kitalált tartalommal. "
            "Tárgyi pontosság kritikus (ne keverd össze tudósokat, évszámokat, felfedezéseket). Biztonság: "
            "SOSE javasolj veszélyes áramot/eszközt felügyelet nélküli otthoni kísérletként.\n"
            f"{MODERN_EXAMPLE_GUIDANCE}\n"
            'JSON: {"title":"Kísérlet és felfedezés","cards":[{"type":"experiment","heading":"",'
            '"discovery":"","sketch":{"viewBox":"0 0 400 300","shapes":[]},"today":"","try_basic":"",'
            '"try_advanced":""}]}')
    raise ValueError(f"unknown mode: {mode}")


async def ensure_lessons(c, topic_id, topic_nat, temak):
    existing = (await c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{topic_id}&select=id,nat_id,title_hu&order=order_index", headers=H_SB)).json()
    have = {L["title_hu"].strip() for L in existing}
    for i, tm in enumerate(temak, start=1):
        if tm["title"].strip() in have:
            continue
        payload = {"topic_id": topic_id, "nat_id": f"{topic_nat}-T{i}", "title": tm["title"],
                   "title_hu": tm["title"], "order_index": i, "is_active": False}
        await c.post(f"{SB}/rest/v1/curriculum_lessons", headers={**H_SB, "Prefer": "return=minimal"}, json=payload)
    return (await c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{topic_id}&select=id,nat_id,title_hu&order=order_index", headers=H_SB)).json()


ALL_MODES = ["text", "story", "visual", "quiz", "experiment"]
FIX_SYS = "Gondos magyar fizika-szerkesztő vagy. CSAK a javított JSON kártyatömböt adod vissza, azonos szerkezettel."


async def apply_fixes(c, lessons, rep, temakor=None):
    """Auto-fix the machine-correctable issues the guard rail found:
    invented names in story + súlyos fact errors + missing mandatory feladat/fogalom."""
    by_title = {L["title_hu"].strip(): L for L in lessons}
    fixes = 0

    async def get_block(lesson_id, mode):
        r = (await c.get(f"{SB}/rest/v1/content_blocks?lesson_id=eq.{lesson_id}&mode=eq.{mode}&select=id,content", headers=H_SB)).json()
        return r[0] if r else None

    async def patch(bid, obj):
        await c.patch(f"{SB}/rest/v1/content_blocks?id=eq.{bid}", headers={**H_SB, "Prefer": "return=minimal"}, json={"content": cards_from(obj)})

    for iss in rep.get("appropriateness", []):
        if iss.get("kind") != "nev":
            continue
        L = by_title.get((iss.get("tema") or "").strip())
        blk = await get_block(L["id"], "story") if L else None
        if not blk:
            continue
        try:
            new = await ai(c, "Írd át az alábbi TÖRTÉNET-kártyákat úgy, hogy MINDEN kitalált személynevet "
                "általános, névtelen szereplőre cserélsz (pl. „egy biciklis”, „a diákok”, „egy szerelő”). "
                "A tartalmat, a sorrendet és a JSON-szerkezetet tartsd meg, csak a neveket cseréld.\n\n"
                "KÁRTYÁK:\n" + json.dumps(blk["content"], ensure_ascii=False),
                temp=0, model=DIST_MODEL, sys=FIX_SYS)
            await patch(blk["id"], new); fixes += 1
            print(f"   🔧 nevek cseréje: „{iss['tema']}” / story")
        except Exception as e:
            print(f"   ⚠ név-javítás sikertelen ({iss.get('tema')}): {e}")

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

    exp_temas = {(iss.get("tema") or "").strip() for iss in rep.get("experiment", [])}
    for tema in exp_temas:
        L = by_title.get(tema)
        blk = await get_block(L["id"], "experiment") if L else None
        if not blk:
            continue
        try:
            new = await ai(c, prompt("experiment", temakor or "", tema, [], [], []))
            new = await proof(c, new)
            await patch(blk["id"], new); fixes += 1
            print(f"   🔧 kísérlet-réteg újragenerálva (relevancia): „{tema}”")
        except Exception as e:
            print(f"   ⚠ kísérlet-réteg javítás sikertelen ({tema}): {e}")

    titles = [L["title_hu"].strip() for L in lessons]
    for miss in rep.get("missing", []):
        el, cat = miss.get("element"), miss.get("cat")
        try:
            new = await ai(c, "Egy kötelező feladat/fogalom hiányzik a tananyagból; pótold. Válaszd ki, melyik "
                f"Témához illik a legjobban, és írj hozzá EGY szöveges kártyát.\n"
                f"Kötelező elem ({cat}): {el}\nVálasztható Témák: {json.dumps(titles, ensure_ascii=False)}\n"
                '4-6 tartalmas, tényszerű magyar mondat, gyakorlatias framing-gel.\n'
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
        print(f"⚠ no physics NAT map entry for „{temakor}” (grade {t.get('grade')})"); return
    temak = nat["temak"]; fogalmak = nat["fogalmak"]; tevekenysegek = nat["tevekenysegek"]

    lessons = await ensure_lessons(c, topic_id, topic_nat, temak)
    by_title = {L["title_hu"].strip(): L for L in lessons}

    print(f"\n🗂️  {temakor}  ({len(temak)} Téma)")
    dist = await distribute_elements(c, temakor, temak, fogalmak, tevekenysegek)
    print("   ✓ fogalmak/tevékenységek szétosztás kész")

    mode_filter = "&mode=in.(" + ",".join(modes) + ")"
    for L in lessons:
        await c.request("DELETE", f"{SB}/rest/v1/content_blocks?lesson_id=eq.{L['id']}{mode_filter}", headers=H_SB)
    if not partial:
        await c.request("DELETE", f"{SB}/rest/v1/content_blocks?topic_id=eq.{topic_id}&lesson_id=is.null", headers=H_SB)

    async def save(lesson_id, mode, scope, obj):
        payload = {"lesson_id": lesson_id, "topic_id": topic_id, "mode": mode, "level": "alap",
                   "scope": scope, "content": cards_from(obj), "review_status": "approved", "is_active": True}
        await c.post(f"{SB}/rest/v1/content_blocks", headers={**H_SB, "Prefer": "return=minimal"}, json=payload)

    sem = asyncio.Semaphore(GEN_CONCURRENCY)

    async def gen_one(L, tm, mode, d):
        async with sem:
            for attempt in (1, 2):
                try:
                    obj = await ai(c, prompt(mode, temakor, tm["title"], tm["feladatok"],
                                              d.get("fogalmak", []), d.get("tevekenysegek", [])))
                    obj = await proof(c, obj)
                    await save(L["id"], mode, "lesson", obj)
                    print(f"   ✓ {tm['title'][:28]} / {mode} ({len(obj.get('cards', []))} kártya)")
                    return
                except Exception as e:
                    print(f"   ⚠ {tm['title'][:28]} / {mode} (próba {attempt}): {e}")

    tasks = []
    for tm in temak:
        L = by_title.get(tm["title"].strip())
        if not L:
            print(f"   ⚠ lecke nem található: {tm['title']}"); continue
        d = dist.get(tm["title"].strip(), dist.get(tm["title"], {cat: [] for cat in DIST_CATS}))
        for mode in modes:
            tasks.append(gen_one(L, tm, mode, d))
    print(f"\n📘 {len(tasks)} blokk generálása (párhuzamosság: {GEN_CONCURRENCY})…")
    await asyncio.gather(*tasks)

    if not partial:
        all_feladatok = [f for tm in temak for f in tm["feladatok"]]
        eb = elem_block(all_feladatok, fogalmak, [])
        print("\n🎯 Témazáró kvíz")
        for attempt in (1, 2):
            try:
                q = await ai(c, f"Témakör: „{temakor}”.\nKészíts 8 kérdéses ÁTFOGÓ TÉMAZÁRÓ kvízt, amely az "
                    f"egész témakör alábbi kötelező feladatait/fogalmait kéri számon, vegyesen:\n{eb}\n"
                    "Minden kérdéshez rövid magyarázat.\n"
                    'JSON: {"title":"Témazáró kvíz","cards":[{"type":"quiz","question_type":"multiple_choice","question":"","options":["A) ","B) ","C) ","D) "],"correct":"A","explanation":""}]}',
                    maxtok=3500)
                q = await proof(c, q)
                await save(None, "quiz", "topic", q)
                print(f"   ✓ témazáró kvíz ({len(q.get('cards', []))} kérdés)")
                break
            except Exception as e:
                print(f"   ⚠ témazáró (próba {attempt}): {e}")
    print("\n✅ Done.")

    if not validate:
        return None
    try:
        import validate_temakor_physics as V
        rep = await V._run(topic_nat)
        rep["topic"]["nat_id"] = topic_nat
        rep["verdict"] = V._verdict(rep)

        rounds = 0
        while autofix and rounds < max_rounds and (rep["fact"] or rep.get("missing") or rep.get("experiment") or any(
                i.get("kind") == "nev" for i in rep["appropriateness"])):
            print(f"\n🔁 auto-fix kör {rounds + 1}…")
            applied = await apply_fixes(c, lessons, rep, temakor=temakor)
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
    ap.add_argument("--nat-id", required=True, help="curriculum_topics.nat_id, e.g. PHYS-78-01")
    ap.add_argument("--no-validate", action="store_true")
    ap.add_argument("--no-autofix", action="store_true")
    ap.add_argument("--modes", help="comma-separated subset to (re)generate (default: all)")
    args = ap.parse_args()
    modes = [m.strip() for m in args.modes.split(",")] if args.modes else None
    async with httpx.AsyncClient() as c:
        await generate_topic(c, args.nat_id, validate=not args.no_validate,
                             modes=modes, autofix=not args.no_autofix)

if __name__ == "__main__":
    asyncio.run(main())
