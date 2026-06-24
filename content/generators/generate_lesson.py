"""
Turul Academy — Lesson Content Generator
=========================================
Generates all 4 lesson modes (text, story, visual, quiz) for any NAT topic.
Supports multiple AI providers via a unified OpenAI-compatible interface.

Supported providers (set PROVIDER or pass --provider):
  openrouter  → OpenRouter (access to Claude, GPT-4o, Gemini, Deepseek, etc.)
  openai      → OpenAI directly (GPT-4o)
  deepseek    → Deepseek (deepseek-chat)
  moonshot    → Kimi / Moonshot AI
  gemini      → Google Gemini (via openai-compat endpoint)

Usage:
    python generate_lesson.py --nat-id HIST-G7-2.4 --dry-run
    python generate_lesson.py --nat-id HIST-G7-2.4 --provider openrouter
    python generate_lesson.py --subject HU-NAT-HISTORY-2020 --grade 7 --provider deepseek
"""

import asyncio
import argparse
import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../backend/.env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# ─── PROVIDER CONFIG ─────────────────────────────────────────

PROVIDERS = {
    "openrouter": {
        "base_url":    "https://openrouter.ai/api/v1/chat/completions",
        "env_key":     "OPENROUTER_API_KEY",
        "default_model": "openai/gpt-4o-mini",   # mid-tier: good HU, strong instruction-following, cheap; override with --model
        "extra_headers": {
            "HTTP-Referer": "https://turul.academy",
            "X-Title": "Turul Academy",
        },
    },
    "openai": {
        "base_url":    "https://api.openai.com/v1/chat/completions",
        "env_key":     "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
    },
    "deepseek": {
        "base_url":    "https://api.deepseek.com/v1/chat/completions",
        "env_key":     "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "moonshot": {
        "base_url":    "https://api.moonshot.cn/v1/chat/completions",
        "env_key":     "MOONSHOT_API_KEY",
        "default_model": "moonshot-v1-8k",
    },
    "gemini": {
        # Google exposes an OpenAI-compat endpoint since late 2024
        "base_url":    "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "env_key":     "GEMINI_API_KEY",
        "default_model": "gemini-2.0-flash",
    },
}

def detect_provider() -> str:
    """Auto-detect which provider key is available in env."""
    preferred_order = ["openrouter", "openai", "deepseek", "gemini", "moonshot"]
    for p in preferred_order:
        if os.getenv(PROVIDERS[p]["env_key"]):
            return p
    return "openrouter"   # will fail loudly if key missing


# ─── PROMPTS ─────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "hu": """Te egy tapasztalt magyar pedagógus és tananyagfejlesztő vagy.
Vonzó, életkornak megfelelő leckéket készítesz 5-12. osztályos tanulóknak.

KÖTELEZŐ SZABÁLYOK:
- Minden szöveg KIZÁRÓLAG magyar nyelven. TILOS idegen (angol) szavakat vagy kifejezéseket használni.
- A tartalom legyen tényszerűen pontos, konkrét (nevek, évszámok, helyszínek), és igazodjon a Magyar NAT 2020 elvárásaihoz a megadott évfolyamon.
- Légy alapos: ne csak egy-két mondat, hanem érdemi, tartalmas magyarázat.
- CSAK érvényes JSON-t válaszolj — semmi markdown jelölés, semmi magyarázat a JSON-on kívül.""",

    "en": """You are an expert Hungarian curriculum writer creating engaging lessons for grades 5-12.

MANDATORY RULES:
- Write ALL text in clear English; do not slip in words from other languages.
- Be factually accurate and concrete (names, dates, places), aligned with the Hungarian NAT 2020 for the given grade.
- Be substantial: real explanation, not one or two thin sentences.
- Respond ONLY with valid JSON — no markdown fences, no text outside the JSON.""",
}


# ─── CONTENT SPINE ───────────────────────────────────────────
# One shared outline per topic. Every mode (text/story/visual/quiz) is then
# generated FROM this same spine, so all four cover the same material — each
# mode is a complete standalone treatment of the topic, and the quiz only ever
# tests points that the lessons actually teach.

def spine_prompt(title: str, nat_id: str, grade: int, lang: str) -> str:
    age = grade + 5
    if lang == "hu":
        return f"""Témakör: „{title}" (NAT azonosító: {nat_id})
