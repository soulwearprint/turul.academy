from __future__ import annotations
from fastapi import APIRouter, Depends
from core.auth import get_current_user, SupabaseUser
from core.db import db_get

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/me")
async def get_my_progress(user: SupabaseUser = Depends(get_current_user)):
    """Get full progress summary for the authenticated user."""
    completed = await db_get(
        "lesson_progress",
        {
            "user_id": f"eq.{user.id}",
            "status": "eq.completed",
            "select": "lesson_id,topic_id,mode_used,completed_at,time_spent_seconds",
        },
        service=True,
    )
    xp = await db_get("user_xp", {"user_id": f"eq.{user.id}", "select": "*"}, service=True)
    badges = await db_get("user_badges", {"user_id": f"eq.{user.id}", "select": "*", "order": "earned_at.desc"}, service=True)

    return {
        "completed_lessons": completed,
        "xp": xp[0] if xp else {"total_xp": 0, "level": 1, "streak_days": 0},
        "badges": badges,
    }


@router.get("/me/subject/{subject_id}")
async def get_subject_progress(
    subject_id: str,
    user: SupabaseUser = Depends(get_current_user),
):
    """Get progress for a specific subject — lessons completed per topic."""
    topics = await db_get(
        "curriculum_topics",
        {"subject_id": f"eq.{subject_id}", "is_active": "eq.true", "select": "id,nat_id,title,grade"},
    )
    topic_ids = [t["id"] for t in topics]
    if not topic_ids:
        return {"topics": [], "completion_pct": 0}

    completed = await db_get(
        "lesson_progress",
        {
            "user_id": f"eq.{user.id}",
            "status": "eq.completed",
            "topic_id": f"in.({','.join(topic_ids)})",
            "select": "topic_id,mode_used",
        },
        service=True,
    )

    completed_by_topic: dict[str, list[str]] = {}
    for row in completed:
        completed_by_topic.setdefault(row["topic_id"], []).append(row["mode_used"])

    topic_summaries = [
        {
            **t,
            "modes_completed": completed_by_topic.get(t["id"], []),
            "is_complete": len(completed_by_topic.get(t["id"], [])) >= 1,
        }
        for t in topics
    ]

    complete_count = sum(1 for t in topic_summaries if t["is_complete"])
    pct = round((complete_count / len(topics)) * 100) if topics else 0

    return {"topics": topic_summaries, "completion_pct": pct}
