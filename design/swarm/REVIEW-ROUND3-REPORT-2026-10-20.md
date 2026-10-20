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

---

# Round 3, sixth pass: items 1-7 fixed, then ONE complete highest-effort sweep (2026-10-20)

## Fixes (commit bf0f8d894). Each new test fails on 033f7c62b; on the committed tree all 14 box tests run and pass.

| item | fix |
|---|---|
| 1 | the S1 readout enforces "as S0 M4" exactly: a collapsed S1 never PASSes, whatever S0 does |
| 2 | the box takes ROOT as a physical path (`pwd -P`), so a symlinked repo path is not "outside the repository" |
| 3 | the copy-back archive is packed only at a successful end, never on a refusal or failure, and an existing archive is never changed |
| 4 | a non-finite logged loss anywhere in the full history voids M5 (`nonfinite_logged_steps`, counted before trimming) |
| 5 | M3 fails when the busiest desk fetched nothing (the card's wording says so) |
| 6 | C0's probe checkpoints go to `<OUT>/c0-probe`, cleared when C0 starts and never packed |
| 7 | `swarm_answer`'s `max_loops` caps the trained rounds |

Tests: 136 OK (3 skips: one pre-existing, two needing a committed tree and passing on it). Discover 296, with the same 4 errors.

## The sweep (max effort, all findings, full branch diff at bf0f8d894): 21 findings. **NOT CLEAN. Stopped: no seal, no bid.**

The reviewer confirmed that flag-off holds and that the S0/S1 marks and verdict precedence match the cards. It ran
read-only checks on: the exit-141 case, the awk money bypass, the parameter counts, the manifest, and the gold-mode
gradient difference. The full list, grouped for one closing round:

**A. Money and paid time (blocking)**
1. C0 never checks the trainer's 14 GiB reserved-memory guard. The bench calls `_train_step` directly, and the probe
   `train_d`'s "aborted" status is ignored. A swarm arm can pass C0 and then abort at the first S0 train, after D1-s0
   (paid) has run. Fix: C0 runs `_check_memory` on every timed arm, and fails C0 (stop-and-ask) on a guard trip or on
   any probe status other than completed.
2. After C0, nothing checks that the remaining MAXH covers `projected_s0_box_hours`, and the default MAXH (8 h) is below
   the bid's own C0 + S0 estimate (8.5 h). The marks step can be cut at MAXH after the money is spent. Fix: refuse to
   start the trains unless the remaining MAXH ≥ the projection × a margin, and set the default MAXH from the bid.
3. The money guard is per invocation, so PART=c0 then PART=s0 on one box can total more than CAP. Fix: record the money
   spent (wall time × DPH) in OUT and charge it against CAP across parts.
4. The readout accepts any T in c0.json: `C0_EXTRA='--t-override …'` works on the real box, and M5 never checks
   `t_override`, the train `size`, or the eval regime/identity. Fix: refuse `--t-override` unless DRYRUN; M5 requires
   `t_override is None`, `T == T_formula`, size "full", and a primary identity on the real card.
5. DPH, CAP and MAXH are never checked to be numbers, so awk string comparisons can bypass the cap. Fix: validate them
   as positive decimals.

**B. Box kit robustness and honesty**

6. `cmd_train` returns 2 for an aborted train, which looks like "refused". Fix: a distinct exit code for a failed step.
7. `git ls-files … | head` under pipefail dies with exit 141 (SIGPIPE) on a large tracked OUT. Fix: no pipe (`--error-unmatch`-free count, or `ls-files -z` into a variable).
8. A VOID rerun has no clean route, and a dry-run rerun is not blocked: same-OUT PART=s0 overwrites files and then
   cannot pack, and the dry run deletes its CKPT, so a rerun passes. Fix: one rule: a run needs a fresh OUT; refuse an
   OUT holding any train/eval/MARKS file; document "rerun = fresh OUT, PART=s0 copying data.json/c0.json read-only".
9. CHECK_ONLY exits before the PART=s0 prerequisite check and the c0 stop-flag check. Fix: run them under CHECK_ONLY too.
10. `pack` leaves out `^ckpt` by name, not the actual (overridable) CKPT. Fix: exclude `$CKPT` itself.
11. host.txt is overwritten on each run, and c0.json's T is not tied to the training host. Fix: per-part host files, and
    PART=s0 refuses when the GPU name or uuid differs from C0's.
12. The runner's default `--ckpt-dir checkpoints/swarm-screen` is not git-ignored. Fix: default under artifacts/.

**C. Readout robustness**

13. Item-set equality is enforced only within a seed; the pooled test silently intersects across seeds. Fix: VOID if a seed's item set differs.
14. Malformed or short per-desk lists (`fetch_count: []`, 3 entries for 4 desks) crash or score as valid. Fix: VOID (schema)
    unless every list has exactly the arm's desk count of finite numbers.

**D. Equality of the arms (fairness, small)**

15. The gold-mode skip (item 5 of the previous pass) changes optimizer behaviour. D1's forward keeps a zero-weight ASK
    term, so the ASK head gets a zero gradient and AdamW decays it, while S0's head is out of the graph and not decayed.
    The reviewer checked this on the tiny model. Fix: make D1 and S0 equal: the swarm keeps its ASK terms in gold, as
    D1 does (so the head decays in both).
16. `log()` still computes `weight_norm()` and a few `.item()` syncs every 50 steps, so the card's "only losses are
    logged" is literally false (cost well under 0.1% of T). Fix: skip `weight_norm` under a seconds budget, and correct the card text.
17. The T formula weights curriculum shares as update shares, and averages FLOPs over 50 batches against time over 40.
    That can move T by one 300 s step near a boundary. Fix: T = F / (FLOP-share-weighted FLOP/s) over the same timed
    batches, which is what the card's "the seconds D1 needs for F FLOPs" means.
18. Round-invariant masks are recomputed every round (host syncs), a cost only S0 pays. Fix: compute them once before the loop.

**E. Tests and cleanups**

19. Importing the runner in tests mutates os.environ (TMPDIR and others) for the whole process. Fix: a fixture that
    restores the environment.
20. Duplicated `_sync`, MODES and round rule. Fix: one shared definition each.
21. `s1_card` recomputes the diversity rows and appends VOID reasons twice. Fix: reuse the first pass.

## Status against Q28

Review clean: **no**. Card sealed: no. Dry run at a sealed commit: not run. **C0 + S0 does not book, and no bid is sent.**
Recommendation: close all 21 in one round, each with a test that fails on the old code. Item 15 changes the training
objective in gold mode back to D1's (equal arms), so it should be stated in the card. Then a full sweep again.

## Seventh pass: all 21 closed (coordinator ruling Oct 20: "close all 21 findings in one round")

Each fix has a regression test. **Every new test was run against the old code (3bc376ceb, with the new test
files copied in) and fails there** (27 tests, classes `SixthPass*` in both swarm test files, plus
`ThirdPassTest.test_gold_mode_keeps_the_ask_terms_like_d1`). Item 19's fix lives in the test file itself, so its
test was shown to fail with the restore lines removed. The box tests run the REAL box script in a throwaway clean git
repo, with a stand-in runner and readout, so every refusal, money and exit path is reached on a CPU host.

| # | fix | test |
|---|---|---|
| 1 | `time_run` checks the run trainer's memory guard after each chunk; an arm that trips it fails (D1/S0m4 → C0 stops); an incomplete overhead probe stops C0 | `test_the_c0_bench_trips_the_run_trainers_memory_guard`, `test_an_aborted_overhead_probe_stops_c0` |
| 2, 3, 5 | CAP is the total across invocations: a box ledger (box_start, dph, cap), refused on mismatch or when no money is left; hard stop = box_start + CAP/DPH (MAXH may only cut it); DPH/CAP/MAXH must be positive decimals; the bid's 8.5 h × DPH > CAP refuses ("a revised bid is needed"); projected S0 beyond the money left → exit 3, not overridable | `test_the_bid_hours_…`, `test_money_inputs_…`, `test_the_total_persists_…`, `test_the_first_invocation_starts_the_ledger_…`, `test_a_projected_s0_beyond_the_money_left_…` |
| 4 | an unregistered T is refused: C0_EXTRA `--t-override` off DRYRUN, runner `--t-override` off tiny, box gate T ≠ T_formula; readout VOIDs a non-formula T, a non-full train or a non-primary eval (`--dry-run` relaxes this for the CPU dry run only) | `test_an_unregistered_t_is_refused`, `test_c0_refuses_a_t_override_…`, `test_an_unregistered_T_voids_the_readout`, `test_tiny_runs_and_non_primary_evals_…` |
| 6 | a failed step exits 5 (no archive) | `test_a_failed_step_exits_5_and_packs_nothing` |
| 7 | the tracked-files check has no pipe (no exit 141) | `test_an_out_with_many_tracked_files_is_refused_not_141` |
| 8 | one run per OUT; rerun = fresh OUT with `PART=s0 FROM=<old OUT>` (copied read-only, sha256 logged) | `test_one_run_per_out`, `test_part_s0_from_an_earlier_out_…` |
| 9, 11 | CHECK_ONLY runs PART=s0's input check, the GPU tie and the C0 gate; per-part host records; PART=s0 refuses a different GPU | `test_check_only_covers_part_s0s_inputs_host_and_gate` |
| 10 | the archive excludes the actual CKPT and c0-probe | `test_a_full_run_packs_without_the_actual_ckpt_…` |
| 12 | the runner's default `--ckpt-dir` is under artifacts/ (git-ignored) | `test_the_runners_default_checkpoint_folder_is_git_ignored` |
| 13 | VOID when item sets differ across seeds | `test_item_sets_that_differ_across_seeds_are_void` |
| 14 | per-desk lists: exactly the arm's desk count of finite numbers, else VOID (schema) | `test_per_desk_lists_must_have_one_finite_number_per_desk` |
| 15 | **ADOPTED**: gold mode keeps the ASK terms, as D1 does (the skip is reverted; recorded pre-seal in RUNCARD-S0 §1) | `test_gold_mode_keeps_the_ask_terms_like_d1` |
| 16 | no weight norm under a seconds budget; card text corrected | `test_weight_norm_is_not_computed_under_a_seconds_budget` |
| 17 | `T_raw = F · Σ w_m s_m / f_m` over the same timed batches (`t_raw_from_modes`); card text records it | `test_t_raw_weights_flop_shares_by_each_modes_own_speed` |
| 18 | round-invariant masks hoisted (losses and gradients bit-identical to the old code in teacher and own mode, checked) | `test_round_invariant_masks_add_no_sync_per_round` |
| 19 | the tests restore the environment after importing the runner | `test_importing_the_runner_leaves_the_test_environment_alone` |
| 20 | one `_sync` (train), one MODES (model), one round rule (`swarm.rounds_for`, used by planned_loops, swarm_forward, swarm_answer) | `test_one_round_rule_and_one_modes` |
| 21 | s1_card reuses M5 / M5b's rows (one pass per arm) | `test_s1_computes_each_arms_diversity_rows_once` |

**Found while testing (new, fixed):** `pack` tarred OUT into a file inside OUT. GNU tar then fails with "file
changed as we read it" (exit 1), so a full run would have failed at its very last step. It now tars beside OUT and
moves the archive in. A pack failure exits 5. The fresh-OUT check also had a bug: a plain path in a nullglob list is
not a glob, so every OUT counted as "holding results". Fixed with `swarm-screen-out.tg[z]`.

**Decision to flag:** the money ledger sits one folder above OUT
(`artifacts/claude-swarm-screen-20261018/money-ledger.json`), not "under OUT" as the ruling said, so that a fresh OUT
cannot reset the total.

Suites: `tests.test_premonition_swarm`, `…_swarm_screen`, `…_model`, `…_train`, `…_label_free`, `…_contenders`,
`…_slices`, `…_data`: 243 tests OK (4 skipped).
