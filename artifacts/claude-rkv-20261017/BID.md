# FUNDING BID: decoder_reader_kv paired A/B (to the coordinator)

Filed 2026-10-17. Nothing is booked. The card it funds is `RUN-CARD.md` in this directory. Prices are
read-only Vast on-demand quotes taken today (reliability ≥ 0.98): RTX 5090 $0.402–0.463/h, RTX 4090
$0.322–0.394/h, RTX 3090 $0.122–0.149/h.

## The ask, in stages: each one is gated on the one before

| Stage | What it buys | Machine | Cost | Gate to the next stage |
|---|---|---|---|---|
| **0** | The toy A/B: `train_toy("D", steps=1500)` for both arms × 3 seeds, plus the guard counts. It answers two questions. Does either arm learn the far-fact toy at all (control did not on 09-18)? Does control fetch at all (otherwise the guard cannot be read)? | CPU: this container or Ben's Mac, about 4 min per run, about 25 min total | **$0** | Control fetches > 0 cards per question **and** at least one arm is above chance. If not, I recommend **no GPU spend**, because the village A/B could not produce a gain that counts. |
| **1** | Timing smoke: 300 steps per arm at full size on village data. It measures s/step and the step count at F, which replaces the estimates below. | 1× RTX 5090 | **cap $0.30** (expected about $0.20, 30 min including setup) | s/step ≤ 3× A's s/FLOP (spec §5). Otherwise re-price before stage 2. |
| **2** | The card: 3 seed pairs = 6 runs at budget F with equal steps, plus eval (score, DEV, guard) and copy-off. | 1× RTX 5090, runs in sequence | **cap $2.50** (expected $0.80–1.85) | Hard stop at the cap. Raw outputs are copied off and checked before the box is destroyed. |
| **2b** | The extension rule only (result within 1 SE of the bar): 2 more pairs. | same | **cap $1.00** | Asked again before spending. |

**Total requested now: stage 0 ($0).** Stages 1 and 2 (≤ $2.80) are requested contingent on stage 0
passing its gate. 2b (≤ $1.00) only on a new ask. The worst case for the whole line is **$3.80**.

## How the stage 2 estimate is built

- Budget F ≈ 3.15e16 FLOPs: A's fair run, 600 s on a 5090 (`design/06-premonition-mini-spec.md` §5).
- D's seconds per FLOP have **never been measured on a GPU**. The spec tolerates up to 3× A's. So one arm-seed takes 10–30 min, and treated takes about +3.4% (hand FLOP count).
- 6 runs → 1.0–3.0 GPU-hours. Eval adds about 0.5 h and setup, data copy and rsync about 0.5 h, for 2.0–4.0 h in total.
- At $0.40–0.46/h that is $0.80–1.85. The $2.50 cap leaves room for the slow end and one re-run.

## What it displaces

- **Against the $50/week Vast cap:** this week's spend so far is **not in the repo**. The ledger (`artifacts/fable-predictions-ledger.md`) stops on 09-29 at "credit $17.98". **[COORDINATOR]** please enter this week's spent-to-date. At ≤ $3.80 worst case, this line uses at most 7.6% of the weekly cap.
- **The $0 alternative:** BensPC's 5070 Ti instead of Vast. That costs $0, but it waits behind the queued g2c3s and B3G2 3M s400 jobs (`reviews/pc-handoff-g2-2026-10-09.md`) and would push them back by about 2–4 h of PC time. I recommend Vast so the Learner-New group 2 queue is not delayed.
- **Older house limits for reference:** the Sep 28 rules had $4 per vast job and Ben's OK for ≥ $0.50 (`handoff/director-briefs/rules.md`). Each stage here is under $4. Stages 1 and 2 are ≥ $0.50 in total, so they need your gate under the Oct 17 rule.

## What I need from you

1. A code review of the change (`premonition/model.py`, `config.py`, `flops.py`, the new test and the guard script). That includes the `premonition/` no-edit override (RUN-CARD F4) and the masking under `wipe="store"`.
2. The four [COORDINATOR] blanks in RUN-CARD.md: the join score definition, the parent (P1 or P2), the DEV-slip family rule, and pooled vs per-seed guard. Then I seal the card.
3. A yes or no on stage 0.
