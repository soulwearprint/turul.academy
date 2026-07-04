"""Shared XP / streak / daily-activity awarding — used by both the legacy quiz
flow and the NAT 3-tier quiz. XP lives in the shared user_xp table so a student's
level and streak span all content."""
from __future__ import annotations
from datetime import date, timedelta
from .db import db_get, db_post, db_patch


def level_for(total_xp: int) -> int:
    # matches the frontend's Math.floor(xp/100)+1
    return max(1, total_xp // 100 + 1)


async def award_xp(user_id: str, xp: int, lessons_delta: int = 0) -> dict:
    """Add XP, roll the daily streak, and bump today's daily_activity. Returns the new totals."""
    today = date.today()
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
        total = (r.get("total_xp") or 0) + xp
        await db_patch("user_xp", {"user_id": f"eq.{user_id}"},
                       {"total_xp": total, "level": level_for(total),
                        "streak_days": streak, "last_activity_date": today_s}, service=True)
    else:
        total, streak = xp, 1
        await db_post("user_xp", {"user_id": user_id, "total_xp": xp, "level": level_for(xp),
                                  "streak_days": 1, "last_activity_date": today_s}, service=True)

    da = await db_get("daily_activity",
                      {"user_id": f"eq.{user_id}", "date": f"eq.{today_s}",
                       "select": "id,xp_earned,lessons_completed"}, service=True)
    if da:
        await db_patch("daily_activity", {"user_id": f"eq.{user_id}", "date": f"eq.{today_s}"},
                       {"xp_earned": (da[0].get("xp_earned") or 0) + xp,
                        "lessons_completed": (da[0].get("lessons_completed") or 0) + lessons_delta}, service=True)
    else:
        await db_post("daily_activity", {"user_id": user_id, "date": today_s,
                                         "xp_earned": xp, "lessons_completed": lessons_delta}, service=True)

    return {"total_xp": total, "level": level_for(total), "streak_days": streak}
