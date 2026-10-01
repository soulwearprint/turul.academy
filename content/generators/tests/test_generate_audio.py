"""python3 -m unittest discover -s content/generators/tests   — no network: Supabase and the TTS provider are httpx.MockTransport fakes."""
import json
import os
import sys
import unittest

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import generate_audio as G  # noqa: E402
from core import speech as S  # noqa: E402

CARD1 = {"heading": "Mi a sebesség?", "body": "Az út és az idő hányadosa."}
CARD2 = {"heading": "Gyorsulás", "body": "A sebesség változása."}
H1 = S.narration_entry("text", CARD1)["hash"]
H2 = S.narration_entry("text", CARD2)["hash"]


class ChunkTests(unittest.TestCase):
    def test_short_text_is_one_chunk(self):
        self.assertEqual(G.split_chunks("Cím.\n\nSzöveg."), ["Cím.\n\nSzöveg."])

    def test_long_text_splits_at_sentences_and_keeps_every_word(self):
        text = " ".join(f"Ez a(z) {i}. mondat." for i in range(400))
        chunks = G.split_chunks(text, limit=500)
        self.assertGreater(len(chunks), 3)
        self.assertTrue(all(len(c) <= 500 for c in chunks))
        self.assertEqual(" ".join(" ".join(chunks).split()), " ".join(text.split()))

    def test_monster_sentence_without_punctuation_is_still_cut(self):
        chunks = G.split_chunks("szó " * 600, limit=300)
        self.assertTrue(all(len(c) <= 300 for c in chunks))
        self.assertEqual(sum(c.count("szó") for c in chunks), 600)

    def test_word_longer_than_the_limit_does_not_loop_forever(self):
        chunks = G.split_chunks("x" * 1000, limit=300)
        self.assertEqual("".join(chunks), "x" * 1000)


class ProviderTests(unittest.TestCase):
    def test_azure_request_is_ssml_with_pauses_and_escaping(self):
        req = G.Azure("KEY", "westeurope").request("Cím & társa.\n\nA < B.\n1914: háború.")
        self.assertEqual(req["url"], "https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1")
        self.assertEqual(req["headers"]["Ocp-Apim-Subscription-Key"], "KEY")
        self.assertEqual(req["headers"]["X-Microsoft-OutputFormat"], G.AZURE_FORMAT)
        ssml = req["content"].decode()
        self.assertIn("<voice name='hu-HU-NoemiNeural'>", ssml)
        self.assertIn("Cím &amp; társa.<break time=\"450ms\"/>A &lt; B.<break time=\"450ms\"/>1914: háború.", ssml)

    def test_openai_request(self):
        req = G.OpenAI("sk-x", model="tts-1").request("Szia.")
        self.assertEqual(req["json"], {"model": "tts-1", "voice": "alloy", "input": "Szia.", "response_format": "mp3"})
        self.assertEqual(req["headers"]["Authorization"], "Bearer sk-x")
        self.assertIn("instructions", G.OpenAI("sk-x").request("Szia.")["json"])

    def test_provider_choice_prefers_azure_and_needs_a_key(self):
        self.assertEqual(G.pick_provider(env={"AZURE_SPEECH_KEY": "k", "AZURE_SPEECH_REGION": "r", "OPENAI_API_KEY": "o"}).name, "azure")
        self.assertEqual(G.pick_provider(env={"OPENAI_API_KEY": "o"}).name, "openai")
        with self.assertRaises(SystemExit):
            G.pick_provider(env={})
        with self.assertRaises(SystemExit):
            G.pick_provider("azure", env={"AZURE_SPEECH_KEY": "k"})     # region missing

    def test_synth_retries_429_then_succeeds_and_joins_chunks(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(429, headers={"Retry-After": "1"}) if len(calls) == 1 else httpx.Response(200, content=b"MP3")
        sleeps = []
        with httpx.Client(transport=httpx.MockTransport(handler)) as c:
            self.assertEqual(G.synth(c, G.OpenAI("k"), "Szia.", sleep=sleeps.append), b"MP3")
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [1.0])

    def test_synth_gives_up_on_a_hard_error(self):
        with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401))) as c:
            with self.assertRaises(httpx.HTTPStatusError):
                G.synth(c, G.OpenAI("bad"), "Szia.")


