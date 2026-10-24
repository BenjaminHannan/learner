# Literature scan: raising affine / sq_plus / double_add (2026-10-24)

Method note: written from my own knowledge of the papers (no live web fetch was run, no code/GPU touched).
URLs are the arXiv abs pages I believe are correct; check before quoting. Labels:
SHOWN = result reported in that paper (in its own setting), SUGGESTED = my reasoning about our setup,
UNTESTED = nobody has tried it in our setup. Card experiments only; nothing here concerns the village model.

## 1. Methods (what / key result / mapping to us)

1. DreamCoder (Ellis+ 2020) https://arxiv.org/abs/2006.08381
   Wake-sleep: wake = search with neural recogniser; sleep-abstraction = compress solved programs into library;
   sleep-dreaming = train recogniser on programs sampled from the library, paired with their executed outputs.
   SHOWN: library+dreams beat either alone on list/text/physics domains. Mapping: our "dream" arm used random
   programs from a flat grammar, with NO library, and hurt. SUGGESTED: DreamCoder's dreams are sampled from a library
   that has already grown, so they are biased toward useful structure; ours were not. Our setup has no abstraction step yet.

2. CodeIt (Butt+ 2024) https://arxiv.org/abs/2402.04858
   ARC: sample programs, run them, relabel the failing program as a correct solution to the input->output it
   actually produced (hindsight), prioritised replay, train. SHOWN: relabelling + replay beat the no-hindsight
   baseline and set ARC SOTA for neural methods at the time. Mapping: this is the arm being tested now. Caveat
   SUGGESTED: CodeIt relabels onto the program's own outputs on the given input; our relabelled tasks are new puzzles,
   so they only help if relabelled puzzles look like pool puzzles (affine-like outputs are rare among random tries).

3. LILO (Grand+ 2023) https://arxiv.org/abs/2310.19791 and Stitch (Bowers+ 2023) https://arxiv.org/abs/2211.16605
   Stitch = fast corpus-guided top-down abstraction search over solved programs; LILO adds an LLM to name/document
   them. SHOWN: Stitch finds libraries orders of magnitude faster than DreamCoder's compressor; LILO beat DreamCoder
   on string/scene/graphics. Mapping: our solved add/mult programs contain repeated "build constant k from 1,2,10,100"
   sub-sequences; Stitch-style mining would extract them as macros. UNTESTED for numeric builders.

4. ExIt, expert iteration (Anthony+ 2017) https://arxiv.org/abs/1705.08439
   Search (expert) improves on the policy; policy imitates the expert; repeat. SHOWN: beat policy gradient on Hex.
   Mapping: our night loop IS ExIt with rejection sampling as the "expert". Lesson SUGGESTED: the expert only helps if
   it is stronger than the policy, i.e. a bigger/smarter search (point 5/6), not just more of the same sampling.

5. STaR (Zelikman+ 2022) https://arxiv.org/abs/2203.14465
   Keep self-generated rationales that reach the right answer; for failures, "rationalise" by giving the answer as a
   hint. SHOWN: bootstraps reasoning on CommonsenseQA/arithmetic. Mapping: our night = STaR without rationalisation.
   Hint analogue = relabelling (CodeIt). Label-free hints would be: reveal one intermediate value. UNTESTED.

6. AlphaCode (Li+ 2022) https://arxiv.org/abs/2203.07814
   Sample up to millions of programs, filter by the visible examples, cluster by behaviour on generated inputs, submit
   few. SHOWN: solve rate scales ~log-linearly with samples; filtering by examples is essential. Mapping: our
   32(+480) is tiny. SUGGESTED: budget is the cheapest lever; behaviour clustering also reduces duplicate trains.

7. Learning to search: PCCoder, Write-Execute-Assess, policy+value
   PCCoder (Zohar & Wolf 2018) https://arxiv.org/abs/1809.04682: predicts next statement conditioned on the
   current *execution state* (variable values), beam search over steps. SHOWN: much faster than DeepCoder on
   longer programs. Write-Execute-Assess (Ellis+ 2019) https://arxiv.org/abs/1906.04604: SMC over program
   prefixes, executing the partial program and a value net scoring the state. SHOWN: beat plain autoregressive
   sampling on CAD/graphics. Mapping: our ops are all total and deterministic, so each prefix can be executed on the
   few-shot inputs cheaply. SUGGESTED: feed executed intermediate values back to the model each step; prune
   prefixes whose values are duplicates/degenerate (all equal, out of range, repeated). A *label-free* value for a
   prefix is weak (no target for intermediates) except "distance of the latest value to the target output".