Célközönség: {grade}. osztályos tanulók (kb. {age} évesek)

Sorolj fel 6-8 KULCSFONTOSSÁGÚ tanulási pontot, amelyet egy {grade}. osztályos tanulónak a Magyar NAT 2020 szerint EBBŐL a témakörből ismernie kell. Logikus, tanórai sorrendben. Mindegyik egy tömör, konkrét mondat (név/évszám/fogalom, ahol releváns). Ez a lista lefedi a témakör teljes elvárt tananyagát.

Adj vissza JSON-t:
{{ "objectives": ["első pont", "második pont", "..."] }}"""
    return f"""Topic: "{title}" (NAT id: {nat_id})
Audience: grade {grade} students (age ~{age})

List 6-8 KEY learning points a grade {grade} student must know about this topic per the Hungarian NAT 2020, in logical teaching order. Each is one concise, concrete sentence. Together they cover the full expected scope.

Return JSON: {{ "objectives": ["first point", "second point", "..."] }}"""


def prompt_for_mode(topic_title: str, topic_title_hu: str, nat_id: str, grade: int, mode: str, spine: list, lang: str = "hu") -> str:
    age = grade + 5
    hu = lang == "hu"
    title_to_use = topic_title_hu if hu else topic_title
    grade_context = f"{grade}. osztályos tanulók (kb. {age} évesek)" if hu else f"grade {grade} students (age ~{age})"
    points_block = "\n".join(f"{i+1}. {p}" for i, p in enumerate(spine))

    base = (f"""Témakör: „{title_to_use}" (NAT azonosító: {nat_id})
Célközönség: {grade_context}

A lecke a következő tanulási pontokra épül — ezeket KELL lefednie, ugyanebben a sorrendben:
{points_block}"""
    if hu else
        f"""Topic: "{title_to_use}" (NAT id: {nat_id})
Audience: {grade_context}

The lesson is built on these learning points — it MUST cover all of them, in this order:
{points_block}""")

    if mode == "text":
        return base + ("""

Készíts egy strukturált SZÖVEGES leckét. MINDEN tanulási ponthoz tartozzon egy kártya (tehát annyi kártya, ahány pont).
Minden kártya:
- "heading": rövid, lényegre törő cím
- "body": 4-6 tartalmas, összefüggő mondat, amely ALAPOSAN kifejti az adott pontot {grade_context} szintjén — konkrét tényekkel, nevekkel, évszámokkal. Ne legyen felületes.
- "key_term": egy kiemelendő kulcsfogalom
Adj vissza JSON-t: {{ "title": "a lecke címe", "cards": [ {{ "type": "text", "heading": "", "body": "", "key_term": "" }} ] }}""".replace("{grade_context}", grade_context)
        if hu else """

Create a structured TEXT lesson. One card PER learning point.
Each card: "heading" (short), "body" (4-6 substantial sentences thoroughly explaining that point with concrete facts/names/dates), "key_term".
Return JSON: { "title": "lesson title", "cards": [ { "type": "text", "heading": "", "body": "", "key_term": "" } ] }""")

    if mode == "story":
        return base + ("""

Készíts egy TÖRTÉNET-leckét: meséld el a témakör anyagát (mind a fenti pontokat) lebilincselő történelmi elbeszélésként, amelynek GERINCE az OK-OKOZAT. Mutasd meg, hogyan vezetett egyik esemény, döntés vagy feszültség a másikhoz, és hogyan vált valami elkerülhetetlenné — minden kártya egy lépés ebben a láncban, a tét egyre nagyobb. A száraz tényeket keltsd életre érzékletes, EMBERI pillanatokkal (egy döntés súlya, a lövészárkok hangulata, egy tömeg reménye vagy félelme), hogy a történet éljen.

FONTOS stílusszabályok:
- NE találj ki kitalált, megnevezett szereplőt vagy fiktív személyes részletet (pl. kitalált katona, kitalált napló, „anyám", „a barátom, János"). KIZÁRÓLAG valós történelmi szereplők, valós nevek, évszámok, helyszínek. Az emberi pillanatok valós, dokumentált helyzeteken alapuljanak (pl. „a frontkatonák", „a szarajevói tömeg") — ne kitaláción.
- NE szólítsd meg az olvasót, KERÜLD a „képzeld el, hogy ott vagy" fordulatot. Harmadik személyben írj.
- Az elbeszélés legyen élő és emberi, DE pontos és tárgyilagos — az ok-okozati ív vigye előre.
- Haladj végig minden tanulási ponton, a sorrendet követve. 6-8 kártya, mindegyik egy fordulópont a láncban.

