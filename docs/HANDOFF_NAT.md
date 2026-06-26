# Handoff — NAT Re-foundation (Turul Academy)

_Resumption guide for a fresh chat window. Last updated 2026-06-24._

## Where we are
Pivoting the content model to be faithful to the **official 2024 NAT kerettanterv** (History).
Old content (linear grade 5→12 arc, served from the legacy `lessons` table) is being replaced by a
NAT-accurate **3-tier model**. Live app is untouched — all new work is additive.

## Why (the finding)
- Hungarian history is taught in **two full cycles**, each ancient→present:
  5–6 (survey) + 7–8 (modern era) = általános iskola; 9–10 + 11–12 = gimnázium (deeper).
- NAT is **Hungary-centered**; world history shown through Hungarian examples.
- Old seed mis-mapped grades AND generated **generic** world-history that missed the NAT-**mandatory**
  Hungarian elements (e.g. WWI was missing Tisza István, Károlyi, Tanácsköztársaság, Trianon topography).
  That's the "out of context / explodes review" risk the user flagged.

## Key artifacts (in repo)
- `content/nat_curriculum/history_nat2020.json` — parsed NAT map: **54 Témakör**, **1309 mandatory elements**
  (Fogalmak/Személyek/Kronológia/Topográfia), 4 grade-bands. Source: user's `~/Downloads/Tortenelem_F.docx` (5–8) + `Tortenelem_K.docx` (9–12).
- `database/migrations/v5_content_model_3tier.sql` — the additive schema (applied).
- `content/generators/generate_temakor.py` — NAT-mandatory-driven generator (currently hardcoded for the WWI slice).
- `content/exports/WWI_temakor_review.md` — **the review doc the user should read.**

## The 3-tier model (migration v5, additive)
```
curriculum_topics  (Témakör)
  └─ curriculum_lessons  (Téma)
       └─ content_blocks   mode: text|story|visual|quiz|world
                           level: alap|emelt        scope: lesson|topic
```
One row-model covers: 4 modes + "Világ ekkor" global layer (mode=world) + per-lesson quiz (scope=lesson) +
end-of-topic quiz (scope=topic, lesson_id NULL) + reserved emelt depth (level=emelt). RLS: public read on `is_active`.

## Vertical slice — DONE & validated (WWI)
- Topic `HIST-78-VH1` "Az első világháború és következményei" (grade 7, **is_active=false** so it's hidden from the live app).
- 3 Témák (curriculum_lessons): T1 "…Magyarország a háborúban", T2 "Magyarország 1918–1919-ben", T3 "A trianoni békediktátum".
- 16 content_blocks generated, Hungary-centered, blended causal+human story, grammar-proofread, level=alap.
- **NAT mandatory coverage audited: 30/30 = 100%.** (re-run check: `/tmp/coverage.py` logic — match elements in non-world blocks.)

## PENDING — next steps in order
1. **User reviews** `content/exports/WWI_temakor_review.md` → approve the quality bar.
2. **Frontend for the 3-tier model** (the live app still renders the OLD `lessons` table):
   - Nav: Topic → Lesson(Téma) → Mode; render `content_blocks`.
   - On-demand **"Világ ekkor"** panel (mode=world) in the lesson player.
   - End-of-topic quiz (scope=topic) surfaced at the topic level.
   - Backend: add routes to read `curriculum_lessons` + `content_blocks` (mirror existing service-role pattern — see `core/db.py`, all user-owned reads/writes use `service=True`).
3. **Re-seed all 54 Témakörök** (Topic + Téma) from `history_nat2020.json`; **generalize** `generate_temakor.py`
   beyond WWI's hardcoded element-distribution (distribute each Témakör's mandatory elements across its Témák —
   the docx have the Témák under each Témakör; may need a second parse pass).
4. **Scale generation** across all Témakörök (OpenRouter `gpt-4o-mini`, detached background, ~cents). Auto-publish (is_active=true).
5. **LATER (schema-ready):** emelt-szint layer (level=emelt, deeper prompt) and "Kérdezd Turult" free-form AI button.

## Locked decisions
Topic=Témakör · Lesson=Téma · story=blended causal+human (NO invented named characters) ·
grammar/proofread pass mandatory before publish · model `openai/gpt-4o-mini`.

## Infra quick-ref
- Academy Supabase: `tqsrwhvvghryycgsxfsj` (account support@turul.app). **MCP: use `supabase-turul`.**
- Backend (Railway): `https://api.turul.academy` — redeploy `cd backend && railway up --service turul-academy-api`.
- Frontend (Vercel): `turul.academy` — git push to `main` auto-deploys (root dir = `frontend`).
- Generators run on OpenRouter (key in `backend/.env`) — do NOT consume Claude limits.
- ⚠️ Open security TODO: rotate the OpenRouter key (leaked to terminal earlier). Supabase service key already rotated.