8. Hypothesis search / inductive reasoning with LMs (Wang+ 2023) https://arxiv.org/abs/2309.05660
   Propose many natural-language hypotheses, implement each as a program, verify on examples. SHOWN: big gains over
   direct prediction on ARC/Syntax-like tasks, with a verifier in the loop. Mapping: hypothesise the parameters first
   ("A=4,B=4"), then compile to steps. SUGGESTED: a two-stage output (parameter guess, then build program) separates
   inference (easy from examples) from construction (the part we fail).

9. Test-time training (Akyurek+ 2024) https://arxiv.org/abs/2411.07279
   Fine-tune per task on augmented copies of its demonstrations. SHOWN: large ARC gains. Mapping: our few-shot
   puzzle has 3 examples; leave-one-out tasks from them are cheap. Cost/benefit weak for 3.3M params: UNTESTED.

10. Bootstrapped / self-generated tasks (curriculum)
   Poesia+ 2024 https://arxiv.org/abs/2407.00695 (learn conjecturing: generate problems at the edge of ability, solve
   with the prover, train both). SHOWN in formal math (Peano). POET https://arxiv.org/abs/1901.01753 (co-evolve
   environments and agents). Mapping = point (c) below: generate harder puzzles by composing solved ones.

11. Prioritised replay: PER https://arxiv.org/abs/1511.05952 (SHOWN: faster RL by replaying high-error samples);
    HER https://arxiv.org/abs/1707.01495 (SHOWN: relabel failed goal as achieved goal; this is CodeIt's root).
    Mapping: weight rare kinds (the rare solved sq_plus/double_add programs) up; cap easy add/mult copies.
    SUGGESTED: with 17% Hard and add/mult dominating, replay probably drowns the few useful new solves.

12. GFlowNets https://arxiv.org/abs/2111.09266 (Bengio+). Train a sampler proportional to reward -> diverse modes
    instead of collapse onto one program per puzzle. SHOWN on molecules; program-synthesis uses are small-scale.
    Mapping: our nightly keep-all-fitting + rejection already approximates this; full GFlowNet is a big change. UNTESTED, last.

13. Constants / sketches
   Sketch (Solar-Lezama thesis, 2008): hole-filling with a solver. BUSTLE https://arxiv.org/abs/2007.14381 and
   TF-Coder https://arxiv.org/abs/2003.09040: bottom-up enumeration with value-based dedup and weighting of
   constants/ops. SHOWN: equivalence pruning by output values is what makes bottom-up search tractable.
   Deep Symbolic Regression https://arxiv.org/abs/1912.04871: policy over expression tokens, constants fit by
   an inner numeric optimiser, risk-seeking gradient. SHOWN: beats GP. Mapping: affine's hard part is the *constants*.
   Our model must emit ~4-5 steps just to build A and B from {1,2,10,100}. SUGGESTED: separate "what are A,B"
   (closed-form from two examples: A=(y2-y1)/(x2-x1), B=y1-A*x1) from "how to build them".
   Note: that closed form is a hand-coded solver; use it only as an *evaluation oracle* or as a clearly flagged hint, not silently.

