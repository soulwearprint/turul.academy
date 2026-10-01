"""python3 -m unittest discover -s backend/tests   (stdlib only; no Supabase, no env needed)"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import speech as S  # noqa: E402


class CleanTests(unittest.TestCase):
    def test_abbreviations(self):
        self.assertEqual(S.clean("Kr. e. 490-ben"), "Krisztus előtt 490-ben")
        self.assertEqual(S.clean("i. sz. 476"), "időszámításunk szerint 476")
        self.assertEqual(S.clean("pl. a víz, stb."), "például a víz, és így tovább")
        self.assertEqual(S.clean("Sok minden, stb. Aztán"), "Sok minden, és így tovább. Aztán")
        self.assertEqual(S.clean("id. Antall József"), "idősebb Antall József")
        self.assertEqual(S.clean("Szt. István"), "Szent István")

    def test_abbreviation_inside_a_word_is_left_alone(self):
        self.assertEqual(S.clean("Az ipl. nem rövidítés"), "Az ipl. nem rövidítés")
        self.assertEqual(S.clean("kid. nem"), "kid. nem")

    def test_units_only_after_a_number(self):
        self.assertEqual(S.clean("72 km/h"), "72 kilométer per óra")
        self.assertEqual(S.clean("9,8 m/s²"), "9,8 méter per szekundumnégyzet")
        self.assertEqual(S.clean("20 m/s"), "20 méter per szekundum")
        self.assertEqual(S.clean("5 kg"), "5 kilogramm")
        self.assertEqual(S.clean("20 °C"), "20 Celsius-fok")
        self.assertEqual(S.clean("a km/h mértékegység"), "a km/h mértékegység")
        self.assertEqual(S.clean("a kg jele"), "a kg jele")

    def test_formulas_are_read_the_way_a_teacher_says_them(self):
        self.assertEqual(S.clean("F = m * a"), "F egyenlő m szorozva a")
        self.assertEqual(S.clean("m = ρ · V"), "m egyenlő ró szorozva V")
        self.assertEqual(S.clean("g·T² / (4π²) ≈ 0,25"), "g szorozva T négyzet osztva (4π négyzet) körülbelül egyenlő 0,25")
        self.assertEqual(S.clean("Q = I² * R * t"), "Q egyenlő I négyzet szorozva R szorozva t")
        self.assertEqual(S.clean("p = m / v"), "p egyenlő m osztva v")
        self.assertEqual(S.clean("(m*g)"), "(m szorozva g)")
        self.assertEqual(S.clean("a + b"), "a plusz b")
        self.assertEqual(S.clean("(×10, ×100)"), "(szorozva 10, szorozva 100)")
        self.assertEqual(S.clean("Megfigyelés → Feltevés"), "Megfigyelés, majd Feltevés")
        self.assertEqual(S.clean("hibahatár ±0,5"), "hibahatár plusz-mínusz 0,5")

    def test_symbols_inside_ordinary_text_are_left_alone(self):
        self.assertEqual(S.clean("a 10² nagyság"), "a 10² nagyság")
        self.assertEqual(S.clean("és/vagy"), "és/vagy")
        self.assertEqual(S.clean("a μm és a ρ-érték"), "a μm és a ró-érték")

    def test_markdown_and_spaces(self):
        self.assertEqual(S.clean("**fontos**  szó itt"), "fontos szó itt")
        self.assertEqual(S.clean(None), "")
        self.assertEqual(S.clean(42), "42")


class EntryTests(unittest.TestCase):
    def test_text_card(self):
        e = S.narration_entry("text", {"heading": "Mi a sebesség?", "body": "Az út és az idő hányadosa", "key_term": "sebesség"})
        self.assertEqual(e["title"], "Mi a sebesség?")
        self.assertEqual(e["text"], "Mi a sebesség?\n\nAz út és az idő hányadosa.\n\nKulcsfogalom: sebesség.")
        self.assertEqual(len(e["hash"]), 40)

    def test_story_skips_mood(self):
        e = S.narration_entry("story", {"heading": "H", "body": "B.", "mood": "feszült"})
        self.assertNotIn("feszült", e["text"])

    def test_visual_reads_description_and_timeline_but_not_caption(self):
        e = S.narration_entry("visual", {"heading": "Az első világháború", "description": "Idővonal.",
                                         "caption": "Forrás: Wikipedia",
                                         "timeline": [{"when": "1914. június 28.", "what": "Merénylet Szarajevóban"}]})
        self.assertIn("1914. június 28.: Merénylet Szarajevóban.", e["text"])
        self.assertNotIn("Forrás", e["text"])

    def test_world_card_has_year_first_and_link(self):
        e = S.narration_entry("world", {"year": "1914", "heading": "A háború kitör", "body": "Európa lángol.", "link_hu": "Magyar katonák is harcoltak."})
        self.assertTrue(e["text"].startswith("1914: A háború kitör."))
        self.assertTrue(e["text"].endswith("Nekünk azért fontos: Magyar katonák is harcoltak."))

    def test_world_card_without_year_or_link(self):
        e = S.narration_entry("world", {"heading": "Cím", "body": "Szöveg."})
        self.assertEqual(e["text"], "Cím.\n\nSzöveg.")

    def test_experiment_card(self):
        e = S.narration_entry("experiment", {"heading": "Galilei", "discovery": "Ejtési kísérlet", "sketch": "ábra",
                                             "today": "Autók", "try_basic": "Ejts le két labdát", "try_advanced": "Mérd az időt"})
        self.assertIn("Felfedezés: Ejtési kísérlet.", e["text"])
        self.assertIn("Próbáld ki, haladó változat: Mérd az időt.", e["text"])
        self.assertNotIn("ábra", e["text"])

    def test_deep_card_reads_question_and_answer(self):
        e = S.narration_entry("deep", {"heading": "H", "body": "B", "did_you_know": "D", "think": "T?", "think_answer": "Igen"})
        self.assertIn("Tudtad: D.", e["text"])
        self.assertIn("Gondolkodj: T?", e["text"])
        self.assertTrue(e["text"].endswith("A válasz: Igen."))

    def test_quiz_reads_options_with_letters_and_never_the_answer(self):
        e = S.narration_entry("quiz", {"question": "Mikor volt a mohácsi csata?", "options": ["A) 1526", "B) 1456", "C) 1848", "D) 1914"],
                                       "correct": "A", "explanation": "1526. augusztus 29."})
        self.assertEqual(e["text"], "Mikor volt a mohácsi csata?\n\nA: 1526. B: 1456. C: 1848. D: 1914.")
        self.assertNotIn("augusztus", e["text"])
        self.assertEqual(e["title"], "Mikor volt a mohácsi csata?")

    def test_empty_or_unknown_cards_give_none(self):
        self.assertIsNone(S.narration_entry("text", {}))
        self.assertIsNone(S.narration_entry("text", {"heading": "", "body": "  "}))
        self.assertIsNone(S.narration_entry("text", "nem kártya"))
        self.assertIsNone(S.narration_entry("sketchbook", {"heading": "x"}))

    def test_hash_depends_only_on_the_spoken_text(self):
        a = S.narration_entry("text", {"heading": "H", "body": "B", "image": {"src": "x"}})
        b = S.narration_entry("text", {"heading": "H", "body": "B"})
        c = S.narration_entry("text", {"heading": "H", "body": "B2"})
        self.assertEqual(a["hash"], b["hash"])
        self.assertNotEqual(a["hash"], c["hash"])

    def test_blocks_are_index_aligned(self):
        out = S.narration_for_blocks({"text": [{"heading": "H", "body": "B"}, {}, {"heading": "K", "body": "L"}],
                                      "bogus": [{"heading": "x"}]})
        self.assertEqual(list(out), ["text"])
        self.assertEqual([e is None for e in out["text"]], [False, True, False])

    def test_audio_modes_exclude_quiz(self):
        self.assertNotIn("quiz", S.AUDIO_MODES)
        self.assertIn("quiz", S.SPEECH_MODES)


if __name__ == "__main__":
    unittest.main()
