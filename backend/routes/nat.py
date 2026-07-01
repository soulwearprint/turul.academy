"""
Read routes for the NAT 3-tier content model (curriculum_topics → curriculum_lessons
(Témák) → content_blocks). Distinct from the legacy `lessons` table the live app uses.

Reads use the service role (trusted backend) so the still-hidden NAT topics
(is_active=false, pre-cutover) are served for preview; content_blocks themselves
are is_active=true. Mirrors the service-role pattern documented in core/db.py.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from core.db import db_get

router = APIRouter(prefix="/api/nat", tags=["nat"])

MODES = ["text", "story", "visual", "quiz", "world"]


@router.get("/topics")
async def nat_topics(grade: Optional[int] = None):
    """All NAT Témakörök (topics that have Témák), ordered by grade then order_index."""
    params = {
        "select": "id,nat_id,title,title_hu,grade,order_index,curriculum_lessons!inner(id)",
        "order": "grade,order_index",
    }
    if grade:
        params["grade"] = f"eq.{grade}"
    rows = await db_get("curriculum_topics", params, service=True)
    for r in rows:
        r.pop("curriculum_lessons", None)  # inner-join marker only
    return rows


@router.get("/topics/{topic_id}")
async def nat_topic(topic_id: str):
    """A Témakör with its Témák (ordered) and whether a topic-quiz exists."""
    topics = await db_get(
        "curriculum_topics",
        {"id": f"eq.{topic_id}",
         "select": "id,nat_id,title,title_hu,grade,order_index,"
                   "curriculum_lessons(id,nat_id,title,title_hu,order_index)"},
        service=True,
    )
    if not topics:
        raise HTTPException(status_code=404, detail="Topic not found")
    topic = topics[0]
    temak = sorted(topic.pop("curriculum_lessons", []) or [], key=lambda l: l.get("order_index", 0))
    quiz = await db_get(
        "content_blocks",
        {"topic_id": f"eq.{topic_id}", "scope": "eq.topic", "is_active": "eq.true",
         "select": "id", "limit": "1"},
        service=True,
    )
    return {**topic, "temak": temak, "has_topic_quiz": bool(quiz)}


@router.get("/lessons/{lesson_id}")
async def nat_lesson(lesson_id: str):
    """A Téma with its content_blocks grouped by mode (lesson scope)."""
    lessons = await db_get(
        "curriculum_lessons",
        {"id": f"eq.{lesson_id}", "select": "id,nat_id,title,title_hu,topic_id,order_index"},
        service=True,
    )
    if not lessons:
        raise HTTPException(status_code=404, detail="Lesson not found")
    blocks = await db_get(
        "content_blocks",
        {"lesson_id": f"eq.{lesson_id}", "scope": "eq.lesson", "is_active": "eq.true",
         "select": "mode,content"},
        service=True,
    )
    by_mode = {b["mode"]: b["content"] for b in blocks}
    return {**lessons[0], "blocks": by_mode, "modes": [m for m in MODES if m in by_mode]}


@router.get("/topics/{topic_id}/quiz")
async def nat_topic_quiz(topic_id: str):
    """The end-of-topic comprehensive quiz (scope=topic)."""
    blocks = await db_get(
        "content_blocks",
        {"topic_id": f"eq.{topic_id}", "scope": "eq.topic", "is_active": "eq.true",
         "select": "content", "limit": "1"},
        service=True,
    )
    if not blocks:
        raise HTTPException(status_code=404, detail="Topic quiz not found")
    return {"cards": blocks[0]["content"]}
