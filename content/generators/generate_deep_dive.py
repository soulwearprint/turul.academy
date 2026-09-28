"""
„Mesélj még!" deep-dive layer (NAT 3-tier) — one `deep` block per Téma.

Pre-generated and guard-railed ONCE, so a student's tap costs nothing: no LLM call
happens at read time (live free models were tested 2026-09-24 and produced unusable
Hungarian; live paid calls would cost per tap).

For each lesson the generator is given exactly what the student reads — the lesson's
text cards, numbered — plus the story/visual headings as context, and writes ONE deep
card per text card. Each deep card carries `anchor` (0-based index of the text card it
expands) so the lesson player can put a „Mesélj még!" button under that card.

Stored as content_blocks(mode='deep', level='emelt', scope='lesson'). `deep` is a new
mode: the lesson endpoint returns it, older frontends simply ignore it.

Guard rail per lesson:
  1. Strict claim verification (gpt-4o): every concrete number/date/name/record/law is
     judged certain / false / uncertain; anything not certain is generalised or removed.
     The subject validators are deliberately lenient ("let uncertain cases go" — right for
     curriculum text), which let wrong trivia through in the v1 run.
  2. The subject's validator (reused): fact check → confirm pass → appropriateness
     (grade fit / Hungarian-only / tone). Severe confirmed fact issues and language/grade
     issues get ONE targeted fix round (re-verified, since a fix can add claims), then are
     re-checked; a lesson still carrying a severe fact issue is saved INACTIVE and flagged.
  3. Proofreading (grammar, Hungarian number format) last.

Usage:
    python generate_deep_dive.py --nat-id PHYS-78-03
    python generate_deep_dive.py --nat-id PHYS-78-03 --dry-run   # generate + check, don't save
    python generate_deep_dive.py --nat-id PHYS-78-03 --reverify  # re-check saved cards only
Writes a review doc to content/exports/<nat_id>_deep_dive_review.md.
"""
import os, json, asyncio, argparse, httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB = os.getenv("SUPABASE_URL"); SVC = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
RK = (os.getenv("OPENROUTER_API_KEY") or "").strip()
# gpt-4o, not the lesson generators' gpt-4o-mini: the POC's mini run (2026-09-28,
# content/exports/PHYS-78-03_deep_dive_review_v1.md) mostly restated its source cards
# instead of going deeper, and padded "did you know" with records/stats it got wrong.
MODEL = "openai/gpt-4o"
FIX_MODEL = "openai/gpt-4o"         # targeted fixes + claim verification (precision matters)
OR = "https://openrouter.ai/api/v1/chat/completions"
H_OR = {"Authorization": f"Bearer {RK}", "Content-Type": "application/json",
        "HTTP-Referer": "https://turul.academy", "X-Title": "Turul"}
H_SB = {"apikey": SVC, "Authorization": f"Bearer {SVC}", "Content-Type": "application/json"}
EXPORTS = os.path.join(os.path.dirname(__file__), "../exports")
FIX_SYS = "Gondos magyar tananyag-szerkesztő vagy. CSAK a javított JSON kártyatömböt adod vissza, azonos szerkezettel."
FIXABLE_APPRO = {"idegen_szo", "korosztaly", "tartalom"}


def subject_cfg(nat_id):
    """Subject-specific prompts + validator module (the validators are parallel, not shared)."""
    if nat_id.startswith("PHYS"):
        import generate_temakor_physics as G, validate_temakor_physics as V
        return {"sys": G.SYS, "V": V, "subject": "fizika", "extra": G.MODERN_EXAMPLE_GUIDANCE + (
            "\nTÉVKÉPZETEK KERÜLÉSE: a kanyarodást a tehetetlenséggel és a befelé mutató (pl. súrlódási) "
            "erővel magyarázd, NE „kifelé toló centrifugális erővel”; a gyorsulás a sebesség VÁLTOZÁSA (iránya "
            "is), nem „gyorsabb sebesség”; a testek tömegüktől függetlenül ugyanúgy esnek (légellenállás nélkül).")}
    import generate_temakor as G, validate_temakor as V
    return {"sys": G.SYS, "V": V, "subject": "történelem", "extra": ""}


