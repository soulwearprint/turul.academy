"""python3 -m unittest discover -s backend/tests   (stdlib only)

What „Felolvasás” says for units, powers of ten and formula letters. The cases are the ones the Hungarian
voice (espeak-ng, via Piper) was measured to read wrongly — see the docstring of core/speech_units.py. The
expected strings are what a teacher would say, so a failure here means the audio would sound wrong.
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import speech as S  # noqa: E402
from core import speech_units as U  # noqa: E402


class UnitsAfterANumber(unittest.TestCase):
    def test_a_bare_symbol_is_spoken_as_the_unit(self):
        for text, spoken in [
            ("10 s alatt", "10 másodperc alatt"),          # a lone s is read as the conjunction, a bare consonant
            ("2000 N erő", "2000 nyúton erő"),             # the N used to be dropped altogether
            ("336 000 J", "336 000 dzsúl"),                 # „jé”
            ("50 Hz", "50 hertz"),
            ("350 Ω", "350 ohm"),                           # „omega”
            ("1 kWh", "1 kilowattóra"),
            ("800 kcal", "800 kilokalória"),
            ("2 T", "2 teszla"),                            # „ötöt”
            ("0,02 A", "0,02 amper"),
            ("90 dB", "90 decibel"),
            ("2,3 eV", "2,3 elektronvolt"),
            ("2 bar", "2 bar"),
            ("100 g", "100 gramm"),
            ("5 l", "5 liter"),
            ("40 Ft", "40 forint"),
            ("12 millió Ft", "12 millió forint"),
            ("3 000 mAh", "3 000 milliamperóra"),
            ("7 μs", "7 mikroszekundum"),
            ("7,4 fm", "7,4 femtométer"),
            ("5 ha", "5 hektár"),
        ]:
            self.assertEqual(S.clean(text), spoken, text)

    def test_a_suffix_after_the_symbol_becomes_part_of_the_word(self):
        for text, spoken in [
            ("50 m-t", "50 métert"),                        # was „em-t”
            ("a 100 m-es táv", "a 100 méteres táv"),
            ("60 W-os izzó", "60 wattos izzó"),
            ("230 V-ra", "230 voltra"),
            ("20 K-nel", "20 kelvinnel"),
            ("100 g-mal", "100 grammal"),
            ("3 W-tal", "3 wattal"),
            ("1 V-tal", "1 volttal"),
            ("10 N-nal", "10 nyútonnal"),
            ("46 Ω-os", "46 ohmos"),
            ("1 kWh-t", "1 kilowattórát"),                  # a/e lengthen: óra → órát
            ("2 h-n át", "2 órán át"),
            ("800 kcal-s pizza", "800 kilokalóriás pizza"),
            ("120 km-t", "120 kilométert"),
            ("2 nC-os", "2 nanokulombos"),
            ("3 W-ot", "3 wattot"),
            ("10 s-ig", "10 másodpercig"),
        ]:
            self.assertEqual(S.clean(text), spoken, text)

    def test_compounds_and_powers(self):
        for text, spoken in [
            ("60 km/h-val", "60 kilométer per órával"),
            ("1,62 m/s²", "1,62 méter per szekundumnégyzet"),
            ("917 kg/m³", "917 kilogramm per köbméter"),
            ("19,3 g/cm³", "19,3 gramm per köbcentiméter"),
            ("1361 W/m²", "1361 watt per négyzetméter"),
            ("676 000 km²", "676 000 négyzetkilométer"),
            ("4 kg·m/s lendületű", "4 kilogramm méter per szekundum lendületű"),
            ("4,19 kJ/(kg·K)", "4,19 kilodzsúl per kilogramm kelvin"),
            ("5 W/(m² · K)", "5 watt per négyzetméter kelvin"),
            ("40 Ft/kWh-val", "40 forint per kilowattórával"),
            ("1 N · m", "1 nyúton méter"),
            ("9 · 10⁹ N · m²/C²", "9 szorozva tíz a kilencediken nyúton négyzetméter per kulomb négyzet"),
        ]:
            self.assertEqual(S.clean(text), spoken, text)

    def test_a_slash_unit_without_a_number_is_still_a_unit(self):
        self.assertEqual(S.clean("sebesség (m/s)"), "sebesség (méter per szekundum)")
        self.assertEqual(S.clean("egysége N/C, vagyis V/m"), "egysége nyúton per kulomb, vagyis volt per méter")
        self.assertEqual(S.clean("mértékegysége W/(m · K)."), "mértékegysége watt per méter kelvin.")
        self.assertEqual(S.clean("Mi a térfogat? A: m³."), "Mi a térfogat? A: köbméter.")

    def test_celsius(self):
        self.assertEqual(S.clean("−50 °C hideg"), "−50 Celziusz-fok hideg")
        self.assertEqual(S.clean("15 °C-on"), "15 Celziusz-fokon")
        self.assertEqual(S.clean("0 °C-os"), "0 Celziusz-fokos")


class WhatStaysAVariable(unittest.TestCase):
    """A symbol is a unit only right after a number. Everywhere else it is a letter in a formula, and a
    wrong expansion is silent and wrong."""

    def test_formula_letters_are_not_units(self):
        self.assertEqual(S.clean("ρ = m/V"), "ró egyenlő m/V")                  # mass over volume, not metre per volt
        self.assertEqual(S.clean("F = m * g"), "F egyenlő m szorozva g")
        self.assertEqual(S.clean("a hosszúság jele l"), "a hosszúság jele l")
        self.assertEqual(S.clean("a térfogat jele V"), "a térfogat jele V")
        self.assertEqual(S.clean("U = I * R"), "U egyenlő I szorozva R")
        self.assertEqual(S.clean("t = √(2h/g)"), "t egyenlő √(2h/g)")          # „2h” is 2·h, not two hours

    def test_a_number_that_is_not_followed_by_a_unit_is_left_alone(self):
        self.assertEqual(S.clean("5 mellett"), "5 mellett")
        self.assertEqual(S.clean("a 3 A osztály"), "a 3 amper osztály")        # known limit: a number + capital A is an ampere
        self.assertEqual(S.clean("5m"), "5m")                                   # attached symbols are not touched
        self.assertEqual(S.clean("3 t"), "3 t")                                 # t is tonne or time: not guessed

    def test_the_letter_s_alone_is_spelled_so_it_is_not_read_as_a_conjunction(self):
        self.assertEqual(S.clean("v = s : t"), "v egyenlő es osztva t")
        self.assertEqual(S.clean("az út (s) és az idő (t)"), "az út (es) és az idő (t)")
        self.assertEqual(S.clean("a másodperc jele s."), "a másodperc jele es.")
        self.assertEqual(S.clean("t = s/v"), "t egyenlő es/v")

    def test_the_letter_a_in_a_formula_is_not_the_article(self):
        self.assertEqual(S.clean("Ha a = 1 m/s²"), "Ha á egyenlő 1 méter per szekundumnégyzet")
        self.assertEqual(S.clean("a gyorsulás (a) fogalma"), "a gyorsulás (á) fogalma")
        self.assertEqual(S.clean("a nehéz test"), "a nehéz test")               # an ordinary article is untouched
        self.assertEqual(S.clean("szorozva a tömeggel"), "szorozva a tömeggel")

    def test_division_colon_but_not_a_proportion(self):
        self.assertEqual(S.clean("230 : 46 = 5 A"), "230 osztva 46 egyenlő 5 amper")
        self.assertEqual(S.clean("az arány 1 : 3 : 5 : 7."), "az arány 1, 3, 5, 7.")
        self.assertEqual(S.clean("Kulcsfogalom: pálya"), "Kulcsfogalom: pálya")


class SymbolsThatRepeatTheWord(unittest.TestCase):
    def test_the_bracket_after_the_spoken_unit_is_dropped(self):
        self.assertEqual(S.clean("a méter per másodperc (m/s)."), "a méter per másodperc.")
        self.assertEqual(S.clean("kilométer per óra (km/h)"), "kilométer per óra")
        self.assertEqual(S.clean("grammot (g), nagyobbakra a tonnát (t)"), "grammot, nagyobbakra a tonnát")
        self.assertEqual(S.clean("amperben (A) mérjük"), "amperben mérjük")
        self.assertEqual(S.clean("az órát (h) és a percet (min)"), "az órát és a percet")
        self.assertEqual(S.clean("köbdeciméterrel (dm³) egyenlő"), "köbdeciméterrel egyenlő")

    def test_a_single_letter_in_brackets_is_a_variable_and_stays(self):
        self.assertEqual(S.clean("A sebesség (v) megmutatja"), "A sebesség (v) megmutatja")
        self.assertEqual(S.clean("a tömeg (m)"), "a tömeg (m)")
        self.assertEqual(S.clean("az erő (N)"), "az erő (N)")
        self.assertEqual(S.clean("minimum (min)"), "minimum (min)")             # not „perc”

    def test_a_bracketed_unit_that_adds_something_is_spoken(self):
        self.assertEqual(S.clean("a tömeg (kg)"), "a tömeg (kilogramm)")


class Names(unittest.TestCase):
    def test_hungarian_pronunciation_of_unit_and_scientist_names(self):
        self.assertEqual(S.clean("Newton törvénye"), "Nyúton törvénye")
        self.assertEqual(S.clean("a joule és Joule-hő"), "a dzsúl és Dzsúl-hő")
        self.assertEqual(S.clean("Nikola Tesla"), "Nikola Teszla")
        self.assertEqual(S.clean("Anders Celsius"), "Anders Celziusz")
        self.assertEqual(S.clean("Max Weber"), "Max Véber")
        self.assertEqual(S.clean("Coulomb-törvény"), "Kulomb-törvény")
        self.assertEqual(S.clean("Pascal"), "Paszkál")
        self.assertEqual(S.clean("Joszif V. Sztálin"), "Joszif Visszarionovics Sztálin")


class PowersOfTen(unittest.TestCase):
    def test_exponent_is_read(self):
        for text, spoken in [
            ("10⁻⁶", "tíz a mínusz hatodikon"),
            ("10¹⁸ elektron", "tíz a tizennyolcadikon elektron"),
            ("10⁵ Pa", "tíz az ötödiken paszkál"),
            ("10² és 10³", "tíz a másodikon és tíz a harmadikon"),
            ("6,2 · 10²⁰", "6,2 szorozva tíz a huszadikon"),
            ("10¹", "tíz az elsőn"),
            ("10⁰", "tíz a nulladikon"),
            ("10⁻¹¹", "tíz a mínusz tizenegyediken"),
            ("10²¹", "tíz a huszonegyediken"),
        ]:
            self.assertEqual(S.clean(text), spoken, text)

    def test_a_number_that_merely_contains_10_is_not_a_power(self):
        self.assertNotIn("tíz a", S.clean("110² és 1,10²"))

    def test_fractions_and_per_mille(self):
        self.assertEqual(S.clean("33⅓ fordulat"), "33 és egyharmad fordulat")
        self.assertEqual(S.clean("kb. 40‰"), "körülbelül 40 ezrelék")


class Acronyms(unittest.TestCase):
    def test_letters_are_spelled_where_the_voice_would_read_a_word(self):
        self.assertEqual(S.clean("az ÁVH és az EKG"), "az á vé há és az é ká gé")
        self.assertEqual(S.clean("USA-ban, UV-fény, SI-mértékegység"), "ú es á-ban, ú vé-fény, es i-mértékegység")

    def test_acronyms_the_voice_reads_correctly_are_left_alone(self):
        self.assertEqual(S.clean("NATO, ENSZ, LED"), "NATO, ENSZ, LED")

    def test_only_whole_tokens_are_replaced(self):
        self.assertEqual(S.clean("USAF EUR"), "USAF EUR")


class GrammarOfTheSuffix(unittest.TestCase):
    def test_accusative(self):
        for stem, acc in [("méter", "métert"), ("kilométer", "kilométert"), ("watt", "wattot"), ("volt", "voltot"),
                          ("gramm", "grammot"), ("ohm", "ohmot"), ("hertz", "hertzet"), ("másodperc", "másodpercet"),
                          ("perc", "percet"), ("dzsúl", "dzsúlt"), ("nyúton", "nyútont"), ("kelvin", "kelvint"),
                          ("óra", "órát"), ("teszla", "teszlát"), ("kalória", "kalóriát"), ("liter", "litert"),
                          ("amper", "ampert"), ("bar", "bart"), ("lumen", "lument"), ("forint", "forintot"),
                          ("Celziusz-fok", "Celziusz-fokot")]:
            self.assertEqual(U._accusative(stem), acc)

    def test_ordinal_exponent_with_article_and_harmony(self):
        for n, said in [(1, "az elsőn"), (2, "a másodikon"), (3, "a harmadikon"), (4, "a negyediken"), (5, "az ötödiken"),
                        (6, "a hatodikon"), (7, "a hetediken"), (8, "a nyolcadikon"), (9, "a kilencediken"),
                        (10, "a tizediken"), (12, "a tizenkettediken"), (20, "a huszadikon"), (50, "az ötvenediken")]:
            self.assertEqual(U._on_the(n), said)


class Safety(unittest.TestCase):
    def test_every_unit_in_the_table_is_spoken_and_leaves_no_symbol_behind(self):
        for sym, say in U._SAY.items():
            if say == sym:   # already a word the voice reads correctly (bar), so nothing to replace
                continue
            out = S.clean(f"5 {sym}")
            self.assertNotEqual(out, f"5 {sym}", sym)
            self.assertNotIn(sym, out.split()[1:], sym)
            self.assertTrue(out.startswith("5 "), sym)
            self.assertIn(say if sym != "s" else "másodperc", out, sym)

    def test_the_slash_whitelist_all_parses(self):
        for expr in U._STANDALONE:
            self.assertTrue(U._spoken(expr), expr)
            self.assertNotIn("/", S.clean(f"a {expr} egység").replace(" egység", ""), expr)

    def test_a_failing_rule_never_breaks_the_text(self):
        with mock.patch.object(S, "units", side_effect=RuntimeError("boom")):
            out = S.clean("10 s alatt, **fontos**")
        self.assertNotIn("másodperc", out)   # the failed rule changed nothing...
        self.assertIn("fontos", out)         # ...and every other rule still ran
        self.assertNotIn("**", out)

    def test_odd_input_does_not_raise(self):
        for text in ["10⁹⁹⁹", "5 m/", "5 m·", "(m/s)", "1/K", "5 m/s/s", "5 -", "⅓", "‰", "5 W-", "5 m-ábra", "((5 m))", "1 000 000 000 000 s"]:
            self.assertIsInstance(S.clean(text), str)


if __name__ == "__main__":
    unittest.main()
