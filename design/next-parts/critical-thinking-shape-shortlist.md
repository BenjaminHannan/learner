# More model-shape ideas: ranked shortlist

Written 2026-10-03 for Ben's ask (13:29 UTC): "Look up online and come up with some more ideas for model shape." Design only. Nothing was trained or run, and no GPU was used.

This ranks the ideas from three literature searches (raw notes in `critical-thinking-notes/shape-looped.md`, `shape-memory.md`, `shape-world.md`) plus one idea from our own data. Each idea's main paper was re-opened on arXiv for this ranking (abstract pages only). Numbers that come only from the notes' summaries of full papers are marked "notes" and must be re-checked in the PDF before a pass mark rests on them.

Labels: **shown** = measured (in the paper, or in our repo/data). **Suggested** = reasoning. **Untested** = never run on our model.

Rulers stay separate: the puzzle ruler (F_eq on 9×9 mazes), the assistant panel (matched ADD/SUB pairs), and the village model (not used here). Card experiments are not used.

## 1. Summary for Ben

- **New first pick (16:30 UTC):** let the answer copy the calculator's result directly. A test with never-repeating data showed the current exit only says answers it was trained on, so better data alone doesn't help.
- **Best bets for "beat bigger models at our size":** extra parallel copies of the thinking state (*state lanes*), and a tiny "look at your neighbours" layer (*Canon layers*). Both are cheap and both have published wins against bigger plain models.
- **Best bets for the wrong-operation errors (38 of 128):** let the model think *before* it calls the calculator (today every call fires before any thinking round), and train it to score every operation instead of copying one.
- **Free to try today, on the CPU:** make each thinking round take a smaller step. It needs no training on saved puzzle models.
- **For learning from a few examples (later):** a head that pairs each example's question with its answer, and a short search for the "task code" at test time.
- **Parked:** a swappable fact table (for stage two, when facts arrive), a world model for Minecraft, and a fast reflex for real-time play.

## 2. How they were ranked

Each idea scored on five questions: does it attack a failure we have **shown**; is there a published result at small size; how many weights does it add (the §7 test counts every one); can it be tested as **one change** with marks fixed first; and does it keep working as size grows. Ideas that need a ruling from Ben, or that only matter once facts or Minecraft arrive, rank lower for now, not out.

## 3. The shortlist

| Rank | Idea | Aims at | Added weights | First test | Ruler | Label |
|---|---|---|---|---|---|---|
| 0 | Pointer exit (copy the tool result) | Answers stuck to the training set | ~260 + 1:1 map | **Done on vast: unseen 0-4% to 84-90%** | Assistant format | shown (reimplementation) |
| 1 | Think before calling | 38 wrong operations; all calls fire at loop 0 | 0 | Running on vast (on top of rank 0) | Assistant panel | fact shown, fix untested |
| 2 | State lanes (Hyperloop) | Beat a plain model 2× our size | ~12k (0.14%) | Practice-side, 3 seeds | Puzzle, then §7 ladder | paper shown, untested for us |
| 3 | Damped round update | Answers wander after round 16; the stop never fires | 0 to 256 | **Free, CPU, saved nets** | Puzzle | paper shown, untested for us |
| 4 | Canon layers | Weak word order; bag-like notebook | ~3k (0.03%) | Generated pointer-chasing | Generated, then assistant | paper shown, untested for us |
| 5 | Score every operation | Wrong operation choice | ~4k | After rank 1 | Assistant panel | paper shown (notes), untested |
| 6 | Pair-binding head | Learn from a few examples | 0 to 65k | After C5 | Few-shot episodes | paper shown, untested |
| 7 | Task-code search (LPN) | Learn from a few examples, forget nothing | 0 stored | After C5 | Few-shot episodes | paper shown, untested |
| 8 | Unshared entry block | The reader sees no context before round 1 | ~0.79M (+9%) | Practice-side, 3 seeds | Puzzle | suggested |

### Rank 1. Think before calling (from our own data)

