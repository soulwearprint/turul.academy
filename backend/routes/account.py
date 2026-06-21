from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import date
from core.auth import get_current_user, SupabaseUser
from core.db import db_get, db_post, db_patch

router = APIRouter(prefix="/api/account", tags=["account"])

UNDER_13_BIRTH_YEAR_THRESHOLD = date.today().year - 13


class ProfileSetup(BaseModel):
    display_name: str
    grade: Optional[int] = None
    birth_year: Optional[int] = None
    school: Optional[str] = None
    preferred_mode: Optional[str] = None
    gamification_level: str = "light"
    language: str = "hu"
    parent_email: Optional[str] = None


@router.get("/me")
async def get_profile(user: SupabaseUser = Depends(get_current_user)):
    profiles = await db_get("user_profiles", {"id": f"eq.{user.id}", "select": "*"}, service=True)
    if not profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profiles[0]


@router.post("/me")
async def create_profile(body: ProfileSetup, user: SupabaseUser = Depends(get_current_user)):
    # ⚠️ GDPR: if under 13, parent_email is required before creating profile
    if body.birth_year and body.birth_year > UNDER_13_BIRTH_YEAR_THRESHOLD:
        if not body.parent_email:
            raise HTTPException(
                status_code=422,
                detail="Parent email required for users under 13 (GDPR compliance)",
            )

    existing = await db_get("user_profiles", {"id": f"eq.{user.id}", "select": "id"}, service=True)
    if existing:
        raise HTTPException(status_code=409, detail="Profile already exists — use PATCH to update")

    return await db_post("user_profiles", {
        "id": user.id,
        "display_name": body.display_name,
        "grade": body.grade,
        "birth_year": body.birth_year,
        "school": body.school,
        "preferred_mode": body.preferred_mode,
        "gamification_level": body.gamification_level,
        "language": body.language,
        "parent_email": body.parent_email,
    }, service=True)


@router.patch("/me")
async def update_profile(body: ProfileSetup, user: SupabaseUser = Depends(get_current_user)):
    payload = body.model_dump(exclude_none=True)
    return await db_patch("user_profiles", {"id": f"eq.{user.id}"}, payload, service=True)


@router.get("/me/subjects")
async def get_enrolled_subjects(user: SupabaseUser = Depends(get_current_user)):
    return await db_get(
        "user_subjects",
        {
            "user_id": f"eq.{user.id}",
            "select": "*,subject:curriculum_subjects(id,code,name,name_hu,grade_min,grade_max)",
        },
        service=True,
    )


@router.post("/me/subjects/{subject_id}")
async def enrol_subject(subject_id: str, user: SupabaseUser = Depends(get_current_user)):
    existing = await db_get(
        "user_subjects",
        {"user_id": f"eq.{user.id}", "subject_id": f"eq.{subject_id}", "select": "id"},
        service=True,
    )
    if existing:
        raise HTTPException(status_code=409, detail="Already enrolled in this subject")
    return await db_post("user_subjects", {"user_id": user.id, "subject_id": subject_id}, service=True)
