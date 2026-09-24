"""Badge awarding. The catalogue lives here (thresholds) and in the frontend
(frontend/src/lib/badges.js: icon + order, i18n: name/description) — keep the
type keys in sync. user_badges is unique per (user_id, badge_type), so
evaluate_badges() is idempotent and safe to call after any activity."""
from __future__ import annotations
import asyncio
from .db import db_get, db_post
from .xp import live_streak

BADGE_TYPES = [
    "first_lesson", "lessons_10", "lessons_25",
    "perfect_quiz", "perfect_5", "comeback",
    "topic_master", "polymath",
    "streak_3", "streak_7", "streak_30",
    "study_60",
]


class _Facts:
    """Lazily-loaded per-user numbers — each query runs only if a still-unearned
    badge actually needs it. Badges are checked concurrently, so the cache holds
    futures: two badges needing the same number share one query."""

    def __init__(self, user_id: str):
        self.uid = user_id
        self._cache: dict = {}

    async def _get(self, key, loader):
        if key not in self._cache:
            self._cache[key] = asyncio.ensure_future(loader())
        return await self._cache[key]

    async def completed(self) -> list[dict]:
        async def load():
            nat, legacy = await asyncio.gather(
                db_get("nat_lesson_progress", {"user_id": f"eq.{self.uid}", "status": "eq.completed",
                                               "select": "lesson_id,topic_id"}, service=True),
                db_get("lesson_progress", {"user_id": f"eq.{self.uid}", "status": "eq.completed",
                                           "select": "lesson_id,topic_id"}, service=True))
            return [dict(r, nat=True) for r in nat] + [dict(r, nat=False) for r in legacy]
        return await self._get("completed", load)

    async def perfect_count(self) -> int:
        async def load():
            nat, legacy = await asyncio.gather(
                db_get("nat_quiz_results", {"user_id": f"eq.{self.uid}", "score": "eq.100",
                                            "select": "lesson_id,topic_id,scope"}, service=True),
                db_get("quiz_results", {"user_id": f"eq.{self.uid}", "score": "eq.100",
                                        "select": "lesson_id"}, service=True))
            # legacy quiz_results keeps every retake — count each quiz once
            return len(nat) + len({r["lesson_id"] for r in legacy})
        return await self._get("perfect", load)

    async def streak(self) -> int:
        async def load():
            rows = await db_get("user_xp", {"user_id": f"eq.{self.uid}",
                                            "select": "streak_days,last_activity_date"}, service=True)
            return live_streak(rows[0] if rows else None)
        return await self._get("streak", load)

    async def study_seconds(self) -> int:
        async def load():
            rows = await db_get("daily_activity", {"user_id": f"eq.{self.uid}",
                                                   "select": "seconds_spent"}, service=True)
            return sum(r.get("seconds_spent") or 0 for r in rows)
        return await self._get("seconds", load)

    async def comeback(self) -> bool:
        """Scored 100% on a quiz after an earlier attempt of that same quiz below 75%."""
        async def load():
            rows = await db_get("nat_quiz_attempts",
                                {"user_id": f"eq.{self.uid}", "select": "lesson_id,topic_id,scope,score",
                                 "order": "created_at"}, service=True)
            low: set = set()
            for r in rows:
                key = (r["scope"], r.get("lesson_id") or r["topic_id"])
                if (r.get("score") or 0) < 75:
                    low.add(key)
                elif r.get("score") == 100 and key in low:
                    return True
            return False
        return await self._get("comeback", load)

    async def topic_master(self) -> bool:
        """Every Téma of at least one NAT Témakör completed."""
        async def load():
            done_by_topic: dict[str, set] = {}
            for r in await self.completed():
                if r["nat"]:
                    done_by_topic.setdefault(r["topic_id"], set()).add(r["lesson_id"])
            if not done_by_topic:
                return False
            lessons = await db_get("curriculum_lessons",
                                   {"topic_id": f"in.({','.join(done_by_topic)})", "select": "id,topic_id"},
                                   service=True)
            total: dict[str, int] = {}
            for l in lessons:
                total[l["topic_id"]] = total.get(l["topic_id"], 0) + 1
            return any(total.get(t) and len(done) >= total[t] for t, done in done_by_topic.items())
        return await self._get("topic_master", load)

    async def subject_count(self) -> int:
        async def load():
            topic_ids = {r["topic_id"] for r in await self.completed() if r.get("topic_id")}
            if not topic_ids:
                return 0
            topics = await db_get("curriculum_topics",
                                  {"id": f"in.({','.join(topic_ids)})", "select": "subject_id"}, service=True)
            return len({t["subject_id"] for t in topics if t.get("subject_id")})
        return await self._get("subjects", load)


async def _earned(f: _Facts, badge: str) -> bool:
    if badge == "first_lesson": return len(await f.completed()) >= 1
    if badge == "lessons_10":   return len(await f.completed()) >= 10
    if badge == "lessons_25":   return len(await f.completed()) >= 25
    if badge == "perfect_quiz": return await f.perfect_count() >= 1
    if badge == "perfect_5":    return await f.perfect_count() >= 5
    if badge == "comeback":     return await f.comeback()
    if badge == "topic_master": return await f.topic_master()
    if badge == "polymath":     return await f.subject_count() >= 2
    if badge == "streak_3":     return await f.streak() >= 3
    if badge == "streak_7":     return await f.streak() >= 7
    if badge == "streak_30":    return await f.streak() >= 30
    if badge == "study_60":     return await f.study_seconds() >= 3600
    return False


async def evaluate_badges(user_id: str) -> list[str]:
    """Award every badge the user now qualifies for; returns the newly earned types."""
    have = {b["badge_type"] for b in await db_get(
        "user_badges", {"user_id": f"eq.{user_id}", "select": "badge_type"}, service=True)}
    todo = [b for b in BADGE_TYPES if b not in have]
    if not todo:
        return []
    facts = _Facts(user_id)
    flags = await asyncio.gather(*(_earned(facts, b) for b in todo))
    new = [b for b, ok in zip(todo, flags) if ok]
    if new:
        await db_post("user_badges", [{"user_id": user_id, "badge_type": b} for b in new], service=True)
    return new


async def safe_evaluate(user_id: str) -> list[str]:
    """Badges are a bonus — never fail the request that triggered the check."""
    try:
        return await evaluate_badges(user_id)
    except Exception:
        return []
