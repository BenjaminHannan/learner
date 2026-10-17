# RUN CARD S0: parallel independent desks + combiner, NO communication (the kill screen)

**Status: DRAFT, NOT SEALED. Written 2026-10-17, before any swarm run of any size, on any data, CPU or
GPU.** Two things must happen before sealing: (1) the coordinator accepts or replaces the PROVISIONAL
ruler mapping in §2 (design §0 items 2-3), and (2) §C0 of `FUNDING-BID.md` reports D's speed numbers,
which fix T in §1. After sealing, amendments follow the house rule: dated, written before the result
files they concern are read, original text kept.

Code: branch `claude/swarm-thinkers` (commit pinned at sealing). `premonition/swarm.py`, flag `thinkers`.
Base: D, v2 tokenizer (`VOCAB_V2`), full preset (d = 128), label-free regime, `premonition.train.train_d`.
Data: a village build `large-seed0-<tag>` made on the box by `step1.build_data` (same tag for every arm;
the tag goes in the readout).

## 1. Arms (every arm × seeds 0, 1, 2; same box; run one at a time, never two on one GPU)

| arm | config | role |
|---|---|---|
| **D1** | `thinkers=1` (today's D, flag off) | the single thinker |
| **S0** | `thinkers=4, swarm_board=False, swarm_rounds=4, board_cards=16` | **the decision** |

* **Matched wall-clock (primary).** Every run trains for exactly T seconds: `train_d(seconds_budget=T,
  flop_budget=1e30)`. `MiniTrainer(seconds_budget=…)` sets both the curriculum share and the stop from
  training seconds, with eval pauses excluded (`TrainerPlumbingTest`). `max_seconds` alone would stop the run but
  leave the curriculum frozen at its FLOP share, so it is not used. **T = the seconds D1 needs for F = 2.6e16 FLOPs on this box, measured in §C0, rounded up to the next 300 s, and capped at 3,600 s.** S0 gets the
  same T, whatever number of steps that buys.
* **Matched parameters (reported, separately).** D1 2,102,228 (v2) vs S0 2,102,740 (+512 desk embeddings, +0.02%).
* **Reported, not matched:** steps, tokens, think FLOPs per question, s/step, peak GPU memory.
* Eval: `evaluate_d_checkpoint(split="validation")` (label-free), max_loops default. S0 is fixed at 4
  rounds and does not halt; D1 halts by HALT, at most 8 loops.

## 2. Rulers (PROVISIONAL mapping, see design §0)

* **Primary: held-out join** = the `far_deep` decision cell (knowable ∧ ¬evidence_kept ∧ depth ≥ 2,
  exclusions applied, `premonition/slices.py`) on the **validation** split (held-out villages). The test
  split is **not** touched by S0 or S1.
* **Forgetting guard: DEV slip** = the `near` and `overall` cells on validation. Family rule: **≥ 2 of 3
  seeds**.
* Statistics: paired by item (and seed, when pooled), `learnlab.metrics.paired_greater_pvalue`,
  α = `policy.ALPHA` = 0.01, margin `policy.MIN_EFFECT` = 0.03, cells need ≥ `MIN_ITEMS` = 100 items
  per seed.

## 3. Marks (registered; each run once)

| mark | bar |
|---|---|
| **M1 join (promote)** | pooled over 3 seeds, S0 `far_deep` ≥ D1 + 3.0 points, and p(S0 > D1) < 0.01 paired; **and** S0 > D1 on ≥ 2 of 3 seeds |
| **M2 DEV slip (guard)** | on ≥ 2 of 3 seeds, S0 `near` < D1 `near` − 3.0 points → **FAIL**; same rule for `overall` |
| **M3 desk usage (guard)** | on every one of ≥ 2 of 3 seeds: every desk's eval `ask_rate` ≥ 0.05, and every desk's `fetch_count` ≥ 0.10 × the busiest desk's. Otherwise the breadth was not used → **FAIL (USAGE-COLLAPSE)** |
| **M4 diversity (guard)** | the readout prints `fetch_overlap`, `register_cos`, `ask_rate[4]`, `fetch_count[4]`, `silent_desks` per seed. If `collapsed` (register_cos > 0.95 **and** fetch_overlap > 0.8) on ≥ 2 of 3 seeds, the verdict line reads **"COLLAPSED: the desks are copies"** and the verdict cannot be PROMOTE |
| **M5 matching (validity)** | every run's train seconds within T ± 2%; same data tag, tokenizer digest, eval items for every arm; `gold_missing` = 0; no NaN loss. Otherwise the run is **VOID** and reruns once under this same card |
| **M6 cells** | `far_deep` has ≥ 100 items per seed; otherwise **INSUFFICIENT** (no verdict) |

**Verdict:**
* **PROMOTE to S1** only if M1 passes and M2, M3, M4, M5, M6 hold.
* **KILL** if pooled S0 − D1 on `far_deep` ≤ 0, **or** S0 < D1 on ≥ 2 of 3 seeds. The swarm line stops.
  S1 is not booked unless the coordinator explicitly overrides (see §6).
* **FAIL** if a guard (M2, M3) fails, whatever M1 says.
* **HOLD** otherwise (a gain between 0 and 3 points, or not significant). No S1 without a coordinator
  ruling.
* Readout VOID if any mark cannot be computed from the files (schema mismatch).

## 4. Predictions (each with what proves it wrong)

* **P0.1** S0 − D1 on `far_deep`, pooled, lands in [−2, +4] points. That is my honest prior: breadth
  without talk mostly buys parallel ASKs. Proved wrong if outside.
* **P0.2** S0's `fetch_overlap` is in [0.2, 0.6]: the assignment splits the evidence but the desks still
  share common cards. Proved wrong outside.
* **P0.3** S0 completes 0.5-0.9 × D1's steps in T. Proved wrong outside. Above 0.9 would mean D is
  launch-bound as hoped; below 0.5 means the swarm is compute-bound at M = 4.
* **P0.4** S0's `near` is within ±3 points of D1's (M2 holds). Proved wrong if M2 fails.

## 5. What each result allows

* PROMOTE → `RUNCARD-S1.md` may be sealed and booked, reusing these S0 checkpoints as its control.
* KILL → no more GPU for the swarm line. Write up, $0 follow-ups only.
* FAIL (guard) → debug offline at $0. A rerun needs a new card.
* HOLD → the coordinator rules. One option is S1 anyway, on the argument in §6.
* No result here changes D's default (`thinkers=1`).

## 6. Known limits (declared before any run)

* **What a KILL does and does not show.** It shows that four desks *without talk* do not beat one
  thinker at matched wall-clock on the held-out join. It does not show that a talking swarm cannot.
  The board is the part designed to carry what a lone desk cannot get. The ladder follows the brief and
  kills here anyway: if breadth alone adds nothing, the cheapest bet is that talk will not rescue it.
  That is a judgement call, and it is flagged for the coordinator.
* The wide single thinker (M × 4 registers, M × top_k per loop) is not an arm, so a PROMOTE cannot
  separate "four desks" from "more rows and fetches per step".
* D has no published full-size village result in this repo. D1 here *is* the baseline, and its
  absolute numbers are new.
* Seeds 0-2 only. The family rule (≥ 2 of 3) is the house's; it is weak against seed luck, which is why
  M1 also needs the pooled paired test.
* Changed facts (conflicting bindings across desks) are reported, not gated.
