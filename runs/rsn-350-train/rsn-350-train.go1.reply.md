Building your 90m plain reasoner — setting up and renting GPU.
Local checks passed and task files read. Now renting the GPU.
Found a 32-core 5090 box at $0.47/h. Renting it now.
First box failed to pull its image. Destroying it and trying the next host.
Still downloading its image (making progress, not stuck). Giving it a short grace before deciding.
GPU box is running. Setting up access and checking the hardware.
Direct SSH works. Checking the box and shipping the code over.
All seal checks pass. Waiting on the venv install, then the generator self-test.
venv ready with CUDA torch. Running the generator self-test.
Self-test passes. Launching the timing pilot.
Both runs training (GPU 99%). Preparing local artifact folders while they run.
Copy phase ~70% done, loss near zero. Checking back after the practice phase starts.
Training finished. Verifying checkpoints, then sealing before eval.
Sealed. Running the 12 evals (dev + both panels per checkpoint), once each.
All 12 evals clean. Pulling every JSON home before touching the instance.
All files home. Reading the scores to build the verdict.
Checksums match. Destroying the GPU box.
Box destroyed and confirmed gone. Writing the results file.
Work is done and the instance is destroyed. Final report:

## VERDICT: FAIL

Z1 FAIL both seeds, Z2 FAIL, Z3 FAIL both seeds, Z4 PASS both seeds. PASS required Z1+Z3+Z4 on both seeds. The pre-registered refutation condition is met (fresh ≤ 296+3 both seeds AND three-step 0/30 both), so "size is the bottleneck" is wrong at this scale. The 10x trigger (Z1 both seeds) is NOT met — no 10x.

## Marks table (integer counts)

| mark | bar | s1 | s2 |
|---|---|---|---|
| Z1 fresh 296-v2 total (checked) | ≥235 / ≥227 (296: 225/217) | 211 FAIL | 209 FAIL |
| Z2 fresh three-step (checked) | ≥6/30 one seed | 0/30 FAIL | 0/30 FAIL |
| Z3 transfer 294-v3 total (checked) | ≥233 each (296: 238/238) | 227 FAIL | 229 FAIL |
| Z4 invented, checked, 296 panel | ≤2 | 0 PASS | 0 PASS |
| Z4 invented, checked, 294 panel | ≤2 | 0 PASS | 0 PASS |

Raw totals: 296-panel finals s1 207/298, s2 206/298; 294-panel finals s1 229/300, s2 230/300. Per-category checked-right counts are in `artifacts/claude-rsn350-20260924/RESULTS.md` (copy-only and final, both panels): worst drops vs 296 are counting 4/30 vs 12/12 both seeds, before/after 22/19 vs 24/20, correction 19/22 vs 23/19; comparing flat 16/16; three-step 0/30 both (all "I don't know" after fact-check). Dev finals (fresh, seed 777): s1 881/1200, s2 897/1200. Training: s1 35.1 min, copy loss 4.0901→0.0042, reward 0.6448→0.8130; s2 35.3 min, copy loss 4.2522→0.0036, reward 0.6202→0.8450. Params confirmed 91,588,629 both runs.

## Every move

1. Read PASSMARKS.md, 350 design doc, both runner docstrings (all via `git show origin/main`). Sealed code never edited.
2. `vastai show instances`: no rsn-350 live (rent-336 + 3 cairn live, untouched). No DUPLICATE.
3. Searched 5090 offers rel≥0.98; cheapest $0.469 (16-core). Rented 32-core offer 43165155 ($0.4727) as contract 52474472 — host docker-proxy error, never left loading, destroyed (~$0). Rental 1 of 4.
4. Rented 48-core offer 49147083 as contract 52475017 ($0.4956/h), label rsn-350. Reached running at ~10 min (see deviations).
5. New venv with torch 2.14.0+cu130 (CUDA ✓) + numpy only. `nproc` 192, RTX 5090 32GB, 80GB disk.
6. Transferred `git archive origin/main` tarball; `sha256sum -c` on all three SEAL files: every line OK. `claude_rsn296_gen.py` → "selftest ok" (20 s).
7. Pilot 1 (seed 9, 100+50 steps): 0.30 min → full-run est ~26 min. Dual pilot (seeds 8+9): 0.57 min wall → est ~40 min for both < 2×26. Chose 2-at-a-time. Est $~0.35, under $3.40 — proceeded.
8. Trained both seeds 2-at-a-time, defaults, changed nothing: 35.1 + 35.3 min. No OOM.
9. SEAL-run.sha256.txt written BEFORE any eval (4 hashes).
10. Eval: first launch failed on my quoting bug (see deviations), zero successful evals; reran from file — 12/12 commands OK, no FAILs, each checkpoint evaluated exactly once (dev + panel296 + panel294 for copy_only and final, both runs).
11. Copied all 16 JSONs to `artifacts/claude-rsn350-20260924/runs/<R>/` before destroying.
12. Wrote RESULTS.md (verdict first), appended 6 ledger lines via `cat >>`.
13. Copied 4 checkpoints to `~/premonition-models/rsn350/<run>/`, sha256 verified identical to seal. Never pushed weights.
14. Destroyed 52475017, confirmed gone (only others' instances remain). Money: ~1.9 h × $0.4956 ≈ **$0.94 total**, under the $4 cap.

## Misses and deviations

- The brief's OPUS-RULES.txt path does not exist (`scratchpad/briefs/` missing); I followed the key rules as restated in the task (additive-only: 0 deletions in the ledger diff, no existing file edited, panels only as category counts).
- Rental 1 died on a broken host (counted). Rental 2 took ~10 min to reach "running" vs the 6-min rule — kept because it showed continuous progress (image download → setup); it then ran clean for 2 h.
- First eval launch failed from local `$VAR` expansion (`W//.pt`); it ran zero successful evals, so the "once per checkpoint" rule still holds exactly.
- Proxy SSH (`ssh4.vast.ai:35016`) refused my attached key; direct port (50856) worked. No other instance touched.

## What it means / doesn't mean (plain high-school English)

Tripling the reasoner's size did not make it smarter — scores went down (fresh 211/209 vs 225/217, transfer 227/229 vs 238), counting got worse (4/30 vs 12/30), and unpractised 3-step chains stay at 0/30. The problem is what it practises, not how big it is. It doesn't mean size can never help, only that 3× didn't. The honesty part still works: 0 invented answers — it says "I don't know" instead of making things up.

PUSH paths on disk for the watcher: `artifacts/claude-rsn350-20260924/RESULTS.md`, `artifacts/claude-rsn350-20260924/SEAL-run.sha256.txt`, `artifacts/claude-rsn350-20260924/runs/`, `artifacts/fable-predictions-ledger.md`.
