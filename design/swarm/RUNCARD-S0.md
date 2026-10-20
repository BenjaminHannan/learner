# RUN CARD S0: parallel independent desks + combiner, NO communication (the kill screen)

**Status: DRAFT, NOT SEALED. Written 2026-10-17, before any swarm run of any size, on any data, CPU or
GPU.** Two things must happen before sealing: (1) the coordinator accepts or replaces the PROVISIONAL
ruler mapping in §2 (design §0 items 2-3), and (2) §C0 of `FUNDING-BID.md` reports D's speed numbers,
which fix T in §1. After sealing, amendments follow the house rule: dated, written before the result
files they concern are read, original text kept.

**2026-10-18 (pre-seal, no swarm result exists):** (1) is done: the coordinator confirmed all three §0
resolutions as written (ruling Q27). Sealing still waits on: the coordinator code review (Q26); a CPU dry run
of the box kit (`design/swarm/BOX-SPEC.md`) showing every mark computable; and C0's T. Three pre-seal
clarifications are made below and marked "(10-18)": DEV slip is per seed and never averaged, M5 drops
`gold_missing` because `train_d` does not log it, and the verdict precedence is fixed.

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
* **(10-20, pre-seal) The card split rule is part of the mechanism under test.** In training, each round's
  still-needed gold cards are split across the desks by their own ASK scores, and **every desk gets ⌊n/M⌋ or
  ⌈n/M⌉ of the n cards** (desks below the floor are served first). It is the same in S0 and S1, and it is used
  only in training, never at inference. This replaces a cap-only rule that could leave a desk with none (review
  round 3, item a). It is settled here, before any run.
* **(10-20, pre-seal) What "equal T" charges.** With `seconds_budget` set, **no arm runs any training
  diagnostic**: no forward hooks (dead-unit fraction, halt rate), no `InsertLog` / `card_stats`, no recall@k.
  The log records the window's losses, the last step's grad norm (already computed for clipping) and throughput
  counters; the weight norm is skipped (10-20, item 16). The GPU is synced before the clock is read when the loop
  ends. So equal T means
  equal training work for D1, S0 and S1 (coordinator ruling, Oct 20, third pass). **Confirmed before adopting it:
  no mark of this card or of RUNCARD-S1 reads any of the removed diagnostics.** From the train reports the readout
  reads only `status`, `train_seconds`, `steps`, `final.loss`, the logged losses in `history`, `loop_mismatches`,
  `seconds_budget` and `stop` (`premonition_swarm_marks.py`, validity block). M1-M4 and M6 read the eval files, and
  the diversity report comes from evaluation.
* **(10-20, pre-seal, sixth pass; its formula is superseded by the next bullet) The T formula, exactly.** C0 times D1 over its timed batches and counts the
  FLOPs of those same batches per curriculum mode. T_raw = F / (D1's FLOP/s), where D1's FLOP/s is weighted by the
  curriculum's FLOP shares: T_raw = F · Σ_m w_m · s_m / f_m (w_m the mode's FLOP share, s_m its measured seconds per
  update, f_m its FLOPs per update, over the same timed batches). T = min(3600, 300 · ceil(T_raw / 300)). This is
  what "the seconds D1 needs for F FLOPs" means; the earlier text weighted update shares and averaged FLOPs over
  more batches than were timed (sweep item 17). **An unregistered T is refused, not only detected:** the box
  refuses `--t-override` off the dry run and refuses to train when c0.json's T differs from its formula T, and the
  readout VOIDs such a folder (item 4).
* **(10-20, pre-seal, eighth pass) The T formula is the time-share one.** A seconds-budget run splits its
  phases by TIME (`MiniTrainer.plan` reads train_seconds / seconds_budget). So in T it spends w_m · T seconds in
  mode m at D1's FLOP/s f_m / s_m there. D1 then spends F FLOPs in **T_raw = F / Σ_m w_m · (f_m / s_m)**, with
  w_m = 0.05 / 0.25 / 0.70 (gold / teacher / own), s_m D1's measured seconds per update and f_m its FLOPs per
  update over the same timed batches. T = min(3600, 300 · ceil(T_raw / 300)) as before. The sixth pass's
  F · Σ w_m s_m / f_m treated the shares as FLOP shares, so D1 trained for T would not spend F (sweep, seventh
  pass, item 4). Adopted by the coordinator session (session_014a7yFK9adwx14ocaqRQ6eZ, ruling of 2026-10-20) as a
  correction, not a moved bar: the card is unsealed and no C0 or S0 data exists. Both arms get the same T either
  way.
