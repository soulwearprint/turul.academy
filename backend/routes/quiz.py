from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.auth import get_current_user, SupabaseUser
from core.db import db_get, db_post, db_patch

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

XP_PER_CORRECT = 10
XP_PERFECT_BONUS = 20


class QuizAnswer(BaseModel):
    question_id: str
    answer: str


class QuizSubmission(BaseModel):
    lesson_id: str
    answers: list[QuizAnswer]


@router.post("/submit")
async def submit_quiz(
    body: QuizSubmission,
    user: SupabaseUser = Depends(get_current_user),
):
    """Submit quiz answers, calculate score, award XP."""
    # Fetch questions
    questions = await db_get(
        "quiz_questions",
        {"lesson_id": f"eq.{body.lesson_id}", "is_active": "eq.true", "select": "id,correct_answer,explanation"},
    )
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this lesson")

    q_map = {q["id"]: q for q in questions}
    results = []
    correct_count = 0

    for ans in body.answers:
        q = q_map.get(ans.question_id)
        if not q:
            continue
        is_correct = ans.answer.strip().lower() == (q["correct_answer"] or "").strip().lower()
        if is_correct:
            correct_count += 1
        results.append({
            "question_id": ans.question_id,
            "answer": ans.answer,
            "is_correct": is_correct,
            "explanation": q.get("explanation"),
        })

    total = len(questions)
    score = round((correct_count / total) * 100) if total else 0
    xp_earned = (correct_count * XP_PER_CORRECT) + (XP_PERFECT_BONUS if score == 100 else 0)

    # Fetch topic_id from lesson
    lessons = await db_get("lessons", {"id": f"eq.{body.lesson_id}", "select": "topic_id"})
    topic_id = lessons[0]["topic_id"] if lessons else None

    # Save result
    result_row = await db_post("quiz_results", {
        "user_id": user.id,
        "lesson_id": body.lesson_id,
        "topic_id": topic_id,
        "score": score,
        "answers": results,
        "xp_earned": xp_earned,
    })

    # Update XP (upsert pattern)
    existing_xp = await db_get("user_xp", {"user_id": f"eq.{user.id}", "select": "total_xp,level"})
    if existing_xp:
        new_total = (existing_xp[0].get("total_xp") or 0) + xp_earned
        new_level = max(1, new_total // 100)  # simple level formula: 100 XP per level
        await db_patch("user_xp", {"user_id": f"eq.{user.id}"}, {"total_xp": new_total, "level": new_level})
    else:
        await db_post("user_xp", {"user_id": user.id, "total_xp": xp_earned, "level": 1})

    # Update daily activity
    today_activity = await db_get(
        "daily_activity",
        {"user_id": f"eq.{user.id}", "date": "eq.today", "select": "id,xp_earned"},
    )
    if today_activity:
        await db_patch(
            "daily_activity",
            {"user_id": f"eq.{user.id}", "date": "eq.today"},
            {"xp_earned": (today_activity[0].get("xp_earned") or 0) + xp_earned},
        )

    return {
        "score": score,
        "correct": correct_count,
        "total": total,
        "xp_earned": xp_earned,
        "results": results,
    }