- **What:** the calculator port may only fire after the core has run at least 2 rounds. Today the call is read before any round (see below), so looping cannot help pick the operation.
- **Evidence:** **shown** in code and outputs. The pipeline scores the operation from `h+e` at the top of each loop, and at loop 0 that is the state straight from `begin_latent`, before any `advance_latent` (`pipeline_code/calculator_runtime_depth_compare.py:117-124, 148` on branch `claude/critical-thinking-data-128-outputs`). In the saved outputs, 127 of 128 rows made exactly one call, at loop 0, and one row made none (`critical-thinking-notes/f1_stdout.txt`). 38 of 128 picked the wrong operation. **Suggested:** a choice made before thinking can't benefit from thinking. Ouro and TRM-style results only show gains from rounds that actually run before the output is read.
- **Our core:** zero new weights. One rule in the call schedule: force `NONE` at loops 0 and 1 so the first call is read after 2 advances. The result still re-enters through the same reserved value and status slots before the next round.
- **Test (one change, after the English pilot reports, on its recipe):** call after round 2 vs call at round 0. 2 seeds, fresh sealed panel of matched pairs. **Pass:** wrong-operation count falls by at least a third on both seeds. **Wrong:** within ±2 of today on both seeds. That would mean operation errors are not a "no time to think" problem.
- **Risk:** fewer rounds remain after the call for using the result, so the 4-round budget may need to be 6. Keep the total rounds fixed in the first test so it stays one change.

### Rank 2. State lanes (loop-level hyper-connections)

- **What:** each position carries 4 parallel copies of its thinking state. Each round reads a learned mix of them, runs the shared blocks once, and writes back to each copy with its own gain.
- **Source:** Zeitoun, Torroba-Hennigen, Kim, *Hyperloop Transformers*, arXiv 2604.21254 (abstract re-opened). **Shown (abstract):** performs well against depth-matched plain Transformers "despite using approximately 50% fewer parameters". **Shown (notes, check PDF):** at 136M, 580M and 991M it beat plain models with ~1.7-2× its weights on perplexity; looping without lanes won at only 1 of 3 sizes; mixing once per loop beat mixing every layer.
- **Our core:** the state grows from [B,N,256] to [B,N,4,256]. About 12k weights. Attention and MoE costs don't change. It grows *state*, not weights, which our plan already prefers.
- **Test:** puzzle ruler, practice-side, 3 seeds. **Pass:** F_eq ≥ +8 over baseline (each seed ≥ +4), and round 48 ≥ round 16. **Wrong:** mean gain < +4. The real test is §7's ladder, because "beats 2× plain" is §7's own pass mark 1.
- **Risk:** lanes must reset to zero for every puzzle, so nothing carries across items (the same proof the old "dual-timescale" idea needed).

### Rank 3. Damped round update

- **What:** each round moves the state only part of the way: `h ← h + α·(f(h) − h)`, with α = 0.25 to start.
- **Sources:** "Right Direction, Wrong Step", arXiv 2609.16665 (abstract re-opened). **Shown:** "a fixed quarter step produces positive gains … for 72.2–83.2% of selected failures across four settings." Parcae, Prairie et al., arXiv 2604.12946 (abstract re-opened). **Shown:** keeping the loop's spectral norm small stabilises training, up to 6.3% lower perplexity than earlier looped models, and about 87.5% of the quality of a Transformer twice its size at equal parameters.
- **Our core:** `step()` returns `LN(blocks(h+e))` today (`claude_fewex_net.py:77-81`, shown). The change returns a partial step toward that. Zero weights for fixed α, 256 for a learned per-channel α.
- **Test (free, CPU, no training):** saved practised puzzle checkpoints. Rounds 1-16 as now, then 17-48 with α = 0.25. Held-out mazes, both seeds. **Pass (all three):** un-solving (right at 16, wrong at 48) at least halves; F_eq at 48 ≥ at 16; the stop fires before the cap on ≥ 90 of 300 mazes (today 0 of 300, per notes). **Wrong:** cap hit on ≥ 290/300 and un-solving within ±20% of today, both seeds.
- **Risk:** our per-round LayerNorm already stops blow-ups, so only the settling effect can transfer (suggested). The assistant panel uses a fixed 4 rounds (v5), so this matters for the puzzle path and for C4, not for today's panel.

### Rank 4. Canon layers

- **What:** before attention and before the MLP, each token adds a weighted mix of its nearest neighbours (kernel 3, no activation).
- **Source:** Allen-Zhu, *Physics of Language Models Part 4.1: Canon Layers*, arXiv 2512.17351 (abstract re-opened). **Shown (abstract):** about 2× reasoning depth; a model with no position code plus Canon matches one with RoPE; validated on synthetic tasks and at 1.3B / 100B tokens. **Shown (notes):** under 0.5% extra weights. Our frozen LM (LFM2.5) already uses short convolutions in 10 of its 16 layers.
- **Our core:** symmetric kernel 3, zero-initialised, only inside each 1-D segment, never on registers. About 3k weights. Placed by the §6 coordinates, never by modality id.
- **Test:** generated pointer-chasing in the notebook ("x7 → q2." lines, nonce names), train 1-4 hops, test 1-8, against the row that already has §6 order coordinates. **Pass:** +15 points at 4 hops and +10 at 8 hops, both seeds. **Wrong:** under +3 at 4 hops, both seeds.
- **Risk:** a 2-D version on mazes looks like the maze race's banned "neighbour message passing", so keep it off the puzzle path unless the Director rules otherwise.

