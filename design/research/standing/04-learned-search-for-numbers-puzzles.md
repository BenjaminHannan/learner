# Standing research 04: learned search for the numbers puzzles

Written 2026-09-28 (standing research helper, Sonnet). Nothing here was run. Link tags: **A** = abstract page fetched and read on 09-28; **T** = title page only; **M** = from memory, not opened. Labels: shown / suggested / untested.

## What is already on main (so I do not repeat it)
- Diagnosis (`artifacts/claude-numbers-diag-20260928/DIAGNOSIS.md`, recounted in `BLIND-RECOUNT.md`): all 12 nets score 0 to 3 of 300 on held-out numbers hands; they reach exactly 1.0 on the 1,062 practice hands, and each practice hand is shown about 2,410 times. Nets memorise a lookup table. If an oracle copied a stored answer shape and chose the number order perfectly, 298 of 300 would be right, so the missing piece is trying orders and checking arithmetic.
- H2 (`artifacts/claude-dir-h2-numbers-20260928/DESIGN.md`): bigger practice pool; its section 5 fallback is any-valid-answer targets.
- G (`artifacts/claude-dir-g-search-20260928/SURVEY.md`, `DESIGN.md`): four learned start vectors, winner-take-all training, pick by the net's own halt head. Its survey covers Tree of Thoughts, Stream of Search, Coconut, verifiers, self-consistency, STaR, looped nets, winner-take-all heads. I do not re-survey those.
So this file adds only what those leave open.

## One new observation (suggested; it follows from the diagnosis, untested)
G picks the winner with the halt head. That head is trained on the target "this answer is exactly right" (`claude_fewex_net.py:171-172`; for numbers `claude_rsn358a_run.py:176-181`). On practice hands the net is exactly right after about step 20,000 (diagnosis, 12 of 12 nets), so from then on the halt target is always 1 on practice. A head whose target never varies has nothing to learn about telling right from wrong on a new hand. So "pick the one that checks out" may have nothing to pick with, even if the streams do diversify. Whether it discriminates on held-out hands is unmeasured; G's read-only split (S_pick vs oracle) will show it. If it does not, the next thing to fix is the judge, and the judge needs wrong answers to learn from.

## Sources (new ones only)
| source | what it says | tag |
|---|---|---|
| Training Verifiers (Cobbe et al.), https://arxiv.org/abs/2110.14168 | Train a judge of completions; sample many, pick the top-ranked. It is the form of "judge separate from proposer". Note the judge is trained on both correct and wrong model samples. The wrong-samples part is from my memory of the method, not in the abstract I read. | A |
| STaR, https://arxiv.org/abs/2203.14465 | Generate answers, keep the ones a checker accepts, train on them, repeat. | A |
| ReST-EM, https://arxiv.org/abs/2312.06585 | Same loop with binary feedback; tested on MATH and APPS with large LMs. | A |
| Thinking Fast and Slow (Expert Iteration), https://arxiv.org/abs/1705.08439 | A fast net is trained on the results of slow search; the net then guides better search. | T |
| AlphaZero, https://arxiv.org/abs/1712.01815 | Self-play with a learned policy and value, search guided by both. | T |
| DeepSeek-R1, https://arxiv.org/abs/2501.12948 | Reasoning learned by reinforcement learning from checkable rewards. | T |
| Large Language Monkeys, https://arxiv.org/abs/2407.21787 | The share of problems solved by any of many samples keeps rising with the number of samples. Whether a judge can find the right sample is a separate question. | A |
| Let's Verify Step by Step, https://arxiv.org/abs/2305.20050 | Judging each step, not only the final answer. | T |
| Scaling test-time compute, https://arxiv.org/abs/2408.03314 | Best-of-N against verifier-guided search under a compute budget. | T |
| RL's Razor, https://arxiv.org/abs/2509.04259 (also topic 03) | On-policy RL forgets less than supervised fine-tuning at a similar new-task score. | A |
| Daw, Niv, Dayan 2005, goal-directed versus habitual control | Brain has a habit system (cached actions) and a planning system (simulated outcomes). | M |
| Pfeiffer and Foster 2013, hippocampal sequences before a choice depict paths to a goal | Rats run through candidate future paths in the hippocampus before choosing. | M |
| Kahneman, "Thinking, Fast and Slow" (2011) | The fast-versus-slow label used in the expert-iteration title. | M |