* **(10-20, pre-seal, ninth pass) Three rulings of the coordinator session (session_014a7yFK9adwx14ocaqRQ6eZ,
  2026-10-20), adopted before any C0 or S0 data exists. Each takes the stricter, consistent option.**
  (a) **The C0 stop ratio is the steps-in-T ratio:** Σ_m w_m / s_m(D1) ÷ Σ_m w_m / s_m(S0m4), with w_m the time
  shares and s_m the mean seconds per update (total timed seconds / timed updates). That is how many times fewer
  updates S0 gets in T than D1. Stop and ask above 2.5. The earlier update-share average of s/update understated
  it (sweep example: 2.29 vs 2.56). T_raw also uses the mean s_m, matching the mean FLOPs per update f_m.
  (b) **Cells:** `far_deep`, `near` and `overall` each need ≥ 100 items in every eval file, else INSUFFICIENT.
  By construction they can reach that: even the tiny dry-run validation split has `overall` 188, `near` 105 and
  `far_deep` 62 per file. The large split is many times bigger, and `far_deep` is its smallest gated cell.
  (c) **The C0 item's $0.70 hard cap is enforced as a sub-cap inside the $4.20 total.** Data + C0 stop at
  BOX_START + 0.70 / DPH hours.
  The registered C0 is also enforced. No extra C0 arguments are allowed off the dry run, and the box gate and M5
  require size full, device cuda, the registered bench settings, a real dph, and a C0 run at the pinned commit.
* **(10-20, pre-seal, sixth pass) Gold mode keeps the ASK terms in both arms.** D1's gold forward keeps a
  zero-weight ASK term (its ASK head gets a zero gradient and AdamW decays it). The swarm now does the same; the
  earlier skip left S0's ASK head out of the graph and undecayed (sweep item 15, ADOPTED by the coordinator,
  Oct 20).
* **Matched parameters (reported, separately).** D1 2,102,228 (v2) vs S0 2,102,740 (+512 desk embeddings, +0.02%).
* **Reported, not matched:** steps, tokens, think FLOPs per question, s/step, peak GPU memory.
* Eval: `evaluate_d_checkpoint(split="validation")` (label-free), max_loops default. S0 is fixed at 4
  rounds and does not halt; D1 halts by HALT, at most 8 loops.

## 2. Rulers (CONFIRMED by the coordinator, ruling Q27, 2026-10-18; see design §0)

* **Primary: held-out join** = the `far_deep` decision cell (knowable ∧ ¬evidence_kept ∧ depth ≥ 2,
  exclusions applied, `premonition/slices.py`) on the **validation** split (held-out villages). The test
  split is **not** touched by S0 or S1.
* **Forgetting guard: DEV slip** = the `near` and `overall` cells on validation. Family rule: **≥ 2 of 3
  seeds**. (10-18, Q27) Judged **per seed, never averaged**. A slip that shows only in the 3-seed mean
  does not count.
* Statistics: paired by item (and seed, when pooled), `learnlab.metrics.paired_greater_pvalue`,
  α = `policy.ALPHA` = 0.01, margin `policy.MIN_EFFECT` = 0.03, cells need ≥ `MIN_ITEMS` = 100 items
  per seed.
* **(10-20, pre-seal) Pooling unit = the item.** Every seed scores the SAME validation items, so (item, seed)
  pairs are not independent. Item difficulty is shared across seeds, and pooling them as separate pairs overstates
  significance (pseudo-replication). So each item's correctness is **averaged over the 3 seeds for each arm**, and
  the paired test (`paired_greater_pvalue`: a sign-flip permutation test on the non-binary item means) runs **over
  items**. The pooled Δ is the mean item-mean difference. The ≥ 2-of-3-seeds condition is unchanged. It removes
  the over-counting, so in general it is the stricter test. Source: review round 3, item 3, ruled by the coordinator session
  (session_014a7yFK9adwx14ocaqRQ6eZ, 2026-10-20), which states that Ben delegated tonight's decisions to it. It is
  adopted before sealing, with no S0/C0 data in existence. The same rule applies to every pooled test in RUNCARD-S1.

