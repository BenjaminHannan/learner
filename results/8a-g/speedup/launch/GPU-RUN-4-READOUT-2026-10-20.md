# GPU-RUN-4 readout against PREREG-launch-defer.md (sealed 10-17): `defer` and `kvcat` on two RTX 4090 hosts

Raw outputs: `collected/box1/profrun/`, `collected/box2/profrun/`. The readout program is `gpu_run_4_marks.py` (the sealed sha256 `02eb8fe3…`), and its full output is in `GPU-RUN-4-marks.md` / `.json`. Booking and money are in `GPU-RUN-4-booking.md`. Labels: **shown** = in these files; **suggested** = my reading; **untested** = not measured.

## Verdict (section 5 of the sealed sheet)

**Mark 2 fails for `defer`: `defer` is not used, however fast.** No port. There is no change to any run, and none to 8aB3G2A4/A8.

**The launch-bound framing is NOT killed. Every mechanism prediction landed:**
- the counts fell (mark 7 holds);
- the kernel time did not grow (0.96×);
- P6 R = 0.59 (predicted ≈ 0.63; dead only at ≥ 0.90);
- `defer` was 1.36× faster on box 2, read under every rule, and 1.51× faster on box 1 (raw, 2 of 3 rounds read).

The kill criteria need a speed gain under 1.10×, so they are not met.

So **neither end state is reached**:
- not shipped, because the sheet's own numerics gate failed;
- not killed, because the framing was confirmed.

The single thing that blocks the port is E4. Section 6 below argues that E4, as written, cannot tell `defer` apart from the ordinary run-to-run divergence of this model. That is a claim about the gate, and only a new pre-registered measurement can settle it (§7).

## Mark by mark (shown)

| mark | result |
|---|---|
| 2 `defer` | bf16 one-update bar **passes**: relative loss difference 3.5e-6 (limit 1e-4), gradient cosine 0.9999996 (limit 0.9999); baseline rerun floor: loss 0, gradient relative L2 3.0e-4, against `defer`'s 9.2e-4. **E4 fails**: mean \|Δloss\| over updates 101–300 is **0.048** (limit 0.02), difference of means **0.035** (limit 0.01); `defer`'s loss is the lower one. → **mark 2 fails** |
| 2 `kvcat` | in deterministic mode the baseline's own rerun was not bitwise, and kvcat was not within it, so it fell to the bf16 bar, which it passes → relabelled **near** (K4 is information only) |
| 3 | box 1: 2 of 3 D4 rounds read. Round 3 was refused by rule (b): one B chunk at 1.057 × its same-numbered median (limit 1.05). D8 also 2 of 3. AA and K4 3 of 3. Box 2: everything 3 of 3. No throttle, no steal, and the trainer-core MHz rule active on both boxes (395 and 102 host-monitor samples) |
| 4 | `rounds_seq` identical in every A and B run of every arm, on both boxes |
| 5 | AA: box 1 **+0.09%**, box 2 **−0.19%** (limit 1%) → both boxes count |
| 6 | two hosts (machine 151645, Quebec, Xeon Platinum 8352V; machine 150319, California, EPYC 9684X), the same image, torch 2.11.0+cu128 and CUDA 12.8 → a valid replication pair |
| 7 | **holds**: stream syncs **1,305 → 62.5** per update (limit 300); DtoH **745 → 20** (limit 150); kernels **75,966 → 44,830** (0.59×, limit 0.65×); cudaLaunchKernel 70,618 → 42,239; kernel time **1,391 → 1,336 ms** per update (0.96×); GPU busy share of the profiled wall 0.36 → 0.61 |
| 1 (D4) | box 2: B < A in every round, B = 0.736 × A, peak 8.15 GB, **but mark 2 fails** → no. Box 1: regime-confounded (2 read rounds) |

## Speed (shown; the warm stretch, in-box A)

| box | host CPU | arm | A s/update (rounds) | B s/update (rounds) | speed | read |
|---|---|---|---|---|---|---|
| 1 | Xeon Platinum 8352V | D4 baseline → defer | 2.384, 2.351, 2.351 | 1.551, 1.556, 1.574 | **1.51×** (raw) | 2 of 3 |
| 1 | | AA | 2.460, 2.381, 2.402 | 2.463, 2.381, 2.404 | 0.999× | 3 of 3 |
| 1 | | K4 defer → defer+kvcat | 1.555, 1.553, 1.555 | 1.443, 1.454, 1.447 | 1.074× | 3 of 3 |
| 1 | | D8 (accum 8) baseline → defer | 3.494, 3.434, 3.413 | 2.010, 1.982, 2.000 | **1.72×** (raw) | 2 of 3 |
| 2 | EPYC 9684X | D4 baseline → defer | 1.827, 1.809, 1.806 | 1.332, 1.335, 1.332 | **1.36×** | 3 of 3 |
| 2 | | AA | 1.837, 1.804, 1.798 | 1.800, 1.805, 1.797 | 1.002× | 3 of 3 |

The historical 2.24 s/update sits between the two boxes' in-box baselines: 2.35 on the slower Xeon, 1.81 on the faster EPYC. As predicted, the gain is larger where the host CPU is slower.

