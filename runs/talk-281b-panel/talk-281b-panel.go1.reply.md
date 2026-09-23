Building your blind test panel — fetching specs and writing items without peeking at code.
Spec paragraph captured. Now I'll set up the output directory and get the exact spec text for the copy file.
Directory is free. Now I'll draft the 60-turn panel design and write the files.
All checks pass. Sealing now.
Verdict: DONE — blind panel for exp 281b written, verified, and sealed. No items are quoted in this report.

Marks table (integer counts, panel.jsonl has 60 lines total):

| Category | Count | Gold rule |
|---|---|---|
| teach_setup | 10 | stored triple Subject\|relation\|Object |
| stored_called | 25 | exact expected value |
| nostore_called | 10 | abstain |
| ambiguous_called | 10 | abstain |
| control_plain | 5 | exact expected value |

Every move (what was built and checked):
- Read only the 281b panel-spec paragraph via git show origin/main (never checked out main, no git log, never opened scripts/, artifacts, or any other panel).
- Wrote 3 new files only, in artifacts/claude-calledpanel281b-20260923/: panel.jsonl, SPEC-COPY.md (verbatim spec paragraph + source line), README.md (counts per category). Nothing existing edited or deleted.
- 10 teach dialogs (d01–d10), each teach exactly "<Name>'s <relation> is <Value>." with invented names and single-token values.
- 25 stored questions, each after its teach in the same dialog (d01–d05 × 3, d06–d10 × 2); 14 of 25 are casual (all-lowercase, no apostrophe, no question mark, whats/what-is), above the 12 minimum.
- 10 no-store same-shape questions (d11–d15) about names never taught; 10 ambiguous items (d16–d20) where the word after called belongs to a work title; 5 plain controls appended as the last turn of d01–d05.
- Machine-checked the sealed files only: exactly the 5 required keys per line, per-dialog turn_index sequences 0..n, teach regex plus teach/gold consistency, stored-after-teach with matching gold, banned names absent.
- Sealed with the exact required shasum command; files untouched after sealing.

Misses: 0. All 60 lines validate; casual count 14 ≥ 12; no banned names.

Deviations:
- PUSH requested but not performed: OPUS-RULES (which applies in full) forbids git commits and pushes, so the sealed directory is left uncommitted in the worktree for the director/harness to collect.
- Ran /usr/bin/python3 read-only checks on my own new panel file (schema/count validation). Never read or ran any repo code, agent, scorer, or other panel.

Seal file contents (artifacts/claude-calledpanel281b-20260923/SEAL.sha256.txt):
0c1c20ad913dbf6c7d232a20c82f1964fc2b690257a9a855113a5fd24f04c763 panel.jsonl
a2569e04b089a763278122193cbf0bca3a361ea3facd96ac5400786ed8b43a3c SPEC-COPY.md

What it means (plain high-school English): there is now a fresh 60-question test that checks whether casually typed called/named questions get the right answer, while also checking that untaught and trick questions get no answer and plain questions still work.
What it doesn't mean: this says nothing about whether any agent passes — the panel was written blind and never run against anything.
