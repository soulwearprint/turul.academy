# CuriousPath — Product Requirements Document (PRD)

**Version:** 0.1 (spec phase)
**Status:** Pre-build — design & documentation only
**Last updated:** 2026-02

---

## 1. Problem Statement

School-age students disengage from formal learning due to one-size-fits-all explanations, study fatigue, weak context for memory, and rigid "right answer or wrong" feedback loops. Existing study apps either over-gamify (distraction) or under-explain (dry). Hungarian students preparing for matura exams also lack tooling tailored to NAT-aligned subject paths.

CuriousPath solves this by making each curriculum topic an **adaptive learning journey** — same content, multiple explanation modes, verified media, cross-subject curiosity links, and motivation loops sized to the learner.

---

## 2. Vision

> "Make required schoolwork the most interesting place a curious 12-year-old can spend 15 minutes."

A student opens the app, sees today's recommended path, finishes a short lesson in their preferred explanation style, branches into one curiosity link if it sparks them, earns a small visible reward, and leaves on a "win." Repeat daily. Confidence grows. Exam readiness grows. Boredom shrinks.

---

## 3. Target Users

### Primary: Students, Grades 5–12 (ages ~10–18)
| Persona | Description | Core need |
|---|---|---|
| **Mira (12, Grade 6)** | Bright but loses focus on long readings; loves stories | Lesson modes that match how she thinks; quick wins |
| **Bence (15, Grade 9)** | Capable academic kid, dislikes "kiddie" gamification | Lightweight progress tracking, depth on demand |
| **Zsófi (17, Grade 11)** | Anxious about matura; uneven across subjects | Subject-targeted exam prep, weak-area surfacing |
| **Levente (13, Grade 7)** | Plays games daily, motivated by XP/achievements | Full gamification opt-in; collectible badges, streaks |

### Secondary (Post-MVP)
- Parents/guardians (progress visibility, Phase 6)
- Teachers (assignment & class view, Future)

### Out of scope (v1)
- Adult learners
- Students under Grade 5
- Special-education-specific cognitive support (basic accessibility only)

---

## 4. Goals & Non-Goals

### Goals (MVP)
1. Deliver curriculum-anchored lessons (Hungarian NAT 2020, 2–3 subjects to start) for Grades 5–12.
2. Let students switch explanation mode mid-lesson without losing position.
3. Track progress at lesson/topic/subject/yearly-goal granularity, save across devices.
4. Provide a default gamification loop that motivates without distracting.
5. Provide a basic exam prep mode (subject-specific revision + practice).
6. Ship without AI; structure data so AI can plug in later without schema rewrites.

### Non-Goals (v1)
- Generating new lesson content with AI
- Multi-region simultaneous curriculum support (architecture supports it; UX surfaces one curriculum at a time)
- Native mobile apps
- Social/competitive features beyond personal streaks

---

## 5. MVP Scope (Phases 1–2)

| Module | MVP Content |
|---|---|
| Onboarding | Grade, subjects (pick 2–3), goals, learning-style quiz, accessibility prefs |
| Curriculum catalog | Hungarian NAT 2020 — pilot subjects: **Mathematics**, **History**, **Biology** (Grade-5–12 coverage curated incrementally) |
| Lesson player | Card-based, multi-mode (text / story / fact-list / quiz / visual), one primary action per screen |
| Progress | Lesson → topic → subject → year, with resume-anywhere |
| Gamification (default light) | Daily streak, completion badges, side-quest banner, XP bar, cosmetic unlock tiers |
| Exam prep (basic) | Per-subject revision pack: worked topics summary + quiz set + weak-area highlight |
| Cross-references | Static curated "Curiosity links" between topics (people, inventions, related subjects) |
| Personalization | Theme (light/dark), font (default/dyslexia), text size, audio playback toggle (where audio exists), explanation-mode preference |
| Verified media | Curated video embed (whitelisted sources) **OR** curated static illustration fallback |
| Auth | Email + password, JWT (no social login in MVP) |

---

## 6. Full Product Phases

| Phase | Theme | Status |
|---|---|---|
| **1** | Discovery & curriculum foundation | spec'd |
| **2** | Core student experience | spec'd |
| **3** | Adaptive learning layer (AI rephrase, stuck mode) | spec'd, deferred AI |
| **4** | Curiosity & cross-subject engine | spec'd (curated edges first) |
| **5** | Exam prep & mastery tracking (full) | spec'd |
| **6** | Parent/teacher visibility & polish | future |

See `Feature_Checklist.md` for itemized tasks.

---

## 7. User Flows

