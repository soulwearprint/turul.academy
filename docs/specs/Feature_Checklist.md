# CuriousPath — Feature Checklist

> **Tracking convention:** `[ ]` = not started · `[~]` = in progress · `[x]` = done · `[!]` = blocked
> **Priority:** **P0** = MVP blocker · **P1** = MVP nice-to-have · **P2** = post-MVP
> **Phase:** matches PRD phases 1–6

Update this file in every feature PR. The first build should focus on **all P0 items in Phases 1 & 2**.

---

## Phase 1 — Discovery & Curriculum Foundation

### 1.1 Curriculum Framework (adapter layer)
- [ ] **P0** Define abstract `Curriculum` schema (region-, version-, language-agnostic) — see `Curriculum_Framework_Spec.md`
- [ ] **P0** Define `Subject → Topic → Lesson → Activity` hierarchy
- [ ] **P0** Define `CurriculumVersion` entity (NAT 2020 vs NAT 2026 vs CCSS, etc.)
- [ ] **P0** Topic ID convention that survives curriculum version upgrades (stable, content-hash + curated alias)
- [ ] **P1** Mapping table format for topic migration between versions
- [ ] **P1** Locale strings table (HU, EN minimum)

### 1.2 Hungary NAT 2020 — Content Schema
- [ ] **P0** Subject catalog for NAT 2020 (Grades 5–12) — full list documented (no content yet)
- [ ] **P0** MVP subject seeds: **Math**, **History**, **Biology** — 3 sample topics each
- [ ] **P1** Topic-to-grade mapping for all NAT 2020 subjects
- [ ] **P1** Cross-reference seed (10–20 curated curiosity links across MVP subjects)

### 1.3 Personalization Schema
- [ ] **P0** `LearnerProfile` schema (grade, subjects, learning style, accessibility, gamification preset)
- [ ] **P0** `Progress` schema (lesson/topic/subject/goal granularity)
- [ ] **P0** `MasteryEstimate` schema (per-topic confidence + recency)
- [ ] **P1** `FatigueSignal` schema (session length, switch-rate, abandonment)

### 1.4 Content Sourcing Rules
- [ ] **P0** Whitelist of verified video sources (see `Content_Sourcing_Policy.md`)
- [ ] **P0** Copyright/attribution model
- [ ] **P1** Static illustration fallback library structure

---

## Phase 2 — Core Student Experience (MVP)

### 2.1 Authentication
- [ ] **P0** Email + password signup
- [ ] **P0** JWT session
- [ ] **P0** Password reset flow
- [ ] **P0** Logout
- [ ] **P1** "Remember me" + refresh token
- [ ] **P2** Social login (Google) — deferred

### 2.2 Onboarding
- [ ] **P0** Language picker (HU default, EN toggle)
- [ ] **P0** Grade selector (5–12)
- [ ] **P0** Subject selector (multi-select, min 1, max 5)
- [ ] **P0** Learning-style 6-Q quiz (saves 1–2 preferred modes)
- [ ] **P0** Accessibility prefs (font, text size, contrast)
- [ ] **P0** Gamification preset choice ("light" default, "full" opt-in, "minimal" toggle)
- [ ] **P1** Optional goal-setting ("finish Math Grade 6 by June")
- [ ] **P1** Onboarding skip + revisit-in-settings

### 2.3 Today / Home Screen
- [ ] **P0** Today's recommended lesson card (1 primary CTA)
- [ ] **P0** Streak indicator
- [ ] **P0** Side-quest banner (1 active at a time)
- [ ] **P0** Quick-resume to last lesson
- [ ] **P1** XP progress bar
- [ ] **P1** Weekly summary tile

### 2.4 Subject Navigation
- [ ] **P0** Subject list (cards)
- [ ] **P0** Subject detail view: topic tree + progress per topic
- [ ] **P0** Topic detail view: lesson list + status
- [ ] **P1** Subject-level mastery chart

