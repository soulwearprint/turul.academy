# CuriousPath — Data Model Specification

**Database:** MongoDB (single DB, `DB_NAME` from env).
**Convention:** All collections use UUID `id` fields (string, not ObjectId) for portability. Server-side Pydantic response models explicitly exclude `_id`.

---

## 1. Collection Map

| Collection | Purpose | Versioned? | Indexed on |
|---|---|---|---|
| `users` | Auth + identity | No | `email` (unique), `id` |
| `learner_profiles` | Per-user learning prefs & state | No | `user_id` |
| `curriculum_versions` | Metadata about each curriculum (NAT 2020, NAT 2026, CCSS, …) | — | `id`, `region`, `version_tag` |
| `subjects` | Subject definitions | Yes (by curriculum) | `curriculum_id`, `code` |
| `topics` | Topic definitions | Yes (by curriculum) | `curriculum_id`, `subject_id`, `stable_topic_key` |
| `lessons` | Lesson content + all mode variants | Yes (by curriculum) | `curriculum_id`, `topic_id`, `id` |
| `progress` | Per-user per-lesson progress | No | `user_id`, `lesson_id` (compound), `user_id+topic_id` |
| `mastery` | Per-user per-topic mastery estimate | No | `user_id+topic_id` |
| `gamification_state` | XP, level, streak, badges, tier | No | `user_id` |
| `events` | Append-only event log (play, complete, mode-switch, …) | No | `user_id+timestamp` |
| `crossrefs` | Curated topic-to-topic curiosity links | Yes (by curriculum) | `from_topic_id`, `to_topic_id` |
| `quizzes` | Quiz items per lesson | Yes (by curriculum) | `lesson_id` |
| `quiz_attempts` | User quiz submissions | No | `user_id+lesson_id` |
| `exam_prep_packs` | Subject-level revision pack metadata | Yes (by curriculum) | `subject_id` |
| `topic_alias_map` | Cross-version topic ID mapping | — | `from_curriculum_id+to_curriculum_id` |
| `locale_strings` | Translatable strings | — | `key+locale` |

---

## 2. Schemas (Pydantic-style sketches)

### 2.1 `users`
```python
class User:
    id: str                       # uuid
    email: str
    password_hash: str            # bcrypt
    locale: str = "hu"            # ISO 639-1
    created_at: datetime          # UTC, stored as ISO string
    last_login_at: datetime | None
    is_deleted: bool = False
    deleted_at: datetime | None
```

### 2.2 `learner_profiles`
```python
class LearnerProfile:
    user_id: str
    grade: int                                  # 5..12
    active_curriculum_id: str                   # FK -> curriculum_versions.id
    subjects: list[str]                         # subject_ids the learner picked
    learning_style_prefs: list[str]             # ['visual', 'story', ...] ordered preference
    accessibility:
        font: str = "default"                   # 'default' | 'dyslexia'
        text_size: str = "M"                    # S | M | L | XL
        theme: str = "light"                    # 'light' | 'dark' | high-contrast key
        audio_enabled: bool = False
    gamification_preset: str = "light"          # 'minimal' | 'light' | 'full'
    pacing: str = "balanced"                    # 'sprint' | 'balanced' | 'deep'
    goals: list[Goal]                           # see below
    created_at: datetime
    updated_at: datetime

class Goal:
    id: str
    description: str                            # e.g. "Finish Math Grade 6 by June"
    subject_id: str | None
    target_date: datetime | None
    completed: bool = False
```

### 2.3 `curriculum_versions`
```python
class CurriculumVersion:
    id: str
    region: str                                 # 'HU' | 'US' | 'UK' | 'AU' | 'CA-ON' | 'JP' | ...
    framework_name: str                         # 'NAT', 'CCSS', 'National Curriculum', ...
    version_tag: str                            # '2020', '2026', 'CCSS-Math-2010', ...
    grade_range: tuple[int, int]                # (5, 12)
    primary_locale: str                         # 'hu', 'en-US', ...
    supported_locales: list[str]                # ['hu', 'en']
    status: str                                 # 'active' | 'preview' | 'deprecated'
    effective_from: date
    effective_until: date | None
    notes: str | None                           # 'NAT 2026 preview — partial subjects'
```

### 2.4 `subjects`
```python
class Subject:
    id: str
    curriculum_id: str
    code: str                                   # stable cross-version code, e.g. 'MATH', 'HIST', 'BIO'
    name_locale: dict[str, str]                 # {'hu': 'Matematika', 'en': 'Mathematics'}
    icon_key: str                               # 'function', 'scroll', 'leaf' (lucide-react names)
    grade_range: tuple[int, int]
    description_locale: dict[str, str]
    order: int                                  # sort order
```

