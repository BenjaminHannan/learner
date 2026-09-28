# Standing research 01: learning a new kind from few examples, and carry-over

Written 2026-09-28 (standing research helper, Sonnet). Nothing here was run. Link tags: **A** = abstract page fetched and read on 09-28; **T** = only the title page loaded (seen, not read); **M** = from memory, not opened. Labels: shown (in a repo file, cited) / suggested (my reasoning) / untested.

## What the ruler does today (shown)
- Adapting to a new kind = full fine-tuning of every weight on k mazes, 2,048 updates, AdamW lr 1e-3 for the loop (`scripts/claude_fewex_bench.py:170-173`, `claude_fewex_eq_bench.py:245`). Practice was on two kinds only (H9 REPORT section 1, finding 2).
- The curves are jumpy: fresh loop seed 1 scores 128 of 300 at k=4,096 but 0 of 300 at k=1,024 and 18 of 300 at k=16,384 (`artifacts/claude-fewex-20260927/RESULTS-EQ.md`, main table). Suggested: some of that is optimiser instability from one fixed lr on all weights, not a lack of skill. Untested.
- Practised loop 51.00 / 51.29 vs plain 33.79 / 33.58 F_eq: carry-over from sums and grids to mazes is already shown on one kind.

## Sources
| source | what it says | tag |
|---|---|---|
| Rapid Learning or Feature Reuse? (ANIL), https://arxiv.org/abs/1909.09157 | MAML works mainly because the starting weights already hold good features. Adapting only the head matches MAML on few-shot image tasks. | A |
| Fine-Tuning can Distort Pretrained Features (LP-FT), https://arxiv.org/abs/2202.10054 | Fine-tuning everything can lose to fitting only the last layer on a far-away new task, because a random head drags the features. Fit the head first, then unfreeze (LP-FT) fixes it in their theory and 10 datasets. | A |
| On First-Order Meta-Learning (Reptile), https://arxiv.org/abs/1803.02999 | Sample a task, train on it, move the start point toward the trained weights. Needs only first derivatives. | A |
| General-Purpose ICL by Meta-Learning Transformers, https://arxiv.org/abs/2212.04458 | A plain transformer can be meta-trained to learn from examples, but there are sharp changes between "generalises", "memorises" and "fails to meta-train" as model size and number of tasks change. | A |
| Pretraining task diversity, https://arxiv.org/abs/2306.15063 | Below a threshold number of practice tasks the net only handles the tasks it practised. | A (H9 read it; I did not re-read) |
| Test-Time Training for Few-Shot, https://arxiv.org/abs/2411.07279 | Updating weights at test time on the given examples gave up to 6x accuracy on ARC (53.0% with an 8B model). | A |
| ARC Prize 2024 Technical Report, https://arxiv.org/abs/2412.04604 | Overview of what won: test-time fine-tuning plus augmentation. | T |
| Few-Shot PEFT beats ICL, https://arxiv.org/abs/2205.05638 | Adapting a tiny part of the weights beat putting examples in the prompt. | T |
| Meta-Dataset, https://arxiv.org/abs/1903.03096 | Benchmark that tests few-example learning across many separate kinds, the sort of ruler we lack. | T |
| Compositional generalisation through meta seq2seq, https://arxiv.org/abs/1906.05381 | Practising on many small "episodes" of made-up rules lets a net apply new rules from a few examples. | T |
| Nature 2023 "Human-like systematic generalization through a meta-learning neural network", https://www.nature.com/articles/s41586-023-06668-3 | Same idea at scale (page loads, I did not read it). | T |
| Tse et al. 2007, schemas and fast learning (doi 10.1126/science.1135935) | Rats with a schema learn new paired associates in one trial and it is stored fast. Site refused my fetch. | M |
| Harlow 1949, learning sets | Monkeys given many discrimination problems get to one-trial learning. Not opened. | M |
| McClelland, McNaughton, O'Reilly 1995, complementary learning systems | Fast hippocampus, slow cortex. Publisher refused my fetch. | M |

## Brain angle (suggested, simplified textbook science, not checked here)
- **Learning sets (Harlow):** the skill of learning quickly is itself learned by practising on many related problems. It is not a bigger dose of one problem. Our practice on two kinds gives little of this.
- **Schemas plus fast writing (Tse; CLS):** once the slow system holds the shared structure, the new case only needs a small, fast change. Here that reads as: keep the reasoning blocks nearly fixed and change a small, fast part.
- **Where silicon can beat biology:** clone the net, try several adapt recipes on the same k examples, keep the best on a held-back few of the k, throw the rest away. A brain cannot rewind.

## Leads, ranked by my guess of chance to reach F_eq +10 over the loop in both seeds (guesses, not measured)
Bars come from H9/H10 marks, not mine. Each is a single change.

**Lead 0 (diagnostic first, not a race entry): is the jumpiness the learning rate?** Re-adapt the practised loop, seed 1, at rungs 1,024 and 16,384 with lr in {3e-4, 1e-3, 3e-3}, nothing else changed. Result that would prove me wrong: scores stay as erratic at every lr (then instability is not lr). Why first: every other lead is judged against noise of about 10 F_eq (H9 finding 4), so knowing the noise source tells the Director what a "gain" means. Cost: 6 short CPU adaptations. Untested.

**Lead 1 (my top pick, chance guess 20%): staged unfreeze (LP-FT / ANIL) at adaptation.** Change only the adapt step: for the first 25% of the 2,048 updates train only the output head and the stop head, then unfreeze everything. Fresh nets and the plain net get the identical rule (fair comparator). No retraining of source nets, no new practice. Why it may help (suggested): the maze head is new; a random head early on damages shared features (LP-FT), which fits the practised nets already being better than fresh ones. Would prove it wrong: practised-loop F_eq not above its unstaged F_eq by more than the noise in both seeds, or gains at k up to 64 but losses at 256 and up. Sits at the low rungs where the ruler earns almost nothing (H9: score lives at 64 and up), which is why I put the chance at 20% and not higher. Untested.

**Lead 2 (chance guess 15%, higher payoff if it works): practise the practising (Reptile-style).** Change only how the 12,000 practice steps are ordered: instead of mixed batches from two kinds, run short inner episodes (n updates on one kind, small n), then move the start weights part-way toward the result, over as many kinds as the practice-breadth job (A, 10 kinds, `handoff/director-board.md` 21:33 entry) provides. Same total updates, same data. Evidence: Reptile, GPICL, Harlow. Needs many kinds; with only two the task-diversity finding says it will not work, so run it only after A's kinds exist. Would prove it wrong: no F_eq gain over ordinary mixed practice on the same 10 kinds in either seed. Also needs a plain-net row: a plain net given the same Reptile schedule, so the loop's gain is not just the schedule. Untested.

**Lead 3 (chance guess 10%): leave-one-out test-time loss.** Adapt with a loss that predicts each of the k examples from the others (as in the TTT paper) instead of plain fit on all k. This is a larger change (needs the net to take examples as input), so it is last. Untested.

## Marks reminders for whoever races these (H8 checklist)
Compare against the higher of loop-with-episodes and baseline loop; keep a plain-net row; F_few (k = 1 to 64) as its own row; bars above the noise of about 10 F_eq.

## Not checked / risks
- I read abstracts only, not full papers. ANIL and LP-FT were run on images, not on mazes; nothing says they transfer here.
- Lead 1's guess depends on the reading that instability is partly an lr/feature-damage effect; Lead 0 tests that.
- I did not search the literature on few-example learning of algorithmic (non-image) tasks in tiny recurrent nets beyond the rows above.
