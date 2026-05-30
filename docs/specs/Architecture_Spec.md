# CuriousPath — Architecture Specification

**Status:** Specification — no implementation yet.
**Stack baseline:** React (existing template) + FastAPI + MongoDB.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       MOBILE-FIRST WEB CLIENT                    │
│                React (existing /app/frontend template)            │
│                                                                  │
│  ┌──────────┐  ┌────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Onboard- │  │ Lesson     │  │ Progress &   │  │ Settings & │ │
│  │ ing flow │  │ Player     │  │ Gamification │  │ Profile    │ │
│  └────┬─────┘  └─────┬──────┘  └──────┬───────┘  └────────────┘ │
│       └──────────────┴────────────────┴────────────────────────┐│
│                                                                ││
│         API client (REACT_APP_BACKEND_URL + /api)              ││
└────────────────────────────────────┬───────────────────────────┘│
                                     │ HTTPS                       
┌────────────────────────────────────▼───────────────────────────┐
│                       FASTAPI BACKEND                            │
│                /app/backend/server.py (+ modules)                │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────┐ │
│  │ Auth        │ │ Curriculum  │ │ Lesson     │ │ Progress   │ │
│  │ module      │ │ module      │ │ module     │ │ module     │ │
│  └─────────────┘ └─────────────┘ └────────────┘ └────────────┘ │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────┐ │
│  │ Gamif.      │ │ Crossref    │ │ Mastery /  │ │ Personal-  │ │
│  │ engine      │ │ engine      │ │ Exam prep  │ │ ization    │ │
│  └─────────────┘ └─────────────┘ └────────────┘ └────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Future (Phase 3+): AI Personalization Service           │  │
│  │  - lesson rephrase  - quiz gen  - stuck-mode adaptive    │  │
│  │  - DEFERRED: see Token_Efficiency_Strategy.md            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬───────────────────────────┘
                                     │
                              ┌──────▼──────┐
                              │   MongoDB   │
                              │ (MONGO_URL) │
                              └─────────────┘
```

---

## 2. System Modules

### 2.1 Auth Module
- Email/password signup & login
- Password hash via bcrypt (NOT in .env-expanded form — see auth playbook before coding)
- JWT access tokens (short-lived) + refresh token (P1)
- Account-deletion endpoint for GDPR
- **No social login in MVP**

### 2.2 Curriculum Module
- Loads & serves the **active curriculum version** for a user
- Reads from versioned curriculum collections (see `Curriculum_Framework_Spec.md`)
- Supports atomic switch when NAT 2026 or another locale ships
- Resolves topic IDs through alias/mapping tables for backwards compatibility

### 2.3 Lesson Module
- Returns lesson card sequence + available modes
- Records play events (start, card-view, mode-switch, complete)
- Multi-mode response: same lesson, multiple content variants in one payload (saves API roundtrips on mode switch)

### 2.4 Progress Module
- Records and queries `Progress` for lesson/topic/subject/goal
- Resume-anywhere (stores `last_position` per lesson)
- Returns aggregated dashboards

### 2.5 Gamification Engine
- Pure-function reward calculation given an event
- Manages: streaks, XP, level, badges, side quests, cosmetic unlock tier
- **Cannot gate learning-style modes or lesson access** (enforced at service layer; rejects any such gating request)

### 2.6 Cross-Reference Engine
- Returns curated curiosity links for a topic
- Phase 4: also serves graph traversal (k-hop neighbors)

### 2.7 Mastery / Exam Prep Module
- MVP: simple weighted-mean per-topic mastery from quiz scores
- Surfaces weak topics per subject
- Exam pack assembly: revision summary + quiz set + (P1) timed mock

### 2.8 Personalization Module
- Stores learner prefs (mode, theme, font, size, audio, pacing, gamification preset)
- Read on every lesson fetch; influences default mode selection

### 2.9 AI Personalization Service (DEFERRED, Phase 3+)
- See `Token_Efficiency_Strategy.md`
- Integration via `integration_playbook_expert_v2` when activated
- Cached, on-demand-only rephrasing

---

## 3. Tech Stack Rationale

| Layer | Choice | Why |
|---|---|---|
| Frontend | React (template provided) | Rich interactive lesson player, dashboards, fits emergent template |
| Frontend styling | Tailwind + shadcn/ui (provided) | Consistent components, accessible, fast |
| Backend | FastAPI | Async, typed, good for content APIs + future AI orchestration |
| DB | MongoDB | Nested curriculum content, flexible personalization, graph-friendly for crossrefs |
| Auth | JWT (bcrypt) | Stateless, mobile-friendly, simple |
| Caching | (Phase 3) In-process LRU + DB-side cache collection | Critical for AI token costs |
| Storage | (Phase 6) Object storage (emergent) | Lesson assets, avatars |
| i18n | JSON locale files (HU/EN) | Lightweight, version-controlled |

---

## 4. API Surface (MVP)

All routes prefixed with `/api`. Authenticated unless marked **(public)**.

### Auth
| Method | Route | Purpose |
|---|---|---|
| POST | `/api/auth/signup` | (public) email/password signup |
| POST | `/api/auth/login` | (public) returns JWT |
| POST | `/api/auth/logout` | invalidate session |
| POST | `/api/auth/password-reset/request` | (public) send reset token |
| POST | `/api/auth/password-reset/confirm` | (public) confirm new password |
| DELETE | `/api/auth/account` | GDPR delete |

### Profile / Personalization
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/me` | profile + prefs |
| PATCH | `/api/me/profile` | update grade, subjects, goals |
| PATCH | `/api/me/preferences` | update theme/font/size/audio/mode/gamification preset |

