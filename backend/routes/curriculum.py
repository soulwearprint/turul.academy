from fastapi import APIRouter, HTTPException
from core.db import db_get

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


@router.get("/subjects")
async def get_subjects():
    """List all active subjects."""
    return await db_get("curriculum_subjects", {"is_active": "eq.true", "select": "*"})


@router.get("/subjects/{subject_id}/topics")
async def get_topics(subject_id: str, grade: int | None = None):
    """Get topics for a subject, optionally filtered by grade."""
    params = {
        "subject_id": f"eq.{subject_id}",
        "is_active": "eq.true",
        "order": "grade,order_index",
        "select": "*",
    }
    if grade:
        params["grade"] = f"eq.{grade}"
    return await db_get("curriculum_topics", params)


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    """Get a single topic with its lessons."""
    topics = await db_get(
        "curriculum_topics",
        {"id": f"eq.{topic_id}", "select": "*,lessons(id,mode,title,reading_time_minutes,difficulty,is_active)"},
    )
    if not topics:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topics[0]


@router.get("/topics/{topic_id}/curiosity-links")
async def get_curiosity_links(topic_id: str):
    """Get curiosity links from a topic."""
    return await db_get(
        "curiosity_links",
        {
            "from_topic_id": f"eq.{topic_id}",
            "select": "*,to_topic:curriculum_topics!to_topic_id(id,title,title_hu,nat_id)",
        },
    )
