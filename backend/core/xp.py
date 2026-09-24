"""Shared XP / streak / daily-activity awarding — used by both the legacy quiz
flow and the NAT 3-tier quiz. XP lives in the shared user_xp table so a student's
level and streak span all content."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo
from .db import db_get, db_post, db_patch, db_rpc

# Students are Hungarian: a "study day" (streak, heatmap) is a Budapest calendar day,
# not the server's UTC day — otherwise 00:30 local study lands on the previous day.
TZ = ZoneInfo("Europe/Budapest")


def today_local() -> date:
    return datetime.now(TZ).date()


def level_for(total_xp: int) -> int:
    # matches the frontend's Math.floor(xp/100)+1
    return max(1, total_xp // 100 + 1)


def live_streak(row: Optional[dict]) -> int:
    """streak_days is only rewritten on activity, so a streak broken days ago still
    reads as its old value — report 0 once the last active day is before yesterday."""
    if not row:
        return 0
    today = today_local()
    if row.get("last_activity_date") not in (today.isoformat(), (today - timedelta(days=1)).isoformat()):
        return 0
    return row.get("streak_days") or 0


async def _roll_streak(user_id: str, xp_delta: int = 0) -> dict:
    """Mark today as an active day (rolling the streak) and apply an XP change."""
    today = today_local()
    today_s = today.isoformat()
    yday_s = (today - timedelta(days=1)).isoformat()

    rows = await db_get("user_xp", {"user_id": f"eq.{user_id}", "select": "*"}, service=True)
    if rows:
        r = rows[0]
        last = r.get("last_activity_date")
        streak = r.get("streak_days") or 0
        if last == today_s:
            pass                      # already active today
        elif last == yday_s:
            streak += 1               # consecutive day
        else:
            streak = 1                # streak broken / first ever
        total = max(0, (r.get("total_xp") or 0) + xp_delta)
        await db_patch("user_xp", {"user_id": f"eq.{user_id}"},
                       {"total_xp": total, "level": level_for(total),
                        "streak_days": streak, "last_activity_date": today_s}, service=True)
    else:
        total, streak = max(0, xp_delta), 1
        await db_post("user_xp", {"user_id": user_id, "total_xp": total, "level": level_for(total),
                                  "streak_days": 1, "last_activity_date": today_s}, service=True)
    return {"total_xp": total, "level": level_for(total), "streak_days": streak}


async def award_xp(user_id: str, xp_delta: int, lessons_delta: int = 0) -> dict:
    """Apply a signed XP change (may be negative — e.g. a quiz retake resets its
    contribution), roll the daily streak, and bump today's daily_activity.
    Returns the new totals. total_xp is floored at 0."""
    totals = await _roll_streak(user_id, xp_delta)
    today_s = today_local().isoformat()

    da = await db_get("daily_activity",
                      {"user_id": f"eq.{user_id}", "date": f"eq.{today_s}",
                       "select": "id,xp_earned,lessons_completed"}, service=True)
    if da:
        await db_patch("daily_activity", {"user_id": f"eq.{user_id}", "date": f"eq.{today_s}"},
                       {"xp_earned": max(0, (da[0].get("xp_earned") or 0) + xp_delta),
                        "lessons_completed": (da[0].get("lessons_completed") or 0) + lessons_delta}, service=True)
    else:
        await db_post("daily_activity", {"user_id": user_id, "date": today_s,
                                         "xp_earned": max(0, xp_delta), "lessons_completed": lessons_delta}, service=True)
    return totals


async def log_study_time(user_id: str, seconds: int) -> None:
    """Add reading time to today's daily_activity and count today as a streak day —
    studying a lesson is activity even when no quiz is submitted."""
    if seconds <= 0:
        return
    await db_rpc("track_study_seconds",
                 {"p_user": user_id, "p_date": today_local().isoformat(), "p_seconds": seconds})
    await _roll_streak(user_id)


async def revoke_xp(user_id: str, xp: int) -> None:
    """Take back XP when progress is reset. Unlike award_xp this does NOT touch the
    streak or today's activity — resetting a lesson isn't studying."""
    if xp <= 0:
        return
    rows = await db_get("user_xp", {"user_id": f"eq.{user_id}", "select": "total_xp"}, service=True)
    if not rows:
        return
    total = max(0, (rows[0].get("total_xp") or 0) - xp)
    await db_patch("user_xp", {"user_id": f"eq.{user_id}"},
                   {"total_xp": total, "level": level_for(total)}, service=True)
