Building the comma guard — reproducing the gap and testing the fix.
Load is 60.3 (above the 60 limit), so I'll do read-only exploration while it drops.
Load is 104 — machine is busy. Continuing with read-only review until it drops.
Load is 106 — too high for runs. I'll write all new files first (cheap), then wait for load to drop before any agent runs. Continuing read-only review:
All context gathered. Now writing the new files (additive only, no runs yet while load is high).
Load is dropping (20.9). Generating config and dev cases:
Config diff is exactly as designed. Load is 19.9 — running the dev pilot on both arms:
263 isn't saving on retry (except 1 case). Debugging with the actual pilot rows:
d263-001 works but d263-002 doesn't even trigger a retry. Checking what 260 stores there and debugging the 263 path directly:
Root cause found — two head behaviors: single-word openers parse (comma-subject teach → my guard works), multi-word openers fail to parse entirely (no teach, nothing stored). The retry must also trigger on save-failure, not just blocked teaches. Rewriting the fix:
Proven shapes found. Fixing my dev expectations (tunable pre-seal):
Dev: 263 55/55, 260 34/55 — gap reproduced and fixed. Now piloting suites + probes:
13 bench moves vs the 138m base — need to check whether these are 263-vs-260 differences:
15 bench units moved 263-vs-260. Inspecting what changed:
Need the full diff on these — checking whether the difference is turn-level or flake:
The guard over-fires on legit comma-names ("Washington, D.C."). Checking verdict-level impact 263-vs-260:
13 verdict flips — systematic. Examining the actual comma-subjects in these cases to find the distinguishing pattern:
All 15 are title/abbreviation names ("Washington, D.C.", "Tony Hall, Baron...", "William Morris, 1st Viscount...", "Hasbro, Inc."). The guard needs a name-internal comma exemption. Adding it:
Dev clean. Re-piloting suites with the exemption:
0 moves, GATE clean. Load spiked to 77 — waiting before rt136:
rt136: 0 moved vs 260. Now rt143 + verifier probes pilots:
Probes match 260's 7 changed rows exactly. Reading 260's full predictions to copy the probe values:
Probes match exactly. Writing predictions:
Piloting latency (1 pair, 1 rep) to confirm the bar before sealing:
Latency pilot +0.449ms — well within bar. All pilots done. Writing PASSMARKS.md:
Seal 13/13 OK. Appending ledger predictions:
Machine is heavily loaded (100–200). Checking whether runall survived the timeout:
Panel is sealed. Now waiting for load ≤60, then running the registered runall:
Dropping steadily. Continuing to wait:
Load 49 — launching the registered runall:
M2 PASS — 80/80, 0 moves. All marks complete. Writing RESULTS.md:
Verdict: **PASS** — exp 263, the comma write guard. M1–M4 all PASS, registered runs done once per arm with sealed scripts.

Marks table (integer counts, 263 vs base):

| mark | 263 | base | bar | verdict |
|---|---|---|---|---|
| M1 comma subjects over 60 | 0 | 16 (260 arm) | 0 | PASS |
| M1 unlisted_opener_teach exact | 20/20 | 1/20 | ≥16/20 | PASS |
| M1 comma_value_ok | 8/8, lost 0 | 8/8 | 0 lost | PASS |
| M1 question writes | 0 | 0 | 0 | PASS |
| M1 control byte-identical | 14/14 | 14/14 | 14/14 | PASS |
| M2 openpanel260 on 263 | 80/80 | 80/80 (260) | equal or better, 0 new junk | PASS |
| M3 suites moved units | 0 (rt136 145, rt143 124, sessions152 180, bench 4×200) | — | exactly predicted (0), 0 new WRONG/WRONG-WRITE/lost OK | PASS |
| M4 latency delta | +0.243 ms (1.859→2.101, n 624+624) | — | ≤ +3 ms | PASS |
| PROBES (reported) | 7 changed rows, exactly as predicted | — | — | PASS |
| Dev (tuned on, 55 dialogs) | 55/55 | 34/55 | — | — |

Every move (19, all toward right, 0 against): c263-001 … c263-019 (unlisted_opener_teach; 260 stored comma-junk on 001–016 and nothing usable on 017–019). 0 moves everywhere else: comma_value 8/8 both, control 14/14 both, openpanel260 80/80 both, suites 0 moved units, probes exactly the 7 predicted rows (B15:t0, B15:t1, D08:t1, D10:t0, D10:t1, E06:t0, E10:t0; stored B15+D10; 1 allowed new write B15:t0; supp 0).

Every miss: panel — 263 misses 10 appositive (c263-021…030, store_ok holds, gold not in reply; no bar) + 4 question (c263-043…046, gold not in reply; no bar), all also missed by 260. 260 additionally misses 19 unlisted (the moves above). No other misses. No abstain flips, so no 5× follow-ups.

Deviations (5): (1) retry also fires when the head never parses the opener turn (multi-word openers store nothing) — pre-seal, documented; (2) name-internal comma exemption (titles/ordinals/abbrevs) added after pilot showed 13 bench verdict flips on real names — 0 moves after; (3) first runall died in load-wait (load 130–209) before any step, re-invoked once, no step ran twice; (4) regscore263.json holds a cosmetic M2-absent error (M2 verdict in openpanel-score263.json); (5) no git push — OPUS-RULES forbids it; deliverables (artifacts/claude-comma263-20260923, scripts/claude_fix263_comma.py, scripts/claude_loop263_agent.py, scripts/claude_comma263_*.py, ledger) are in the worktree. Seal 13/13 OK, panel schema OK, 260-arm fidelity 60/60 vs base260.jsonl.

What it means: sentences starting with a never-seen opener ("yo", "get this", "real talk") now save the plain fact instead of junk like "Yo, Kestrel" or nothing; comma values, questions, and all suites/probes/timing are unchanged from 260.

What it doesn't mean: two-comma turns still lose the fact by design; unlisted-opener questions keep 260's didn't-understand reply; title-comma names pass through untouched; this was 60 panel items plus frozen suites, not every sentence possible.