14. Composing sub-skills / refactoring
   ReGAL https://arxiv.org/abs/2401.16467 (SHOWN: refactoring programs into shared helper functions raises
   LLM code-gen accuracy); DreamCoder/Stitch above. Library-learning gains come from shorter programs, not
   new capability: same functions, fewer tokens. Compositional generalisation in seq models is known to be brittle
   (SCAN, https://arxiv.org/abs/1711.00350; SHOWN fails on novel compositions unless trained on them; a meta-learning
   fix is Lake & Baroni 2023, https://www.nature.com/articles/s41586-023-06668-3).
   Mapping: affine = mult-then-add; the model has practised both but never their composition. Expect
   SCAN-style failure; this explains affine ~0% and is the strongest reason to put compositions in training.

## 2. Our three options (a)(b)(c)

(a) Macros ("build k", "x*A"). SHOWN elsewhere (Stitch/ReGAL) to cut length and search cost. SUGGESTED: with
    macros affine = BuildA, mul, BuildB, add = 4 tokens-ish instead of 5-9 raw steps; fits 7-step cap with margin.
    Risk: macros need arguments (which k?). Fixed macros for 1..30 add vocabulary; parametric macros change the
    action space. It changes the task definition (new ops), so held-out comparisons must note it. Mine macros only
    from programs the model itself found (no oracle), else it is cheating.
(b) Budget shaping. SHOWN (AlphaCode) that samples scale log-linearly; SUGGESTED: adaptive sampling is cheaper than
    anything else and tests whether the failure is reach or ranking. Per-step verifier: only valid for pruning
    degenerate/duplicate prefixes and "value-distance to target"; no intermediate ground truth exists. UNTESTED.
(c) Skill-composition dreams. Analogous to DreamCoder dreams but on-distribution (programs the model *found* on
    real puzzles) and CodeIt hindsight (label = executed output). SUGGESTED: strongest fit, because
    double_add = mult∘add and affine = add∘mult are exactly compositions of the two practised kinds. Caveat for
    honesty: composing add∘mult teaches the held-out structure directly; report it as "composition training",
    not zero-shot. Mix generic compositions (also add∘add, mult∘mult, 3-fold) not only the two held-out shapes, and
    report on sq_plus (x*x not a composition of practised kinds) as the clean generalisation control.

## 3. Ranking: five ideas, cheapest first (one change each)

1. Adaptive search budget for unsolved puzzles. UNTESTED in our setup; SHOWN generally (AlphaCode).
   Change: puzzles with 0 fits after 32+480 get 8x more samples (about 4000) at night 4 only; nothing else.
   Pass (fixed now): held-out affine+sq_plus+double_add combined solved >= 3% (baseline ~0-1%) AND Hard >= 17%.
   Proves it wrong: still 0 solved on all three at 8x budget -> the proposal distribution cannot reach them;
   stop spending on sampling, go to 3/4.
2. Execution-state conditioning + prefix dedup (PCCoder-style). SHOWN in PCCoder; UNTESTED here.
   Change: at each step the model sees the values computed so far on the example inputs; discard prefixes whose new
   value equals an existing value or is out of [-1000,1000]. Keep sampling budget fixed.
   Pass: Hard fit rate at fixed 32+480 budget rises >= 3 points absolute over matched-seed baseline, no regression on add/mult.
   Wrong if: fit rate within +-1 point (noise across 3 seeds), meaning the model already tracks values internally.
3. Skill-composition dreams (GPT's idea), as a *small* mix. SUGGESTED, UNTESTED.
   Change: from programs found on real pool puzzles, build compositions (generic pairs/triples, inputs drawn
   like pool queries, labels = executed outputs, fit check by execution), mix at 10-20% of the night's training set.
   Pass: affine >= 10% and double_add >= 10% on held-out puzzles, Hard not below 11% (the random-dream collapse level was 1-2%).
   Wrong if: Hard falls below 8% (same failure as random dreams: distribution shift), OR training loss on composed
   items drops but real affine stays <3% (model memorised composed dreams, did not transfer to real examples).
4. Fixed macros mined from the model's own solved programs (Stitch-style, 2-3 macros: "build B", "x*A").
   SHOWN to help in other domains; UNTESTED here.
   Change: extract the two most frequent repeated sub-sequences from last night's kept programs; add as single
   ops for the next night; re-expand when scoring so fits are real. Pass: median kept-program length on add/mult
   falls >= 30% AND affine >= 5%. Wrong if: length falls but affine stays <2% (the composition, not length, was the barrier)
   or macro mining picks out junk (fewer than 2 macros appear in >=5% of kept programs).
5. Prioritised replay weighted toward rare kinds + shortest-program dedup. SUGGESTED (PER/CodeIt).
   Change: per night, replay weight inversely proportional to kind frequency; keep only the shortest fitting program
   per puzzle. Pass: sq_plus or double_add >= 3% with Hard not lower. Wrong if: held-out stay at 0 while
   train-kind accuracy drops (just less data on the easy kinds; no rare-kind discovery to upweight).
   (Hindsight relabelling, running now, is not ranked; judge it with the same pass mark as idea 3: affine >= 10%.)

Order of work: run 1 then 2 in parallel (both only change search); 3 and 4 only change training data / action space.
Do one at a time against a matched-seed baseline, 3 seeds, since night-to-night noise (6/11/13/17%) is large.

## 4. For a high-school senior (5 sentences)

Our little model can already learn simple tricks like "add 4" or "times 4", but it fails when a puzzle needs both tricks glued together, like "times 4, then add 4". Scientists who built similar learners found three things that help: let it guess many more times, let it check each step of its guess as it goes, and let it practise on glued-together versions of tricks it has already mastered. Making up random practice problems hurt us, probably because they looked nothing like the real ones, so any practice must be built from things the model actually solved. We will test one idea at a time, decide the passing score before running, and keep the result that would prove the idea wrong. If even a huge number of guesses never finds a single gluing, the model simply cannot think of the idea yet, and we must teach composition directly.