### 2.5 `topics`
```python
class Topic:
    id: str
    curriculum_id: str
    subject_id: str
    parent_topic_id: str | None                 # supports hierarchical topics
    stable_topic_key: str                       # cross-version-stable, e.g. 'frac-add-1'
    name_locale: dict[str, str]
    grade: int                                  # primary grade
    grade_range: tuple[int, int] | None         # if spans grades
    order: int
    summary_locale: dict[str, str]
    learning_outcomes: list[str]                # locale-keyed array of outcome IDs
    estimated_minutes: int                      # informational
```

### 2.6 `lessons`
```python
class Lesson:
    id: str
    curriculum_id: str
    topic_id: str
    title_locale: dict[str, str]
    order: int
    estimated_minutes: int
    modes: dict[str, ModeContent]               # keyed by mode name
    media: list[MediaRef]
    quiz_id: str | None                         # FK to quizzes
    crossref_ids: list[str]                     # FK to crossrefs (curated curiosity links)
    version: int = 1                            # bump on content edit; client cache invalidation

class ModeContent:
    cards: list[Card]                           # each card = atomic concept
    locale: str

class Card:
    id: str
    type: str                                   # 'text' | 'fact-list' | 'story' | 'visual' | 'audio-script'
    body_locale: dict[str, str]                 # for text-bearing types
    media_ref: str | None                       # for visual
    audio_ref: str | None

class MediaRef:
    id: str
    kind: str                                   # 'video-embed' | 'illustration' | 'diagram'
    source_url: str
    source_attribution: str                     # required for verified videos
    license: str                                # 'CC-BY-SA', 'public-domain', 'fair-use-edu', 'in-house'
    locale: str
```

### 2.7 `progress`
```python
class Progress:
    id: str
    user_id: str
    lesson_id: str
    topic_id: str
    subject_id: str
    curriculum_id: str
    status: str                                 # 'not_started' | 'in_progress' | 'completed'
    last_card_id: str | None
    last_mode: str | None
    completion_pct: float                       # 0..1
    started_at: datetime | None
    completed_at: datetime | None
    last_active_at: datetime
    mode_switches: int = 0
```

### 2.8 `mastery`
```python
class Mastery:
    user_id: str
    topic_id: str
    subject_id: str
    curriculum_id: str
    confidence: float                           # 0..1, computed
    quiz_attempts_count: int
    last_quiz_score: float | None
    last_updated_at: datetime
    weak_area: bool                             # surfaced if confidence < threshold and attempts > N
```

### 2.9 `gamification_state`
```python
class GamificationState:
    user_id: str
    xp: int = 0
    level: int = 1
    streak_count: int = 0
    longest_streak: int = 0
    last_check_in_date: date | None
    badges: list[BadgeRef]
    current_side_quest: SideQuest | None
    cosmetic_unlock_tier: int = 1               # 1..N (gating ONLY for cosmetics)
    preset: str = "light"                       # mirror of profile preference
    updated_at: datetime

class BadgeRef:
    badge_key: str                              # 'first-lesson', 'topic-mastery-math-fractions'
    earned_at: datetime
    tier: int = 1                               # bronze/silver/gold for repeatable badges

class SideQuest:
    quest_key: str                              # 'do-1-quiz-today'
    description_locale: dict[str, str]
    progress: float                             # 0..1
    expires_at: datetime
    reward_xp: int
```

### 2.10 `events` (append-only)
```python
class Event:
    id: str
    user_id: str
    type: str                                   # 'lesson_start' | 'card_view' | 'mode_switch' | 'lesson_complete' | 'quiz_submit' | 'check_in' | 'stuck_pressed'
    payload: dict                               # flexible
    timestamp: datetime
```

### 2.11 `crossrefs`
```python
class CrossRef:
    id: str
    curriculum_id: str
    from_topic_id: str
    to_node:
        kind: str                               # 'topic' | 'person' | 'invention' | 'work' | 'event' | 'concept'
        ref_id: str | None                      # if 'topic', then topic id
        name_locale: dict[str, str]
        summary_locale: dict[str, str]
        source_attribution: str | None
    relation_kind: str                          # 'related-concept' | 'inventor-of' | 'historical-context' | 'real-world-application'
    curated_by: str                             # author id
    confidence: str = "curated"                 # 'curated' (default) | 'ai-suggested' (Phase 4 only)
```

