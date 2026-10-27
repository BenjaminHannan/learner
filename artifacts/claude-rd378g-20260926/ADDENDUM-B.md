# rd-378g addendum B (2026-09-26 18:34 UTC): which grades train G, a DEV format check, and three report-only rows

Written before any GLM note or grade for rd-378g has been read (the rd378g-teacher job is still running on the Mac).
PASSMARKS.md and ADDENDUM-A.md stay as sealed; this file adds to them. Marks G1-G4 and the proved-wrong line are
unchanged.

## B1: grades
The label gate for teacher grades moved (rd-378k PASSMARKS-C and PASSMARKS-E): training grades come only from
labeller v3 (scripts/claude_rd378k_teacher3.py), and only if artifacts/claude-rd378k-20260926/VERIFY-gate3.md says PASS
on all rows. rd378g-teacher's own grades (glm/judge_w1.jsonl, labeller v1) train nothing. The 240 dialogs are graded
again by labeller v3 into glm3/ (glm3/notes_w1.jsonl is a byte-for-byte copy of glm/notes_w1.jsonl), and the rows are
`python -B scripts/claude_rd378_data.py --notes artifacts/claude-rd378g-20260926/glm3 --out artifacts/claude-rd378g-20260926/rows`
(a turn is kept only if every note is "ok" and missed == 0; a turn whose missed is unknown, -1, is dropped).
If gate3 fails, G is not trained on GLM grades and the Thread manager gets the counts and the one option PASSMARKS-E names.

## B2: DEV format check before the registered run (test-hygiene rule 3)
After training and before any LoCoMo text is written or scored, G writes notes over rows/dev_dialogs.jsonl (GLM dialogs
held out by id hash, never trained on). If more than 2% of those turns do not parse, the run stops there: no LoCoMo
step runs, no verdict is recorded, and the format problem is fixed first.

## B3: report-only rows (never a mark)
- when off: scripts/claude_rd378g_whenoff.py score, the same scoring with the note's "when" not appended to its text
  (Thread manager, 17:31 UTC: how much of the gain rides on that hand-written step).
- grad_none_after_first_backward from G's summary.json (should be 0).
- note openings (test-hygiene rule 1): among the training targets, the three most common first two words of a note and
  their counts, and the share of empty targets. G is a dedicated note model whose output must parse as the notes JSON
  the store reads (checked by code); it is not the talker.
- v1 against v3: turns kept by each labeller over the same 240 dialogs.
