Running your sealed 280p probe — verifying the seal and assembling 60 fresh dialogs.
Seal checks out 12/12. Now mapping how to run the five arms.
Design is clear — 60 fresh dialogs plus the 12 chatweak ones. Checking runtime budget before I write them.
Runtime looks cheap (~43s for the last full panel). Writing the 60 fresh dialogs now.
60 dialogs / 73 turns written. Creating the two probe scripts (new files only).
Scripts ready. Running the probe panel on all five arms now.
All five arms ran the probe. Scoring with the sealed mechanical rule.
Probe holds at 73/73. Now running the chatweak dev set on all five arms.
Small arg-parsing bug in my scorer — fixing it.
Both sets hold. Pulling the exact counts for the report.
All counts verified. Writing the RESULTS.md now.
Verdict: HOLD (report-only probe — no bar can be changed by it). Measured: 280m agrees with the mechanical owner on 73/73 fresh probe turns and 91/91 chatweak dev turns, with 0 overlaps, 0 question/small-talk writes, 0 store differences vs 260, and 0 old-sheet hits.

Marks table (integer counts):

| mark | probe (60 new dialogs / 73 turns) | chatweak dev (12 dialogs / 91 turns) |
|---|---|---|
| turns, each run once on all 5 arms | 73 | 91 |
| agreement (280m == mechanical owner: reply + writes + store) | 73/73 | 91/91 |
| overlaps (2+ piece arms differing from 260 on one turn) | 0 | 0 |
| miss ids | none | none |
| writes on question turns (280m) | 0 | 0 |
| writes on small-talk turns (280m) | 0 | 0 |
| writes on non-teach turns | 11, all control-statement turns, each byte-identical to its owner | 15, all statement turns (0 on "?" turns, 0 in small-talk dialog) |
| store differences 280m vs 260 | 0 | 0 |
| owner counts | 260: 55, 280b: 11, 282b: 5, 281: 2 (sum 73) | 260: 87, 282b: 2, 280b: 1, 281: 1 (sum 91) |
| old-sheet scan hits on 280m replies | 0 | n/a (reply files listed in RESULTS.md) |

Every move: probe by category — ability 10/10, teach 8/8, called 12/12, smalltalk 15/15, mixed 8/8, control 20/20. Ability-text counts (report-only): 280m CAN-line 9 ability + 2 mixed vs 260's 5 + 2, all agreeing with owner, so inherited from the pieces. The 11 probe write ids: probe280p-46#0, -47#0, -48#0, -49#0, -56#0, -56#1, -57#0, -57#1, -58#0, -59#0, -59#1 (plain teaches and corrections, statements only). The 15 chatweak write ids: t01-teach-askback#1, #2, #5; t02-twohop#1, #2; t03-backwards#0, #1, #3, #5; t04-corrections#0, #1, #3; t05-forgetting#0; t12-restart#0, #1 (ids only, no text). Combined: 164/164 turns agree, 0 overlaps in 164 turns.

Deviations and notes:
1. The brief's rules-file path does not exist here; I followed the key points quoted in the task.
2. I listed (never read item-by-item) the sealed panel folder while orienting; no panel text was read, tuned on, or quoted, and all 60 probe dialogs are my own with fictional names.
3. Two driver-only fixes to my own NEW unsealed scripts (reported, no sealed file touched): `scripts/claude_probe280p_run.py` handles the chatweak restart-marker row; `scripts/claude_probe280p_score.py` had an argv off-by-one fixed before its first good run. 280m seal re-checked OK after the runs.
4. `artifacts/fable-predictions-ledger.md` shows 51 insertions I did not make (another worker in this shared worktree; I never wrote to it).
5. No commit/push performed: `artifacts/` is gitignored (`.gitignore:5`), so `artifacts/claude-probe280p-20260923` (dialogs.json, RESULTS.md, run/) cannot be pushed by normal git; `scripts/claude_probe280p_run.py` and `scripts/claude_probe280p_score.py` are untracked and pushable. All files are ready for the director to collect. Other standing worktree changes were left alone; I never used git log, checkout, or merge.

What it means (plain high-school English): on 73 brand-new everyday-chat turns I wrote and 91 dev turns, the joined agent always gave exactly the answer the responsible piece would have given, never had two pieces fight over a turn, never saved anything on a question or greeting, and its memory matched the base everywhere except where a piece had already changed it.

What it doesn't mean: it doesn't change the 280p PASS (report-only by design); it doesn't mean the answers are factually correct, only that the join faithfully replays its pieces (truth of claims is the director's separate check); and 164 turns prove 0 overlaps here, not that overlaps are impossible.
