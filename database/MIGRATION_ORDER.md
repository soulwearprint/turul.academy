# Turul Academy — Migration Order

Apply migrations in order via Supabase SQL Editor.
Supabase project: https://neshzfcetxradwhbmdbb.supabase.co

## Applied

| Version | File | Description | Status |
|---|---|---|---|
| v1 | v1_foundation.sql | Core schema: curriculum, lessons, quiz, progress, gamification, RLS, grants | ⬜ pending |

## Rules

- Never edit an applied migration — create a new version instead
- Always include RLS policies AND explicit GRANTs in every new table
- Naming: `v{N}_{description}.sql`
- Update this file when applying each migration
