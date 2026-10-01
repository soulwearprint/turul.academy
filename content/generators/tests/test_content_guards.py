import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import content_guards as G


class Articles(unittest.TestCase):
    def fix(self, s):
        return G.fix_articles(s)[0]

    def test_a_before_vowel_word(self):
        self.assertEqual(self.fix("a új kor és a alma"), "az új kor és az alma")

    def test_numerals(self):
        self.assertEqual(self.fix("A 1930-as évek, a 1970-es, a 5 fő, az 80 ember, az 18. század, a 1. helyen"),
                         "Az 1930-as évek, az 1970-es, az 5 fő, a 80 ember, a 18. század, az 1. helyen")
        self.assertEqual(self.fix("a 2008-ban, az 2008-ban"), "a 2008-ban, a 2008-ban")
        self.assertEqual(self.fix("a 50 fő, a 500 fő, az 5000 fő, a 2000 fő, a 1000 fő"),
                         "az 50 fő, az 500 fő, az 5000 fő, a 2000 fő, az 1000 fő")

    def test_roman(self):
        self.assertEqual(self.fix("a I. világháború, az II. világháború, a V. Károly, az X. század"),
                         "az I. világháború, a II. világháború, az V. Károly, a X. század")

    def test_az_pronoun_left_alone(self):
        self.assertEqual(self.fix("Az nem igaz, az pedig kevés"), "Az nem igaz, az pedig kevés")

    def test_acronyms_flagged_not_changed(self):
        out, flagged = G.fix_articles("a MDF és a NATO, az MSZP")
        self.assertEqual(out, "a MDF és a NATO, az MSZP")
        self.assertEqual(len(flagged), 1)                    # „a MDF” → check az

    def test_variable_a_and(self):
        self.assertEqual(self.fix("az a és b pont"), "az a és b pont")

    def test_already_correct(self):
        s = "Az ország a világ egyik legkisebbike, az első évben a tizedik helyen."
        self.assertEqual(self.fix(s), s)


class Text(unittest.TestCase):
    def test_duplicate_parenthesis(self):
        self.assertEqual(G.collapse_duplicate_parentheses("a hanghullám (hanghullám) terjed"), "a hanghullám terjed")
        self.assertEqual(G.collapse_duplicate_parentheses("az erő (force) mértéke"), "az erő (force) mértéke")

    def test_english_gloss(self):
        self.assertEqual(G.english_gloss("a sebesség (speed of light) nagy"), ["(speed of light)"])
        self.assertEqual(G.english_gloss("Mohács (1526)"), [])

    def test_dedupe(self):
        cards = [{"heading": "Miniszterelnökök", "body": "Antall József 1990 és 1993 között irányította az országot, Horn Gyula követte."},
                 {"heading": "Kormányfők", "body": "Gyorsulás és sebesség fogalma a fizikában kerül elő."},
                 {"heading": "Miniszterelnökök", "body": "Antall József 1990 és 1993 között irányította az országot, Horn Gyula követte őt."}]
        kept, dropped = G.dedupe_cards(cards)
        self.assertEqual(dropped, [2])
        self.assertEqual(len(kept), 2)


def card(q, opts, key, exp="magyarázat"):
    return {"type": "quiz", "question_type": "multiple_choice", "question": q,
            "options": [f"{'ABCD'[i]}) {o}" for i, o in enumerate(opts)], "correct": key, "explanation": exp}


