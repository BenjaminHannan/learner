Building the 282b follow-up — setting up and reading the brief.
Rules read and base context loaded. Now studying the 282 base code.
Now looking at the helper APIs and how entities/relations are detected.
Base study done. Checking relation surfaces, assistant name, and 282's saved suite rows.
Design is clear. Updating the plan and starting the build.
Now the dev cases generator — 65 dialogs in my own wording.
Now the panel runner with the strict schema gate.
Now the scorer.
Now the M2 reg scorer and the two driver scripts.
Classifier works. One gap: "see ya soon" has no class word. Moving `soon` to close-class (safe: only affects all-vocab turns).
Mechanism works ("yo sup man" moves only on 282b). Running the dev pilot on both arms.
Load is 62.4 — above the 60 threshold. Waiting before the second arm.
64/65 — one bad expectation of mine (single question turn can't store). Fixing the dev case to include the teach.
Dev 65/65, 18 moves, no problems. Promoting the clean re-run into pilot and verifying suite base files exist.
Pilot M2 PASS — 0 moves everywhere, probes 0 changes. Now the mock-panel end-to-end test.
End-to-end PASS. Adding an empty-text guard to the scorer gate too, then negative tests.
All gates verified. Writing predictions and PASSMARKS.
Seal 12/12 OK, ledger P282b.1–3 appended. Running registered M2 now.
Registered M2 PASS. Now waiting for the panel seal (poll 2 min, up to 120 min).
Panel seal is present. Running the registered M1+M3 panel script.
M1 30/35 (bar 32) — FAIL; M3 PASS. Analyzing misses mechanically (ids only, no text) and re-verifying the seal.
Writing RESULTS.md and the outcome ledger line.
VERDICT: registered FAIL on M1 only — writer greeting+closing fitting 30/35 on 282b (bar 32/35), 2 turns short. Everything else PASS. No sealed file changed (seal 12/12 OK after the runs); no re-runs; panel never read item by item, no item quoted.

Marks table (integer counts, 282 beside 282b):

| mark | 282b | 282 | bar | verdict |
|---|---|---|---|---|
| M1 writer greeting+closing fitting (35 turns: greeting 20, closing 15) | 30 (greeting 15, closing 15) | 19 (greeting 10, closing 9) | ≥ 32 | FAIL |
| M1 writes on greeting+closing, 282b | 0 | — | 0 | PASS |
| M1 question writes, 282b, whole panel | 0 | — | 0 | PASS |
| M1 mixed+control exact vs 282 (25 turns) | 25/25 | — | 25/25 | PASS |
| M1 store diffs | 0 | — | 0 | PASS |
| M2 sessions152 (180 units) | 0 moves, GATE clean | — | 0 | PASS |
| M2 bench (4×200) | 0 moves, GATE clean | — | 0 | PASS |
| M2 rt136 (145 units) | 0 field diffs, labels identical to 282's | — | 0 | PASS |
| M2 rt143 (124 rows) | 0 diffs | — | 0 | PASS |
| Probes vp (98) / supp (12) vs 282 rows | 0 / 0 changes | — | 0 | PASS |
| M3 wellbeing (20 items) | 17 | 17 | ≥ 282 | PASS |
| M3 other 36 items same, 0 writes, 0 diffs | 36/36, 0, 0 | — | all | PASS |
| Dev (65 dialogs, 79 turns, my wording) | 65/65 | — | n/a | — |

Every move 282→282b (11, all turn 0, ev 0→0, all toward the head's canonical reply): d_greet_07, d_greet_12, d_greet_15, d_greet_17, d_greet_18, d_close_03, d_close_08, d_close_09, d_close_12, d_close_13, d_close_14. Every miss (5, all greeting, all byte-identical to 282 — the layer added nothing on them): d_greet_08, d_greet_16, d_greet_20 (identical non-fitting fixed reply on both arms, equal to none of the arm's probe replies), d_greet_13, d_greet_14 (abstain on both arms). 0 new wrongs, 0 new abstains vs 282. Dev moves (18): d282b-002/007/009/010/011/013/014/015/016/017/018/021/026/036/037/038/039/040 turn 0. Changed replies live in: artifacts/claude-small282b-20260923/run/panel-282b.json (11), pilot/dev282b.json (18); st234/vp/vs runs changed 0 replies.

Deviations: (1) st234 run only once (registered run), as required; (2) listed smallpanel282 filenames only during orientation, never contents; (3) dev pilot ran twice pre-seal over my own bad store expectation (fixed, re-ran 65/65, 0 problems); (4) mock-panel end-to-end test in /tmp pre-seal incl. `user` key, empty-text refusal (exit 4), SCHEMA-MISMATCH (exit 3); (5) no abstain-ward flips so no 5× follow-ups; (6) panel seal present on first poll (2/2 OK), load < 60 and disk > 11 GB throughout; (7) ledger appended P282b.1–4; additive-only kept (all 282b files new, seal 12/12).

What it means (high-school English): the agent got friendlier without breaking anything real — casual hellos/goodbyes with extra words now get normal replies, up from 19 to 30 of 35, closings a perfect 15/15, and every change was a gain with zero regressions. But 5 greeting wordings behave exactly as before, so it missed the 90% bar by 2.

What it doesn't mean: it doesn't mean the idea failed — M2, probes, and M3 all pass with literally zero changes — but greetings only reached 15/20, and this was one 60-turn blind panel plus the frozen suites, not every sentence anyone could type.
