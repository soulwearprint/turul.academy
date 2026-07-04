"""
Read routes for the NAT 3-tier content model (curriculum_topics → curriculum_lessons
(Témák) → content_blocks). Distinct from the legacy `lessons` table the live app uses.

Reads use the service role (trusted backend) so the still-hidden NAT topics
(is_active=false, pre-cutover) are served for preview; content_blocks themselves
are is_active=true. Mirrors the service-role pattern documented in core/db.py.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from core.db import db_get, db_post, db_patch
from core.auth import get_current_user, SupabaseUser
from core.xp import award_xp

router = APIRouter(prefix="/api/nat", tags=["nat"])

MODES = ["text", "story", "visual", "quiz", "world"]
XP_PER_CORRECT = 10
XP_PERFECT_BONUS = 20


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


# ─── progress + quiz (user-owned; service-role writes scoped by user.id) ───

class ProgressBody(BaseModel):
    status: Optional[str] = None            # in_progress | completed
    mode_used: Optional[str] = None
    time_spent_seconds: Optional[int] = None


async def _upsert_progress(user_id, lesson_id, topic_id, status=None, mode_used=None, seconds=None):
    existing = await db_get("nat_lesson_progress",
                            {"user_id": f"eq.{user_id}", "lesson_id": f"eq.{lesson_id}", "select": "id,status"},
                            service=True)
    patch = {}
    if status: patch["status"] = status
    if mode_used: patch["mode_used"] = mode_used
    if seconds is not None: patch["time_spent_seconds"] = seconds
    if status == "completed": patch["completed_at"] = "now()"
    if existing:
        newly = status == "completed" and existing[0].get("status") != "completed"
        if patch:
            await db_patch("nat_lesson_progress",
                           {"user_id": f"eq.{user_id}", "lesson_id": f"eq.{lesson_id}"}, patch, service=True)
        return newly
    await db_post("nat_lesson_progress",
                  {"user_id": user_id, "lesson_id": lesson_id, "topic_id": topic_id,
                   "status": status or "in_progress", "mode_used": mode_used,
                   "time_spent_seconds": seconds}, service=True)
    return status == "completed"


@router.post("/lessons/{lesson_id}/progress")
async def nat_lesson_progress(lesson_id: str, body: ProgressBody,
                              user: SupabaseUser = Depends(get_current_user)):
    """Record that the user started/finished a Téma."""
    rows = await db_get("curriculum_lessons", {"id": f"eq.{lesson_id}", "select": "topic_id"}, service=True)
    if not rows:
        raise HTTPException(status_code=404, detail="Lesson not found")
    await _upsert_progress(user.id, lesson_id, rows[0]["topic_id"],
                           body.status, body.mode_used, body.time_spent_seconds)
    return {"ok": True}


class QuizSubmit(BaseModel):
    topic_id: str
    lesson_id: Optional[str] = None         # None → topic-scope quiz
    scope: str = "lesson"                   # lesson | topic
    answers: list[str]                      # picked letters (A/B/C/D) in card order


@router.post("/quiz/submit")
async def nat_quiz_submit(body: QuizSubmit, user: SupabaseUser = Depends(get_current_user)):
    """Grade a NAT quiz against its content_blocks, award XP, record the result."""
    if body.scope == "topic":
        params = {"topic_id": f"eq.{body.topic_id}", "scope": "eq.topic"}
    else:
        if not body.lesson_id:
            raise HTTPException(status_code=422, detail="lesson_id required for a lesson quiz")
        params = {"lesson_id": f"eq.{body.lesson_id}", "scope": "eq.lesson", "mode": "eq.quiz"}
    params |= {"is_active": "eq.true", "select": "content", "limit": "1"}
    blocks = await db_get("content_blocks", params, service=True)
    if not blocks:
        raise HTTPException(status_code=404, detail="Quiz not found")
    cards = blocks[0]["content"] or []

    per, correct = [], 0
    for i, card in enumerate(cards):
        want = (card.get("correct") or "").strip()[:1].upper()
        got = (body.answers[i].strip()[:1].upper() if i < len(body.answers) else "")
        ok = bool(want) and got == want
        correct += ok
        per.append(ok)
    total = len(cards)
    score = round(correct / total * 100) if total else 0
    xp = correct * XP_PER_CORRECT + (XP_PERFECT_BONUS if score == 100 and total else 0)

    lessons_delta = 0
    if body.scope == "lesson":
        newly = await _upsert_progress(user.id, body.lesson_id, body.topic_id,
                                       status="completed", mode_used="quiz")
        lessons_delta = 1 if newly else 0

    await db_post("nat_quiz_results", {
        "user_id": user.id, "topic_id": body.topic_id, "lesson_id": body.lesson_id,
        "scope": body.scope, "score": score, "correct": correct, "total": total,
        "answers": body.answers, "xp_earned": xp,
    }, service=True)
    totals = await award_xp(user.id, xp, lessons_delta=lessons_delta)
    return {"score": score, "correct": correct, "total": total, "results": per,
            "xp_earned": xp, **totals}


@router.get("/progress/me")
async def nat_progress_me(user: SupabaseUser = Depends(get_current_user)):
    """Per-topic completion for the NAT content + shared XP summary."""
    done = await db_get("nat_lesson_progress",
                        {"user_id": f"eq.{user.id}", "status": "eq.completed",
                         "select": "lesson_id,topic_id"}, service=True)
    by_topic: dict[str, int] = {}
    for r in done:
        by_topic[r["topic_id"]] = by_topic.get(r["topic_id"], 0) + 1
    return {"completed_lessons": len(done), "completed_by_topic": by_topic}
