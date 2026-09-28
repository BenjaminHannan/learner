# Item F: examples in view (research and design only)

Written 2026-09-28 21:2x UTC by Director helper HF. **Nothing was run, no script was written, no model was scored.** Design waits on item A (practice over about 10 kinds, `handoff/director-roadmap.md`) and on the H1 held-out kinds (`artifacts/claude-dir-h1-heldout-20260928/`). Claims are labelled **shown** (read in a repo file or a fetched abstract), **suggested** (my reasoning) or **untested**. Paper facts below come from arXiv abstract pages only, through a fetch tool that summarises; I did not read full papers.

## 1. The question in plain words
Today the ruler teaches a new kind by changing the weights (2,048 updates on k examples, `RESULTS-EQ.md`). A person glancing at two worked examples changes nothing in their brain's wiring; the examples sit in working memory while they solve. Test: put s solved examples of the new kind in the net's input next to the question, change no weights, and see if it answers better.

## 2. What the repo already shows (shown)
- Weight updates barely work at small k: practised loop 0 to 1 of 300 at k=1 and 0 of 300 at k=4 in both seeds; first reaches 150 of 300 at k=256 (seed 0) or 64 (seed 1) (`RESULTS-EQ.md`, main table). So examples in view has a very low bar at s of 1 to 8 and a high prize: reaching 150 of 300 with 8 examples would be 8 to 32 times fewer examples than weight updates need.
- The net's input is already a stack of grids with a `slot` mask marking where it must write, loss only on slot cells (`scripts/claude_rsn358a_envs.py:46`, `claude_fewex_net.py:153-158`); the Latin-grid practice already appends extra rows below the puzzle (`claude_fewex_data.py:21-26`). So a solved example is the same item with its answer written into the tokens and its slot set to 0. (suggested that maze items work the same way; I did not open the maze builder.)
- Attention position bias is clipped at plus or minus 4 rows/columns and four of eight heads see only a 3-column strip (`claude_fewex_net.py:26,33-45`). Far-apart example blocks are therefore told apart by content, not by position. (suggested risk)
- H9 already ruled out a task register or hypernetwork for now because two kinds are too few (`artifacts/claude-dir-h9-novelty-20260928/REPORT.md` section 8). Examples in view is the same need, so it waits on A.

## 3. Prior work (all abstract-level; F = fetched abstract)
| Work | What it says | Use here |
|---|---|---|
| Garg, Tsipras, Liang, Valiant, arXiv 2208.01066 (F) | A transformer trained from scratch on prompts of (x, f(x)) pairs learns function classes in context, including under a shift between training and prompt data | Precedent that the format can be learned from scratch |
| Chan et al., arXiv 2205.05055 (F) | In-context learning appears when training data is bursty (same items cluster), has many rare classes, and meanings vary; only in transformers, not recurrent nets | Episodes must be bursty: support and query from one instance family. Our loop is transformer blocks, so the recurrence warning is not obviously a problem (suggested) |
| Raventós et al., arXiv 2306.15063 (F) | Below a task-diversity threshold the net acts as a Bayesian guess over training tasks; above it, it learns new tasks from a few prompt examples | Why item A comes first. Numbers are for regression and do not transfer |
| Kirsch et al., arXiv 2212.04458 (F) | Meta-trained nets switch between memorising, generalising and failing to train depending on task count, size and optimisation; the bottleneck is the state that can be read when predicting; biasing the training distribution helps | Examples in view enlarge the readable state; expect a memorise-vs-generalise switch as kinds grow |
| Yadlowsky et al., arXiv 2311.00871 (F) | Tasks outside the pretraining mix cause failures and degraded generalisation | A truly unseen kind is the hard case. A null result is likely at 2 kinds (suggested) |
| MetaICL, Min et al., arXiv 2110.15943 (F) | Meta-training on many tasks makes few-shot prompts work; task diversity is essential; helps most under domain shift | Same lesson at language scale |
| Lake and Baroni, Nature 623:115 (2023) (S, search snippet only) | Training on a stream of few-shot episodes (study examples plus query) gives human-like systematic generalisation | Closest design precedent for the episode format |
| Yang et al., arXiv 2311.12424 (F) | Looped transformers match standard ones at learning in-context algorithms with under 10% of the weights (data-fitting tasks) | Supports using the loop; regression only |
| von Oswald et al. 2212.07677; Akyürek et al. 2211.15661 (F) | Trained transformers implement gradient-descent-like and ridge-regression-like updates in the forward pass (linear settings) | Suggests loop rounds could act as internal update steps; untested for grids |
| Min et al., arXiv 2202.12837 (F) | In LLMs, randomly wrong labels in the examples barely hurt; format, label space and input distribution matter | Why a shuffled-answer control is required: a gain could come from the format alone |
| Hendel et al., arXiv 2310.15916 (F) | Examples get compressed into a single task vector | A later probe, not part of this test |
| TTT for few-shot, arXiv 2411.07279; induction vs transduction, arXiv 2411.02272 (F) | On ARC, weight updates at test time help; direct prediction from examples and program inference solve different problems and combine well | Justifies a report-only arm that does both (view, then update) |

