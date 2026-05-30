# Curriculum: Hungary — NAT 2020 (First Implementation)

This is the first concrete curriculum implementation, plugged into the framework defined in `Curriculum_Framework_Spec.md`.

**`curriculum_versions` row (planned):**
```json
{
  "id": "<uuid>",
  "region": "HU",
  "framework_name": "NAT",
  "version_tag": "2020",
  "grade_range": [5, 12],
  "primary_locale": "hu",
  "supported_locales": ["hu", "en"],
  "status": "active",
  "effective_from": "2020-09-01",
  "effective_until": null,
  "notes": "Hungary National Core Curriculum 2020 + kerettanterv. NAT 2026 in preparation."
}
```

---

## 1. Subject Catalog

### 1.1 Lower secondary (Grades 5–8)

| Generic Code | Name (HU) | Name (EN) | Grades | Typical weekly hours (5→8) |
|---|---|---|---|---|
| `HUN_LIT` | Magyar nyelv és irodalom | Hungarian Language and Literature | 5–8 | 4, 4, 3, 3 |
| `MATH` | Matematika | Mathematics | 5–8 | 4, 4, 3, 3 |
| `HIST` | Történelem | History | 5–8 | 2, 2, 2, 2 |
| `CIVICS` | Állampolgári ismeretek | Citizenship | 8 | 1 (Grade 8) |
| `ETHICS` | Etika / hit- és erkölcstan | Ethics / R.E. | 5–8 | 1 each |
| `SCI_INT` | Természettudomány | Integrated Natural Science | 5–6 | 2, 2 |
| `CHEM` | Kémia | Chemistry | 7–8 | 1, 2 |
| `PHYS` | Fizika | Physics | 7–8 | 1, 2 |
| `BIO` | Biológia | Biology | 7–8 | 2, 1 |
| `GEO` | Földrajz | Geography | 7–8 | 2, 1 |
| `LANG_EN_FL1` | Első idegen nyelv (jellemzően angol) | First Foreign Language (typically English) | 5–8 | 3, 3, 3, 3 |
| `ART_VIS` | Vizuális kultúra | Visual Culture | 5–8 | varies |
| `ART_MUSIC` | Ének-zene | Music | 5–8 | varies |
| `DIGITAL` | Digitális kultúra | Digital Culture | 5–8 | varies |
| `TECH` | Technika és tervezés | Technology and Design | 5–7 | 1 each |
| `PE` | Testnevelés | Physical Education | 5–8 | 5 each |
| `HON_NEP` | Hon- és népismeret | National Heritage Studies | 6 | 1 (Grade 6) |

### 1.2 Upper secondary (Grades 9–12, gimnázium)

| Generic Code | Name (HU) | Name (EN) | Grades | Typical weekly hours (9→12) |
|---|---|---|---|---|
| `HUN_LIT` | Magyar nyelv és irodalom | Hungarian Language and Literature | 9–12 | 3, 4, 4, 4 |
| `MATH` | Matematika | Mathematics | 9–12 | 3, 3, 3, 3 |
| `HIST` | Történelem | History | 9–12 | 2, 2, 3, 3 |
| `CIVICS` | Állampolgári ismeretek | Citizenship | 12 | (Grade 12) |
| `ETHICS` | Etika / hittan | Ethics / R.E. | 9–12 | varies |
| `SCI_INT` | Természettudomány | Integrated Natural Science | 11 | 1 (Grade 11) |
| `CHEM` | Kémia | Chemistry | 9–10 | 1, 2 |
| `PHYS` | Fizika | Physics | 9–10 | 2, 3 |
| `BIO` | Biológia | Biology | 10–11 | 3, 2 |
| `GEO` | Földrajz | Geography | 9–10 | 2, 1 |
| `LANG_EN_FL1` | Első idegen nyelv | First Foreign Language | 9–12 | 3, 3, 4, 4 |
| `LANG_FL2` | Második idegen nyelv | Second Foreign Language | 9–12 | 3, 3, 3, 3 |
| `ART_VIS` | Vizuális kultúra | Visual Culture | 9–10 | varies |
| `ART_MUSIC` | Ének-zene | Music | 9–10 | varies |
| `DRAMA` | Dráma és színház | Drama and Theatre | 12 | (Grade 12) |
| `MEDIA` | Mozgóképkultúra és médiaismeret | Film and Media Studies | 12 | (Grade 12) |
| `DIGITAL` | Digitális kultúra | Digital Culture | 9–11 | varies |
| `PE` | Testnevelés | Physical Education | 9–12 | 5 each |

