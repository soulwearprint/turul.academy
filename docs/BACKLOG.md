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

- **Badges.** `user_badges` table + schema already exist (see `routes/progress.py` — `/me`
  already returns `badges`), but nothing ever awards one. Needs: badge definitions (what earns
  one — streaks? topic completion? perfect quiz scores?), an awarding mechanism (probably
  alongside `award_xp()` in `core/xp.py`), and badge art/icons.

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
