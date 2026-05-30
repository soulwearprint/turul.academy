# CuriousPath — Token / Credit Efficiency Strategy

**Status:** Pre-planning. AI is **not** in MVP. This document exists so when AI is enabled (Phase 3+), we don't pay rookie costs.

**Audience:** Engineering + finance.

---

## 1. Why This Matters

Naive AI integration on a learner app can burn budget fast:
- Every lesson view × every learner × multiple rephrasings × multiple modes = O(many ×) tokens
- Quiz generation on demand, per learner, per topic, repeated
- "Always-on" curiosity link generation

Without strategy, the bill scales with usage (good for revenue, bad for margins if not priced correctly).

**Our approach: defer + design.** Ship MVP with curated content. When we add AI, every feature is gated by cost-aware design.

---

## 2. Cost Control Principles

1. **Cache aggressively.** Once a lesson has been rephrased into "story mode," store it. Don't regenerate per user.
2. **Pre-generate the common, on-demand the rare.** Top-trafficked lessons get pre-generated mode variants (curated or AI). Long-tail / personalized variants generated lazily.
3. **Tier the model to the task.** Don't use a flagship model for a 1-sentence rewrite.
4. **Bound output length.** Every prompt specifies max tokens. No "write me an essay" prompts.
5. **Reuse across users where possible.** A "story mode" rephrase of a lesson doesn't need to be unique per learner. Personalization happens via metadata (tone preference), not full regeneration.
6. **Throttle by feature flag.** Each AI feature has independent on/off + rate limits.
7. **Monitor per-user spend.** Track inference cost per user per day; soft-throttle abusers; surface usage in admin dashboard.

---

## 3. Caching Layers

```
Request: "Rephrase lesson L in story mode for learner U"
   │
   ├─ Layer 1: Per-lesson cache
   │     Key: (lesson_id, mode, style_token)
   │     → If hit: return cached. No LLM call.
   │
   ├─ Layer 2: Per-user override cache (rare)
   │     Key: (lesson_id, mode, user_id) — only if user has high-personalization profile
   │     → If hit: return cached.
   │
   └─ Miss → call LLM → store in Layer 1 (and Layer 2 if user-specific)
```

- Layer 1 cache: MongoDB `lesson_mode_cache` collection.
- TTL: indefinite for stable lesson content; invalidated when lesson `version` bumps.
- Estimated cache hit rate after warm-up: **>95%** for popular lessons.

---

## 4. Model Tiering

| Task | MVP-deferred model | When to use cheaper model |
|---|---|---|
| Short lesson rephrase (≤200 words) | Mid-tier model (e.g. GPT-4o-mini / Gemini Flash) | Almost always |
| Lesson-level story mode generation | Mid-tier model | Default |
| Complex quiz generation w/ answer rationale | Higher-tier model | Only when generated for review/seed, not per-user |
| Cross-reference suggestion (Phase 4) | Mid-tier | Default |
| "I'm stuck" intelligent re-explanation | Mid-tier with short max-tokens | Default |
| Adult curation review of AI output | Higher-tier (one-off) | Editorial only |

**Default:** mid-tier. Escalation requires explicit feature decision.

---

## 5. Prompt Discipline (when AI activates)

Every AI call:
- Has a **named template** in code (not free-form prompt building in handlers)
- Has explicit `max_output_tokens`
- Has a **JSON output schema** where possible (eliminates parse cost & error retries)
- Includes only the **minimal context** needed (the specific lesson card, not the whole lesson)
- Logs `template_id`, `model_id`, `tokens_in`, `tokens_out`, `latency_ms`, `cache_status` per call

---

## 6. Pre-Generation vs On-Demand Decision

Per AI feature, decide:

| Feature | Pre-gen? | Rationale |
|---|---|---|
| Story mode for top 200 lessons | Yes | High cache hit rate; one-time cost |
| Story mode for long-tail lessons | On-demand | Rare requests; cache after first |
| Quiz items (extra variants) | Yes (one-time, batched) | Stored in `quizzes` collection |
| AI-generated curiosity links | Pre-gen (editorial review before publishing) | Trust requires review |
| "I'm stuck" alternate explanation | On-demand | Per-user context valuable |
| Personalized study plan | On-demand, infrequent (~1× / week) | Bounded frequency |

---

## 7. Feature Flags (when AI activates)

Each AI feature gets its own flag with three states: `off`, `internal` (employees only), `on`. Independent for:
- `ai.rephrase_modes`
- `ai.stuck_mode_assist`
- `ai.quiz_generation`
- `ai.crossref_suggestions`
- `ai.study_plan_personalization`

Daily/monthly cost cap per flag is configurable; on breach, flag auto-degrades to `off` with admin alert.

---

## 8. Per-User Budget Awareness

- Each user has a tracked `ai_inference_cost_30d` value
- A soft cap (admin-configurable) triggers throttling: lower priority queue, fall back to curated content
- Hard cap triggers full degrade to curated only (with friendly message)
- Free vs paid tier distinction (when monetization arrives) can map directly to these caps

---

## 9. When Curated Content Beats AI

Even after AI is on, prefer curated content when:
- The lesson is core/foundational (high traffic) — pre-curate the modes
- Accuracy is exam-critical (math proofs, dates, scientific facts) — AI hallucinations are expensive in trust
- The student is a minor (always — extra trust care)
- A great verified video already exists — show it

AI use cases where it shines for us:
- Last-mile personalization (tone shift to a stuck learner's level)
- Alternate-angle explanation generation when curated variant doesn't fit
- Side-quest copy variants (low risk)
- Quiz item *seeds* for curator review

---

## 10. Cost Math Sketch (illustrative, recalc when activated)

Assumptions (illustrative):
- 1000 active learners
- Avg 5 lessons/week each = 5000 lesson views/week
- Mode variants pre-generated: 0 marginal cost per view
- "I'm stuck" used 1 in 20 views = 250 calls/week
- Avg "I'm stuck" call = 600 tokens in + 200 tokens out
- Mid-tier model price (assume ~$0.30 / M input, $1.20 / M output)
- Per-call cost: 600 × 0.30/1M + 200 × 1.20/1M ≈ **$0.00042**
- Weekly: 250 × $0.00042 ≈ **$0.11/week**
- Plus quiz generation (batched, ~$30/month seed cost amortized) + curiosity gen (editorial, batched)

Conclusion: **AI cost is low when the design is right; high when it isn't.** Discipline > model choice.

---

## 11. Integration When Activated

When the time comes to enable AI:
1. Call `integration_playbook_expert_v2` with the chosen model + task
2. Use the universal Emergent LLM key
3. Honor the playbook's installation/SDK choices
4. Wrap calls in the caching + flag framework above
5. Add cost dashboards before turning the flag on for general users

---

## 12. What Stays Curated Forever

Even at full AI maturity, these are **always** human-curated:
- Verified video selection
- Cross-reference editorial vetting (AI may suggest; curator approves)
- Exam-prep core revision summaries
- Anything shown as a "fact" in a confidence-affecting context
