-- v6_nat_progress — progress + quiz results for the NAT 3-tier content model.
-- The legacy lesson_progress/quiz_results tables FK their lesson_id to the old
-- `lessons` table, so they can't reference curriculum_lessons. These NAT tables
-- reference curriculum_lessons/curriculum_topics. XP + streaks stay unified in
-- the shared user_xp + daily_activity tables. RLS: user-owned (*_own).

CREATE TABLE IF NOT EXISTS public.nat_lesson_progress (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  lesson_id uuid NOT NULL REFERENCES public.curriculum_lessons(id) ON DELETE CASCADE,
  topic_id uuid NOT NULL REFERENCES public.curriculum_topics(id) ON DELETE CASCADE,
  status text DEFAULT 'in_progress',
  mode_used text,
  started_at timestamptz DEFAULT now(),
  completed_at timestamptz,
  time_spent_seconds int,
  UNIQUE (user_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS public.nat_quiz_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  topic_id uuid NOT NULL REFERENCES public.curriculum_topics(id) ON DELETE CASCADE,
  lesson_id uuid REFERENCES public.curriculum_lessons(id) ON DELETE CASCADE,  -- NULL = topic-scope quiz
  scope text NOT NULL DEFAULT 'lesson',
  score int, correct int, total int,
  answers jsonb NOT NULL DEFAULT '[]',
  xp_earned int DEFAULT 0,
  completed_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS nat_lesson_progress_user ON public.nat_lesson_progress(user_id);
CREATE INDEX IF NOT EXISTS nat_quiz_results_user ON public.nat_quiz_results(user_id);

ALTER TABLE public.nat_lesson_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nat_quiz_results   ENABLE ROW LEVEL SECURITY;

-- user-owned: a user may only see/modify their own rows (defense-in-depth; the
-- backend uses the service role and scopes by user.id in code).
CREATE POLICY nat_lesson_progress_own ON public.nat_lesson_progress
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY nat_quiz_results_own ON public.nat_quiz_results
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