### 2.5 Lesson Player
- [ ] **P0** Card-based layout (1 concept/card, ≤80 words/card text mode)
- [ ] **P0** Mode switcher: **Text**, **Story**, **Fact-list**, **Visual** (curated only in MVP), **Quiz**, **Audio** (browser TTS)
- [ ] **P0** Auto-save position on every card transition
- [ ] **P0** "I'm stuck" button → presents same card in alternate mode (manual switch in MVP)
- [ ] **P0** End-of-lesson 3–5 Q quiz
- [ ] **P0** Lesson completion event → progress + XP + (optional) badge
- [ ] **P1** Lesson bookmark
- [ ] **P1** Lesson notes (free text, local)

### 2.6 Progress & Save State
- [ ] **P0** Save resume position across devices (server-side)
- [ ] **P0** Lesson completion %
- [ ] **P0** Topic completion %
- [ ] **P0** Subject completion %
- [ ] **P0** Year/goal completion %
- [ ] **P1** Activity history feed

### 2.7 Gamification — Default Light Loop
- [ ] **P0** Daily streak counter (resets at student-local midnight)
- [ ] **P0** Check-in reward (small XP) for first activity each day
- [ ] **P0** Lesson completion badges
- [ ] **P0** Topic completion badge
- [ ] **P0** Subject milestone badge
- [ ] **P0** Side-quest engine (1 active, examples: "do a quiz today", "review 1 topic")
- [ ] **P0** XP & level system
- [ ] **P0** Progressive unlock tiers — **cosmetic only** (see `Gamification_Spec.md`)
  - [ ] **P0** Tier 1: static profile picture (default)
  - [ ] **P1** Tier 2: animated avatar (unlock at XP gate)
  - [ ] **P1** Tier 3: theme variants
  - [ ] **P2** Tier 4: collectible cards
- [ ] **P1** Full gamer mode opt-in (richer animations, leaderboards-vs-self, achievement screens)
- [ ] **P0** **Hard rule enforced in code:** learning-style modes, accessibility, lesson access NEVER gated by XP/level

### 2.8 Personalization
- [ ] **P0** Theme toggle (light/dark)
- [ ] **P0** Font selector (default / dyslexia-friendly)
- [ ] **P0** Text size (S/M/L/XL)
- [ ] **P0** Audio playback toggle
- [ ] **P0** Default explanation mode preference
- [ ] **P1** Pacing preference (short sprints vs longer sessions)
- [ ] **P1** Reward style preference (visual celebration intensity)

### 2.9 Settings & Profile
- [ ] **P0** Edit grade
- [ ] **P0** Edit subjects
- [ ] **P0** Edit learning style
- [ ] **P0** Edit accessibility prefs
- [ ] **P0** Change password
- [ ] **P0** Logout / delete account (GDPR baseline)

### 2.10 Verified Media Layer
- [ ] **P0** Whitelisted video embed component (YouTube /education channels, MTVA, etc.)
- [ ] **P0** Static curated illustration fallback
- [ ] **P1** Video attribution display + source link
- [ ] **P2** AI-generated visuals (deferred)

---

## Phase 3 — Adaptive Learning Layer (AI deferred)

> ⚠️ Phase 3 items requiring AI are documented but **deferred** until cost/strategy in `Token_Efficiency_Strategy.md` is approved.

- [ ] **P1** "Stuck mode" intelligent variant suggestion (rule-based first, AI later)
- [ ] **P2** AI lesson rephrasing per learner style
- [ ] **P2** AI-generated anecdote/fact enrichment
- [ ] **P2** AI quiz question generation
- [ ] **P1** Difficulty pacing (rule-based: recent quiz accuracy → next quiz difficulty)
- [ ] **P1** Encouragement cue system (rule-based microcopy)

---

## Phase 4 — Curiosity & Cross-Subject Engine

