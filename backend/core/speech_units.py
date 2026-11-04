"""SI units, powers of ten and formula letters for „Felolvasás” — what a speech engine gets wrong in a
physics card, and how it is written so a voice reads it the way a Hungarian teacher would.

Stdlib-only and imported by core/speech.py, so the API, the audio generator and the browser voice all
get the same text (see the module docstring there).

Everything below was measured, not assumed: the audio is made with Piper, whose Hungarian text
front end is espeak-ng, and the cases are the ones that voice actually reads wrongly:

  "10 s alatt"      → „tíz s” — a lone s is taken for the old conjunction "s" and read as a bare consonant
  "50 m-t"          → „em-t” — the symbol is spelled, the suffix is a consonant on its own
  "2000 N erő"      → the N is dropped altogether
  "5 T"             → „ötöt” — the T is read as an accusative ending
  "336 000 J"       → „jé”;   "2 Hz" → „há zé”;   "0,5 Ω" → „omega”;   "kcal" → „ktsal”
  "joule", "newton" → read as written („jóle”, „nevton”); the Hungarian names sound „dzsúl”, „nyúton”
  "10⁻⁶"            → the exponent is silent, so a power of ten is read as plain „tíz”
  "⅓", "‰"          → read in English / not at all

Rules are deliberately narrow. A symbol is only a unit directly after a number (so a bare m, N or s in
a formula stays a variable), and a wrong expansion is silent and wrong, so anything ambiguous is left
alone and falls back to the voice's own reading.
"""
from __future__ import annotations

import re

_SUPERSCRIPT = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_LETTER = "A-Za-zÁÉÍÓÖŐÚÜŰáéíóöőúüű"

# ── the unit table ──────────────────────────────────────────────────────────────────────────────
_PREFIXES = {"T": "tera", "G": "giga", "M": "mega", "k": "kilo", "h": "hekto", "d": "deci", "c": "centi",
             "m": "milli", "µ": "mikro", "μ": "mikro", "n": "nano", "f": "femto"}

# symbol: (spoken, spoken when a prefix is attached, prefixes it takes, how a text spells it out).
# Respellings (dzsúl, nyúton, paszkál, …) are what the voice needs to be fed to say the Hungarian
# pronunciation; the text is only ever heard, never shown.
_BASES = {
    "m": ("méter", "méter", "kdcmµμnf", ""),
    "g": ("gramm", "gramm", "km", ""),
    "s": ("másodperc", "szekundum", "mµμn", "szekundum"),
    "min": ("perc", "perc", "", ""),
    "h": ("óra", "óra", "", ""),
    "N": ("nyúton", "nyúton", "kmµμ", "newton"),
    "J": ("dzsúl", "dzsúl", "kM", "joule"),
    "W": ("watt", "watt", "kMGT", ""),
    "Wh": ("wattóra", "wattóra", "kMGT", ""),
    "V": ("volt", "volt", "kmMµμ", ""),
    "A": ("amper", "amper", "mµμ", ""),
    "Ω": ("ohm", "ohm", "kM", ""),
    "Hz": ("hertz", "hertz", "kMG", ""),
    "Pa": ("paszkál", "paszkál", "hkM", "pascal"),
    "bar": ("bar", "bar", "m", ""),
    "eV": ("elektronvolt", "elektronvolt", "kMG", ""),
    "C": ("kulomb", "kulomb", "mµμn", "coulomb"),
    "Wb": ("véber", "véber", "m", "weber"),
    "T": ("teszla", "teszla", "mµμn", "tesla"),
    "K": ("kelvin", "kelvin", "", ""),
    "Bq": ("bekkerel", "bekkerel", "kM", "becquerel"),
    "Sv": ("szívert", "szívert", "mµμ", "sievert"),
    "dB": ("decibel", "decibel", "", ""),
    "l": ("liter", "liter", "mcd", ""),
    "cal": ("kalória", "kalória", "k", ""),
    "lm": ("lumen", "lumen", "", ""),
    "Ft": ("forint", "forint", "", ""),
    "Ah": ("amperóra", "amperóra", "m", ""),
    "Gy": ("grej", "grej", "mµμ", "gray"),
    "ha": ("hektár", "hektár", "", ""),
}

_SAY: dict[str, str] = {}      # symbol → spoken name
_ROOTS: dict[str, tuple] = {}  # symbol → the words a text uses when it spells the unit out
for _sym, (_say, _prefixed, _takes, _alias) in _BASES.items():
    _SAY[_sym] = _say
    _ROOTS[_sym] = tuple(x for x in (_say, _alias) if x)
    for _p in _takes:
        _SAY[_p + _sym] = _PREFIXES[_p] + _prefixed
        _ROOTS[_p + _sym] = tuple(_PREFIXES[_p] + x for x in (_prefixed, _alias) if x)

