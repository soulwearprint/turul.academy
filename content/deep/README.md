# Deep-dive cards written without OpenRouter

`<nat_id>.json` holds „Mesélj még!” cards (mode `deep`) for every lesson that had none in the
snapshot. They were written by the cloud audit session from the snapshot's text cards, with
facts checked while writing, so no OpenRouter call is needed. They follow the same rules as
`generate_deep_dive.py`: one card per text card (`anchor`), something new beyond the card (a why,
a surprising consequence, or a small worked example), grade-level language, and an empty
`did_you_know` rather than an uncertain one. Where the lesson's text card is wrong (see
`content/qa/<nat_id>.json`), the deep card gives the correct facts.

```bash
cd content/generators
python ingest_deep_dive.py --check                    # offline: anchors, empty fields, articles, decimals
python ingest_deep_dive.py --nat-id PHYS-78-01 --dry-run
python ingest_deep_dive.py --all                      # save every file (skips lessons that already have deep)
```

A lesson is skipped if its live text block is not the one the cards were written for
(different block id or card count), so anchors can't point at the wrong card. Apply the
`content/qa` fixes before or after; they only change text inside cards, never the card count.
