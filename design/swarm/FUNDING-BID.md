# Funding bid: swarm screen ladder (to the coordinator, under the $50/week Vast cap)

**Status: BID, not booked.** All $0 work is done or listed below. Nothing is rented until the coordinator
gates this bid, and the run cards are sealed first (`RUNCARD-S0.md` §0). All code is a draft until the
coordinator code-reviews it.

**Coordinator ruling Q28 (2026-10-18):** C0 + S0 is YES in principle, hard cap **$4.20 total**, inside the
week's unallocated room (about $20.14). It books ONLY after all of these: (1) the Q26 code review passes;
(2) the Q27 fills are in and the card is sealed; (3) the box-script dry run is done; (4) C0 clears the
stop-and-ask rule (above 2.5×: stop and ask, do not book S0). **S1 ($2.40) is NOT booked.** It is a separate
later ask, only after an S0 PROMOTE. The PC route is not taken. Main-line adoption of the swarm is Ben's call
and is neither asked nor granted here.

## What the money buys

One answer, in two steps, at a small fixed cost: **does running four thinkers at once inside D beat one
thinker on the held-out join (`far_deep`), and does letting them talk add more?** A KILL at S0 ends the
line for about $4.

## Items (Vast, RTX 4090 or 5090, dph_total ≤ $0.46, reliability ≥ 0.98, house rental rules)

| item | what | box-hours (estimate) | expected | hard cap | when |
|---|---|---|---|---|---|
| **C0** | Build the village data on the box once. Measure s/step for D1 and for S0/S1 at M = 2, 4, 8 (warm stretch, 3 interleaved rounds, the GR4 bench protocol), plus GPU-busy fraction from the profiler. Sets T | 1.0 | $0.46 | $0.70 | first |
| **S0** | D1 and S0 × seeds 0-2, each T ≤ 3,600 s; 6 validation evals; readout | ≤ 7.5 | ≤ $3.45 | $3.50 | after C0, if C0 does not stop it |
| **S1** | S1 × seeds 0-2 (reuses the S0 controls); 3 evals + 9 lesion evals; readout | ≤ 5.0 | ≤ $2.30 | $2.40 | only after S0 = PROMOTE |
| | **total if everything runs** | ≤ 13.5 | **≤ $6.21** | **$6.60** | |

**Asking now: C0 + S0 = $4.20 cap.** S1 ($2.40) is a separate yes, after the S0 readout.

**C0 stop-and-ask rule (free insurance).** If S0 at M = 4 runs more than 2.5 × D1's s/step, concurrency is
*not* near-free for D. The premise that D is launch-bound would then be wrong for this model. C0
reports this, and S0 is **not** started until the coordinator rules (on M = 2, or go as is). Cost of
finding out: ≤ $0.70.

## What it displaces

* Money: ≤ $6.60 of the $50 week. This week already has GR4 launch-defer at ≤ $2.07
  (`PREREG-launch-defer.md` on `claude/launch-bound-solve`). The week's running total is read before
  booking. If the two together exceed what the coordinator wants this week, C0 + S0 alone fit in $4.20.
* Box time: one rented box at a time, so no contention with GR4's two boxes if booked after them.
* The free route is BensPC (RTX 5070 Ti), at $0. It displaces the B3 ladder on the PC, and the PC is
  reserved for that ladder (FINISHED-MODEL §1), so I do **not** propose it unless the coordinator prefers
  it. A run on the PC would also need its own T, from a PC-side C0.
* Agent time: one Sonnet runner session per item, and an Opus readout.

## $0 work still to do before booking (pre-approved, not yet done)

1. Coordinator code review of `premonition/swarm.py` and the train.py plumbing (slot granted, Q26; the code is
   commit `124e6c6fe` on `claude/swarm-thinkers`, the commit after `d046698cf`).
2. A box script (`scripts/premonition_swarm_box.sh` + a marks readout `scripts/premonition_swarm_marks.py`)
   that pins the commit and file hashes. It has to pass a CPU dry run at the tiny preset that shows every
   mark is computable from its outputs (the house sealing rule, as in GR4 §9).
3. ~~The coordinator rules on the PROVISIONAL rulers (design §0).~~ **Done 2026-10-18 (Q27): all three
   confirmed as written.**
4. Seal S0 with T filled in from C0. The C0 bench is pure measurement with no accuracy readout, so it
   cannot contaminate the pre-registration.

## Spend discipline

Each box refuses MAXH × DPH above its item cap. Copy back and check before destroying the box. One ledger
line per launch. Every dollar figure in a readout is wall time × the billed rate.
