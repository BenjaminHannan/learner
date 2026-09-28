# dir-h2: a bigger pool for the number puzzles (helper H2, 2026-09-28)

Labels: SHOWN = counted or read from code here. SUGGESTED = fits the counts. UNTESTED = nobody has run it.
Marks: PASSMARKS.md (written first, before any script). Queue jobs: queue-h2-a.md (primary, 4 nets), queue-h2-b.md (replication, 4 nets, released after the primary is recounted).
Torch is not installed on this box, so nothing that trains or loads a net was run here (rule 12). What was run: the pure-python selftest below.

## 1. Plain summary
The nets memorise the 1,062 practice hands of "numbers" as a lookup table, so the 300 hands they never saw get 0 to 3 right. The
diagnosis says: stop showing the same items so often. This experiment does exactly that and nothing else: the 4-number practice
draws from 36,782 different (hand, target) pairs instead of 1,062 hands, so each pair is shown about 70 times instead of about 2,400.
Then we count how many of the 300 unseen hands are solved. If it does not work, the result says which way it failed.

## 2. Reading the proposal critically (DIAGNOSIS.md section 3)
Confirmed from code (SHOWN):
- It changes only the pool. In `claude_rsn358a_run.py` the 4-number items come from one line, `rng.choice(self.four if size == 4 else self.three)` (line 159), and `self.four` is set at line 148 from `split_four(number_hands())`. The new runner replaces `Source.four` with the wide pool and assigns nothing else in the sealed modules (selftest step 6 parses the file and lists the assignments: `R.Source`, `self.four`). Tasks, sizes (`TRAIN_SIZES`), the per-batch kind and size choice, loss, halt rule, architecture, steps, tests and the fixed env all come from the sealed 358u code, 20 of 20 sha256 lines checked.
- Held-out and blind panels: the 300 held-out hands are `split_four(...)[1]`, the same call that builds the sealed numbers4 test. None of them is in the new pool at any target (selftest [3]: 0 of 300). The runner never opens a test file or a panel; tests are read only by the sealed `eval` command that 358u used. numbers5 uses 5-number hands from `five_hands(seed 35832)`, which the change does not touch. Nothing else named a blind panel.
- Counts (pure python, selftest [2], [4], [5]): 37,082 (hand, target) pairs over 1,519 hands (targets 5-40, hands 1-13 minus the 300); 1,062 of them are the old target-24 practice pairs with the same stored answers (checked equal); 300 dev pairs with target not 24 are removed from practice, leaving 36,782; 69.6 draws per pair against 2,411 per hand before (35 times fewer repeats). All 37,082 stored answers pass the exact checker.

Weak points I found (not hidden):
1. **It adds targets, not hands (SHOWN).** The hands go from 1,062 to 1,519 (only 457 more, all unsolvable at 24). A net can still memorise (hand, target) pairs, and the 300 test hands are new hands. Whether 36,782 pairs at 70 draws each is enough to stop memorising is exactly what is being tested (SUGGESTED that it may not be; the diagnosis also predicts about 25% pass).
2. **The graded target falls to 2.9% of practice (SHOWN).** If the net generalises to other targets but not to 24, the marks say so ("too little target 24") and do not call the idea wrong.
3. **Widening the target changes what the net sees (SHOWN).** In the old pool the target cell was always 24 for 4 numbers, now it varies (the 3-number stream already varied it, so the net has met this). This is part of the pool change, not a separate one, but a result can come from "must read the target" as well as "fewer repeats". The dev pairs (P_other) help separate these.
4. **The same random stream now serves a bigger list (SHOWN in code, effect SUGGESTED to be nil).** `rng.choice` on a list of 36,782 instead of 1,062 shifts later draws of sums and grids for the same seed, so their items are different fresh items, not the same ones. Both are drawn from huge spaces, so I expect no effect; sums4 and grids5 gates would show it.
5. **No new signal for checking arithmetic (SHOWN).** The loss is still cross-entropy on one stored answer. The diagnosis's cause 2 (nothing rewards trying orders and checking) is untouched by this change, so a "memorised again" or "cannot fit" result is quite possible and useful. See section 5.
6. **Not in this run, by the diagnosis's own choice:** numbers3 (1,902 draws per pair) and sums1 (55 items) still repeat a lot. They are not graded here.
7. **Not run:** `claude_dir_h2_run.py` needs torch and the sealed nets code; it compiles (py_compile) but was not executed here. It relies on `R.train` looking up `Source` in module `R` at call time (line 267 of `claude_rsn358a_run.py`, and the 358i2 wrapper calls the original `train`), so setting `R.Source` reaches training. UNTESTED until the builder's step 4 runs `run selftest` on BensPC.