Minden kártya: "heading" (a fordulópont rövid címe), "body" (4-6 mondat: oksági ívet hordozó, élénk, mégis tényszerű elbeszélés), "mood" (egy szó: feszült / drámai / kíváncsi / reményteljes / komoly).
Adj vissza JSON-t: {{ "title": "a lecke címe", "cards": [ {{ "type": "story", "heading": "", "body": "", "mood": "" }} ] }}"""
        if hu else """

Create a STORY lesson: tell the material (all points above) as a gripping historical narrative whose BACKBONE is CAUSE AND EFFECT. Show how one event, decision or tension led to the next and how something became inevitable — each card a step in that chain, the stakes rising. Bring the dry facts to life with vivid, HUMAN moments (the weight of a decision, the mood of the trenches, a crowd's hope or fear) so the story breathes.

IMPORTANT style rules:
- Do NOT invent named characters or fictional personal detail (no made-up soldier, diary, "my mother", "my friend János"). ONLY real historical figures, real names, dates, places. Ground human moments in real, documented situations (e.g. "the front-line soldiers", "the Sarajevo crowd"), never invention.
- Do NOT address the reader; avoid "imagine you are there". Third person.
- Alive and human, but accurate and objective — let the causal arc drive it forward.
- Move through every learning point in order. 6-8 cards, each a turning point in the chain.
Each card: "heading" (turning-point title), "body" (4-6 vivid yet factual sentences carrying the causal arc), "mood" (tense/dramatic/curious/hopeful/solemn).
Return JSON: { "title": "lesson title", "cards": [ { "type": "story", "heading": "", "body": "", "mood": "" } ] }""")

    if mode == "visual":
        return base + ("""

Készíts egy VIZUÁLIS leckét: MINDEN ponthoz írj le egy-egy szemléltető vizuális elemet (idővonal, térkép, diagram, arckép, grafikon), amely segít megérteni az adott pontot. A leírás legyen elég részletes ahhoz, hogy kép nélkül is tanulható legyen. Annyi kártya, ahány pont.
Minden kártya: "heading", "visual_type" (idővonal | térkép | diagram | arckép | grafikon), "description" (3-4 mondat, mit mutat és mire figyeljünk), "caption" (egymondatos képaláírás).
Adj vissza JSON-t: {{ "title": "a lecke címe", "cards": [ {{ "type": "visual", "heading": "", "visual_type": "", "description": "", "caption": "" }} ] }}"""
        if hu else """

Create a VISUAL lesson: for EACH point, describe one illustrative visual (timeline/map/diagram/portrait/chart) detailed enough to learn from without the image. One card per point.
Each card: "heading", "visual_type", "description" (3-4 sentences), "caption".
Return JSON: { "title": "lesson title", "cards": [ { "type": "visual", "heading": "", "visual_type": "", "description": "", "caption": "" } ] }""")

    if mode == "quiz":
        return base + ("""

Készíts egy KVÍZT 5 kérdéssel. KIZÁRÓLAG a fenti tanulási pontokból kérdezz — SOHA ne kérdezz olyasmit, ami nem szerepel a pontok között. Lehetőleg minden fontos pontot érints. Változatos kérdéstípusok.
Minden kérdés: "question_type" (multiple_choice | true_false), "question", "options" (["A) ...","B) ...","C) ...","D) ..."]), "correct" (a helyes betű), "explanation" (1-2 mondat: miért helyes, és miért nem a többi).
Adj vissza JSON-t: {{ "title": "a lecke címe", "cards": [ {{ "type": "quiz", "question_type": "", "question": "", "options": [], "correct": "", "explanation": "" }} ] }}"""
        if hu else """

Create a QUIZ of 5 questions. Test ONLY the learning points above — never ask about anything not in those points. Cover the important points. Mix question types.
Each: "question_type" (multiple_choice|true_false), "question", "options" (A-D), "correct" (letter), "explanation" (1-2 sentences).
Return JSON: { "title": "lesson title", "cards": [ { "type": "quiz", "question_type": "", "question": "", "options": [], "correct": "", "explanation": "" } ] }""")

    raise ValueError(f"Unknown mode: {mode}")



# ─── AI CALL ─────────────────────────────────────────────────

def strip_json_fences(raw: str) -> str:
    """Some models wrap output in ```json ... ``` despite instructions."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return raw.strip()


async def call_ai(prompt: str, provider_cfg: dict, api_key: str, model: str, client: httpx.AsyncClient, lang: str = "hu") -> dict:
    request_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if "extra_headers" in provider_cfg:
        request_headers.update(provider_cfg["extra_headers"])

    payload = {
        "model": model,
        "max_tokens": 4000,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPTS[lang]},
            {"role": "user",   "content": prompt},
        ],
    }

    resp = await client.post(
        provider_cfg["base_url"],
        headers=request_headers,
        json=payload,
        timeout=90.0,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    return json.loads(strip_json_fences(raw))


PROOFREAD_SYSTEM = {
    "hu": "Te egy gondos, profi magyar nyelvi lektor (korrektor) vagy. Kizárólag a nyelvi helyességet javítod.",
    "en": "You are a careful professional proofreader. You fix only language correctness.",
}


async def proofread(content: dict, provider_cfg: dict, api_key: str, model: str, client: httpx.AsyncClient, lang: str = "hu") -> dict:
    """Grammar / spelling / punctuation pass over a lesson's text fields.
    Preserves meaning, style, JSON structure and keys — only fixes correctness."""
    if lang == "hu":
        instruction = (
            "Javítsd ki az alábbi JSON szöveges mezőiben a helyesírási, nyelvtani, "
            "központozási és elgépelési hibákat. NE változtasd meg a tartalmat, a jelentést, "
            "a stílust, a JSON szerkezetét vagy a kulcsokat — kizárólag a magyar szöveg "
            "helyességét. Ha nincs hiba, add vissza változatlanul. CSAK a javított JSON-t add vissza.\n\n"
        )
    else:
        instruction = (
            "Fix spelling, grammar, punctuation and typos in the text fields of the JSON below. "
            "Do NOT change content, meaning, style, JSON structure or keys — only correctness. "
            "Return ONLY the corrected JSON.\n\n"
        )

    request_headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if "extra_headers" in provider_cfg:
        request_headers.update(provider_cfg["extra_headers"])

    payload = {
        "model": model,
        "max_tokens": 4000,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": PROOFREAD_SYSTEM[lang]},
            {"role": "user", "content": instruction + json.dumps(content, ensure_ascii=False)},
        ],
    }
    resp = await client.post(provider_cfg["base_url"], headers=request_headers, json=payload, timeout=90.0)
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    return json.loads(strip_json_fences(raw))


