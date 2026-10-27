# slp-361 pass marks (registered 2026-09-25, before any run)

Change (one): staged commit + undo for a whole sleep (scripts/claude_slp361_undo.py). A judge decides after the
sleep; on "reject" the night is undone. Card test, CPU, $0, seeds 1 and 2. Every arm has slp-360 installed.
World: exp-104 (fable_sleep104_drive.build_turns, noise 0): 50 taught facts, 20 grandmother questions,
5 fillers = 75 turns; then the sleep step; then 5 new-people probes + 1 broken-chain probe; then a restart from
the same state dir and the 6 probes again.

Arms: N = 360, no sleep at all. S = 360, one sleep (no 361). A = 360 + 361, judge accepts. R = 360 + 361, judge
rejects. R2 = R, then a second sleep with a judge that accepts (after the restart probes).

| Mark | Bar (each seed) |
|---|---|
| P361.1 R: every file under the state dir except state.json and undo361/ is byte-identical before vs after the rejected sleep | all identical |
| P361.2 R: main notebook event log byte-identical before vs after | identical |
| P361.3 R: the 12 probe replies (6 after sleep + 6 after restart) identical to arm N's | 12/12 |
| P361.4 R: experience log length after the undo equals its length before the sleep | equal (75) |
| P361.5 A: all 87 replies (75 turns + 6 + 6) identical to arm S's, and installed = S's | 87/87 and same |
| P361.6 R: every file the rejected sleep created still exists under undo361/ (nothing deleted) | all present |
| P361.7 R2: right after the undone night and its probes, in the same process (no restart), a second sleep with an accepting judge installs the word; its 5 probes right | installed; ≥ 4/5 |

Report only: count of files moved and restored per undo; S's installed flag and probes (expected installed, 5/5).

Proved wrong if: any file other than state.json differs after a rejected night, or any R probe reply differs
from never having slept.
