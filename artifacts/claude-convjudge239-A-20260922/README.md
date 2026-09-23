# claude-convjudge239-A-20260922 — TEST-ONLY

TEST-ONLY. Judge A's blind hand grades of agent 138i on the exp 239 conversation panel
(artifacts/claude-convpanel239-20260922, seal checked OK before grading).

- RESULTS.md: rubric, rates, mistake counts, ranked failure classes in general words (safe for builders to read).
- grades-138i.jsonl: one row per turn (244), every rubric field plus a one-line fix.
- examples-TEST-ONLY.md: verbatim panel examples. Builders must NOT read this file or grades-138i.jsonl
  (the fix lines echo panel content); do not tune on anything here.

Judge A read only the panel, the transcripts and the stored triples. No agent code or design notes were read.
