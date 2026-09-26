Sealed rerun — checking credit and duplicate gates before touching GPUs.
Gates pass — no duplicates, credit OK. Renting a GPU now.
Gates pass. Renting the cheapest 5090 now.
Host failed to pull the image (registry proxy error). Retrying start on the same instance.
Host can't pull the image — destroying and trying another host (rental 1 failed, ~$0.07 spent).
Both failures were the same broken host (410852). Renting on host 406325 (KR, where a healthy 5090 already runs).
This host is provisioning properly. Waiting for SSH.
SSH up on RTX 5090. Checking env and shipping sealed code.
Selftest ok. Downloading the pinned BASE snapshot (same files as dl-2).
BASE ready. Launching the registered run detached.
Launch never ran (bad local workdir). Relaunching with cd in the remote command.
Run is live (PID 583). Verifying old rentals are gone, then monitoring.
Fast pace — 3 S nights in 22 min. Continuing to monitor.
K pace is fast (~2.4 min/night). ~6 nights left, projecting finish ~15:40 UTC, inside budget.
One night left. Waiting for completion.
Run finished. Copying results back now.
Verdict FAIL computed. Destroying the rental now to stop billing, then writing the report.
Rental gone. Checking how prior results were pushed before writing mine.
Checking the sealed code didn't move under me while the run was going.
Sealed code identical across the main move. Writing the report.
No clobber — only my line differs. Committing and pushing.
Push is blocked in this environment — committing locally (the watcher has carried results before when a builder couldn't push).
**Verdict: FAIL.** F3, F4, F5 pass; F1, F2 fail. Not inconclusive, proved-wrong false.

Integer counts (base TEST lucky 59, reached 37, greedy 4; HARM right 200/300; pool 880):
- F1: K night-7 lost 6, 19 (sum 25) vs S 16, 17 (sum 33). Needs sum ≤ 16 (0.5×33) and each K < each S — 25 > 16; s7 19 > 16 and > 17. FAIL.
- F2: K nights lost > 10: 4 of 14 (K s6: 4,5,7,9,3,8,6 = 0; K s7: 4,9,8,12,19,16,19 = 4). Needs ≤ 1. FAIL.
- F3: K final lucky 208, 298 ≥ 118 (2×59) each; gains K 388 ≥ 0.8 × S 419 = 335. PASS.
- F4: 0 of 14 K nights > 15% below prior night. PASS.
- F5: K final reached 64, 59 ≥ 37. PASS.
- Proved-wrong (K ≥ S both seeds): s6 6 ≥ 16 no. False.
- Noted: K held KL drift at 0.031–0.035 vs S 0.175–0.186, but did not cut forgetting.

Run facts: RTX 5090, 84.7 min, selftest ok, sealed code unmodified (byte-identical across a main move mid-run), BASE = pinned 87179e5c snapshot, commit ba72f9b5. Spend ~$0.99 of $1.20 (r3 exact $0.823 for 1.634h × $0.5037; r1 ~$0.09, r2 ~$0.08 estimated). Rental destroyed, confirmed gone, 0 claude-fixsleep-dl4b live. Credit at gate: 5.487064616269862.

Deviations (every one):
1. 3 rentals, not 1: rentals 1–2 (52756261, 52757337, both host 410852) never started — host's docker registry proxy refused the image pull; destroyed, ~$0.17 sunk. Rental 3 (52758310, host 406325 KR) ran clean.
2. transformers==5.17.0 pip-installed on the rental (stated need; runtime image ships torch 2.8.0+cu128 but no transformers) — same version as dl-2/dl-3.
3. Credit NOT re-checked before re-rents (gate checked once at 5.49).
4. PUSH incomplete: results committed locally as 62ffcff47 on top of origin/builder-outbox in worktree /tmp/dl4push (files: gpu/dl4_results.json, gpu/anchor_pool.json, gpu/log.txt, RESULTS-gpu.md, ledger line), but `git push` is denied by environment rule. Same files + ledger line also present in the card-experiment-handoff worktree for the watcher to carry (dl-3 precedent).
5. "[dl4] S s6 night 1" appeared at ~37 min (inside the 45-min TOO-SLOW line, but noted).
