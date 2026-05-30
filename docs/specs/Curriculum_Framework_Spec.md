# CuriousPath — Curriculum Framework (Adapter Pattern)

**Goal:** Build the curriculum layer so it absorbs:
1. **Curriculum version bumps within a region** (NAT 2020 → NAT 2026)
2. **New regions/countries** (US CCSS, UK National Curriculum, AU Australian Curriculum, CA provincial, JP MEXT, etc.)
with **low-to-moderate engineering effort** and **zero learner-data loss**.

This document is the contract every curriculum integration must satisfy.

---

## 1. Design Principles

1. **Abstract first, regional second.** All curricula plug into the same internal model. Region-specific quirks live in adapters, not core schema.
2. **Versioning is a first-class concept.** Every piece of curriculum content carries its `curriculum_id`. New versions = new rows, never mutations.
3. **Stable cross-version keys.** Each topic gets a `stable_topic_key` that survives version bumps for the same concept (e.g. `fractions-addition` stays `fractions-addition` whether under NAT 2020 or NAT 2026).
4. **Mapping > magic.** Cross-version mapping is explicit (`topic_alias_map` collection), not inferred.
5. **Locale-clean.** Curriculum content uses locale-keyed maps everywhere. No assumption of language by curriculum.
6. **Progress survives migration.** Learner progress refs `curriculum_id + topic_id`. When user switches, mapped topics carry forward, unmapped ones surface as "review recommended."
7. **One active curriculum per user at a time** (UX simplicity). System supports more, UI surfaces one.

---

## 2. Conceptual Model

```
CurriculumVersion (HU/NAT/2020)
   └─ Subject (MATH)
        ├─ Topic (fractions)
        │    └─ Lesson (intro-to-fractions)
        │         ├─ ModeVariant: text, story, visual, fact-list, quiz, audio
        │         └─ MediaRef[]
        └─ Topic (algebra)
   └─ Subject (HIST)
   └─ ...
   └─ CrossRef[]
   └─ ExamPrepPack[]

TopicAliasMap (NAT 2020 ↔ NAT 2026)
   └─ from_topic_id → to_topic_id (relation: same / merged / split / removed / renamed)
```

See `Data_Model_Spec.md` for full field-level schemas.

---

## 3. Identifier Strategy (the key to portability)

### 3.1 IDs
- `id` — UUID, globally unique, the actual DB key.
- `curriculum_id` — UUID, identifies version.
- `stable_topic_key` — a **slug** unique within a `curriculum_id` but **intentionally shared** across versions/regions when the underlying concept matches.

### 3.2 `stable_topic_key` naming convention
- `<subject-code>.<topic-slug>[.<subtopic-slug>]`
- All lowercase, dot-separated, ASCII.
- Examples:
  - `math.fractions.addition`
  - `math.algebra.linear-equations`
  - `hist.industrial-revolution`
  - `bio.cell.mitosis`
- Slugs are **concept-based**, not curriculum-jargon-based. "Algebraic identities" is `math.algebra.identities`, not `math.azonosság` (Hungarian-only).

### 3.3 Subject codes (cross-curriculum stable)
| Code | Meaning |
|---|---|
| `MATH` | Mathematics |
| `HIST` | History |
| `BIO` | Biology |
| `CHEM` | Chemistry |
| `PHYS` | Physics |
| `GEO` | Geography |
| `HUN_LIT` | Hungarian Language & Literature (locale-specific) |
| `LIT` | Literature (generic) |
| `LANG_HU` | Hungarian as first language |
| `LANG_EN_FL1` | English as first foreign language |
| `LANG_EN` | English (native, for UK/US/etc.) |
| `CIVICS` | Civic / Citizenship education |
| `ETHICS` | Ethics / Religious Education |
| `ART_VIS` | Visual arts |
| `ART_MUSIC` | Music |
| `DIGITAL` | Digital culture / Computing |
| `TECH` | Technology and design |
| `PE` | Physical education |
| `SCI_INT` | Integrated natural science |
| `MEDIA` | Media literacy / Film |
| `DRAMA` | Drama and theatre |

Region-specific codes use suffixes (e.g. `HUN_LIT` because Hungarian-language literature is locale-bound). The mapping table in each curriculum implementation declares which generic subjects this region's subject relates to.

---

## 4. Adapter Pattern

Each curriculum implementation lives in its own seed/data layer and ships:

```
curriculum_adapters/
   nat_2020_hu/
      metadata.json        # CurriculumVersion row
      subjects.json        # Subject rows
      topics/              # Topic rows (by subject)
      lessons/             # Lesson rows
      quizzes/             # Quiz rows
      crossrefs.json       # CrossRef rows
      locale_strings.json  # Translations
      alias_map_from_<prev>.json  # optional: how this maps from prior version
   nat_2026_hu/            # future, same shape
   ccss_us/                # future
   ukcurr_uk/              # future
   ac_au/                  # future
   ...
```

A loader script ingests these into MongoDB on deploy/seed. No code change needed for a new curriculum — just data + an optional alias map.

---

## 5. Version Migration Lifecycle

