# Kit sleeph6r: rent one vast card for dir-h6 (sleep length, arm B)

Helper H7, 2026-09-28. Built from the `sleep358n3r` pattern. Everything here is NEW; no existing file was changed. Nothing has been rented, and no vast key or `~/.config/vastai/` was read or printed. The jobs are HELD; the Director releases them.

## What it does (plain words)
One rented GPU runs dir-h6: four seeds (13 to 16), each on one of 358u's loop checkpoints, arms N, S, L and B, 3 nights. The B arm is the long night (6,000 steps) with only the learning rate lowered to 1.5e-6. A Mac-side guard watches the money and the clock, saves progress to the Mac every 30 minutes, and at the end copies the results back, checks them against a sha256 list made on the rental, and only then destroys that exact rental.

## Files
| File | Job |
|---|---|
| `vcommon.sh` | shared values and helpers (limits, `bounded`, `copy_back`, `destroy` and `stop_inst` that refuse ids this task did not create) |
| `offers.py` | offer search: best TFLOPS per $/h, fit check |
| `vstart.sh` | the start: refusals first, then rent, guard, uploads, braces launch |
| `vguard.sh` | the Mac guard: 5 minute checks, 30 minute snapshots, ends on DONE, FAILED, BUDGET-STOP, TIME-STOP, STALL, PRELAUNCH-STOP, HOST-FAIL |
| `vcollect.sh` | puts the copied-back files in `artifacts/claude-dir-h6-sleeplen-20260928/{runs,run-vast}/` and writes `COLLECT.txt` (no scores) |
| `box/drive.sh` | runs ON the rental: torch check, seals, checkpoints, smoke, four seed runs |
| `box/halt.sh` | runs ON the rental: stops the runs by exact pid before the copy-back |
| `test/` | fake vastai, fake ssh, fake clock and `run-tests.sh` (see `test/README.md`, `test/OUTPUT.txt`) |
| `handoff/queue/h7-dirh6-1-start.md`, `-2-collect.md`, `-3-collect.md`, `000-bash-h7-dirh6-inputs.md` | HELD queue jobs |

## The rules it follows (where each is)
- torch pinned to 2.11.0 (cu128) and recorded: `box/drive.sh:25-30` (fails closed if torch < 2.11, no CUDA, or compute capability < 8.0).
- Offer search: `QUERY` at `vcommon.sh:34` (compute_cap >= 800, cuda_max_good >= 12.8, reliability >= 0.98, one GPU, >= 24 GB), ranked by TFLOPS per $/h in `offers.py`.
- Fit check: estimate x $/h <= 0.8 x money stop: `FIT` at `vcommon.sh:46`, applied in `offers.py`. Money stop `CAP_STOP=3.00` (`vcommon.sh:37`), hard cap 4.00.
- Guard state is written before any long remote call: `vstart.sh` writes `$G/state` and starts the guard as soon as ssh answers, before the uploads.
- Braces launch: `LAUNCH_CMD` at `vcommon.sh:59`.
- Checkpoints saved during the run: the guard's 30 minute snapshots (`SNAP_EVERY`, `vcommon.sh:54`). The h6 script writes its JSON only at the end of a seed and saves no weights, so what a snapshot holds mid-run is the per-night count lines in `W/sNN.log`, not weights.
- Copy-back against a sha256 manifest: `copy_back` in `vcommon.sh`; destroy only by exact id after a verified copy, only for ids in `$G/rentals.txt`.

## Order of use (the Director)
1. `000-bash-h7-dirh6-inputs` (read-only, $0): prints "N of 4 Mac checkpoints match their seals".
2. `000-bash-vastcredit` (existing job): credit must be at least $4.
3. The `PIN=` line in the three queue jobs names the commit that holds this kit. Move it only if a sealed file changes (the pin must hold this kit and both sealed sets, and be on main).
4. Delete the `STATUS: HELD` line of `h7-dirh6-1-start`. It prints STARTED (or a refusal).
5. Release `h7-dirh6-2-collect` about the estimated hours plus 30 minutes later. NOT-YET means the guard is still running; `h7-dirh6-3-collect` picks it up.
6. The blind recount of the marks comes after collect (`PASSMARKS.md`), before any RESULTS.md.

## What only the Mac can supply
Weights are never in git. They must already exist on the Mac at `~/premonition-models/rsn358u/`:

```
654b9b73846bc285a55202dfb5ccc0cda802d54dc99bae5323c9bd4ba0fa6cce  loop-s13/final.pt
b7083b1d5ed5883b3beae0e5f27fee9ff68b6a83c23cd3694b13e1eaed25d2c2  loop-s14/final.pt
d709b2f48ee72fc0bc0c21535ad168c22445742f552e96c55bb5b0beda89d404  loop-s15/final.pt
8bc9249c089cbdeb44c046eccb59f57fc2e00c30ec738c4c2b1068514fc53586  loop-s16/final.pt
```
These lines are copied from `artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt`. The same four hashes are the `ckpt_sha256` values in slp-358n3's seed JSONs, so dir-h6 starts from the same base slp-358n3 used (shown, by reading both files). Also on the Mac: `vastai` configured (this kit never reads it), `~/.ssh/id_ed25519.pub`, `uv` python 3.12, and at least $4 of credit.

## Things the H6 queue file (queue-h6-sleeplen.md) got different, and what I did
- Kit name: it said `sleeph6v`, copied from `sleep358nv`. The real pattern folder is `sleep358n3r`, and the brief says `sleeph6r`, so the kit is `sleeph6r`. The queue files are named `h7-dirh6-*` (the Director may rename them; the job name is taken from the file name).
- `<PIN>`: the queue jobs pin a commit. The start job refuses if the pin is not an ancestor of origin/main or if either seal does not match.
- Kept `cpu_cores_effective >= 8` in the search (the H6 draft said to drop it). Reason (suggested, not measured): four seed processes run at once and the H6 script's CPU load has never been measured; a card on a host with few cores could be slowed by that. This is a deviation I chose; delete `cpu_cores_effective>=$MINCPU` in `vcommon.sh:34` to follow the draft.
- No weights come back and none are sealed.
- Per-run GPU memory: `RUN_GB=6` (`vcommon.sh:43`), measured in slp-358n3 as 5.03 to 5.93 GB per process.
- Time estimate `BASE_H=4.0` (`vcommon.sh:42`) is the H6 draft's number and is conservative: slp-358n3's busiest seed took 53.5 minutes on an RTX 3090 (inferred that dir-h6 is nearer 1 to 2 hours; untested).

## Risks
- `scripts/claude_dir_h6_sleeplen.py` has never been run (no torch on the test box). The rental's `smoke` step guards this; the kit never fixes the script.
- The h6 script writes its result JSON only at the end of a seed, so a stop in the middle loses that seed's numbers (suggested: a JSON after each night; I did not edit the script).
- Tested only on Linux against fakes, not on macOS bash 3.2 and not with shellcheck. Timing is a virtual clock.
- A job that dies at the watcher's 75 minute alarm leaves `vstart.sh` running by itself; the guard survives (test 13b). `vstart.sh` can run longer than 75 minutes in the worst case (three hosts at 15 minutes for ssh plus uploads).
- If the sealed scripts change, the pin must be moved and the start job re-read.
