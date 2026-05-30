# CuriousPath — UI / UX Guidelines

**Primary device target:** mobile (360×640 baseline, scaling up gracefully).
**Branding & visual identity polish:** deferred until after MVP validation. This document covers structural/UX rules and accessibility — not final look-and-feel.

---

## 1. Core Principles

1. **One primary action per screen.** Cognitive load is the enemy.
2. **Card-based content.** Lessons, dashboards, settings — all cards. Scrollable, swipeable on mobile.
3. **Readability over density.** Generous whitespace, short paragraphs, controlled line length (~45–70 chars).
4. **Visible progress everywhere.** Bars, percentages, "next step" indicators — but understated, never noisy.
5. **Respect the learner's settings.** If they picked dyslexia font, every screen uses it. If they picked dark theme, no white flash transitions.
6. **Animations are short and purposeful.** 150–300ms; never block input; never on every interaction.
7. **Same content, multiple skins.** Mode switcher persists across cards; switching is instant, no full reload.
8. **Mobile-first means thumb-first.** Primary actions in the lower 60% of the screen.

---

## 2. Mobile-First Layout Rules

### 2.1 Breakpoints
| Name | Width | Layout |
|---|---|---|
| `mobile` | <640px | Single column, full-width cards, bottom navigation |
| `tablet` | 640–1024px | Single column with wider gutters; optional side rail at >900px |
| `desktop` | >1024px | Two-column where useful (lesson + cross-refs sidebar); never required |

### 2.2 Navigation
- **Mobile:** Bottom tab bar (Home / Subjects / Progress / Profile). Max 4 tabs.
- **Tablet/Desktop:** Same tab bar at top OR persistent left rail.
- Lesson player **hides nav** to maximize content space; close button top-left, mode-switcher top-right.

### 2.3 Touch Targets
- Minimum 44×44px tap target for all interactive elements.
- 8px minimum spacing between adjacent tappable elements.

### 2.4 Safe Areas
- Respect device safe areas (notches, home indicator). Use CSS `env(safe-area-inset-*)`.

---

## 3. Lesson Player UX

### 3.1 Anatomy of a lesson screen
```
┌──────────────────────────────┐
│ ✕ close          [mode ▾]    │   ← top bar (auto-hides on scroll on tablet)
├──────────────────────────────┤
│                              │
│   [Card content area]        │   ← swipe left/right for prev/next card
│                              │
│   ────────                   │
│   • • ○ ○ ○                  │   ← card progress dots
│                              │
├──────────────────────────────┤
│                              │
│  [ Primary action button ]   │   ← "Continue" / "Submit" / "I'm stuck"
│                              │
└──────────────────────────────┘
```

### 3.2 Rules
- **One concept per card.** Text cards: ≤80 words. Fact-list cards: ≤7 items.
- **Swipe to advance** + visible "Continue" button (both work).
- **Mode switcher pinned** at top-right; one tap reveals dropdown with all available modes for this lesson; selection swaps content without losing card position.
- **"I'm stuck" button** appears on every card; tapping it cycles to the next available mode (MVP behavior) and shows a brief micro-toast: "Switched to Story mode — same content, different angle."
- **Quiz cards** look distinct (subtle border accent), keyboard-friendly, immediate visual feedback (no delayed reveal).

### 3.3 Auto-save
- Position saves on every card transition (debounced ~500ms).
- Resume on next visit lands directly on last card, in last-used mode.

---

## 4. Visual Hierarchy

### 4.1 Type scale (binding)
| Token | Mobile | Tablet+ | Use |
|---|---|---|---|
| `h1` | `text-3xl` (28–30px) | `text-4xl` (36px) | Screen titles, lesson title |
| `h2` | `text-xl` (20px) | `text-2xl` (24px) | Card headings, section headings |
| `h3` | `text-lg` (18px) | `text-lg` (18px) | Sub-headings |
| `body` | `text-base` (16px) | `text-base` (16px) | Default reading text |
| `caption` | `text-sm` (14px) | `text-sm` (14px) | Metadata, hints |
| `micro` | `text-xs` (12px) | `text-xs` (12px) | Timestamps, footer notes |

User's text-size preference multiplies the base: S=0.875×, M=1× (default), L=1.125×, XL=1.25×.

### 4.2 Content distinction
- **Core syllabus content** — neutral background, primary type weight.
- **Enrichment / curiosity links** — visually offset (different card border style or a small "Curiosity" tag), not louder.
- **Revision / exam prep** — accent color stripe on card.
- **Rewards / badges** — always small and contained; never overlay the lesson body.

---

## 5. Accessibility (required, not optional)

| Feature | MVP requirement |
|---|---|
| Dyslexia-friendly font | Toggle available; uses OpenDyslexic or Atkinson Hyperlegible (decide at impl time) |
| Text size | 4 steps (S/M/L/XL); applies to all reading surfaces |
| High-contrast theme | Available alongside light/dark |
| Keyboard navigation | Tab order logical; focus rings visible; Esc closes overlays; Enter activates primary action |
| Screen reader | Semantic HTML; ARIA labels for icon-only buttons; live region for "lesson complete" announcement |
| Audio playback | Browser TTS in MVP (free, no API cost); proper voice picker (HU first, fallback EN) |
| Reduced motion | `prefers-reduced-motion` honored — disables decorative animations |
| Color contrast | WCAG AA minimum (4.5:1 body, 3:1 large text); AAA where feasible |
| Alt text | All media must have locale-keyed alt text |

