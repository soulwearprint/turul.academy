"""narration_for() with the database stubbed out: audio is matched by text hash, and a failing
lookup never breaks the lesson."""
import asyncio
import os
import sys
import unittest

os.environ.setdefault("SUPABASE_URL", "http://supabase.invalid")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import narration as N  # noqa: E402
from core import speech as S  # noqa: E402

CARD = {"heading": "Mi a sebesség?", "body": "Az út és az idő hányadosa."}
HASH = S.narration_entry("text", CARD)["hash"]


def run(coro):
    return asyncio.run(coro)


class NarrationForTests(unittest.TestCase):
    def setUp(self):
        self._orig = N.db_get
        self.calls = []

    def tearDown(self):
        N.db_get = self._orig

    def stub(self, rows=None, boom=False):
        async def fake(table, params, **kw):
            self.calls.append((table, params, kw))
            if boom:
                raise RuntimeError("relation \"narration_audio\" does not exist")
            return rows or []
        N.db_get = fake

    def test_audio_path_is_attached_when_the_text_hash_matches(self):
        self.stub(rows=[{"text_hash": HASH, "path": f"{HASH[:2]}/{HASH}.mp3"}])
        out = run(N.narration_for({"text": [CARD, {}]}))
        self.assertEqual(out["text"][0]["audio"], f"content-audio/{HASH[:2]}/{HASH}.mp3")
        self.assertEqual(out["text"][0]["title"], "Mi a sebesség?")
        self.assertIsNone(out["text"][1])
        self.assertEqual(self.calls[0][0], "narration_audio")
        self.assertTrue(self.calls[0][2]["service"])

    def test_edited_card_has_no_audio(self):
        self.stub(rows=[{"text_hash": "0" * 40, "path": "00/old.mp3"}])
        out = run(N.narration_for({"text": [CARD]}))
        self.assertIsNone(out["text"][0]["audio"])
        self.assertIn("Az út és az idő", out["text"][0]["text"])

    def test_database_failure_falls_back_to_text_only(self):
        self.stub(boom=True)
        out = run(N.narration_for({"text": [CARD]}))
        self.assertIsNone(out["text"][0]["audio"])

    def test_quiz_is_never_looked_up(self):
        self.stub(rows=[])
        out = run(N.narration_for({"quiz": [{"question": "Q?", "options": ["A) x", "B) y"]}]}))
        self.assertEqual(self.calls, [])
        self.assertIsNone(out["quiz"][0]["audio"])
        self.assertEqual(out["quiz"][0]["text"], "Q?\n\nA: x. B: y.")

    def test_no_audio_modes_means_no_query(self):
        self.stub()
        run(N.narration_for({}))
        self.assertEqual(self.calls, [])

    def test_quiz_narration_for_topic_quiz(self):
        out = N.quiz_narration([{"question": "Q1?", "options": ["A) x"]}, {"options": []}])
        self.assertEqual(out[0]["text"], "Q1?\n\nA: x.")
        self.assertIsNone(out[1])


if __name__ == "__main__":
    unittest.main()
