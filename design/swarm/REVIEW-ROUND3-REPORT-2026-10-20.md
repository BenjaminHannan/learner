# Swarm: review fix round 3, report (2026-10-19/20)

Ruling (new coordinator, Oct 19, by cross-session message from session_014a7yFK9adwx14ocaqRQ6eZ on Ben's account, title
"Learner-New coordinator handoff"): GO on the two blocking round-2 items; then run the built-in review on the **full branch
diff** and record the verdict here. Spend $0, CPU only. **Code stays DRAFT. Nothing seals or books.**

## 1. Fixes (commit 755f377d0)

| item | fix | regression tests (each fails on d58a18ada) |
|---|---|---|
| 1 host sync per forward in `entity_table` | `torch._assert_async(ents.max() < n_ent)`: a device-side assert on CUDA, raises at once on CPU | `test_entity_table_range_check_reads_nothing_on_the_host`; `test_out_of_range_entity_id_raises` (now `RuntimeError`); `test_flag_off_never_builds_the_entity_table` (with thinkers == 1 the table is never built, and losses, gradients and answers are bit-identical to the frozen pre-swarm copy for all 3 variants) |
| 2 BOX-SPEC said dry-run T = 30 | BOX-SPEC lines 51 and 113 now say 120, as the kit runs, with the reason recorded; the kit is unchanged | n/a |

Test-only: the no-sync recorder now inspects only the index tuple of index/index_put (this removes round 2's finding 5,
a false positive on bool values). The manifest is regenerated.

**Tests:** swarm + box kit + model + train: 105 run, OK (1 pre-existing skip). Discover over `test_premonition_*.py`:
265 run. The same 4 import-time errors occur on unmodified 73b8e0224.

## 2. Built-in review, FULL branch diff (main...755f377d0): 10 findings. **VERDICT: NOT CLEAN. New blocking issues,
so I stopped: no patch, no seal, no bid.**

Blocking: they bear on whether the S0 kill screen is valid or fair. Items a and b are confirmed in code.
- **a. `balanced_assignment` can leave a desk with no target** (`swarm.py:165`). It caps each desk at ceil(|need|/M) but
  sets no floor. Reproduced: 6 needed cards, M = 4, desks 0-2 preferring every card gives [2, 2, 2, 0]; 5 cards give
  [2, 2, 1, 0]. The docstring's "every desk gets floor or ceil" is false, and the tests only cover M = 2. This trains the
  desks with lower scores to stay silent, which pushes S0 toward the M3 USAGE-COLLAPSE guard: a bias inside the
  mechanism under test. Fix: also enforce a floor of floor(|need|/M) per desk, via a min-cost/greedy fill that serves
  desks below the floor first; add M = 3, 4 and 8 tests.
- **b. A rerun on the same box wastes paid GPU time** (`premonition_swarm_box.sh:155`). Checkpoints go to fixed paths
  and `learnlab.ckpt.save_checkpoint` refuses to overwrite. A VOID rerun (allowed once by M5), or PART=s0 after a
  partial run, trains the full T and then raises at save, so no train JSON is written. Fix: refuse before training if
  the checkpoint exists, or give each attempt its own folder.
- **c. Timing fairness of the matched wall-clock screen.** These charge the arms' training clocks unequally:
  - c1: each swarm training step computes unused diagnostics (`swarm_register_cos`, `swarm_fetch_overlap`,
    `swarm_ask_rate`) with host syncs (`swarm.py:404`);
  - c2: `balanced_assignment` syncs on every pick (`swarm.py:170`);
  - c3: on tracked steps D1 alone pays for `InsertLog` + `card_stats` (`train.py:318`).
  c1 and c2 bias against S0 and c3 favours it, and all three move the C0 ratio that drives stop-and-ask. Fix: make the
  swarm path sync-free (diagnostics only on tracked steps, unmasked writes in the assignment), and either skip card
  diagnostics for every arm in screen runs or charge them outside `train_seconds`.

Non-blocking:
- d. A resumed run loses `seconds_budget`, because `checkpoint_config` / `resume_trainer` don't carry it (no resume in the box).
- e. The final step's time is not added to `train_seconds` when the loop ends some other way than the seconds budget.
- f. The swarm's retrieval and loop metrics are not comparable to D1's.
- g. `answer_with_gold` has no swarm guard.
- h. `Board.post` rewrites the whole board once per column.

## 3. Status against the Q28 gates

Review clean: **no**. Card sealed: no. Dry run at a sealed commit: no (the last dry run, at d58a18a, predates these fixes,
and the sealed commit must follow the next round). C0 stop-and-ask: in force. **C0 + S0 does not book, and no bid is sent.**
Next: a fix round for a, b and c (on a ruling), with regression tests, then the full-diff review again; if clean, the
120 s dry run at the sealed commit, then the seal, then the bid with the sealed commit's hash.
