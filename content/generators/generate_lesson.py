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
        "default_model": "anthropic/claude-3-5-haiku",   # cheap + fast; swap to claude-3-5-sonnet for quality
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
    "hu": """Te egy tapasztalt magyar középiskolai pedagógus és tananyagfejlesztő vagy.
Vonzó, életkornak megfelelő leckéket készítesz 5-12. osztályos tanulóknak.
Minden tartalom legyen tényszerűen pontos, igazodjon a Magyar NAT 2020 tantervhez,
és pedagógiailag megalapozott. Írj érthető, lebilincselő stílusban, a célkorosztálynak megfelelően.
CSAK érvényes JSON-t válaszolj — semmi markdown jelölés, semmi magyarázat a JSON-on kívül.""",

    "en": """You are an expert Hungarian secondary school educator and curriculum writer.
You create engaging, age-appropriate lesson content for students grades 5-12.
All content must be factually accurate, aligned with the Hungarian NAT 2020 curriculum,
and pedagogically sound. Write in a clear, engaging style appropriate for the target grade.
Respond ONLY with valid JSON — no markdown fences, no explanation outside the JSON.""",
}


def prompt_for_mode(topic_title: str, topic_title_hu: str, nat_id: str, grade: int, mode: str, lang: str = "hu") -> str:
    age = grade + 5

    if lang == "hu":
        grade_context = f"{grade}. osztályos tanulók (kb. {age} évesek)"
        title_to_use = topic_title_hu
        lang_instruction = "Minden szöveges tartalmat MAGYAR NYELVEN írj."
    else:
        grade_context = f"Grade {grade} students (age ~{age})"
        title_to_use = topic_title
        lang_instruction = "Write all text content in ENGLISH."

    base = f"""Témakör: „{title_to_use}" (NAT azonosító: {nat_id})
Célközönség: {grade_context}
Nyelv: {lang_instruction}"""

    if mode == "text":
        if lang == "hu":
            return f"""{base}

Készíts egy strukturált SZÖVEGES leckét 4-6 kártyával. Minden kártya egy-egy összefüggő fogalmat dolgoz fel.
Adj vissza JSON-t:
{{
  "title": "a lecke címe magyarul",
  "cards": [
    {{
      "type": "text",
      "heading": "rövid fejléc",
      "body": "3-5 mondat, amely egyértelműen elmagyarázza ezt a fogalmat {grade_context} számára. Tényszerű, közvetlen, oktatási jellegű.",
      "key_term": "opcionális: egy kiemelendő kulcsfogalom"
    }}
  ]
}}"""
        else:
            return f"""{base}

Create a structured TEXT lesson with 4-6 cards. Each card is one focused concept.
Return JSON:
{{
  "title": "lesson title",
  "cards": [
    {{
      "type": "text",
      "heading": "short heading",
      "body": "3-5 sentences explaining this concept clearly for {grade_context}. Factual, direct, educational.",
      "key_term": "optional: one key term to highlight"
    }}
  ]
}}"""

    elif mode == "story":
        if lang == "hu":
            return f"""{base}

Készíts egy TÖRTÉNET-leckét — ugyanazok a tények, narratív formában elmesélve. 4-5 kártya.
Helyezd a tanulót „az esemény közepébe". Használj élénk, de történelmileg pontos részleteket.
Adj vissza JSON-t:
{{
  "title": "a lecke címe magyarul",
  "cards": [
    {{
      "type": "story",
      "heading": "rövid fejléc",
      "body": "3-5 mondat narratív elbeszélés. Jelen idő. Magával ragadó, de tényszerű.",
      "mood": "egy szó: feszült / drámai / kíváncsi / reményteljes / komoly"
    }}
  ]
}}"""
        else:
            return f"""{base}

Create a STORY lesson — same facts, told as a narrative. 4-5 story cards.
Put the student 'in the moment'. Use vivid but historically accurate detail.
Return JSON:
{{
  "title": "lesson title",
  "cards": [
    {{
      "type": "story",
      "heading": "short heading",
      "body": "3-5 sentences of narrative storytelling. Present tense. Immersive but factual.",
      "mood": "one word: tense / dramatic / curious / hopeful / solemn"
    }}
  ]
}}"""

    elif mode == "visual":
        if lang == "hu":
            return f"""{base}

Készíts egy VIZUÁLIS leckét — írd le, mit látna a tanuló egy diagramon, térképen vagy illusztráción.
4-5 kártya, mindegyik egy-egy vizuális elemet ír le elég részletesen ahhoz, hogy a kép nélkül is érthető legyen.
Adj vissza JSON-t:
{{
  "title": "a lecke címe magyarul",
  "cards": [
    {{
      "type": "visual",
      "heading": "rövid fejléc",
      "visual_type": "idővonal | térkép | diagram | arckép | grafikon",
      "description": "2-3 mondat, amely pontosan leírja, mit mutat ez a vizuális elem és mire érdemes figyelni.",
      "caption": "egy mondatos képaláírás, ahogyan a kép alatt szerepelne"
    }}
  ]
}}"""
        else:
            return f"""{base}

Create a VISUAL lesson — describe what a student would SEE in a diagram, map, or illustration.
4-5 cards, each describing one visual element clearly enough to understand without the image.
Return JSON:
{{
  "title": "lesson title",
  "cards": [
    {{
      "type": "visual",
      "heading": "short heading",
      "visual_type": "timeline | map | diagram | portrait | chart",
      "description": "2-3 sentences describing exactly what this visual shows and what to notice.",
      "caption": "one-sentence caption as it would appear under the image"
    }}
  ]
}}"""

    elif mode == "quiz":
        if lang == "hu":
            return f"""{base}

Készíts egy KVÍZT 4 kérdéssel, amelyek a témakör megértését tesztelik.
Változatos kérdéstípusokat használj. Minden helyes válaszhoz adj rövid magyarázatot.
Adj vissza JSON-t:
{{
  "title": "a lecke címe magyarul",
  "cards": [
    {{
      "type": "quiz",
      "question_type": "multiple_choice | true_false",
      "question": "egyértelmű kérdés szövege",
      "options": ["A) lehetőség", "B) lehetőség", "C) lehetőség", "D) lehetőség"],
      "correct": "A",
      "explanation": "1-2 mondat, amely elmagyarázza, miért helyes ez, és miért helytelenek a többiek."
    }}
  ]
}}"""
        else:
            return f"""{base}

Create a QUIZ with 4 questions testing understanding of this topic.
Mix question types. Include a short explanation for each correct answer.
Return JSON:
{{
  "title": "lesson title",
  "cards": [
    {{
      "type": "quiz",
      "question_type": "multiple_choice | true_false",
      "question": "clear question text",
      "options": ["A) option", "B) option", "C) option", "D) option"],
      "correct": "A",
      "explanation": "1-2 sentences explaining why this is correct and what makes the others wrong."
    }}
  ]
}}"""

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
        "max_tokens": 2000,
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