## 3. Marks (registered; each run once)

| mark | bar |
|---|---|
| **M1 join (promote)** | pooled over 3 seeds (item means, §2, 10-20), S0 `far_deep` ≥ D1 + 3.0 points, and p(S0 > D1) < 0.01 paired over items; **and** S0 > D1 on ≥ 2 of 3 seeds |
| **M2 DEV slip (guard)** | on ≥ 2 of 3 seeds, S0 `near` < D1 `near` − 3.0 points → **FAIL**; same rule for `overall`, judged separately. Per seed, never averaged (10-18) |
| **M3 desk usage (guard)** | on every one of ≥ 2 of 3 seeds: every desk's eval `ask_rate` ≥ 0.05, the busiest desk fetched at least one real card (`fetch_count` > 0), and every desk's `fetch_count` ≥ 0.10 × the busiest desk's. Otherwise the breadth was not used → **FAIL (USAGE-COLLAPSE)**. (10-20, pre-seal: the "> 0" makes explicit that no fetch at all is unused breadth; the ratio alone passed 0 ≥ 0.1 × 0) |
| **M4 diversity (guard)** | the readout prints `fetch_overlap`, `register_cos`, `ask_rate[4]`, `fetch_count[4]`, `silent_desks` per seed. If `collapsed` (register_cos > 0.95 **and** fetch_overlap > 0.8) on ≥ 2 of 3 seeds, the verdict line reads **"COLLAPSED: the desks are copies"** and the verdict cannot be PROMOTE |
| **M5 matching (validity)** | every run's train seconds within T ± 2%; same data tag, tokenizer digest, eval items for every arm; `loop_mismatches` = 0 in every train report; no NaN loss. (10-18: `gold_missing` dropped. `train_d` does not log it. The gold-to-card mapping is covered by `test_premonition_model` / `test_premonition_swarm`.) Otherwise the run is **VOID** and reruns once under this same card |
| **M6 cells** | `far_deep` has ≥ 100 items per seed; otherwise **INSUFFICIENT** (no verdict). (10-20, pre-seal, ninth pass: `near` and `overall`, the M2 guard's cells, must each have ≥ 100 too, as §2 says. See §1.) |

**Verdict:**
* **PROMOTE to S1** only if M1 passes and M2, M3, M4, M5, M6 hold.
* **KILL** if pooled S0 − D1 on `far_deep` ≤ 0, **or** S0 < D1 on ≥ 2 of 3 seeds. The swarm line stops.
  S1 is not booked unless the coordinator explicitly overrides (see §6).
* **FAIL** if a guard (M2, M3) fails, whatever M1 says.
* **HOLD** otherwise (a gain between 0 and 3 points, or not significant). No S1 without a coordinator
  ruling.
* Readout VOID if any mark cannot be computed from the files (schema mismatch).
* **Precedence (10-18), when more than one applies:** VOID > INSUFFICIENT > KILL > FAIL > PROMOTE > HOLD.
  KILL outranks a guard FAIL, because a worse swarm stops the line whatever else broke. A COLLAPSED result
  that meets M1 is HOLD, and its verdict line carries the COLLAPSED text.
* The readout program is `scripts/premonition_swarm_marks.py --card S0` (box kit, `BOX-SPEC.md`). It is the
  program the CPU dry run exercised.

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
* (10-18) **What "matched wall-clock" includes.** `train_seconds` counts everything in the training loop:
  host-side batch collation as well as GPU steps. A faster-stepping arm (D1) therefore spends a larger
  share of T on collation. That is what equal wall-clock means here, and steps are reported beside it.
* (10-18) **Tokenizer.** Both arms use the v2 contender tokenizer `premonition-tok-v2-fallback.json`
  (7,068 ids, digest 2c9d06aed330), the only one `premonition.identity` admits for primary scoring.
  It was fitted on the fallback pattern text, while the village now renders the real pattern bank, so
  `build_tokenizer` logs a warning. Both arms see the same tokens, so the comparison is fair. Absolute
  accuracy may sit below what a matched tokenizer would give.
