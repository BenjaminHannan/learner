# Why no net learns the numbers puzzles (Helper T, 2026-09-28T18:55Z)

Read-only diagnosis. No training, no GPU, no edits to existing files. Scripts and outputs are in this folder:
`scripts/claude_numbers_diag_answers.py` -> `answers.json`, and `scripts/claude_numbers_diag_logs.py` -> `logs.json`
(both run with `python -B`, no torch needed, about 40 s and 15 s). Added after the manager's follow-up (torch 2.14 CPU became available): `scripts/claude_numbers_diag_fitnet.py` -> `fitnet.json` (the fitted net run on CPU, 1 thread, about 40 s) and `scripts/claude_numbers_diag_rule.py` -> `rule.json` (the repeat-rule audit).
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
- SHOWN, without arithmetic the expected score is small. Expected right answers out of 300 for strategies that use no arithmetic: a random well-formed answer with the right numbers 2.39 (A); the single commonest stored skeleton with random number order 7.50 (B); a skeleton drawn from the stored-answer frequencies with random number order 5.53 (C); copying the nearest practice hand's answer with its numbers remapped by rank 1 (D; and 3 of 1,062 on leave-one-out practice hands). The 12 nets' held-out scores (16 of 3,600 = 0.44%) are below A (0.80%) and C (1.84%) and close to D. SUGGESTED reading: the nets behave like a lookup that at best copies a near hand, and the fitted codex net scores 2 of 300, at A (see "The fitted net on the held-out hands").
- SHOWN, on the underfit net's saved outputs (the only ones), near-misses are not near: 86 of 300 answers use exactly the right four numbers, but the mean distance (of 7 tokens) to the nearest valid answer is 3.21, against 3.16 for one random well-formed answer with the right numbers per hand (logs.json `saved_outputs_underfit_net`). Of the 54 well-formed wrong answers (right numbers, wrong value) the median miss is 25.5 away from 24, none is within 1 and 3 are within 3 (recomputed for this report; logs.json lists the 56 distances including the 2 right ones). Caveat: this net is underfit (train exactness about 8%). The fitted net gives the same picture (3.33 vs 3.16; see below).
- SUGGESTED, no training signal asks for it: the loss is cross-entropy on one stored answer plus a halt loss on whether that answer is exactly right (`claude_rsn358a_run.py:176-181,291-301`). Once the stored answer is memorised the loss is zero, and nothing pushes the net to test number orders.

### 3. One stored answer among many (SHOWN that it exists; effect UNTESTED; not the reason held-out is near 0)
- SHOWN: the target row is one stored solution per hand (`claude_rsn358a_envs.py:248-258`, first found by the solver in `claude_blurt1.py:45`), while the grader accepts any valid answer (`claude_rsn358a_envs.py:263-274`). Median valid answers per 4-hand is 22 (13 of 1,062 have one) (answers.json `answers`). Training "exact" means equal to the stored answer (`claude_rsn358a_run.py:180`).
- Because the grader is looser than the training target, it can only help the nets, and they still score about 0. So this mismatch cannot by itself explain the held-out result. It may make the rule harder to learn (55 arbitrary answer styles to imitate); that part is UNTESTED. Codex made the same point (DIAGNOSIS.md:9).

### Ruled out or not the cause
- Too little practice: **not it (SHOWN).** numbers4 gets 1/6 of steps, the same as grids5 (which reaches 300 of 300) and twice sums4 (1/12) (`claude_rsn358a_run.py:162-165`, `claude_rsn358a_envs.py:41`). Numbers is fitted by step 19,500-27,000 of 60,000 in 12 of 12 nets, i.e. it is fitted with more than half the run left over.
- Answer format hard for a one-shot head: **not it for practised items (SHOWN), but it breaks on unseen hands (SHOWN, new).** The fitted net writes all 7 tokens correctly on 962 of 962 practice hands (`fit-baseline-s9276193/train_summary.json`, `final_probe`; also 150 of 150 re-run here, fitnet.json `practice_962_sanity_first_150`). On the 300 held-out hands, 103 of its answers are not even valid postfix (stack error), 110 more are valid postfix with the wrong numbers, 85 have the right numbers and a wrong value, 2 are right (fitnet.json `held_out_300`; see "The fitted net on the held-out hands" below). SUGGESTED: this is a symptom of lookup (the format was memorised per item, not learned as a grammar), not a separate cause; no run has fixed format alone.
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

