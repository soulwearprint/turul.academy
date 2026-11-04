"""Narration text for „Felolvasás” (read aloud) — what a card sounds like when it is read to a student.

Pure and stdlib-only on purpose: the API (routes/nat.py, routes/lessons.py) and the audio
generator (content/generators/generate_audio.py) import this same module, so the browser voice,
the pre-generated audio files and the cache key (`text_hash`) can never drift apart. Change the
wording rules here and every card whose text changes simply gets a new hash → new audio.

Entry shape (one per card, None when a card has nothing to say):
    {"title": "Mi a sebesség?", "text": "Mi a sebesség?\\n\\nA sebesség …", "hash": "<40 hex>"}
"""
from __future__ import annotations

import hashlib
import logging
import re

from .speech_units import acronyms, formulas, units

# Cards that become audio files (the audiobook). Quiz cards are read aloud only by the
# browser voice, one question at a time — a quiz is interactive, not something to play locked.
AUDIO_MODES = ("text", "story", "visual", "world", "experiment", "deep")
SPEECH_MODES = AUDIO_MODES + ("quiz",)

_CAP = "A-ZÁÉÍÓÖŐÚÜŰ"

# Abbreviations a Hungarian reader expands without thinking but a speech engine spells out.
# Only unambiguous ones: a wrong expansion is silent and wrong, so the list stays short.
_ABBREVIATIONS = [
    (re.compile(r"\bKr\.\s*e\."), "Krisztus előtt"),
    (re.compile(r"\bKr\.\s*u\."), "Krisztus után"),
    (re.compile(r"\bi\.\s*e\."), "időszámításunk előtt"),
    (re.compile(r"\bi\.\s*sz\."), "időszámításunk szerint"),
    (re.compile(rf"(?<!\w)stb\.(?=\s+[{_CAP}])"), "és így tovább."),
    (re.compile(r"(?<!\w)stb\."), "és így tovább"),
    (re.compile(r"(?<!\w)pl\."), "például"),
    (re.compile(r"(?<!\w)ún\."), "úgynevezett"),
    (re.compile(r"(?<!\w)ill\."), "illetve"),
    (re.compile(r"(?<!\w)kb\."), "körülbelül"),
    (re.compile(r"(?<=\d) db(?!\w)"), " darab"),
    (re.compile(r"(?<!\w)ld\."), "lásd"),
    (re.compile(rf"(?<!\w)id\.\s+(?=[{_CAP}])"), "idősebb "),
    (re.compile(rf"(?<!\w)ifj\.\s+(?=[{_CAP}])"), "ifjabb "),
    (re.compile(rf"(?<!\w)Szt\.\s+(?=[{_CAP}])"), "Szent "),
    (re.compile(rf"(?<!\w)dr\.\s+(?=[{_CAP}])"), "doktor "),
]

# Formula symbols a speech engine reads as "csillag", "kalap" or not at all. Spoken the way a
# Hungarian teacher reads the formula aloud: F = m * a → „F egyenlő m szorozva a”.
_SYMBOLS = [
    (re.compile(r"\s*[×·]\s*|\s\*\s|(?<=\w)\*(?=\w)"), " szorozva "),
    (re.compile(r"\s*≈\s*"), " körülbelül egyenlő "),
    (re.compile(r"\s*=\s*"), " egyenlő "),
    (re.compile(r"(?<=\S)\s\+\s(?=\S)"), " plusz "),
    (re.compile(r"(?<=\S)\s/\s(?=\S)"), " osztva "),
    (re.compile(r"\s*→\s*"), ", majd "),
    (re.compile(r"±\s*"), "plusz-mínusz "),
    (re.compile(r"(?<=[^\W\d_)])\s*(?:²|\^2)"), " négyzet"),
    (re.compile(r"(?<=[^\W\d_)])\s*(?:³|\^3)"), " köb"),
]

_GREEK = {"ρ": "ró", "Δ": "delta", "π": "pi", "λ": "lambda", "α": "alfa", "β": "béta", "γ": "gamma", "ω": "omega", "μ": "mű"}
_GREEK_RX = re.compile(r"(?<!\w)([" + "".join(_GREEK) + r"])(?!\w)")

_MARKDOWN = [
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),
    (re.compile(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)"), r"\1"),
    (re.compile(r"`([^`]*)`"), r"\1"),
]


def _safely(rule, text: str) -> str:
    """Read-aloud must never be able to break a lesson page: a rule that fails leaves its text as it was."""
    try:
        return rule(text)
    except Exception:   # pragma: no cover — guarded by tests that every table entry parses
        logging.getLogger(__name__).exception("speech rule %s failed", getattr(rule, "__name__", repr(rule)))
        return text


