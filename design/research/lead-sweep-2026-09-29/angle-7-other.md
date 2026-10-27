# Angle 7: everything else that bears on the open problems

Written 2026-09-29 01:57 UTC by the angle-7 research agent. Research only: no repo file changed, nothing trained.
Labels: **shown** = measured in a repo file or in a cited source; **suggested** = my reasoning; **untested** = new prediction.
Web reading depth is stated per source. Several arXiv ids below carry 2026 numbers (they appeared in search results, dated after my memory); I read them by search snippet or fetched summary only, not line by line.

## 1. Short answer (for Ben, plain words)

- Nothing outside the other angles looks like a sure +8 on the ruler by itself. The biggest measured lever is already known: practising on two kinds instead of none moved the loop from 20.7 to 51.0 F_eq (shown, RESULTS-EQ.md). The literature says the next lever is more kinds of practice, which is queued (A). I do not re-propose it.
- Reading the code, the fine-tuning step on mazes shrinks every weight by about 18% over its 2,048 updates (weight decay 0.1 pulls toward zero, not toward the practised weights). Nobody has tried turning that off. It is one line, reuses the saved practice nets, and costs about three CPU hours. It is my Test 1. I put its odds of a +8 at about 10%, but it is the cheapest untried change and its result (either way) says whether decay matters at all.
- The ruler itself is adequate for the +8.0 bar on baseline-style changes, but not for changes that alter practice (the sparse loop moved +3.9 in one seed and -6.3 in the other). Test 3 fixes that with two more seeds.
- For scaling (item 7): the published looped-model scaling work says extra loops are worth less than extra distinct layers, and looping does not add knowledge capacity. So "the gap does not shrink" is a real risk, not a given (see 3.5). The repo's own lf-sz race is the right test; I add nothing to it.

## 2. What I read in the repo (shown)

- Model (claude_fewex_net.py): 2 shared blocks, d=256; z = h + e re-injected every round; LayerNorm on state; halt head = Linear on the mean over all cells; positions are relative biases only (row and column offsets clipped at +-4), half the heads see only columns within +-1. No absolute position anywhere.
- Practice loss: rounds 1..16 random, gradient on last 1..6; CE on last k rounds + 0.5 x BCE of halt vs "every fill cell right".
- Adaptation (claude_fewex_bench.py Learner, lines ~184-206): fresh AdamW, lr 1e-3, **wd 0.1**, betas (.9,.95), 50-step warmup then constant lr, clip 1.0. Per update: 3 no-grad rounds + 2 grad rounds, hidden state carried across the 4 updates of a batch (so depth seen is about 5, 10, 15, 20 rounds), CE only, no stop loss. Plain net: one pass.
- Ruler numbers (RESULTS-EQ.md): practised loop 51.00/51.29, plain 33.79/33.58, fresh loop 20.67/21.50, fresh plain 22.46/25.00. Curves are non-monotonic (fresh loop seed 1: 166 of 300 at k=64, 0 of 300 at k=1,024).
- Noise (NOISE.md): 3.96 F_eq (all starts, rung recipe); direct same-start seed gaps RMS 1.46 (dev), largest 2.54 (holdout). H9: sparse loop effect +3.88 / -6.25.
- Numbers (RECOUNT.md): plain nets fit the pool (exactness 1.0) yet score 4-6 of 300 held out; loop nets do not even fit it (0.38 / 0.56). All four at or below the fixed-guess floor 12.

## 3. Sources (strongest first)