async def save_lesson(topic_id: str, mode: str, content: dict, dry_run: bool = False) -> None:
    payload = {
        "topic_id": topic_id,
        "mode": mode,
        "title": content.get("title", f"{mode.title()} Lesson"),
        "content": content.get("cards", []),
        "generated_by": "ai",
        "review_status": "pending",
        "is_active": False,
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

async def generate_for_topic(topic: dict, modes: list, dry_run: bool, provider_cfg: dict, api_key: str, model: str, lang: str = "hu") -> None:
    print(f"\n📚 [{topic['nat_id']}] {topic['title_hu']} (Grade {topic['grade']})")

    async with httpx.AsyncClient() as client:
        for mode in modes:
            print(f"  → {mode}...", end=" ", flush=True)
            try:
                prompt = prompt_for_mode(
                    topic["title"], topic["title_hu"],
                    topic["nat_id"], topic["grade"], mode, lang
                )
                content = await call_ai(prompt, provider_cfg, api_key, model, client, lang)
                print(f"✓ ({len(content.get('cards', []))} cards)")
                await save_lesson(topic["id"], mode, content, dry_run)
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
        await generate_for_topic(topic, modes, args.dry_run, provider_cfg, api_key, model, args.lang)

    print("\n✅ Done.")


if __name__ == "__main__":
    asyncio.run(main())