## Brain angle (suggested, simplified, not checked here)
- Our net is in habit mode: a cached answer for each hand it has seen (2,410 repeats each). The brain plans with a model: it runs candidate paths in its head and scores them against the goal.
- Checking is easier than finding. People verify "3 x 8 = 24" instantly, then build the search on that.
- Silicon can do better on checking: an exact calculator costs nothing. The goals page allows "a calculator for arithmetic" as a silicon advantage (`design/v3/30-modes/ben-goals-2026-09-26.md`, brain-versus-silicon list). Used as a training signal only, it is not a hand-written stand-in for thinking; used at test time as a routing tool it would need Ben's reading of that rule (untested question, not decided here).

## Leads, ranked (guesses mine, not measured)
**Lead 1 (guess 30% that the judge separates right from wrong on unseen hands, AUROC 0.9 or better; top pick because it fixes what search runs on): train the judge on wrong answers.** Change only what the halt or a small judge head is trained on: add, from code, unlimited (hand, candidate answer, right/wrong) rows where wrong candidates are perturbations of valid answers (one number swapped, one operation changed, one slot moved) and the label is the checker's verdict, not equality with a stored string. Fresh rows each step, so nothing is memorised. Measure by itself first: AUROC and coverage-versus-risk (as in topic 02 Lead 3) on the 300 held-out hands, before any search. Wrong if AUROC on held-out hands is below 0.7 in either seed. Caveat: this teaches "evaluate an expression against a target", a general arithmetic-checking skill like sums; whether that counts as telling the net the kind is a question for the Director, not settled by me. Untested.

**Lead 2 (guess 25%, larger payoff): expert iteration with the checker as reward.** Change only the numbers-4 practice data: replace the stored answer with the net's own sampled answers that the checker accepts (its K G-streams, or temperature samples), fresh hands each round from an unlimited pool, several rounds. This uses H2's any-valid grading as the training signal, so it needs H2 or G first to show the net can produce any valid answer at all (coverage above 0 of 300 at K = 4). Evidence: STaR and ReST-EM (A, on large LMs with checkable answers), expert iteration (T). Wrong if held-out coverage at K = 4 does not exceed the no-search floors of 2.39 to 7.50 of 300 (diagnosis "Numbers behind the ranking", computed there) by more than seed noise. RL's Razor gives a side reason to prefer on-policy over copying answers: less forgetting of old kinds (A, abstract only, in a large-model setting). Untested.

**Lead 3 (guess 10%): judge-guided step-by-step search.** Score partial answers with the Lead 1 judge and expand the best few, AlphaZero-style. It is the largest change; only after Lead 1 passes. Untested.

## Marks reminders (H8 checklist)
Compare against the higher of the G streams and the plain loop; a plain-net row is mandatory (plain nets score 0 to 3 of 300 today); check the gain is not memorisation by scoring on the 300 held-out hands with pool overlap counted (as in the diagnosis: 0 of 300 overlap).

## Not checked / risks
- Abstracts only; none of these papers used a tiny from-scratch net on this puzzle. Stream of Search (T; covered by G) is the closest.
- My observation that the halt target is constant after memorisation rests on the diagnosis's exactness curves, not on a measured halt-head output.
- Lead 1 uses code-made perturbations; whether the judge learns arithmetic or perturbation artefacts is a real risk, so include a check with a different kind of wrong answer (for example, right numbers wrong order) that the training rows did not contain.