class Quiz(unittest.TestCase):
    def test_shuffle_moves_key_with_answer(self):
        for i in range(30):
            c = card(f"Kérdés {i}?", ["Helyes válasz", "Rossz egy", "Rossz kettő", "Rossz három"], "A")
            s = G.shuffle_quiz_card(c)
            body = s["options"]["ABCD".index(s["correct"])]
            self.assertTrue(body.endswith("Helyes válasz"), (c, s))
            self.assertEqual(sorted(o[:2] for o in s["options"]), ["A)", "B)", "C)", "D)"])

    def test_shuffle_is_deterministic_and_spreads_keys(self):
        keys = []
        for i in range(60):
            c = card(f"Kérdés {i}?", ["X", "Y", "Z", "W"], "A")
            self.assertEqual(G.shuffle_quiz_card(c), G.shuffle_quiz_card(c))
            keys.append(G.shuffle_quiz_card(c)["correct"])
        self.assertEqual(set(keys), set("ABCD"))
        self.assertLess(keys.count("A"), 30)

    def test_positional_option_stays_last(self):
        c = card("Q?", ["Egy", "Kettő", "Három", "Egyik sem"], "D")
        s = G.shuffle_quiz_card(c)
        self.assertTrue(s["options"][3].endswith("Egyik sem"))
        self.assertEqual(s["correct"], "D")

    def test_true_false_untouched(self):
        c = card("Igaz?", ["Igaz", "Hamis", "Igaz", "Hamis"], "A")
        self.assertEqual(G.shuffle_quiz_card(c), c)

    def test_explanation_letter_refs_remapped(self):
        c = card("Q?", ["Jó", "Rossz1", "Rossz2", "Rossz3"], "A", "A) a helyes, a B válasz téves.")
        s = G.shuffle_quiz_card(c)
        self.assertIn(f"{s['correct']}) a helyes", s["explanation"])

    def test_problems(self):
        self.assertIn("duplicate options", G.quiz_problems(card("Q?", ["a", "a", "b", "c"], "A")))
        self.assertTrue(any("not A–D" in p for p in G.quiz_problems(card("Q?", ["a", "b", "c", "d"], "E"))))
        self.assertTrue(any("explanation matches option" in p for p in G.quiz_problems(
            card("Q?", ["tej", "kenyér szeletelve", "víz", "olaj"], "A", "A kenyér szeletelve tartható, szeletelve kenyér"))))
        self.assertEqual(G.quiz_problems(card("Q?", ["a", "b", "c", "d"], "B", "ok")), [])

    def test_unshuffled_distribution(self):
        cards = [card(f"Q{i}?", ["a", "b", "c", "d"], "A") for i in range(5)]
        self.assertIn("5/5", G.key_distribution_problem(cards))
        self.assertIsNone(G.key_distribution_problem([card("Q?", list("abcd"), k) for k in "ABCDA"]))


class Postprocess(unittest.TestCase):
    def test_quiz_block(self):
        obj = {"title": "t", "cards": [card(f"Q{i}?", ["j", "r1", "r2", "r3"], "A") for i in range(8)]}
        out, notes = G.postprocess("quiz", obj)
        self.assertEqual(len(out["cards"]), 8)
        self.assertIsNone(G.key_distribution_problem(out["cards"]))

    def test_text_block_cleans(self):
        obj = {"title": "t", "cards": [{"type": "text", "heading": "H", "body": "A 1930-as évek a hanghullám (hanghullám) kora.", "key_term": "k"}]}
        out, _ = G.postprocess("text", obj)
        self.assertEqual(out["cards"][0]["body"], "Az 1930-as évek a hanghullám kora.")

    def test_bare_card_and_list(self):
        c = {"type": "world", "year": "", "heading": "h", "body": "a új kor", "link_hu": ""}
        out, _ = G.postprocess("world", c)
        self.assertEqual(out["body"], "az új kor")
        out, _ = G.postprocess("world", [c])
        self.assertEqual(out[0]["body"], "az új kor")


if __name__ == "__main__":
    unittest.main()


class Safety(unittest.TestCase):
    def test_unsafe(self):
        c = {"type": "experiment", "try_basic": "Tedd az üvegpalackot a fagyasztóba, hogy megfagyjon a víz.", "try_advanced": ""}
        self.assertTrue(G.unsafe_experiment(c))
        self.assertTrue(any("unsafe" in p for p in G.card_problems("experiment", c)))
        ok = {"type": "experiment", "try_basic": "Mérd meg, hogy a golyó milyen gyorsan gurul le a lejtőn.", "try_advanced": ""}
        self.assertEqual(G.unsafe_experiment(ok), [])