class FakeSupabase:
    """Just enough of PostgREST + Storage for collect/run/prune."""

    def __init__(self, audio_rows=()):
        self.audio = {r["text_hash"]: dict(r) for r in audio_rows}
        self.uploads, self.deleted_files, self.tts_calls = {}, [], 0

    def handler(self, request: httpx.Request):
        path, q = request.url.path, dict(request.url.params)
        if path == "/rest/v1/curriculum_topics":
            return httpx.Response(200, json=[{"id": "T1", "nat_id": "PHYS-1"}])
        if path == "/rest/v1/curriculum_lessons":
            return httpx.Response(200, json=[{"id": "L1"}])
        if path == "/rest/v1/content_blocks":
            return httpx.Response(200, json=[{"lesson_id": "L1", "mode": "text", "content": [CARD1, {}, CARD2]},
                                             {"lesson_id": "L1", "mode": "quiz", "content": [{"question": "Q?", "options": ["A) x"]}]}])
        if path == "/rest/v1/narration_audio" and request.method == "GET":
            wanted = q.get("text_hash")
            rows = list(self.audio.values())
            if wanted:
                ids = wanted[4:-1].split(",")
                rows = [r for r in rows if r["text_hash"] in ids]
            return httpx.Response(200, json=rows)
        if path == "/rest/v1/narration_audio" and request.method == "POST":
            row = json.loads(request.content)
            self.audio[row["text_hash"]] = row
            return httpx.Response(201)
        if path == "/rest/v1/narration_audio" and request.method == "DELETE":
            self.audio.pop(q["text_hash"][3:], None)
            return httpx.Response(204)
        if path.startswith("/storage/v1/object/content-audio/") and request.method == "POST":
            self.uploads[path.rsplit("/content-audio/", 1)[1]] = request.content
            assert request.headers["x-upsert"] == "true"
            assert request.headers["cache-control"] == "max-age=31536000"
            return httpx.Response(200)
        if path == "/storage/v1/object/content-audio" and request.method == "DELETE":
            self.deleted_files += json.loads(request.content)["prefixes"]
            return httpx.Response(200)
        if "tts.speech" in str(request.url) or "audio/speech" in str(request.url):
            self.tts_calls += 1
            return httpx.Response(200, content=b"ID3-fake-mp3")
        return httpx.Response(404, json={"message": f"unhandled {request.method} {request.url}"})


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSupabase()
        self.client = httpx.Client(transport=httpx.MockTransport(self.fake.handler))
        self.db = G.Supa(self.client, "http://sb.test", "svc")
        os.environ["OPENAI_API_KEY"] = "sk-test"
        os.environ.pop("AZURE_SPEECH_KEY", None)

    def tearDown(self):
        self.client.close()

    def args(self, *extra):
        return ["run", "--nat-id", "PHYS-1", *extra]

    def test_collect_follows_reading_order_skips_empty_cards_and_quiz(self):
        found = G.collect(self.db, ["PHYS-1"])
        self.assertEqual(list(found), [H1, H2])
        self.assertEqual(found[H1]["nat_id"], "PHYS-1")

    def test_dry_run_spends_nothing(self):
        a = G.argparse.Namespace(nat_id="PHYS-1", all=False, modes=list(S.AUDIO_MODES), provider=None, n=3,
                                 max_chars=10_000, apply=False)
        G.cmd_run(self.db, self.client, a)
        self.assertEqual((self.fake.tts_calls, self.fake.uploads, self.fake.audio), (0, {}, {}))

    def test_apply_synthesises_uploads_and_records_each_missing_text(self):
        a = G.argparse.Namespace(nat_id="PHYS-1", all=False, modes=list(S.AUDIO_MODES), provider="openai", n=3,
                                 max_chars=10_000, apply=True)
        G.cmd_run(self.db, self.client, a)
        self.assertEqual(self.fake.tts_calls, 2)
        self.assertEqual(set(self.fake.uploads), {G.audio_path(H1), G.audio_path(H2)})
        row = self.fake.audio[H1]
        self.assertEqual((row["path"], row["provider"], row["voice"], row["bytes"]), (G.audio_path(H1), "openai", "alloy", len(b"ID3-fake-mp3")))
        self.assertEqual(row["chars"], len(S.narration_entry("text", CARD1)["text"]))

    def test_second_run_only_does_what_is_missing(self):
        self.fake.audio[H1] = {"text_hash": H1, "path": G.audio_path(H1)}
        a = G.argparse.Namespace(nat_id="PHYS-1", all=False, modes=list(S.AUDIO_MODES), provider="openai", n=3,
                                 max_chars=10_000, apply=True)
        G.cmd_run(self.db, self.client, a)
        self.assertEqual(self.fake.tts_calls, 1)
        self.assertEqual(list(self.fake.uploads), [G.audio_path(H2)])

    def test_char_budget_stops_the_run(self):
        a = G.argparse.Namespace(nat_id="PHYS-1", all=False, modes=list(S.AUDIO_MODES), provider="openai", n=3,
                                 max_chars=len(S.narration_entry("text", CARD1)["text"]) + 1, apply=True)
        G.cmd_run(self.db, self.client, a)
        self.assertEqual(self.fake.tts_calls, 1)

    def test_prune_removes_only_unreferenced_audio(self):
        self.fake.audio[H1] = {"text_hash": H1, "path": G.audio_path(H1)}
        old = "0" * 40
        self.fake.audio[old] = {"text_hash": old, "path": G.audio_path(old)}
        a = G.argparse.Namespace(apply=True)
        G.cmd_prune(self.db, a)
        self.assertEqual(self.fake.deleted_files, [G.audio_path(old)])
        self.assertEqual(set(self.fake.audio), {H1})

    def test_prune_dry_run_deletes_nothing(self):
        old = "0" * 40
        self.fake.audio[old] = {"text_hash": old, "path": G.audio_path(old)}
        G.cmd_prune(self.db, G.argparse.Namespace(apply=False))
        self.assertEqual((self.fake.deleted_files, set(self.fake.audio)), ([], {old}))

    def test_five_failures_in_a_row_stop_the_run(self):
        calls = []

        def handler(request):
            if "audio/speech" in str(request.url):
                calls.append(1)
                return httpx.Response(401)
            return self.fake.handler(request)
        # one more distinct card, so there is something left to stop before
        cards = [{"heading": f"H{i}", "body": f"B{i}"} for i in range(8)]
        orig = self.fake.handler

        def multi(request):
            if request.url.path == "/rest/v1/content_blocks":
                return httpx.Response(200, json=[{"lesson_id": "L1", "mode": "text", "content": cards}])
            return handler(request) if "audio/speech" in str(request.url) else orig(request)
        client = httpx.Client(transport=httpx.MockTransport(multi))
        a = G.argparse.Namespace(nat_id="PHYS-1", all=False, modes=list(S.AUDIO_MODES), provider="openai", n=3,
                                 max_chars=10_000, apply=True)
        G.cmd_run(G.Supa(client, "http://sb.test", "svc"), client, a)
        self.assertEqual(len(calls), 5)


if __name__ == "__main__":
    unittest.main()
