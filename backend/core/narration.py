"""„Felolvasás” payload for a lesson: the text of every card, plus the Storage path of its audio
file where one has been generated (content/generators/generate_audio.py).

Audio is looked up by the hash of the spoken text (core/speech.py), so a card that was edited
since its audio was made simply has no match and falls back to the browser's own voice until
the generator is run again. Never raises: read-aloud must not be able to break a lesson page.
"""
from __future__ import annotations

from .db import db_get
from .speech import AUDIO_MODES, narration_for_blocks

AUDIO_BUCKET = "content-audio"


def _public(entry: dict | None, audio: str | None = None) -> dict | None:
    return None if entry is None else {"title": entry["title"], "text": entry["text"], "audio": audio}


async def _audio_paths(hashes: set) -> dict:
    if not hashes:
        return {}
    try:
        rows = await db_get("narration_audio",
                            {"select": "text_hash,path", "text_hash": f"in.({','.join(sorted(hashes))})"},
                            service=True)
    except Exception:   # table not migrated yet, or a Supabase hiccup: the browser voice still works
        return {}
    return {r["text_hash"]: f"{AUDIO_BUCKET}/{r['path']}" for r in rows}


async def narration_for(blocks: dict) -> dict:
    """{mode: [card, …]} → {mode: [{title, text, audio} | None, …]}, index-aligned with the cards."""
    entries = narration_for_blocks(blocks)
    paths = await _audio_paths({e["hash"] for mode in AUDIO_MODES for e in entries.get(mode, []) if e})
    return {mode: [_public(e, paths.get(e["hash"]) if (e and mode in AUDIO_MODES) else None) for e in es]
            for mode, es in entries.items()}


def quiz_narration(cards) -> list:
    """Questions + options only (never the answer). Browser voice, no audio files."""
    return [_public(e) for e in narration_for_blocks({"quiz": cards or []}).get("quiz", [])]