### Rank 5. Score every operation (action-value plan head)

- **What:** instead of copying the one right operation, the plan head predicts for each operation whether it leads to the right answer. Labels are free: run every operation through the calculator when generating data.
- **Source:** Ruoss et al., *Amortized Planning with Large-Scale Transformers* (chess "without search"), arXiv 2402.04494 (abstract re-opened; it confirms action-value vs state-value vs copying ablations). **Shown (notes, check PDF):** at 9M weights, puzzle accuracy 83.3% (action-value), 77.5% (state-value), 65.7% (copying).
- **Our core:** the deferred plan head with a new target. About 4k weights.
- **Test (after rank 1):** target switched from copying to a per-operation yes/no score, argmax, no branching. **Pass:** at least a quarter fewer wrong operations on a fresh sealed panel, both seeds. **Wrong:** within ±2. If it passes, a later row tries the top 2 operations through the real tool and keeps the higher-scored branch.
- **Risk:** needs a tool whose options can be listed. The calculator can be; web search can't.

### Rank 6. Pair-binding head for examples

- **What:** one attention head matches the question against each example's *input* and reads that example's *output*.
- **Source:** Zhang & Bottou, *Memory Mosaics at scale*, arXiv 2507.03285 (abstract re-opened). **Shown:** at 1T training tokens it beats a transformer trained on 8T tokens at carrying out new tasks at inference time, with parity on stored knowledge.
- **Our core:** uses the §6 example roles. Repurpose 1 of 8 heads (0 weights) or add one (~65k).
- **Test:** one change on top of C5. **Pass:** k=0 → k=8 gain at least C5's +10 points, rising with k, shuffled pairs within 5 of k=0, both seeds. **Wrong:** ≤ +3 over C5.
- **Risk:** needs C5 to pass first.

### Rank 7. Task-code search (latent program network)

- **What:** after reading the examples, the registers hold a "task code". At test, ~10 gradient steps adjust only that code to fit the examples. Weights stay frozen, so nothing is forgotten.
- **Source:** Macfarlane & Bonnet, *Searching Latent Program Spaces*, arXiv 2411.08706 (abstract re-opened). **Shown:** on ARC-AGI, out-of-distribution performance doubles when test-time search is on. **Contrary (notes):** tuning only TRM's task embeddings at test scored near zero; LPN differs by training *with* the inner step.
- **Test:** after C5; 1 inner step in training, 10 at test. **Pass:** +8 over C5 at k=8, both seeds. **Wrong:** under +3.
- **Risk:** test-time gradient steps could be read as "settling". It optimises fit to the user's examples, never the reasoning state. Needs Ben's ruling.

### Rank 8. Unshared entry block

- **What:** one ordinary block runs once on the inputs before the shared blocks loop.
- **Sources (notes):** Mixture-of-Recursions, arXiv 2507.10524 ("middle-cycle" sharing had the lowest loss of 4 schemes); Huginn, Parcae and Hyperloop all keep unshared ends. **Suggested.**
- **Test:** puzzle ruler, 3 arms (baseline / entry block / same block as a third shared block). **Pass:** entry ≥ +8 over baseline and ≥ +4 over the third-block arm. **Wrong:** entry within +2 of the third-block arm (the gain is just weights).
- **Risk:** +9% weights, which §7 counts against us.

## 4. Parked for later stages

| Idea | Why later | Source |
|---|---|---|
| Swappable fact table in the text reader | Facts come in stage two. A removable table may count as "lookup"; Ben decides. | Engram, arXiv 2601.07372 |
| Imagine the tool result (latent world model) | The Minecraft world model. Needs a ruling: close to the predictive-coding ban. | EfficientZero 2111.00210, TD-MPC2 2310.16828 |
| "What changed?" head (inverse dynamics) | Later labels Minecraft video with actions. | VPT 2206.11795 |
| Slow core plus fast reflex, with a THINK action | Real-time play. Stage one only needs registers readable after any round. | Helix (blog), arXiv 2407.15421 |
| Slot workspace | Biggest change; matters for long inputs (frames plus guides). | arXiv 2406.12272 |
| Memorisation sinks | C3's never-repeating data removes the repetition it fixes. Useful later for guides and gameplay. | arXiv 2507.09937 |
| Short conv inside experts (URM) | Overlaps Canon; half our heads already see ±1 neighbours. | arXiv 2512.14693 (ARC-AGI-1 53.8% shown) |
| Equal-weight rounds, separate stop loss | Cheap, but must follow C4 to stay one change. | Ouro 2510.25741 |

