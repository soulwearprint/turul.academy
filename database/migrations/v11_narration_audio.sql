-- v11_narration_audio — pre-generated audio for „Felolvasás” (read aloud / audiobook mode).
--
-- A phone that locks its screen stops the browser's own voice (speechSynthesis), but keeps playing
-- an ordinary audio file. So the lesson text is turned into mp3 files once (content/generators/
-- generate_audio.py), stored in the public bucket `content-audio`, and played with <audio> +
-- the Media Session API (lock-screen controls).
--
-- Audio is content-addressed: `text_hash` = sha256 of the exact narrated text (backend/core/speech.py),
-- first 40 hex. A card that is edited gets a new hash, so it is never matched to stale audio — the app
-- falls back to the browser voice for it until the generator is run again — and identical text in two
-- lessons shares one file. Old files/rows are removed with `generate_audio.py prune`.
--
-- Backend/script-only table (same pattern as media_refs): RLS on, no client policies; the API reads it
-- with the service role and hands the Storage path to the app inside the lesson response. The bucket is
-- public-read (like content-media); only the service role can write to it — no storage.objects policies.

CREATE TABLE IF NOT EXISTS public.narration_audio (
  text_hash   text PRIMARY KEY CHECK (text_hash ~ '^[0-9a-f]{40}$'),
  path        text NOT NULL,                          -- inside the bucket, e.g. 'da/da4204….mp3'
  provider    text NOT NULL,                          -- 'azure' | 'openai'
  voice       text NOT NULL,                          -- e.g. 'hu-HU-NoemiNeural'
  chars       integer NOT NULL CHECK (chars > 0),     -- characters synthesised (what the provider bills)
  bytes       integer NOT NULL CHECK (bytes > 0),
  created_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.narration_audio ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.narration_audio FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.narration_audio TO service_role;

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('content-audio', 'content-audio', true, 10485760, ARRAY['audio/mpeg'])
ON CONFLICT (id) DO NOTHING;
