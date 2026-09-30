"""
Deterministic post-processing and checks for generated lesson content.

The QA audit (content/qa/, PR #6) found the same mechanical errors in every band. They are cheap
to prevent in code, so the generators call `postprocess()` before saving, and `qa_audit.py lint`
calls the same `card_problems()` / `block_problems()` on existing content.

What it does
  quiz      shuffle options (the LLM puts the key on A far too often), relabel A–D, keep
            "minden fenti" / "egyik sem" style options last, remap letters quoted in the
            explanation, flag bad keys / duplicate options / key-vs-explanation conflicts
  text      drop near-duplicate cards, collapse "hanghullám (hanghullám)", fix a/az
  all       flag English glosses, flag a/az uncertainties (acronyms) instead of guessing

No network, no dependencies. Fixes are applied only where the rule is unambiguous; everything
else is returned as an issue string for the caller to print (or to trigger one retry).
"""
import hashlib
import random
import re

VOWELS = "aáeéiíoóöőuúüűAÁEÉIÍOÓÖŐUÚÜŰ"
CONSONANTS = "bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ"
_WORD = r"[^\W\d_]"     # any letter

# ── a / az ───────────────────────────────────────────────────────────────────
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(s):
    total, prev = 0, 0
    for ch in reversed(s):
        v = ROMAN[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def number_starts_with_vowel(n):
    """Does the Hungarian reading of n start with a vowel?
    1 egy, 5 öt, 50 ötven, 500 ötszáz, 1000-1999 ezer…, 5000 ötezer, 1 000 000 egymillió are vowels;
    2 két, 10 tíz, 100 száz, 2000 kétezer… are consonants."""
    if n >= 1_000_000:
        return number_starts_with_vowel(n // 1_000_000) if n < 10**9 else False
    if n >= 1000:
        thousands = n // 1000
        return True if thousands == 1 else number_starts_with_vowel(thousands)
    if n >= 100:
        return n // 100 == 5
    if n >= 10:
        return n // 10 == 5
    return n in (1, 5)


# Letter names that start with a vowel (em, en, es, ef, el, er, iksz, …). Used only to *flag* acronyms.
_VOWEL_LETTER_NAMES = set("AEFILMNORSUXYÁÉÍÓÖŐÚÜŰ")
# Acronyms read as words rather than letter by letter: article follows the first sound of the word.
_ACRONYM_WORDS = {"NATO": False, "UNESCO": True, "UNICEF": True, "FIFA": False, "OPEC": True,
                  "LED": False, "NASA": False, "LIGO": False, "MÁV": False, "FIDESZ": False, "MEFESZ": False,
                  "ENSZ": True, "EU": True, "USA": True}    # True = starts with a vowel when read


def _next_word_vowel(word):
    """(starts_with_vowel, kind) for the word an article precedes. kind: 'num' (numeral, Roman
    numeral), 'word' (plain word), 'acr' (acronym, reading uncertain), or None (unknown)."""
    m = re.match(r"(\d+)", word)
    if m:
        return number_starts_with_vowel(int(m.group(1))), "num"
    rm = re.fullmatch(r"([IVXLCDM]+)\.", word)
    if rm:
        return number_starts_with_vowel(roman_to_int(rm.group(1))), "num"
    if re.fullmatch(rf"{_WORD}+", word):
        if word.isupper() and len(word) >= 2:
            if word in _ACRONYM_WORDS:
                return _ACRONYM_WORDS[word], "acr"
            return word[0] in _VOWEL_LETTER_NAMES, "acr"
        return word[0] in VOWELS, "word"
    return None, None


_ART = re.compile(rf"(?<![\w-])(?P<art>[Aa]z?)(?P<sp>[ \t]+)(?P<word>[\w][\w\-–/.,]*)")
_SKIP_NEXT = {"és", "vagy", "illetve", "is", "pont", "oldal", "betű"}   # „a és b”, „A pont”, „a betű”


def fix_articles(text):
    """Correct a/az. Safe rewrites only:
      a → az before a word that starts with a vowel, and a/az before numerals and Roman numerals
      (az 1930-as, a 80-as, az I. világháború).
    Not rewritten, only reported: az → a before plain words (az can be a pronoun: „az nem igaz”),
    and acronyms (MDF, NATO), where the article depends on how the abbreviation is spoken.
    Returns (text, flagged)."""
    flagged = []

    def repl(m):
        art, word = m.group("art"), m.group("word")
        bare = re.sub(r"[,;:!?)]+$", "", word)
        if bare.rstrip(".").lower() in _SKIP_NEXT:
            return m.group(0)
        vowel, kind = _next_word_vowel(bare if re.fullmatch(r"[IVXLCDM]+\.", bare) else bare.rstrip("."))
        if vowel is None:
            return m.group(0)
        want = "az" if vowel else "a"
        if art.lower() == want:
            return m.group(0)
        if kind == "num" or (kind == "word" and want == "az"):
            new = want.capitalize() if art[0].isupper() else want
            return f"{new}{m.group('sp')}{word}"
        if kind == "acr":                                   # plain-word „az” (pronoun) is not reported
            flagged.append(f"„{art} {bare}” (check: {want})")
        return m.group(0)

    return _ART.sub(repl, text), flagged


# ── small text fixes ─────────────────────────────────────────────────────────
_DUP_PAREN = re.compile(rf"(?P<w>{_WORD}[\w\- ]{{2,60}}?)\s*\(\s*(?P=w)\s*\)", re.I)


def collapse_duplicate_parentheses(text):
    """„hanghullám (hanghullám)” → „hanghullám”."""
    return _DUP_PAREN.sub(lambda m: m.group("w"), text)


_EN_WORDS = {"the", "of", "and", "with", "for", "from", "force", "wave", "energy", "speed", "law",
             "theory", "effect", "field", "current", "voltage", "light", "sound", "heat", "mass"}


def english_gloss(text):
    """Parenthetical glosses written in English (only ASCII words, at least one real English word)."""
    hits = []
    for m in re.finditer(r"\(([A-Za-z][A-Za-z' \-]{2,40})\)", text):
        words = re.findall(r"[A-Za-z']+", m.group(1).lower())
        if any(w in _EN_WORDS for w in words):
            hits.append(m.group(0))
    return hits


# ── duplicate cards ──────────────────────────────────────────────────────────
def _tokens(s):
    return {w for w in re.findall(rf"{_WORD}{{4,}}", (s or "").lower())}


def _jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def dedupe_cards(cards, body_key="body", threshold=0.55, same_heading=0.35):
    """Drop later cards that restate an earlier one (same heading and a similar body, or a very
    similar body). Returns (kept, dropped_indexes)."""
    kept, dropped, sigs = [], [], []
    for i, c in enumerate(cards):
        if not isinstance(c, dict):
            kept.append(c); continue
        body = _tokens(c.get(body_key) or c.get("description") or "")
        head = re.sub(r"\W+", " ", (c.get("heading") or "").lower()).strip()
        dup = False
        for h2, b2 in sigs:
            sim = _jaccard(body, b2)
            if sim >= threshold or (head and head == h2 and sim >= same_heading):
                dup = True; break
        if dup:
            dropped.append(i)
        else:
            kept.append(c); sigs.append((head, body))
    return kept, dropped


# ── quiz ─────────────────────────────────────────────────────────────────────
_LABEL = re.compile(r"^\s*([A-Da-d])\s*[)\.]\s*")
_POSITIONAL = re.compile(r"^(minden\b|mindhárom|mindkét|mindegyik|egyik sem|nem\b.{0,12}\bsem\b|"
                         r"a fentiek|fenti)", re.I)
_TF = {"igaz", "hamis", "igen", "nem"}


def _option_bodies(options):
    return [_LABEL.sub("", o or "", count=1).strip() for o in options]


def _stable_rng(card):
    seed = hashlib.sha256(((card.get("question") or "") + "|".join(card.get("options") or [])).encode()).hexdigest()
    return random.Random(seed)


def shuffle_quiz_card(card):
    """Shuffle a multiple-choice card's options, relabel A–D, and move `correct` with the answer.
    Deterministic for a given card, so regenerating the same content is stable. True/false cards
    and cards with a malformed key are returned unchanged (and reported by `quiz_problems`)."""
    opts = card.get("options") or []
    key = (card.get("correct") or "").strip().upper()[:1]
    if len(opts) != 4 or key not in "ABCD":
        return card
    bodies = _option_bodies(opts)
    if {b.lower().rstrip(".") for b in bodies} <= _TF:
        return card
    idx_key = "ABCD".index(key)
    fixed_last = [i for i, b in enumerate(bodies) if _POSITIONAL.match(b)]
    movable = [i for i in range(4) if i not in fixed_last]
    order = movable[:]
    _stable_rng(card).shuffle(order)
    if order == movable and len(movable) > 1:            # make sure we really moved something
        order = movable[1:] + movable[:1]
    new_order = order + fixed_last                          # positional options stay last, in place order
    mapping = {old: new for new, old in enumerate(new_order)}
    out = dict(card)
    out["options"] = [f"{'ABCD'[n]}) {bodies[old]}" for n, old in enumerate(new_order)]
    out["correct"] = "ABCD"[mapping[idx_key]]
    exp = card.get("explanation") or ""
    if exp:
        inv = {"ABCD"[o]: "ABCD"[n] for o, n in mapping.items()}
        exp = re.sub(r"\b([A-D])\)", lambda m: f"{inv[m.group(1)]})", exp)
        exp = re.sub(r"\b([A-D])(\s+(?:opció|válasz|lehetőség|állítás)\w*)",
                     lambda m: f"{inv[m.group(1)]}{m.group(2)}", exp)
        out["explanation"] = exp
    return out


def quiz_problems(card):
    """Mechanical problems in one quiz card."""
    out = []
    opts = card.get("options") or []
    key = (card.get("correct") or "").strip().upper()[:1]
    if len(opts) != 4:
        out.append(f"{len(opts)} options (expected 4)")
        return out
    if key not in "ABCD":
        out.append(f"correct={card.get('correct')!r} is not A–D")
        return out
    bodies = [b.lower().rstrip(".") for b in _option_bodies(opts)]
    if len(set(bodies)) < 4:
        out.append("duplicate options")
    if any(_POSITIONAL.match(b) and i != 3 for i, b in enumerate(_option_bodies(opts))):
        out.append("„minden fenti / egyik sem” option is not last")
    if any(re.match(r"^(minden fenti|mindegyik)\b", b, re.I) for b in _option_bodies(opts)):
        out.append("„minden fenti” option (more than one answer can be right)")
    if not (card.get("explanation") or "").strip():
        out.append("no explanation")
    else:                                                   # does the explanation back a different option?
        exp = _tokens(card["explanation"])
        scores = [_jaccard(_tokens(b), exp) for b in _option_bodies(opts)]
        best = max(range(4), key=lambda i: scores[i])
        if best != "ABCD".index(key) and scores[best] >= 0.25 and scores[best] - scores["ABCD".index(key)] >= 0.2:
            out.append(f"explanation matches option {'ABCD'[best]} better than the key {key}")
    return out


def key_distribution_problem(cards, min_cards=5):
    """A quiz whose keys are all (or almost all) the same letter was not shuffled."""
    keys = [(c.get("correct") or "").strip().upper()[:1] for c in cards if isinstance(c, dict)]
    keys = [k for k in keys if k in "ABCD"]
    if len(keys) >= min_cards:
        top = max(set(keys), key=keys.count)
        if keys.count(top) / len(keys) >= 0.8:
            return f"{keys.count(top)}/{len(keys)} keys are {top}"
    return None


# ── card / block level entry points ──────────────────────────────────────────
PROSE_KEYS = ("heading", "body", "key_term", "description", "caption", "question", "explanation",
              "discovery", "today", "try_basic", "try_advanced", "link_hu")


def _map_strings(card, fn):
    out = dict(card)
    for k in PROSE_KEYS:
        if isinstance(out.get(k), str):
            out[k] = fn(out[k])
    if isinstance(out.get("options"), list):
        out["options"] = [fn(o) if isinstance(o, str) else o for o in out["options"]]
    return out


_UNSAFE = [
    (re.compile(r"(mikrohullámú|mikró)\w*.{0,80}(telefon|mobil|fém|alufólia|villa|tojás)|"
                r"(telefon|mobil|fém|alufólia|villa|tojás).{0,80}(mikrohullámú|mikró)", re.I | re.S),
     "microwave experiment with a phone/metal/egg"),
    (re.compile(r"(üveg\w*).{0,80}(fagyasztó|mélyhűtő|fagyaszt)", re.I | re.S),
     "glass container in a freezer (it can burst)"),
    (re.compile(r"\b(konnektor|dugalj|hálózati (feszültség|áram)|230 ?V)", re.I),
     "mains electricity in a home experiment"),
    (re.compile(r"(nyílt láng|gyújtó|benzin|spiritusz|tűz(et)? gyújt)", re.I), "open flame / flammable liquid"),
]


def unsafe_experiment(card):
    blob = " ".join(str(card.get(k) or "") for k in ("try_basic", "try_advanced"))
    return [label for rx, label in _UNSAFE if rx.search(blob)]


def card_problems(mode, card):
    """Issues that cannot be fixed mechanically. Used by lint and by postprocess."""
    issues = []
    if not isinstance(card, dict):
        return issues
    if mode == "quiz" or card.get("type") == "quiz":
        issues += [f"quiz: {p}" for p in quiz_problems(card)]
    blob = " ".join(str(card.get(k) or "") for k in PROSE_KEYS)
    blob += " " + " ".join(card.get("options") or []) if isinstance(card.get("options"), list) else ""
    issues += [f"English gloss {g}" for g in english_gloss(blob)]
    _, flagged = fix_articles(blob)
    issues += [f"article {f}" for f in flagged]
    if re.search(_DUP_PAREN, blob):
        issues.append("duplicated parenthesis")
    if mode == "experiment" or card.get("type") == "experiment":
        issues += [f"unsafe experiment: {u}" for u in unsafe_experiment(card)]
    return issues


def block_problems(mode, cards):
    issues = []
    if mode in ("text", "story") and cards:
        _, dropped = dedupe_cards(cards)
        issues += [f"card {i} duplicates an earlier card" for i in dropped]
    if mode == "quiz":
        p = key_distribution_problem(cards)
        if p:
            issues.append(f"quiz not shuffled: {p}")
    return issues


def postprocess(mode, obj):
    """Clean one generated block. `obj` is {"title", "cards": [...]} (or a bare card list).
    Returns (obj, notes): notes describe what changed or what still needs a look."""
    wrapped = isinstance(obj, dict) and "cards" in obj
    cards = obj["cards"] if wrapped else (obj if isinstance(obj, list) else [obj])
    notes = []

    def clean(s):
        s = collapse_duplicate_parentheses(s)
        s, _ = fix_articles(s)
        return s

    cards = [_map_strings(c, clean) if isinstance(c, dict) else c for c in cards]
    if mode in ("text", "story"):
        cards, dropped = dedupe_cards(cards)
        if dropped:
            notes.append(f"dropped duplicate cards {dropped}")
    if mode == "quiz":
        cards = [shuffle_quiz_card(c) if isinstance(c, dict) else c for c in cards]
    for i, c in enumerate(cards):
        notes += [f"card {i}: {p}" for p in card_problems(mode, c)]
    if wrapped:
        obj = {**obj, "cards": cards}
        return obj, notes
    return (cards if isinstance(obj, list) else cards[0]), notes


def has_blocking_problem(notes):
    """Problems worth one regeneration retry (the model produced a broken key or options)."""
    return any(n for n in notes if "is not A–D" in n or "options (expected 4)" in n
               or "duplicate options" in n or "explanation matches option" in n)