- [ ] **P0 (MVP-lite)** Curated curiosity links per topic (10–20 seeded across MVP subjects)
- [ ] **P1** Topic relationship graph data model
- [ ] **P1** "Explore" branch UI — view linked node without losing syllabus position
- [ ] **P1** Return-to-syllabus breadcrumb
- [ ] **P2** Auto-generated relationship suggestions (AI, deferred)
- [ ] **P2** People / Events / Inventions / Works mini-cards
- [ ] **P2** Timeline view of related historical figures across subjects

---

## Phase 5 — Exam Prep & Mastery Tracking

### 5.1 Mastery Engine
- [ ] **P0 (MVP-lite)** Per-topic mastery estimate (simple weighted average of quiz scores)
- [ ] **P1** Recency decay
- [ ] **P1** Weak-area surfacing on subject dashboard
- [ ] **P2** Spaced-repetition scheduler

### 5.2 Exam Prep Module
- [ ] **P0** Per-subject revision pack (worked-topic summaries)
- [ ] **P0** Per-subject practice quiz set
- [ ] **P0** Subject switcher with auto-save
- [ ] **P1** Timed mock mode
- [ ] **P1** Weak-area targeted practice
- [ ] **P2** Matura-specific exam simulator
- [ ] **P2** Readiness score & charts

---

## Phase 6 — Parent/Teacher Visibility & Polish

- [ ] **P2** Parent account type + linkage
- [ ] **P2** Teacher account type
- [ ] **P2** Parent dashboard (progress, streak, weak areas)
- [ ] **P2** Notifications (in-app + optional email — see `Content_Sourcing_Policy.md` for email vendor)
- [ ] **P2** Reminder system (study-time scheduling)
- [ ] **P2** Theme expansion / brand polish
- [ ] **P2** Avatar editor depth
- [ ] **P2** Voice tutor / conversational assistant
- [ ] **P2** Offline study packs (PWA → service worker)
- [ ] **P2** Handwriting / worksheet upload (OCR + feedback)
- [ ] **P2** Burnout detection & adaptive scheduling

---

## Cross-Cutting Engineering

### CC.1 Backend
- [ ] **P0** FastAPI scaffold with `/api` prefix on every route
- [ ] **P0** MongoDB connection via `MONGO_URL` env
- [ ] **P0** JWT auth middleware
- [ ] **P0** Pydantic response models (exclude `_id`)
- [ ] **P0** CORS config

### CC.2 Frontend
- [ ] **P0** React app via existing template
- [ ] **P0** Mobile-first responsive layout
- [ ] **P0** `REACT_APP_BACKEND_URL` usage everywhere
- [ ] **P0** Theme provider (light/dark, font swap, text size)
- [ ] **P0** Lesson player route + state machine
- [ ] **P0** Toast/notification via `sonner`
- [ ] **P0** PWA manifest (Phase 6 wires service worker)

### CC.3 Testing & Quality
- [ ] **P0** Unit tests for progress engine (math, not UI)
- [ ] **P0** Backend integration tests for auth + lesson endpoints
- [ ] **P0** Frontend e2e smoke (onboarding → 1 lesson → complete)
- [ ] **P0** Lint clean (ruff + eslint)
- [ ] **P0** `data-testid` on every interactive element

### CC.4 Compliance / Trust
- [ ] **P0** GDPR-friendly data model (delete-account flow)
- [ ] **P0** Minor user data policy (no contact harvesting)
- [ ] **P0** Terms / Privacy stub
- [ ] **P1** Cookie policy + consent banner (EU)

### CC.5 Observability
- [ ] **P1** Basic event logging (lesson start, complete, mode switch)
- [ ] **P1** Error log aggregation
- [ ] **P2** Funnel analytics
- [ ] **P2** A/B test framework

---

## Definition of Done (Per Feature)

A feature is **done** only when:
1. Code merged.
2. `data-testid` added on every interactive element.
3. Auto-save behavior verified if it touches progress.
4. Translated strings present for HU + EN.
5. Mobile viewport tested at 360×640.
6. Accessibility check: keyboard nav + dyslexia font compatibility.
7. Tests pass; testing subagent green.
8. Checklist item in this file flipped to `[x]`.
