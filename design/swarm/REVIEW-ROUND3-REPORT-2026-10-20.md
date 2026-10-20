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

---

# Round 3, second pass: fixes for a-c, then the full-branch review again (2026-10-20)

Ruling (coordinator session_014a7yFK9adwx14ocaqRQ6eZ, Oct 20): GO on a-c, each with a regression test that fails on the old
code; carry non-blocking items only if they are a few lines in files already touched; then the full-diff review. If clean:
the 120 s dry run at the sealed commit, seal, bid. If not: stop and report. Spend $0.

## Fixes (commit e5ec841a6). All 8 new tests fail on baf1e071e and pass now.

| item | fix | test |
|---|---|---|
| a | `balanced_assignment`: every desk gets ⌊n/M⌋ or ⌈n/M⌉ (below-floor desks served first). **The rule is written into RUNCARD-S0 §1 as part of the mechanism (10-20, pre-seal).** | 4 desks × 6 cards (was [2,2,2,0]); floor/ceil property for M = 3, 4, 8 |
| b | runner refuses BEFORE training if the checkpoint path exists | `CheckpointRefusalTest` (train_d never runs) |
| c | no per-step swarm diagnostics in training; the split uses a static number of picks and unmasked writes (no sync); with a seconds budget no arm records card insertions, and post-step diagnostics are timed off `train_seconds` (card §1, 10-20) | no-diagnostics test, split no-sync test, equal-charge test |
| d (carried) | `seconds_budget` survives checkpoint and resume | resume test |
| e (carried) | `train_seconds` counts the final stretch however the loop ends | in the equal-charge test |
| f (part) | training recall is desk 0's, comparable with D1 and validation | n/a |
| g (carried) | `answer_with_gold` refuses a swarm | guard test |
| h (carried) | `Board.post` runs the FIFO on ids, then writes the board once | the exact row-contents and no-sync tests still pass |

Still open from round 3: f's loop metric (desk-rounds in training against rounds in validation; documented). Tests: 113 OK
(1 pre-existing skip); discover 273 run, with the same 4 import-time errors as unmodified main.

## Full-branch review at e5ec841a6: 10 findings. **VERDICT: NOT CLEAN. Stopped: no dry run at a sealed commit, no seal, no bid.**

New and blocking (1-3 confirmed in code):
1. **My item-c timing is wrong on CUDA** (`train.py:341`). `began` is read before the queued backward and optimizer step
   finish. The first `.item()` then waits for them, so GPU training time is counted as `diagnostic_seconds` and cut from
   `train_seconds`. The bias differs by arm (S0's backward is heavier), and M5 cannot see it. Fix: `torch.cuda.synchronize()`
   before `began` when timed, plus a test that the timed block starts after a sync (CPU: a recorded call).
2. **The box does not refuse a dirty working tree** (`premonition_swarm_box.sh:98`). The run imports modules outside the
   18-file manifest (`learnlab/train.py`, `learnlab/ckpt.py`, `learnlab/tokenizer.py`, `learnlab/village/*`,
   `premonition/pointer.py`), so an uncommitted edit to one of them passes "HEAD == PIN" and "manifest OK". Fix: refuse
   unless `git status --porcelain` is empty (the dry run must then commit its manifest first), and widen the manifest.
3. **The pooled p-value in M1 (and in S1's M1/M2) treats the 3 seeds' identical validation items as independent pairs**
   (`premonition_swarm_marks.py:272`). Every seed is scored on the same items, so item difficulty is shared and
   significance is overstated. The card's §2 says "paired by item (and seed, when pooled)". **This is a method choice in a
   pre-registered card, and under the standing rule a bar or method change goes to Ben.** Options: (i) a per-item average
   over seeds (each item's mean correctness for S0 vs D1), paired over items; (ii) a seed-blocked test (a paired test per
   seed, then combined), or a permutation test over item-level seed means; (iii) keep the card as written. I recommend (i):
   it is the simplest honest unit, and the per-seed ≥ 2-of-3 condition stays as written.

Validity, not blocking for correctness:

4. `projected_box_hours` counts a train as exactly T, but each train also spends time on caches, calibration, the final
   validation and the save (the dry run: about 60% over T at T = 30 s, and much less at T ≥ 300 s), so `money_stop` can
   under-predict. Spend is still hard-capped by MAXH × DPH ≤ $4.20. Fix: project with measured overhead (C0 can time one
   short `train_d`).
5. Subclasses (`address_reader`, `direct_reader`, QRead variants) do not compose with thinkers > 1, despite the docstring.
   Fix: refuse at build and correct the docstring. No subclass is in the screen.

Cleanups (open): 6 `planned_loops` duplicates the swarm round rule; 7 `Board.post`'s column loop costs launches (S1 only);
8 `swarm._recall` duplicates `_recall`; 9 `swarm_forward` duplicates about 40 lines of `forward`; 10 InsertLog guards sit at
call sites.

## Status against Q28

Review clean: **no**. Card sealed: no. 120 s dry run at the sealed commit: not run (it waits for a clean review).
**C0 + S0 does not book, and no bid is sent.** Next, on a ruling: fix 1-2 (and 4-5) with tests, and settle 3 (Ben).
