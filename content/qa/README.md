# Content audit: web fact-check findings

One file per Témakör: `content/qa/<nat_id>.json`. Each file checks the snapshot
`content/snapshot/<nat_id>.json` against the live web. The snapshot is exported by
`content/generators/export_snapshot.py`, because the lessons themselves live in Supabase.

The work is split between two sessions:

| Step | Who | Tool |
|---|---|---|
| Export lessons (every mode, quizzes, inactive blocks) | session with DB keys | `export_snapshot.py` |
| Fact-check against the web, write findings | audit session (no DB keys) | `qa_audit.py checklist / lint / validate` |
| Apply fixes | session with DB keys | `qa_audit.py apply` → `edit_content_card` RPC |

Applying goes through `edit_content_card`, so every fix is logged in `content_edits` and can
be undone from `/admin/reports → Szerkesztések`. The RPC also compares the stored card with
the one in `fix.before`. If the card changed after the export, the RPC refuses the edit
(409) and `apply` skips that finding without overwriting anything.

## File format

```json
{
  "nat_id": "HIST-56-01",
  "snapshot_exported_at": "<copied from the snapshot>",
  "checked_at": "2026-09-29",
  "coverage": {"blocks": 14, "cards": 61, "claims_checked": 38},
  "findings": [
    {
      "id": "HIST-56-01-001",
      "lesson_id": "…", "block_id": "…", "mode": "quiz", "scope": "lesson", "card_index": 3,
      "field": "options[1]",
      "verdict": "outdated",
      "severity": "high",
      "claim": "Kiptum 2:00:35 — jelenlegi maratoni világrekord",
      "explanation": "Sawe ran 1:59:30 in London on 2026-04-26; World Athletics has ratified it.",
      "sources": [{"url": "https://worldathletics.org/…", "title": "…", "accessed": "2026-09-29"}],
      "apply": "auto",
      "fix": {"before": { …the whole card as in the snapshot… }, "after": { …the whole corrected card… }}
    }
  ]
}
```

Only problems are recorded. `coverage` shows how much was checked, so "no findings" can be
told apart from "not checked".

### `verdict`
| value | meaning |
|---|---|
| `wrong` | the claim is false |
| `outdated` | it was true but no longer is (records, "ma", statistics) |
| `misleading` | technically true, but it teaches a wrong picture or a misconception |
| `quiz_key` | the answer marked correct is wrong, or more than one option is correct |
| `unverifiable` | no reliable source confirms it, so it should be generalised or removed |
| `language` | grammar, Hungarian number format (tizedesvessző, ezres szóköz), a/az articles |

`wrong`, `outdated` and `misleading` need at least one source; `quiz_key` does too when the
error is factual (not when it is internal, e.g. the marked letter is not among the options). Source priority:
the official body (World Athletics, UCI, World Aquatics, BIPM, NASA/ESA …), then an academic
or museum source or an encyclopedia (Britannica, MEK, Arcanum), then Wikipedia (only as a
secondary source). When sources contradict each other, the verdict is `unverifiable` and
`apply` is `review`.

### `severity`
- `high`: a student would learn something false, or get marked wrong for a correct answer
  (quiz errors are always high).
- `medium`: a factual slip that doesn't affect understanding (a secondary date, a detail).
- `low`: style or language.

### `apply`
- `auto`: `fix.after` is safe to apply as is (a clear error with a clear source).
- `review`: a teacher or you decides first (interpretation, curriculum simplification,
  contradictory sources). `apply --include-review` applies these too.
- `none`: flag only, no fix given (e.g. a missing image, or a structural problem).

`fix.before` is always the whole card exactly as in the snapshot. `fix.after` is the whole
corrected card with the same keys. For each card there is at most one finding with a fix;
several problems on one card are merged into one `after`.

## Commands

```bash
cd content/generators
python qa_audit.py checklist HIST-56-01 [--modes text quiz]  # every text field, numbered
python qa_audit.py lint HIST-56-01 [--only quiz_key time_sensitive]
python qa_audit.py validate [HIST-56-01 …]                   # exits 1 on any error
python qa_audit.py status                                     # coverage per band
python qa_audit.py apply HIST-56-01 --dry-run                 # needs backend/.env
python qa_audit.py apply HIST-56-01 --editor <user_profiles.id>
```

`apply` records the created `content_edits.id` of each fix in the file's `applied` field, so
running it again doesn't apply anything twice.

## What gets checked
- Every concrete claim (dates, names, numbers, places, records, "a világ leg-…", "ma",
  statistics) against a source.
- Quizzes: whether the answer key is correct, whether there's a single correct answer, and
  whether the explanation matches.
- Physics: misconceptions (centrifugal force, "gyorsulás = gyorsabb", heavier objects fall
  faster …) and units.
- History: anachronisms and the global context layer (whether it fits the lesson's period).
- NOT checked: textbook simplifications that are correct at the grade level, or style that
  isn't an error.
