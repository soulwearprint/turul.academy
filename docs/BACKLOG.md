# Turul Academy — Cross-cutting Backlog

_Durable TODO list for ideas/fixes not yet scheduled into an active handoff. Distinct from
`HANDOFF_*.md` files, which are "how to resume in-progress work" — this is "don't lose this
idea when a session gets archived." Added 2026-07-07._

## Product features

- **Layered lesson filter.** A way to find lessons by filtering on **subject + topic + a
  word/phrase**, in any combination (e.g. just a word search across all subjects; or subject +
  word; or all three). Doesn't exist yet in any form — the current nav is pure drill-down
  (Subject → Topic → Téma), no search/filter layer. Needs a search endpoint (probably
  `ILIKE`/full-text search over `curriculum_topics.title_hu` + `curriculum_lessons.title_hu`,
  scoped by optional `subject_id`) and a UI entry point (a search bar, probably on the Subjects
  page or a new dedicated search page).

- ~~**Badges.**~~ Built 2026-09-24: 12 badges, catalogue in `backend/core/badges.py` +
  `frontend/src/lib/badges.js`, awarded after quiz submits / study-time flushes and on opening
  the Progress page. Still open: real badge art (emoji placeholders today).

- **„Mesélj még!” deep-dive layer — POC live on PHYS-78-03 (2026-09-28).** One `deep`
  content block per Téma (level `emelt`), one card per text card via `anchor`; pre-generated,
  no LLM call on tap. Generator: `content/generators/generate_deep_dive.py` (gpt-4o + strict
  claim/misconception verifier + subject validator). ~$0.35 per Témakör. Review docs
  `content/exports/PHYS-78-03_deep_dive_review*.md` (v1 = gpt-4o-mini, too shallow + wrong
  trivia). Automated checks still missed 2 subtle slips → **human review before rolling out
  to more topics.** To pull it: `UPDATE content_blocks SET is_active=false WHERE mode='deep'`.