def clean(text) -> str:
    """One piece of card text → what the voice should read."""
    if not text:
        return ""
    s = str(text).replace(" ", " ").replace("\r\n", "\n")
    for rx, rep in _MARKDOWN:
        s = rx.sub(rep, s)
    for rx, rep in _ABBREVIATIONS:
        s = rx.sub(rep, s)
    s = _safely(units, s)
    s = _safely(acronyms, s)
    for rx, rep in _SYMBOLS:
        s = rx.sub(rep, s)
    s = _safely(formulas, s)
    s = _GREEK_RX.sub(lambda m: _GREEK[m.group(1)], s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+([,.;:!?)])", r"\1", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _sentence(text) -> str:
    """cleaned text that ends in sentence punctuation, so the voice pauses after it."""
    s = clean(text)
    if s and s[-1] not in ".!?…:;":
        s += "."
    return s


def _labelled(label: str, text) -> str:
    s = _sentence(text)
    return f"{label}: {s}" if s else ""


def _join(parts) -> str:
    return "\n\n".join(p for p in parts if p)


def _timeline(items) -> str:
    out = []
    for it in items or []:
        if isinstance(it, dict):
            when, what = clean(it.get("when")), _sentence(it.get("what"))
            if what:
                out.append(f"{when}: {what}" if when else what)
    return "\n".join(out)


def _letter(i: int) -> str:
    return chr(65 + i)


_OPTION_LABEL = re.compile(r"^\(?[A-Da-d][).:]\s+")


def _option(text) -> str:
    """Stored options carry their own „A) ” label; the narration adds the letter itself."""
    return _sentence(_OPTION_LABEL.sub("", str(text or "").strip()))


def _build(mode: str, card: dict) -> tuple[str, str]:
    """(title, text) for one card. Fields the page shows only as decoration (mood, caption,
    image credits, sketch descriptions) are skipped — they are not part of the lesson."""
    heading = clean(card.get("heading"))
    if mode == "text":
        text = _join([_sentence(heading), _sentence(card.get("body")), _labelled("Kulcsfogalom", card.get("key_term"))])
    elif mode == "story":
        text = _join([_sentence(heading), _sentence(card.get("body"))])
    elif mode == "visual":
        text = _join([_sentence(heading), _sentence(card.get("description")), _timeline(card.get("timeline"))])
    elif mode == "world":
        year = clean(card.get("year"))
        # "1914: A háború kitör…" — a year can't take a suffix safely (vowel harmony), so a colon.
        text = _join([_labelled(year, heading) if year and heading else _sentence(heading or year),
                      _sentence(card.get("body")), _labelled("Nekünk azért fontos", card.get("link_hu"))])
    elif mode == "experiment":
        text = _join([_sentence(heading), _labelled("Felfedezés", card.get("discovery")),
                      _labelled("Ma", card.get("today")),
                      _labelled("Próbáld ki, egyszerű változat", card.get("try_basic")),
                      _labelled("Próbáld ki, haladó változat", card.get("try_advanced"))])
    elif mode == "deep":
        text = _join([_sentence(heading), _sentence(card.get("body")), _labelled("Tudtad", card.get("did_you_know")),
                      _labelled("Gondolkodj", card.get("think")), _labelled("A válasz", card.get("think_answer"))])
    elif mode == "quiz":
        question = _sentence(card.get("question"))
        options = [_option(o) for o in card.get("options") or []]
        text = _join([question, " ".join(f"{_letter(i)}: {o}" for i, o in enumerate(options) if o)])
        heading = heading or clean(card.get("question"))
    else:
        return "", ""
    title = heading[:80] if heading else ""
    return title, text


def text_hash(text: str) -> str:
    """Cache key of a narration text (shared by the API and the audio generator)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:40]


def narration_entry(mode: str, card) -> dict | None:
    if not isinstance(card, dict) or mode not in SPEECH_MODES:
        return None
    title, text = _build(mode, card)
    if not text:
        return None
    return {"title": title, "text": text, "hash": text_hash(text)}


def narration_for_blocks(blocks: dict) -> dict:
    """{mode: [card, …]} → {mode: [entry | None, …]} — index-aligned with the cards."""
    return {mode: [narration_entry(mode, c) for c in cards]
            for mode, cards in blocks.items() if mode in SPEECH_MODES and isinstance(cards, list)}
