Your registered re-test is queued — I'll verify the sealed baseline and set up the 280n run.
Baseline files check out — now I'll confirm the seal and map the scoring requirements.
New scorer drafted — now I'll validate the mixed-ownership logic end-to-end.
Core paths pass — now I'll check the remaining edge cases.
All mock checks pass — now I'll lock in the predictions and seal.
The blind panel just landed — I'll verify its seal and run the registered pass.
Load is above the shared-machine threshold, so the sealed runner will wait for a quiet slot before starting the suite run.
All registered runs are complete — now I'll verify the seals and write up the results.
**Verdict: registered FAIL on the M1 bar only — agreement 87/90, bar 90/90.** M2 PASS, M3 PASS, M4 PASS. No sealed file changed (own seal 3/3 OK, 280m 12/12 OK, panel 2/2 OK after the runs). No re-seal, no silent re-runs, no agent code change.

Marks table (integer counts, 73 dialogs, 90 turns, one run per arm):

| mark | result |
|---|---|
| M1 ability 280m vs 280b | 25/25 |
| M1 teach 280m vs 260 | 8/8 |
| M1 called 280m vs 281 | 12/12 |
| M1 smalltalk 280m vs 282b | 25/25 |
| M1 mixed, mechanical owner (280b: 5, 260: 5) | 10/10 |
| M1 control 280m vs 260 | 7/10 |
| M1 total | 87/90 = FAIL (bar 100%) |
| M1 overlaps | 0 (bar 0) |
| M1 280m writes on question turns | 0 (bar 0) |
| M1 280m writes on smalltalk turns | 0 (bar 0) |
| M1 store diffs 280m vs 260 | 0 |
| M1 old-sheet scan hits on 280m | 0 (director claim check) |
| M2 sessions152 moves | exactly 3, reply-only, 0 write changes (predicted ids S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9) |
| M2 bench / rt136 (145 rows) / rt143 (124 rows) moves | 0 / 0 / 0 |
| M2 gates vs 260 | identical (sd clean; rt136 NOT-clean on both, same inherited counts; vs-138j labels identical) |
| M2 verifier probes | vp exactly N06+E04, supp 0 = PASS |
| M3 smalltalkpanel234 (56 items, once each) | wellbeing 280m 17/20 vs 260 16/20, other 36/36, 0 writes, 0 diffs = PASS |
| M4 notebook-zero | 0 diffs = PASS |

Every move / every miss (ids only, never item text): the only 3 misses are `ct00#1`, `ct01#1`, `ct04#1` (control, fixed owner 260, turn 1 of 2-turn dialogs). Measured mechanically from the recorded rows: on each, only 281's reply differs from 260's (260 == 280b == 282b), and 280m is byte-identical to 281; write counts 0 on all arms; stored triples identical (teach triple preserved); no CAN-line text on any arm. So all 90 turns equal some piece arm, and no turn had 2+ parts differing. The mechanical mixed rule worked: 10/10 mixed (the ability-led shape that sank 280m is now owned by 280b). Called items: scorer-side 12/12 agreement; right/wrong and claim checks are the director's from `run/panel-280m.json` + `run/panel-score280n.json` + per-arm run files.

Deviations: none from protocol. Panel sealed ~4 min after my seal (inside 120 min); seal checked 2/2 OK before the single run. Mock pre-seal: PASS 8/8 exit 0; overlap mock FAIL 8/9 exit 1 with overlap id; empty-text exit 4; schema-mismatch exit 3; sealed-runner loader 7 dialogs / 8 turns. Sealed M2 runner waited on machine load internally (518 s total). One standing-rule conflict: the task's PUSH line asks for pushes, but the rules forbid commits/pushes, so nothing was committed or pushed; all files (`artifacts/claude-join280n-20260923/`, `scripts/claude_join280n_*`, `scripts/claude_280n_*`, ledger with P280n.1–P280n.5) are in place in the worktree. Predictions: P280n.1 figure wrong (87 not 100), its 0-overlap/write/scan parts right; P280n.2 right exactly; P280n.3 right; P280n.4 bar-miss clause tripped on the 3 controls.

What it means (plain high-school English): the join behaved exactly as built on all 90 fresh turns — every reply came from one of its parts, nothing extra was written or memorized. The new counting rule fixed last time's mixed-turn problem. What failed is again the prediction of who owns a turn: 3 control turns use called wording, so the called-question part answers them while the plan said the base would.

What it doesn't mean: the join learned nothing new and broke nothing old — frozen tests match the base except the 5 pre-approved moves, small talk improved slightly, zero turns had two parts fighting, and no sealed file (280m included) was touched.
