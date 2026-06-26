"""
Témakör generator (NAT 3-tier vertical slice).
Generates, for one Témakör (Topic), per-Téma (Lesson) content driven by the
official NAT mandatory elements, in Hungary-centered framing, plus a "Világ ekkor"
global layer per lesson and an end-of-topic comprehensive quiz. Level = alap.
Writes to content_blocks. Hardcoded for the WWI slice (HIST-78-VH1).
"""
import os, json, asyncio, httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
RK = os.getenv("OPENROUTER_API_KEY")
MODEL = "openai/gpt-4o-mini"
OR = "https://openrouter.ai/api/v1/chat/completions"
H_OR = {"Authorization": f"Bearer {RK}", "Content-Type": "application/json",
        "HTTP-Referer": "https://turul.academy", "X-Title": "Turul"}
H_SB = {"apikey": SVC, "Authorization": f"Bearer {SVC}", "Content-Type": "application/json"}

TOPIC_NAT = "HIST-78-VH1"
SYS = ("Te egy tapasztalt magyar történelemtanár és tananyagfejlesztő vagy. A magyar nemzet és "
       "Magyarország története áll a középpontban; az egyetemes történelmet ehhez kapcsolva, magyar "
       "nézőpontból mutatod be (NAT 2020). Minden szöveg KIZÁRÓLAG magyar nyelven, idegen szavak nélkül, "
       "tényszerűen pontos. CSAK érvényes JSON-t adsz vissza.")

# Mandatory NAT elements distributed across the 3 Témák (historically correct partition)
DIST = {
 "HIST-78-VH1-T1": {"fogalmak":["antant","központi hatalmak","front","állóháború","hátország"],
                    "szemelyek":["Tisza István"], "kronologia":["1914–1918 (az első világháború)"],
                    "topografia":["Szarajevó","Szerbia","Doberdó"]},
 "HIST-78-VH1-T2": {"fogalmak":["bolsevik","tanácsköztársaság","vörösterror","fehér különítményes megtorlások"],
                    "szemelyek":["Lenin","Károlyi Mihály","Horthy Miklós"], "kronologia":["1917 (a bolsevik hatalomátvétel)"],
                    "topografia":[]},
 "HIST-78-VH1-T3": {"fogalmak":["kisantant"], "szemelyek":[], "kronologia":["1920. június 4. (a trianoni békediktátum)"],
                    "topografia":["Kárpátalja","Felvidék","Délvidék","Burgenland","Erdély","Csehszlovákia","Jugoszlávia","Románia","Ausztria"]},
}

def elem_block(d):
    def fmt(k, label): return f"{label}: {', '.join(d[k])}" if d[k] else ""
    return "\n".join(x for x in [fmt('fogalmak','Fogalmak'), fmt('szemelyek','Személyek'),
                                 fmt('kronologia','Kronológia'), fmt('topografia','Topográfia')] if x)