### 3.1 Bansal et al. 2022, "End-to-end Algorithm Synthesis with Recurrent Networks: Extrapolation without Overthinking" https://arxiv.org/abs/2202.05826
- Shown by authors (abstract read only, via fetch; results on mazes, prefix sums, chess are the authors' own, later reused by others): a recurrent net trained on small mazes solves bigger ones by running more iterations, if (a) the problem is re-injected each round ("recall") and (b) training mixes a random-depth loss with a longer-run loss ("progressive loss") so behaviour does not depend on iteration number. Without these it "overthinks": accuracy degrades as iterations pile up.
- Maps to us: our loop already has recall (z = h + e) and a random-depth no-grad-prefix loss (same family as their progressive loss). The train 16 / test 48 gap is therefore the expected use, not a defect (suggested). Repo evidence agrees: on mazes, fixed-16 accuracy is within 0-14 of 300 of learned-48 accuracy, so nothing degrades by round 48 (shown, H9 sec. 2).
- Bearing on open problems: stop and carry-over. It says extrapolating depth works; it does not say the stop head transfers.

### 3.2 Fan et al. 2024, "Looped Transformers for Length Generalization" https://arxiv.org/abs/2409.15647 (abstract read via fetch; NeurIPS-W 2024 / ICLR 2025)
- Shown by authors only: looped transformers with adaptive step counts length-generalise on arithmetic/algorithmic tasks; supervision only at the final step; stop by oracle step count or max-confidence rule. Not independently reproduced as far as I found.
- Maps to us: bears on stop (open problem 2). Their max-confidence stop is a hand rule on a practised task family; the repo's problem is the stop head on an unpractised kind, which they do not test. No new test from this source; it supports the queued label-free-stop work (standing/02).

### 3.3 Saunshi et al. 2025 (ICLR), "Reasoning with Latent Thoughts: On the Power of Looped Transformers" https://arxiv.org/abs/2502.17416 (abstract via search)
- Shown by authors: a k-layer block looped L times nearly matches a kL-layer plain model on synthetic reasoning (addition, p-hop induction), and beats a k-layer plain model. Follow-up work (Ouro, https://arxiv.org/abs/2510.25741, abstract via search) reports looping does not raise knowledge capacity per parameter but keeps or improves multi-hop reasoning.
- Maps to item 7 and to numbers: it supports "reasoner beats plain at equal weights" on reasoning-shaped tasks and warns the gain is about depth, not memory. Numbers hands are memory-plus-search, so the loop not fitting the pool (0.38 / 0.56) fits "looping is not a capacity boost" (suggested).

### 3.4 Parcae and iso-depth scaling for looped LMs: https://arxiv.org/abs/2604.12946 (search snippet) and https://arxiv.org/pdf/2604.21106 (fetched summary, thin)
- Shown by authors (language-model loss, not puzzles): compute-optimal training raises loop count and data together; test-time looping follows a saturating exponential; each extra recurrence is worth substantially less than an extra distinct block; the value of a recurrence is "not a single constant" and depends on setup. Parcae's stability fix constrains the spectral norm of the input-injection term.
- Maps to item 7: the finish line "gap not shrinking" is not guaranteed by these results; on LM loss the recurrence discount is a live risk. Our task is exactness on puzzles where depth matters, closer to Saunshi than to perplexity, so I mark it **suggested** that the gap holds on reasoning but unshown at our scale.
- Maps to the audit: injection stability (their spectral-norm point) is one reason our fixed-scale re-injection z = h + e followed by LayerNorm is a safe design; no change proposed.

### 3.5 Hyperparameter transfer for looped nets: https://arxiv.org/html/2606.18524v1 (fetched, read summary) plus muP, https://arxiv.org/pdf/2203.03466
- Shown by authors (single seed, 183-438M-param Llama-style, FineWeb-Edu): for a looped stack with L unique layers repeated N times, scale the residual branch by lambda/(N sqrt(L)); then the best learning rate is nearly the same for N in 1..8 and transfers across unique depth with a m_L^(-1/2) rule. Authors say results are one seed each. muP (Yang et al., authors' own at up to 6.7B) says best lr/init transfer across width when parameterised right.
- Maps to item 7: our recipe (lr 1e-3, wd 0.1, same for d=128 plain and d=256 loop) is a standard-parameterisation setting. When the reasoner grows, the best lr will shift; a bigger model that "fails" the ruler could be a mistuned lr rather than a real loss of the loop advantage (suggested). The plain arm did get an lr sweep (PLAIN_LRS in the bench); the loop got one value. The lr angle (queued) covers adaptation lr; a width-scaling comparison should use the residual-scale rule above or sweep lr per width. Not a test on its own: a rule for how to run lf-sz.

### 3.6 Grokking and weight decay (e.g. https://arxiv.org/abs/2605.20441, search snippet only; plus the classic modular-arithmetic grokking line)
- Shown by authors on modular-arithmetic transformers: weight decay is the control that separates memorising from generalising; memorisation circuits must be eroded before the algorithmic one is learnable.
- Maps to numbers: plain nets memorised 1,062 hands (each seen ~2,410 times) at wd 0.1 and never generalised. Grokking says that is the memorise phase; escaping it usually needs stronger decay, more steps, or more diverse data. The H2 result (bigger pool, loop cannot fit) is a different failure. It also gives a reason to test wd in adaptation (Test 1): decay is the lever that shifts memorise vs generalise, and adaptation is where memorising k mazes happens (untested for our nets).

### 3.7 Task diversity and procedural data: Raventos et al. 2023 https://proceedings.neurips.cc/paper_files/paper/2023/hash/2e10b2c2e1aa4f8083c37dfe269873f8-Abstract-Conference.html (abstract via search); Reasoning Gym https://arxiv.org/abs/2505.24760 (abstract only; I could not confirm its cross-domain transfer numbers from the abstract, so I do not rely on them)
- Shown by authors (linear regression ICL): a task-diversity threshold; below it the net acts like a memoriser of its practice tasks, above it it generalises to new tasks. H9 already cites this.
- Maps to numbers and carry-over: two practised kinds is likely below threshold; consistent with numbers memorisation. This is exactly queued item A (10 kinds). I only add: the threshold is on the number of distinct tasks, so A's result should be read as a curve over 2, 5, 10 kinds, not one point (suggested).

Not used (not strongly evidenced for tiny recurrent nets): Muon, schedule-free optimisers. I found nothing that shows a gain on 1-2M-parameter looped nets, so I do not propose one.

## 4. Mechanism audit of the model and training code

| # | Detail | What literature says | Verdict | Label |
|---|---|---|---|---|
| 1 | Train rounds 1..16, test 48 | Bansal: iteration-agnostic training extrapolates; repo: fixed-16 ~ learned-48 on mazes | Not a problem. Mazes have routes up to 31 cells; the net solves them with at most 20 rounds in adaptation | shown (repo) / shown (Bansal, authors) |
| 2 | Halt = Linear on mean over all cells; target is "all fill cells exact" | ACT/PonderNet-style halting use a global scalar too; global exactness over 81 cells is a rare-event label on a new kind | Risky but owned by stop angle (H12, SL, Pond). Never fires on mazes: 300/300 cap at most rungs | shown (repo) |
| 3 | Re-injection z = h + e | Bansal recall; Parcae injection stability | Fine, matches evidence | shown (authors) |
| 4 | Weight decay 0.1 on everything (embeddings, LayerNorm gains, biases, the +-4 bias tables) in practice AND adaptation | Decoupled decay toward zero during fine-tuning erodes practised features; common recipes exempt norms/biases; grokking work makes decay the memorise-vs-generalise knob | Adaptation decay is the one cheap change with no prior test. Factor (1-1e-4)^2048 = 0.82 on every weight | suggested; Test 1 |
| 5 | Three maze marker tokens ("/", "+", "*") get zero gradient in practice: random-init rows shrunk only by decay | New-token init from the mean of trained rows helps fine-tuning in LMs (author write-ups; I did not fetch) | Probably costs mostly low-k rungs; k=1..16 add only ~1.3 of the F_eq points (H9 rung shares), so cannot reach +8 by itself; may reach F_few | suggested; Test 2 |
| 6 | Adaptation uses 3+2 rounds, no stop loss, state carried between the 4 updates | Bansal progressive loss uses random depths | Depth covered (5-20). Stop loss is queued (H12) | shown / queued |
| 7 | Relative-only position, clip +-4, half the heads window +-1 columns only | Fan/Bansal need no absolute position for size extrapolation; 7x7 and 11x11 checks in ruler exist | No evidence of harm; 11x11 scores are in RESULTS-EQ.md and were not asked about here | untested |
| 8 | Loop lr 1e-3 not swept, plain lr swept over three values | muP: optimum shifts with width; loop is d=256, plain d=128 | Possible unfairness in favour of plain; direction is the safe one for the claim "loop beats plain" (loop gets less tuning) | suggested; lr angle covers |
| 9 | Numbers: loop cannot fit 36,782-pair pool; plain memorises | Grokking: memorise first; diversity threshold | Not a bug in code; pool has 1,519 hands, still too few to force a rule | shown (recount) / suggested |

## 5. Ruler statistics: is 2 seeds x 300 mazes enough?

My arithmetic on the repo's numbers (suggested, not a repo result):
- Test-set sampling: one rung on 300 mazes has binomial sd of at most 2.9 points; averaged over 8 rungs about 1.0 F_eq if the rung errors were independent, and much less in a paired comparison because every arm scores the same 300 mazes. Sampling is not the problem.
- Training-run variance dominates. Two estimates of one run's sd: direct same-start seed gaps (RMS 1.46 F_eq on dev, 2.54 largest on holdout) give about 1.0-1.8; the rung-based recipe (3.96 for a gap) gives about 2.8. Design changes that alter practice add source-net variance: sparse loop effects were +3.88 and -6.25.
- With 2 seeds on each side, the sd of a difference of means equals the sd of one run. Minimum detectable effect (one-sided 5%, power 80%, factor 2.49):
  - run sd 1.5 -> MDE about 3.7
  - run sd 2.8 -> about 7.0
  - effect sd 5 (sparse-like) -> about 12
- So the +8.0 bar is honest for adaptation-side changes (same source nets, paired seeds) and too tight for practice-side changes. For practice-side changes require 3 seeds or a bar of +12. For F_few (4 rungs) the bar +10.5 sits at the same level.
- Non-monotonic collapses (fresh loop seed 1: 0 of 300 at k=1,024) show individual rungs can crash for optimisation reasons. Average over 8 rungs helps; a change that removes crashes would look like a big win. Check crashes explicitly: count rungs below 30 of 300 after a rung above 150 of 300.

## 6. Which single change is most likely to move the finish line?

Ranked by my guess (all suggested, untested):
1. More practised kinds (A, queued): largest measured lever; already owned.
2. Nothing else outside the angles has a documented effect size near +8 on these nets. The best untried single lines are adaptation weight decay (Test 1) and the marker-token init for F_few (Test 2).
3. For stop, numbers, sleep: my sources add no new lever beyond what standing/01-06 hold. Numbers: grokking says memorise-then-generalise needs diversity or stronger decay, best tried after A shows a diversity effect.
4. For item 7: run lf-sz at three widths with lr swept per width (or the residual-scale rule in 3.5); a gap that shrinks with width is the published risk.

## 7. Cheap one-change tests (each fits the fair ruler)

Common: 9x9 mazes, 8 rungs, 2048 updates, same panels and pools, practised loop and practised plain rows, seeds 0 and 1, baseline = RESULTS-EQ.md holdout rows (loop 51.00/51.29, plain 33.79/33.58). Dev first, then the sealed holdout once, as the ruler requires. Hardware: the ruler is fp32 CPU; Mac CPU is fine.

### Test 1: no weight decay during maze adaptation (untested)
- Single change: the adaptation Learner uses wd 0.0 instead of 0.1. Everything else, including the sealed practice checkpoints, unchanged. Applied to both loop and plain (same lr).
- Cost: reuses the 4 existing source nets; 16 adaptation jobs of 2,048 updates, about 3 h wall clock with 8 concurrent CPU jobs (the previous 8-job run took 169 min; loop only takes about 4-5 jobs per seed-arm). /bin/bash.
- Pass marks (fixed now): loop F_eq mean over 2 seeds >= 59.1 (baseline mean 51.15 + 8.0) and each seed >= baseline + 4.0; plain row reported and must not gain more than the loop (else the effect is generic, not about the loop).
- Proven wrong if: mean gain < +4.0 or either seed loses more than 4.0. A drop of 8 or more would show decay was helping (informative, not a failure of the test).
- Follow-up only if gain >= +4: L2-SP style anchor (decay toward practised weights instead of zero) as a second, separate test. I do not expect this to interact with the queued lr / staged-unfreeze tests, but it should be run after them or with the same lr so the two are not confounded.
- My odds of pass: about 10%.

### Test 2: initialise the three never-practised marker-token rows to the mean of the trained token rows at adaptation start (untested; needs a ruling)
- Single change: at the start of adaptation only, rows for tokens that received no gradient in practice are set to the mean of the other token rows (same for loop and plain). Legality caveat: "which tokens got no gradient" is knowable from the practice log without a kind label, but the Director must rule it is not a hand rule; it is the standard new-vocabulary init. It differs from queued A (which changes practice data) and R-series (which change architecture).
- Cost: same reused sources; the F_few rungs only (k = 1, 4, 16, 64) x 2 seeds x 2 arms = 16 short jobs, about 1.5 h. /bin/bash.
- Pass marks: F_few mean over 2 seeds >= baseline + 10.5 (loop baseline: seed 0 (1+0+28+137)/1200 = 13.8%, seed 1 (1+0+3+190)/1200 = 16.2%) and each seed >= +5.0. F_eq only reported.
- Proven wrong if: F_few gain < +5 in both seeds. Then the random rows are not the bottleneck and the 3 tokens can be dropped from suspicion.
- Odds: about 10% (k=64 would have to go from 137-190 to about 250).

### Test 3: baseline noise re-measurement (measurement, not a design)
- Single change: two more seeds (2, 3) of the practised loop and practised plain rows, using the existing pipeline unchanged (new source nets, 12,000 steps, then the eq ladder). Purpose is to fix the bar, not to test an idea.
- Cost: loop source about 47 min per seed on CPU (2,800 s recorded), plain about 15 min; adaptation about 3 h; roughly 5 h total, /bin/bash.
- Decision rule fixed now: pooled run sd s over 4 seeds (per arm, rung-averaged F_eq). New bar for adaptation-side changes = 2.5 x s (paired) and for practice-side changes 3.5 x s (unpaired, 2 seeds per side). If s < 2.0, the F_eq bar +8.0 may be lowered to +5.0; if s > 3.5, it must be raised or seeds increased to 3.
- Proven wrong if: the pooled sd comes out between 2.2 and 3.4. Then the current +8.0 bar stands and the test only confirms it (my working guess of the truth is 1.5-2.8).

## 8. What I could not verify / risks

- Web sources: Fan (abstract only), Bansal (abstract only), Saunshi and Ouro (abstract via search), Parcae and iso-depth (search snippet and thin fetched summary; the iso-depth fetch did not give the exponent), grokking/weight-decay (snippet), Raventos (snippet), Reasoning Gym (abstract without transfer numbers). The residual-scaling paper was fetched and summarised; it is single-seed by its own admission. Treat every published claim as authors-only unless independently cited above.
- Test 1 and 2 odds are my guesses. Both are cheap because they reuse sealed source nets.
- The "0.82 shrink" figure is arithmetic on AdamW's decoupled decay at constant lr 1e-3 for 2,048 steps (shown by code reading; effect on accuracy untested). During adaptation lr is constant after a 50-step warmup, so this is what happens.
- Weight-decay-timescale scaling for larger models (that decay x lr x steps should be held fixed when width or steps grow) is from memory, not fetched; check before using it for lf-sz.
- I did not cover tiny-net optimisers (Muon, schedule-free) because nothing strong turned up.