```
T0  ┐ NAT 2020 active, 100% of users
    │
T1  │ NAT 2026 imported (status=preview), QA only
    │
T2  │ topic_alias_map (NAT2020 → NAT2026) authored
    │
T3  │ NAT 2026 status=active alongside NAT 2020
    │ → New users default to NAT 2026
    │ → Existing users see opt-in banner: "Your curriculum is updating"
    │
T4  │ Users opt in → server runs migration script:
    │   - read user's progress on NAT 2020
    │   - apply topic_alias_map
    │   - same/renamed → carry forward
    │   - merged/split → surface "review" hint
    │   - removed → archive (still visible in history, not in active path)
    │
T5  ┘ After grace period, NAT 2020 → status=deprecated
    │ Auto-migrate remaining users (with notification)
```

**Key guarantee:** A user's earned XP, badges, streaks, and historical event log are **never reset** by a curriculum upgrade.

---

## 6. Regional Adapter Compatibility Notes

### Hungary (HU)
- Grade bands: 1–4, 5–8, 9–12. Ours: 5–12.
- Single national framework: **NAT** (Nemzeti Alaptanterv) + **kerettanterv** (framework curriculum).
- Subjects map cleanly to our generic codes; only `HUN_LIT`, `LANG_HU`, `LANG_EN_FL1` need locale-aware naming.
- See `Curriculum_Hungary_NAT_2020.md`.

### United States (US) — Future
- No single national curriculum. Two practical anchors:
  - **CCSS** (Common Core State Standards) for Math + ELA (adopted by ~41 states)
  - **NGSS** (Next Generation Science Standards) for Science (~20+ states)
  - State-level standards otherwise (TX, FL, CA have their own)
- **Adapter approach:** Each adopted standard becomes its own `CurriculumVersion`. State curricula get codes like `state_tx_teks_2024`.
- Grade bands: K-12. Need to extend `grade_range` to include K (encoded as 0).
- Subject codes: existing codes work; CCSS-ELA → our `LIT` + `LANG_EN`.

### United Kingdom (UK) — Future
- **National Curriculum (England)** organized by Key Stages:
  - KS1 (Year 1–2), KS2 (Year 3–6), KS3 (Year 7–9), KS4 (Year 10–11), KS5 (Year 12–13)
- Scotland: **Curriculum for Excellence (CfE)** — different structure (Early, First, Second, Third, Fourth, Senior).
- Wales / NI: separate frameworks.
- **Adapter approach:** Each becomes a separate `curriculum_versions` row. Key-stage and year-of-study mapping table required.

### Canada (CA) — Future
- **Provincial** curricula. No national one. Each province (Ontario, BC, Quebec, …) gets its own `curriculum_versions` row.
- Code pattern: `curr_ca_on_2023`, `curr_ca_bc_2024`, etc.

### Australia (AU) — Future
- **Australian Curriculum (ACARA)** — national, current version v9.0.
- Years F (Foundation) – 10 nationally; Years 11–12 are state-level (SACE, HSC, VCE, QCE, WACE).
- Foundation year encoded as grade 0; senior years require state-level extensions.

### Japan (JP) — Future
- **MEXT Course of Study** (学習指導要領), revised on ~10-year cycles.
- Stages: Elementary (Grades 1–6), Lower Secondary (Grades 7–9), Upper Secondary (Grades 10–12).
- Subjects include some without direct generic codes (e.g., 道徳 *moral education*). Add as `MORAL` subject code if needed.

### EU (other) — Future
- Each member state has its own framework. Adapter per state, same pattern as Hungary.

---

## 7. Adding a New Curriculum — Checklist

- [ ] Create `curriculum_adapters/<id>/` folder
- [ ] Write `metadata.json` (CurriculumVersion row)
- [ ] Author `subjects.json` mapping to generic subject codes; add new codes if a subject is region-unique
- [ ] Author `topics/<subject_code>.json` with `stable_topic_key`s (re-use existing keys where concept matches!)
- [ ] Author `lessons/<topic_key>.json` with mode variants
- [ ] Author `quizzes/<lesson_id>.json`
- [ ] Author `crossrefs.json`
- [ ] Add `locale_strings.json` for UI strings if new locale needed
- [ ] (Optional) Write `alias_map_from_<prev_curriculum_id>.json`
- [ ] Run seed/loader; verify in preview mode
- [ ] QA → flip status to `active`

---

## 8. UX Implications

- **One active curriculum visible at a time.** Switching is a settings action with confirmation modal.
- **Migration banner** when admin marks a new version `active`.
- **Locale picker** independent of curriculum (a HU/NAT user can read EN-locale UI; content remains HU).
- **Future:** "Study a topic in another curriculum's framing" link in `crossrefs` (extra context — e.g., a Hungarian student curious how UK frames the Industrial Revolution).

---

## 9. Things Explicitly Out of Scope (For Now)

- Real-time content collaboration across curricula
- Automatic AI-driven curriculum alignment (Phase 6+; risky for accuracy)
- Country-specific exam-board fully simulated (e.g., A-Levels, SATs, IB) — start with general subject prep
- Per-school customization (covered by Phase 6 "school edition" if we ever do it)