> Source: Eurydice summary of NAT 2020 and `kerettanterv`. Numbers are typical mandates; specific schools may adjust within national framework.

**Mandatory weekly hours:** 32 / 32 / 30 / 29 (Grades 9–12). Up to 34 with electives.

---

## 2. MVP Subject Selection

For the first build, we pilot **3 subjects** with the widest learner appeal and content diversity:

| Code | Why this subject in MVP |
|---|---|
| `MATH` | Universally required; high anxiety/fatigue subject; demonstrates value of mode-switching (visual ↔ text ↔ practice) |
| `HIST` | Story-mode and curiosity links shine here; demonstrates the curiosity engine clearly |
| `BIO` | Visual-mode showcase (cells, anatomy, ecosystems); curated diagrams available |

**Out of MVP** (but in catalog): all other subjects.

---

## 3. MVP Content Seeds (sample topics — to be authored by Content team)

### MATH — Grade 6 sample topics
- `math.fractions.intro` — What is a fraction?
- `math.fractions.addition` — Adding fractions with like/unlike denominators
- `math.geometry.area-of-rectangles` — Rectangles & area

### HIST — Grade 7 sample topics
- `hist.ancient.rome-rise` — Rise of the Roman Republic
- `hist.middle-ages.feudalism` — How feudalism worked
- `hist.industrial-revolution` — The Industrial Revolution (cross-ref-rich)

### BIO — Grade 8 sample topics
- `bio.cell.intro` — Cell structure essentials
- `bio.ecosystems.food-webs` — Food webs and trophic levels
- `bio.human.respiratory-system` — How we breathe

Total MVP launch target: **~9 fully-authored topics → ~27 lessons across the three subjects**. Each lesson with all 6 modes is authored.

---

## 4. Curiosity Cross-Reference Seeds (curated MVP set)

Examples (to be expanded by content team):

| From topic | To node | Relation |
|---|---|---|
| `hist.industrial-revolution` | Person: James Watt | `inventor-of` (steam engine) |
| `hist.industrial-revolution` | `bio.ecosystems.food-webs` | `practical-application` (impact on ecosystems) |
| `math.geometry.area-of-rectangles` | Concept: Pythagorean theorem | `related-concept` |
| `bio.cell.intro` | Person: Robert Hooke | `historical-context` (coined "cell") |
| `hist.ancient.rome-rise` | `math.fractions.intro` | `historical-context` (Roman numerical systems) |
| `bio.human.respiratory-system` | `hist.industrial-revolution` | `practical-application` (smog & lung health) |

---

## 5. Matura / Exam Prep Mapping (Future Phase 5 focus)

Hungary's `érettségi vizsga` (matura) is taken at Grade 12 with:
- **Mandatory subjects:** Hungarian Language & Literature, Mathematics, History, a Foreign Language, plus one elective
- **Levels:** standard (`középszint`) and advanced (`emelt szint`)

MVP exam prep targets **standard-level** prep paths per pilot subject. Advanced level deferred. Mock-exam simulator is Phase 5 P2.

---

## 6. NAT 2026 Readiness Notes

NAT 2026 is anticipated. To absorb it cleanly:

- Reuse all `stable_topic_key`s where the concept is unchanged (likely the vast majority of MATH, BIO, basic HIST).
- Author `alias_map_from_nat_2020_to_nat_2026.json` once changes are known.
- Migration script will surface "you already mastered this" hints for unchanged topics.
- New topics get new `stable_topic_key`s; removed topics archived (history preserved).
- Grade-level shifts for a topic (e.g., moved from Grade 8 to Grade 7) handled via the `Mapping.relation = "renamed"` with notes.

---

## 7. Open Items for Content Team

1. Final approval on the 3 MVP subjects and 9 topics list
2. Provisional content authors (subject-matter experts)
3. Curated video whitelist sign-off for each subject (see `Content_Sourcing_Policy.md`)
4. EN translation pass for UI strings only (lesson content remains HU at MVP launch)
