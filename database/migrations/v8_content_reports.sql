-- v8_content_reports — „Hibát találtál?” student reports + a reviewer queue, and role hardening.

-- ── 1. Role hardening ────────────────────────────────────────────
-- user_profiles_own (FOR ALL USING auth.uid() = id) plus the table-wide grants let a signed-in
-- user INSERT/UPDATE their own profile row — every column, `role` included. With the public
-- anon key from the frontend bundle, anyone could make themselves 'reviewer'/'admin', which
-- already unlocks lessons_reviewer_update (editing legacy lesson content) and would unlock the
-- report queue below. From now on only the service role (trusted backend) or direct SQL may
-- set a role; end-user requests are pinned to their current role / 'student'.
CREATE OR REPLACE FUNCTION public.protect_user_role() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
  IF coalesce(auth.role(), '') IN ('authenticated', 'anon') THEN
    IF TG_OP = 'INSERT' THEN
      NEW.role := 'student';
    ELSIF NEW.role IS DISTINCT FROM OLD.role THEN
      RAISE EXCEPTION 'role can only be changed by an administrator' USING ERRCODE = '42501';
    END IF;
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS user_profiles_protect_role ON public.user_profiles;
CREATE TRIGGER user_profiles_protect_role
  BEFORE INSERT OR UPDATE ON public.user_profiles
  FOR EACH ROW EXECUTE FUNCTION public.protect_user_role();

-- ── 2. Content reports ───────────────────────────────────────────
-- One row per student report on one card. `card_snapshot` keeps the card as the student saw it:
-- the generators delete + re-insert blocks on regeneration (block_id then goes NULL), and the
-- reviewer still needs to see what was reported.
CREATE TABLE IF NOT EXISTS public.content_reports (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid REFERENCES auth.users(id) ON DELETE SET NULL,   -- reports outlive accounts
  topic_id      uuid NOT NULL REFERENCES public.curriculum_topics(id) ON DELETE CASCADE,
  lesson_id     uuid REFERENCES public.curriculum_lessons(id) ON DELETE CASCADE,  -- NULL = topic quiz
  block_id      uuid REFERENCES public.content_blocks(id) ON DELETE SET NULL,
  scope         text NOT NULL DEFAULT 'lesson',
  mode          text NOT NULL,
  card_index    int  NOT NULL CHECK (card_index >= 0),
  card_snapshot jsonb NOT NULL,
  reason        text NOT NULL CHECK (reason IN ('teny', 'kviz', 'nyelv', 'erthetetlen', 'egyeb')),
  comment       text CHECK (char_length(comment) <= 500),
  status        text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'dismissed')),
  reviewer_note text,
  resolved_by   uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  resolved_at   timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS content_reports_status ON public.content_reports(status, created_at DESC);
CREATE INDEX IF NOT EXISTS content_reports_user ON public.content_reports(user_id, created_at DESC);
-- One open report per student per card (a second tap updates it instead of piling up).
CREATE UNIQUE INDEX IF NOT EXISTS content_reports_one_open
  ON public.content_reports(user_id, block_id, card_index) WHERE status = 'open';

ALTER TABLE public.content_reports ENABLE ROW LEVEL SECURITY;
-- Students may see/file only their own reports (defense-in-depth; the backend uses the service
-- role). Reviewing goes through the backend, which checks the reviewer role.
DROP POLICY IF EXISTS content_reports_own_select ON public.content_reports;
CREATE POLICY content_reports_own_select ON public.content_reports
  FOR SELECT USING (auth.uid() = user_id);
DROP POLICY IF EXISTS content_reports_own_insert ON public.content_reports;
CREATE POLICY content_reports_own_insert ON public.content_reports
  FOR INSERT WITH CHECK (auth.uid() = user_id AND status = 'open');
GRANT SELECT, INSERT ON public.content_reports TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.content_reports TO service_role;
