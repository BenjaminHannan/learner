Blind panel writer for 282b — building your sealed test set without touching any code.
Spec extracted (282b paragraph only). Now checking the target directory is fresh, then writing the panel.
Directory is fresh. Creating it and writing the three files.
I made an encoding error on five emoji (wrote literal `\u0001`/`\u0002` escapes instead of emoji). Fixing those lines before sealing.
Now the spec copy and readme.
Validating my own file (schema, counts, sequencing) before sealing.
Validation passes. Sealing now.
VERDICT: Panel complete and sealed. `artifacts/claude-smallpanel282b-20260923/` holds 60 turns across 48 dialogs, matching the 282b spec counts exactly.

Marks table (integer counts, writer-side only — nothing has run):

| category | turns | gold form |
|---|---|---|
| greeting | 20 | `smalltalk` |
| closing | 15 | `smalltalk` |
| mixed | 15 | 8 teach triples `Subject\|relation\|Object` + 7 exact answers |
| control | 10 | 5 teach triples + 5 exact answers |
| total | 60 | 48 dialogs, 0-based turn_index, all sequences check out |

Every move: created 4 new files, nothing else touched — `panel.jsonl` (60 lines, exact keys `dialog_id, turn_index, user_text, category, gold`), `SPEC-COPY.md` (verbatim 282b panel-spec paragraph), `README.md` (counts per category), `SEAL.sha256.txt`. Validation before sealing confirmed 60/60 lines parse, key sets exact, counts 20/15/15/10, 48 dialogs with sequential turn indices, 13 teaches with 13 distinct invented names, no control characters.

Misses: none at write time. Two deviations to report honestly: (1) I fixed 5 emoji bytes in my own unsealed draft before sealing (literal escape text replaced with the intended emoji) — this happened before the seal, so the seal covers the final bytes; (2) to locate the one allowed paragraph I listed section headings and viewed only lines 119–140 of the spec file — I never opened scripts, scorers, or any other panel, and never ran any repo code.

What it means (plain English): the test is ready for the 282b builder. 35 of the 60 turns check whether casual hellos and thank-yous get a friendly reply instead of an error; the other 25 check that real fact-teaching and fact-questions still work when small talk is mixed in or left out.

What it doesn't mean: this says nothing about whether the 282b fix itself works — no agent ran, no score exists, and I never looked at the 4 items 282 missed, so this panel can't be tuned to them. Seal contents:

```
cf83b2001f01fa0de8b90ccd413bdedadefed7ab9f91360d25d915bcc63d2994  artifacts/claude-smallpanel282b-20260923/panel.jsonl
32537032813801b1188222b1db5ef7bc42e847d5afa802f22bf9f08bdb504857  artifacts/claude-smallpanel282b-20260923/SPEC-COPY.md
```

Deliverable (uncommitted, per the no-commit rule) at: `artifacts/claude-smallpanel282b-20260923`.
