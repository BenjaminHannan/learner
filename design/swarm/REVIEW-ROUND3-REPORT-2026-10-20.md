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

---

# Round 3, third pass: items 1-5 per the ruling of Oct 20, then the full-branch review (2026-10-20)

## Fixes (commit aefad2808). Every new test fails on c70b3d86e and passes now.

| item | fix | test |
|---|---|---|
| 1 | `MiniTrainer` syncs CUDA before the diagnostics timer | CUDA-path mock: sync once per timed logged step, before the clock; `_sync` calls `torch.cuda.synchronize` on cuda |
| 2 | the box refuses a dirty `git status` in every mode; the dry run checks the committed manifest; the manifest pins all 46 imported repo modules + the box script, from a fresh-interpreter import closure; `manifest --check` on the box also fails on any unpinned import; full-run checkpoints sit under the git-ignored `artifacts/` | `BoxGuardTest` (dirty tree → exit 2 before any step; closure ⊆ manifest; committed manifest matches) |
| 3 (ruled) | pooled tests use item means over seeds, paired over items; the ≥ 2-of-3 rule is unchanged; written into RUNCARD-S0 §2 and S1 M1 before sealing, with the reason and the ruling cited | 6 items flipping in every seed → HOLD (the old 3× pooling gave PROMOTE) |
| 4 | money_stop projection adds each train's measured overhead outside T (C0 probes one short S0 train_d); a required argument; the MAXH × DPH ≤ $4.20 hard cap is unchanged | overhead pushes a $3.28 projection to $3.61, over the $3.50 S0 cap; omitting it is a TypeError |
| 5 | subclasses refuse at build when thinkers > 1 unless they declare `SWARM_COMPATIBLE` themselves; docstring corrected | bare subclass, inherited opt-in, CardBypassMini and QReadMini refuse; flag-off builds |

Tests: swarm + kit + model + train: 120 OK (1 pre-existing skip). Discover: 280, with the same 4 import-time errors as main.

## Full-branch review at aefad2808: 10 findings. **VERDICT: NOT CLEAN. Stopped: no dry run at a sealed commit, no seal, no bid.**

Blocking (confirmed):
1. **The documented dry run always refuses** (`premonition_swarm_box.sh:42/96`). The default DRYRUN `OUT`
   (`artifacts/.../dryrun`) holds 76 files force-added to git by the first dry run. The first log line appends to that
   tracked `box.log`, which dirties the tree before the new clean-tree check. My own dry runs passed only because they
   overrode `OUT`. Fix: default each dry run's `OUT` to a fresh `dryrun-<short sha>` folder, and refuse if `OUT` holds
   any tracked file.

Unequal clock charges that remain (the class item c targeted). Each is small but real:

2. `_recall` scores ASK for all Q × M desks, then keeps desk 0, so S0 pays M× for a training diagnostic. Fix: score
   desk 0's rows only.
3. The final-stretch reading (and the eval pause, which the screen never uses: `eval_every=0`) takes timestamps
   without a CUDA sync, so the last step's queued work is uncounted. That is less than one step in thousands.
4. The GELU/HALT forward hooks on logged steps run inside forward. Their cost differs by arm and counts as training time.

Recommendation for 2-4: **a structural fix, not a fourth patch.** Under `seconds_budget`, run NO tracked diagnostics
in training (no forward hooks, no InsertLog, no `_recall`), for every arm. Losses still log from the step outputs, and
the run cards read none of these diagnostics. Add one `_sync` when the loop ends. That removes the whole class at
once, and the "equal diagnostics charge" machinery (timer, `diagnostic_seconds`) can go.

