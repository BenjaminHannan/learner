# V1 Gate S report (2026-10-21)

Branch `claude/v1-assembly`. Spec `V1_SPEC.md` sha256 `a2abfe31...c7634b82f7d40b079e2a0346b0139c7be` (unchanged); params `V1_PARAMS.md` + `V1_PARAMS-AMENDMENT-1.md`. Raw outputs are in `design/v1/gate-s/` (box1 = first GPU job, box3 = second GPU job, cpu = local runs). No arm has started. The sealed splits were never opened.

## For Ben (plain words)
The assembled model runs end to end and passes the smoke test, with one asterisk: on the graphics card, "stop and restart" gives almost the same numbers but not identical ones (on the CPU it is exactly identical). Each arm should cost about $1.6 to train, so both arms together are about $3.3, far under the $20-per-arm cap. The creative sleep with the guard on went from 0% to 26% on practice puzzles after a small trial run, and the guard is using only 8-16% of the learning signal, nowhere near the 50% stop line. Nothing sealed was touched.

## Gate S, item by item
| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Pinned-environment preflight on the actual box | **PASS** | RTX 4090, torch 2.7.1+cu128 = `v1/PINS.json`; guard 21.16 GiB = 0.9 x detected 23.52 GiB; 5 FULL-arm steps ran, loss 22.9 -> 17.6; ckpt round trip ok (`box1/preflight.json`) |
| 2 | Overfit one batch | **PASS** (D on GPU; creative path) | 64 questions, 300 steps: FLOOR loss 22.55 -> 0.0042 (answer loss 0.0001); FULL 22.55 -> 0.0054; creative sleep path on 64 records 112.2 -> -0.36 (that loss can go below zero; it passes the fixed "<= 5% of start" mark). Mark fixed before the run (`v1/gate_s.py`). Run on a rented GPU, not Ben's PC (watcher down) |
| 3 | Component-ran log | **PASS** | S2: decoder memory 76 -> 92 rows (+16 raw-card rows) with the flag on, valid rows 49 -> 64 on the same batch. Muon: 29 tensors / 1,105,920 params in the Muon group, 29 of 29 moved after 4 steps (gold + teacher). Bridge: P_dc grad 14.0, P_cd grad 0.3, both weights nonzero. **G1 KL term live and nonzero** (see below). Sleep phase started and all four stages ran |
| 4 | ~2% of steps, loss falling | **PASS** | 300-step compressed full curriculum (gold, teacher, own) on both arms, 2.5% of 12,000: train loss 22.9 -> 3.4; dev loss FLOOR 22.8 -> 3.07, FULL 22.8 -> 3.22; dev accuracy 0 -> 16.6% / 13.5%; no NaN; A2/A1 did not fire. The literal real-plan 2% (240 steps) is gold-phase only; it first hit the memory guard (below) and was replaced by this schedule-compressed run |
| 5 | Save / kill / resume | **CPU PASS, GPU not bit-exact** | CPU FULL arm: steps recomputed after resume equal the first pass exactly (max diff 0.0). GPU: resumed vs first-pass max diff 7e-4 (job 1) and 9.6e-3 (job 2) against my GPU mark of 1e-3: **mark not met literally on GPU**. Two identical-seed GPU runs already differ by 0.06 before any kill (bf16 + atomics), so this is hardware noise, not a resume bug; a deterministic-GPU re-run is possible if you want the literal mark |
| 6 | Scoring end-to-end on dev | **PASS** | `final_eval` ran on CPU (D dev/validation, creative dev, bridge-off lesion, W1/W2 flags, KL share) -> `cpu/e2e_final_dev.json`; GPU: D dev scored 2,157 questions at every 100 steps; creative dev scored in the sleep run. Never the sealed splits |

