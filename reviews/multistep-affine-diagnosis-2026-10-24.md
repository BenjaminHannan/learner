# Why affine stays at ~0% first-try (CPU-only diagnosis, 2026-10-24)

Scope: the small card experiments (creative/ B2 few-shot rules), not the village model. Scripts: /tmp/claude-0/-home-user-learner/67942a90-1503-5fd0-b69c-3babf609e11b/scratchpad/affine/ (q1.py, trees.py, mc2.py, c.py). Pool only; test.jsonl never opened.
Labels: SHOWN = from my numbers below; SUGGESTED = reasoning, not measured; UNTESTED = no data.
Caveat: the brief allowed Haiku helpers and one Opus critique; this agent had no sub-agent tool, so nothing was delegated and the Opus critique of Q5 was NOT done. Please have Ben relay Q5 to Astra/GPT if he wants an outside check.

## Q1. Shortest program length (fewshot.find_reference, 7 steps, 2M-state cap; all 615 questions found a program)
| kind | n | len 2 | len 3 | len 4 | len 5 | mean |
|---|---|---|---|---|---|---|
| affine | 205 | 0 | 32 | 140 | 33 | 4.00 |
| sq_plus | 205 | 0 | 121 | 84 | 0 | 3.41 |
| double_add | 204 | 21 | 183 | 0 | 0 | 2.90 |
Affine per (A,B): length depends mostly on how cheaply B (and A) can be built. Length 3: (3,4) (3,6) (3,10) (4,4) (4,8) (4,10) (5,5) (5,10). Length 5: (3,13) (4,13) (4,15) (5,14) (6,7) (6,9) (6,11) (6,13) (6,14). A=6 is the worst row (no length-3 question; all are 4 or 5).
Note find_reference merges equal value vectors, so a few lengths could be 1 too long (the (3,4)=3 case suggests it also accepts coincidental fits; see Q4).

## Q2. Distinct shortest programs and non-shortest fits (trees.py, 6 random questions per kind; expression TREES without sharing, commutative pairs counted up to a factor 2)
Trees with n ops that reproduce examples AND key (hits at n=min / n=min+1):
- affine: n=4: 0-30 trees (typ. 8-30; (5,14) none until n=5); n=5: 227-3674.
- sq_plus: n=3: 0-6; n=4: 48-394; n=5: 4.9k-31k.
- double_add: n=3: 8-45; n=4: 1.0k-3.3k; n=5: 88k-273k.
So the number of fitting programs grows about 100x per extra step, and at the shortest length double_add has ~3x more than affine, ~5x more than sq_plus. Non-shortest fitting programs are the majority at every kind (n+1 is 100x n). (SHOWN for this sample; DAG programs with shared steps not counted.)

## Q3. Random-sampler hit rate (mc2.py; uniform ops 1-7, operands uniform over x, 4 constants, earlier results, answer = last step, must read x; 6 questions/kind, 1.8M draws for L<=4, 5.4M for L>=5)
Per-draw chance of a program that fits examples and key:
- affine: L3 5.6e-7 (1 hit), L4 5.6e-7 (1), L5 3.0e-6, L6 3.7e-6, L7 2.6e-6.
- sq_plus: L3 1.1e-6 (2), L4 0 (0), L5 1.9e-6, L6 3.0e-6, L7 2.6e-6.
- double_add: L3 2.8e-6 (5), L4 1.1e-5, L5 1.2e-5, L6 1.3e-5, L7 1.8e-5.
Hits are tiny (1-97 events), so only the order of magnitude is trustworthy. (SHOWN)
Readings:
1. A uniform sampler is near zero for all three (1e-6 to 2e-5 per draw; with 512 tries ~0.05%-1% per question). So the 15-25% rates seen for sq_plus/double_add are the model's learned bias, not luck. (SHOWN for uniform; model bias SUGGESTED)
2. Uniform-random does NOT separate affine from sq_plus (both ~1-3e-6). It does make double_add ~4-5x easier. So "affine is harder purely by length" does not explain affine vs sq_plus under uniform sampling. (SHOWN)
3. Constants cost (c.py): the cost of building a number from {1,2,10,100} with + - * / is c(3..15)= 1,1,1,2,2,1,1,0,1,1,2,2,2 steps. Naive affine length = c(A)+c(B)+2 gives 4-6; observed is ~1 lower (shared constants, e.g. a built 2 reused), but the pattern holds: lengths 3/4/5 track c(A)+c(B). A=6,7,13,14,15 need 2 steps each. Mean build cost: A 1.25, B 1.31 steps, i.e. ~2.6 of affine's ~4.0 steps are only constant-building; sq_plus and double_add need only one constant (B), ~1.3. (SHOWN)
4. Why sq_plus may still climb (SUGGESTED, untested): the warm-up rules add (x+B) and mult (A*x) already teach "build a constant, then op with x". sq_plus = mult(x,x) then the add pattern (2 sub-skills, 1 constant). Affine = mult pattern + add pattern + two constants built separately, so it must chain two constant-builders correctly with no step in between that gets reward. A 2-3 step lead in length and two independent constant sub-chains multiply the failure probability.

