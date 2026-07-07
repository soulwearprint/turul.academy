# Handoff — NAT Re-foundation, Physics (Turul Academy)

_Resumption guide for a fresh chat window. Written 2026-07-07, after completing the same
re-foundation for History — see `docs/HANDOFF_NAT.md` for the full precedent._

## Goal
Do for Physics (Fizika) what was just done for History: replace the legacy, NAT-unfaithful
`lessons`-table content with the NAT-2020-accurate 3-tier model (`curriculum_topics` →
`curriculum_lessons` (Téma) → `content_blocks`), generated + guard-rail-validated + deployed.

## Current state (legacy, still live)
Physics has **36 topics, grades 7–11**, on the OLD model — served from the legacy `lessons`
table via `/api/curriculum/*`, exactly how History looked before its re-foundation. Subject
row: `curriculum_subjects` code `HU-NAT-PHYSICS-2020`. Nothing to touch here until the new
content is ready to cut over — the live app keeps serving these 36 topics in the meantime.

## What's actually reusable — and what ISN'T (read this before starting)

**Reusable as-is (architecture + infra):**
- The 3-tier schema (`curriculum_lessons`, `content_blocks` — migration v5) is subject-agnostic;
  no schema change needed, just a different `subject_id`.
- The guard rail's **completeness/fact/appropriateness/auto-fix machinery** in
  `content/generators/validate_temakor.py` and the parallelized, resumable, budgeted runner
  pattern in `run_all_nat.py` — the *process* (generate → validate → auto-fix loop → chunked
  resumable runs) is sound and proven at 54-topic scale.
- The frontend card renderers (`ContentCards.jsx`: text/story/visual/world/QuizRunner) — the
  4-mode + world-layer + scored-quiz UI pattern works for any subject's content.
- Backend `routes/nat.py` reads (`/topics`, `/topics/{id}`, `/lessons/{id}`, `/quiz/submit`,
  `/progress/me`) are already subject-agnostic **in behavior** — see the bug below though.
- XP/progress (`core/xp.py`, `nat_lesson_progress`, `nat_quiz_results`, migration v6) — fully
  shared, no changes needed; a Physics quiz will award XP into the same pool as History.

**NOT reusable without real rework:**
1. **⚠️ Subject-mixing bug to fix FIRST.** `GET /api/nat/topics` and the frontend `/nat` route
   have **no subject filter** — they return/render *every* topic that has `curriculum_lessons`,
   regardless of subject. The moment Physics topics exist in this model, `/nat` will interleave
   History and Physics topics in one list. **Full writeup + recommended fix: see
   `docs/BACKLOG.md`** ("Known bug to fix — subject-mixing in the 3-tier model"). Fix this
   before generating/seeding any Physics content.
2. **The NAT element taxonomy is History-shaped.** `parse_nat_temak.py`,
   `history_nat2020.json`/`history_nat2020_temak.json`, and every generator/guard-rail prompt
   assume four categories: `fogalmak` (concepts) / `szemelyek` (people) / `kronologia`
   (chronology) / `topografia` (places). That's how the History kerettanterv is organized —
   Physics's official NAT 2020 document is very unlikely to use the same four categories (think
   concepts/formulas/experiments/units, or similar — **check the actual source docx first**).
   Expect to:
   - Write a **new parser** (`parse_nat_temak_physics.py` or a generalized version) once you
     have the source docx and can see its real structure — don't assume the History parser's
     table-column layout transfers.
   - Rewrite the mandatory-element categories and the `elem_block()` formatting in
     `generate_temakor.py` to match whatever Physics actually specifies.
   - Rewrite the mode prompts (`prompt()` in `generate_temakor.py`) — the "Hungary-centered,
     mandatory elements" framing was written for history; physics content should probably keep
     the STORY mode's "everyday/bottom-up" pivot (it's a good pattern regardless of subject) but
     the concept/fact framing needs subject-appropriate language, not history's `SYS` prompt.
   - Re-examine whether "Világ ekkor" (parallel world events) even makes sense for Physics, or
     whether the world-layer should become something else (e.g. "in practice today" / real-world
     applications). Don't force History's global-history layer onto physics without thinking
     about whether it's the right pedagogical move — ask the user if unsure.
3. **No source document yet.** Unlike History (`~/Downloads/Tortenelem_F.docx` +
   `Tortenelem_K.docx`, official 2024 kerettanterv), there is no equivalent Physics kerettanterv
   docx in this repo or `~/Downloads/`. **First step of the next session: ask the user for the
   official NAT 2020 Fizika kerettanterv document(s)** (likely one per grade-band, mirroring
   History's F/5–8 + K/9–12 split — Physics currently spans grades 7–11 in the legacy data, so
   confirm the actual official band structure from the source rather than assuming it matches
   History's).

## Recommended order (mirrors how History actually went, adjusted for the above)
1. Get the source docx from the user; parse its actual structure (don't assume History's).
2. Build/adapt the parser → a `physics_nat2020(_temak).json` equivalent.
3. Fix the subject-mixing bug in `routes/nat.py` + frontend routing (do this before generating
   anything, so History doesn't regress when Physics topics start appearing in `curriculum_lessons`).
4. Adapt `generate_temakor.py`'s prompts/categories for Physics; validate the story/world/quiz
   pivots make sense for this subject (ask the user, don't assume history's answers transfer).
   **Locked content direction (user, 2026-07-07 — full detail in `docs/BACKLOG.md`): Physics
   content should be less academic, more hands-on/anecdotal.** Keep the required definitions/
   rules, but augment them — where applicable — with reproducible-at-home experiments,
   anecdotes about the circumstances of discovery/invention, and modern real-world usage
   examples. Don't force these where a topic is too abstract for them.
5. Seed scaffolds (adapt `seed_nat_topics.py`: new `SUBJECT_PHYSICS` id, a fresh grade-band split
   — reuse the hours-balanced-split logic, it's subject-agnostic).
6. Generate a small cross-topic review batch first (2–3 topics spanning different grades/eras of
   physics) and get the user's sign-off on quality **before** the full run — this caught real
   problems in History (story mode's names bug, world-layer vagueness) and is worth repeating.
7. Full generation run via the resumable/budgeted `run_all_nat.py` pattern. Watch the OpenRouter
   spend cap (~$0.30–0.35/Témakör in History; rotate the key first, see HANDOFF_NAT.md's open TODO).
8. Advisory sweep (`sweep_validate.py`) for a teacher pass.
9. Cutover: activate Physics's new topics, retire the 36 legacy ones, wire frontend routing
   (now correctly subject-scoped per step 3).

## Infra quick-ref (unchanged from History)
- Academy Supabase: `tqsrwhvvghryycgsxfsj`. MCP: `supabase-turul`.
- Backend (Railway): `https://api.turul.academy` — **deploys via `railway up --service
  turul-academy-api` (CLI, manual) — does NOT auto-deploy on git push.** This bit the History
  rollout once (pushed code sat undeployed for weeks); don't forget it for Physics.
- Frontend (Vercel): `turul.academy` — auto-deploys on push to `main`.
- Generators run on OpenRouter (key in `backend/.env`), separate from Claude usage.