### Sleep + G1 (the combination never run before)
Production settings (full warm-up and N', 32/480 tries, G1 on every weight-changing stage) on a **1/8-size pool**, GPU, `box1/gate_s_sleeptime.json`:
- KL term nonzero on **every update** in all four stages (256/256, 256/256, 89/89, 108/108); KL share of total loss after the first 25% of each stage: 8.9%, 8.0%, 15.9%, 16.4% (rule A3 stops at > 50%). Lock: 27 projected layers, 41 frozen tensors (the same 41 as the recorded G1).
- Creative dev first-try: raw parent **0.0%** -> **26.2%** (by kind: last_digit 76%, square 53%, double_add 2%, affine 0%, sq_plus 0%). This is DEV, a 1/8 pool, one trial; it is not W2 (sealed) and it says nothing yet about the sealed 20% mark.

### Memory guard finding (fixed)
First GPU job: D at 55,000 tokens/batch peaked at 22.19 GiB reserved and tripped the 0.9 x card guard (21.16 GiB). Cause: allocator fragmentation. With `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (now set in `v1/run.py`) the peak is **8.4-9.2 GiB** across all curriculum phases. The guard stays 0.9 x detected memory; nothing was loosened.

## Measured speed, memory, projected cost per arm (RTX 4090, 55,000-token batches)
| | FLOOR | FULL |
|---|---|---|
| Wake tokens/s | 150,000 | 133,000 |
| Peak GPU reserved | 9.2 GiB | 8.8 GiB |
| Wake, 12,000 steps (~48k tokens/step, ~572M tokens) | ~1.06 h | ~1.19 h |
| Dev evals (20 x 512 visits) | ~0.3 h | ~0.3 h |
| Data build on the box (400 shards, box shows 2 CPUs) | ~0.5 h | ~0.5 h |
| Creative sleep + G1 (scaled from the 1/8-pool run; fixed 15-min temperature pick) | ~0.75 h | ~0.75 h |
| **Total box hours** | **~2.6 h** | **~2.8 h** |
| **Cost at $0.55/h** | **~$1.5** | **~$1.6** |

Both arms: about $3.1-3.3 (two boxes in parallel, ~3 h). Caps are $20 per arm. Vast credit now $10.66; the arms plus a one-relaunch reserve fit without a top-up. Steps are not cut. (Spending headroom would allow several times more steps; the spec fixes 12,000, so that is a ruling, not something I changed.)

## Spend on Gate S (Vast, inside your $1.50 ruling)
Credit 11.898 -> 10.664 = **$1.23** in total. Roughly $0.8 of it is compute on three boxes (57075076 job 1; 57086296 job 2, a **dead host whose disk could not be read, nothing recovered, destroyed with `--abandon`**; 57090058 job 2 retry) and roughly $0.4 is storage/idle time while stopped boxes waited for slow pulls (per-box splits are estimates; the total is from the live credit read). All three boxes were destroyed after their pull (or abandoned) and verified gone.

## What went wrong along the way (for the record)
1. Review round 1 (blocking-only) found 10 items; all fixed (`V1_PARAMS-AMENDMENT-1.md`, KNOWN_ISSUES 16-18). It caught a real CUDA crash that Gate S would have hit in sleep, and a read of the sealed creative file in `stones.py` (removed; verified equivalent on rule keys).
2. The auto-mode classifier blocked my `waitlog` guard (it can stop a box). I polled read-only and stopped/destroyed boxes by hand; that is why one stopped box cost its 10-minute closing sleep.
3. The pull route moves ~1 MB parts through Vast's execute call; the checkpoint tarball was 800+ MB, so I added `pull --only out.tar.gz`. A full-arm checkpoint pull will need a smaller export (final models only) or a different route; see below.

## Open items for the coordinator
1. **A5 (box death) is only partly deliverable.** Resume works in code and on CPU/GPU; a dead host's disk can be unreadable (box 2). Checkpoints live only on the box, so a dead box is a restart from the last checkpoint only if the box can be pulled. Mitigation: arms run in several short phases, and I will pull each checkpoint set after each phase; or accept restart-from-scratch (an arm is ~3 h, ~$1.6).
2. **GPU resume mark (item 5).** Say whether CPU-exact is enough or you want a deterministic-mode GPU re-run (~$0.3).
3. **Parallel arms:** two boxes, FLOOR and FULL, same commit, each with its own pack (`v1/rent.py pack --kind arm --arm floor|full`); each needs the rental click.
4. Everything in KNOWN_ISSUES stands. In particular the bridge is inert for W1/W2 by design, and G1's hard lock may limit the creative gain (A3 watches it; so far 8-16% share).
