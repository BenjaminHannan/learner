# Research-lead sweep, 2026-09-29: merged findings and the five tests most likely to move the finish line

Written 2026-09-29 (`date -u` 01:58 at start of merge) by the research lead. Seven Sonnet agents each researched one angle (files `angle-1` to `angle-7` in this folder; the shared brief is `BRIEF.md`). I read every report, checked the factual claims about our own code and results against the repo, and merged them. **Nothing was trained or run.** Labels: **shown** = a measured result in a cited source or a repo file; **suggested** = reasoning; **untested** = nobody has run it here. "Authors only" = not reproduced by anyone independent that we found. Most papers were read at abstract or HTML-summary level (the PDF fetches failed); treat every external number as second-hand until someone opens the paper. The small card experiments and the village model are not part of any claim here.

## 0. Plain summary for Ben
1. The tiny puzzle solvers that beat big models (TRM, HRM) win mainly by two plain tricks: grading the answer after every round of thinking, and **huge free variety** (the same maze turned and flipped 8 ways). Our loop already has the first trick. It does not get the second when it learns a new kind: it sees exactly k mazes, never their turned copies. That is the cheapest big lever we found (test 1).
2. The stop does not fire on new mazes, but the answers are good. At k = 256 the practised loop gets 256 of 300 mazes right and still uses all 48 rounds on all 300. Something we noticed: after the k = 16,384 sleep, which never trains the stop head at all, the stop fires on 292 of 300. So the stop head works when the thinking "looks familiar". A free read of the saved nets can tell which of the three queued stop fixes is aimed at the right cause (test 2).
3. Numbers puzzles: the stored answer is "the first answer a fixed brute-force search finds". To copy it, the net would have to replay the search's dead ends. A known fix (from Sudoku and N-Queens work) is to grade the net against whichever correct answer is nearest its own guess (test 3).
4. "Gets better with use" has never been measured over more than 3 nights, and nobody has checked whether the net slowly loses its ability to learn new things. Test 4 runs 5 days, a new kind each day, and measures that.
5. For the assistant's memory, the published evidence says the search step (which notes get found) matters more than clever memory systems. We don't yet know whether our 1.2B talker can read the right notes when it is handed them. Test 5 answers that in under an hour.