- **Visual-tab images (variant C) — PHYS-78-03 diagram pilot APPLIED 2026-09-29 (PR #2); photo sourcing NOT done.**
  Tier order: image/timeline (`card.image`, `card.timeline`) → in-house SVG (`card.diagram`, SketchDiagram
  shapes) → text placeholder. Images are self-hosted (never hotlinked), see the `content-media`
  Storage bucket / `content/media/staging/`.

  *Done (and how):*
  - `database/migrations/v10_media_refs.sql` applied by hand in the Supabase SQL editor (see MIGRATION_ORDER).
  - `content/generators/apply_media.py --nat-id PHYS-78-03 --file ../media/PHYS-78-03_diagrams.json`:
    dry-run checked by the owner (all 6 keyword→card matches accepted), then `--apply`. Result: 6 `card.diagram`
    entries written and 6 `media_refs` rows (`kind=diagram`, `status=approved`) across 3 PHYS-78-03 lessons
    (verified by reading `media_refs` back: 6 rows). Diagrams: free fall, braking car / friction, straight vs curved
    path, distance vs displacement, speed magnitude+direction, distance–time–speed.
  - `content/generators/source_media.py` (Commons search, licence whitelist PD/CC0/CC BY/CC BY-SA, writes *pending*
    candidates only, `--download` for human-approved ones) now honours `Retry-After` on HTTP 429 (5 tries, max 120 s wait);
    offline-tested only.

  *Not done, and why:*
  - **No photo candidates were sourced.** Commons refused the cloud sandbox's IP: first 429, then a 403 from
    Wikimedia's edge ("Please respect our robot policy…", even for a plain `siteinfo` call). That is an IP-level block,
    so backoff does not help. Deliberately not worked around. Nothing was written to `PHYS-78-03_candidates.json`.
  - To do it: run from a non-throttled machine (e.g. the owner's Mac), one call per Téma:
    `python source_media.py --nat-id PHYS-78-03 --tema "Mozgások megfigyelése és csoportosítása" --match pálya sebesség --query "motion trajectory car road" --out ../media/PHYS-78-03_candidates.json`,
    `--tema "Út és idő kiszámítása" --match út idő átlagsebesség --query "speedometer car dashboard"`,
    `--tema "Erők és gyorsulás vizsgálata" --match fékez súrlód gyorsul --query "car braking skid marks"`.
    Then a human opens each Commons file page, checks the licence, sets `"status": "approved"`, runs `--download`, then
    `apply_media.py` on the file. Or email bot-traffic@wikimedia.org if cloud-side sourcing is wanted.
  - Open question: whether a Wikimedia personal API token / OAuth lifts the limit for the Commons *Action API* is
    unknown (the docs at www.mediawiki.org were not readable from the sandbox; not needed for an IP block). A
    "bot account" is for editing and is NOT needed for read-only sourcing.

  *Still open / unverified:*
  - **Human review of the 6 diagrams' physics** before the lessons go public (the deep-dive layer had 2 subtle errors
    that automated checks missed). The 6 `media_refs` rows are `approved` by default for authored diagrams — this is
    not the same as reviewed. Whether those lessons are `is_active` (i.e. publicly visible) was not checked.
  - Rendering after PR #2's merge (which unified on `card.image`/`card.timeline`/`card.diagram`) was not re-checked in the
    running app; the apply happened before the merge.
  - CC BY / CC BY-SA photos need a visible credit (author, licence, source) in the UI and stored in `media_refs`;
    confirm `VisualCard` shows it before any photo goes live. Share-alike may bind cropped/edited derivatives.
  - The owner's first-task image (on their Mac) needs the file, author, licence and source URL supplied.
  - Not built: History timelines/maps generator, quarterly link/licence re-check job, curator UI.

- **Emelt-szint (advanced depth layer).** Schema-ready: `content_blocks.level` already supports
  `alap` (default, in use) vs `emelt` (reserved, unused). Needs: a decision on which topics get
  an emelt version, a deeper-prompt variant of the generator, and a UI toggle/tab to switch
  level in the lesson player (`NatLessonPage.jsx` currently only ever requests `alap`).

- **"Kérdezd Turult"** (free-form AI Q&A button). Not built. Would need a new chat-style
  endpoint (likely RAG-lite: pull the current lesson's `content_blocks` as context, forward to
  an LLM) and a UI entry point in the lesson player. Worth thinking about token/cost budget
  before building (flagged in the original scaling-warnings list as needing design work first).

## Known bug to fix — subject-mixing in the 3-tier model

`GET /api/nat/topics` and the frontend `/nat` route have **no subject filter** — they return/
render every topic that has `curriculum_lessons`, regardless of subject. This is harmless today
(only History uses the 3-tier model) but will break the moment Physics content is seeded into
the same tables — the two subjects' topics will interleave in one list.

**User's suggested fix:** move `/api/nat/topics` to `/api/nat/subject/topics`.

**Suggested refinement before implementing** (the literal path above is ambiguous — is
"subject" a static segment or a placeholder for an ID?): the codebase already has a working
precedent for exactly this in the legacy model — `backend/routes/curriculum.py`'s
`GET /api/curriculum/subjects/{subject_id}/topics`. Two ways to match that:

1. **Nested path, mirroring the legacy route** (more RESTful, most consistent with existing
   code): `GET /api/nat/subjects/{subject_id}/topics`. Clean, discoverable, but requires the
   frontend to always know/pass a `subject_id` before it can list anything.
2. **Optional query param on the existing route** (smaller diff): `GET /api/nat/topics?subject_id=...`,
   mirroring how `grade` is *already* an optional filter param on that same endpoint
   (`nat_topics(grade: Optional[int] = None)` in `routes/nat.py`). Backward-compatible — an
   unfiltered call still works (useful for admin/debug tooling) — and requires no new route.

Recommendation: **option 2** — it's the smaller change, consistent with the existing `grade`
filter pattern on the same endpoint, and doesn't force every caller to pre-know a subject_id.
Whichever is chosen, the frontend also needs rewiring: `NatTopicsPage.jsx` needs to receive/read
a subject_id (route param or context) and pass it through; `HomePage.jsx`'s `subjectHref()` and
the inline routing check in `SubjectsPage.jsx` (both currently hardcode `HISTORY → /nat`) need
to route *any* subject with 3-tier content to `/nat` with that subject's id attached.

**This must be fixed before Physics content is seeded**, not after — see `HANDOFF_PHYSICS.md`.

## Physics content style — locked direction (2026-07-07)

For the Physics NAT re-foundation (`HANDOFF_PHYSICS.md`), content should be **less academic,
more hands-on and anecdotal** than the History content's pattern. Specifically, augment the
required definitions/rules (still mandatory — students need these for the curriculum) with,
**where applicable**:
- **Actual experiments** demonstrating the concept — bonus points for ones reproducible at
  home with everyday materials, not just lab equipment.
- **Anecdotes about the circumstances of discovery/invention** — who figured this out, under
  what circumstances, what problem were they trying to solve.
- **Practical, modern-world usage examples** — where this shows up in technology or everyday
  life today, not just historical/textbook framing.

"Where applicable" matters — some physics topics are abstract/mathematical enough that not all
three augmentations will fit naturally; don't force an anecdote or a home experiment where none
exists. This is a content-generation prompt design decision for whoever builds the Physics
generator — likely maps onto specific modes (e.g. `story` mode carries the anecdote/invention
angle, similar to how History's `story` mode carries the bottom-up everyday-life angle; a mode
or block could carry the home-experiment angle) rather than being crammed into every mode
uniformly. Cross-reference: `HANDOFF_PHYSICS.md`'s note that Physics's mode prompts need real
rework, not reuse of History's prompts as-is.
