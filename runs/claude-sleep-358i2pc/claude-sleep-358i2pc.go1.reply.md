Starting the sealed 358i2 build — checking gates, passmarks, and BensPC status.
Duplicate check passed — now reading the sealed task spec and checking BensPC access.
GPU marker names this job — verifying no rival run before proceeding.
Workdir staged on BensPC — now verifying the 19-file seal.
Seal and Stage 0 pass — running required selftests.
Checks pass — launching loop seeds 1 and 2 on BensPC.
Quoting broke that probe — retrying with cmd tools that need no escaping.
Fixing the remote listing (no Unix tools in cmd).
Quoting misfire — retrying the process-tree query with the working pattern.
Parent chain confirmed — identifying the launcher.
Both pythons gone after the husk kill — checking GPU and logs.
Both seeds launched — verifying they survive and advance.
Detached launch returned PID 10348 — testing survival across session close.
Seed 1 survives detached — launching seed 2 the same way.
8.8 GB free ≥ 5 GB gate — launching seeds 3 and 4.
All 4 seeds running — waiting 15 min for the finish projection.
Halfway there, pace steady — waiting for the final stretch.
Seed 1 finished (60k steps, final.pt present) — sealing and evaluating it.
All 4 seeds at 60k — sealing the remaining checkpoints.
GPU free — evaluating seed 1.
Weights backed up — pulling all run files to the Mac.
Reference data located — dumping plain counts and building the scorer.
All marks computed — pulling remaining report fields.
All data in hand — checking ledger format before writing results.
Writing the sealed results file.
Files staged — releasing the GPU marker.
**Verdict: SUSPECT CONFIRMED** (V0, M1, M2, M3 all pass; proved-wrong not triggered).

Marks table (integer counts; plain = 358i's own runs/plain-s{1..4}/tests.json on origin/main):

| mark | rule | result |
|---|---|---|
| V0 validity | steps_block_nograd = 0 every seed | 0/0/0/0 of 60000 steps x4 — PASS |
| M1 speed | dev grids5@10k >= 100/200 on >= 3/4 seeds | 195/198/197/200, 4/4 — PASS (358i loop was 0/1/2/1) |
| M2 | mean loop−plain grids5 >= −10 | +1.00 (300.00 vs 299.00) — PASS (358i: −77.5) |
| M3 | mean loop−plain grids6 >= −10 | +51.75 (289.50 vs 237.75) — PASS (358i: −83) |
| proved-wrong | dev@10k <= 20 on >=3/4 AND gap <= −50 | 0/4 seeds; gap +1.00 — NOT triggered |

Gaps loop−plain (4-seed means, /300): sums4 +0.00, sums6 +100.50, sums8 +160.25, grids5 +1.00, grids6 +51.75, grids7 +55.00, numbers4 −0.25, numbers5 +0.00, sums10 +163.25, sums12 +138.00. 358t-style G0/G1/G2/G3 all met (report-only). 19/19 seal lines match; 4 checkpoints sealed (64 hex each) before eval; each eval ran exactly once per checkpoint; Mac weight copies re-hashed match; 0 weights in git; 19 files staged for the watcher to push (RESULTS.md, SEAL-run.sha256.txt, 16 run files, ledger line appended).

Every move/miss/deviation: (1) DUPLICATE gate clear (no RESULTS.md on either branch). (2) Machine BensPC per ADDENDUM-1, torch 2.11.0+cu128/RTX 5070 Ti; Stage 0 report-only, 0/12 both lines, did not stop. (3) GPU-BUSY.txt pre-existed naming this same job — proceeded, deleted at end; GPU idle now. (4) First seed-1 attempt died at ~11k steps when I killed its coupled parent process — my error; seed 1 restarted clean (only its partial scratch logs deleted), all accepted results from clean runs. (5) Detached launches via Win32_Process Create (PIDs recorded); seeds 1+2 ~2 min apart, 3+4 after the 5-min gate at 8.8 GB free; 15-min projection showed all finishing in cap, so no TOO-SLOW stop — all 4 conclusive (102.8/104.8/104.9/104.8 min). (6) Evals sequential after training; selftest/check-mask strings carried detail suffixes, accepted. (7) Disk 8.49 GB at start; $0; ~2.5 h of 8 h cap.

What it means in plain English: the autocast weight cache was the culprit — with it off, 358i's loop learns exactly as fast as plain (195–200 vs plain's 160–174 at step 10k) and the grid gap vanishes. What it doesn't mean: the loop isn't proven better overall — numbers4/5 sit at 0–2/300 on both arms (neither learned them), and plain ran on a different machine. 358d/358i/358x stay registered; they get an addendum, not a rewrite.
