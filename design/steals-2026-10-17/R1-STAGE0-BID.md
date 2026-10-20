# Bid: R1 stage 0, Muon against AdamW on the far-fact toy (to the coordinator)

Filed 2026-10-20. **Cost: $0.** It runs on CPU in this cloud container, with no rental and nothing booked. The card is
"RUN CARD R1" in `REPORT.md`, with its blanks filled by Q42. Stage 0 was approved on condition of a clean review of
the full package. That review is recorded in `REPORT.md` §7.

## What it buys
One registered toy answer to the question: does the Muon option reach a lower held-out loss **per second of
training** than AdamW on D, without costing held-out accuracy? It also tells us whether the learning rate decides
the sign, as the 60-step smoke run suggested.

## The run (fixed now, before it starts)
- **Code:** `scripts/premonition_steals_r1_stage0.py` at the reviewed commit of `claude/steals-8`, with the default
  settings. Each arm is `train.toy_setup("D", steps=1500, seed=s, lr=..., optimizer=...)`.
- **Arms:**
  - A0: AdamW, lr 3e-3.
  - A1: Muon, lr 3e-3 (the recipe).
  - A2: Muon, lr 2e-2.
- **Seeds:** 0, 1, 2. At each seed the model and the batches are bit-identical across arms.
- **Order:** within a seed, arms are interleaved in 50-step chunks. The order is keyed by the seed, a Latin square
  over seeds 0–2.
- **Machine:** CPU, `OMP_NUM_THREADS=1`, nothing else running.
- **Expected time:** about 70–90 minutes (9 arm-runs of 1,500 steps at about 0.3 s per step).
- **Output:** `artifacts/claude-steals-20261017/r1-stage0/`: the log, one JSON per arm and seed, and `result.json`.
  It is committed with `git add -f`.

## Pre-set marks (card sections 4–7, as filled by Q42)
- **Primary readout.**
  - Held-out loss in teacher mode with 4 fixed loops, on the 4 fixed held-out toy batches, after every 50 steps.
    Evaluation time is off the clock.
  - The value used is that loss interpolated at T* = the shorter arm's training seconds.
  - d_s = loss(A0, T*) − loss(Ak, T*).
- **Bar, each Muon arm against A0 on its own:** mean(d) − 2·SD(d)/√3 > 0, **and** d_s > 0 in at least 2 of 3
  seeds, **and** mean(d) ≥ 3% of A0's loss at T*.
- **Guard:** if Ak's held-out toy accuracy is more than 3 points below A0's in at least 2 of 3 seeds, the pass does
  not count.
- **Verdicts:**
  - **PASS:** the bar and the guard both hold.
  - **NOT COUNTED (guard):** the bar holds and the guard trips.
  - **PROVED WRONG:** mean(d) + 2·SD(d)/√3 < 0.
  - **NOT SHOWN:** anything else.
  - **DID NOT TRAIN:** a non-finite loss.
- **What would prove Muon wrong on D:** A1 and A2 both behind A0 at T* by more than 2 SE.
- **Prediction (a guess, written before the run):** A2 PASS; A1 NOT SHOWN or PROVED WRONG.
- **Reported, not claimed:** the equal-step final held-out loss, ms per optimizer step, s per training step, final
  training losses, accuracy with own retrieval and with gold cards, and recall@4.

## What it displaces
Nothing paid. It occupies this container's CPU for about 1.5 h, and R2's stage 0 waits until it finishes (Q43
sequences R2 second).

## What I need
A yes or no to start R1 stage 0 at the reviewed commit.
