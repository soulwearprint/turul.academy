# Handoff — NAT Re-foundation (Turul Academy)

_Resumption guide for a fresh chat window. Last updated 2026-06-26._

## Where we are
Pivoting the content model to be faithful to the **official 2024 NAT kerettanterv** (History).
Old content (linear grade 5→12 arc, served from the legacy `lessons` table) is being replaced by a
NAT-accurate **3-tier model**. Live app is untouched — all new work is additive.

**Progress as of 2026-06-26:** the generator is now **generalized for any Témakör**, all **54 NAT
Témakörök + 166 Témák are seeded** (new topics, `is_active=false`), a **per-topic content guard rail**
is in place, and a **5-topic cross-era review batch** is generated and awaiting the user's quality
sign-off. Only ~49 Témakörök remain to be content-generated. See "STATUS" + "PENDING" below.

## STATUS (2026-06-26)
- **Content quality bar (approved on WWI):** story = 3rd-person bottom-up *everyday* lens across
  DISTINCT life-domains (work/home/power/economy/children/illness), no invented named characters,
  deliberately NOT the top-down causal chain (that's `text`). "Világ ekkor" (world) = 3–4 sentence
  bodies, per-event year, and a CONCRETE causal `link_hu` back to the lesson's Hungarian topic.
- **Guard rail** (`content/generators/validate_temakor.py`, auto-runs after generation): 3 checks per
  topic. (1) **Completeness** — deterministic HARD GATE: every NAT-mandatory element taught in the
  non-world blocks (quote/compound-robust matching) + all 5 modes + topic quiz. (2) **Fact-check** and
  (3) **Appropriateness/brand-voice** — run on **gpt-4o** (bulk generation stays on gpt-4o-mini),
  ADVISORY only (verdict REVIEW, never auto-block), with a confirmation pass to cut false positives.
  Verdicts: PASS / REVIEW / FAIL (FAIL = completeness gap only). It has caught real errors (Horthy's
  1920 regency, Károlyi vs Kun Béla, a Visegrád 1335 anachronism) — all fixed in the WWI/medieval slices.
- **Generalized generator** (`generate_temakor.py --nat-id <topic>`): reads Témák+Altémák from the
  parsed map, an LLM (gpt-4o) distributes the Témakör's mandatory elements across its Témák, generates
  4 modes + world + per-lesson quizzes + topic quiz, idempotently auto-seeds Témák, then guard-rails.
- **Seeded:** 54 NAT topics + 166 Témák via `seed_nat_topics.py` (nat_id `HIST-<band>-NN`; old
  mis-mapped 98 topics left alone — distinguished by "has curriculum_lessons"). All `is_active=false`.
- **Generated + validated (5, all 100% completeness, REVIEW):** WWI `HIST-78-VH1`, medieval
  `HIST-56-MA1`, `HIST-56-03` (kereszténység), `HIST-910-12` (reformkor), `HIST-1112-11` (kádári
  diktatúra). Review docs in `content/exports/*_review.md`.

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
- `content/nat_curriculum/history_nat2020_temak.json` — **second parse pass**: 54 Témakör → 166 Témák
  (+Altémák) + band + elements. Produced by `parse_nat_temak.py`. This is the structure the generator/seeder read.
- `database/migrations/v5_content_model_3tier.sql` — the additive schema (applied).
- `content/generators/generate_temakor.py` — **generalized** NAT generator (`--nat-id <topic>`); LLM element distribution.
- `content/generators/validate_temakor.py` — the **guard rail** (completeness/fact/appropriateness).
- `content/generators/seed_nat_topics.py` — seeds all 54 NAT topics + Témák (idempotent).
- `content/generators/export_temakor_review.py` — renders a topic's content_blocks to a review `.md`.
- `content/exports/*_review.md` — human review docs (WWI, HIST-56-MA1, HIST-56-03, HIST-910-12, HIST-1112-11).

## The 3-tier model (migration v5, additive)
```
curriculum_topics  (Témakör)
  └─ curriculum_lessons  (Téma)
       └─ content_blocks   mode: text|story|visual|quiz|world
                           level: alap|emelt        scope: lesson|topic
```
One row-model covers: 4 modes + "Világ ekkor" global layer (mode=world) + per-lesson quiz (scope=lesson) +
end-of-topic quiz (scope=topic, lesson_id NULL) + reserved emelt depth (level=emelt). RLS: public read on `is_active`.

## GENERATION STATUS (2026-06-27) — 47/54 done, blocked on OpenRouter limit
Ran the full generation via `run_all_nat.py` (parallelized, guard-rail + 2-round auto-fix per topic,
in resumable foreground chunks). **47/54 Témakörök fully generated**; most REVIEW, a few PASS.

- **BLOCKED:** the OpenRouter key hit its **$15 monthly limit** ($15.08/$15) — all calls now 403
  ("Key limit exceeded"). See [[reference-openrouter-limit]]. **Unblock:** raise the cap / add credits at
  the OpenRouter workspace, then `python run_all_nat.py` (resumable) finishes the rest.
- **7 topics NOT yet generated** (0 content_blocks): HIST-1112-09, -10, -12, -13, -14, -15, -16
  (the final gimnázium 11–12 Témakörök).
- **7 topics generated but verdict=FAIL** (content exists, but a NAT element coverage gap the auto-fix
  couldn't close in 2 rounds — need a re-run once unblocked): HIST-56-08, HIST-78-04, HIST-78-08,
  HIST-910-02, HIST-910-05, HIST-910-07, HIST-910-08.
- Runner cost ≈ $0.30–0.35/Témakör; budget ~$18–20 for all 54.

## PENDING — next steps in order
1. **Unblock OpenRouter** (raise key limit) → `python run_all_nat.py` to finish the 7 ungenerated + redo
   the 7 FAILs (resumable — only touches incomplete/failed topics; FAILs need `--regen-all` or per-`--nat-ids`).
2. **User reviews the generated content** (`python export_temakor_review.py <nat-id>` → `content/exports/*_review.md`).
   All content `is_active=true` at block level but topics `is_active=false` (hidden from live app).
   Advisory fact flags to teacher-check before go-live: reformkor (alsótábla/Metternich), kereszténység (Ábrahám dating), etc.
3. **Frontend for the 3-tier model** (the live app still renders the OLD `lessons` table):
   - Nav: Topic → Lesson(Téma) → Mode; render `content_blocks`.
   - On-demand **"Világ ekkor"** panel (mode=world) in the lesson player.
   - End-of-topic quiz (scope=topic) surfaced at the topic level.
   - Backend: add routes to read `curriculum_lessons` + `content_blocks` (mirror existing service-role pattern — see `core/db.py`, all user-owned reads/writes use `service=True`).
   - Cutover: flip new NAT topics `is_active=true` and retire/hide the old mis-mapped 98 topics.
4. **LATER (schema-ready):** emelt-szint layer (level=emelt, deeper prompt) and "Kérdezd Turult" free-form AI button.

## Locked decisions
Topic=Témakör · Lesson=Téma · story = **3rd-person bottom-up everyday lens across distinct life-domains**
(NO invented named characters; NOT the top-down causal chain) · world = fuller body + per-event year +
concrete causal link_hu · grammar/proofread pass mandatory · generation model `openai/gpt-4o-mini`,
distribution + guard-rail judging on `openai/gpt-4o` · completeness is the only hard gate, fact +
appropriateness are advisory · 54 NEW NAT topics (old 98 left for the live app until cutover).

## Infra quick-ref
- Academy Supabase: `tqsrwhvvghryycgsxfsj` (account support@turul.app). **MCP: use `supabase-turul`.**
- Backend (Railway): `https://api.turul.academy` — redeploy `cd backend && railway up --service turul-academy-api`.
- Frontend (Vercel): `turul.academy` — git push to `main` auto-deploys (root dir = `frontend`).
- Generators run on OpenRouter (key in `backend/.env`) — do NOT consume Claude limits.
- ⚠️ Open security TODO: rotate the OpenRouter key (leaked to terminal earlier). Supabase service key already rotated.