_LENGTHS = {"m", "km", "dm", "cm", "mm", "µm", "μm", "nm"}      # m² → négyzetméter, not „méter négyzet”
_SYM = "|".join(re.escape(s) for s in sorted(_SAY, key=len, reverse=True))
_POWER = r"(?:[²³]|\^[23])"
_TERM = rf"(?:{_SYM}){_POWER}?"
_PRODUCT = rf"{_TERM}(?:\s?[·⋅]\s?{_TERM})*"
_EXPR = rf"{_PRODUCT}(?:/(?:{_TERM}|\({_PRODUCT}\)))?"        # km/h, kg·m/s, J/(kg·K), W/m²
_SUFFIX = r"(?:-(?P<suf>[a-záéíóöőúüű]{1,7}))?"               # „50 m-t”, „60 W-os”, „20 K-nel”
_END = rf"(?![{_LETTER}0-9_²³])"

# A unit symbol is a unit only right after a number (or „ezer”, „millió”), written with its space.
_AFTER_NUMBER = re.compile(rf"(?P<num>[\d{_SUPERSCRIPT}]|\bezer|\bmillió|\bmilliárd) (?P<expr>{_EXPR}){_SUFFIX}{_END}")
_CELSIUS = re.compile(rf"(?P<num>\d) ?°\s?C{_SUFFIX}(?![{_LETTER}0-9_])")
# Compounds with a slash read as „em per es” when left alone, and these cannot be a formula
# (m/V is mass over volume, so it is deliberately not here). Anything else needs a number in front.
_STANDALONE = ["m/s²", "m/s", "km/h", "km/s", "N/C", "V/m", "N/m", "kg/m³", "g/cm³", "g/m³", "J/kg", "kJ/kg",
               "MJ/kg", "W/m²", "MV/m", "lm/W", "Ft/kWh", "g/kWh", "MJ/m³", "m²/s", "m³/s", "kg/s",
               "km²", "m²", "cm²", "mm²", "m³", "dm³", "cm³", "kg·m/s", "J/(kg·K)", "J/(kg · K)", "kJ/(kg·K)",
               "kJ/(kg · K)", "W/(m·K)", "W/(m · K)", "W/(m²·K)", "W/(m² · K)"]
_STANDALONE_RX = re.compile(
    r"(?<![\w/])(?P<expr>" + "|".join(re.escape(x) for x in sorted(_STANDALONE, key=len, reverse=True)) + rf"){_SUFFIX}(?![\w/²³])")
_PER_KELVIN = re.compile(r"(?<![\w/.,])1/K(?![\w/])")


def _lengthened(stem: str) -> str:
    """Hungarian lengthens a final a/e before a suffix: óra → órá-, tesla → teszlá-."""
    return stem[:-1] + {"a": "á", "e": "é"}[stem[-1]] if stem[-1] in "ae" else stem


def _accusative(stem: str) -> str:
    """The -t form: métert, wattot, hertzet, dzsúlt, órát. Written suffixes are used as they stand, but a
    bare „-t” has lost its linking vowel, which has to come back to be read (m-t → métert)."""
    if stem[-1] in "ae":
        return _lengthened(stem) + "t"
    if stem[-1] in "rln" or stem.endswith("ly"):
        return stem + "t"
    vowels = [c for c in stem if c in "aáeéiíoóöőuúüű"]
    harmony = [c for c in vowels if c not in "ií"] or vowels
    last = harmony[-1] if harmony else "o"
    return stem + ("öt" if last in "öőüű" else "et" if last in "eé" else "ot")


def _attach(phrase: str, suffix: str | None) -> str:
    """phrase + the Hungarian suffix the text wrote after the symbol, joined into one word."""
    if not suffix:
        return phrase
    head, _, stem = phrase.rpartition(" ")
    suffix = suffix.lower()
    if suffix == "t":
        word = _accusative(stem)
    else:
        stem = _lengthened(stem)
        if len(stem) > 1 and stem[-1] == stem[-2] == suffix[0]:
            suffix = suffix[1:]                   # watt + tal → wattal, gramm + mal → grammal
        word = stem + suffix
    return f"{head} {word}" if head else word


