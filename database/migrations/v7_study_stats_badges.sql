-- v7_study_stats_badges — time tracking, quiz-attempt history, badges, study heatmap.
--
-- 1. nat_lesson_progress.time_spent_seconds becomes an ACCUMULATED total across visits
--    (was a single overwrite nobody sent), plus a per-mode breakdown so the stats page
--    can derive "seconds per card" from each tab's card count.
-- 2. daily_activity.seconds_spent — study time per (Budapest-local) day, for the heatmap.
-- 3. nat_quiz_attempts — append-only log of every NAT quiz submission. nat_quiz_results
--    keeps only the latest attempt (XP reset semantics), so without this there is no
--    first-try vs latest comparison and no "questions you keep missing".
-- 4. user_badges unique per (user, badge_type) so awarding is idempotent.
-- 5. Atomic increment helpers (called by the backend with the service role) so two
--    overlapping time flushes from one lesson visit can't lose each other's seconds.

-- ── 1. Per-lesson time ───────────────────────────────────────────
ALTER TABLE public.nat_lesson_progress
  ADD COLUMN IF NOT EXISTS mode_seconds jsonb NOT NULL DEFAULT '{}';
UPDATE public.nat_lesson_progress SET time_spent_seconds = 0 WHERE time_spent_seconds IS NULL;
ALTER TABLE public.nat_lesson_progress ALTER COLUMN time_spent_seconds SET DEFAULT 0;

-- ── 2. Study seconds per day ─────────────────────────────────────
ALTER TABLE public.daily_activity
  ADD COLUMN IF NOT EXISTS seconds_spent int NOT NULL DEFAULT 0;

-- ── 3. Quiz attempt log ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.nat_quiz_attempts (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  topic_id   uuid NOT NULL REFERENCES public.curriculum_topics(id) ON DELETE CASCADE,
  lesson_id  uuid REFERENCES public.curriculum_lessons(id) ON DELETE CASCADE,  -- NULL = topic-scope quiz
  scope      text NOT NULL DEFAULT 'lesson',
  score      int, correct int, total int,
  answers    jsonb NOT NULL DEFAULT '[]',   -- picked letters, card order
  results    jsonb NOT NULL DEFAULT '[]',   -- true/false per question, card order
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS nat_quiz_attempts_user ON public.nat_quiz_attempts(user_id, created_at);

ALTER TABLE public.nat_quiz_attempts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS nat_quiz_attempts_own ON public.nat_quiz_attempts;
CREATE POLICY nat_quiz_attempts_own ON public.nat_quiz_attempts
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.nat_quiz_attempts TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.nat_quiz_attempts TO service_role;

-- Backfill: every existing latest-attempt row becomes that quiz's first logged attempt,
-- re-graded per question against the current quiz content.
INSERT INTO public.nat_quiz_attempts
  (user_id, topic_id, lesson_id, scope, score, correct, total, answers, results, created_at)
SELECT r.user_id, r.topic_id, r.lesson_id, r.scope, r.score, r.correct, r.total, r.answers,
       COALESCE((
         SELECT jsonb_agg(
                  upper(left(btrim(COALESCE(c.card->>'correct', '')), 1)) <> ''
                  AND upper(left(btrim(COALESCE(c.card->>'correct', '')), 1))
                    = upper(left(btrim(COALESCE(r.answers->>(c.ord - 1)::int, '')), 1))
                  ORDER BY c.ord)
         FROM jsonb_array_elements(cb.content) WITH ORDINALITY AS c(card, ord)
       ), '[]'::jsonb),
       COALESCE(r.completed_at, now())
FROM public.nat_quiz_results r
JOIN LATERAL (
  SELECT b.content FROM public.content_blocks b
  WHERE b.is_active
    AND ((r.scope = 'lesson' AND b.scope = 'lesson' AND b.mode = 'quiz' AND b.lesson_id = r.lesson_id)
      OR (r.scope = 'topic'  AND b.scope = 'topic'  AND b.topic_id = r.topic_id))
  LIMIT 1
) cb ON true
WHERE NOT EXISTS (SELECT 1 FROM public.nat_quiz_attempts a WHERE a.user_id = r.user_id);

-- ── 4. Idempotent badges ─────────────────────────────────────────
DELETE FROM public.user_badges a
USING public.user_badges b
WHERE a.user_id = b.user_id AND a.badge_type = b.badge_type AND a.earned_at > b.earned_at;
CREATE UNIQUE INDEX IF NOT EXISTS user_badges_user_type ON public.user_badges(user_id, badge_type);

-- ── Card counts per block (stats: seconds per card without shipping content) ──
CREATE OR REPLACE VIEW public.content_block_card_counts
WITH (security_invoker = true) AS
SELECT lesson_id, topic_id, scope, mode, jsonb_array_length(content) AS card_count
FROM public.content_blocks
WHERE is_active AND jsonb_typeof(content) = 'array';
GRANT SELECT ON public.content_block_card_counts TO service_role;

-- ── 5. Atomic increments (service role only) ─────────────────────
CREATE OR REPLACE FUNCTION public.nat_track_time(
  p_user uuid, p_lesson uuid, p_topic uuid, p_seconds int, p_modes jsonb)
RETURNS void LANGUAGE sql SECURITY INVOKER SET search_path = public AS $$
  INSERT INTO nat_lesson_progress (user_id, lesson_id, topic_id, status, time_spent_seconds, mode_seconds)
  VALUES (p_user, p_lesson, p_topic, 'in_progress', p_seconds, COALESCE(p_modes, '{}'))
  ON CONFLICT (user_id, lesson_id) DO UPDATE SET
    time_spent_seconds = COALESCE(nat_lesson_progress.time_spent_seconds, 0) + EXCLUDED.time_spent_seconds,
    mode_seconds = (
      SELECT COALESCE(jsonb_object_agg(k,
               COALESCE((nat_lesson_progress.mode_seconds->>k)::int, 0)
             + COALESCE((EXCLUDED.mode_seconds->>k)::int, 0)), '{}'::jsonb)
      FROM jsonb_object_keys(nat_lesson_progress.mode_seconds || EXCLUDED.mode_seconds) AS k
    );
$$;

CREATE OR REPLACE FUNCTION public.track_study_seconds(p_user uuid, p_date date, p_seconds int)
RETURNS void LANGUAGE sql SECURITY INVOKER SET search_path = public AS $$
  INSERT INTO daily_activity (user_id, date, seconds_spent)
  VALUES (p_user, p_date, p_seconds)
  ON CONFLICT (user_id, date) DO UPDATE SET
    seconds_spent = daily_activity.seconds_spent + EXCLUDED.seconds_spent;
$$;

REVOKE EXECUTE ON FUNCTION public.nat_track_time(uuid, uuid, uuid, int, jsonb) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.track_study_seconds(uuid, date, int) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.nat_track_time(uuid, uuid, uuid, int, jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.track_study_seconds(uuid, date, int) TO service_role;