# ─── SUPABASE ────────────────────────────────────────────────

async def get_topics(nat_id: str = None, subject_code: str = None, grade: int = None) -> list:
    params = {"select": "id,nat_id,title,title_hu,grade"}
    if nat_id:
        params["nat_id"] = f"eq.{nat_id}"
    if grade:
        params["grade"] = f"eq.{grade}"
    if subject_code:
        params["select"] = "id,nat_id,title,title_hu,grade,subject:curriculum_subjects!subject_id(code)"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/curriculum_topics",
            headers=HEADERS,
            params=params,
        )
        resp.raise_for_status()
        topics = resp.json()

    if subject_code:
        topics = [t for t in topics if t.get("subject", {}).get("code") == subject_code]

    return topics


async def save_lesson(topic_id: str, mode: str, content: dict, dry_run: bool = False, activate: bool = False) -> None:
    payload = {
        "topic_id": topic_id,
        "mode": mode,
        "title": content.get("title", f"{mode.title()} Lesson"),
        "content": content.get("cards", []),
        "generated_by": "ai",
        "review_status": "approved" if activate else "pending",
        "is_active": activate,
    }

    if dry_run:
        print(f"\n{'='*60}")
        print(f"[DRY RUN] Would save {mode} lesson:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/lessons?on_conflict=topic_id,mode",
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"},
            json=payload,
        )
        if resp.status_code not in (200, 201):
            print(f"  ⚠️  Save failed ({resp.status_code}): {resp.text[:200]}")
        else:
            print(f"  ✅ Saved {mode} lesson (pending review)")


# ─── MAIN ────────────────────────────────────────────────────

