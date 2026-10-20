# RUN CARD S1: the full swarm (board ON) against S0, to isolate what communication adds

**Status: DRAFT, NOT SEALED. Written 2026-10-17, before any swarm run.** Sealable only after S0's verdict
is PROMOTE (or the coordinator overrides a HOLD/KILL in writing). Same sealing rules as `RUNCARD-S0.md`.
**2026-10-18:** the coordinator ruled S1 NOT booked. It is a separate later ask, made only after S0 returns
PROMOTE (Q28). The rulers are confirmed (Q27). The pre-seal clarifications of S0 (10-18) apply here too:
DEV slip per seed and never averaged, `loop_mismatches` instead of `gold_missing`, and precedence
VOID > INSUFFICIENT > KILL-COMM > FAIL > PASS > HOLD.

Code and data: identical to S0 (same commit, data tag, tokenizer, box type, T). The S0 and D1
checkpoints from the S0 screen are reused as controls, so S1 trains only the new arm.

## 1. Arm (seeds 0, 1, 2)

| arm | config | role |
|---|---|---|
| **S1** | `thinkers=4, swarm_board=True, swarm_rounds=4, board_cards=16` | **the decision** |
| S0 (reused) | from the S0 screen | the control: same desks, board off |
| D1 (reused) | from the S0 screen | the forgetting guard's reference |

* Matched wall-clock: same T as S0. Matched parameters: S1 has +256 over S0 (board row types), so
  2,102,996 (+768, +0.04% over D1).
* Eval-time lesions on every S1 checkpoint (no training): `lesion="board"` (S1 run as S0),
  `lesion="notes"`, `lesion="cards"`.

## 2. Rulers

As S0 §2: `far_deep` on validation is primary; `near` / `overall` with the ≥ 2 of 3 family rule is the
forgetting guard. Same statistics.

## 3. Marks

| mark | bar |
|---|---|
| **M1 communication adds** | pooled over 3 seeds (item means over seeds, paired over items: RUNCARD-S0 §2, 10-20), S1 `far_deep` ≥ S0 + 3.0 points, p(S1 > S0) < 0.01; and S1 > S0 on ≥ 2 of 3 seeds |
| **M2 board is used** | pooled, S1 intact − S1 `lesion="board"` on `far_deep` ≥ 3.0 points, p < 0.01, and the drop is positive on ≥ 2 of 3 seeds. Otherwise **FAIL (BOARD-UNUSED)**: any S1 gain came from training dynamics, not talk (the register-loop failure, design §1) |
| **M3 DEV slip vs D1** | on ≥ 2 of 3 seeds, S1 `near` < D1 `near` − 3.0, or S1 `overall` < D1 `overall` − 3.0 → **FAIL** |
| **M4 desk usage** | as S0 M3, for S1 |
| **M5 diversity** | as S0 M4. **Also:** the board is a broadcast, so the readout prints S1 − S0 `register_cos`. If S1 is collapsed and S0 is not, the verdict line says **"the board collapsed the desks"** and cannot PASS |
| **M6 validity** | as S0 M5 and M6 |

**Verdict:** **PASS** (communication adds and is used) only if M1 and M2 pass and M3-M6 hold.
**KILL-COMM** if pooled S1 − S0 ≤ 0 or S1 < S0 on ≥ 2 of 3 seeds. **FAIL** on a guard. **HOLD**
otherwise.

Information only: `lesion="notes"` and `lesion="cards"` drops (which half of the board carries the
gain), S1 vs D1 on `far_deep`, per-depth cells (`depth_2` … `depth_5`), the `changed` slice (conflicting
bindings), steps in T, and the S0 → S1 changes in `fetch_overlap` and `ask_rate`.

## 4. Predictions

* **P1.1** S1 − S0 on `far_deep`, pooled, lands in [0, +6] points. Proved wrong outside.
* **P1.2** The `board` lesion costs more than the `notes` lesion alone, i.e. posted cards carry most of
  the gain. Proved wrong if the notes lesion costs more.
* **P1.3** S1's `fetch_overlap` is *lower* than S0's: posted cards make re-fetching useless. Proved wrong
  if higher.
* **P1.4** S1 completes ≥ 0.95 × S0's steps in T (the board adds 20 rows to 76). Proved wrong if fewer.

## 5. What each result allows

* PASS → a design note proposing the next rung, with the wide-single-thinker control, M = 8, and a
  swarm-level halt, each under its own card. `thinkers` stays OFF by default until Ben decides.
* KILL-COMM, or FAIL (BOARD-UNUSED) → the board line stops. A new design is needed, not a tweak.
* FAIL (DEV slip) → debug offline at $0.
* HOLD → the coordinator rules.

## 6. Known limits

* The `board` lesion runs an S1-trained model *as* S0. That is the right test of "is the board used",
  but it is out of distribution for that model, so the drop is an upper bound on the board's value. The
  S1 − S0 comparison (M1) is the clean estimate.
* Everything in S0 §6 applies.
