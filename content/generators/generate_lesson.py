"""
Turul Academy — Lesson Content Generator
=========================================
Generates all 4 lesson modes (text, story, visual, quiz) for any NAT topic.
Uses Claude via the Anthropic API.

Usage:
    python generate_lesson.py --nat-id HIST-G7-2.4 --dry-run
    python generate_lesson.py --nat-id HIST-G7-2.4
    python generate_lesson.py --subject HU-NAT-HISTORY-2020 --grade 7
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
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# ─── PROMPTS ─────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert Hungarian secondary school educator and curriculum writer.
You create engaging, age-appropriate lesson content for students grades 5-12.
All content must be factually accurate, aligned with the Hungarian NAT 2020 curriculum,
and pedagogically sound. Write in a clear, engaging style appropriate for the target grade.
Respond ONLY with valid JSON — no markdown fences, no explanation outside the JSON."""


def prompt_for_mode(topic_title: str, topic_title_hu: str, nat_id: str, grade: int, mode: str) -> str:
    age = grade + 5
    grade_context = f"Grade {grade} students (age ~{age})"

    base = f"""Topic: "{topic_title}" ("{topic_title_hu}")
NAT ID: {nat_id}
Target audience: {grade_context}"""

    if mode == "text":
        return f"""{base}

Create a structured TEXT lesson with 4-6 cards. Each card is one focused concept.
Return JSON:
{{
  "title": "lesson title in English",
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
        return f"""{base}

Create a STORY lesson — same facts, told as a narrative. 4-5 story cards.
Put the student 'in the moment'. Use vivid but historically accurate detail.
Return JSON:
{{
  "title": "lesson title in English",
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
        return f"""{base}

Create a VISUAL lesson — describe what a student would SEE in a diagram, map, or illustration.
4-5 cards, each describing one visual element clearly enough to understand without the image.
Return JSON:
{{
  "title": "lesson title in English",
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
        return f"""{base}

Create a QUIZ with 4 questions testing understanding of this topic.
Mix question types. Include a short explanation for each correct answer.
Return JSON:
{{
  "title": "lesson title in English",
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


# ─── API CALLS ───────────────────────────────────────────────

async def call_claude(prompt: str, client: httpx.AsyncClient) -> dict:
    """Call Claude claude-opus-4-5 to generate lesson content."""
    resp = await client.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-opus-4-5",
            "max_tokens": 2000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    raw = resp.json()["content"][0]["text"]
    return json.loads(raw)


async def get_topics(nat_id: str = None, subject_code: str = None, grade: int = None) -> list:
    """Fetch topics from Supabase."""
    params = {"select": "id,nat_id,title,title_hu,grade"}
    if nat_id:
        params["nat_id"] = f"eq.{nat_id}"
    if grade:
        params["grade"] = f"eq.{grade}"
    if subject_code:
        # join via subject
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
    """Save generated lesson to Supabase (inactive until teacher approves)."""
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
        # Upsert — replace if same topic+mode exists
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/lessons",
            headers={**HEADERS, "Prefer": "return=representation,resolution=merge-duplicates"},
            json=payload,
        )
        if resp.status_code not in (200, 201):
            print(f"  ⚠️  Save failed ({resp.status_code}): {resp.text[:200]}")
        else:
            print(f"  ✅ Saved {mode} lesson (pending review)")


# ─── MAIN ────────────────────────────────────────────────────

async def generate_for_topic(topic: dict, modes: list, dry_run: bool) -> None:
    print(f"\n📚 Generating: [{topic['nat_id']}] {topic['title']} (Grade {topic['grade']})")

    async with httpx.AsyncClient() as client:
        for mode in modes:
            print(f"  → {mode}...", end=" ", flush=True)
            try:
                prompt = prompt_for_mode(
                    topic["title"], topic["title_hu"],
                    topic["nat_id"], topic["grade"], mode
                )
                content = await call_claude(prompt, client)
                print(f"✓ ({len(content.get('cards', []))} cards)")
                await save_lesson(topic["id"], mode, content, dry_run)
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parse error: {e}")
            except Exception as e:
                print(f"⚠️  Error: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Generate Turul Academy lesson content")
    parser.add_argument("--nat-id",   help="Single topic NAT ID e.g. HIST-G7-2.4")
    parser.add_argument("--subject",  help="Subject code e.g. HU-NAT-HISTORY-2020")
    parser.add_argument("--grade",    type=int, help="Filter by grade")
    parser.add_argument("--modes",    default="text,story,visual,quiz", help="Comma-separated modes")
    parser.add_argument("--dry-run",  action="store_true", help="Print output without saving")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY not set in backend/.env")
        return

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
        await generate_for_topic(topic, modes, args.dry_run)

    print("\n✅ Done.")


if __name__ == "__main__":
    asyncio.run(main())