def _term(term: str, denominator: bool) -> str:
    m = re.fullmatch(rf"({_SYM})(²|³|\^2|\^3)?", term.strip())
    sym, power = m.group(1), m.group(2)
    if power:
        word = "négyzet" if power in ("²", "^2") else "köb"
        if sym in _LENGTHS:
            return word + _SAY[sym]
        return "szekundum" + word if sym == "s" else f"{_SAY[sym]} {word}"
    if sym == "s":
        return "szekundum" if denominator else "másodperc"
    return _SAY[sym]


def _spoken(expr: str, suffix: str | None = None) -> str:
    top, _, bottom = expr.partition("/")
    parts = [" ".join(_term(t, False) for t in re.split(r"[·⋅]", top) if t.strip())]
    if bottom:
        parts.append(" ".join(_term(t, True) for t in re.split(r"[·⋅]", bottom.strip("()")) if t.strip()))
    return _attach(" per ".join(parts), suffix)


# ── spelled-out names ───────────────────────────────────────────────────────────────────────────
_NAMES = {"newton": "nyúton", "joule": "dzsúl", "pascal": "paszkál", "becquerel": "bekkerel", "tesla": "teszla",
          "coulomb": "kulomb", "celsius": "celziusz", "sievert": "szívert", "weber": "véber"}
_NAMES_RX = re.compile(r"\b(" + "|".join(_NAMES) + ")", re.I)


def _respell_name(m: re.Match) -> str:
    word = _NAMES[m.group(1).lower()]
    return word[0].upper() + word[1:] if m.group(1)[0].isupper() else word


# ── „méter per másodperc (m/s)” — the symbol repeats what was just said ──────────────────────────
_PARENTHETICAL = re.compile(rf"(?P<word>[^\W\d_]+(?:\s+per\s+[^\W\d_]+)?)\s*\((?P<expr>{_EXPR})\)")
_TONNE = re.compile(r"(\btonn\w*)\s*\(t\)", re.I)
_NOT_EXPANDED_ALONE = {"min"}       # „minimum (min)” must stay „minimum (min)”


def _names_of(term: str) -> tuple:
    m = re.fullmatch(rf"({_SYM})", term.strip())
    return _ROOTS[m.group(1)] if m else ()


def _repeats(word: str, expr: str) -> bool:
    """Does `word` (the word before the bracket) already say what the symbol in the bracket says?"""
    top, _, bottom = expr.partition("/")
    word = word.lower()
    if not bottom and re.fullmatch(_TERM, expr) and re.search(_POWER, expr):
        return word.startswith(_spoken(expr))
    if bottom:
        return any(word.startswith(f"{a} per {b}") or word.startswith(f"{a} per {_lengthened(b)}")
                   for a in _names_of(top) for b in _names_of(bottom.strip("()")))
    return any(word.startswith(root) or word.startswith(_lengthened(root)) for root in _names_of(top))   # óra → órát


def _parenthetical(m: re.Match) -> str:
    word, expr = m.group("word"), m.group("expr")
    if _repeats(word, expr):
        return word
    if (len(expr) > 1 or "/" in expr) and expr not in _NOT_EXPANDED_ALONE and not re.search(_POWER, expr):
        return f"{word} ({_spoken(expr)})"
    return m.group(0)                # a single letter in brackets is a variable: „az út (s)”;  (m²) is left to _STANDALONE


# ── powers of ten: 10⁻⁶ ─────────────────────────────────────────────────────────────────────────
_POWER_OF_TEN = re.compile(rf"(?<![\d,.{_SUPERSCRIPT}])10(?P<neg>⁻)?(?P<exp>[{_SUPERSCRIPT}]+)")
_ONES = ["", "egyedik", "kettedik", "harmadik", "negyedik", "ötödik", "hatodik", "hetedik", "nyolcadik", "kilencedik"]
_TENS = ["", "tizen", "huszon", "harminc", "negyven", "ötven", "hatvan", "hetven", "nyolcvan", "kilencven"]
_TENTH = ["", "tizedik", "huszadik", "harmincadik", "negyvenedik", "ötvenedik", "hatvanadik", "hetvenedik",
          "nyolcvanadik", "kilencvenedik"]


def _ordinal(n: int) -> str:
    if n == 0:
        return "nulladik"
    if n == 1:
        return "első"
    if n == 2:
        return "második"
    tens, ones = divmod(n, 10)
    return _TENTH[tens] if not ones else _TENS[tens] + _ONES[ones]


def _on_the(n: int) -> str:
    """„a hatodikon”, „az ötödiken”, „az elsőn” — the exponent as Hungarian says it after „tíz”."""
    word = _ordinal(n)
    vowels = [c for c in word[:-1] if c in "aáeéiíoóöőuúüű"]
    harmony = [c for c in vowels if c not in "ií"] or vowels
    on = word + "n" if word == "első" else word + ("en" if harmony and harmony[-1] in "eéöőüű" else "on")
    return ("az " if word[0] in "aáeéiíoóöőuúüű" else "a ") + on


