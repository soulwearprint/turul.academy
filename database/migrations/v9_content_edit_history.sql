-- v9_content_edit_history — every reviewer card edit is logged (before / after / who / when)
-- and can be undone.
--
-- Until now PUT /api/reports/card overwrote content_blocks.content in place; the only other
-- copy of the old wording was the report's card_snapshot, which is gone once the report is
-- deleted (found 2026-09-29 while clearing QA reports).

-- ── 1. The log ───────────────────────────────────────────────────
-- Location columns (topic/lesson/mode/scope/card_index) are copied in, not only block_id: the
-- generators delete + re-insert blocks on regeneration, which NULLs block_id, and the history
-- should still say which card it was.
CREATE TABLE IF NOT EXISTS public.content_edits (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  block_id    uuid REFERENCES public.content_blocks(id) ON DELETE SET NULL,
  topic_id    uuid REFERENCES public.curriculum_topics(id) ON DELETE CASCADE,
  lesson_id   uuid REFERENCES public.curriculum_lessons(id) ON DELETE CASCADE,  -- NULL = topic-scope block
  mode        text NOT NULL,
  scope       text NOT NULL,
  card_index  int  NOT NULL CHECK (card_index >= 0),
  before      jsonb NOT NULL,
  after       jsonb NOT NULL,
  -- user_profiles (not auth.users) so PostgREST can embed the editor's display name.
  edited_by   uuid REFERENCES public.user_profiles(id) ON DELETE SET NULL,
  report_ids  uuid[] NOT NULL DEFAULT '{}',   -- reports that prompted it (no FK: history outlives reports)
  reverts     uuid REFERENCES public.content_edits(id) ON DELETE SET NULL,  -- set on an undo
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS content_edits_recent ON public.content_edits(created_at DESC);
CREATE INDEX IF NOT EXISTS content_edits_card ON public.content_edits(block_id, card_index, created_at DESC);
CREATE INDEX IF NOT EXISTS content_edits_reverts ON public.content_edits(reverts) WHERE reverts IS NOT NULL;

-- Backend-only table: RLS on with no client policies = deny for anon/authenticated. The
-- backend reads/writes it with the service role after checking the reviewer role.
ALTER TABLE public.content_edits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.content_edits FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.content_edits TO service_role;

-- ── 2. Edit = compare-and-set + log, in one transaction ──────────
-- p_before is the card as the reviewer loaded it. If someone else changed it meanwhile the
-- edit is refused (HTTP 409 via PostgREST's PTxxx codes) instead of silently overwriting.
CREATE OR REPLACE FUNCTION public.edit_content_card(
  p_block_id uuid, p_card_index int, p_before jsonb, p_after jsonb, p_editor uuid,
  p_report_ids uuid[] DEFAULT '{}', p_reverts uuid DEFAULT NULL
) RETURNS uuid
LANGUAGE plpgsql SET search_path = public AS $$
DECLARE
  b   public.content_blocks%ROWTYPE;
  cur jsonb;
  eid uuid;
BEGIN
  SELECT * INTO b FROM public.content_blocks WHERE id = p_block_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'content block not found' USING ERRCODE = 'PT404';
  END IF;
  cur := b.content -> p_card_index;
  IF cur IS NULL THEN
    RAISE EXCEPTION 'card_index out of range' USING ERRCODE = 'PT422';
  END IF;
  IF cur <> p_before THEN
    RAISE EXCEPTION 'card changed since it was loaded' USING ERRCODE = 'PT409';
  END IF;
  IF cur = p_after THEN
    RETURN NULL;                                   -- nothing changed, nothing to log
  END IF;

  UPDATE public.content_blocks
     SET content = jsonb_set(content, ARRAY[p_card_index::text], p_after), updated_at = now()
   WHERE id = p_block_id;

  INSERT INTO public.content_edits
    (block_id, topic_id, lesson_id, mode, scope, card_index, before, after, edited_by, report_ids, reverts)
  VALUES
    (b.id, b.topic_id, b.lesson_id, b.mode, b.scope, p_card_index, cur, p_after, p_editor,
     coalesce(p_report_ids, '{}'), p_reverts)
  RETURNING id INTO eid;
  RETURN eid;
END $$;

REVOKE EXECUTE ON FUNCTION public.edit_content_card(uuid, int, jsonb, jsonb, uuid, uuid[], uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.edit_content_card(uuid, int, jsonb, jsonb, uuid, uuid[], uuid) TO service_role;
