"""
„Hibát találtál?” — students flag a content card; reviewers work through the queue.

Delayed quality control on top of the generators' guard rails: automated checks miss
things (see content/exports/*_deep_dive_review*.md), students reading every card won't.

Reviewer = user_profiles.role in (reviewer, admin). Roles can only be set by the service
role / direct SQL since migration v8 (before that a student could promote themselves).
Reporter identities are never returned to reviewers — only counts, reasons and comments.

Every card edit is logged in content_edits (before / after / who / when, migration v9) and
can be undone from the queue's „Szerkesztések” tab.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.auth import get_current_user, SupabaseUser
from core.db import db_get, db_post, db_patch, db_rpc

router = APIRouter(prefix="/api/reports", tags=["reports"])

REASONS = {"teny", "kviz", "nyelv", "erthetetlen", "egyeb"}
MODES = {"text", "story", "visual", "quiz", "world", "experiment", "deep"}
MAX_PER_DAY = 30          # a curious student may flag a lot; a script may not
MAX_COMMENT = 500


async def _is_reviewer(user_id: str) -> bool:
    rows = await db_get("user_profiles", {"id": f"eq.{user_id}", "select": "role"}, service=True)
    return bool(rows) and rows[0].get("role") in ("reviewer", "admin")


async def _require_reviewer(user: SupabaseUser):
    if not await _is_reviewer(user.id):
        raise HTTPException(status_code=403, detail="Reviewers only")


async def _find_block(scope: str, mode: str, topic_id: str, lesson_id: Optional[str]):
    if scope == "topic":
        params = {"topic_id": f"eq.{topic_id}", "scope": "eq.topic"}
    else:
        if not lesson_id:
            raise HTTPException(status_code=422, detail="lesson_id required for a lesson card")
        params = {"lesson_id": f"eq.{lesson_id}", "scope": "eq.lesson", "mode": f"eq.{mode}"}
    rows = await db_get("content_blocks", dict(params, is_active="eq.true", select="id,content", limit="1"),
                        service=True)
    return rows[0] if rows else None


class ReportBody(BaseModel):
    topic_id: str
    lesson_id: Optional[str] = None
    scope: str = "lesson"                 # lesson | topic (topic quiz)
    mode: str
    card_index: int
    reason: str
    comment: Optional[str] = None


@router.post("")
async def create_report(body: ReportBody, user: SupabaseUser = Depends(get_current_user)):
    if body.reason not in REASONS or body.mode not in MODES or body.scope not in ("lesson", "topic"):
        raise HTTPException(status_code=422, detail="Invalid reason/mode/scope")
    comment = (body.comment or "").strip()[:MAX_COMMENT] or None
    block = await _find_block(body.scope, body.mode, body.topic_id, body.lesson_id)
    if not block:
        raise HTTPException(status_code=404, detail="Content not found")
    cards = block.get("content") or []
    if not 0 <= body.card_index < len(cards):
        raise HTTPException(status_code=422, detail="card_index out of range")

    # Same student, same card, still open → update it rather than stacking duplicates.
    mine = {"user_id": f"eq.{user.id}", "block_id": f"eq.{block['id']}",
            "card_index": f"eq.{body.card_index}", "status": "eq.open"}
    if await db_get("content_reports", dict(mine, select="id"), service=True):
        await db_patch("content_reports", mine, {"reason": body.reason, "comment": comment}, service=True)
        return {"ok": True, "updated": True}

    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    recent = await db_get("content_reports", {"user_id": f"eq.{user.id}", "created_at": f"gte.{since}",
                                              "select": "id"}, service=True)
    if len(recent) >= MAX_PER_DAY:
        raise HTTPException(status_code=429, detail="Too many reports today")

    await db_post("content_reports", {
        "user_id": user.id, "topic_id": body.topic_id, "lesson_id": body.lesson_id if body.scope == "lesson" else None,
        "block_id": block["id"], "scope": body.scope, "mode": body.mode, "card_index": body.card_index,
        "card_snapshot": cards[body.card_index], "reason": body.reason, "comment": comment,
    }, service=True)
    return {"ok": True}


@router.get("/summary")
async def reports_summary(user: SupabaseUser = Depends(get_current_user)):
    """Open-report count for the reviewer's Profile link (non-reviewers just get reviewer=false)."""
    if not await _is_reviewer(user.id):
        return {"reviewer": False, "open": 0}
    rows = await db_get("content_reports", {"status": "eq.open", "select": "id", "limit": "1000"}, service=True)
    return {"reviewer": True, "open": len(rows)}