async def ai(c, prompt, temp=0.55, maxtok=3200, sys=SYS):
    r = await c.post(OR, headers=H_OR, json={"model":MODEL,"max_tokens":maxtok,"temperature":temp,
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
            'szemszögéből, hanem a mindennapi élet KÜLÖNBÖZŐ ÁGAIT járd körül. Példák a lefedendő, eltérő területekre (válassz '
            'közülük, ne ismételd): a frontkatonák mindennapjai (lövészárok, sovány fejadag, honvágy, a családtól való elszakadás); '
            'a hátország asszonyai (sorbanállás az élelemért, a férfiak helyét átvevő gyári munka); a kormányzat és a hivatalok '
            'nehézségei (jegyrendszer, hadigazdálkodás megszervezése); a gazdaság és a hadiipar terhei (a parasztok és az '
            'ellátási lánc, rekvirálás, nyersanyaghiány); a gyerekek és az iskola háborús hétköznapjai; a sebesültek, kórházak, '
            'járványok. '
            'Névtelen, de VALÓS, dokumentált korabeli körülményeken alapuló, REPREZENTATÍV alanyokat használj '
            '(pl. „a doberdói lövészárokban szolgáló honvédek”, „a hátországban maradt asszonyok”, „a falusi gazdák”); kitalált, '
            'NEVESÍTETT történelmi személyt SOHA ne találj ki. Érzékletes, anyagi és érzelmi valóság. '
            'Ahol természetes, kösd a kötelező fogalmakat az ÁTÉLT valóságukhoz (pl. állóháború → a lövészárok-lét; '
            'hátország → az otthon maradtak élete). 5-8 kártya, mindegyik MÁS témáról.\n'
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
            "„befolyásolta a helyzetet”. Példa a rossz (homályos) vs. jó (konkrét) megfogalmazásra: rossz: „befolyásolta a magyar "
            "katonák harci helyzetét”; jó: „a felszabaduló német erőket nyugatra vezényelték, így sok magyar katonát a hazájától "
            "több száz kilométerre, az olasz vagy nyugati fronton vetettek be”. Felső szintű tények kellenek, nem mély elbeszélés. "
            "TILOS az általános, sablonos megfogalmazás (pl. „alapvetően formálta Magyarország jövőjét”, „közvetlenül érintett volt”, "
            "„meghatározta a helyzetét”). "
            "Ügyelj a pontosságra (pl. Magyarország I. világháborút lezáró békeszerződése a TRIANONI, 1920. június 4. — NEM a versailles-i). "
            "Ez kiegészítő, érdeklődő tanulóknak szóló réteg, nem kötelező tananyag. 4-6 kártya.\n"
            'JSON: {"title":"Világ ekkor","cards":[{"type":"world","year":"az adott esemény saját évszáma","heading":"","body":"","link_hu":"konkrét ok-okozati kapcsolat e lecke magyar anyagához"}]}')

async def main():
    async with httpx.AsyncClient() as c:
        # fetch topic + lessons
        t = (await c.get(f"{SB}/rest/v1/curriculum_topics?nat_id=eq.{TOPIC_NAT}&select=id,title_hu", headers=H_SB)).json()[0]
        topic_id, temakor = t["id"], t["title_hu"]
        lessons = (await c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{topic_id}&select=id,nat_id,title_hu&order=order_index", headers=H_SB)).json()
        # clean slate for this topic
        await c.request("DELETE", f"{SB}/rest/v1/content_blocks?topic_id=eq.{topic_id}", headers=H_SB)
        for L in (await c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{topic_id}&select=id", headers=H_SB)).json():
            await c.request("DELETE", f"{SB}/rest/v1/content_blocks?lesson_id=eq.{L['id']}", headers=H_SB)

        async def save(lesson_id, mode, scope, obj):
            cards = obj.get("cards", obj) if isinstance(obj, dict) else obj
            payload = {"lesson_id":lesson_id, "topic_id":topic_id, "mode":mode, "level":"alap",
                       "scope":scope, "content":cards, "review_status":"approved", "is_active":True}
            await c.post(f"{SB}/rest/v1/content_blocks", headers={**H_SB,"Prefer":"return=minimal"}, json=payload)

        for L in lessons:
            d = DIST[L["nat_id"]]; eb = elem_block(d)
            print(f"\n📘 {L['title_hu']}")
            for mode in ["text","story","visual","quiz","world"]:
                try:
                    obj = await ai(c, prompt(mode, temakor, L["title_hu"], "—", eb))
                    obj = await proof(c, obj)
                    await save(L["id"], mode, "lesson", obj)
                    print(f"   ✓ {mode} ({len(obj.get('cards',[]))} kártya)")
                except Exception as e:
                    print(f"   ⚠ {mode}: {e}")

        # end-of-topic comprehensive quiz (all elements)
        all_eb = "\n".join(elem_block(d) for d in DIST.values())
        print("\n🎯 Témazáró kvíz")
        try:
            q = await ai(c, f"Témakör: „{temakor}”.\nKészíts 8 kérdéses ÁTFOGÓ TÉMAZÁRÓ kvízt, amely az egész témakör "
                f"alábbi kötelező NAT-elemeit kéri számon, vegyesen:\n{all_eb}\nMinden kérdéshez rövid magyarázat.\n"
                'JSON: {"title":"Témazáró kvíz","cards":[{"type":"quiz","question_type":"multiple_choice","question":"","options":["A) ","B) ","C) ","D) "],"correct":"A","explanation":""}]}',
                maxtok=3500)
            q = await proof(c, q)
            await save(None, "quiz", "topic", q)
            print(f"   ✓ témazáró kvíz ({len(q.get('cards',[]))} kérdés)")
        except Exception as e:
            print(f"   ⚠ témazáró: {e}")
    print("\n✅ Done.")

    # ---- guard rail: validate the freshly generated topic ----
    try:
        import validate_temakor as V
        rep = await V._run(TOPIC_NAT)
        rep["topic"]["nat_id"] = TOPIC_NAT
        rep["verdict"] = V._verdict(rep)
        print("\n" + "=" * 60 + "\n🛡️  GUARD RAIL\n" + "=" * 60)
        print(V._report_md(rep))
        print(f"\n→ GUARD RAIL: {rep['verdict']}")
    except Exception as e:
        print(f"⚠ validáció kihagyva: {e}")

asyncio.run(main())