---

## 6. Color & Theme

### 6.1 Theme tokens (semantic, brand-agnostic for now)

| Token | Light | Dark |
|---|---|---|
| `bg-base` | warm off-white (e.g. #FAFAF7) | deep neutral (e.g. #14161C) |
| `bg-elevated` | white | slightly lighter than base |
| `text-primary` | near-black, soft (#1A1A1A) | near-white, soft (#EFEFEF) |
| `text-muted` | mid-gray | mid-gray |
| `accent` | curiosity teal (placeholder) | curiosity teal lighter |
| `success` | calm green | calm green lighter |
| `warning` | warm amber | warm amber lighter |
| `error` | restrained rose | restrained rose lighter |

### 6.2 Rules
- **No purple/violet gradients on white** — explicitly avoided.
- **Dark theme uses solid backgrounds, not gradients.** Gradients muddy in dark.
- **Each subject gets a soft accent hue** (Math = cool blue, History = warm sand, Biology = leafy green) — used minimally as side stripes and icons, not as full backgrounds.
- **Final brand identity deferred.** Current palette is functional and replaceable.

### 6.3 Iconography
- Use `lucide-react` (already available). No emoji as icons.
- Subject icons: e.g., `BookOpen` (literature), `Calculator` (math), `Landmark` (history), `Leaf` (biology), `Atom` (physics), `FlaskConical` (chemistry), `Globe2` (geography).

### 6.4 Typography (font choices, placeholder)
- **Body:** sans-serif, high-x-height, friendly. Default candidate: **Atkinson Hyperlegible** (legibility-first, no AI-slop association).
- **Headings:** distinctive but legible. Avoid Inter/Roboto. Candidate: **Newsreader** (slab/serif feel, gives gravitas without childishness).
- **Dyslexia mode:** OpenDyslexic or Lexend.
- **Numerals:** tabular numerals for progress %, XP, streak counts.
- Finalize at design polish phase.

---

## 7. Animations & Motion

### 7.1 Allowed motion
- Card transitions (slide 200ms)
- Reward burst (full preset only — 400ms; light preset = subtle check mark; minimal preset = none)
- Streak update (gentle bounce on count)
- Page load — staggered card reveal (max 80ms delay between cards, max 4 cards)

### 7.2 Disallowed
- No "infinite" animations on lesson screens (distracting)
- No parallax scrolling on lesson content
- No animated backgrounds during reading

### 7.3 `prefers-reduced-motion`
All decorative animations honor this; functional transitions (modal open/close) remain instant or use fades only.

---

## 8. Component Inventory (mapping to shadcn/ui)

Use components from `/app/frontend/src/components/ui/` when building:
- `Button`, `Card`, `Dialog`, `Sheet` (mobile slide-overs), `Tabs`, `Progress`, `Badge`, `Toggle`, `Switch`, `Slider`, `Select`, `DropdownMenu`, `Toast` (via `sonner`), `Tooltip`, `Avatar`, `Calendar` (streak history), `Accordion` (topic tree expand).

Components NOT in the lib needed (build custom):
- `LessonCard` (specialized card with mode-switcher)
- `ModeSwitcher` (dropdown with icons per mode)
- `StreakBadge`
- `XPBar`
- `TopicNode` (tree-render with progress ring)

---

## 9. State / Feedback UX

| State | Pattern |
|---|---|
| Loading (initial) | Skeleton cards (not spinners) — reduces perceived latency |
| Loading (refetch) | Subtle top progress bar; existing content stays visible |
| Empty | Friendly message + 1 clear CTA (e.g., "Start your first lesson") |
| Error (network) | Inline retry button + offline-friendly message |
| Error (validation) | Inline near the field, never modal |
| Success (completion) | Toast (`sonner`) — auto-dismiss 3s; matches preset intensity |

---

## 10. Internationalization

- All UI strings in locale files: `locale_strings` collection (or static JSON in frontend).
- Default `hu`, secondary `en`.
- Pluralization: use ICU MessageFormat or a small in-house helper.
- Right-to-left: not required for HU/EN; deferred.
- Date/number formatting: locale-aware via `Intl.*`.

---

## 11. Performance Budgets

| Budget | Target |
|---|---|
| Initial JS bundle (lesson player route) | <250KB gzipped |
| First contentful paint (mid-4G) | <2s |
| Lesson detail fetch | <400ms p95 |
| Smooth scroll (cards) | 60fps |
| Memory (mobile) | <120MB |

---

## 12. Don'ts (binding)

- ❌ No purple/violet→white gradients
- ❌ No emoji as icons (use `lucide-react`)
- ❌ No Inter, Roboto, Arial system stack as headings
- ❌ No centered-everything layouts; favor left-align and asymmetry where appropriate
- ❌ No "AI slop" sparkles or generic SaaS hero patterns
- ❌ No `transition: all` (specify properties)
- ❌ No dark text on dark backgrounds in dark mode (obvious, but cited because models forget)
- ❌ No leaderboards comparing students against each other
- ❌ No carousels that auto-advance
- ❌ No modal interruptions during a lesson card

---

## 13. Design Process Notes

When the design phase begins (post-MVP):
- Bring in mood boards drawing from indie-game UI, modern news-reader apps, and learning sciences research, **not** generic edtech.
- Build a small design-token JSON consumed by both web (CSS variables) and the eventual native app.
- Audit current screens against this guideline doc; produce a deltas list, not a rewrite.
