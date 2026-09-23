Building exp 281 — setting up the called/named questions fix.
Sibling panels are forming — checking the lane for 281 before I start.
Structure mapped. Setting up the work plan and digging into the probe failure.
Failure reproduced on 260. Probing the wording variants before designing the fix.
All four called-wordings fail systematically on 260 while plain questions work. Checking the sibling's dev/runner pattern, then writing the fix.
Pattern is clear. Writing the fix and agent files now (all new files).
Now the dev set — 46 dialogs in my own wording.
Now the scorer and runner.
I misrouted the runall content into the panel script path — fixing by writing both correctly.
46 dev cases ready. Piloting on both arms.
Dev pilot is 46/46 with exactly the 30 predicted moves. Verifying the 260-side failure modes for the report.
All four shapes fixed, everything else identical. Scanning suites for called-wording before the heavy pilot.
One probe turn will move — checking precisely which turns match my rewrite.
N06 will move on 281 (stored fact + name-of wording) — that's a predicted move. Launching the pilot suite run.
Pilot confirms: 0 suite moves, exactly one probe move (N06). Checking its new reply.
Pilot regscore PASS. Validating the panel runner/scorer on a mock panel in /tmp.
Mock works, but my broken-abstain regex is too broad — tightening it to only flag replies ending in called/named.
Seal is 15/15 OK. Appending ledger predictions.
Ledger appended. Entering the panel-seal wait loop.
Panel sealed. Verifying both seals and reading the spec copy (not the items).
Both seals OK. The panel uses per-turn rows (`dialog_id/turn_index/user_text/category/gold`) — my sealed runner expects whole-dialog items, so per the 268 precedent I'll add new driver files (sealed files untouched) rather than modify anything sealed.
Driver validated. Writing the registered panel-run script and executing the registered runs.
Registered suites PASS exactly as predicted. Running the blind panel once per arm.
Panel run once per arm: stored 16/25 — below the 90% bar. Running a mechanical miss analysis (booleans only, no item text).
Diagnosis is mechanical and complete. Collecting the moved-ids list for RESULTS (ids only).
Ledger outcome appended. Checking how sibling artifacts are staged to interpret PUSH correctly (OPUS-RULES forbids remote pushes).
Verdict: FAIL — stored bar 16/25 (needs ≥23/25). Every other bar passes.

Marks table (integer counts, 260 beside 281):

| bar | 281 | 260 | pass? |
|---|---|---|---|
| stored answered exactly (≥23/25) | 16/25 | 0/25 | FAIL |
| stored wrong answers (0) | 0 | 0 | pass |
| not-stored abstain (10/10) | 10/10 | 10/10 | pass |
| ambiguous same as 260 (10/10) | 10/10 | — | pass |
| control same as 260 (5/5) | 5/5 | — | pass |
| panel store diffs 281 vs 260 (0) | 0/60 | — | pass |
| question writes on 281 (0) | 0 | 0 | pass |
| teach gold stored | 8/10 | 8/10 | identical |
| suites: sessions152 / bench / rt136 / rt143 moves | 0/0/0/0 | — | pass |
| verifier probes moves | 1 (N06, predicted) / supp 0 | — | pass |
| dev set 281 | 46/46 | — | n/a |

Every move: panel stored → right on 16 ids (D01#1, D01#2, D01#3, D03#1, D03#2, D04#1, D04#2, D05#1, D05#2, D05#3, D06#1, D06#2, D07#1, D07#2, D08#2, D09#1), all toward right, 0 against. Probe N06 → the stored answer (predicted). Dev 30/30 stored-shape turns → exact value (predicted).
Every miss: 9 stored abstains (D02#1, D02#2, D02#3, D03#3, D04#3, D08#1, D09#2, D10#1, D10#2), 0 wrong. 5 sit in dialogs whose teach fails identically on 260 (empty store, unanswerable on any arm); 4 are called-wordings outside the four sealed shapes (contraction-fronted, possessive-name, no-question-mark casuals) kept as 260 by design. 0 flips toward abstain anywhere, so no 5× follow-ups. Shared misses: teach 2/10 and control 1/5 fail equally on 260.
Deviations: (1) No schema gate — the brief gave no exact schema, declared pre-seal in PASSMARKS; the writer's per-turn-row schema matched the spec counts exactly, so no VOID. (2) Post-seal driver addition (panelrun.py, panelscore.py, panelrun.sh — new files; diffs described in RESULTS.md); sealed 15 files unchanged, seal re-verified 15/15 OK. (3) Sealed panel.sh/runner unused (whole-dialog loader); registered panel ran via the new drivers, once per arm. Changed replies live only in scripts/claude_fix281_called.py.

What it means: asking "called/named" questions the plain way now gets the stored answer on all four spec shapes, with zero guesses, zero wrong answers, and zero notebook changes — 16 blind items fixed, nothing broken.
What it doesn't mean: it doesn't cover every casual wording — shortened and punctuation-free forms of the question still get the old reply, and if the teaching itself didn't stick, no question wording can help.
