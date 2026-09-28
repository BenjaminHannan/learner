# Why no net learns the numbers puzzles (Helper T, 2026-09-28T18:55Z)

Read-only diagnosis. No training, no GPU, no edits to existing files. Scripts and outputs are in this folder:
`scripts/claude_numbers_diag_answers.py` -> `answers.json`, and `scripts/claude_numbers_diag_logs.py` -> `logs.json`
(both run with `python -B`, no torch needed, about 40 s and 15 s).
Labels: SHOWN = a count computed from code or saved files (source given). SUGGESTED = fits the counts but a different reading is possible.
UNTESTED = nobody has run it.

## Plain-language summary (for Ben)
- The nets do not fail to learn numbers puzzles. They learn the 1,062 practice hands perfectly (a score of 1.0, meaning they write the stored answer for every one). They just learn them as a lookup table. The 300 hands they are tested on are hands they never saw, and a lookup table has nothing to say about those.
- Sums and grids do not have this problem, because there are hundreds of millions of different sums and grids, so nothing can be memorised. The numbers practice has only 1,062 hands, and each one is shown about 2,400 times.
- What is missing is the skill of trying number orders and checking the arithmetic. The answer's shape is easy to copy. The saved tests show that nearly every held-out hand can be solved by copying a shape that appears in practice and putting the numbers in the right order. Picking that order needs arithmetic, and nothing in the training rewards the net for doing it.
- The loop's extra thinking rounds do not help here (a count of right answers after 1 round and after 48 rounds is the same). They help on sums, where the rounds carry a carry along.
- One change is proposed (section 3): stop repeating practice items, by using the target range the 3-number puzzles already use. It has fixed pass marks and a result that would prove the idea wrong.

## 0. Prior work (read, not re-derived)
`artifacts/codex-numbers-20260927/DIAGNOSIS.md` already showed: alternatives exist on 2,333 of 2,408 practice pairs (median 8, max 335) (DIAGNOSIS.md:9; `diagnostics/label-cache-summary.json`); the historical nets fit practice at 1.0 and score 0-5 of 300 held out (DIAGNOSIS.md:13); an underfit net's error breakdown on the 300 (DIAGNOSIS.md:26); a fitted net at 962 of 962 practice and 0 of 100 held-out (DIAGNOSIS.md:41). I re-ran the alternatives count from the enumerator and got the same numbers (answers.json `answers`: 2333 of 2408, median 8, max 335). What is new here: the search-free floors (cause 2), the pool arithmetic, the 12-net training curves, the thinking-time counts over 8 loop nets, the near-miss comparison with a random control, and a proposed fix.
No 358u/358u2/358i3 net files are on this machine (`find artifacts -name '*.pt'` finds only nets from codex-numbers, vread, gr1, autoroute; none from rsn358). No torch is installed and downloads are not allowed, so no saved net could be run. The only saved per-item outputs on the 300 held-out hands are from an UNDERFIT net (`codex-numbers-20260927/diagnostics/baseline-s9276191/numbers4.json`, width 128, 20,000 steps).

## 1. Causes ranked by evidence