### 2.12 `quizzes` and `quiz_attempts`
```python
class Quiz:
    id: str
    lesson_id: str
    locale: str
    items: list[QuizItem]

class QuizItem:
    id: str
    type: str                                   # 'mcq' | 'true-false' | 'short-text'
    prompt_locale: dict[str, str]
    options_locale: list[dict[str, str]] | None
    correct_option_index: int | None
    correct_text_alternatives: list[str] | None
    difficulty: int                             # 1..5
    explanation_locale: dict[str, str]

class QuizAttempt:
    id: str
    user_id: str
    quiz_id: str
    lesson_id: str
    started_at: datetime
    submitted_at: datetime | None
    answers: list[Answer]
    score: float                                # 0..1
    elapsed_seconds: int

class Answer:
    item_id: str
    response: str | int                         # text or option index
    correct: bool
    time_spent_seconds: int
```

### 2.13 `topic_alias_map` (cross-version migration)
```python
class TopicAliasMap:
    id: str
    from_curriculum_id: str                     # e.g. NAT 2020
    to_curriculum_id: str                       # e.g. NAT 2026
    mappings: list[Mapping]

class Mapping:
    from_topic_id: str
    to_topic_id: str | None                     # None = topic removed
    relation: str                               # 'same' | 'merged' | 'split' | 'removed' | 'renamed'
    notes: str | None
```

### 2.14 `locale_strings`
```python
class LocaleString:
    key: str                                    # e.g. 'onboarding.welcome'
    locale: str                                 # 'hu', 'en'
    value: str
    context: str | None                         # for translators
```

---

## 3. Critical Indexes

- `users.email` — unique
- `learner_profiles.user_id` — unique
- `progress` — compound `(user_id, lesson_id)` unique; secondary `(user_id, topic_id)`
- `mastery` — compound `(user_id, topic_id)` unique
- `gamification_state.user_id` — unique
- `events` — `(user_id, timestamp)` descending
- `topics.stable_topic_key` — non-unique (intentional; can repeat across versions); but `(curriculum_id, stable_topic_key)` unique
- `lessons` — `(curriculum_id, topic_id, order)`

---

## 4. Data-Handling Rules

1. **Never return `_id`** in API responses. Projections in queries: `{"_id": 0}`. Pydantic models exclude it.
2. **UUID strings for all `id` fields.** Generated server-side at create time.
3. **Datetimes** stored as ISO 8601 strings (UTC). Use `datetime.now(timezone.utc)` not `utcnow()`.
4. **Locale fields** are always `dict[str, str]` keyed by ISO 639-1; never store a single-locale string in a content field.
5. **Versioning is content-level.** When NAT 2026 ships, we insert new `curriculum_versions` row + new `subjects/topics/lessons/quizzes/crossrefs` rows referencing the new curriculum_id. We DO NOT mutate existing 2020 content.
6. **Progress is curriculum-tagged.** A user's progress on NAT 2020 remains visible even after switching to NAT 2026 (migrate via `topic_alias_map` when possible).
7. **Append-only `events`.** Don't update events. Aggregations build downstream tables (mastery, gamification snapshots).
8. **Soft-delete users** for GDPR — set `is_deleted=true`, clear PII fields (email replaced by hashed token), preserve aggregate analytics.

---

## 5. Migration Workflow (Curriculum Version Bump)

When NAT 2026 (or any new curriculum) is added:

1. Insert new row in `curriculum_versions` with `status="preview"`.
2. Author/import new `subjects`, `topics`, `lessons`, `quizzes`, `crossrefs` referencing that `curriculum_id`.
3. Author `topic_alias_map` from current active version → new version.
4. QA the new curriculum in preview mode (admin-only).
5. Flip `status="active"`; deprecate the old one (`status="deprecated"`).
6. Users keep their existing `active_curriculum_id` until they opt in (or admin forces migration).
7. On opt-in: server walks user's `progress` rows, applies `topic_alias_map` to surface "you already completed X in the new curriculum" hints.

---

## 6. Sample Seed Sizes (MVP launch target)

| Collection | Approx rows at launch |
|---|---|
| `curriculum_versions` | 1 (NAT 2020) |
| `subjects` | 3 (Math, History, Biology) |
| `topics` | ~50 (≈3 sample topics × 8 grades × 2 subjects average) |
| `lessons` | ~150 (~3 lessons/topic) |
| `quizzes` | ~150 |
| `crossrefs` | ~30 curated curiosity links |
| `locale_strings` | ~400 UI strings × 2 locales = 800 |