## 3. What was built
- `scripts/claude_dir_h2_pool.py` (pure python): builds the pool, splits the 300 dev pairs (seed 41707), holds the counts and the selftest.
- `scripts/claude_dir_h2_run.py` (needs torch): imports the sealed `claude_rsn358u_run`, swaps `R.Source` for `WideSource`, adds an `extra` command (P_other on the 300 dev pairs, P_train24 on 300 fixed practice hands), and passes `train`, `eval`, `poison`, `check-mask` through unchanged. It prints the "h2 pool:" line at the start of each run.
- `PASSMARKS.md`, this file, `queue-h2-a.md`, `queue-h2-b.md`.
- To do by the Director on submit: write `SEAL-h2.sha256.txt` (sha256 of PASSMARKS.md and the two scripts) that queue step 2 checks; the blind recount step writes `VERIFY-recount.md`.

## 4. Selftest output (pure python, run here 2026-09-28)
```
[1] sealed 358u code and tests: 20 of 20 sha256 lines match
[2] pool 37082 pairs over 1519 hands; practice 36782, dev 300; old pool 1062 hands at target 24
[3] held-out hands (300) in the pool: 0; held-out (hand, 24) pairs in the pool: 0; dev pairs in practice: 0
[4] all 37082 stored answers pass the exact checker; the 1062 target-24 pairs equal the old practice pool
[5] numbers4 draws 2560000; new 69.6 per pair (old 2411 per hand, 35x more); 200,000 simulated draws touched 36639 of 36782 pairs; target-24 share 0.029
[6] claude_dir_h2_run.py assigns only ['R.Source', 'self.four'] in the sealed modules; no test-panel path, no key access
selftest ok
```
Run with `python3 -B scripts/claude_dir_h2_pool.py selftest` (about 80 s).

## 5. Fallback: the NEXT single change if this one fails (not bundled)
Trigger: WRONG or "cannot fit" or "memorised again" in PASSMARKS.md (a "too little target 24" result asks for a different next step).
Brain first (SUGGESTED, simplified textbook science): a person does not learn one stored answer per puzzle. They try a pairing, compute, check against the goal, and count any route that works as success.
**Change: judge answers by the checker, not by equality with one stored string ("any-valid-answer targets").**
- For each drawn (hand, target), the code enumerates every valid postfix answer (the codex diagnosis already did this: 2,333 of 2,408 practice pairs have more than one, median 8; the code is `scripts/codex_numbers_20260927_labels.py`, to be checked before use) and the training target for that draw is one whole valid answer picked at random from that set. Whole expressions only: mixing tokens from different valid answers made an invalid answer on 12 of 12 sampled pairs (codex DIAGNOSIS.md line 11), so token-wise unions are ruled out.
- The halt target becomes "the current answer passes the exact checker" instead of "equals the stored answer", so the stop head and the token loss say the same thing.
- Pool stays whatever the winner of this experiment left (old pool if this failed to help). Same tests, same steps, sealed code except the target chooser. Data is code-made, so it is allowed.
- Why it is the next candidate: it removes the 55 arbitrary answer styles (the diagnosis's cause 3) and lets the one-shot head learn "any route that hits the target", which is a step toward trying orders and checking (cause 2). It does not add a real search loop, which is why it is a sensible small change and not a claim of a fix.
- Risks (SUGGESTED): random targets add noise, so a net may fit more slowly; with several valid answers per draw a net could still memorise a set of answers per hand.
- If that fails too: the search-and-verify step: the net writes k guesses, code keeps the valid ones, and only those are trained on (expert-iteration style); it needs a new sampler and is a larger change, so it is not proposed until this smaller one has been read.
Pass marks for that step would be written before its run, in its own PASSMARKS.md, with the same 30 of 300 bar.

## 6. Risks and what remains
- Compute time on BensPC is an estimate (4 to 8 hours for four nets, two at once), not measured; the queue job has a 12 h cap and a TOO-SLOW rule.
- The pool build takes about 1 to 3 minutes per process at start (37,082 solver calls).
- Nothing has run. No result is claimed.
- Director to do: seal the h2 files, submit queue-h2-a.md, hold queue-h2-b.md until the primary is recounted.
