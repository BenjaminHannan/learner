# DRAFT bid: R1 stage 1, Muon against AdamW on village data (to the coordinator)

Drafted 2026-10-20 under the coordinator's 10-20 ruling ("DRAFT it now. Don't book."). **Nothing is booked, and
nothing runs on a GPU until you rule on this bid.** Stage 0 (`REPORT.md`, "R1 stage 0 RESULT") gave A1, Muon at
the recipe lr, a PASS on the toy, with 3 of 3 seeds positive and +14.3% held-out loss at equal clock. It also showed
A1's toy recall@4 at about 0.33, against AdamW's 0.95, 0.63 and 0.32. That is why this card has a pass-blocking
retrieval guard (G-RET).

## 0. Prerequisites at $0, before any booking (each one gets a built-in review)
- **P1:** `train.train_d` gains `optimizer="adamw"|"muon"`, passed through to `MiniTrainer`. The default stays
  AdamW and stays bit-identical (the identity harness covers it). Today `train_d` has no optimizer option.
- **P2:** a village launcher and runner for this card.
  - It trains both arms per seed.
  - It runs the held-out evaluation hook off the clock.
  - It does the T\* interpolation and the scoring below.
  - It writes `RESULT.json` and a run note, and copies everything off the box with sha256 checks before the box is
    destroyed.
  - There is no training CLI for D today (PR 79, F5).
- **P3:** a CPU dry run of the launcher on a few village visits at the tiny preset. Its sole purpose is checking
  the plumbing.

## 1. The one change, and the lr question for you
The change is the optimizer: `MiniTrainer(optimizer="muon")` against the default AdamW. Stage 0 showed one specific
thing: Muon helps **at the same lr as AdamW**, which is Moonshot's RMS-matched recipe. On the toy both ran at 3e-3.
The village default lr in `train_d` is 1e-3.

**[COORDINATOR] choose one:**
- **(i), my recommendation:** both arms at the village default, lr 1e-3. This is the recipe applied to the village
  run: one change, and the house default kept.
- **(ii):** both arms at 3e-3, the stage-0 value. AdamW at 3e-3 is not the village default, so the control would
  also be off-default.

Muon at 3e-3 against AdamW at 1e-3 would be **two changes**, the optimizer and the lr, so I do not propose it.

## 2. Setup
- **Model:** D, full preset (d = 128, about 2.10M parameters with the v2 vocabulary), every steal flag off.
- **Training:** `train_d` defaults apart from the optimizer: warmup 100, clip 1.0, bf16 on CUDA, max_tokens 55,000,
  max_visits 48, and the curriculum gold 0–5%, teacher 5–30%, own 30–100%.
- **Parent:** a paired fresh start. No D checkpoint exists anywhere. At each seed both arms are bit-identical at
  init and see the same data order.
- **Seeds:** 0, 1, 2.
- **Length:** the same FLOP budget F for both arms. The models are identical, so the step counts are identical too.
  Spec §5 gives F ≈ 3.15e16, A's fair run. **[COORDINATOR]** confirm F, or a smaller F for stage 1. Wall clock is
  logged per step.
- **Machine:** one Vast RTX 5090, on-demand only, never interruptible. The arms of a seed run back to back on the
  same box.

## 3. Pre-set marks (written before any run)
- **Primary readout:** held-out village validation loss.
  - Teacher mode, 4 fixed loops, on a fixed set of 256 validation visits with fixed distractor seeds.
  - Evaluated every 500 steps under `no_grad`, with evaluation time off the clock.
  - The value used is that loss interpolated at T\* = the shorter arm's training seconds.
  - d_s = loss(A0, T\*) − loss(A1, T\*).
- **Bar:** mean(d) − 2·SD(d)/√3 > 0, **and** d_s > 0 in at least 2 of 3 seeds, **and** mean(d) ≥ 3% of A0's loss
  at T\*. This is Q42's loss-readout rule.
