# CuriousPath — Gamification Specification

> **Inviolable Rule (architectural):**
> Gamification may unlock or scale **cosmetic** features (avatars, themes, decorations, animation intensity, side quest variety).
> Gamification **must never gate**: learning-style modes, accessibility settings, lesson access, exam prep, or any content. Learning is uncapped from day 1.

This rule is enforced in the **gamification engine service** at the function-call level (any attempt to gate a learning capability is rejected and logged).

---

## 1. Philosophy

Gamification serves **motivation and consistency**, not engagement-for-its-own-sake. The system must work invisibly for the academic learner (Bence) and visibly for the gamer learner (Levente). Defaults skew restrained; depth is opt-in.

**Three rewards drive consistency:**
1. **Visibility of progress** (streaks, XP, badges, level)
2. **Visible wins on completion** (animations sized to preset)
3. **Cosmetic self-expression** (avatars, themes — unlocked progressively)

---

## 2. Presets

A new student picks (or accepts default) one of three presets during onboarding; switchable anytime in settings.

| Preset | When recommended | Visual intensity | XP/Level visible? | Streak prominence | Side quests? | Animations |
|---|---|---|---|---|---|---|
| `minimal` | Older students, anti-gaming | Very low | Hidden by default | Subtle | Off | None |
| `light` *(default)* | New users; most learners | Restrained | Yes, small | Visible, not loud | Yes, 1 at a time | Subtle (200–400ms) |
| `full` | Self-identified gamers / motivation-by-rewards | Rich | Yes, prominent | Loud, celebratory | Yes, 1–2 at a time | Rich (with particle effects) |

**Important:** The preset only changes presentation. The **underlying gamification engine state is identical** — all users earn XP, badges, streaks. Just the visibility changes. This means a user can flip from `minimal` to `full` and suddenly see all the rewards they had quietly accumulated.

---

## 3. The Default Light Loop (most students will see this)

### 3.1 Daily check-in
- First learning action of the day → small XP reward (`+5 XP`)
- Updates `streak_count` if action is on consecutive day
- Streak does **not** "punish" missed days harshly — see 3.3.

### 3.2 Lesson loop
- Start a lesson → no reward (no friction either)
- Complete a card → no per-card reward (avoid over-stimulation)
- Mode switch → no reward (mode switching is normal, not a feat)
- Complete a lesson → `+10–25 XP` (proportional to lesson length × quiz performance)
- Complete topic → `+50 XP + topic badge`
- Complete subject for a grade → `+200 XP + subject milestone badge`

### 3.3 Streaks — soft consistency
- Daily check-in updates streak.
- Missed a day? Streak shows "1-day grace" indicator — 1 free recovery day per week.
- Missed 2+ days? Streak resets to 0 but **longest streak preserved as a badge**.
- No "shame" UX. Reset is informational ("New streak begins today — let's go!").

### 3.4 Side quests
- 1 active side quest at any time (`light` preset). Refreshes daily or on completion.
- Examples:
  - "Do 1 quiz today" (+15 XP)
  - "Review a topic you've already started" (+10 XP)
  - "Try a new explanation mode in any lesson" (+10 XP) — encourages mode discovery
  - "Explore a curiosity link" (+10 XP) — encourages curiosity branch
- Quest pool is curated, balanced across study habits + curiosity + practice.
- Quests are skippable (no penalty); a refresh button is available once per day.

### 3.5 Badges
- Granted on milestones (lesson, topic, subject, grade-year, exam-prep).
- Stored under `gamification_state.badges`.
- Tiered (bronze/silver/gold) for repeatable badges (e.g., "Math Module Complete").
- Badge gallery viewable in profile.

### 3.6 XP & Levels
- Levels scale logarithmically — early levels easy (encouragement), later levels gradual.
- Suggested curve: Level N requires `100 * N^1.5` XP.
- Levels exist primarily to drive **cosmetic unlock tiers** (next section).

---

## 4. Progressive Cosmetic Unlock Tiers

The student's customization options expand as they level up. **This is the only place gamification gates anything.**

