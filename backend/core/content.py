"""Facts derived from the content that actually exists (vs. the curriculum rows' static values)."""
from __future__ import annotations
from .db import db_get


async def grade_ranges() -> dict[str, tuple[int, int]]:
    """{subject_id: (lowest, highest) grade that has lessons}. Service role: NAT topics are
    still is_active=false pre-cutover, so an anon read would see none."""
    rows = await db_get("curriculum_topics",
                        {"select": "subject_id,grade,curriculum_lessons!inner(id)"}, service=True)
    out: dict[str, tuple[int, int]] = {}
    for r in rows:
        sid, g = r.get("subject_id"), r.get("grade")
        if not sid or g is None:
            continue
        lo, hi = out.get(sid, (g, g))
        out[sid] = (min(lo, g), max(hi, g))
    return out


def with_content_grades(subject: dict | None, ranges: dict) -> dict | None:
    """Report the grades a student can actually study. curriculum_subjects.grade_min/max is
    the subject's nominal range — Physics said 7–12 while the NAT only teaches it in 7–10 —
    so it's only the fallback for a subject with no lessons yet."""
    if subject and subject.get("id") in ranges:
        subject["grade_min"], subject["grade_max"] = ranges[subject["id"]]
    return subject
