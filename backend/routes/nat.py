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
from core.db import db_get, db_post, db_patch, db_delete, db_rpc
from core.auth import get_current_user, SupabaseUser
from core.xp import award_xp, log_study_time, revoke_xp
from core.badges import safe_evaluate

router = APIRouter(prefix="/api/nat", tags=["nat"])

MODES = ["text", "story", "visual", "quiz", "world", "experiment", "deep"]   # deep = „Mesélj még!” layer
READING_MODES = [m for m in MODES if m != "quiz"]
XP_PER_CORRECT = 10
XP_PERFECT_BONUS = 20
# One flush covers one uninterrupted stretch of a lesson visit; anything longer is a
# tab left open, not study — cap it so it can't swamp the averages.
MAX_FLUSH_SECONDS = 30 * 60
# A tab only counts as "read" (for seconds-per-card) after this much time on it.
MIN_MODE_SECONDS = 3


@router.get("/topics")
async def nat_topics(grade: Optional[int] = None, subject_id: Optional[str] = None):
    """All NAT Témakörök (topics that have Témák), ordered by grade then order_index."""
    params = {
        "select": "id,nat_id,title,title_hu,grade,order_index,curriculum_lessons!inner(id)",
        "order": "grade,order_index",
    }
    if grade:
        params["grade"] = f"eq.{grade}"
    if subject_id:
        params["subject_id"] = f"eq.{subject_id}"
    rows = await db_get("curriculum_topics", params, service=True)
    for r in rows:
        # Was an inner-join existence marker only — now surfaced as a count so the
        # frontend can advertise how many Témák sit under each Témakör tile.
        r["lesson_count"] = len(r.pop("curriculum_lessons", None) or [])
    return rows


