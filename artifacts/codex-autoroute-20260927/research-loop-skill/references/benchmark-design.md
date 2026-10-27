# Designing the benchmark

The loop optimizes whatever number you give it, and it will find every shortcut that number allows. That makes this the most consequential file in the skill.

## Contents
1. From a goal to metrics
2. Worked example: "new skills shouldn't overwrite old ones"
3. Other goal shapes
4. The per-trial budget
5. Noise and seeds
6. Designing the holdout
7. Leakage and reward-hacking checklist
8. The eval script contract

## 1. From a goal to metrics

1. **Name the capability.** Say what the model or program should be able to do that it can't now, stated as behavior rather than mechanism. "Keeps what it learned" is a capability; "uses EWC" is a mechanism.
2. **Borrow the field's metric** if one exists (the research phase should have found it). Standard metrics make results comparable to papers and come with known pitfalls.
3. **Choose one primary scalar** for keep/discard decisions. If two things matter, either combine them into one well-motivated number (e.g. mean final accuracy over all tasks, which rewards both remembering and learning), or make one primary and the other a guard.
4. **Add guards** for everything the primary metric could be traded against: new-task learning, speed, memory, output validity. A guard is a floor, usually relative to the baseline, e.g. `new_task_acc>=baseline-0.02`.
5. **Define the reference points** that give the number meaning: a floor (naive), a strong simple baseline, and a ceiling (an oracle or upper bound). Report progress as the fraction of the floor-to-ceiling gap closed.

## 2. Worked example: "new skills shouldn't overwrite old ones"

This is continual learning, and the problem it describes is catastrophic forgetting.

**Protocol.** The model sees tasks T1, T2, ..., Tk one after another, and never revisits old data unless the method stores some. After each task, evaluate on every task's test set. This fills a matrix R, where R[i][j] is the accuracy on task j after training through task i.

**Standard metrics** (Lopez-Paz and Ranzato, 2017, "Gradient Episodic Memory"):
- ACC = mean over j of R[k][j]: final accuracy averaged over all tasks. This is a good primary, because it rewards both remembering and learning.
- BWT = mean over j < k of (R[k][j] - R[j][j]): backward transfer. Negative means forgetting; this is the thing the user cares about.
- FWT: how much earlier tasks help learn later ones. It is optional.
- Forgetting (Chaudhry et al.): for each old task, the best accuracy it ever had minus its final accuracy, averaged.

**A sensible setup.** Make the primary ACC, with two guards:
- plasticity (mean R[j][j], i.e. how well each task is learned when it arrives) `>= baseline - small margin`, so the method cannot "remember" by refusing to learn
- a compute or memory guard if the method might cheat by storing everything

**References:**
- floor: naive sequential fine-tuning
- strong baseline: experience replay with a small buffer, which is known to beat many purpose-built methods (Chaudhry et al., 2019, "On Tiny Episodic Memories in Continual Learning")
- ceiling: joint training on all tasks at once

**Dev versus holdout.** The loop must not be able to learn "this particular sequence of tasks." Build the tasks from a generator:
- Use different task orderings, different sampled tasks, or freshly randomized facts for the holdout.
- Dev uses seeds or task pools A, and holdout uses seeds or task pools B that the loop never sees.
- If a method only helps on the dev sequence, holdout confirmation will expose it.

**Budget.** Use small models, short tasks and a few thousand steps, so one full sequence plus evaluation fits in 5 to 10 minutes. Check that floor < replay < joint holds at this scale before trusting it.

## 3. Other goal shapes

| goal | primary | typical guards | holdout |
|---|---|---|---|
| faster training | time (or steps) to reach a target validation loss | final quality | a different data shard or model size |
| higher accuracy | held-out accuracy or loss | runtime, memory | unseen data split |
| faster code | median wall time over fixed inputs | output equality with the reference | different inputs or sizes |
| better reasoning on a task family | accuracy on generated problems | answer format validity, compute per answer | problems from unseen generator seeds or templates |
| smaller or cheaper model | quality at a fixed parameter or FLOP budget | latency | unseen split |

For "time to target", cap the run at the budget and score a miss as the budget plus a penalty, so crashes and slow runs are ordered sensibly.

## 4. The per-trial budget

- Fix it in wall-clock time or steps, and enforce it inside the eval, so every trial costs the same and results are comparable.
- Choose it by trading signal against throughput: 5 to 10 minutes typically gives 50 to 100 trials a night.
- **Rank check:** the ordering of the reference methods at the short budget should match their ordering at a longer budget, or at least their ordering in the literature. If it doesn't, the short budget measures something else, such as early-training speed. Lengthen the budget or shrink the problem.
- On a single GPU, run one eval at a time. Parallel runs distort timings and cause out-of-memory crashes.

## 5. Noise and seeds

- The seed should change the things that genuinely vary: initialization, data order, sampled tasks. If results don't change with the seed, a single lucky configuration will look like progress.
- `calibrate` measures the spread across seeds. The minimum detectable improvement it prints is roughly z × sigma × sqrt(1/n_trial + 1/n_incumbent).
- If that number is larger than the effects you expect (typically a few tenths of a point to a few points), reduce noise before looping: use more eval examples, use more seeds per trial (`--seeds 3`), or average over more tasks.
- The harness confirms every apparent win on fresh seeds before keeping it. That removes most seed luck, but it cannot fix an eval that is too small.

## 6. Designing the holdout

The holdout answers one question: did the loop improve the capability, or did it fit the dev set?
- It must test the **same capability** on **unseen instances**: new data, new generator seeds, new task orderings. It should not test a different capability.
- It must be the **same difficulty distribution** as dev. Otherwise holdout changes reflect the distribution shift, not overfitting.
- It is **only ever run by the harness** (`calibrate` and `confirm`). Don't open its data files or print its examples. Every look at it, including reading its contents, leaks information into your next decision.
- It needs to be big enough that its noise is small relative to the effects. The harness uses the holdout spread from `calibrate` to decide whether a check counts as a regression.

## 7. Leakage and reward-hacking checklist

Check these before locking.

- [ ] The eval data never appears in training, and the holdout never appears anywhere the loop can see.
- [ ] The metric is computed by locked code, not by code the loop edits. The model code must not be able to report its own score.
- [ ] Nothing the loop can edit changes what is measured: the eval set size, which tasks are included, the seeds, or the time budget.
- [ ] No cache, checkpoint or file persists from one run to the next and leaks labels or results.
- [ ] Guards cover the obvious trades: memorizing instead of learning, refusing to learn new tasks, blowing the compute budget, emitting invalid outputs.
- [ ] A crash or timeout produces a non-zero exit code or no metric line, never a default "good" number.
- [ ] Outputs and checkpoints are written outside the repo or to gitignored folders.

If you later discover a hole, fix it rather than exploiting it. Commit the fix, run `relock --reason`, re-run the references, and recalibrate.

## 8. The eval script contract

- Print one line per metric, exactly `name: value` (or `name=value`), for the primary metric and every guard metric. Other output is fine; the harness takes the last match.
- Read the seed from the command (`{seed}` is substituted) or from the `RL_SEED` environment variable.
- `RL_SPLIT` is `dev` or `holdout`, if one script serves both.
- Exit non-zero on any failure.
- Finish inside `--timeout-min`. The harness kills the whole process tree on timeout and records a crash.
- Be deterministic given the seed, apart from genuine GPU nondeterminism.