- **G-ACC, accuracy guard:** A1's held-out accuracy from `validate` (own retrieval) must not be more than 3 points
  below A0's in 2 of 3 seeds.
  - This is the village exp1 primary score if you name one (**[COORDINATOR]**, as in PR 79).
  - Otherwise it is `validate` accuracy on the 256 visits.
- **G-RET, retrieval guard (pass-blocking, as you required):** recall@4 from `validate` (`gold_recall_at_4`) is
  reported for both arms in every seed. G-RET **trips** if either holds:
  - (a) pooled mean recall@4(A1) < 0.8 × pooled mean recall@4(A0);
  - (b) A1's recall@4 is more than 0.10 below A0's in at least 2 of 3 seeds.

  A loss or accuracy gain that comes with a retrieval loss does not count.
- **Verdicts, in order:**
  1. **DID NOT TRAIN:** a non-finite loss.
  2. **NOT COUNTED (retrieval guard):** the bar holds and G-RET trips.
  3. **NOT COUNTED (accuracy guard):** the bar holds and G-ACC trips.
  4. **PASS:** the bar holds, and G-RET and G-ACC both hold.
  5. **PROVED WRONG:** mean(d) + 2·SD(d)/√3 < 0.
  6. **NOT SHOWN:** anything else.
- **What would prove it wrong:** A1 behind A0 at T\* by more than 2 SE, or a loss gain that G-RET voids. The second
  would mean that Muon buys its answer-path gain by giving up retrieval, which is the risk stage 0 hinted at.
- **Reported, not claimed:**
  - equal-step final loss
  - ms per optimizer step and s per training step
  - final losses (lm, ask, ans, halt)
  - accuracy with gold cards
  - asked_rate, loops, halt_rate
  - recall@4 at every evaluation
- **Prediction (a guess):** A1 PASS on loss, and G-RET holds narrowly. P(G-RET trips) ≈ 0.35, because toy recall
  under Muon was low.

## 4. Cost, staged. Each stage is gated on the one before
Prices are PR 79's read-only Vast on-demand quotes from 10-17 (RTX 5090 $0.402–0.463/h, reliability ≥ 0.98). I
will re-quote them before booking.

| Stage | What it buys | Machine | Expected | Hard stop | Gate to the next stage |
|---|---|---|---|---|---|
| 1a | A timing smoke: 300 steps per arm at full size on village data. It measures s/step for each optimizer on the GPU (Muon's Newton–Schulz runs in bf16 there) and the step count at F. | 1× RTX 5090 | about 0.5 GPU-h, about $0.20 | **$0.30** | Muon's s/step ≤ 1.25× AdamW's (otherwise re-price), and D's s/FLOP is plausible against spec §5. |
| 1b | The card: 3 seed pairs = 6 runs at F, plus evaluation and copy-off. | 1× RTX 5090, runs in sequence | 2.0–4.0 GPU-h, $0.80–1.85 | **$2.50** | Hard stop at the cap. Raw outputs are copied off and checked before the box is destroyed. |

- **GPU hours:** 2.5–4.5 in total. D's GPU seconds per FLOP have never been measured, so stage 1a replaces this
  estimate.
- **Total requested:** at most **$2.80**, and only after P1–P3 pass review.
- **Against the cap:** at Q42, $5.58 was spent and $29.86 committed of the $50/week cap, leaving about $20.14
  unallocated. This bid would use at most 14% of that. **[COORDINATOR]** confirm the current figure.

## 5. What it displaces
- **No PC time:** it runs on Vast, so the BensPC queue is untouched.
- **R2 comes first:** R2 stage 0 ($0, CPU) is still pending its fixes and re-review, and it should land before
  this bid's P1–P3 take review slots.

## 6. What I need from you
1. The lr choice in §1.
2. F, or a smaller stage-1 F.
3. The village primary score, or `validate` accuracy as G-ACC's measure.
4. Confirmation of the current spend.
5. A yes or no on starting P1–P3 ($0) now. Booking stays a separate decision after they pass.
