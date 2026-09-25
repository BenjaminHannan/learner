# 381 pass marks: stricter "is that right?" harness (month-end line, fixed 2026-09-25 ~03:20 UTC, before judging)

Change: scripts/claude_e2e381_harness.py:confirm_answer381 replaces the 336 runner's confirm_answer (which says yes
when the whole reply names any true value and owner). 381 reads only the confirm question and says yes only when
owner, relation (alias groups in the file) and value(s) all match one fact valid at that turn; unparsable is no.
Built by reading the 54 confirm questions of the DEV rehearsal dev3 (DEV is ordinary dev data). There, 381 turned
13 of the old 39 "yes" into "no" and all 13 were wrong claims by my reading (e.g. "is your snack uriah?").

## Held-out check (no bank A, B, C or D involved)
holdout_questions.jsonl: the 73 distinct DEV confirm questions from every other DEV run (330-dev, 330c-dev, dev2,
lis-e2edev) that are not in dev3, each with the facts true at that turn. Two blind Opus judges answer each as the
user would ("yes" only if the question's claim is exactly true: right person, right relation, right value; else
"no"); a third decides splits. holdout_key.json (old and 381 answers) is applied afterwards by script.

| Mark | What | Bar |
|---|---|---|
| H1 | 381 says yes where the judges say no | 0 |
| H2 | 381 says yes where the judges say yes, over the judges' yes | >= 95% |
Report only: the same two counts for the old harness.
Proved wrong: if H1 > 0, parsing the claim is not enough and the harness needs a judge-model user instead.
Use: 381 is for new banks (C, D) only; 336 and 336b keep the sealed old harness.