### 1. Lookup memorisation on a tiny finite pool: it happens (SHOWN); it is what blocks transfer (SUGGESTED); a bigger pool cures it (UNTESTED)
- SHOWN, the pool is tiny. The 4-number practice draws from 1,062 hands (`scripts/claude_rsn358a_run.py:148,159`; split at `scripts/claude_rsn358a_envs.py:292-299`). All possible 4-number multisets from 1-13 number 1,820, of which 1,362 are solvable at 24, and 300 of those are the test (answers.json `pool`). Each batch picks a kind, then a size (`claude_rsn358a_run.py:162-165`; sizes at `claude_rsn358a_envs.py:41`), so numbers4 gets 1/6 of 60,000 steps = 10,000 batches x 256 = 2.56 M draws, i.e. **2,410 draws per hand** (numbers3: 1,902 per pair). Sums4 gets 1.28 M draws over at least 99 M distinct (a, b) pairs, so almost none repeat. Grids draw from 20,000 bases with 28,800 row/column/flip variants each (answers.json `pool`).
- SHOWN, the nets reach exactly 1.0 on practice. In all 12 nets (rsn358u loop x4, plain x4, rsn358u2 loop x4) the training window for numbers4 first reaches exactness 0.99 between step 19,500 and 27,000 and ends at 1.0 (logs.json `training_curves_and_tests`). The same 12 nets score 16 of 3,600 (0.44%) on the 300 held-out hands (0-3 per net; RESULTS.md:12 of rsn358u and the tests.json files).
- SHOWN, in the fitted codex run (seed 9276193) practice validity climbs 15 -> 399 -> 849 -> 919 -> ... -> 962 of 962 while the 100 held-out hands stay at 0 at all 12 checks (logs.json `fit_run_probes_s9276193`; from `codex-numbers-20260927/diagnostics/fit-baseline-s9276193/probe_log.jsonl`). There was no moment when held-out began to rise.
- SHOWN, the held-out hands are not harder: median 20 valid answers per held-out hand vs 22 per practice hand; only 3 of 300 have a single valid answer (answers.json `answers`).
- Why "SUGGESTED" and not "SHOWN": the contrast with sums/grids is confounded (sums and grids are also different tasks). No run has changed the pool alone. (Codex's DIAGNOSIS.md:41 says the same.)

### 2. Nothing in training asks the net to search or check arithmetic; the hard step is picking the number order (SUGGESTED, built on SHOWN counts)
- SHOWN, the answer shape is not the hard part. If an oracle could copy a shape (the stored answers use 55 distinct skeletons of ops and slots) and choose the number order perfectly, **298 of 300** held-out hands would be right; using only the 5 commonest skeletons, 167 of 300 (answers.json `floors_on_300_heldout` E).
- SHOWN, without arithmetic the expected score is small. Expected right answers out of 300 for strategies that use no arithmetic: a random well-formed answer with the right numbers 2.39 (A); the single commonest stored skeleton with random number order 7.50 (B); a skeleton drawn from the stored-answer frequencies with random number order 5.53 (C); copying the nearest practice hand's answer with its numbers remapped by rank 1 (D; and 3 of 1,062 on leave-one-out practice hands). The 12 nets' held-out scores (16 of 3,600 = 0.44%) are below A (0.80%) and C (1.84%) and close to D. SUGGESTED reading: the nets behave like a lookup that at best copies a near hand, and they do not even reliably hit A (untested: the memorising nets' held-out outputs were not saved).
- SHOWN, on the underfit net's saved outputs (the only ones), near-misses are not near: 86 of 300 answers use exactly the right four numbers, but the mean distance (of 7 tokens) to the nearest valid answer is 3.21, against 3.16 for one random well-formed answer with the right numbers per hand (logs.json `saved_outputs_underfit_net`). Of the 54 well-formed wrong answers (right numbers, wrong value) the median miss is 25.5 away from 24, none is within 1 and 3 are within 3 (recomputed for this report; logs.json lists the 56 distances including the 2 right ones). Caveat: this net is underfit (train exactness about 8%), so it says what an unfitted net does, not what the memorisers do.
- SUGGESTED, no training signal asks for it: the loss is cross-entropy on one stored answer plus a halt loss on whether that answer is exactly right (`claude_rsn358a_run.py:176-181,291-301`). Once the stored answer is memorised the loss is zero, and nothing pushes the net to test number orders.

### 3. One stored answer among many (SHOWN that it exists; effect UNTESTED; not the reason held-out is near 0)
- SHOWN: the target row is one stored solution per hand (`claude_rsn358a_envs.py:248-258`, first found by the solver in `claude_blurt1.py:45`), while the grader accepts any valid answer (`claude_rsn358a_envs.py:263-274`). Median valid answers per 4-hand is 22 (13 of 1,062 have one) (answers.json `answers`). Training "exact" means equal to the stored answer (`claude_rsn358a_run.py:180`).
- Because the grader is looser than the training target, it can only help the nets, and they still score about 0. So this mismatch cannot by itself explain the held-out result. It may make the rule harder to learn (55 arbitrary answer styles to imitate); that part is UNTESTED. Codex made the same point (DIAGNOSIS.md:9).

### Ruled out or not the cause
- Too little practice: **not it (SHOWN).** numbers4 gets 1/6 of steps, the same as grids5 (which reaches 300 of 300) and twice sums4 (1/12) (`claude_rsn358a_run.py:162-165`, `claude_rsn358a_envs.py:41`). Numbers is fitted by step 19,500-27,000 of 60,000 in 12 of 12 nets, i.e. it is fitted with more than half the run left over.
- Answer format hard for a one-shot head: **not it for fitted items (SHOWN).** The same head writes all 7 tokens (numbers and operators, in postfix) correctly on 962 of 962 practice hands (`fit-baseline-s9276193/train_summary.json`, `final_probe`). Whether the held-out outputs of a memorising net are well formed is UNTESTED (not saved).
- Loop thinking time: **used, but not for search (SHOWN).** Over the 8 loop nets (rsn358u and rsn358u2), the mean stop is 6.64-7.79 rounds on numbers4, against 6.76-7.24 on sums4 and 8.87-10.68 on grids5. The number of right numbers4 answers, summed over the 8 loop nets (of 2,400), is 10 after 1 round, 11 after 2, 12 after 4, 10 after 8, and 12 at 12, 16, 24, 32 and 48 rounds. Counting a hit at any of the 48 rounds gives 22 of 2,400 (0.92%), the same as one random well-formed answer with the right numbers (0.80%) (logs.json `loop_thinking`). In the underfit net the answer keeps changing (6.6 different answers over 48 rounds, last change about round 25 on average) without settling on a right one. Loop-vs-plain on numbers4 is 0.75 vs 1.25 of 300 (rsn358u), i.e. no difference.
- Numbers5 (0-2 of 300 per net): needs a 9-token answer that was never practised; it inherits the 4-number failure and adds nothing on its own.

## Numbers behind the ranking
| item | value | where |
|---|---|---|
| practice 4-hands / held-out / possible | 1,062 / 300 / 1,820 multisets (1,362 solvable) | answers.json `pool` |
| draws per practice hand in 60,000 steps | 2,410 (numbers4), 1,902 (numbers3) | answers.json `pool` |
| sums4 draws vs distinct pairs | 1.28 M vs at least 99 M | answers.json `pool` |
| practice pairs with more than one valid answer | 2,333 of 2,408 (median 8) | answers.json `answers` |
| train exactness step 0.99 first reached, numbers4 | 19,500-27,000 (12 of 12 nets) | logs.json |
| held-out numbers4, 12 nets | 16 of 3,600 | logs.json |
| search-free floors A / B / C / D, of 300 | 2.39 / 7.50 / 5.53 / 1 | answers.json |
| skeleton-copy plus perfect order ceiling | 298 of 300 (167 with top 5 skeletons) | answers.json |
| 8 loop nets, numbers4 right after 1 / 48 rounds | 10 / 12 of 2,400 | logs.json |

## 2. Limits of this diagnosis
- The 358u/358u2 nets are not here. Every statement about them rests on their `train_log.jsonl`, `tests.json` and the code, not on their outputs.
- The fitted memorising codex net (`fit-baseline-s9276193/final.pt`) exists but cannot be run (no torch). Its held-out outputs would show whether it writes a well-formed answer, whether the numbers are right, and how close the arithmetic is. That is UNTESTED.
- The floors A-D assume a strategy; they do not prove what a net does internally.

## 3. Proposed fix: one change, fixed pass marks, a proved-wrong result

**Change (one):** stop repeating practice items. Draw each 4-number practice item as a (hand, target) pair with the target uniform over 5-40, as the 3-number practice already does (`claude_rsn358a_envs.py:277-288`, `number_hands`: 3-number hands use numbers 1-9 and targets 5-40), with the stored answer from the same solver. The 300 held-out hands are removed from practice at every target. The pool goes from 1,062 pairs (2,410 draws each) to **37,082 pairs (about 69 draws each)** (answers.json `wider`; 1,519 hands, targets 5-40, solvable only). Nothing else changes: same loss, same halt rule, no kind label (env fixed at 0 as in 358u), no solver at test time, same tests. Sums, grids and 3-number practice are untouched.
General reading: the rule is "no practice item may be shown thousands of times". The generator for numbers is the only one with a small finite pool, and the target range is a knob the numbers generator already has. It does not put arithmetic into the net.
Honest limits: it is a change to one kind's generator, and it reduces practice on target 24 itself from 100% to 2.9% of numbers4 draws. If the net needs many target-24 examples this change can hide a real gain.

**Run:** rsn358u sealed code with only the pool change in a new runner file (the runner is written and sealed before training; I did not write it). Loop arm, seeds 13-16, 60,000 steps, batch 256. Cost is about $0.5 and 70 min for 4 nets on one RTX 5090 (`artifacts/claude-rsn358u2-20260928/RESULTS.md:13`). Comparison: rsn358u loop 1, 1, 0, 1 of 300 and rsn358u2 loop 2, 2, 3, 1 (tests.json).

**Pass marks (fixed now, before any run):**
- V (validity): `steps_block_nograd` = 0 on 4 of 4 nets; poison identical on 4 of 4; a check shows none of the 300 held-out hands is in the practice pool at any target. Otherwise INCONCLUSIVE.
- PASS: numbers4 (the same sealed 300 hands, target 24, right at the net's own stop) is at least **30 of 300 on at least 3 of 4 seeds**, AND sums4 and grids5 are at least 285 of 300 on all 4 seeds. (30 is 4 times the best search-free floor, B = 7.5, and 10 times the best earlier net, 3.)
- Also reported, not graded: 300 held-out (hand, target) pairs from the wider pool (fixed seed, removed from practice) and the final-window numbers4 training exactness.
- **Proved wrong (pool size was not the problem):** numbers4 is at most **8 of 300 on all 4 seeds** (at the search-free floor). Read the two sub-cases with the extra numbers:
  - practice exactness at least 0.9 and held-out pairs at most 8 of 300: it memorised the wider pool too (69 draws per pair was still too many, or memorising is what this net does with any pool this size);
  - practice exactness below 0.5: it cannot even fit the wider pool, which supports cause 2 (the net has no way to search) over cause 1.
- Anything between (9-29 on some seed, or 30+ on only 1-2 seeds): partial, no claim, no second change until the marks are read.

Prediction (SUGGESTED, not a result): PASS about 25%. The likeliest outcomes are "memorises again" or "cannot fit". That would still be informative, because it sends the next step to a training signal that rewards checking (cause 2) rather than to more data.

**Outside opinion (CLAUDE.md):** cause 1 vs cause 2 has two plausible readings. If Ben wants a GPT (web) prompt I can write one with the tables above pasted in, saved under `reviews/`.

## 4. Reproduce
```
python -B scripts/claude_numbers_diag_answers.py   # -> artifacts/claude-numbers-diag-20260928/answers.json
python -B scripts/claude_numbers_diag_logs.py      # -> artifacts/claude-numbers-diag-20260928/logs.json
```
Both are deterministic (seeded) and read only existing files and the generator.
