#!/bin/bash
# Full content regeneration onto the new generator: spine-based, blended causal+human
# story voice, grammar/proofread pass, auto-published. Runs on OpenRouter (gpt-4o-mini)
# — does NOT use Claude limits. Each lesson upserts + activates as produced, so an
# interruption still publishes completed topics; re-running is idempotent.
cd /Users/gabor/Documents/GitHub/turul-academy/content/generators
echo "===== REGEN START $(date) ====="
echo ">>>>> HISTORY (all grades 5-12)"
python3 generate_lesson.py --subject HU-NAT-HISTORY-2020 --activate
echo ">>>>> PHYSICS (all grades 7-11)"
python3 generate_lesson.py --subject HU-NAT-PHYSICS-2020 --activate
echo "===== REGEN DONE $(date) ====="