### Curriculum
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/curriculum/active` | returns active curriculum metadata for user |
| GET | `/api/curriculum/subjects?grade=` | subjects available for grade |
| GET | `/api/curriculum/subjects/{subject_id}/topics` | topic tree |
| GET | `/api/curriculum/topics/{topic_id}` | topic detail |

### Lesson
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/lessons/{lesson_id}` | full lesson incl. all available modes |
| POST | `/api/lessons/{lesson_id}/events` | play events (start, card-view, mode-switch, complete) |
| POST | `/api/lessons/{lesson_id}/quiz/submit` | submit quiz answers |

### Progress
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/progress/summary` | overall dashboard |
| GET | `/api/progress/subjects/{subject_id}` | subject-level breakdown |
| GET | `/api/progress/topics/{topic_id}` | topic-level breakdown |
| GET | `/api/progress/resume` | next-up suggestion |

### Gamification
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/gamification/state` | XP, level, badges, streak, unlock tier |
| GET | `/api/gamification/side-quest` | current active side quest |
| POST | `/api/gamification/check-in` | daily check-in event |

### Cross-references
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/crossref/topic/{topic_id}` | curated links for topic |
| GET | `/api/crossref/explore/{node_id}` | (Phase 4) k-hop traversal |

### Exam Prep
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/exam-prep/{subject_id}` | pack: weak areas + revision + practice |
| POST | `/api/exam-prep/{subject_id}/mock/start` | (P1) timed mock |

### Health / Meta
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| GET | `/api/locales` | available languages |

---

## 5. State Management (Frontend)

- **Global** (React context): auth, user profile, active curriculum, theme/font/size/audio preferences, current XP/streak
- **Route-scoped:** current lesson state machine (idle / playing / quiz / complete)
- **No Redux.** Context + local component state. Server is source of truth; client refetches on critical events.
- **Offline:** not in MVP. Avoid local-only writes — every mutation goes to API.

---

## 6. Non-Functional Requirements

| Concern | Target |
|---|---|
| Mobile reading at 360×640 | First-class — every screen tested at this width |
| API p95 latency | <400ms for lesson fetch, <250ms for progress writes |
| Lesson asset size | <300KB per lesson (text + light visuals) |
| Cold-start to first paint | <2s on mid-tier 4G |
| Accessibility | WCAG 2.1 AA target; dyslexia font; keyboard nav |
| i18n | HU + EN at launch; locale string table; no string literals in UI |
| Privacy | GDPR-baseline; delete-account works; no third-party trackers in MVP |
| Curriculum swap | A user's `curriculum_version_id` swap should be a single field update without progress loss |

---

## 7. Key Architectural Rules

1. **No backend route without `/api` prefix.**
2. **No frontend fetch without `process.env.REACT_APP_BACKEND_URL`.**
3. **No `_id` in API responses** — exclude via Pydantic models.
4. **No business logic in route handlers** — handlers call service modules.
5. **Gamification cannot gate learning.** Enforced as a function-level guard in the gamification engine.
6. **Curriculum content is versioned, not mutated.** New version = new document set + mapping table.
7. **AI not in MVP.** Any AI-flavored endpoint must be feature-flagged off and integration-playbook-gated before activation.

---

## 8. Deployment / Environment

- Backend on port 8001 (supervisor-managed), bound to 0.0.0.0
- Frontend on port 3000 (supervisor-managed)
- All URLs/credentials via `.env` — never hardcoded
- MongoDB via `MONGO_URL` + `DB_NAME` (existing)
- Hot reload assumed; restart only on .env/dependency changes