## 1. Cross-check: what I verified and what I corrected
- **Shown (code):** training draws 1..16 rounds, gradient on the last <=6 (`scripts/claude_fewex_net.py:24`), and tests read up to 48 rounds (`scripts/claude_fewex_bench.py:76-78`). The stop needs stop-prob > 0.5 AND 3 identical answers.
- **Shown (RESULTS-EQ.md holdout table, lines 75-83):** practised loop, seed 0: k=256 has 256 of 300 right and 300 of 300 cap hits; k=16,384 has 274 right and 163 cap hits; **sleep16384 has 289 right and only 8 cap hits (mean 10.0 rounds)**. Sleep (`claude_fewex_bench.py:208-228`) trains cross-entropy only, with **no stop-head loss**, on 8 mazes + 4 sums + 4 grids per step. So the head fired after a change to the body alone. None of the agents noticed this. It favours angle 4's cause 1 (the head reads maze states that are off its practised distribution) over "the stop target cannot transfer" (suggested).
- **Shown:** there is no augmentation anywhere in the few-example ruler (grep for rot/flip/augment in `claude_fewex_*.py`). Angles 1 and 2 both found this on their own and both propose D4 augmentation.
- **Shown:** the sleep replay store is fixed at 128 items per kind (`claude_fewex_data.py:43-46`), although generators exist. The older night tests (`claude_slp358n3_nights.py:278`) replayed fresh generated puzzles instead.
- **Shown:** adaptation uses AdamW wd 0.1, constant lr after a 50-step warm-up (`claude_fewex_bench.py:170-173`). The maze tokens reuse the operator tokens "/ + *" (`claude_rsn358m_maze.py:28`), which sums and grids never use.
- **Corrected (angle 3):** the report calls the stored numbers answer "an arbitrary tie-break". It is deterministic: `claude_blurt1.solve` returns the first solution of a depth-first search over pairings of the *sorted* hand (`claude_blurt1.py:45-57`), while the net sees the numbers shuffled (`claude_rsn358a_envs.py:251`). So the label does carry a rule, but predicting it means simulating the search, failed branches included. Its proposed fix, "a canonical answer chosen by a fixed rule", has the same flaw, because any fixed choice among valid answers needs search to compute. I replace it with a min-over-valid-answers loss (test 3). The H2 fallback (a random valid answer per draw, `artifacts/claude-dir-h2-numbers-20260928/DESIGN.md` section 5) is the one-of-many "random target" baseline; min-loss is a different, known alternative.
- **Conflict settled (angles 1 vs 7):** angle 1 calls "train 16, test 48" the biggest gap. Angle 7 says it is not a defect for accuracy. The repo sides with angle 7 on accuracy: learned-stop reads are within 0 to 14 of 300 of the fixed-16 read. So training to 48 is a stop fix, not an F_eq fix. It waits on test 2 (it is angle 4's T2) and is not in the top five.
- **Noise (angle 7, arithmetic checked against `artifacts/claude-dir-lr-20260928/NOISE.md`):** same-start seed gaps in F_eq are at most 2.5. The +8.0 bar is fair for adaptation-side changes on the sealed source nets. Practice-side changes (new source nets) carry more spread: the sparse loop moved +3.9 and -6.3. Those need 3 seeds or a larger bar. Tests 1 and 2 are adaptation- or read-side on purpose.

## 2. By angle (full text, sources and marks in each angle file)
Each row gives the strongest sources, what is shown vs suggested, how it maps to our problems, and the angle's best cheap test.

### Angle 1: tiny looped reasoners (`angle-1-looped-reasoners.md`)
- **Sources:**
  - TRM, https://arxiv.org/abs/2510.04871 (authors only).
  - ARC Prize HRM analysis, https://arcprize.org/blog/hrm-analysis (independent rerun).
  - HRM mechanistic analysis, https://arxiv.org/html/2601.10679 (independent, one group).
  - TRM ARC checkpoint analysis, https://arxiv.org/html/2512.11847v1.
  - Bansal et al., https://arxiv.org/abs/2202.05826 (abstract only).
- **Shown:**
  - Deep supervision with a detached carried state was the biggest HRM factor: one refinement pass is worth +13 points (ARC Prize).
  - The hierarchy is worth about 5 points and ACT halting only marginal gains.
  - Heavy augmentation matters a lot: 8 dihedral copies for mazes, up to 1,000 for Sudoku.
  - EMA of weights is worth 7.5 points on Sudoku (authors only).
  - HRM often has no fixed point and corrupts correct answers when run longer.
  - TRM trains and tests at the same depth.
- **Maps to:**
  - Our recipe already has input re-injection, a short BPTT window, random-depth loss and a BCE halt.
  - The gaps are augmentation at adaptation, EMA, and the untrained rounds 17-48.
- **Best cheap test:** D4 augmentation at adaptation (merged into test 1). Runner-up: EMA of weights during adaptation (decay 0.99, one run).

### Angle 2: new task kinds (`angle-2-new-kinds.md`)
- **Sources:**
  - TTT, Akyurek et al., https://arxiv.org/abs/2411.07279 (authors only).
  - ARChitects product of experts, https://arxiv.org/abs/2505.07859.
  - CompressARC, https://arxiv.org/abs/2512.06104.
  - ARC Prize 2024 report, https://arxiv.org/abs/2412.04604.
  - Task diversity, https://arxiv.org/abs/2306.15063.
- **Shown (authors):**
  - Removing geometric augmentation during test-time training is the largest single ablation loss.
  - Voting across symmetry views helps.
  - CompressARC (76k weights, no pretraining) reaches 20% on ARC-AGI-1, but fails on connectivity and planning.
  - No source shows gains that build up across tasks. TTT and CompressARC throw each task's changes away.
- **Maps to:** item 3 (few examples) and item 4 (carry-over). Nothing here is evidence for improve-with-use.
- **Best cheap test:** D4 augmentation of the k adaptation mazes (test 1). Free companion: a D4 vote at read-out on the existing adapted checkpoints (report-only).

### Angle 3: search inside the model (`angle-3-search.md`)
- **Sources:**
  - Ye et al. (diffusion beats autoregression on Countdown/Sudoku), https://arxiv.org/abs/2410.14157 (authors only).
  - Stream of Search, https://arxiv.org/abs/2404.03683.
  - TRM.
  - Geiping, https://arxiv.org/abs/2502.05171.
  - Added by me: Nandwani et al., one-of-many solutions, https://arxiv.org/abs/2008.11990 (search-result summary; up to +21 points over baselines on N-Queens, Futoshiki and Sudoku, authors only).
- **Shown:**
  - The puzzle is the 24-game with a 7-token postfix answer. Median 22 valid answers per hand (angle 3, from the diagnosis files).
  - Small diffusion models reach 52% on Countdown-4 at 6M weights, but trained on about 450k fresh problems.
- **Suggested:**
  - Our 1,062 practice hands are roughly 500x too few for search to emerge.
  - Why the loop cannot fit (0.38 / 0.56 exactness) is corrected in section 1: the label is the brute-force solver's first find.
- **Best cheap test:** the min-over-valid-answers loss (test 3). Follow-ups: masked-answer denoising, and noisy starts, which would also give a label-free stop from agreement across starts.

### Angle 4: adaptive computation and stopping (`angle-4-stopping.md`)
- **Sources:**
  - Path independence, https://arxiv.org/abs/2211.09961.
  - Bansal et al., https://arxiv.org/abs/2202.05826.
  - Geiping, https://arxiv.org/abs/2502.05171.
  - Jacobian regularisation of equilibrium models, https://arxiv.org/abs/2106.14342.
  - CALM exit calibration, https://arxiv.org/abs/2207.07061.
  - All abstract only.
- **Shown:** nets that reach the same end state from different starts extrapolate their thinking time better (authors).
- **Suggested ranked causes of the dead stop:**
  1. The fixed head is offset by the shift to maze states. The sleep clue in section 1 supports this.
  2. Rounds 17-48 are never trained.
  3. The "exact now" target is almost always 1 late in practice.
  4. Answer flicker breaks the 3-agree rule.
- **Maps to:**
  - Convergence is a precondition for the queued SL test, not an alternative to it.
  - Nobody has measured per-round movement over the 48 rounds.
- **Best cheap test:** the zero-training per-round read (test 2). Then train to 48 rounds (T2) or a contraction penalty (T3), whichever the read points to.

### Angle 5: continual learning and sleep (`angle-5-sleep.md`)
- **Sources:**
  - Effect of scale on forgetting (Ramasesh), https://research.google/pubs/effect-of-scale-on-catastrophic-forgetting-in-neural-networks/.
  - Sparse memory finetuning, https://arxiv.org/abs/2510.15103 (authors only).
  - Loss of plasticity, Dohare et al., Nature 2024, https://www.nature.com/articles/s41586-024-07711-7.
  - Scale only delays plasticity loss, https://arxiv.org/abs/2606.24752.
  - SDFT, https://arxiv.org/abs/2601.19897.
- **Shown:**
  - Bigger nets forget less mainly when they are pretrained. Nets trained from scratch do not reliably benefit.
  - Sparse memory finetuning forgets 11%, vs 71% for LoRA and 89% for full fine-tuning (facts, not skills).
  - Plain nets slowly lose the ability to learn new tasks over long task sequences.
- **Maps to:**
  - lf-8's pass (old grids kept 181 / 177 vs 120 / 61 of 200) mixes size and depth; `lf-sz` checks it.
  - Nothing in the repo measures plasticity.
  - Generator replay is an upper bound for puzzles. Real user data has no generator, so keep the two cases apart.
- **Best cheap test:** many days, with a plasticity probe (test 4). CPU-feasible runner-up: after the maze day, update only the top 10% of weights by maze vs old-kind gradient ratio (run after KS Lead 0).

### Angle 6: memory for assistants (`angle-6-memory.md`)
- **Sources:**
  - LongMemEval, https://arxiv.org/abs/2410.10813.
  - MemDelta audit, https://arxiv.org/abs/2606.29914 (one unreproduced preprint).
  - Fine-tuning vs retrieval, https://arxiv.org/abs/2312.05934.
  - Memory layers at scale, https://arxiv.org/abs/2412.09764.
  - Sparse memory finetuning.
- **Shown:**
  - Long context collapses for small readers: Llama-3.1-8B loses 55 points from the evidence-only setting.
  - In the audit, the retriever and embedder dominate, and Mem0 ties plain retrieval with a matched embedder.
  - Vendor scores (Mem0 94%, Hindsight 91%, Zep 71%) are authors only and not comparable.
  - No primary LongMemEval score for a 1-2B reader was found.
- **Maps to:**
  - Items 1 and 6.
  - The design note `design/v3/30-modes/382-memory-store-interface.md` names MiniLM as the retriever, which the audit calls the weak-embedder trap.
- **Best cheap test:** what the talker sees: evidence only vs top-10 retrieved vs top-10 as short notes (test 5). Then M1, an embedder swap, and M3, an "I don't know" gate on retrieval scores.

### Angle 7: everything else (`angle-7-other.md`)
- **Sources:**
  - Task diversity, https://arxiv.org/abs/2306.15063.
  - Bansal et al.
  - Looped-model scaling, https://arxiv.org/abs/2604.12946 and Ouro, https://arxiv.org/abs/2510.25741 (snippets).
  - Looped residual-scale rule, https://arxiv.org/html/2606.18524v1.
- **Shown:** in language-model scaling, a repeated round is worth less than a distinct layer, and looping adds no knowledge capacity (authors). That makes item 7 ("the gap does not shrink") a real risk.
- **Shown (code):**
  - Adaptation decays every weight toward zero (wd 0.1, about 18% over 2,048 steps), not toward the practised weights.
  - The loop got one learning rate while the plain net got three to choose from.
- **Best cheap tests:**
  - wd 0 at adaptation (about 10% odds).
  - Two more baseline seeds to fix the practice-side noise bar.
  - For `lf-sz`: sweep learning rate per width.

## 3. Ranked shortlist: the 5 tests most likely to move the finish line
Ranked by (chance it passes) x (how much of the finish line it moves) x (improves with use / holds with scale). Chances are my guesses, not measurements. Each is one change, with marks fixed here before any run. The Director may tighten the marks but not loosen them after scores exist.

### 1. D4 augmentation of the k adaptation mazes (items 3, 4; angles 1 + 2 converged)
- **Change:** in the maze adaptation step only, apply one random rotation/reflection (of 8) to each maze in each batch. Wall, start, goal and path are transformed together. Same k mazes, same 2,048 updates, same sealed source nets, same scoring (no voting). Applied to every arm (practised loop, fresh loop, plain) so the ruler stays fair.
- **Why:** TTT and TRM both list augmentation as their largest ablation, and it multiplies every example the user gives by 8. That is the improve-with-use shape, and it does not depend on model size (suggested).
- **Pass:**
  - Practised-loop F_eq at least +8.0 over its own un-augmented row (mean of seeds 0 and 1, each seed at least +4.0), OR F_few at least +10.5 (each seed at least +5).
  - AND the loop-minus-plain F_eq gap, both arms augmented, no smaller than today's +17.2 minus 3.3.
- **Wrong:** loop gain under +4.0 in both seeds, or plain gains as much as the loop (gap shrinks by more than 4).
- **Report-only:** 8-view plurality vote at read-out on the same nets. Also the share of mazes whose answer is the same under all 8 views.
- **Cost:** same as a baseline adaptation ladder. About 3 h per arm-seed on the Mac CPU; on the 5070 Ti about 20-40 min per arm-seed (estimate, not measured; needs the fp32 CPU-equivalence smoke first). $0.
- **Flag for the Director:**
  - Choosing D4 is a symmetry prior picked by hand, the same flag H9 raised for R2.
  - It is valid for mazes and grids, not for sums, so applying it assumes the new kind is symmetric.
  - A kind-blind follow-up is a second change: clone the net, adapt with and without augmentation, keep the better on a held-back few of the k.
  - R2 (soft-D4 inside the architecture) is queued. Test 1 tells whether the data route gives the same gain without a new practice run.
- **Chance:** about 35%.

### 2. Zero-training per-round read of the saved nets (item 2; angle 4 T1 + angle 1 D1 + the sleep clue)
- **Change:** none to any net. On the saved practised-loop checkpoints (k = 64 to 16,384, both seeds) and the sleep64 / sleep16384 checkpoints, on the 300 dev mazes, record for every round 1..48:
  - state movement |h_t - h_{t-1}| / |h_t|;
  - stop probability q_t;
  - whole-answer flips;
  - accuracy;
  - agreement of the round-48 answer between a zero start and a small random start;
  - for the sleep pairs, the shift of the halt logit on the same mazes.
- **Classify each net (marks from angle 4):**
  - **HEAD:** on mazes right at round 16, q exceeds 0.5 at some round in under 30% of them.
  - **FLICKER:** q exceeds 0.5 in at least 70% of them, but the 3-agree rule is met in under 30%.
  - **CONVERGES:** movement at rounds 44-48 is no more than 0.25x the median at rounds 2-6, on 8 or more of the 10 adapted nets, and the two starts agree on at least 90%.
  - **DRIFTS:** movement at rounds 44-48 exceeds 0.5x the median at rounds 14-16 on at least half the nets, or the two starts agree on under 70%.
- **Wrong** (the causes are not separable this way): HEAD and FLICKER conditions both pass on more than 70% of mazes, yet the stop fires on under 30%.
- **What it decides:**
  - HEAD points to Pond and SL.
  - FLICKER points to a read-rule change.
  - DRIFTS points to training to 48 rounds or a contraction penalty.
  - If the sleep16384 halt-logit shift explains its 8 cap hits, that also supports mixing old kinds into the adaptation day.
- **Cost:** Mac CPU, a few hours, $0. Best added as extra columns to the queued `sl-1-read` job, not a separate job. It needs the adapted checkpoints: the Director's 23:07 log says loop k*.pt files were missing on the Mac and ks-1 rebuilds them.
- **Chance it gives a clear verdict:** about 70%. It moves the finish line only through the fix it picks.

### 3. Numbers: grade against the nearest valid answer (numbers; angle 3 corrected)
- **Change:** the same pool as H2 (36,782 pairs), seeds 13 and 14, and the same steps and code. Only the training target changes. For each draw, enumerate the valid postfix answers (the enumerator exists in the diagnosis scripts). The token loss is the whole-answer cross-entropy against the valid answer with the lowest loss under the net's current prediction ("min-loss"). The halt target stays "equals the chosen target", which now amounts to "is valid". Kind-blind. The checker is used only to build training data, never at test.
- **Why:** the stored answer is the solver's first find, which needs the search's dead ends to predict (section 1). One-of-many work shows the choice of target among valid answers matters on Sudoku and N-Queens (Nandwani et al., authors only).
- **Pass:**
  - Loop practice validity at least 0.90 on both seeds (H2: 0.38 / 0.56).
  - AND numbers4 at least 36 of 300 on both seeds (3x the floor of 12).
  - Plain-net row reported. The gain counts as the loop's only if the loop beats plain by at least 12 of 300.
  - Sums4/grids5 gates as in H2.
- **Wrong:** validity below 0.60 on both seeds (the label rule was not the blocker). Validity at least 0.90 with numbers4 at 12 or less on both seeds means it memorised again, so the next step is the larger fresh pool (a separate change). Scores of 13 to 35 are partial: no claim.
- **Worth adding as a second arm:** H2's random-valid-answer fallback, run beside it. That is the exact random-vs-min comparison in the one-of-many literature.
- **Cost:** 2 loop + 2 plain nets, about 2 h on the 5070 Ti (estimated from the diagnosis's 5090 figures). $0 on BensPC.
- **Chance:** about 25% to pass fully, about 50% to fit.
- **Needs:** the Director's call that choosing among code-made valid answers is not "telling the kind".

### 4. Five days, five kinds, with a plasticity probe (item 5 and Ben's premise; angle 5 MD1)
- **Setup:** five day/night cycles, a new held-out kind each day (mazes, then H1's graph and rank, then substitutes from A). Each night is the existing sleep.
- **Change:** night replay of old kinds drawn fresh from the generators with true labels, instead of the fixed 16-item store. This is a disclosed puzzle-only upper bound. Real user data has no generator.
- **Probe (every arm):** after each night, adapt a copy on 64 new 9x9 mazes and score F_few.
- **Pass:**
  - Every earlier kind at least +20 of 200 (mazes +30 of 300) over the 16-store arm on both seeds, mean of 3 sleep draws, margin max(6, 2 x SE).
  - AND the probe at night 5 no more than 8 F_eq points below night 0.
  - The plain-net row is reported beside it.
- **Wrong:** within 5 of the store arm on every earlier kind in both seeds (store size is not what limits sleep), or the probe falls by more than 15 in both arms (plasticity loss is real, so the next single change is an L2-toward-start regulariser).
- **Cost:** about 2-4 h on the 5070 Ti. A 3-cycle pilot takes 1-2 h. $0 on BensPC.
- **Depends on:** H1's kinds (dir-h1-heldout-r2 running).
- **Chance:** about 40% for the store-vs-generator gain. The probe is the first measurement of "gets better over many days" in this repo, whatever the verdict.

### 5. Can the 1.2B talker read the right notes? (items 1, 6; angle 6 M2)
- **Setup:** a 100-question LongMemEval-S dev slice, stratified by type and including about 6 abstention questions. Hash it before any run. The other 400 questions stay sealed for the final.
- **Change:** what LFM2.5-1.2B is given. Arms:
  - (a) evidence sessions only (oracle);
  - (b) top-10 retrieved rounds;
  - (c) the same top-10 as short fact notes;
  - plus closed-book and plain rows.
- **Pass:** oracle at least 50%, AND notes beat raw top-10 by at least 10 points (paired McNemar, p < 0.05).
- **Wrong:** oracle under 30%. Then the reader is the limit, and item 6 needs a bigger or trained reader before any retriever work. Raw top-10 beating oracle also counts as wrong.
- **What it decides:** whether item 6 is a retriever job or a reader job before anyone builds more memory machinery.
- **Cost:** under 1 h on the 5070 Ti. $0.
- **Chance:** about 45% to pass fully; about 90% to give a decisive answer.

### Next in line (not in the top five, each one change)
- wd 0.1 to 0 at adaptation (angle 7), and EMA of weights at adaptation (angle 1). Cheap, adaptation-side, about 10-20% each.
- Train rounds to 48, or a contraction penalty. Run only if test 2 says DRIFTS.
- Top-10% sparse update after the maze day. Run after KS Lead 0.
- Swap the embedder (M1), then an "I don't know" gate on retrieval scores (M3).
- Two extra baseline seeds to fix the practice-side bar (angle 7 T3). Worth doing before sealing marks for any new practice-side design, including the sparse MoE.
- lf-sz and MoE: sweep learning rate per width so "bigger" is not handicapped by a stale lr.

## 4. What I could not verify
- External numbers come from abstracts and machine summaries of HTML pages. Before any mark depends on one, open the paper.
- The TRM figures (maze 85%, Sudoku ablations) are the authors' own.
- Costs on the 5070 Ti are estimates, not timings.
- Test 2 needs the adapted checkpoints on the Mac (see the Director's 23:07 UTC 09-28 log).
- Test 1's flag and test 3's "kind" question are the Director's and Ben's calls, not mine.
- An outside opinion on the two hard "two readings" questions (the dead stop; why the loop cannot fit numbers) is drafted at `reviews/gpt-diagnose-stop-and-numbers-2026-09-29.md`.
