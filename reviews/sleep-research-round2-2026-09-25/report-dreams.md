# Sleep round 2: self-made practice, self-play, and proving that sleep helps

Labels used below: **SHOWN** means a paper reported this result. **SUGGESTED** means someone argued it, or I only saw the abstract. **UNTESTED** means it is my own idea. Everything here is a small card experiment on the 30M loop reasoner. The village model comes last and only gets a note. Cost assumes a 5090 at $0.49–0.99/h, so $4 buys about 4–8 GPU-hours. The repo's own figure is that rsn-296 cost about $2.09 for the whole run.

**The main point.** In Absolute Zero (arXiv 2505.03335) and R-Zero (2508.05004), a large language model writes its own problems. Absolute Zero proposes code tasks. R-Zero's "Challenger" is rewarded for aiming at about 50% solver success, and it gave Qwen3-4B-Base +6.49 on math (SHOWN). A 30M reasoner cannot write meaningful problems. For Premonition, the problem writer should be **the exact code generator, with its knobs picked by a small learned or bandit controller**. The reasoner only solves. This keeps what these papers get right, which is aiming at the edge of the reasoner's ability, without letting the model make up tasks (SUGGESTED).

## Idea 1. Choose tonight's practice by learning progress
**What.** Split the generator's settings into cells: question kind × number of steps (2–5) × notebook size. Each night, sample cells in proportion to recent learning progress: how fast the pass rate in that cell is changing, or how close it is to 50%. Cells that are already mastered, and cells that are still hopeless, get few samples.

**Evidence.**
- Teacher-student curriculum learning (Matiisen, 1707.00183) picked sub-tasks by the slope of the learning curve and beat fixed curricula on LSTM decimal addition (SHOWN).
- ALP-GMM (1910.07224) and Prioritized Level Replay (2010.03934) did the same for RL environments (SHOWN).
- Bae et al. (2504.03380) proved that GRPO's expected improvement is bounded below by the variance of per-task success. Keeping tasks at middle difficulty gave up to +12% in under half the steps (SHOWN).
- MAGELLAN (2502.07709) learned to predict its own learning progress across a large goal space (SHOWN).

**Fit.** This may explain the 0/30 on three-step chains. If every GRPO group on three-step items scores 0, there is no gradient at all. A learning-progress picker would mix in 3-step cells where some sub-case succeeds, for example short notebooks, and hold 2-step cells that are already perfect at a small replay share (UNTESTED as a diagnosis). The picker needs about 50 lines of code on top of claude_rsn296_gen.py.

**First experiment.** Both arms start from the same checkpoint, run the same GRPO steps, and use 3 seeds. The only difference is uniform cell sampling versus the learning-progress picker.
- **Pass:** blind 3-step accuracy is at least 8 points higher for the picker (n=300, mean over seeds, every seed the same sign), and 2-step is not worse by more than 2 points.
- **Proved wrong if:** the fraction of 3-step groups with a nonzero reward spread rises, but blind 3-step accuracy does not. That would mean the difficulty signal is not the bottleneck.

**How it could fool us.** Learning progress measured on practice can climb because the model found a shortcut in one cell. So the picker's numbers must never be used as evidence, and the picker gets no access to panel cells.

## Idea 2. A challenger that hunts for surface-pattern shortcuts
**What.** A second controller chooses the distractor settings from 296's `_style`: near-miss rows, extra facts about people on the chain, order of the time stamps, people reused as values. It is rewarded when the solver fails an item that the independent solver confirms is uniquely answerable. This is how the reasoner is forced to learn rules instead of surface patterns.

**Evidence.**
- PAIRED (2012.02096) trained an adversary rewarded by regret and got more robust transfer to held-out environments (SHOWN).
- Asymmetric self-play (Sukhbaatar, 1703.05407): "Alice" proposes tasks and "Bob" learns them (SHOWN in small environments).
- 2603.02218 argues that self-play improves only if each round adds learnable information (title and abstract only, SUGGESTED).

**Fit.** This speaks to open question 3 in the round-1 note: how to make lures that are hard for the model but still exactly checkable. The controller is a bandit over roughly 8 knobs, so it adds no GPU cost.

**First experiment.** A diagnostic probe with no training. Run the challenger against the 296 checkpoint.
- **Pass:** within 2k samples it finds at least one knob setting where the solver drops at least 30 points below its average, while the independent solver confirms every item.
- **Proved wrong if:** no setting drops accuracy by more than 10 points. In that case the model's weakness is chain length, not distractors, and this idea is dropped.

**How it could fool us.** The adversary will find generator bugs, such as ambiguous or unanswerable items, before it finds real weaknesses. Every item it picks is re-solved by 296's independent `solve()`, and its settings are capped at 20% of a night.

## Idea 3. Relabel failed chains with the question they actually answered
**What.** When the reasoner gets a 3-step question wrong, its answer is often correct for a different question over the same rows: it stopped one step early, or it followed the wrong relation. Code finds that question, relabels the episode, and uses it as a checked positive example. This gives learning signal even where the model is never right.

**Evidence.**
- Hindsight Experience Replay (1707.01495) relabels failed goals and solved sparse-reward robot tasks that plain RL could not (SHOWN).
- STaR's "rationalization" (2203.14465) trains on corrected versions of failed attempts (SHOWN on math and CommonsenseQA).

