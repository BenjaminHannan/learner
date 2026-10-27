# Angle 2: handling new task kinds (ARC test-time adaptation, CompressARC, task diversity)

Written 2026-09-29 01:55 UTC (`date -u`), research agent (Sonnet). Nothing was run, trained or edited. Labels: shown (source's own measured result, or a repo file I cite) / suggested (my reasoning) / untested. "Author-only" = not independently reproduced that I could find. Read depth is stated per source: I read abstracts, search snippets and short fetch summaries. Several PDFs did not render as text, so I have NOT read full papers. Numbers below come from fetch summaries and should be re-checked before anyone builds on them (BRIEF and CLAUDE.md both say check claims against the source).

Small card experiments and the village model are not mentioned here. Everything below is about the reasoner and the 9x9 maze ruler.

## 1. Strongest sources

**S1. Akyurek et al., "The Surprising Effectiveness of Test-Time Training for Abstract Reasoning" (arXiv 2411.07279, https://arxiv.org/abs/2411.07279).** Read: abstract plus a fetch summary of the ablation figures.
- Shown (authors' figures, ARC subset, 1B-8B LMs; author-only, though ARC Prize 2024 report says TTT was central to winners): leave-one-out tasks built from the demonstration pairs give about 29%. Dropping the geometric transformations of those tasks costs about 16 tasks (to about 55% of the baseline). A shared adapter instead of a per-task LoRA costs about 7 tasks. Training on the demonstration outputs helped modestly (26 -> 29). The direct input->output format was worse (about 11 tasks).
- Also shown by them: augmented inference with voting across transformed views adds on top of TTT (I did not get the exact numbers).
- Shown by them: on BIG-Bench Hard a SHARED adapter helped and example-permutation mattered (55.7 without vs 57.8 with), so "per-task" is not universal.
- Suggested reading: the augmentation (data-side symmetry) is the biggest single ingredient after the basic idea of training on the task itself.

**S2. ARChitects, "The LLM ARChitect" (2024 paper award runner-up, https://da-fr.github.io/arc-prize-2024/the_architects.pdf) and "Product of Experts with LLMs: Boosting Performance on ARC Is a Matter of Perspective" (https://arxiv.org/abs/2505.07859, ICML 2025).** Read: search-result summaries only; the PDF did not render.
- Shown by authors (author-only, but the 2024 private score of 53.5 was measured by the competition): generate a few candidate answers by depth-first search, then re-score each candidate under every symmetry-transformed view of the puzzle and combine scores as a product (sum of negative log-likelihoods). Choose the candidate that all views agree is likely. Test-time training precedes this.
- Suggested: this is voting across augmentations with a learned scorer in place of a fixed majority. It only needs the net to give a likelihood for a whole answer.

**S3. Liao and Gu, "ARC-AGI Without Pretraining" (CompressARC, https://arxiv.org/abs/2512.06104; blog https://iliao2345.github.io/blog_posts/arc_agi_without_pretraining/arc_agi_without_pretraining.html).** Read: search summary plus blog-page summary.
- Shown by authors (author-only; the 2025 competition report lists it in the "zero-pretraining" group): 76K parameters, no pretraining, no dataset, trained only on the single target puzzle for about 2,000 Adam steps (lr 0.01), about 20 minutes on an RTX 4070 per puzzle. 20% on the ARC-AGI-1 evaluation set, about 34.75% on the training set, 4% on ARC-AGI-2 (pass@2).
- Shown: the architecture bakes in equivariance to colour permutations, spatial flips and rotations (weight tying between height and width), and to the order of example pairs. The objective is compression (description length of the puzzle including the unknown output).
- Shown by authors: it fails on counting, long-range extension, connectivity ("topological properties"), and agent planning. Mazes are exactly a connectivity/planning kind, so do not expect CompressARC as-is to solve them. Suggested.

**S4. Jolicoeur-Martineau, "Less is More: Recursive Reasoning with Tiny Networks" (TRM, https://arxiv.org/abs/2510.04871).** Read: search-result summary.
- Shown by authors: one 2-layer, 7M-parameter looped net; Maze-Hard 85%, Sudoku-Extreme 87%, ARC-AGI-1 45%, ARC-AGI-2 8%. Trained on about 1,000 ARC examples. From memory (untested here, please verify) the ARC setup relies on heavy augmentation (many dihedral and colour-permuted copies per puzzle) and votes over augmented views at test time.
- Suggested relevance: this is the closest published cousin of Premonition's loop (small, shared weights, looped). It is the model NVARC 2025 borrowed from (S5). It shows that augmentation plus voting are used with small looped nets on maze-like tasks too.

**S5. ARC Prize 2025 Technical Report (https://arxiv.org/html/2601.10904v1) and ARC Prize 2024 Technical Report (https://arxiv.org/abs/2412.04604).** Read: abstract and a fetch summary only.
- Shown (competition-measured): 2024 top score rose from 33% to 55.5% by TTT and program synthesis. 2025: NVARC 24.03% on ARC-AGI-2 (improved ARChitects-style TTT model, a TRM-based component, and a large synthetic-data pipeline), ARChitects 16.53% (2D-aware masked-diffusion model with recursive self-refinement and multi-perspective scoring), MindsAI 12.64% (test-time fine-tuning, augmentation ensembles, tokenizer dropout). The report's theme: "refinement loops" (per-task iterative optimisation with feedback), and it says performance is constrained by knowledge coverage.
- Also related, not opened in detail: Li et al., "Combining Induction and Transduction" (https://arxiv.org/abs/2411.02272, abstract only). Shown by authors: program-writing models and direct-output models solve different puzzles; an ensemble gets close to human level on their ARC subset. Greenblatt's sample-many-programs approach: from memory only, not opened.

Task-diversity sources (S6 group), abstract-level only: Raventos et al. (https://arxiv.org/abs/2306.15063): below a threshold number of pretraining tasks the transformer just acts as a Bayes estimator over the tasks it practised; above it, it generalises to unseen linear regression tasks (shown by authors, linear regression only). Kirsch GPICL (https://arxiv.org/abs/2212.04458): sharp phase changes between generalise / memorise / fail to meta-train as size and task count change. Chan et al. 2022 ("Data distributional properties drive emergent in-context learning", not opened): burstiness and many rare classes are what make ICL appear; and Lake and Baroni MLC (Nature 2023, not opened): meta-learning over many made-up-rule episodes gives human-like compositional generalisation. All standing-01 material; I add only what it says about the threshold's size below.

## 2. Answers to the four key questions

**(a) Which ingredients made test-time adaptation work?** Ranked by evidence strength (suggested ranking from the sources above):
1. Training on the task's own examples at test time at all (the whole TTT point; shown in S1, S5).
2. Symmetry augmentation of the adaptation examples (shown in S1: removing it is the largest single drop in the ablation I saw; TRM and MindsAI also rely on it).
3. Augmented inference plus aggregation (voting or product-of-experts scoring): shown in S1/S2 as an extra gain on top of TTT; author-only for exact sizes.
4. Per-task adapter vs shared: per-task better on ARC, shared better on BBH (S1). Already the LoRA-day lead in standing 03; not proposed here.
5. Leave-one-out: shown in S1 vs direct format, but it needs a net that takes examples as input. Premonition's net takes one puzzle at a time, so it does not fit (standing 01, lead 3).
Note: all of these were shown on models with 1B+ weights or, for TRM/CompressARC, on grid puzzles with only colour tokens. Nothing here is shown at 1.6M weights on mazes.

**(b) What does CompressARC imply for the "fresh loop" row and for improve-with-use?** Suggested, untested:
- The fresh loop scores 20.67 / 21.50 F_eq (artifacts/claude-fewex-20260927/RESULTS-EQ.md). CompressARC shows a tiny net trained from scratch on one puzzle can work, but only because symmetry was built into the architecture, the objective was compression, and it ran 2,000 steps per puzzle. Premonition's fresh loop has none of these, so a low fresh-loop row is what S3 predicts. It does not say from-scratch is a dead end.
- It supports the "practised loop beats fresh" story from the other side: what practice supplies is priors that CompressARC hard-codes (symmetries, adjacency). This makes symmetry a shared candidate for both rows.
- For improve-with-use: CompressARC's per-puzzle cost (20 min on a 4070) is per new puzzle and throws everything away afterwards. Improve-with-use needs the opposite: what was learned on one puzzle kept. TTT papers (S1) also discard the adapter after each task, so none of these sources shows improvement that accumulates. That gap is real and I found no source closing it (untested).

**(c) How diverse must tasks be at ~1-10M weights?** I found no source with a measured threshold at this size. Shown at other scales only: GPICL has sharp transitions depending on size and number of tasks (abstract). Raventos found a threshold for linear regression in a small transformer (their model is on the order of 10M weights, from memory, unverified; the threshold was in the thousands of tasks, from memory, unverified). Suggested: Premonition has 2 practised kinds and the brief queues A (10 kinds); treat 2 kinds as below any plausible threshold, and treat maze carry-over so far (51 vs 34 plain) as a first sign that even two kinds transfer some prior. The number of practice tasks that count is probably many random instances of a kind (thousands) times many kinds (tens), not one or the other. Untested.

**(d) Cheapest change likely to lift F_eq/F_few and scale with size?** Suggested: symmetry (D4) augmentation of the k adaptation mazes, plus voting across the 8 views at read-out. Both are evidenced by S1/S2/S4 (augmentation was the largest ablation effect I saw), both scale with model size (S1 uses 1B-8B models, S5 uses 4B), and both leave the architecture alone. Not in the repo already (see section 3).

## 3. Grid symmetries valid for mazes, and the repo check

- Valid (suggested, from the definition of a maze): the 8 rotations/reflections (dihedral group D4) of a 9x9 grid keep a maze a maze if start, goal, walls and the answer path are all transformed together. Transposing or flipping the grid does not change connectivity or shortest paths. Colour/token permutation is NOT a valid free augmentation unless the reader is built symbol-agnostic (wall vs path have fixed meaning). Reordering the k examples is trivially valid but only matters for nets that see several at once.
- Caveat to check before building: if the net reads a fixed answer format with direction words or coordinates (not just cells), those must be transformed with the grid. From the brief the read head gives per-cell answers, so this looks fine (suggested; check the maze generator).
- Repo check (shown): `Grep` for augment|rot90|flip|transpose|permut across scripts/claude_fewex*.py matched only the attention reshape in scripts/claude_fewex_net.py lines 40 and 47. So neither claude_fewex_eq_bench.py nor claude_fewex_bench.py augments the adaptation set. I did not open the maze generator or the practice generators (untested whether practice on sums/grids used any D4 flips).
- Overlap with queued work (BRIEF): R2 "soft-D4 loop" is queued. As I read it, that is a change to the loop's architecture or training. Here the difference is: (i) my T1 changes only the k adaptation examples (data side, at adaptation time, same weights and same 2,048 updates), and (ii) my T2 changes only read-out (no training). If R2 already includes D4-augmented adaptation or D4 voting, drop the overlapping test and tell Ben; I have not seen R2's design.

## 4. Mapping to Premonition's open problems

| open problem | what this angle says | label |
|---|---|---|
| few-example ruler (F_few, k 1-64) | augmentation multiplies the effective k by up to 8 for free; TTT shows this is where the gain is largest at small k | suggested |
| carry-over to unpractised kinds | TTT/ARC do not test this (they adapt on the new task); GPICL/Raventos say diversity is the lever; queued A and H1 cover it | shown (others) / suggested |
| improve-with-use | no source shows accumulation; TTT and CompressARC discard per-task changes; the sleep work (KS, T1-T3) is the only accumulation route | suggested |
| scale | S1 and S5 show TTT plus augmentation growing with model size (1B to 8B) and beating bigger models; TRM shows it also works at 7M | shown (authors) |
| fresh loop row | expect it to rise with augmentation too; keep it as a control | suggested |

## 5. Tests (one change each; fair ruler)

Common set-up: 9x9 mazes; adapt for 2,048 updates exactly as in claude_fewex_eq_bench.py; report F_eq and F_few for practised loop, plain net, fresh loop, seeds 0 and 1 at least (use 3 if time allows, noise is 3.3-4.2 F_eq sd, artifacts/claude-dir-lr-20260928/NOISE.md); bar F_eq +8.0, F_few +10.5. Compare each arm against ITS OWN unaugmented row so the loop's gain cannot be a plain-net artefact.

**T1. D4 augmentation of the adaptation set (data side, no new updates).**
- Change: on each of the 2,048 updates, draw one of the k mazes and apply one of the 8 D4 transforms (chosen at random) to the whole maze plus its target. Nothing else differs: same lr, batch, steps, same test mazes, same read-out.
- Pass marks (fixed now): practised-loop F_few (mean over k = 1..64) up by at least +10.5 vs the same seed's unaugmented row in BOTH seeds, AND F_eq at k >= 256 not lower by more than 3.3 (one noise sd) in either seed. Plain-net row measured the same way; report both. A pass for the loop counts as "loop-specific" only if the loop gain exceeds the plain-net gain by 5 or more; otherwise it is a general ruler gain.
- Proved wrong if: F_few gains are under 4 in either seed at k <= 64 (inside noise), or the gain appears only at k >= 1,024 (then augmentation is just more data and not a few-example tool).
- Cost: no extra training steps; the transform is a few array operations. Mac CPU: same as the existing adaptation runs (about one adaptation run per arm, seed, and rung; with 5-8 rungs, 3 arms, 2 seeds that is 30-50 short runs, same cost as the existing ruler). RTX 5070 Ti: minutes per run.

**T2. D4 voting at read-out (no training).**
- Change: on the ALREADY adapted checkpoints from the current ruler (no retraining), run the maze through the loop in all 8 D4 views, map each answer back to the original frame, and take the plurality answer over whole-maze exact matches (fall back to the identity view on ties). Stop rule, cap 48, unchanged per view.
- Pass marks (fixed now): F_eq at least +8.0 over the same checkpoints read out with a single view, in BOTH seeds, for the practised loop, at the rungs where the single-view score is above the chance floor. Also report the plain-net row the same way.
- Proved wrong if: F_eq gain is under 3.3 in either seed, or the voted answer is worse than the identity view (then errors are correlated across views, or the loop is not equivariant enough for views to disagree usefully, which would also count against R2).
- Cost: evaluation only, 8x eval time (300 mazes x up to 48 rounds x 8 views). GPU: minutes. Mac CPU: about 8x the existing eval cost per checkpoint, perhaps an hour per seed (suggested, unmeasured).
- Reading the pair: T2 uses T1's checkpoints only as an optional add-on. Run T2 first on existing checkpoints since it costs nothing to train; run T1 next; then T1+T2 together is a third row, not a test.

**T3 (diagnostic, not a race entry): is the loop equivariant already?** Take one practised-loop checkpoint and compare its answers on a maze with its answers on the 7 transformed copies (mapped back). Report the fraction of mazes where all 8 agree. Pass mark: none, this only sets expectations. If agreement is under 50% while accuracy on the identity view is above 60%, T2 has a lot of room; if agreement is near 100%, skip T1/T2 (nothing to gain). Cost: seconds on CPU.

## 6. Risks and things not checked

- I did not read full papers. S1's numbers are from a fetch summary of figures, percentages approximate; S2 and S4 details are from search summaries; TRM's augmentation setup is from memory.
- All the ARC evidence is on 1B+ language models or on grid puzzles with colour tokens. Whether D4 augmentation helps a 1.6M-weight looped net on mazes is untested.
- Augmenting only the adaptation set does not fix the practice-stage priors; if practice had no D4 views, the practised loop may be non-equivariant, and T1 could help the fresh loop and plain net as much as the practised loop.
- Voting cannot fix the never-firing stop rule (300 of 300 hit the 48 cap): every view runs to the cap. Stop-rule work is queued elsewhere (H12, SL, Pond).
- Improve-with-use has no support in this literature; do not take TTT wins as evidence for it.
