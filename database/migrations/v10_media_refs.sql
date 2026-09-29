-- v10_media_refs — audit/review trail for images shown on „visual” cards.
--
-- Fallback order (docs/specs/Content_Sourcing_Policy.md §3):
--   sourced asset (Wikimedia Commons etc., licence-checked)  →  in-house generated SVG  →  text-only.
-- The card JSON (content_blocks.content[i].media / .diagram) is what the app renders; this table
-- is the licence + review record behind every `media` entry, so an asset can be traced, re-checked
-- and soft-deleted (deleted_at) without losing history. In-house SVG diagrams get a row too
-- (kind='svg', license='in-house').
--
-- Backend/script-only: RLS on, no client policies. Approved rows are exposed to the app through the
-- card JSON, not by direct table reads (attribution is embedded in the card at apply time).

CREATE TABLE IF NOT EXISTS public.media_refs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id        uuid REFERENCES public.curriculum_topics(id) ON DELETE CASCADE,
  lesson_id       uuid REFERENCES public.curriculum_lessons(id) ON DELETE CASCADE,
  card_heading    text NOT NULL,                       -- card matched on heading (indexes shift on regeneration)
  kind            text NOT NULL CHECK (kind IN ('photo', 'svg', 'diagram')),
  title           text,
  source_url      text,                                -- landing page (e.g. Commons file page); NULL for in-house
  asset_path      text,                                -- self-hosted copy, e.g. /media/PHYS-78-03/x.jpg — never hotlinked
  author          text,
  license         text NOT NULL,                       -- 'CC0' | 'PD' | 'CC-BY-4.0' | 'CC-BY-SA-4.0' | 'in-house' ...
  license_url     text,
  attribution     text NOT NULL,                       -- exact credit line shown under the image
  status          text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  verified_by     uuid REFERENCES public.user_profiles(id) ON DELETE SET NULL,   -- curator ≠ author
  verified_at     timestamptz,
  last_checked_at timestamptz,                         -- quarterly link/licence re-check
  deleted_at      timestamptz,                         -- soft delete → card falls back to the next tier
  created_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (status <> 'approved' OR verified_at IS NOT NULL OR license = 'in-house')
);
CREATE INDEX IF NOT EXISTS media_refs_lesson ON public.media_refs(lesson_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS media_refs_status ON public.media_refs(status) WHERE deleted_at IS NULL;

ALTER TABLE public.media_refs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.media_refs FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.media_refs TO service_role;