@router.get("")
async def list_reports(status: str = "open", user: SupabaseUser = Depends(get_current_user)):
    """The review queue: reports grouped per card, with the card as reported and as it is now."""
    await _require_reviewer(user)
    if status not in ("open", "resolved", "dismissed"):
        raise HTTPException(status_code=422, detail="Invalid status")
    rows = await db_get("content_reports", {
        "status": f"eq.{status}", "order": "created_at.desc", "limit": "300",
        "select": "id,topic_id,lesson_id,block_id,scope,mode,card_index,card_snapshot,reason,comment,"
                  "reviewer_note,resolved_at,created_at,"
                  "lesson:curriculum_lessons(title_hu),topic:curriculum_topics(title_hu,nat_id,grade)",
    }, service=True)
    block_ids = sorted({r["block_id"] for r in rows if r.get("block_id")})
    current = {b["id"]: b.get("content") or [] for b in await db_get(
        "content_blocks", {"id": f"in.({','.join(block_ids)})", "select": "id,content"}, service=True)} if block_ids else {}

    groups: dict = {}
    for r in rows:
        key = (r.get("block_id") or f"{r.get('lesson_id')}:{r['mode']}:{r['scope']}", r["card_index"])
        g = groups.get(key)
        if not g:
            now_cards = current.get(r.get("block_id")) if r.get("block_id") else None
            now_card = now_cards[r["card_index"]] if now_cards and r["card_index"] < len(now_cards) else None
            g = groups[key] = {
                "block_id": r.get("block_id"), "card_index": r["card_index"], "mode": r["mode"],
                "scope": r["scope"], "topic_id": r["topic_id"], "lesson_id": r.get("lesson_id"),
                "topic_title": (r.get("topic") or {}).get("title_hu"), "nat_id": (r.get("topic") or {}).get("nat_id"),
                "lesson_title": (r.get("lesson") or {}).get("title_hu"),
                "snapshot": r["card_snapshot"], "current": now_card,
                "changed": now_card is not None and now_card != r["card_snapshot"],
                "editable": now_card is not None,
                "report_ids": [], "reasons": {}, "comments": [], "latest": r["created_at"],
                "reviewer_note": r.get("reviewer_note"), "resolved_at": r.get("resolved_at"),
            }
        g["report_ids"].append(r["id"])
        g["reasons"][r["reason"]] = g["reasons"].get(r["reason"], 0) + 1
        if r.get("comment"):
            g["comments"].append(r["comment"])
    # Most-reported cards first; ties → most recently reported first (stable two-pass sort).
    out = sorted(groups.values(), key=lambda g: g["latest"], reverse=True)
    out.sort(key=lambda g: len(g["report_ids"]), reverse=True)
    return {"groups": out, "reports": len(rows)}


class ResolveBody(BaseModel):
    report_ids: list[str]
    status: str                            # resolved | dismissed | open (reopen)
    note: Optional[str] = None


@router.post("/resolve")
async def resolve_reports(body: ResolveBody, user: SupabaseUser = Depends(get_current_user)):
    await _require_reviewer(user)
    if body.status not in ("resolved", "dismissed", "open") or not body.report_ids:
        raise HTTPException(status_code=422, detail="Invalid status or no reports")
    reopen = body.status == "open"
    await db_patch("content_reports", {"id": f"in.({','.join(body.report_ids)})"}, {
        "status": body.status, "reviewer_note": (body.note or "").strip()[:1000] or None,
        "resolved_by": None if reopen else user.id, "resolved_at": None if reopen else "now()",
    }, service=True)
    return {"ok": True}


class CardEdit(BaseModel):
    block_id: str
    card_index: int
    card: dict
    before: Optional[dict] = None          # the card as the reviewer loaded it (conflict check)
    report_ids: list[UUID] = []            # the reports that prompted the edit, for the log


def _same_shape(old, new) -> bool:
    """A reviewer edits wording, not structure: same keys, strings stay strings, option lists
    keep their length, anything else (e.g. an experiment card's sketch) is untouched."""
    if set(old) != set(new):
        return False
    for k, v in old.items():
        if isinstance(v, str) and not isinstance(new[k], str):
            return False
        if isinstance(v, list) and (not isinstance(new[k], list) or len(new[k]) != len(v)
                                    or not all(isinstance(x, str) for x in new[k])):
            return False
        if not isinstance(v, (str, list)) and new[k] != v:
            return False
    return True


async def _apply_edit(block_id: str, card_index: int, before: dict, after: dict, editor: str,
                      report_ids=(), reverts: Optional[str] = None) -> Optional[str]:
    """Write the card and its log row in one transaction (edit_content_card). The function
    refuses (409) if the card no longer matches `before` — someone edited it meanwhile."""
    try:
        return await db_rpc("edit_content_card", {
            "p_block_id": block_id, "p_card_index": card_index, "p_before": before, "p_after": after,
            "p_editor": editor, "p_report_ids": [str(r) for r in report_ids], "p_reverts": reverts,
        })
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (404, 409, 422):
            raise HTTPException(status_code=e.response.status_code,
                                detail=(e.response.json() or {}).get("message", "Edit refused"))
        raise