| Tier | Unlock at | What unlocks | Why |
|---|---|---|---|
| **T1 — Starter** | Default | Static profile picture (choose from preset set of 8), default theme, default avatar style | Frictionless start |
| **T2 — Explorer** | Level 5 (~5 lessons completed) | Animated avatar option (3 variants), 2 extra themes (e.g., warm/cool), expanded profile picture set | Quick visible reward |
| **T3 — Scholar** | Level 12 | Background patterns, badge frames, secondary theme palette | Mid-term motivation |
| **T4 — Curator** | Level 25 | Collectible decorations (per-subject keepsakes earned from topic mastery), custom name color | Long-term goal |
| **T5 — Voyager** | Level 50 | Rare seasonal/limited cosmetics, profile showcase area | Aspirational |

**Notes:**
- All tiers above T1 are purely cosmetic.
- Tiers do **not** require purchase. No in-app payments at MVP.
- "Full gamer" preset users get the same tiers but with more theatrical unlock ceremonies.
- "Minimal" preset users still earn unlock tiers silently; can opt to display them later.

---

## 5. Reward Distribution Examples (calibration)

| Event | Light preset XP | Full preset XP | Notes |
|---|---|---|---|
| Daily check-in | 5 | 5 | Identical reward; only animation differs |
| Lesson complete (typical) | 15 | 15 | |
| Lesson complete + 100% quiz | 25 | 25 | |
| Topic complete | 50 | 50 + topic badge animation | |
| Subject grade-year milestone | 200 | 200 + ceremony | |
| Side quest complete (small) | 10 | 10 | |
| Side quest complete (large) | 25 | 25 | |
| Exam prep mock complete | 40 | 40 | |
| Curiosity link explored | 5 | 5 | One-time per link |
| Mode switch | 0 | 0 | Never rewarded (avoid gaming the loop) |
| "I'm stuck" used | 0 | 0 | Never penalized either |

---

## 6. Adaptive Difficulty in Quizzes (rule-based, MVP)

Quiz difficulty adapts per topic based on recent quiz performance:

```
if last_3_quizzes_accuracy >= 0.8:
    next_quiz.difficulty = min(5, current + 1)
elif last_3_quizzes_accuracy < 0.5:
    next_quiz.difficulty = max(1, current - 1)
else:
    keep same
```

- Quiz items are stored with `difficulty` (1–5).
- Selection pulls items at the current target difficulty.
- This is independent of gamification — it's pedagogical.
- AI-based adaptive generation is Phase 3+ (deferred).

---

## 7. Anti-Fatigue Cues (rule-based)

Triggered by event-log signals — not by AI in MVP.

| Signal | Cue |
|---|---|
| Session > 25 min continuous | Gentle "Take a 2-min break?" prompt (dismissable) |
| 3+ wrong quiz answers in a row | "Want to switch mode?" suggestion |
| Lesson abandoned mid-way | On next session, surface "Resume where you left off" prominently |
| Streak about to break (24h+ since last activity) | Friendly reminder push (in-app banner; email if opted in) |
| Several mode switches in one lesson | No intervention — switching is desired behavior |

---

## 8. What Gamification **Does Not Do**

This is the binding negative spec. Violations are bugs.

- ❌ Does **not** lock any lesson behind XP/level
- ❌ Does **not** lock any explanation mode (text/story/visual/quiz/audio/fact-list) behind XP
- ❌ Does **not** lock accessibility features behind XP
- ❌ Does **not** lock exam prep behind XP
- ❌ Does **not** show leaderboards against other users (only self-leaderboards in full preset; comparing to your own past)
- ❌ Does **not** show streak loss with negative/shaming language
- ❌ Does **not** apply time pressure to learning (timed practice is opt-in only)
- ❌ Does **not** notify outside the app without explicit opt-in
- ❌ Does **not** include any in-app purchases at MVP

---

## 9. Engineering Guardrail (Service-Level)

The gamification engine exposes only these mutations:
- `award_xp(user_id, amount, reason_key)`
- `mark_streak_check_in(user_id)`
- `award_badge(user_id, badge_key, tier=1)`
- `update_unlock_tier(user_id)`
- `assign_side_quest(user_id, quest_key)`

There is **no** `lock_mode()`, `lock_lesson()`, `lock_feature()` function. Any attempt to add one fails code review.

---

## 10. Open Items

- Badge artwork direction (defer to post-MVP)
- Avatar art style (defer to post-MVP)
- Seasonal cosmetic cadence (Phase 6)
- Whether to introduce a private "study buddy" peer feature (out of scope MVP)