## 5. Looked at, not proposed

- **HRM two-level loops:** the ARC Prize re-run credits most of the gain to training-time refinement, which random-depth training already covers.
- **Per-token depth (MoR):** lost to the plain model at 135M; its gains are speed.
- **Coconut latent chain-of-thought:** needs written chains to start from; our loop is already latent.
- **Energy settling (EBT):** banned for the maze race.
- **TTT, Titans, ATLAS, Mamba-2, xLSTM:** the earlier note dropped them as "fast weights". Correction: per v5, the fast-weight ban covers only the maze race, and v5 lists an error-correcting fast-weight matrix as a lower-ranked fallback. The reason to skip them *now* is different: their wins show up at 16k+ tokens, and our inputs are ≤ 256 tokens. Revisit if long Minecraft episodes need memory beyond the notebook.

## 6. What I'd do first

**Update 16:30 UTC 10-03: the exit, not the data, looks like the bottleneck.** The F1 check on the saved outputs (shown) found every wrong answer was a training answer. A follow-up on vast.ai (PR #29, `reasoner_fresh/RESULTS.md`, a reimplementation of the recipe, not the PC pipeline) then trained on 48,000 never-repeating questions. Shown there: answers never seen in training scored 0.0% and 4.2% (vs 0.0% and 3.1% for a repeated pool), while the calculator call was right about 90% of the time and train fit was 100%. 375 of 377 wrong unseen answers were training answers. So never-repeating data alone does not fix it. The averaged 8-vector exit behaves like a lookup over the answers it was trained to say (suggested). Note the test also asks the exit to make the LM say a token it was never trained to produce. That is why rank 0 below now comes first.

### Rank 0 (added 16:30 UTC). Pointer exit: let the answer copy the tool result

- **What:** the output path gets a second route that reads the calculator's result slot directly (1:1, no pooling), plus a learned gate that picks "copy the result" or "say something else". This is the pointer-generator idea. It is not v5's rejected *forced* copying, because the gate is learned and can decline.
- **Sources:** See, Liu, Manning, *Get To The Point: Summarization with Pointer-Generator Networks*, arXiv 1704.04368 (2017). Vinyals, Fortunato, Jaitly, *Pointer Networks*, arXiv 1506.03134 (2015). Both are widely used and cited here from memory, so re-open them before a pass mark rests on them. **Shown in those papers:** copying handles words never seen as outputs, which a fixed output set cannot do.
- **Our core:** the value slot already holds the result's own LM token embedding (`_numeric_value` in `calculator_runtime_depth_compare.py`, shown). The talker adds one route that maps the result slot into the prefix 1:1, and one gate scalar. Roughly 260 weights for the gate, plus whatever the 1:1 map needs (one 256 → LM-width map if not shared with the existing 32 path).
- **Result (16:52 UTC, PR #29 `reasoner_fresh/RESULTS.md`, reimplementation, shown there):** the tested version fed the frozen LM's embedding of the result token in as a 9th prefix vector, with no gate. Unseen-answer accuracy rose from 0.0% / 4.2% to 89.6% / 84.4% (2 seeds). Final accuracy now equals the right-call rate exactly, and none of the wrong answers is a training answer (0 of 25). One mark was missed: seen answers fell 6.2 and 5.2 points against a 5-point limit, so it is "not falsified" rather than a full pass. Still open: the learned gate (untested), multi-step answers, and the PC pipeline.
- **What it moves:** every remaining error is now a wrong call, and the call is right only 60-69% of the time on new wording. So rank 1 (think before calling, now running on vast on top of the copy path) and rank 5 (score every operation) are next.
- **Risk:** a pure copy route would solve calculator questions without any reasoning. Keep the gate, and keep questions that need a step after the call (for example, using the result in a second call) in the eval, so the gate can't just always copy.


1. **Now, free:** the damped-round CPU test (rank 3) on saved puzzle checkpoints, if the execution owner can spare the files. It changes nothing in the pilot.
2. **After the English pilot reports:** rank 1 (think before calling), then rank 5. They go straight at the wrong-operation errors.
3. **Practice-side, puzzle ruler:** rank 2 (lanes), then rank 4 (Canon) on generated data. Lanes go into the §7 ladder if they pass.
4. **After C5:** ranks 6 and 7, for few-example learning.

One change per row, 2 seeds (3 for practice-side), marks sealed by hash before each run, as in the design doc §4.