async def generate_for_topic(topic: dict, modes: list, dry_run: bool, provider_cfg: dict, api_key: str, model: str, lang: str = "hu", activate: bool = False) -> None:
    print(f"\n📚 [{topic['nat_id']}] {topic['title_hu']} (Grade {topic['grade']})")

    title = topic["title_hu"] if lang == "hu" else topic["title"]

    async with httpx.AsyncClient() as client:
        # Pass 1 — build the shared content spine (the NAT-aligned learning points)
        print("  → spine...", end=" ", flush=True)
        try:
            spine_data = await call_ai(spine_prompt(title, topic["nat_id"], topic["grade"], lang),
                                       provider_cfg, api_key, model, client, lang)
            spine = spine_data.get("objectives", [])
            if not spine:
                print("⚠️  empty spine — skipping topic")
                return
            print(f"✓ ({len(spine)} learning points)")
        except Exception as e:
            print(f"⚠️  spine failed: {e} — skipping topic")
            return

        # Pass 2 — generate each mode FROM the shared spine
        for mode in modes:
            print(f"  → {mode}...", end=" ", flush=True)
            try:
                prompt = prompt_for_mode(
                    topic["title"], topic["title_hu"],
                    topic["nat_id"], topic["grade"], mode, spine, lang
                )
                content = await call_ai(prompt, provider_cfg, api_key, model, client, lang)
                # Grammar/spelling pass before publishing; keep original if proofread fails
                try:
                    content = await proofread(content, provider_cfg, api_key, model, client, lang)
                    print(f"✓ ({len(content.get('cards', []))} cards, proofread)")
                except Exception as pe:
                    print(f"✓ ({len(content.get('cards', []))} cards, ⚠ proofread skipped: {pe})")
                await save_lesson(topic["id"], mode, content, dry_run, activate)
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parse error: {e}")
            except httpx.HTTPStatusError as e:
                print(f"⚠️  API error {e.response.status_code}: {e.response.text[:150]}")
            except Exception as e:
                print(f"⚠️  Error: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Generate Turul Academy lesson content")
    parser.add_argument("--nat-id",   help="Single topic NAT ID e.g. HIST-G7-2.4")
    parser.add_argument("--subject",  help="Subject code e.g. HU-NAT-HISTORY-2020")
    parser.add_argument("--grade",    type=int, help="Filter by grade")
    parser.add_argument("--modes",    default="text,story,visual,quiz", help="Comma-separated modes")
    parser.add_argument("--dry-run",  action="store_true", help="Print output without saving")
    parser.add_argument("--activate", action="store_true", help="Save lessons as active + approved (publish immediately)")
    parser.add_argument("--provider", choices=list(PROVIDERS.keys()),
                        help="AI provider (auto-detected from env if omitted)")
    parser.add_argument("--model",    help="Override model name (e.g. gpt-4o, deepseek-reasoner)")
    parser.add_argument("--lang",     default="hu", choices=["hu", "en"],
                        help="Language for generated content (default: hu)")
    args = parser.parse_args()

    # Resolve provider
    provider_name = args.provider or detect_provider()
    provider_cfg  = PROVIDERS[provider_name]
    api_key       = os.getenv(provider_cfg["env_key"])
    model         = args.model or provider_cfg["default_model"]

    if not api_key:
        print(f"❌ {provider_cfg['env_key']} not set in backend/.env")
        print(f"   Available providers: {', '.join(PROVIDERS.keys())}")
        print(f"   Set one of: {', '.join(p['env_key'] for p in PROVIDERS.values())}")
        return

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in backend/.env")
        return

    print(f"🤖 Provider: {provider_name} | Model: {model} | Lang: {args.lang}")

    modes = [m.strip() for m in args.modes.split(",")]

    if args.nat_id:
        topics = await get_topics(nat_id=args.nat_id)
    elif args.subject:
        topics = await get_topics(subject_code=args.subject, grade=args.grade)
    else:
        print("❌ Provide --nat-id or --subject")
        return

    if not topics:
        print("❌ No topics found matching your filter")
        return

    print(f"Found {len(topics)} topic(s). Generating {len(modes)} mode(s) each...")
    if args.dry_run:
        print("(DRY RUN — nothing will be saved)\n")

    for topic in topics:
        await generate_for_topic(topic, modes, args.dry_run, provider_cfg, api_key, model, args.lang, args.activate)

    print("\n✅ Done.")


if __name__ == "__main__":
    asyncio.run(main())