@router.put("/card")
async def edit_card(body: CardEdit, user: SupabaseUser = Depends(get_current_user)):
    """Fix a reported card in place (reviewers only). The report keeps the original snapshot;
    content_edits keeps the before/after so the edit can be undone."""
    await _require_reviewer(user)
    rows = await db_get("content_blocks", {"id": f"eq.{body.block_id}", "select": "id,content"}, service=True)
    if not rows:
        raise HTTPException(status_code=404, detail="Block not found")
    cards = rows[0].get("content") or []
    if not 0 <= body.card_index < len(cards):
        raise HTTPException(status_code=422, detail="card_index out of range")
    if not _same_shape(cards[body.card_index], body.card):
        raise HTTPException(status_code=422, detail="Card structure changed")
    if "correct" in body.card and (body.card["correct"] or "").strip()[:1].upper() not in ("A", "B", "C", "D"):
        raise HTTPException(status_code=422, detail="correct must be A–D")
    before = body.before if body.before is not None else cards[body.card_index]
    edit_id = await _apply_edit(body.block_id, body.card_index, before, body.card, user.id, body.report_ids)
    return {"ok": True, "card": body.card, "edit_id": edit_id}


@router.get("/edits")
async def list_edits(limit: int = 50, user: SupabaseUser = Depends(get_current_user)):
    """Recent card edits, newest first: what changed, who, when, and whether it can be undone."""
    await _require_reviewer(user)
    rows = await db_get("content_edits", {
        "order": "created_at.desc", "limit": str(min(max(limit, 1), 200)),
        "select": "id,block_id,topic_id,lesson_id,mode,scope,card_index,before,after,reverts,created_at,"
                  "editor:user_profiles(display_name),"
                  "lesson:curriculum_lessons(title_hu),topic:curriculum_topics(title_hu,nat_id)",
    }, service=True)
    block_ids = sorted({r["block_id"] for r in rows if r.get("block_id")})
    current = {b["id"]: b.get("content") or [] for b in await db_get(
        "content_blocks", {"id": f"in.({','.join(block_ids)})", "select": "id,content"}, service=True)} if block_ids else {}

    # An undo is always newer than the edit it reverts, and a card's latest edit is newer than
    # its older ones — so within this newest-first window both facts are complete.
    reverted = {r["reverts"] for r in rows if r.get("reverts")}
    seen_cards: set = set()
    out = []
    for r in rows:
        card_key = (r.get("block_id"), r["card_index"])
        latest = r.get("block_id") is not None and card_key not in seen_cards
        seen_cards.add(card_key)
        now_cards = current.get(r.get("block_id")) or []
        now_card = now_cards[r["card_index"]] if r["card_index"] < len(now_cards) else None
        out.append({
            "id": r["id"], "block_id": r.get("block_id"), "card_index": r["card_index"],
            "mode": r["mode"], "scope": r["scope"], "topic_id": r.get("topic_id"), "lesson_id": r.get("lesson_id"),
            "topic_title": (r.get("topic") or {}).get("title_hu"), "nat_id": (r.get("topic") or {}).get("nat_id"),
            "lesson_title": (r.get("lesson") or {}).get("title_hu"),
            "editor": (r.get("editor") or {}).get("display_name"), "created_at": r["created_at"],
            "before": r["before"], "after": r["after"],
            "is_undo": bool(r.get("reverts")), "reverted": r["id"] in reverted,
            # Undo only the card's latest edit, and only while the live card still matches it.
            "undoable": latest and now_card == r["after"],
        })
    return {"edits": out}


@router.post("/edits/{edit_id}/revert")
async def revert_edit(edit_id: UUID, user: SupabaseUser = Depends(get_current_user)):
    """Undo an edit: put its `before` back (logged as a new edit that `reverts` it)."""
    await _require_reviewer(user)
    rows = await db_get("content_edits", {"id": f"eq.{edit_id}", "select": "id,block_id,card_index,before,after"},
                        service=True)
    if not rows:
        raise HTTPException(status_code=404, detail="Edit not found")
    e = rows[0]
    if not e.get("block_id"):
        raise HTTPException(status_code=410, detail="The card has been regenerated since")
    new_id = await _apply_edit(e["block_id"], e["card_index"], e["after"], e["before"], user.id, reverts=e["id"])
    return {"ok": True, "edit_id": new_id}