Brain (simplified textbook science, not checked here): working memory holds only a few items and the hippocampus stores episodes quickly. Where silicon does better (suggested): hold examples exactly and in any number the memory allows, and later fetch the most relevant solved examples from Ben's notebook instead of the last few. Retrieval is out of scope for this test.

## 4. The design: one sealed single change
**The one change:** practice is rewritten in an *episode* format, and at test the new kind is given as an episode with s solved examples and no weight update. Everything else stays: same two seeds, same source nets' architecture (loop, and plain as the rival), same total number of practice queries and the same practised kinds as item A, same held-out kinds and panels as H1/A (never opened by practice), same F_eq-style scoring in counts of 300.

**Episode format (general, never shaped to a kind).** A practice item becomes: m solved examples of one kind, then the query. Each solved example is a puzzle grid with its answer written in and slot = 0, stacked vertically as the Latin-grid legend rows are today. All examples in an episode come from one kind and one size and are distinct layouts. Loss only on the query's slot cells (as now). No kind id anywhere. m is drawn 0 to 8 per episode so the net also works with none. Kind mix per episode is the A kinds, so that kind changes every episode (the net must read the examples to know what to do).

**Test.** Held-out kind X (from H1 and A, at least 2 kinds). Support of s = 1, 2, 4, 8 solved layouts drawn by code from the same generator, disjoint from panel layouts, from a fixed per-seed pool. Score 300 graded panel items per s, each item with a fresh random support. Report also order of support (permuted twice, report only).

**Arms** (2 seeds each, eight per kind):
- V: episodic practice, examples in view, no updates (the claim).
- V0: same net, s = 0 (format with no examples).
- VS: same net, s examples whose *answers are shuffled across the examples* (puzzle i shown with the answer of puzzle j). Format present, information wrong.
- Plain-V: the plain net (8 blocks, width 128) with the same episodic practice, same test. The rival.
- U (baseline, existing harness): A-practised loop with weight updates at k = s, using the H1/A ruler; k = 1 and 4 already exist in the eight-rung ladder; k = 2 and 8 are two extra rungs run by the same harness. Not retrained.
- Report-only: C3 = A-practised loop *without* episodic training, examples shown at test (format the net never saw); VU = V then the harness's 2,048 updates on the same k examples (does looking first help updating); and, if cheap, V trained on only the two old kinds to check the diversity prediction (suggested: no gain).

**Guards before any test on X (fail: report and stop).** G1: V source at zero and at m = 4 examples scores at least 190 of 200 on 4-digit sums and 190 of 200 on 5x5 grids (same guard panel as M2 of H9 section 6). G2: nonzero fp32 gradient in every 2-D matrix, as V2. G3: no test-panel or test-support layout appears in practice (hash check, 0 of pool). G4: stored weights within 2% of the loop's 1,645,726 (the format adds no weights: suggested; needs checking).

**Cost (suggested, untested).** Episodes are much longer: 9x9 with s = 8 is 17 grids, 1,377 cells, against 81 today, so attention costs about 290 times more per round and the CPU ruler (169 minutes per run) will not do. This needs a GPU job (vast, cap $4). Practice length in queries is kept equal to the sources', so total supervised signal is equal; compute is not. I have not estimated the wall time. If it is too large, cap s at 4 and m at 4.

## 5. Risks (all suggested)
1. Item A may not reach enough kinds; the whole test is then INCONCLUSIVE, not failed (see PASSMARKS validity).
2. The position bias cannot say "the second example"; the net may need content matching only, which is fine for mazes-like stacks but untested.
3. The net may learn to ignore examples and rely on what it memorised (Kirsch, Raventós). VS and V0 exist to catch this.
4. Held-out kinds that share structure with practised kinds (H1 rank/graph vs sums/grids) may make V look good without reading examples; V0 handles that, and it is why V is judged against V0 and not only against U.
5. Equal queries is not equal compute; a reader may say V got more practice. Stated openly.