@router.get("/topics/{topic_id}")
async def nat_topic(topic_id: str):
    """A Témakör with its Témák (ordered) and whether a topic-quiz exists."""
    topics = await db_get(
        "curriculum_topics",
        {"id": f"eq.{topic_id}",
         "select": "id,nat_id,title,title_hu,grade,order_index,subject_id,"
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
    status: Optional[str] = None            # in_progress | read (all main tabs viewed) | completed
    mode_used: Optional[str] = None
    # Time is a DELTA — seconds of active study since the client's last flush — and is
    # added to the lesson's running total (a lesson is usually studied over several visits).
    time_spent_seconds: Optional[int] = None
    mode_seconds: Optional[dict[str, int]] = None   # the same delta, split by tab


# Ordered so a status update never regresses further-along progress — e.g. reopening
# a completed lesson to re-read it must not drop it back to "in_progress".
STATUS_RANK = {"in_progress": 1, "read": 2, "completed": 3}


async def _upsert_progress(user_id, lesson_id, topic_id, status=None, mode_used=None):
    existing = await db_get("nat_lesson_progress",
                            {"user_id": f"eq.{user_id}", "lesson_id": f"eq.{lesson_id}", "select": "id,status"},
                            service=True)
    prev_status = existing[0].get("status") if existing else None
    apply_status = status and STATUS_RANK.get(status, 0) >= STATUS_RANK.get(prev_status, 0)

    patch = {}
    if apply_status: patch["status"] = status
    if mode_used: patch["mode_used"] = mode_used
    if status == "completed" and apply_status: patch["completed_at"] = "now()"
    if existing:
        newly = status == "completed" and prev_status != "completed"
        if patch:
            await db_patch("nat_lesson_progress",
                           {"user_id": f"eq.{user_id}", "lesson_id": f"eq.{lesson_id}"}, patch, service=True)
        return newly
    await db_post("nat_lesson_progress",
                  {"user_id": user_id, "lesson_id": lesson_id, "topic_id": topic_id,
                   "status": status or "in_progress", "mode_used": mode_used}, service=True)
    return status == "completed"


def _clean_time(body: ProgressBody) -> tuple[int, dict]:
    modes = {m: min(max(int(s), 0), MAX_FLUSH_SECONDS)
             for m, s in (body.mode_seconds or {}).items() if m in MODES}
    modes = {m: s for m, s in modes.items() if s > 0}
    total = body.time_spent_seconds if body.time_spent_seconds is not None else sum(modes.values())
    return min(max(int(total or 0), 0), MAX_FLUSH_SECONDS), modes


@router.post("/lessons/{lesson_id}/progress")
async def nat_lesson_progress(lesson_id: str, body: ProgressBody,
                              user: SupabaseUser = Depends(get_current_user)):
    """Record study time on a Téma and/or move its status forward."""
    rows = await db_get("curriculum_lessons", {"id": f"eq.{lesson_id}", "select": "topic_id"}, service=True)
    if not rows:
        raise HTTPException(status_code=404, detail="Lesson not found")
    topic_id = rows[0]["topic_id"]
    seconds, modes = _clean_time(body)
    if seconds > 0:
        # Atomic upsert-and-add (creates the row as in_progress on a first visit).
        await db_rpc("nat_track_time", {"p_user": user.id, "p_lesson": lesson_id, "p_topic": topic_id,
                                        "p_seconds": seconds, "p_modes": modes})
        await log_study_time(user.id, seconds)
    if body.status or body.mode_used:
        await _upsert_progress(user.id, lesson_id, topic_id, body.status, body.mode_used)
    new_badges = await safe_evaluate(user.id) if (seconds > 0 or body.status) else []
    return {"ok": True, "new_badges": new_badges}


@router.delete("/lessons/{lesson_id}/progress")
async def nat_lesson_reset(lesson_id: str, user: SupabaseUser = Depends(get_current_user)):
    """Undo a Téma: its status, study time, quiz result and attempt history — e.g. a
    lesson opened by mistake, or a clean retake. The quiz XP it earned is taken back.
    Earned badges and the study-calendar history stay (those record what happened)."""
    scope = {"user_id": f"eq.{user.id}", "lesson_id": f"eq.{lesson_id}"}
    results = await db_get("nat_quiz_results", dict(scope, select="xp_earned"), service=True)
    xp = sum(r.get("xp_earned") or 0 for r in results)
    for table in ("nat_quiz_results", "nat_quiz_attempts", "nat_lesson_progress"):
        await db_delete(table, scope, service=True)
    await revoke_xp(user.id, xp)
    return {"ok": True, "xp_removed": xp}


class QuizSubmit(BaseModel):
    topic_id: str
    lesson_id: Optional[str] = None         # None → topic-scope quiz
    scope: str = "lesson"                   # lesson | topic
    answers: list[str]                      # picked letters (A/B/C/D) in card order


@router.post("/quiz/submit")
async def nat_quiz_submit(body: QuizSubmit, user: SupabaseUser = Depends(get_current_user)):
    """Grade a NAT quiz against its content_blocks, award XP, record the result.

    Retakes RESET rather than accumulate: a quiz's contribution to total_xp is always
    its most recent attempt, not the sum of every attempt (otherwise a student could
    farm XP by resubmitting the same quiz repeatedly).
    """
    if body.scope == "topic":
        params = {"topic_id": f"eq.{body.topic_id}", "scope": "eq.topic"}
    else:
        if not body.lesson_id:
            raise HTTPException(status_code=422, detail="lesson_id required for a lesson quiz")
        params = {"lesson_id": f"eq.{body.lesson_id}", "scope": "eq.lesson", "mode": "eq.quiz"}
    block_params = dict(params, **{"is_active": "eq.true", "select": "content", "limit": "1"})
    blocks = await db_get("content_blocks", block_params, service=True)
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

    # Reset semantics: find this quiz's previously-counted XP for this user, wipe it,
    # and only add the DELTA to total_xp — so retaking never inflates the total beyond
    # what this latest attempt actually earned.
    result_params = {"user_id": f"eq.{user.id}", "scope": f"eq.{body.scope}",
                     "lesson_id": f"eq.{body.lesson_id}" if body.scope == "lesson" else "is.null",
                     "topic_id": f"eq.{body.topic_id}"}
    prev = await db_get("nat_quiz_results", dict(result_params, select="id,xp_earned"), service=True)
    prev_xp = sum(p.get("xp_earned") or 0 for p in prev)
    if prev:
        await db_delete("nat_quiz_results", result_params, service=True)
    xp_delta = xp - prev_xp

    attempt = {"user_id": user.id, "topic_id": body.topic_id, "lesson_id": body.lesson_id,
               "scope": body.scope, "score": score, "correct": correct, "total": total,
               "answers": body.answers}
    await db_post("nat_quiz_results", dict(attempt, xp_earned=xp), service=True)
    # Every attempt is also logged (results keeps only the latest) — the history behind
    # first-try vs latest scores and "questions you keep missing".
    await db_post("nat_quiz_attempts", dict(attempt, results=per), service=True)
    totals = await award_xp(user.id, xp_delta, lessons_delta=lessons_delta)
    new_badges = await safe_evaluate(user.id)
    return {"score": score, "correct": correct, "total": total, "results": per,
            "xp_earned": xp_delta, "new_badges": new_badges, **totals}


@router.get("/progress/me")
async def nat_progress_me(user: SupabaseUser = Depends(get_current_user)):
    """Per-topic completion + per-lesson status (for status colour-coding) + shared XP summary."""
    rows = await db_get("nat_lesson_progress",
                        {"user_id": f"eq.{user.id}",
                         "select": "lesson_id,topic_id,status"}, service=True)
    by_topic: dict[str, int] = {}
    lesson_status: dict[str, str] = {}
    for r in rows:
        lesson_status[r["lesson_id"]] = r["status"]
        if r["status"] == "completed":
            by_topic[r["topic_id"]] = by_topic.get(r["topic_id"], 0) + 1
    completed_lessons = sum(1 for s in lesson_status.values() if s == "completed")
    return {"completed_lessons": completed_lessons, "completed_by_topic": by_topic,
            "lesson_status": lesson_status}


def _in(ids) -> str:
    return f"in.({','.join(ids)})"


def _avg(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values)) if values else None


@router.get("/stats/me")
async def nat_stats_me(user: SupabaseUser = Depends(get_current_user)):
    """Per-Témakör / per-Téma study stats: time, seconds per card read, and quiz
    retention (first attempt vs latest). Only topics the user has touched."""
    uid = f"eq.{user.id}"
    progress = await db_get("nat_lesson_progress",
                            {"user_id": uid, "select": "lesson_id,topic_id,status,time_spent_seconds,mode_seconds"},
                            service=True)
    results = await db_get("nat_quiz_results",
                           {"user_id": uid, "select": "lesson_id,topic_id,scope,score"}, service=True)
    attempts = await db_get("nat_quiz_attempts",
                            {"user_id": uid, "select": "lesson_id,topic_id,scope,score", "order": "created_at"},
                            service=True)
    topic_ids = {r["topic_id"] for r in progress + results}
    if not topic_ids:
        return {"topics": [], "totals": {"seconds": 0, "lessons": 0, "quizzes": 0, "quiz_avg": None}}

    topics = await db_get("curriculum_topics",
                          {"id": _in(topic_ids),
                           "select": "id,nat_id,title,title_hu,grade,order_index,subject_id,"
                                     "curriculum_lessons(id,title,title_hu,order_index)"},
                          service=True)
    lesson_ids = [r["lesson_id"] for r in progress]
    counts = await db_get("content_block_card_counts",
                          {"lesson_id": _in(lesson_ids), "scope": "eq.lesson",
                           "select": "lesson_id,mode,card_count"}, service=True) if lesson_ids else []
    cards: dict[str, dict] = {}
    for c in counts:
        cards.setdefault(c["lesson_id"], {})[c["mode"]] = c["card_count"] or 0

    prog = {r["lesson_id"]: r for r in progress}
    latest = {(r["scope"], r.get("lesson_id") or r["topic_id"]): r["score"] for r in results}
    first: dict = {}
    tries: dict = {}
    for a in attempts:
        key = (a["scope"], a.get("lesson_id") or a["topic_id"])
        first.setdefault(key, a["score"])
        tries[key] = tries.get(key, 0) + 1

    out_topics = []
    for t in sorted(topics, key=lambda t: (t.get("grade") or 0, t.get("order_index") or 0)):
        lessons_out = []
        all_lessons = t.pop("curriculum_lessons", []) or []
        for l in sorted(all_lessons, key=lambda l: l.get("order_index") or 0):
            p = prog.get(l["id"])
            key = ("lesson", l["id"])
            if not p and key not in latest:
                continue
            ms = (p or {}).get("mode_seconds") or {}
            read_s = sum(ms.get(m, 0) for m in READING_MODES)
            n_cards = sum(cards.get(l["id"], {}).get(m, 0)
                          for m in READING_MODES if ms.get(m, 0) >= MIN_MODE_SECONDS)
            lessons_out.append({
                "lesson_id": l["id"], "title": l.get("title"), "title_hu": l.get("title_hu"),
                "order_index": l.get("order_index"), "status": (p or {}).get("status"),
                "seconds": (p or {}).get("time_spent_seconds") or 0,
                "read_seconds": read_s, "cards_read": n_cards,
                "sec_per_card": round(read_s / n_cards) if n_cards else None,
                "quiz_score": latest.get(key), "first_score": first.get(key), "attempts": tries.get(key, 0),
            })
        read_s = sum(x["read_seconds"] for x in lessons_out)
        n_cards = sum(x["cards_read"] for x in lessons_out)
        out_topics.append({
            "topic_id": t["id"], "nat_id": t.get("nat_id"), "title": t.get("title"),
            "title_hu": t.get("title_hu"), "grade": t.get("grade"), "subject_id": t.get("subject_id"),
            "seconds": sum(x["seconds"] for x in lessons_out),
            "sec_per_card": round(read_s / n_cards) if n_cards else None,
            "quiz_avg": _avg(x["quiz_score"] for x in lessons_out),
            "first_avg": _avg(x["first_score"] for x in lessons_out),
            "topic_quiz": latest.get(("topic", t["id"])),
            "lessons_done": sum(1 for x in lessons_out if x["status"] == "completed"),
            "lessons_total": len(all_lessons),
            "lessons": lessons_out,
        })
    return {
        "topics": out_topics,
        "totals": {
            "seconds": sum(r.get("time_spent_seconds") or 0 for r in progress),
            "lessons": len(progress),
            "quizzes": len(results),
            "quiz_avg": _avg(r["score"] for r in results),
        },
    }


@router.get("/review/me")
async def nat_review_me(user: SupabaseUser = Depends(get_current_user)):
    """Questions the user got wrong on their most recent attempt of each quiz, ranked by
    how many attempts missed them. Attempts graded against an older version of a quiz
    (different question count) are ignored — the indexes wouldn't line up."""
    attempts = await db_get("nat_quiz_attempts",
                            {"user_id": f"eq.{user.id}", "order": "created_at.desc", "limit": "400",
                             "select": "lesson_id,topic_id,scope,total,results,answers,created_at"},
                            service=True)
    by_quiz: dict = {}
    for a in attempts:
        by_quiz.setdefault((a["scope"], a.get("lesson_id") or a["topic_id"]), []).append(a)
    if not by_quiz:
        return {"items": [], "count": 0}

    lesson_ids = [k for s, k in by_quiz if s == "lesson"]
    topic_quiz_ids = [k for s, k in by_quiz if s == "topic"]
    blocks = []
    if lesson_ids:
        blocks += await db_get("content_blocks",
                               {"lesson_id": _in(lesson_ids), "scope": "eq.lesson", "mode": "eq.quiz",
                                "is_active": "eq.true", "select": "lesson_id,topic_id,scope,content"}, service=True)
    if topic_quiz_ids:
        blocks += await db_get("content_blocks",
                               {"topic_id": _in(topic_quiz_ids), "scope": "eq.topic",
                                "is_active": "eq.true", "select": "lesson_id,topic_id,scope,content"}, service=True)
    content = {(b["scope"], b.get("lesson_id") if b["scope"] == "lesson" else b["topic_id"]): b["content"] or []
               for b in blocks}

    lessons = await db_get("curriculum_lessons",
                           {"id": _in(lesson_ids), "select": "id,title,title_hu,topic_id"},
                           service=True) if lesson_ids else []
    lesson_by_id = {l["id"]: l for l in lessons}
    all_topic_ids = set(topic_quiz_ids) | {l["topic_id"] for l in lessons}
    topics = await db_get("curriculum_topics", {"id": _in(all_topic_ids), "select": "id,title,title_hu"},
                          service=True) if all_topic_ids else []
    topic_by_id = {t["id"]: t for t in topics}

    items = []
    for (scope, qid), quiz_attempts in by_quiz.items():
        cards = content.get((scope, qid))
        if not cards:
            continue
        valid = [a for a in quiz_attempts
                 if a.get("total") == len(cards) and len(a.get("results") or []) == len(cards)]
        if not valid:
            continue
        last = valid[0]                                   # newest first
        lesson = lesson_by_id.get(qid) if scope == "lesson" else None
        topic = topic_by_id.get(lesson["topic_id"] if lesson else qid) or {}
        for i, card in enumerate(cards):
            if last["results"][i]:
                continue
            answers = last.get("answers") or []
            items.append({
                "scope": scope, "lesson_id": qid if scope == "lesson" else None,
                "topic_id": lesson["topic_id"] if lesson else qid, "index": i,
                "question": card.get("question"), "options": card.get("options") or [],
                "correct": (card.get("correct") or "").strip()[:1].upper(),
                "explanation": card.get("explanation"),
                "your_answer": answers[i] if i < len(answers) else "",
                "misses": sum(1 for a in valid if not a["results"][i]), "attempts": len(valid),
                "last_at": last["created_at"],
                "lesson_title": (lesson or {}).get("title"), "lesson_title_hu": (lesson or {}).get("title_hu"),
                "topic_title": topic.get("title"), "topic_title_hu": topic.get("title_hu"),
            })
    # Most-missed first; ties → most recently missed first (stable two-pass sort).
    items.sort(key=lambda x: x["last_at"], reverse=True)
    items.sort(key=lambda x: x["misses"], reverse=True)
    return {"items": items[:60], "count": len(items)}