## Predictions

| | prediction | result |
|---|---|---|
| P1 | D4 ≥ 1.25× on each box | box 2 **right** (1.36×); box 1 undecided under mark 3 (raw 1.51×) |
| P2 | D8 ≥ D4 | box 1 raw 1.72× vs 1.51× (both 2 of 3 read: undecided by the rules, right in the raw numbers) |
| P3 | K4 between 1.00× and 1.10× | **right** (1.074×) |
| P4 | PC gain smaller than the 4090's | not tested |
| P5 | `defer` peak ≤ baseline + 0.5 GB | **right** (8.15 vs 8.33 GB) |
| P6 | R = profiled kernel time ÷ unprofiled A | **R = 0.59** (predicted ≈ 0.63): the framing stands |

## What a 24,000-update run would cost (NOT a claim; mark 2 forbids using `defer`)

Information only, from the measured in-box numbers. The baseline holds today.
- **Box 1:** baseline 2.35 s/update, about 15.7 h. `defer` would be about 1.56 s/update, about 10.4 h.
- **Box 2:** baseline 1.81 s/update, about 12.1 h. `defer` would be about 1.33 s/update, about 8.9 h.
- **Accum 8, box 1:** 3.43 s/update, about 22.9 h. `defer` would be about 2.00 s/update, about 13.3 h.

## Why E4 failed, and why that may be the gate rather than `defer` (suggested; read carefully)

Shown:
- The two 300-update traces agree to about 1e-4 relative at update 1 (−8e-5 on a loss of about 18).
- They first differ by more than 0.01 at update 47.
- From update 51 on, `defer`'s loss is lower in every 50-update window by 0.03–0.04, with single-update gaps up to 0.28.
- One update of the same batch (abequiv) agrees to 3.5e-6 in loss and 0.9999996 in gradient cosine. That is a gradient difference about 3× the baseline's own rerun noise (relative L2 9.2e-4 against 3.0e-4).

Suggested:
- This shape — an exact start, then a gap that grows from last-bit rounding into a persistent offset after about 50 updates — is what chaotic amplification of rounding differences looks like. The record shows the same model doing exactly this to itself: on the PC, the same code resumed from its own update-100 checkpoint differed by **0.0167 mean |Δ| within just 50 redone updates, max 0.119** (TRACE-A-READING-2026-10-14.md). That is already near E4's 0.02 limit with no code change at all.
- The E4 limits (0.02 / 0.01) were registered for `eg_once` on the plain PTC arm (PREREG-eg-once.md). They were carried into this sheet without a baseline-vs-baseline E4 on B3G2. They are absolute limits, set for a model whose loss is about 0.24 late in training, and that sheet calls E4 "a smoke check … it does not replace the seed spread" (PREREG-eg-once.md:22). B3G2's loss over updates 101–300 is about 2.9, 12 times larger. So 0.02 is about 0.7% of the loss here, against about 8% where it was set. `defer`'s 0.048 is 1.7% of the loss (shown arithmetic). This is the same class of defect as the chunk-spread rule the gate struck in condition 1: a fixed bar with no measured noise floor under it.
- A persistent sign within one pair is not evidence of a systematic effect. Once two chaotic trajectories separate they stay separated, so a single pair cannot distinguish "defer trains differently" from "any two runs drift this far".

Untested: whether baseline against baseline (two runs of the same code on the same GPU) also exceeds 0.02 / 0.01 over updates 101–300. **That one number decides between the two readings, and this run did not measure it.**

I am not re-reading the sealed sheet. Mark 2 failed as written, and `defer` stays unused.

## 7. What would move this forward (a bid for the coordinator; nothing booked)

A new pre-registration, GPU-RUN-5 "E4 noise floor", one 4090 box:
1. Two baseline 300-update traces, same seed and rows: the A–A E4 statistic.
2. One more baseline vs `defer` trace.
3. Rule fixed in advance: `defer`'s E4 is read against the A–A floor. Mean |Δ| and difference of means must each be ≤ max(the registered limit, 1.5 × A–A).
   - If A–A itself exceeds the registered limits, the E4 limits are recorded as unreadable for B3G2. Mark 2 for `defer` then rests on the bar plus the floor-relative E4.
   - If A–A is well inside the limits while `defer` is not, `defer` changes training: closed.

Money: about 30 + 3 × 14 = 72 minutes up; about $0.6 at $0.47/h billed, with a $1 cap. It would displace nothing on the PC. It buys the decision whether the 1.36–1.51× speed-up (5–6 h saved per 24,000-update run) can be used at all.

## Money (shown)

| box | billed rate | up | cost |
|---|---|---|---|
| 1 (56810922) | $0.4696/h | 00:15:21–02:00:28 = 105.1 min | $0.82 |
| 2 (56810924) | $0.5126/h | 00:15:21–00:55:16 = 39.9 min | $0.34 |
| **total** | | | **$1.16** (granted $2.07; expected $1.8) |

Credit went from $22.21 to $20.74 (−$1.47). The extra $0.31 is not GPU-RUN-4's: other sessions' instances were listed on the account. Both GPU-RUN-4 boxes are destroyed and no longer listed.