## Q4. Ambiguity from the 3 examples (trees.py, "wrong" = distinct value vectors matching all examples but not the key)
- affine: 0 wrong at min size; at n=5: 0-9 distinct wrong functions (total wrong trees 0-126, vs 227-3674 right ones). Rare.
- sq_plus: 0 wrong at n<=4; n=5: 0-18 distinct wrong (0-417 trees vs 5k-31k right).
- double_add: 0 wrong at n<=3; n=4: 0-8 distinct; n=5: 0-32 distinct wrong (2-25k trees vs 88k-273k right).
So examples pin the rule down for all three kinds; ambiguity is NOT the reason affine fails. A fitting program is almost always the right rule (affine ~97-100% of fitting trees are right; double_add up to ~10% wrong at n=5 for some B). (SHOWN)
Also: rules_real.predictions() already checks at pool-build time that examples fix one answer among its rule table.

## Q5. Ranked fixes (all SUGGESTED / UNTESTED; one change at a time; marks fixed before running; none involve touching test.jsonl)
1. Curriculum stepping stone: sleep on records of 2-constant programs the model can already find, e.g. "mult then add" with B=10 or B in {11,12,9,8} (length 3, c(B)<=1), then raise B. Evidence: the model solves length-3 sq_plus/double_add; affine length 3 questions are 32/205 (A in 3..5, B in {4,5,6,10}). Pass mark: affine first-try on the 32 length-3 pool questions >= 10% after 2 nights, while length-5 stays unchanged, add/mult reach@32 >= 50% (existing mark). Proved wrong if: length-3 affine stays < 3% after 2 nights, which says the problem is not length.
2. Report first-try by affine LENGTH (zero GPU; analysis only). Pass mark: first-try on length 3 >= 3x first-try on length 5. If the rates are equal across length, the diagnosis (length/constants) is wrong and look at the model's op/operand habits instead.
3. Add constants 3 and 5 (or a 3-slot macro "A*x" for A in 3..6 from existing mult programs). With 3,5 the naive c(A)+c(B)+2 mean drops about 1 step (e.g. (5,5) 4 to 2; (6,13) 6 to 4). Cost: B2 slot map change (slots 16..19 fixed), requires a new B2 and invalidates the held-out seal; highest effect, highest cost. Pass mark: affine reach@32 on a fresh DEV sample doubles with the same night count. Proved wrong if unchanged.
4. Per-question search budget scaled by kind (c2_stuck allocation is kind-blind by design; changing it breaks the leak test). Instead raise N2 for ALL stuck questions from 480 to ~2000. Uniform rate math: 2000 tries only reaches ~0.6% on affine L5 under uniform sampling, so only helps if the model's bias is already strong; expect small. Pass mark: affine multi-step records rise from ~0 to >= 20/205 after one night. Proved wrong if still < 5.
5. Data recipe: supply "add" and "mult" programs in the exact style of the affine decomposition (same slot numbering, B built from 2+2, 10-2) so the model sees the constant-building idiom. Pass mark: B-constant chains appear in >= 30% of fitting affine tries. Not recommended before 1-2.

## Plain summary for Ben (high-school senior)
Affine needs about four steps, and two of them are only making the numbers A and B out of 1, 2, 10 and 100, so the model has to get a longer chain exactly right. Random guessing finds affine about as rarely as sq_plus, so the gap is from what the model already learned: it practised "times a number" and "plus a number" separately but never chains them. The cheapest next step is to look at results by program length and to practise short two-step affine questions first; adding the constants 3 and 5 would help most but costs the most.
