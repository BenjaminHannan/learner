Scoring the listener stack on the month-end bank — assembling your report-only run.
Found the lis-313 pattern — now tracking down the common rules to get the setup right.
I've got the ground rules — now mapping the e2e harness and bank.
Runner and scorer mapped — now checking the arms and pre-flight requirements.
Pre-checks show the earlier reader run hit memory limits — verifying the lane is clear before I start.
Lane is clear and panel is done — setting up the combined tree and checks.
The seal check failed on paths — inspecting the seal file to fix the invocation.
Checks passed — seal OK, model hash matches. Starting the three arm runs.
First arm failed on a missing dependency — checking how the earlier run invoked the reader.
Reader loaded and arm C is running — polling progress.
Nine of ten lives done on arm C — waiting for the final life, then launching arm S.
Arm S nearly done — waiting on its last life.
All three arms finished — now scoring.
Scoring complete — copying artifacts to the worktree and writing RESULTS.md.
REPORT: listener stack scored on the month-end DEV bank (report only, no marks). All three arms completed; nothing was edited.

Checks: DEV bank SEAL all 3 OK; lis301-merged safetensors sha256 matches `b4fd93a2…d21b890`; uptime load ~15–25 (below stop line, lis-314-panel had exited rc=0); disk 64 GB free → 59 GB free. One env fix, no code edit: first launch died with `ModuleNotFoundError: No module named 'transformers'` from the sealed reader, so I added `--with transformers --with safetensors` to the uv prefix (same prefix lis-311b used).

Counts (mechanical scorer, 194 user turns / 131 facts each arm):

| Arm | Confirm rows | Asks RIGHT (+RIGHT_CONFIRM) | Asks WRONG | Asks ABSTAIN | Facts saved | New triples | ms median / p90 / max |
|---|---|---|---|---|---|---|---|
| lisC (310 ask-back) | 75 | 10 (+0) | 2 | 51 | 49/131 | 50 (1 unsupported) | 2337 / 18182 / 76213 |
| lisS (+313+315+314) | 33 | 12 (+3) | 7 | 42 | 34/131 | 35 (0) | 2456 / 15025 / 64918 |
| lisG (+316 full) | 33 | 12 (+3) | 7 | 42 | 34/131 | 35 (0) | 2295 / 11787 / 48064 |

Deviations/notes: lisS and lisG are mechanically identical on every count except wall-clock ms — the +316 layer changed nothing on DEV (same replies, saves, asks). lisC asks the user more than twice as often (75 vs 33 confirms) and saves more facts mechanically (49 vs 34); whether the extra saves are right is for the blind judges. No arm wrote on nosave (0) or creative (0) turns; all day-1 saves kept to end (27/27, 19/19, 19/19). Slowest single turn 76 s — under the 5-min stop line. Device: Mac arm64, reader on MPS (float16), loop on CPU; timings noisy (shared Mac). Runs took ~25/19/19 min, inside the 150-min cap.

What it means in plain English: the full wrapper stack (S/G) asks fewer follow-up questions than the bare ask-back base but also banks fewer facts on this dev set; the top 316 layer made zero measurable difference here. What it doesn't mean: this says nothing about which saves are correct — the blind judge packets decide that — and nothing about the sealed TEST bank.

PUSH: `artifacts/claude-lis-e2edev-20260924` (RESULTS.md, run/arm_lis{C,S,G}.jsonl, scored/mechanical.json + judge/grammar packets; checksums verified identical to the run tree). Note: `artifacts/` is gitignored in this worktree — the watcher will need to pick up the PUSH path as with prior tasks.
