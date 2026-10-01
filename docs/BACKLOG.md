# Turul Academy — Cross-cutting Backlog

_Durable TODO list for ideas/fixes not yet scheduled into an active handoff. Distinct from
`HANDOFF_*.md` files, which are "how to resume in-progress work" — this is "don't lose this
idea when a session gets archived." Added 2026-07-07._

## Product features

- **Felolvasás (read aloud / audiobook mode) — built 2026-10-01, audio not generated yet.** A „Lecke meghallgatása” button
  on every lesson tab (reads the tab card after card, outlines the current card), a „Felolvasás” button on every card and
  deep dive, one per quiz question (question + options, never the answer), and a player bar that stays on every page.
  *Why files:* browsers stop `speechSynthesis` when the screen locks, but keep playing an `<audio>` file and show its
  lock-screen controls (Media Session). So the lesson text is turned into mp3 files once; a card with no file is read
  by the browser's own voice instead (on screen only, the bar says so).
  - *Code:* `backend/core/speech.py` (what is spoken; the only place that decides it), `backend/core/narration.py` +
    `routes/nat.py` / `routes/lessons.py` (each lesson response now carries `narration` per card), `frontend/src/lib/narration.js`
    (player, tested with `npm test`), `NarrationBar` / `ReadAloudButton`, `database/migrations/v11_narration_audio.sql`,
    `content/generators/generate_audio.py`.
  - *To switch the audiobook on (nothing here is done yet):* 1) apply v11 in the Supabase SQL editor; 2) put
    `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION` (or `OPENAI_API_KEY`) in `backend/.env`; 3) `generate_audio.py sample
    --nat-id PHYS-78-03` and **listen** — Hungarian quality differs a lot between voices; 4) `generate_audio.py run
    --nat-id PHYS-78-03 --apply`, then more Témakörök, or `--all --apply --max-chars 3000000`. Re-run after content edits
    (edited cards get a new hash and fall back to the browser voice until then); `prune` deletes audio nobody uses.
  - *Size (measured 2026-10-01 on live content, 6,586 distinct texts):* 3.09 M characters ≈ 60 h ≈ 870 MB at 32 kbit/s,
    ≈ $49 at an assumed $16 per million characters (check the provider's price). Without „Mesélj még!”: 1.93 M ≈ $31;
    only the `text` tab (`--modes text`): 0.85 M ≈ $14.
  - *Not verified:* locked-screen playback on a real iPhone and Android phone (only headless Chromium was available:
    auto-advance, Media Session metadata, navigation persistence). Both TTS providers are implemented against their
    documented REST APIs but have not been called (no key in the cloud session). If iOS drops the card-to-card hand-off
    while locked, the fallback is one mp3 per tab with cue points.
  - *Known gaps:* listening is not counted as study time (the timer needs a visible, touched page); no offline audio
    (files are not cached by the service worker — Safari needs range-request handling for that); pronunciation of
    years/ordinals/names is whatever the voice does, apart from the abbreviations, units and formulas `speech.py` expands.

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

- **Visual-tab images (variant C) — PHYS-78-03 diagrams APPLIED 2026-09-29 (PR #2); 10 photos + 6 more own drawings APPLIED 2026-09-30; three lesson 2–3 cards keep their simple native sketches.**
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

  *Photos applied 2026-09-30, three batches* (`content/media/lesson_images_2026_09b.py --batch 1|2|3`, cards written through `edit_content_card`,
  so undoable from the review queue; files uploaded to `content-media`, sources/licences in `manifest.json`):
  Sebesség mérése (lesson 2; Hungarian radar speed display, CC BY-SA 3.0), Nehézségi erő (lesson 3; NASA feather+hammer
  on the Moon, PD), Önvezérelt autó / Légzsák / Biztonsági öv (lesson 4; lidar CC BY 2.0, crash test CC BY-SA 4.0,
  belted dummy CC BY 2.0). Batch 2 added: motorcycle speedometer (Sebesség, CC BY-SA 4.0), Tasmanian distance sign (Utazásból hátralévő idő, CC BY-SA 4.0), skid marks (Fékezés, CC BY-SA 3.0), stopwatch (Sebesség mérésének eljárása, CC BY 4.0) and a Frankfurt road-safety installation of a car that hit a tree at 120 km/h (Kölcsönhatás).
  Batch 3 (same day, on the owner's request): the tree-crash photo was **replaced by a crash-test photo** (a Corvette that went through a 35 mph ≈ 56 km/h head-on test, shown at an exhibition; JaseMan, CC BY 2.0; the old file `utkozes-fanak.webp` stays in Storage so the edit can be undone from the review queue) and the six remaining graph/screen cards got **own drawings** from `content/media/make_physics_diagrams_2.py`: Átlagsebesség (two-leg trip, 100 km : 2 h = 50 km/h), Sebesség és út kapcsolata (v–t graph, area = 200 m), Idő és távolság (120 km at four speeds), Newton 2. törvénye (same 2 N on 1 kg and 2 kg), and two phone-screen mock-ups, Közlekedéstervezés (route planner) and Mozgás elemzése applikációval (motion-analysis app). **The two phone screens are illustrative drawings, not screenshots of a real app**; they say so on the drawing and in the card text/caption, and their `visual_type` was changed from képernyőfotó/screenshot to „szemléltető rajz”. The card texts next to all of them are new Hungarian text written by the assistant — **not yet read by a teacher** (the owner said the teachers will review them later).

  *Not done:*
  - Three lesson 2–3 cards still show only the simple native sketch (`card.diagram`, drawn by SketchDiagram), no photo or
    finished drawing: Megtett út (lesson 2), Az elejtett test mozgása and Külső hatások az autó mozgásában (lesson 3). Their
    stored description text describes a richer picture than the sketch shows, so a teacher should either accept the sketch or
    ask for a redraw. Every other visual card of the four lessons now has an image; lesson 1 already had its images.
  - Sourcing from the cloud sandbox works only with **curl** at about one request per 40 s: Wikimedia returns 429 (Retry-After)
    when the shared cloud IP is busy, and 403 to Python `httpx` requests even when curl succeeds from the same IP. So
    `source_media.py` (httpx) fails in the cloud; from a normal machine it should work. Do not try to get around the rate limit.
  - The earlier `media_refs` licence table (v10) is used only for the 6 diagrams; the photos are tracked in `manifest.json`
    like lesson 1's images. Decide whether to unify.

  *Still open / unverified:*
  - **Human review of the 6 diagrams' physics** before the lessons go public (the deep-dive layer had 2 subtle errors
    that automated checks missed). The 6 `media_refs` rows are `approved` by default for authored diagrams — this is
    not the same as reviewed. The visual blocks of all 4 PHYS-78-03 lessons were `is_active=true` on 2026-09-30, so the diagrams and the new photos are publicly visible now.
  - Rendering after PR #2's merge (which unified on `card.image`/`card.timeline`/`card.diagram`) was not re-checked in the
    running app; the apply happened before the merge.
  - CC BY / CC BY-SA photos need a visible credit (author, licence, source) in the UI and stored in `media_refs`;
    `CardImage` prints `credit` + a source link under every image (read in code, not seen in the running app). Share-alike may bind cropped/edited derivatives.
  - The owner's own first-task image (on their Mac) was dropped on request (2026-09-30): "forget the first image".
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
