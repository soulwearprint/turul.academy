from __future__ import annotations
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from core.auth import get_current_user, SupabaseUser
from core.db import db_get, db_patch, db_delete
from core.xp import live_streak, today_local
from core.badges import safe_evaluate

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/me")
async def get_my_progress(user: SupabaseUser = Depends(get_current_user)):
    """Flat progress summary (legacy + NAT content unified).

    XP/streak live in the shared user_xp table; the completed-lesson count spans both
    legacy `lesson_progress` (Physics etc.) and `nat_lesson_progress` (History).
    """
    legacy = await db_get(
        "lesson_progress",
        {"user_id": f"eq.{user.id}", "status": "eq.completed", "select": "lesson_id"},
        service=True,
    )
    nat = await db_get(
        "nat_lesson_progress",
        {"user_id": f"eq.{user.id}", "status": "eq.completed", "select": "lesson_id"},
        service=True,
    )
    xp = await db_get("user_xp", {"user_id": f"eq.{user.id}", "select": "*"}, service=True)
    badges = await db_get("user_badges",
                          {"user_id": f"eq.{user.id}", "select": "badge_type,earned_at", "order": "earned_at.desc"},
                          service=True)
    x = xp[0] if xp else {}

    return {
        "total_xp": x.get("total_xp") or 0,
        "level": x.get("level") or 1,
        "streak_days": live_streak(x),
        "completed_lessons": len(legacy) + len(nat),
        "badges": badges,
    }


@router.get("/me/badges")
async def get_my_badges(user: SupabaseUser = Depends(get_current_user)):
    """Earned badges. Re-evaluates first, so badges earned before awarding existed
    (or missed by a failed check) show up the next time the page is opened."""
    await safe_evaluate(user.id)
    return await db_get("user_badges",
                        {"user_id": f"eq.{user.id}", "select": "badge_type,earned_at", "order": "earned_at"},
                        service=True)


@router.get("/me/activity")
async def get_my_activity(days: int = 119, user: SupabaseUser = Depends(get_current_user)):
    """Daily study log for the calendar heatmap (Budapest-local days), plus streaks."""
    days = max(7, min(days, 371))
    today = today_local()
    since = today - timedelta(days=days - 1)
    rows = await db_get("daily_activity",
                        {"user_id": f"eq.{user.id}", "date": f"gte.{since.isoformat()}",
                         "select": "date,seconds_spent,xp_earned,lessons_completed", "order": "date"},
                        service=True)
    xp = await db_get("user_xp", {"user_id": f"eq.{user.id}", "select": "streak_days,last_activity_date"},
                      service=True)

    # Longest streak over ALL history (the window above may cut a run in half).
    all_days = await db_get("daily_activity",
                            {"user_id": f"eq.{user.id}", "select": "date,seconds_spent", "order": "date"},
                            service=True)
    longest = run = 0
    prev = None
    for r in all_days:
        d = date.fromisoformat(r["date"])
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        longest = max(longest, run)
        prev = d

    return {
        "today": today.isoformat(),
        "days": [{"date": r["date"], "seconds": r.get("seconds_spent") or 0, "xp": r.get("xp_earned") or 0,
                  "lessons": r.get("lessons_completed") or 0} for r in rows],
        "current_streak": live_streak(xp[0] if xp else None),
        "longest_streak": longest,
        # All-time study time — the calendar's history, which (unlike the per-lesson
        # stats) a per-lesson reset leaves alone.
        "total_seconds": sum(r.get("seconds_spent") or 0 for r in all_days),
    }


# Every user-owned progress table. Profile, enrolled subjects and the account survive.
RESET_TABLES = ["nat_quiz_attempts", "nat_quiz_results", "nat_lesson_progress",
                "quiz_results", "lesson_progress", "daily_activity", "user_badges"]


@router.delete("/me")
async def reset_my_progress(confirm: str = "", user: SupabaseUser = Depends(get_current_user)):
    """Wipe ALL of the user's learning progress: lesson statuses, study time, quiz
    results + history, XP/level/streak, study calendar and badges. Requires
    ?confirm=RESET so a stray request can't do this."""
    if confirm != "RESET":
        raise HTTPException(status_code=422, detail="Pass confirm=RESET to wipe all progress")
    for table in RESET_TABLES:
        await db_delete(table, {"user_id": f"eq.{user.id}"}, service=True)
    await db_patch("user_xp", {"user_id": f"eq.{user.id}"},
                   {"total_xp": 0, "level": 1, "streak_days": 0, "last_activity_date": None}, service=True)
    return {"ok": True}


@router.get("/me/subject/{subject_id}")
async def get_subject_progress(
    subject_id: str,
    user: SupabaseUser = Depends(get_current_user),
):
    """Get progress for a specific subject — lessons completed per topic.

    Unions the legacy `lesson_progress` (e.g. Physics, still on the old `lessons`
    table) with `nat_lesson_progress` (History's 3-tier Témák) so this works for
    any subject regardless of which content model its topics use.

    NAT subjects (topics with Témák — still is_active=false pre-cutover, hence the
    service-role read) report completed Témák / all Témák instead.
    """
    nat_topics = await db_get(
        "curriculum_topics",
        {"subject_id": f"eq.{subject_id}", "select": "id,curriculum_lessons!inner(id)"},
        service=True,
    )
    nat_total = sum(len(t.get("curriculum_lessons") or []) for t in nat_topics)
    if nat_total:
        done = await db_get(
            "nat_lesson_progress",
            {"user_id": f"eq.{user.id}", "status": "eq.completed",
             "topic_id": f"in.({','.join(t['id'] for t in nat_topics)})", "select": "lesson_id"},
            service=True,
        )
        return {"topics": [], "completion_pct": round(len(done) / nat_total * 100),
                "lessons_done": len(done), "lessons_total": nat_total}

    topics = await db_get(
        "curriculum_topics",
        {"subject_id": f"eq.{subject_id}", "is_active": "eq.true", "select": "id,nat_id,title,grade"},
    )
    topic_ids = [t["id"] for t in topics]
    if not topic_ids:
        return {"topics": [], "completion_pct": 0}

    ids_csv = ",".join(topic_ids)
    legacy = await db_get(
        "lesson_progress",
        {"user_id": f"eq.{user.id}", "status": "eq.completed",
         "topic_id": f"in.({ids_csv})", "select": "topic_id,mode_used"},
        service=True,
    )
    nat = await db_get(
        "nat_lesson_progress",
        {"user_id": f"eq.{user.id}", "status": "eq.completed",
         "topic_id": f"in.({ids_csv})", "select": "topic_id,mode_used"},
        service=True,
    )

    completed_by_topic: dict[str, list[str]] = {}
    for row in legacy + nat:
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
