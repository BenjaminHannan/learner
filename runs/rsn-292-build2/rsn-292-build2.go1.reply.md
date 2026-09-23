Resuming the 292 builder — picking up drafts and finishing the merge.
Drafts are in place — now verifying the merge pieces and specs.
Pieces confirmed and blind panels sealed — now smoke-testing the build.
Found a build check failure — diagnosing the ears wiring.
Root cause found — the check looks at the wrong ears object. Fixing the draft.
One check fixed, another guard failing — tracing the install order.
Install-order bug confirmed — moving the guard install after imports.
Build is green — now gathering piece predictions for pass marks.
Core interactions confirmed — now checking chain and reverse shapes.
Load is high — parking the pilot to wait for a quiet slot, then running it.
Pilot is queued behind load — polling until the machine frees up.
Load still saturated — verifying scorer interfaces while waiting.
Pilot finished — reading the results.
Suites look clean — confirming move sets match the base exactly.
Yes/no moves match predictions exactly — now checking probes.
One probe move needs stability testing — running it five times.
The reader claims more shapes than documented — reading its parser.
Pilot decoded — now fixing two draft bugs and writing the final files.
Amendment recorded — writing predictions and pass marks.
Seal verified 10/10 — appending predictions and launching registered runs.
Corr scorer exited 3 — inspecting whether it's a schema void.
Corr rows miss sealed fields — reading the panel's own runner to mirror it.
Fidelity holds on three panels — writing the schema-conformant corr runner.
Registered suites match the pilot — verifying every move id.
Probe diffs are just labels — checking the rt136 move sets.
All marks confirmed — redoing the void corr panel runs.
291 fidelity is exact — running the 292 arm.
Corr is byte-identical — saving records and launching M5.
Arms ran once each — the scorer just needs its flag interface.
292 takes 73/80 with zero wrong — running per-item bar checks.
All M5 bars pass — filing records and results.
**Verdict: PASS (M1–M5 all pass).** Merge 292 = 291 + 266b lift + 268b guard + 293 reader is done, sealed (10/10 OK), registered, and reported. Fresh mix panel: 292 gets 73/80 with 0 wrong (base 291: 35/80).

**Marks table (integer counts, registered CPU runs)**

| mark | counts |
|---|---|
| M1 chain (70): fidelity 266b 67/70 exact families | right_lost 0, new_wrong 0, new_write 0 |
| M1 nhop (60): fidelity 268b 55/60, bug 11/16 + 1 wrong | 0 / 0 / 0 |
| M1 yesno (85): fidelity 293 85/85, 0 wrong/writes | 0 / 0 / 0 |
| M1 corr (96): fidelity 291 table 73/96·17·3·1 exact; 292 identical 96/96 | right_lost 0, new_wrong 0 |
| M2 suites vs 291 | sessions 0 moves; bench 0; marks123 1 reply-only (rt81 D_q_vs_s-04 OK→UNCLEAR); rt136 set == 291 (21 inherited) 0 new; rt143 2 (M3 Q2→Yes, O5 Q2→IDK); GATE clean |
| M3 probes | restarts 0 moves (36 turns); verifier 1 reply-only (N02 rows[1] Q2→honest IDK, stores identical, stable 5/5); 0 ghosts/dups/bad-writes |
| M4 latency (3×208 turns) | +0.53/+0.41/+0.61 ms (bar +5) |
| M5 mix (80, once/arm, sealed scorer) | 291: 35/0; 266b: 24/10; 268b: 29/6; 293: 44/8; 292: 73/0/7miss; union-right 56, lost 0; wrong beyond 291: 0; controls 24/24 identical; writes 0; mixed 9/12 (no bar) |

**Every move:** M2 D_q_vs_s-04, M3, O5; M3 N02-rows[1]; all predicted exactly in predicted_moves292.json. No other case moved anywhere; every miss is an honest abstain, never a guess.

**Deviations (sealed files never edited post-seal; seal re-verified 10/10):** D1 corr first ran under the wrong runner (7-field rows → sealed scorer SCHEMA-MISMATCH exit 3, VOID ×2, rows kept); redone with new post-seal mirror driver scripts/claude_292_corrarm_run.py. D2 m5.sh called the mix scorer positionally (exit 2, scoring VOID; once-per-arm rows valid); rescored with sealed --panel/--rows/--base flags, exits 0. D3 five pre-seal draft fixes disclosed in PASSMARKS.md (agent _check ears object; 268 install order; runall tally --out; score rt143 arrays; design pilot amendment for the N02 lift interaction). No fix292_glue needed.

**What it means:** one agent does all four jobs — chain asks 12/12 (were 0), yes/no 14/14 (were 0), keeps every backwards answer and correction behavior, 0 writes on any question turn, 56/56 piece-right items kept.

**What it doesn't mean:** yes/no about a chain still passes through unanswered by design; the 268b employer-shape hole travels along; the 17 corr wrongs are inherited from the parents (verb-wording denials fail on every arm); the mix panel can't show 268b's guard effect (no backwards item reaches the n-hop frame on 291).

Ready to push: artifacts/claude-merge292-20260923 (incl. PASSMARKS, predicted_moves292, SEAL, run/, m5-check, RESULTS), scripts/claude_loop292_agent.py, scripts/claude_292_corrarm_run.py, scripts/claude_292_panelrun/score/runall/m5run/m5, design/v3/30-modes/292-merge-muse.md, artifacts/fable-predictions-ledger.md (P292.1 + P292.2 appended).