**Fit.** Stopping early is exactly where the "thinking stop" token goes wrong. A relabeled example teaches "you stopped at step 2", with the correct stop point written in (UNTESTED).

**First experiment.** Add relabeled examples as 20% of the 3-step practice, against a twin that gets the same number of extra fresh generator items.
- **Pass:** blind 3-step accuracy at least 6 points above the twin, and the rate of stopping one step early at least 30% lower.
- **Proved wrong if:** the early-stop rate falls but 3-step accuracy does not rise.

**How it could fool us.** This is a self-confirmation loop: the model learns that whatever it answered was the right question. Keep the cap, rebuild each relabeled question from the generator's own frame templates so the wording is correct, and require the independent solver to agree.

## Idea 4. A test that can show sleep causes the gain
Twins and placebos, fixed before any run (the design is UNTESTED):

| Arm | What changes |
|---|---|
| S: sleep | Full recipe (practice school plus Ideas 1–3, whichever passed) |
| W: awake | No update. The same checkpoint is scored again, which measures noise |
| G: generic | Same GPU-seconds and tokens, plain uniform 296 generator |
| P: placebo | S's pipeline, but rewards shuffled across the batch |

- **Why P exists.** Random or wrong rewards "improved" Qwen2.5 on math benchmarks (2506.10947, SHOWN). On a fresh synthetic benchmark built to be contamination-free, the gain disappeared: only correct rewards helped (2507.10532, SHOWN). If P comes close to S, the gain came from the extra updates, not from what sleep taught.
- **Held-out rule families.** Hash each item's structure: question kind + ordered relation path + number of steps. After the recipe is frozen, draw a salt from the hash of the freeze commit and use it to send 25% of structure types to the panel only. The generator refuses those types.
- **Fresh blind panel.** A separate script generates it after the freeze, with a fresh name and value vocabulary. It has 300 items per cell: 2, 3 and 5 steps, the held-out families, and missing-row questions where the right answer is "I don't know". Scoring is exact code.
- **Contamination checks, logged.**
  - Zero exact overlap of row sets between the practice logs and the panel.
  - Zero overlap of structure hashes for the held-out families.
  - Share of panel items that share a 13-gram with any practice item, reported next to the score.
- **Statistics.** 3 seeds per arm, 95% bootstrap intervals over items and seeds. Also report pass@k at k=1 and k=64. RLVR has been shown to narrow pass@k at large k compared with the base model (2504.13837, SHOWN). If S wins at k=1 and loses at k=64, it sharpened what the model could already do rather than adding a new skill. Gains that are not reported with their seed variance often do not hold up (2504.07086, SHOWN).
- **Budget.** Train each arm for about 12 minutes from a shared checkpoint, with 3 seeds each. W needs no training, so that is S, G and P: 9 runs ≈ 1.8 h, plus about 20 minutes of scoring. That is roughly $1.1–2.1, under $4 (UNTESTED estimate).
- **Pass (registered):**
  - S − G ≥ 8 points on blind 3-step, and S − P ≥ 8, with each 95% interval above 0.
  - The gain on held-out families is at least half the gain on the other families.
  - The false-answer rate on missing-row questions is not higher than W's.
  - Zero invented answers.
- **Proved wrong if:**
  - S − G < 3 points. Then it is only extra practice.
  - The held-out gain is below 25% of the in-family gain. Then it learned surface patterns.
  - P reaches 60% or more of S's gain.

## Village model (separate, later)
Run the same four arms on the whole agent only after Idea 4 passes on the card. Use new-fact panels written after the freeze, with W and G twins that also run "nights". Never score on the day's own questions, which are the practice.

## Plain summary for Ben
Right now the reasoner never gets a three-step question right. When practice is all failures, the RL training gets no signal at all. The fix is to let code choose tonight's practice: the kinds of question it is just starting to get right (Idea 1), the tricks that fool it (Idea 2), and its own mistakes, re-labelled as correct answers to the question it actually answered (Idea 3). To show that sleep caused a gain, compare against three twins: one that doesn't sleep, one that does the same amount of ordinary practice, and one that "sleeps" with scrambled grades. Test them all on new questions, including whole kinds of question that were never practised. Sleep only counts if it clearly beats all three.

Sources: [R-Zero](https://arxiv.org/abs/2508.05004v2), [Absolute Zero](https://arxiv.org/abs/2505.03335v2), [Reasoning or Memorization](https://arxiv.org/abs/2507.10532), [MAGELLAN](https://arxiv.org/abs/2502.07709), [Online Difficulty Filtering](https://arxiv.org/abs/2504.03380), [A Sober Look](https://arxiv.org/abs/2504.07086), [Self-Play Learnable Information Gain](https://arxiv.org/pdf/2603.02218)

Other arXiv IDs cited from memory, not re-checked this session: 1707.00183, 1910.07224, 2010.03934, 2012.02096, 1703.05407, 1707.01495, 2203.14465, 2506.10947, 2504.13837.

Files read: /home/user/learner/design/v3/30-modes/360-sleep-plan.md, /home/user/learner/design/v3/30-modes/sleep-research-2026-09-24.md, /home/user/learner/scripts/claude_rsn296_gen.py