def _power_of_ten(m: re.Match) -> str:
    n = int("".join(str(_SUPERSCRIPT.index(c)) for c in m.group("exp")))
    if n > 99:
        return m.group(0)
    return "tíz " + ("a mínusz " + _ordinal_on(n) if m.group("neg") else _on_the(n))


def _ordinal_on(n: int) -> str:
    return _on_the(n).split(" ", 1)[1]


# ── the entry points ────────────────────────────────────────────────────────────────────────────
_FRACTIONS = [(re.compile(r"(\d)⅓"), r"\1 és egyharmad"), (re.compile(r"(\d)⅔"), r"\1 és kétharmad"),
              (re.compile(r"⅓"), "egyharmad"), (re.compile(r"⅔"), "kétharmad"), (re.compile(r"¼"), "egynegyed"),
              (re.compile(r"¾"), "háromnegyed"), (re.compile(r"\s*‰"), " ezrelék")]


def units(text: str) -> str:
    """Spoken names for units and powers of ten, applied before the formula-symbol rules."""
    s = _NAMES_RX.sub(_respell_name, text)
    s = _TONNE.sub(r"\1", s)
    s = _PARENTHETICAL.sub(_parenthetical, s)
    s = _CELSIUS.sub(lambda m: m.group("num") + " " + _attach("Celziusz-fok", m.group("suf")), s)
    s = _AFTER_NUMBER.sub(lambda m: f"{m.group('num')} {_spoken(m.group('expr'), m.group('suf'))}", s)
    s = _STANDALONE_RX.sub(lambda m: _spoken(m.group("expr"), m.group("suf")), s)
    s = _PER_KELVIN.sub("egy per kelvin", s)
    s = _POWER_OF_TEN.sub(_power_of_ten, s)      # after the units: „10⁹ N” needs its superscript to be a number
    for rx, rep in _FRACTIONS:
        s = rx.sub(rep, s)
    return s


# Acronyms espeak-ng reads as a word where Hungarians spell the letters (measured: ÁVH → „áv-h”, EKG →
# „ekg”, USA → „úsa”, GDP in English). Only the ones whose reading is certain; the rest it gets right.
_SPELLED = {"ÁVH": "á vé há", "EKG": "é ká gé", "EEG": "é é gé", "USA": "ú es á", "UV": "ú vé", "EU": "é ú",
            "GDP": "gé dé pé", "IMF": "i em ef", "INF": "i en ef", "ABS": "á bé es", "WTO": "vé té ó",
            "WHO": "vé há ó", "MRI": "em er i", "CSE": "cé es é", "ISS": "i es es", "IPCC": "i pé cé cé",
            "SI": "es i", "AM": "á em", "AC": "á cé", "DC": "dé cé", "SDI": "es dé i", "TVA": "té vé á",
            "NSDAP": "en es dé á pé"}
_SPELLED_RX = re.compile(r"(?<![\wÁÉÍÓÖŐÚÜŰ])(" + "|".join(sorted(_SPELLED, key=len, reverse=True)) + r")(?![\wáéíóöőúüű])")


def acronyms(text: str) -> str:
    return _SPELLED_RX.sub(lambda m: _SPELLED[m.group(1)], text)


_RATIO = re.compile(r"\d+(?: : \d+){2,}")           # „1 : 3 : 5 : 7” is a proportion, not a division
_DIVISION = re.compile(r"(?<=\S) : (?=\S)")
_LONE_S = re.compile(r"(?<![\w.\-])s(?![\w\-])")
_LONE_A = re.compile(r"\b(szorozva|osztva|plusz|mínusz|egyenlő) a(?=[).,;:?!\]]|$| egyenlő| szorozva| osztva| plusz| mínusz)")


def formulas(text: str) -> str:
    """Division colons and the formula letters a voice reads as a different word."""
    s = _RATIO.sub(lambda m: m.group(0).replace(" : ", ", "), text)
    s = _DIVISION.sub(" osztva ", s)
    s = re.sub(r"(?<![\w/.\-])Joszif V\.", "Joszif Visszarionovics", s)
    s = _LONE_S.sub("es", s)                 # the letter s: left alone it is read as the conjunction „s”
    s = re.sub(r"(?<![\w])a egyenlő", "á egyenlő", s)      # acceleration: „az” would stand before a vowel
    s = _LONE_A.sub(r"\1 á", s)
    return re.sub(r"\(a\)", "(á)", s)