# Summed from each response's own usage.cost — the account-level /credits counter lags by
# minutes (the v1 run read $0.037 there; the settled figure was $0.089).
COST = {"usd": 0.0}


async def ai(c, prompt, sys, temp=0.5, maxtok=4000, model=MODEL):
    r = await c.post(OR, headers=H_OR, json={"model": model, "max_tokens": maxtok, "temperature": temp,
        "response_format": {"type": "json_object"}, "usage": {"include": True},
        "messages": [{"role": "system", "content": sys}, {"role": "user", "content": prompt}]}, timeout=180)
    r.raise_for_status()
    body = r.json()
    COST["usd"] += (body.get("usage") or {}).get("cost") or 0
    raw = body["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.splitlines()[1:-1])
    # raw_decode tolerates trailing text after the JSON object (seen with gpt-4o).
    return json.JSONDecoder().raw_decode(raw[raw.index("{"):])[0]


def deep_prompt(cfg, temakor, grade, tema, text_cards, context):
    numbered = "\n".join(f"[{i}] {c.get('heading', '')}: {c.get('body', '')}" for i, c in enumerate(text_cards))
    return (
        f"Tantárgy: {cfg['subject']}. Évfolyam: {grade}. Témakör: „{temakor}”.\nLecke (Téma): „{tema}”.\n\n"
        f"A diák ezeket a SZÖVEG-kártyákat olvassa (0-tól számozva):\n{numbered}\n\n"
        f"A lecke többi része (csak kontextus, ne ismételd): {context}\n\n"
        "FELADAT: „Mesélj még!” MÉLYÍTŐ réteg. MINDEN fenti szöveg-kártyához írj PONTOSAN EGY mélyítő kártyát "
        "(`anchor` = a kártya száma). Ezt akkor látja a diák, ha a kártya alatt a „Mesélj még!” gombra bök, "
        "mert kíváncsi lett — tehát OLYAT kell kapnia, amit a kártyából MÉG NEM tud. A mélyítés:\n"
        "- TILOS a kártya tartalmát vagy példáját újramondani. Minden mélyítés hozzon legalább EGY ÚJ gondolatot "
        "az alábbiak közül: (a) a MIÉRT — a mögöttes ok/mechanizmus, amit a kártya csak kimond; (b) egy "
        "MEGLEPŐ, a józan észnek ellentmondó következmény; (c) egy kis, fejben is követhető SZÁMPÉLDA "
        "évfolyamnak megfelelő, kerek számokkal, ami megmutat valamit, amit a kártya nem.\n"
        f"- Maradjon a(z) {grade}. évfolyam szintjén: mélyebb, de NEM nehezebb matematika. Új képletet vagy "
        "szakszót csak akkor használj, ha szavakkal is elmagyarázod. A fogalmakat PONTOSAN használd (pl. a "
        "gyorsulás nem „gyorsabb sebesség”, a teljesítmény nem gyorsulás).\n"
        "- `heading`: rövid, kíváncsiságot keltő cím (ne a kártya címének megismétlése).\n"
        "- `body`: 4-6 tartalmas, tényszerű mondat, a diákot tegezve.\n"
        "- `did_you_know`: EGY meglepő tény 1-2 mondatban, amely a JELENSÉGRŐL szól (hogyan működik a világ), "
        "NEM rekord, piaci/statisztikai adat, márka, törvény vagy évszám. Ha nincs ilyen, biztosan igaz tény, "
        "hagyd ÜRESEN — az üres mező jobb, mint egy bizonytalan adat.\n"
        "- `think`: egy gondolkodtató kérdés a mindennapokból; `think_answer`: 1-2 mondatos magyarázó válasz "
        "a diákhoz szólva (NE első személyben, mintha a diák válaszolna).\n"
        "- Minden mélyítés MÁS példát használjon — ne ismételd ugyanazt az autót, sportot, eszközt.\n"
        "- Számok magyar formátumban: ezres tagolás szóközzel (20 200 km), tizedesvessző (9,81 m/s²).\n"
        "- Tárgyi pontosság KRITIKUS: inkább legyél általánosabb, mint hogy kitalálj adatot. Ne adj kitalált "
        "személynevet szereplőnek.\n"
        f"{cfg['extra']}\n"
        'JSON: {"cards":[{"type":"deep","anchor":0,"heading":"","body":"","did_you_know":"","think":"","think_answer":""}]}')


def normalize(cards, n_text):
    """One card per anchor, anchors in range, sorted — the player relies on this."""
    by_anchor = {}
    for card in cards if isinstance(cards, list) else []:
        try:
            a = int(card.get("anchor"))
        except (TypeError, ValueError):
            continue
        if 0 <= a < n_text and a not in by_anchor and (card.get("body") or "").strip():
            card["anchor"] = a
            card["type"] = "deep"
            by_anchor[a] = card
    return [by_anchor[a] for a in sorted(by_anchor)]


VERIFY_SYS = ("Szigorú magyar tényellenőr és szakmódszertanos tanár vagy. Itt NEM a tankönyvi egyszerűsítést "
              "bírálod, hanem (1) minden KONKRÉT, ellenőrizhető állítást (szám, évszám, név, rekord, jogszabály, "
              "statisztika, időtartam, „a világ leg-…”) — csak akkor „biztos”, ha BIZTOSAN igaz és nem elavuló; "
              "és (2) a TÉVKÉPZETEKET és pontatlan fogalomhasználatot, amit egy diák rosszul tanulna meg (pl. "
              "fizikában: a „centrifugális erő” mint a kanyarban kifelé toló valódi erő — helyesen: a test a "
              "tehetetlensége miatt egyenesen haladna tovább, a súrlódás adja a befelé mutató erőt; "
              "„gyorsul” = „gyorsabban megy” egyenletes körmozgásnál; a nehezebb test gyorsabban esik; "
              "teljesítmény/energia/erő összekeverése). CSAK érvényes JSON-t adsz vissza.")


async def verify_claims(c, cards):
    """Strict pass for what the subject validators (lenient by design) let through in the POC:
    shaky records/dates/stats/durations AND misconceptions (v2 kept "centrifugal force pushes the
    car outward"). Shaky did_you_know facts are deleted, not generalised — v2's generalising
    left empty husks ("jelentős erők hatnak")."""
    out = await ai(c, "Vizsgáld át az alábbi kártyákat. Sorold fel (a) az ÖSSZES konkrét, ellenőrizhető állítást "
        "és ítéld meg: biztos | hamis | bizonytalan; (b) minden TÉVKÉPZETET vagy pontatlan fogalomhasználatot "
        "(verdict: tevkepzet). A nem „biztos” tételekhez adj `fix` utasítást:\n"
        "- ha a tétel a `did_you_know` mezőben van: a `did_you_know` legyen ÜRES (ne általánosítsd);\n"
        "- tévképzetnél: írd le a HELYES magyarázatot, amivel a mondatot le kell cserélni;\n"
        "- egyéb bizonytalan adatnál: a mondat az adat NÉLKÜL, vagy töröld a mondatot.\n"
        '{"claims":[{"anchor":0,"field":"body|did_you_know|think_answer","claim":"",'
        '"verdict":"biztos|hamis|bizonytalan|tevkepzet","fix":""}]}\n\n'
        f"KÁRTYÁK:\n{json.dumps(cards, ensure_ascii=False)}", VERIFY_SYS, temp=0, maxtok=3500, model=FIX_MODEL)
    bad = [x for x in out.get("claims", []) if x.get("verdict") in ("hamis", "bizonytalan", "tevkepzet")]
    if not bad:
        return cards, []
    fixed = await ai(c, "Alkalmazd az alábbi javításokat a kártyákon. Új számadatot, nevet vagy évszámot NE írj be. "
        "Ha egy `did_you_know` a javítás után már nem tartalmaz konkrét, meglepő információt, legyen ÜRES. "
        "Az `anchor` értékeket, a kulcsokat és a kártyák számát NE változtasd.\n\nJAVÍTÁSOK:\n"
        + "\n".join(f"- [{x.get('anchor')} / {x.get('field', '?')}] „{x.get('claim')}” ({x.get('verdict')}) → "
                    f"{x.get('fix')}" for x in bad)
        + "\n\nKÁRTYÁK:\n" + json.dumps(cards, ensure_ascii=False) + '\n\nJSON: {"cards":[...]}',
        FIX_SYS, temp=0, model=FIX_MODEL)
    return fixed.get("cards", cards), [f"{x.get('verdict')}: {x.get('claim')}" for x in bad]


async def verify_until_clean(c, cards, n_text, rounds=2):
    """The verifier's own rewrite can introduce a new shaky claim (v3: a removed day-length
    fact came back as a different wrong one), so re-verify the fixed cards."""
    removed = []
    for _ in range(rounds):
        cards, bad = await verify_claims(c, cards)
        cards = normalize(cards, n_text)
        removed += bad
        if not bad:
            break
    return cards, removed


async def check(c, V, tema, cards, band):
    blocks = [{"mode": "deep", "content": cards}]
    facts = await V._confirm_facts(c, await V._fact_check(c, tema, blocks))
    appro = await V._appro_check(c, tema, blocks, band)
    return facts, appro


async def fix(c, cards, facts, appro):
    todo = [f"TÁRGYI HIBA: {x.get('claim')} — miért: {x.get('why')} — helyesen: {x.get('fix')}"
            for x in facts if x.get("severity") == "sulyos"]
    todo += [f"{x.get('kind')}: {x.get('detail')} — javaslat: {x.get('suggestion')}"
             for x in appro if x.get("kind") in FIXABLE_APPRO]
    if not todo:
        return cards, []
    out = await ai(c, "Javítsd az alábbi mélyítő kártyákat a felsorolt hibák szerint. A javított állítás legyen "
        "biztosan igaz — ha nem vagy benne biztos, fogalmazd általánosabban vagy hagyd el azt a részt. "
        "Az `anchor` értékeket, a kulcsokat és a kártyák számát NE változtasd.\n\nHIBÁK:\n- "
        + "\n- ".join(todo) + "\n\nKÁRTYÁK:\n" + json.dumps(cards, ensure_ascii=False)
        + '\n\nJSON: {"cards":[...]}', FIX_SYS, temp=0, model=FIX_MODEL)
    return out.get("cards", cards), todo


async def proof(c, cards):
    try:
        out = await ai(c, "Javítsd ki az alábbi JSON szöveges mezőiben a helyesírási, nyelvtani és központozási "
            "hibákat (a névelőt is: „az 1990-es”, nem „a 1990-es”), és írd a számokat magyar formátumban (ezres "
            "tagolás szóközzel, tizedesvessző). NE változtasd a tartalmat, szerkezetet vagy kulcsokat. "
            "CSAK a javított JSON-t add vissza.\n\n"
            + json.dumps({"cards": cards}, ensure_ascii=False),
            "Gondos magyar korrektor vagy. Csak JSON-t adsz vissza.", temp=0)
        return out.get("cards", cards)
    except Exception:
        return cards


async def lesson_deep(c, cfg, topic, L, blocks, reverify=False):
    text_cards = blocks.get("text") or []
    if not text_cards:
        return {"lesson": L, "skipped": "nincs szöveg-kártya"}
    ctx = "; ".join(f"{m}: " + " / ".join(x.get("heading", "") for x in blocks.get(m) or [])
                    for m in ("story", "visual") if blocks.get(m))
    if reverify:
        cards = normalize(blocks.get("deep") or [], len(text_cards))
        if not cards:
            return {"lesson": L, "skipped": "nincs mentett mélyítés"}
        return await guard(c, cfg, topic, L, text_cards, cards)
    for attempt in (1, 2):
        try:
            out = await ai(c, deep_prompt(cfg, topic["title_hu"], topic["grade"], L["title_hu"], text_cards, ctx),
                           cfg["sys"])
            cards = normalize(out.get("cards", []), len(text_cards))
            if len(cards) >= max(1, len(text_cards) - 1):
                break
            print(f"   ⚠ {L['title_hu'][:30]}: csak {len(cards)}/{len(text_cards)} kártya (próba {attempt})")
        except Exception as e:
            print(f"   ⚠ {L['title_hu'][:30]} (próba {attempt}): {e}")
            cards = []
    if not cards:
        return {"lesson": L, "skipped": "generálás sikertelen"}
    return await guard(c, cfg, topic, L, text_cards, cards)


async def guard(c, cfg, topic, L, text_cards, cards):
    V = cfg["V"]
    band = V._band_label(topic["grade"])
    cards, verified = await verify_until_clean(c, cards, len(text_cards))

    facts, appro = await check(c, V, L["title_hu"], cards, band)
    fixed = []
    if any(x.get("severity") == "sulyos" for x in facts) or any(x.get("kind") in FIXABLE_APPRO for x in appro):
        cards, fixed = await fix(c, cards, facts, appro)
        cards, reverified = await verify_until_clean(c, normalize(cards, len(text_cards)), len(text_cards))
        verified += reverified                                    # fixes can add claims too
        facts, appro = await check(c, V, L["title_hu"], cards, band)
    cards = normalize(await proof(c, cards), len(text_cards))
    severe = [x for x in facts if x.get("severity") == "sulyos"]
    print(f"   ✓ {L['title_hu'][:34]}: {len(cards)} mélyítés · kiszűrt állítás {len(verified)} · "
          f"javítva {len(fixed)} · maradt: {len(severe)} súlyos / {len(facts) - len(severe)} csekély tény, "
          f"{len(appro)} egyéb")
    return {"lesson": L, "text": text_cards, "cards": cards, "fixed": fixed, "verified": verified,
            "facts": facts, "appro": appro, "active": not severe}


async def safe_lesson_deep(c, cfg, topic, L, blocks, reverify=False):
    """One lesson failing (bad JSON twice, API error) must not abort the whole Témakör."""
    try:
        return await lesson_deep(c, cfg, topic, L, blocks, reverify)
    except Exception as e:
        print(f"   ⚠ {L['title_hu'][:34]}: {e}")
        return {"lesson": L, "skipped": f"hiba: {e}"}


def report_md(topic, results, cost):
    out = [f"# „Mesélj még!” mélyítés — {topic['title_hu']} ({topic['nat_id']}, {topic['grade']}. évf.)", "",
           f"Generálás: `{MODEL}` · ellenőrzés/javítás: `gpt-4o` · költség: **${cost:.3f}**", ""]
    for r in results:
        L = r["lesson"]
        out += [f"## {L['title_hu']}", ""]
        if r.get("skipped"):
            out += [f"_Kihagyva: {r['skipped']}_", ""]
            continue
        status = "✅ élesítve" if r["active"] else "⛔ NEM élesítve (súlyos tárgyi hiba maradt)"
        out += [f"**Guard rail:** {status} · kiszűrt bizonytalan/hamis állítás: {len(r['verified'])} · "
                f"javított tételek: {len(r['fixed'])} · maradt csekély tény: {len(r['facts'])} · "
                f"egyéb megjegyzés: {len(r['appro'])}", ""]
        for x in r["verified"]:
            out.append(f"- ✂️ kiszűrve ({x})")
        for x in r["fixed"]:
            out.append(f"- 🔧 javítva: {x}")
        for x in r["facts"]:
            out.append(f"- ⚠️ tény ({x.get('severity')}): {x.get('claim')} → {x.get('fix')}")
        for x in r["appro"]:
            out.append(f"- 💬 {x.get('kind')}: {x.get('detail')}")
        out.append("")
        for d in r["cards"]:
            src = r["text"][d["anchor"]]
            out += [f"### Kártya {d['anchor'] + 1}: {src.get('heading', '')}",
                    f"> {src.get('body', '')}", "",
                    f"**🔎 {d.get('heading', '')}**", "", d.get("body", ""), ""]
            if d.get("did_you_know"):
                out += [f"💡 **Tudtad?** {d['did_you_know']}", ""]
            if d.get("think"):
                out += [f"🤔 **Gondolkodj!** {d['think']}", f"_Válasz: {d.get('think_answer', '')}_", ""]
    return "\n".join(out)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nat-id", required=True, help="curriculum_topics.nat_id, e.g. PHYS-78-03")
    ap.add_argument("--dry-run", action="store_true", help="generate + check, but don't write to the DB")
    ap.add_argument("--reverify", action="store_true",
                    help="re-run the guard rail on the SAVED deep cards (no regeneration)")
    args = ap.parse_args()
    cfg = subject_cfg(args.nat_id)

    async with httpx.AsyncClient() as c:
        t = (await c.get(f"{SB}/rest/v1/curriculum_topics?nat_id=eq.{args.nat_id}&select=id,nat_id,title_hu,grade",
                         headers=H_SB)).json()
        if not t:
            print(f"⚠ topic {args.nat_id} not found"); return
        topic = t[0]
        lessons = (await c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{topic['id']}"
                               f"&select=id,title_hu&order=order_index", headers=H_SB)).json()
        rows = (await c.get(f"{SB}/rest/v1/content_blocks?topic_id=eq.{topic['id']}&scope=eq.lesson"
                            f"&mode=in.(text,story,visual,deep)&select=lesson_id,mode,content,is_active",
                            headers=H_SB)).json()
        blocks = {}
        for b in rows:
            if b["is_active"] or b["mode"] == "deep":        # an inactive deep block is re-checkable
                blocks.setdefault(b["lesson_id"], {})[b["mode"]] = b["content"]

        print(f"\n🔎 {topic['title_hu']} — {len(lessons)} Téma")
        results = await asyncio.gather(*(safe_lesson_deep(c, cfg, topic, L, blocks.get(L["id"], {}), args.reverify)
                                         for L in lessons))
        cost = COST["usd"]

        if not args.dry_run:
            for r in results:
                if r.get("skipped"):
                    continue
                lid = r["lesson"]["id"]
                await c.request("DELETE", f"{SB}/rest/v1/content_blocks?lesson_id=eq.{lid}&mode=eq.deep", headers=H_SB)
                await c.post(f"{SB}/rest/v1/content_blocks", headers={**H_SB, "Prefer": "return=minimal"}, json={
                    "lesson_id": lid, "topic_id": topic["id"], "mode": "deep", "level": "emelt", "scope": "lesson",
                    "content": r["cards"], "review_status": "approved" if r["active"] else "pending",
                    "is_active": r["active"]})
        path = os.path.join(EXPORTS, f"{args.nat_id}_deep_dive_review.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report_md(topic, results, cost))
        print(f"\n💰 költség: ${cost:.3f}   📝 {os.path.relpath(path)}"
              f"{'   (dry run — nem mentve)' if args.dry_run else ''}")


if __name__ == "__main__":
    asyncio.run(main())