Lower severity (open): 5 gold mode computes the ASK loss though its weight is 0 (S0's clock pays for it); 6
`desk_asks` counts final-round asks, which cannot fetch (M3's fetch-count half still catches a silent desk); 7
`merge_mask` builds a [Q·M, L, n_ent] tensor per round from an M-times duplicated table; 8 the round rule is written in
three places; 9 there are two `_sync` helpers; 10 `Board.posted` is used only by tests, and IMPLEMENTATION-SPEC §7
still describes the removed per-step metrics and the union recall.

## Status against Q28

Review clean: **no**. Card sealed: no. Dry run at a sealed commit: not run. **C0 + S0 does not book, and no bid is sent.**

---

# Round 3, fourth pass: the dry-run blocker, the structural diagnostics change, items 5, 6, 10 (2026-10-20)

## Fixes (commit 060fc1cb3). Every new test fails on edd38e12b and passes now.

| item | fix | test |
|---|---|---|
| 1 | the dry run's default OUT is a fresh `dryrun-<sha>`; the box refuses before writing if OUT holds a git-tracked file; `CHECK_ONLY=1` runs every refusal check and stops | the documented dry run (DRYRUN=1 PIN=HEAD, default OUT) passes every check on the committed tree and leaves it clean; a tracked OUT is refused untouched |
| 2 (ruled) | with `seconds_budget`, no arm runs any training diagnostic (no hooks, no InsertLog, no recall@k); losses only; the GPU is synced when the loop ends (and before an eval pause). This replaces the `diagnostic_seconds` timer. **Confirmed in RUNCARD-S0 before adopting: no mark reads a removed diagnostic** (train reports are read only for status, train_seconds, steps, final/logged loss, loop_mismatches, seconds_budget, stop) | no hooks/InsertLog/recall under a seconds budget, for both D1 and swarm; flag-off training unchanged; one sync at loop end |
| 5 | gold mode skips the swarm's split and ASK terms when the ASK weight is 0 | split never called in gold |
| 6 | `desk_asks` counts only rounds that can fetch | max desk_asks = rounds - 1 |
| 10 | test-only `Board.posted` removed; IMPLEMENTATION-SPEC §6-9 match the code | n/a |

Tests: 124 OK (one pre-existing skip; the documented-dry-run test runs on the committed tree and passes). Discover:
284, with the same 4 import-time errors as main.

## Full-branch review at 060fc1cb3: 10 findings. **VERDICT: NOT CLEAN. Stopped: no dry run at a sealed commit, no seal, no bid.**

Blocking:
1. **C0 benchmarks a different workload than the training it calibrates** (`premonition_swarm_screen.py`, `fresh_trainer`).
   Its MiniTrainer has no seconds budget, so `train_diagnostics` stays on and every timed C0 update computes recall@k
   (4x wider for S0). T (from D1's FLOP/s) and the 2.5x stop ratio both come from that bench. Fix: C0's trainers run
   exactly as the screen trains (diagnostics off), plus a test that `fresh_trainer`'s model has `train_diagnostics`
   False and that `_train_step` registers no hooks there.
2. **A rerun dies late, after paid work** (`premonition_swarm_box.sh:50`). The existing-checkpoint refusal fires only at
   the first `train` step, after the data build and C0, and a failed dry run leaves `ckpt-dryrun` behind. Fix: put
   CKPT under the per-run OUT (fresh per commit), make it overridable, and check it in the pre-flight (CHECK_ONLY too).
3. **An OUT outside the repo crashes the script** (exit 128 from `git ls-files` under `pipefail`) instead of refusing.
   Fix: refuse an OUT outside the repo explicitly (exit 2), or treat outside as untracked.

Lower severity (open): 4 the round rule is written in three places; 5 round-invariant masks are recomputed every
round (D1's forward does the same once per loop, so it is no bias); 6 `swarm_answer` repeats the answer preamble;
7 `merge_mask` memory (M duplicate tables); 8 `_recall` computes all desks and keeps desk 0 (training with
diagnostics on only; it also inflated C0 under finding 1); 9 the diagnostics switch mutates the model; 10 gold-phase
recall is absent for the swarm in FLOP-budget runs.

## Status against Q28

Review clean: **no**. Card sealed: no. Dry run at a sealed commit: not run. **C0 + S0 does not book, and no bid is sent.**
Recommendation: one round for 1-3, and 8 with it, since it is the root of C0's extra recall cost.

---

# Round 3, fifth pass: C0 = run trainer, refusals before paid work, OUT placement, desk-0 recall (2026-10-20)

## Fixes (commit 682dfdbd4). Each new test fails on 832480799; on the committed tree all 8 box tests run and pass.

| item | fix | test |
|---|---|---|
| 1 | C0's bench trainers are built from the run's single `RUN_SETTINGS` (passed by `cmd_train` to `train_d`) and the same `d_trainer` constructor `train_d` uses; they have a seconds budget, so training diagnostics are off as in the runs | bench vs run trainer field by field (config, curriculum, flop budget, tolerance, seed, device, budget set, diagnostics off, model config) through the real cmd_train → train_d kwargs |
| 2 | checkpoints at `<OUT>/ckpt` (CKPT overridable, relative, git-ignored); a non-empty checkpoint folder is refused in the pre-flight, before data and C0 | a real dry run on an OUT holding a checkpoint exits 2 with no data.json or c0.json |
| 3 | an OUT outside the repo, or not git-ignored, is refused with exit 2 before anything is written | outside OUT → exit 2 (not 128), nothing written; non-ignored OUT and absolute CKPT refused |
| 4 | `_recall` scores desk 0's Q rows only | store.ask sees Q rows once (not Q·M); same value as before |

Tests: 129 OK (3 skips: one pre-existing, two that need a committed tree and pass on it). Discover 289, with the same 4 errors.

## Full-branch review at 682dfdbd4: 10 findings. **VERDICT: NOT CLEAN. Stopped: no dry run at a sealed commit, no seal, no bid.**

Blocking (all confirmed in code):
1. **The S1 readout can PASS a collapsed S1** (`premonition_swarm_marks.py:614`). The PASS branch checks only "the board
   collapsed the desks" (S1 collapsed and S0 not). If both are collapsed, S1 PASSes with the COLLAPSED text, but RUNCARD-S1
   M5 says "as S0 M4", which forbids the positive verdict for a collapsed swarm. Fix: S1 collapsed → HOLD.
2. **Symlinked paths make the box refuse its own default OUT** (`box.sh:31/62`). `realpath -m` resolves OUT's symlinks,
   but ROOT comes from `pwd`. On a box where `/workspace` or `artifacts/` is a symlink, the default OUT looks
   "outside the repository" (exit 2), so the paid run cannot start. Fix: `ROOT=$(realpath ...)` too, plus a symlink test.
3. **The EXIT trap re-packs the copy-back tarball on every exit, refusals and CHECK_ONLY included** (`box.sh:103`).
   A pre-flight re-run on a finished OUT deletes and rebuilds `swarm-screen-out.tgz`, so its sha256 no longer matches the
   one logged at DONE. Fix: arm the trap only once the first step starts, and never touch an existing tarball.
4. **The M5 "no non-finite loss" check sees only the last 5 logged windows**, because `trim_history` runs before the
   train JSON is written. Fix: count non-finite logged losses over the full history before trimming, and gate M5 on the count.
5. **M3's fetch-count test passes when every desk fetched nothing** (`marks.py:356`): 0 ≥ 0.1 × 0. Fix: also require the
   busiest desk's fetch_count > 0.
6. **C0's probe checkpoints sit in CKPT.** If C0 is killed (the MAXH timeout), they are left there, and PART=s0 on that OUT
   then refuses with advice that cannot work (a fresh OUT has no data.json or c0.json). Fix: probes go to a separate
   `<OUT>/c0-probe` scratch folder, removed at C0 start.

Lower severity (open):

7. `swarm_answer` treats `max_loops` as a fixed round count, not a cap (the screen uses the default).
8. The split and post loops cost kernel launches. That is the swarm's own implementation cost, and C0 measures it honestly.
9. `merge_mask` memory.
10. Duplicated helpers: `_sync`, MODES, the round rule.

## Status against Q28

Review clean: **no**. Card sealed: no. Dry run at a sealed commit: not run. **C0 + S0 does not book, and no bid is sent.**
Recommendation: one round for 1-6 (each small and testable), with 7 alongside since it is one line.
