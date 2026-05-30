# CuriousPath — Content Sourcing Policy

This document defines what content sources are allowed, how attribution works, fallback rules when nothing suitable exists, and the curation workflow.

> **Principle:** Trust > quantity. We'd rather show one verified diagram than five borderline videos.
> **MVP rule:** No AI-generated media. Curated only.

---

## 1. Allowed Source Tiers

### Tier A — Always allowed (whitelisted)
Embed and link without per-asset review.

- **Public institutional channels** — MTVA / MTVA Archívum, national museums, national libraries, state universities (`.edu`, `.ac.*`)
- **Khan Academy** (CC-BY-NC-SA where applicable)
- **CK-12 Foundation** (CC-BY-NC)
- **National educational broadcasters** (BBC Bitesize, ARD Mediathek, Sulinet [HU])
- **Wikimedia Commons** images, diagrams marked CC-BY-SA, public domain, or CC0
- **OpenStax** (CC-BY)
- **NASA, NOAA, ESA imagery** (mostly public domain — verify per asset)

### Tier B — Allowed per-asset review
Whitelisted at the asset level, not the channel level.

- **YouTube channels of known educators** (e.g., 3Blue1Brown, Veritasium, Crash Course) — embed only with explicit per-channel approval and attribution
- **Hungarian educator YouTube channels** — case-by-case
- **University lecture recordings** (specific permissions verified)
- **Public-domain books / classical texts** (Project Gutenberg, MEK [Magyar Elektronikus Könyvtár])

### Tier C — Disallowed
- ❌ Random YouTube uploads (low trust)
- ❌ Commercial textbook publisher content (without license)
- ❌ Paid streaming platforms (Netflix, etc.)
- ❌ Social media user-generated content
- ❌ AI-generated images, video, audio at MVP
- ❌ Any source without clear provenance

---

## 2. Per-Asset Metadata (required)

Every `MediaRef` row stores:

| Field | Required | Example |
|---|---|---|
| `source_url` | yes | https://commons.wikimedia.org/wiki/File:Cell_diagram.png |
| `source_attribution` | yes | "Diagram: Wikimedia Commons, user 'Acme'" |
| `license` | yes | "CC-BY-SA-4.0" |
| `license_url` | yes | https://creativecommons.org/licenses/by-sa/4.0/ |
| `verified_at` | yes | 2026-02-15 |
| `verified_by` | yes | (curator user id) |
| `notes` | optional | "Cropped to focus on nucleus" |

Attribution is always **visible to the learner** on the asset — small caption beneath video/image. Not buried in app credits.

---

## 3. Fallback Hierarchy (when no Tier A/B asset exists)

For each lesson card needing media, in order of preference:

1. **Tier A verified asset** (preferred)
2. **Tier B reviewed asset**
3. **Curated static illustration** from our in-house illustration library (in-house authorship)
4. **Text-only card with descriptive prose** (always available)

We do **not** fall back to AI-generated media in MVP. If we ever do (Phase 6+), it must be explicitly labeled "AI illustration — not a photograph."

---

## 4. Verified Video Embedding Rules

- Always embed via the source platform's official embed (YouTube iframe, etc.) — never re-host
- Use `youtube-nocookie.com` (or equivalent) where available — better privacy posture
- Disable related-video suggestions in the iframe parameters
- Attach attribution caption visible without click
- Track only "video opened" / "video completed" events; no third-party tracker injection

---

## 5. Static Illustration Library

In-house illustrations (when commissioned/produced):
- SVG-first (scales clean on mobile)
- Stored in object storage (Phase 6) — at MVP, ship inline or via static asset folder
- Locale-neutral where possible (use locale-keyed labels overlaid by app, not baked-in text)
- Color palette aligns to subject accent hues (see `UI_UX_Guidelines.md`)

---

## 6. Curation Workflow

```
1. Content author identifies a need (lesson X needs media for card 3)
2. Search Tier A → Tier B → in-house library
3. Capture metadata (URL, license, attribution)
4. Submit MediaRef row in review queue
5. Curator (separate role from author) verifies:
   - URL still resolves
   - License compatible with our use (especially commercial use — CC-NC requires care)
   - Attribution complete
   - No content concerns (age-appropriate, factually accurate)
6. Approved → published to lesson
7. Quarterly link-check job re-verifies URLs still live; broken refs surface to curator
```

---

## 7. Copyright & Trust Safeguards

- **License compatibility check** for every asset. If our app is ad-free and non-commercial for students at MVP, CC-NC works. If we monetize later, NC assets must be replaced.
- **DMCA / takedown process** documented at launch (even if rare).
- **Removed assets** are soft-deleted, not hard-deleted — the lesson falls back to next-tier source automatically.
- **Auditable trail:** every MediaRef has create_at + verified_by + last_checked_at.

---

## 8. Data Privacy in Embedded Content

- No tracking pixels from third parties.
- All video embeds use privacy-enhanced modes where supported.
- We do not pass user identifiers to embedded content sources.

---

## 9. Future: AI-Generated Media (Phase 6+, not MVP)

When AI-generated visuals/animations are introduced:
- Always labeled clearly ("AI illustration")
- Subject expert reviews each before publishing — not auto-published
- Stored with `generator_model`, `prompt_hash`, `generated_at`
- Same license discipline as everything else (we own the prompt, generator's TOS governs use)

---

## 10. Content Removal & Versioning

- When a lesson is revised, the old version is archived (not deleted) for audit
- When a media source disappears, the broken lesson surfaces a soft warning to admins, and the user-facing card auto-falls-back to the next-tier asset
- Content team has a monthly "verified content drift" report

---

## 11. Hungarian-Specific Notes

- **Sulinet** (sulinet.hu) is a state-curated educational resource — Tier A.
- **MTVA Archívum** is Tier A for historical footage but specific clips require per-asset attribution.
- **Hungarian Wikipedia** mirrors Wikimedia Commons rules — Tier A.
- **MEK (Magyar Elektronikus Könyvtár)** — Tier B for classical Hungarian literature texts.

---

## 12. Quick-Reference Decision Tree

```
Need media for a card?
│
├─ Is it on Tier A? → use it, attribute it. Done.
│
├─ Is there a Tier B option? → submit for per-asset review. If approved, use it.
│
├─ Have an in-house illustration? → use it.
│
├─ Else → text-only card. No AI media. No random YouTube.
```
