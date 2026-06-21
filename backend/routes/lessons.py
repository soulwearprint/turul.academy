from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from core.auth import get_current_user, SupabaseUser
from core.db import db_get, db_post, db_patch

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("/{lesson_id}")
async def get_lesson(lesson_id: str):
    """Get a single lesson with its content cards."""
    lessons = await db_get(
        "lessons",
        {"id": f"eq.{lesson_id}", "is_active": "eq.true", "select": "*"},
    )
    if not lessons:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lessons[0]


@router.get("/topic/{topic_id}")
async def get_lessons_for_topic(topic_id: str):
    """Get all active lessons for a topic (all modes)."""
    return await db_get(
        "lessons",
        {"topic_id": f"eq.{topic_id}", "is_active": "eq.true", "select": "id,mode,title,reading_time_minutes,difficulty"},
    )


@router.get("/{lesson_id}/quiz")
async def get_quiz_questions(lesson_id: str):
    """Get quiz questions for a lesson."""
    return await db_get(
        "quiz_questions",
        {"lesson_id": f"eq.{lesson_id}", "is_active": "eq.true", "select": "id,question_type,question,options,difficulty"},
    )


class ProgressUpdate(BaseModel):
    status: str
    mode_used: Optional[str] = None
    time_spent_seconds: Optional[int] = None


@router.post("/{lesson_id}/progress")
async def update_progress(
    lesson_id: str,
    body: ProgressUpdate,
    user: SupabaseUser = Depends(get_current_user),
):
    """Upsert lesson progress for the authenticated user."""
    existing = await db_get(
        "lesson_progress",
        {"user_id": f"eq.{user.id}", "lesson_id": f"eq.{lesson_id}", "select": "id,topic_id"},
    )

    payload: dict = {"status": body.status}
    if body.mode_used:
        payload["mode_used"] = body.mode_used
    if body.time_spent_seconds:
        payload["time_spent_seconds"] = body.time_spent_seconds
    if body.status == "in_progress" and not existing:
        payload["started_at"] = "now()"
    if body.status == "completed":
        payload["completed_at"] = "now()"

    if existing:
        return await db_patch(
            "lesson_progress",
            {"user_id": f"eq.{user.id}", "lesson_id": f"eq.{lesson_id}"},
            payload,
            service=True,
        )
    else:
        lessons = await db_get("lessons", {"id": f"eq.{lesson_id}", "select": "topic_id"})
        if not lessons:
            raise HTTPException(status_code=404, detail="Lesson not found")
        return await db_post("lesson_progress", {
            "user_id": user.id,
            "lesson_id": lesson_id,
            "topic_id": lessons[0]["topic_id"],
            **payload,
        }, service=True)
