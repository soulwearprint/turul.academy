# Turul Academy — Migration Order

Apply migrations in order via Supabase SQL Editor.
Supabase project: https://tqsrwhvvghryycgsxfsj.supabase.co

## Applied

| Version | File | Description | Status |
|---|---|---|---|
| v1 | v1_foundation.sql | Core schema: curriculum, lessons, quiz, progress, gamification, RLS, grants | ⬜ pending |
| v7 | v7_study_stats_badges.sql | NAT time tracking (accumulated + per mode), daily study seconds, `nat_quiz_attempts` log (backfilled), unique badges, card-count view, atomic increment RPCs | ✅ applied 2026-09-24 |
| v8 | v8_content_reports.sql | `content_reports` („Hibát találtál?” queue) + trigger stopping users from changing their own `role` (was self-promotable to admin via REST) | ✅ applied 2026-09-28 |

## Rules

- Never edit an applied migration — create a new version instead
- Always include RLS policies AND explicit GRANTs in every new table
- Naming: `v{N}_{description}.sql`
- Update this file when applying each migration