### 7.1 First-time onboarding
1. Land → pick language (HU default, EN available) → sign up (email/password)
2. Select grade → pick subjects (min 1, max 5 in MVP)
3. Learning-style quick quiz (6 questions, picks 1–2 preferred modes; **changeable anytime**)
4. Accessibility prefs (font, contrast, text size)
5. Optional goal set ("finish Math Grade 6 by June")
6. Land on **Today** screen with 1 recommended lesson

### 7.2 Daily learning loop
1. Open app → Today screen → 1 recommended lesson (≤10 min) + streak status + 1 side-quest
2. Tap lesson → multi-card lesson player
3. Reach end card → quiz (3–5 Q) → earn XP + badge (if applicable)
4. Lesson complete → "Up next" suggestion + 1 curiosity link
5. Return to Today, see updated streak

### 7.3 Stuck-mode loop (Phase 3, MVP-lite version: manual switch)
- "I'm stuck" button on any lesson card → presents same content in a different mode (e.g., visual instead of text). In MVP, this is a manual mode switch; in Phase 3 it becomes AI-adaptive.

### 7.4 Exam prep entry
1. Subject dashboard → "Exam prep" tab → choose subject (auto-saves progress on switch)
2. View weak-area summary (computed from quiz history)
3. Pick: Revision read / Practice quiz / Timed mock
4. Result feeds back into mastery estimate

---

## 8. Success Metrics

### North Star
**Weekly Active Learners completing ≥3 lessons/week** (proxy for habit formation)

### MVP KPIs
| Metric | Target (3 months post-launch) |
|---|---|
| Day-7 retention | ≥35% |
| Avg session length | 8–14 min (sweet spot — not too short, not fatigued) |
| Lessons completed / WAL | ≥4 |
| Mode-switch rate | ≥20% of users (proves multi-mode value) |
| Streak ≥7 days | ≥15% of MAU |
| Self-reported "fun" score | ≥4/5 |
| Avg per-user inference cost when AI ships | Stay under defined budget (see `Token_Efficiency_Strategy.md`) |

---

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Over-gamification distracts from learning | Med | High | Gamification limited to cosmetic unlocks; learning content never gated; default mode is light |
| Curriculum drift (NAT 2026 release) | High | High | Adapter pattern (`Curriculum_Framework_Spec.md`) — versioned curriculum, atomic swap, mapping table for topic migration |
| Locked into Hungary | Med | High | Same adapter pattern supports CCSS/UK/AU/JP/CA out-of-box; locale-agnostic IDs |
| Content authoring becomes bottleneck | High | Med | Author once in normalized schema; mode variants stored as separate fields, not separate lessons |
| Copyright/trust on embedded video | Med | High | Whitelist-only sources (state TV, public uni, .edu); see `Content_Sourcing_Policy.md` |
| AI cost runaway when enabled | Med | High | On-demand-only rephrase, aggressive cache, model tiering (see `Token_Efficiency_Strategy.md`) |
| Mobile reading fatigue | Med | High | Card-based UI, max ~80 words/card, audio toggle |
| Anti-gamer kids find badges patronizing | Med | Med | Default loop is restrained; full gamer mode is opt-in only |

---

## 10. Open Questions (Resolved)

| Question | Decision |
|---|---|
| Age range MVP? | Grades 5–12 |
| Curriculum? | Hungary, NAT 2020 (NAT 2026 supported via adapter when released) |
| Web vs mobile? | Mobile-first responsive web |
| Parents/teachers in v1? | Students only |
| AI-generated video? | No. Curated content first |
| Gamification depth? | Customizable; default = light; full gamer mode opt-in |
| Exam prep target? | Subject-based prep paths, switchable anytime |

## 11. Open Questions (Still Open)

- Which 2–3 subjects pilot first? *Proposal: Mathematics, History, Biology (broad audience, mix of analytical/narrative/visual).*
- Should onboarding offer EN as well as HU for MVP, or HU-only? *Proposal: HU primary, EN as toggle.*
- Audio narration: pre-recorded voice actors, or browser TTS in MVP? *Proposal: browser TTS in MVP, voice actors Phase 6.*
- Acceptable matura-prep authoring volume per launch (full subject? subset of topics?) — needs Content team input.

---

## 12. Glossary

- **NAT** — *Nemzeti Alaptanterv*, Hungary's National Core Curriculum.
- **Kerettanterv** — Framework curriculum derived from NAT.
- **Matura** — Hungarian school-leaving exam (Grade 12).
- **Mode** — A presentation style for the same lesson content (text, story, visual, quiz, audio, fact-list).
- **Curiosity link** — A curated cross-reference from one topic to a related concept, person, or work.
- **Mastery estimate** — Per-topic confidence score derived from quiz performance + recency.
