#!/bin/bash
# Regenerate all OLD-generator content onto the new spine generator, auto-publishing.
# Runs on OpenRouter (gpt-4o-mini) — does NOT use Claude limits. Resilient: each
# lesson upserts + activates as it's produced, so an interruption still publishes
# completed topics. Re-running is idempotent.
cd /Users/gabor/Documents/GitHub/turul-academy/content/generators
echo "===== REGEN START $(date) ====="
for g in 5 6 7 8 9 10; do
  echo ">>>>> History grade $g"
  python3 generate_lesson.py --subject HU-NAT-HISTORY-2020 --grade "$g" --activate
done
echo ">>>>> Physics (all grades)"
python3 generate_lesson.py --subject HU-NAT-PHYSICS-2020 --activate
echo "===== REGEN DONE $(date) ====="
