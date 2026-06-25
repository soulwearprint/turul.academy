-- v5_content_model_3tier — NAT re-foundation (vertical-slice schema, additive)
-- Adds the 3-tier model alongside the legacy `lessons` table (which the live app
-- still uses) so existing testing is undisturbed.
--   curriculum_topics (Témakör)  →  curriculum_lessons (Téma)  →  content_blocks
--   content_blocks dimensions: mode (text|story|visual|quiz|world),
--   level (alap|emelt), scope (lesson|topic). One flexible row model covers
--   the 4 modes + the "Világ ekkor" global layer + per-lesson & per-topic
--   quizzes + (reserved) emelt-szint depth.
-- See content/generators/generate_temakor.py for NAT-mandatory-driven generation.

CREATE TABLE IF NOT EXISTS public.curriculum_lessons (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id uuid NOT NULL REFERENCES public.curriculum_topics(id) ON DELETE CASCADE,
  nat_id text, title text NOT NULL, title_hu text NOT NULL,
  order_index int NOT NULL DEFAULT 0, is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.content_blocks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lesson_id uuid REFERENCES public.curriculum_lessons(id) ON DELETE CASCADE,
  topic_id uuid REFERENCES public.curriculum_topics(id) ON DELETE CASCADE,
  mode text NOT NULL, level text NOT NULL DEFAULT 'alap', scope text NOT NULL DEFAULT 'lesson',
  content jsonb NOT NULL DEFAULT '[]', generated_by text DEFAULT 'ai',
  review_status text DEFAULT 'pending', is_active boolean DEFAULT false,
  created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS content_blocks_lesson_uq ON public.content_blocks(lesson_id, mode, level) WHERE lesson_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS content_blocks_topic_uq  ON public.content_blocks(topic_id, mode, level)  WHERE lesson_id IS NULL;
CREATE POLICY curriculum_lessons_public_read ON public.curriculum_lessons FOR SELECT USING (true);
CREATE POLICY content_blocks_public_read ON public.content_blocks FOR SELECT USING (is_active = true);
