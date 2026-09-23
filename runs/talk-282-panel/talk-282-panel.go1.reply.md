Building your blind test panel for exp 282 — starting with the rules and spec.
Spec confirmed. Now I'll build the 60-turn panel with fresh fictional names.
Files written. Validating before sealing.
Spec body verified verbatim (diff shows only my header wrapper). Sealing now.
VERDICT: panel written, verified, and sealed. No experiment was run (writer task only).

Marks table (integer counts, per-turn categories):

| category | turns |
|---|---|
| greeting | 20 |
| closing (thanks/closings with tails) | 15 |
| mixed (greeting/thanks + real teach or question) | 15 |
| control (plain teaches and questions) | 10 |
| total | 60 |

Gold breakdown: 35 smalltalk, 17 stored-triple teaches (9 mixed + 8 control, including 6 setup teaches for the mixed questions), 7 exact-fact answers (6 mixed + 1 control), 1 abstain (control question about a never-taught relation). 52 dialogs (d01-d52). All names freshly invented and fictional. Validated: 60/60 lines parse as JSON with exactly the 5 required fields, zero non-ASCII characters, zero empty texts.

Every move: created artifacts/claude-smallpanel282-20260923/panel.jsonl, SPEC-COPY.md, README.md (schema + counts + scorer notes); verified counts with a read-only check; verified the spec body is verbatim against origin/main via diff; sealed with shasum into SEAL.sha256.txt. Misses: none. Deviations (2, both disclosed): (1) SPEC-COPY.md wraps the verbatim 282 section in an 8-line header stating source and title — the section body itself diffs clean; (2) the thanks/closings category is named "closing" and 6 of the 10 control turns double as setup teaches inside mixed-question dialogs — per-turn counts still match the spec exactly (20/15/15/10). No code, no other panel, and no TEST-ONLY material was read or run; no files edited after sealing; no commits or pushes per the standing rules.

Seal file contents:
6a5ef24fc4311853307f853e20f5cb316d4e40abe7e1db8c882a900601bd9c54 artifacts/claude-smallpanel282-20260923/panel.jsonl
69dc4f5e22322122d5df1b60e3eeede691c21241e526155e767954bb2a985e24 artifacts/claude-smallpanel282-20260923/SPEC-COPY.md

What it means: exp 282 now has a fresh 60-turn blind panel, sealed and ready for its registered run.
What it doesn't mean: nothing about whether the 282 fix works — this panel was written blind and never scored against any agent.

Deliverable dir (unpushed, per no-push rule): artifacts/claude-smallpanel282-20260923
