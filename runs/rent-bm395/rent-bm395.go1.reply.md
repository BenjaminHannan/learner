Starting rent-bm395 — fetching specs and checking gates.
Credit and duplicate gates pass — renting a 5090.
Wrong image name — checking the working one.
Instance running — uploading the code tree.
SSH key attached but auth fails — diagnosing connection.
Upload works via `vastai copy`. Now debugging SSH execution.
SSH still blocked — checking instance logs before rebooting.
SSH looks wedged on this instance. Destroying and renting fresh (rental 3).
SSH works on the fresh instance. Uploading and setting up.
Environment ready — downloading the two models.
Models downloaded, paths check out. Running seals and fetch.
Seals pass. Running fetch.
Fetch matches. Running self-test and smoke.
Self-test passes. Running smoke test.
Smoke passes. Launching both registered lanes.
Lane 2 failed to launch (wrong cwd — shell `&` chaining). Lane 1 is running. Relaunching Lane 2 with explicit cwd.
I mistyped the arm path — killing that process and relaunching correctly.
Both lanes running well. Monitoring progress.
All arms complete with 1986 rows each. Gathering final metadata before copy-back.
Copy verified — destroying the instance.
Files verified. Placing results and writing the report.
Verdict: RUN COMPLETE, all arms valid. E, E20 and Rb2 each have 1986 rows, both commands exit 0, seals OK. Scoring is not part of this task.

Credit number (CREDIT GATE): 7.063765917599895 — above $2.50, rented.

Counts:
| check | count |
|---|---|
| seal bm395 lines OK | 9 / 9 |
| seal bm390-code lines OK | 8 / 8 |
| fetch locomo_qa | 1986 |
| selftest PASS lines | 6 + BM395-SELFTEST PASS |
| smoke E / E20 rows | 5 / 5 |
| lane1 [bm395] lines | 10 |
| lane2 [bm390] lines | 10 |
| locomo_E rows | 1986 |
| locomo_E20 rows | 1986 |
| locomo_Rb2 rows | 1986 |
| rentals used (limit 4) | 3 |
| spend of $1.00 budget | ~$0.47 |

Moves: fetched main + builder-outbox; duplicate gate clear (no run dir, no RESULTS-rent, no live rent-bm395). Rental 1 (wrong image, never ran, $0.00) destroyed. Rental 2 (SSH tunnel wedged, key attached but proxy denied, reboot failed) destroyed ~$0.10. Rental 3 (RTX 5090, $0.5659/h) did the whole job, destroyed 20:57:51 UTC, confirmed gone. Tree uploaded, pip + pyarrow only, BASE 87179e5c… + MiniLM exact path verified, torch 2.8.0+cu128 / transformers 5.17.0. Fetch line, selftest, smoke all match spec. Lanes overlapped on one GPU (lane1 20:38–20:54:53Z, lane2 20:40–20:47:15Z). Peak GPU mem seen 5823 MiB. Run files copied back, sizes + sha256 match box, then destroy, then ledger line appended. New files only: run/*.jsonl (3), RESULTS-rent.md. No file edited; no question/answer/reply opened, printed or quoted.

Misses/deviations: lane 2 needed 3 launches — (1) cwd bug died instantly with "can't open file '/root/scripts/claude_bm390.py'"; (2) my typo used a placeholder model path, failed fast with offline OSError; (3) correct launch is the registered run. `ps` checked before each retry; lane 1 untouched; no command ever ran twice. Lane starts ~2 min apart, still fully overlapped. Exit codes 0 are inferred from normal completion (wrote lines, no traceback), not captured via wait. Account credit fell $7.06 → $5.65, but siblings billed the same account concurrently; this task's metered share is ~$0.47.

What this means in plain English: the GPU experiment ran exactly once as registered — the 1B model answered all 1986 test questions three ways (memory-store top 10, top 20, BM25 top 10), and every output row is saved and verified. Whether the memory store actually answers better is decided later by the unchanged scorer, not here. PUSH: artifacts/claude-bm395-20260925/RESULTS-rent.md, artifacts/claude-bm395-20260925/run, artifacts/fable-predictions-ledger.md.