## The fitted net on the held-out hands (new, CPU inference, all SHOWN)
Net: codex `fit-baseline-s9276193/final.pt` (width 256, 2 layers, loop, 60,000 steps; 962 of 962 on its practice hands). Loaded read-only with codex's own code (`codex_numbers_20260927_run.py: load_checkpoint, run_trace, stop_round`), torch 2.14.0+cpu, 1 thread, no edits. Load check: 150 of 150 practice hands right at its own stop, 149-150 right at every fixed round count (fitnet.json `practice_962_sanity_first_150`), so the loading is correct. Its 962 practice hands are the manifest's `train_four_hands`; the 300 held-out hands are codex's `panels/numbers4.jsonl` (the same 300 as `split_four`), which this net never saw, plus its own 100 dev hands.
| of 300 held-out hands (own stop) | count |
|---|---|
| valid answer | 2 |
| valid postfix, wrong numbers | 110 |
| not valid postfix (malformed) | 103 |
| valid postfix, right numbers, wrong value | 85 (median miss 13 from 24; 15 within 3) |
| answers using exactly the right four numbers | 123 |
- Distance to the nearest valid answer (of 7 tokens): mean 3.33 for the net, against 3.16 for one random well-formed answer with the right numbers per hand; 79 answers within 2 tokens vs 90 for the random control. So the net's answers are not nearer to a valid answer than random guesses. On the 100 dev hands: 3.26 vs 3.32 (0 valid, 42 malformed, 32 wrong numbers, 26 wrong value).
- Copying: only 7 of 300 outputs are identical to the stored answer of some practice hand; 8 of 300 equal the nearest practice hand's answer with its numbers swapped in by rank; 21 of 300 have the same operator/slot skeleton as the nearest practice hand's answer (the most common stored skeleton alone covers about 7% of practice hands, so this is near chance). So the answers are not simple copies of a nearby practice answer: on unseen hands the lookup does not hand back a neighbour, it produces something that is mostly not a valid answer at all. (SUGGESTED reading of why: the net stores each hand's answer separately; it has no rule for hands it has not stored.)
- Rounds: right after 1 round 0; after 2, 4, 8, 16 rounds 2; after 32 rounds 3; after 48 rounds 1; right at any of the 48 rounds 5 (of 300); own stop 2; mean stop at round 4.95; mean 4.0 different answers over 48 rounds. Extra thinking is not what is missing here either (0 to 3 of 300 at every count). This matches the 8-loop-net counts above.
- What it changes: cause 1 and cause 2 stand. The ruling on format is corrected (above). The floors A-D still apply: this net's 2 of 300 sits at floor A (2.39). Nothing here makes a pass mark wrong: the PASS bar (30 of 300) and the proved-wrong bar (8 of 300) are unchanged.

## 2. Limits of this diagnosis
- The 358u/358u2 nets are not here. Every statement about them rests on their `train_log.jsonl`, `tests.json` and the code, not on their outputs.
- The rsn358u/u2 nets themselves are still not here, so the fitted-net results above are for codex's smaller net (1.6 M weights, batch 128), not for the 6.3 M-weight nets that produced the 0-3 of 300. That the bigger nets behave the same on unseen hands is SUGGESTED by their scores (0-3 of 300), not shown.
- The floors A-D assume a strategy; they do not prove what a net does internally.

## 3. Proposed fix: one change, fixed pass marks, a proved-wrong result

**Change (one), stated as a general rule applied by code to every practice stream:** *every practice stream must have at least N = 1 distinct item per M = 1,000 draws* (at most 1,000 draws per distinct item on average). A stream is a (kind, size) pair as drawn by `Source.batch` (`claude_rsn358a_run.py:162-165`). "Distinct item" is counted on the tokens, not the kind: the key is (sorted multiset of all input cell tokens, target tokens), so the display shuffle of a number puzzle is not a new item. The audit reads no kind label and no solver. Audit output: rule.json, from `scripts/claude_numbers_diag_rule.py` (about 4 min, deterministic).
- Why these values (SUGGESTED, not derived): the streams that end up memorised have 1,902 (numbers3) and 2,410 (numbers4) draws per item and fit to 1.0 (section 1). The stream sizes that are tested on fresh items and solved (sums4, grids5) have 0.03 and at most 128 draws per item (grids on the most conservative count: only the 20,000 stored bases, ignoring the 28,800 variants and symbol relabelling per base). sums2 (441) and sums3 (8.6) are not tested on their own, so nothing shows whether they memorise. M = 1,000 sits in that gap, about 2 times below the failing streams. M = 100 would also flag sums2 (441), which nobody has shown to be a problem. The gap between 441 and 1,902 is not tested, so the value is a guess; the experiment below only tests the far side (69 draws per pair).
- Which streams the rule touches (rule.json, draws per item): sums1 23,273 (55 distinct items); numbers3 1,902 (1,346); numbers4 2,410 (1,062). It passes sums2 441, sums3 8.6, sums4 0.03, grids4 128, grids5 128. **So the rule touches three streams, not only numbers4.** I am reporting this rather than shaping the rule to hit only numbers4.
- How each touched stream meets the rule:
  - numbers4: by the target-range knob the numbers generator already has (the 3-number puzzles already use targets 5-40): draw (hand, target) pairs with the target uniform over 5-40, the 300 held-out hands removed at every target, the stored answer from the same solver (`claude_rsn358a_envs.py:277-288`, hands 1-13 for four numbers). Pool 1,062 -> **37,082 pairs, 69 draws per pair** (rule.json, answers.json `wider`), which meets the rule with room to spare.
  - numbers3: already uses the target knob (targets 5-40 over hands 1-9), so that knob is spent. The only other knob is the number range (1-9 to 1-13). Widening it is a second change.
  - sums1: the whole space is 55 items (0-9 plus 0-9, order ignored). No knob can meet the rule.
- **Decision for the manager:** for this first run the graded change is the numbers4 stream only. numbers3 and sums1 are audited and reported as known failures of the rule, not changed, because (a) sums1 cannot meet it, (b) widening numbers3 is a second change, and (c) neither is graded by the pass marks. If the manager wants the rule enforced on every stream, the run is a larger change (numbers3 range widened, sums1 capped at 55,000 draws = 1,000 per item, which shrinks its share of practice) and the pass marks would need a guard on sums4/grids5 that already exists. I recommend not doing that in one run.
Nothing else changes: same loss, same halt rule, no kind label (env fixed at 0 as in 358u), no solver at test time, same tests. Sums, grids and 3-number practice are untouched in the run.
Honest limits: the rule is general but the run enforces it on one stream by a numbers-generator knob, and it cuts practice on target 24 itself from 100% to 2.9% of numbers4 draws (1,062 of 37,082 pairs). If the net needs many target-24 examples this change can hide a real gain; the wider-pool held-out pairs below are how the marks tell those apart.

**Run:** rsn358u sealed code with only the pool change in a new runner file (the runner is written and sealed before training; I did not write it). Loop arm, seeds 13-16, 60,000 steps, batch 256. Cost is about $0.5 and 70 min for 4 nets on one RTX 5090 (`artifacts/claude-rsn358u2-20260928/RESULTS.md:13`). Comparison: rsn358u loop 1, 1, 0, 1 of 300 and rsn358u2 loop 2, 2, 3, 1 (tests.json).

**Pass marks (fixed now, before any run):**
- V (validity): `steps_block_nograd` = 0 on 4 of 4 nets; poison identical on 4 of 4; a check shows none of the 300 held-out hands is in the practice pool at any target. Otherwise INCONCLUSIVE.
- PASS: numbers4 (the same sealed 300 hands, target 24, right at the net's own stop) is at least **30 of 300 on at least 3 of 4 seeds**, AND sums4 and grids5 are at least 285 of 300 on all 4 seeds. (30 is 4 times the best search-free floor, B = 7.5, and 10 times the best earlier net, 3.)
- Also reported (used only to read the two failure cases below): **P_other** = 300 (hand, target) pairs with target not 24 from the wider pool (fixed seed, hands not in the 300 held-out, removed from practice at their pair), right at the net's own stop out of 300, and the final-window numbers4 training exactness.
- **Proved wrong (pool size was not the problem):** numbers4 is at most **8 of 300 on all 4 seeds** (at the search-free floor). Then the extra numbers separate three readings, with the same bar as the pass mark (30 of 300) for P_other:
  - **memorised again:** practice exactness at least 0.9 AND P_other at most 8 of 300 AND numbers4 at most 8 of 300. The net stores the 37,082 pairs as it stored the 1,062 hands; new pairs (new hands, other targets) fail just as target-24 hands do. Pool size at 69 draws per pair was not enough.
  - **too little target-24 practice:** P_other at least 30 of 300 on at least 3 of 4 seeds while numbers4 (target 24) is at most 8 of 300. The net did generalise to unseen pairs, so widening the pool worked; what fails is target 24 itself, which was 2.9% of its numbers4 draws. This is NOT counted as the pool idea being wrong. It sends the next step to a second change (more weight on the graded target), not proposed now.
  - **cannot fit:** practice exactness below 0.5. It cannot even fit the wider pool, which supports cause 2 (the net has no way to search) over cause 1.
  P_other between 9 and 29 with numbers4 at most 8: partial, no claim.
- Anything else (numbers4 of 9-29 on some seed, or 30+ on only 1-2 seeds): partial, no claim, no second change until the marks are read. The pass marks are unchanged by the fitted-net result.

Prediction (SUGGESTED, not a result): PASS about 25%. The likeliest outcomes are "memorises again" or "cannot fit". That would still be informative, because it sends the next step to a training signal that rewards checking (cause 2) rather than to more data.

**Outside opinion (CLAUDE.md):** cause 1 vs cause 2 has two plausible readings. If Ben wants a GPT (web) prompt I can write one with the tables above pasted in, saved under `reviews/`.

## 4. Reproduce
```
python -B scripts/claude_numbers_diag_answers.py   # -> artifacts/claude-numbers-diag-20260928/answers.json
python -B scripts/claude_numbers_diag_logs.py      # -> artifacts/claude-numbers-diag-20260928/logs.json
python -B scripts/claude_numbers_diag_fitnet.py    # -> fitnet.json (needs torch; CPU, 1 thread, ~40 s; loads codex's final.pt read-only)
python -B scripts/claude_numbers_diag_rule.py      # -> rule.json (~4 min)
```
Both are deterministic (seeded) and read only existing files and the generator.
