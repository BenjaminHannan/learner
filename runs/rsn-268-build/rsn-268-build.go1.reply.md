Building the n-hop guard — reproducing the bug, then verifying the fix.
I've mapped the bug's cause. Now I'll examine the failing cases to design the guard.
Now let me set up tracking and check remaining interfaces.
251 is a sibling experiment, not in my lineage. Now let me look at the repro/probe driver pattern.
Interfaces clear. Writing my dev repro driver (36 dev + 34 own dialogs, fresh agent per dialog).
d18 abstains on 138m (DIAG studied 138n — different lineage). Let me check the 153 fallback layer's coverage before building.
Now checking whether the B73 explicit composer could also claim these reverse questions after the guard.
Checking how drivers load agent modules, then building.
Now writing the guard.
Guard selftest passes. Now the agent file.
Agent builds. Running the dev pilot on 268.
Load is 106 — waiting before heavy suites. Meanwhile, writing the supplemental founder dialogs (new file, fixed possessive phrasing).
Supp confirms the pattern. Waiting for load to drop before the heavy M2 pilot.
Load is down. Running the M2 pilot (frozen suites vs 138m rows).
M2 pilot: 0 moves, GATE clean on sessions152/bench/marks123. Now rt136 + rt143.
Exactly 138m's set. Direct row compare vs 138m's saved rows next, plus rt143.
268 is byte-identical to 138m on all 145 rt136 rows. Now rt143.
rt143: 0 moves. Checking probe file formats, then M3 pilot.
M3 restart files: rows identical on all 5. Now the verifier probes.
M3 pilot clean (0 changes, 110 dialogs). M4 latency pilot next.
M4 pilot: −0.01 ms. Now the full turn-by-turn diff of dev rows (138m vs 268) to enumerate every move.
All 21 dev moves characterized (0 teach/triple changes). Checking what 138m's seal covered, to mirror the protocol.
Protocol clear. Writing the registered driver and scorer.
Checking actual output structures before finalizing the scorer.
Now generating the dialog definitions and predictions files from pilot evidence.
Writing PASSMARKS.md.
Validating the scorer against pilot outputs in a mock run layout.
Scorer validates. Sealing now.
Sealed and ledger appended. Starting registered runs.
Registered DEV/M2/M3/M4 all PASS. Verifying seal integrity and no errors.
Panel is available. Copying the folder unchanged.
138m rerun reproduces the writer's base exactly (46/0/0). Running the 268 arm once.
Identical totals. Verifying row-by-row whether the guard fired anywhere on the panel.
All 70 per-item identical. Writing RESULTS.md.
Verdict: **FAIL** — on M1 bar 1 only (`reverse_chain` 10/24, bar ≥ 22/24). Every other clause of every mark passes.

Marks table (integer counts, 138m beside every figure):

| mark | 138m | 268 | bar | verdict |
|---|---|---|---|---|
| M1 reverse_chain right /24 | 10 | 10 | ≥ 22 | **FAIL** |
| M1 reverse_chain wrong /24 | 0 | 0 | 0 | pass |
| M1 reverse_nochain kept (4 right) | 4 | 4 | keep all | pass |
| M1 uncued_reverse /8 | 8 | 8 identical | 8/8 ident | pass |
| M1 forward_chain /12 | 12 | 12 identical | 12/12 ident | pass |
| M1 forward_1hop /10 | 9+1 miss | identical | identical | pass |
| M1 abstain /6 | 3+3 miss | identical | identical | pass |
| M1 wrong /70, writes /70 | 0, 0 | 0, 0 | 0, 0 | pass |
| M1 per-item rows identical /70 | — | 70 | — | pass |
| DEV moves (predicted by id) | — | 21/21 exact | exact | pass |
| SUPP moves (predicted by id) | — | 3/3 exact | exact | pass |
| DEV+SUPP teach/triple changes, new wrong | — | 0, 0 | 0 | pass |
| M2 suites moves (sessions152/bench/marks123) | — | 0/0/0, GATE clean | 0 | pass |
| M2 rt136 labels | — | C019–C031+C076+C079 (15) | exact | pass |
| M2 rt136 direct rows vs 138m (145) | — | 0 moved | [] | pass |
| M2 rt143 moves/flips (124) | — | 0/0 | 0 | pass |
| M2 forward n-hop moves | — | 0 | 0 | pass |
| M3 restart probes equal (5 files) | — | 5/5 | 5/5 | pass |
| M3 verifier diffs (98+12) | — | [] / [] | [] | pass |
| M3 ghosts / dup fails / write changes | — | 0/0/0 | 0 | pass |
| M4 median delta | — | −0.003 ms | ≤ +5 ms | pass |

Every move (dev 21 + supp 3; panel 0): to 190 gold (4: d01, d03, d29, o02); to "Was that a question?" (2: d02, d04); to 190 honest decline (3: d05, d06, o04); to honest abstain (7: d11, d12, d16, o01, o20, o28, o29); to true 153-wording fact (5: d33, d34, o09, o15, o18); supp p01 abstain, p02 153-wording, p04 abstain. 184/205 other dev turns identical, incl. all teaches and the d13/d17 over-walks.

Every miss: the 14 non-right reverse_chain panel items (12 at stage `none`, 2 at `bench73`) plus the baseline misses both arms share (reverse_nochain 6, forward_1hop n268-060, abstain n268-066/067/068).

Deviations: D1 — post-seal new driver `scripts/claude_268_panelrun.py` only (panel arrived after seal; sealed files untouched, seal re-verified 18/18 OK; panel seal 5/5 OK). D2 — o11/o13/o25 broken teaches kept as RECORD, repeated as p01–p07 (pre-seal, in PASSMARKS). D3 — design doc's "12/12 flip to gold" (proposed on 138n, never built) measures 4/12-to-gold on the 138m base; stated pre-seal. One run per arm, no re-runs, no re-seal, no item quoted.

Diagnosis (one note): stage census shows **zero** reverse_chain items at `loop138-nhop` on either arm (153-reverse 8 right, 190-reverse 2 right, none 12 miss, bench73 2 miss). The panel never presents a forward-walkable frame, so a frame-suppressing guard is provably a no-op there: 268 == 138m on all 70, and reverse_chain stays at baseline 10/24. No falsifier triggered (0 forward-fact answers, 0 forward changes, 0 new wrong values).

What it means: the safety switch works exactly as specified where the bug lives — 21/21 backwards questions stopped getting wrong forward answers, with zero side effects — but this blind test contained zero cases of the bug (base already 0 wrong), so the switch changed nothing and the 22/24 reach goal was missed.
What it doesn't mean: it doesn't mean the guard is broken, the base regressed, or any fact was mis-stored; nor does it mean all backwards wordings now get right answers — some still get honest non-answers, by design of the one-change fall-through.

Files left in the worktree for collection (no push per OPUS-RULES): `artifacts/claude-nhop268-20260923/` (PASSMARKS, config, predictions, SEAL, run/, RESULTS.md), `artifacts/claude-nhoppanel268-20260923/` (panel copy, seal OK), `scripts/claude_fix268_nhopdir.py`, `scripts/claude_loop268_agent.py`, `scripts/claude_268_devrepro.py`, `scripts/claude_268_supp.py`, `scripts/claude_268_runall.sh`, `scripts/claude_268_score.py`, `scripts/claude_268_panelrun.py`, ledger P268.1–P268.7 appended only.
