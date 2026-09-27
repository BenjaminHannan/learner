# Replay allocation review — design only, no run

## Recommendation

Test **one fixed replay-budget reallocation** against a paired dense baseline: move **125 grid replay batches from phase B to phase C**. Keep the 6,500 total optimizer steps, batch size, model size, total **400** replay batches, total **325 grid** replay batches, and **75 sum** replay batches unchanged. The resulting schedule is **B: 125 grids + 2,375 sums; C: 200 grids + 75 sums + 1,225 mazes**. Predeclare collision-free, evenly spread C replay indices before any run; for example, in each of 25 blocks of 60 C steps, place grids at positions 5, 13, 20, 28, 35, 43, 50, 60 and sums at 10, 30, 55. In B, every 20th step is a grid batch. This is a *replay timing* test, not a claim that this schedule will pass.

This is more defensible than either exact 225-grid-C proposal: it nearly triples late grid replay (75 → 200) while preserving both kinds' aggregate replay counts. It gives C **125 fewer maze batches**, a 9.26% reduction from 1,350. The proposed 100/225/75 variant costs 150 maze batches (11.11%) and halves B's grid protection; the 125/225/50 variant cuts C sums replay by 25. The 125/225/75 combination uses **425**, not 400, replay batches. None of these reallocations holds each phase's new-kind exposure fixed: the cost of later grid practice must be reported rather than hidden under “same total steps.”

| Schedule | B grids / sums | C grids / sums / mazes | Total replay: grids + sums | B grid share | C maze change |
| --- | ---: | ---: | ---: | ---: | ---: |
| e4 dense baseline | 250 / 2,250 | 75 / 75 / 1,350 | 325 + 75 = 400 | 10% | — |
| **Recommended shift 125** | **125 / 2,375** | **200 / 75 / 1,225** | **325 + 75 = 400** | **5%** | **−125 (−9.26%)** |
| Considered: B100, C225G/75S | 100 / 2,400 | 225 / 75 / 1,200 | 325 + 75 = 400 | 4% | −150 (−11.11%) |
| Considered: B125, C225G/50S | 125 / 2,375 | 225 / 50 / 1,225 | 350 + 50 = 400 | 5% | −125 (−9.26%) |
| Considered: B125, C225G/75S | 125 / 2,375 | 225 / 75 / 1,200 | 350 + 75 = **425** | 5% | −150 (−11.11%) |

## Why this is a hard target

The [e4 dense results](../claude-rsn358e4-20260927/RESULTS.md) on six previously read dev seeds show mean grids5 **196.5 after A → 170.5 after B → 128.0 after C**. The per-seed B→C grid losses are **36, 53, 22, 73, 33, 38**. A target mean of 180 after C requires **+52** relative to the prior C mean, greater than simply erasing the mean C-phase loss of 42.5. Worse, moving grid replay out of B may lower the starting B score below 170.5; the C allocation would have to repair that damage too. The proposed C grid increase is large enough to be worth a single registered test, but no dose-response result establishes that it can recover 52 points. The per-seed floor of 160 is especially demanding against old dense C scores of **60** and **103**.

The same e4 dense arm averaged sums4 **200 after B, 191.83 after C** and maze7 **150.33 after C**, with mean total **T = 470.17/600**. To reach the proposed T mark (**≥510.17**), mean grids 180 and mazes no lower than 140.33 leave sums needing at least **189.83**. That is little slack. Preserving C's 75 sum replay batches matters because the old C sums range was 184–195; reducing them to 50 adds avoidable risk. Reducing maze practice from 1,350 to 1,225 may also cost more than the allowed 10 points, especially with no measured maze learning curve. More late grid replay is therefore a plausible retention pressure, not a plausible *guarantee* of retention without a maze penalty.

The [e5 warm-router](../claude-rsn358e5-20260927/RESULTS.md) and [e6 shared-layer](../claude-rsn358e6-20260927/RESULTS.md) results argue against spending this single-change test on experts. e5 forced new-group routing and still learned mazes at only **5.67/200** on average; e6 restored new-kind learning by unfreezing shared layers but collapsed grids to **42.33/200** after C. The dense e4 arm remained the strongest total-score comparator (**470.17** versus e5 **251.83** and e6 **321.17**). These are prior dev observations, not predictions on fresh panels.

## Controls and scope the parent should seal

The old e4 dense model has an explicit `env` embedding: `R.Net.embed` adds `self.env(env)`, and `R.tensors` obtains `env` from `Item.env`. Its 470.17 total is therefore **not a label-free baseline**. The new comparison needs the same common, label-free dense front end in **both** arms, no caller kind ID or hand-coded routing signal to the model at evaluation, and the same total **1,646,750 trainable parameters** per arm. The exact checker may use the hidden kind as scoring metadata; the model must not. If a front-end change alters parameter count or behavior, the paired new baseline—not the e4 historical mean—sets the maze and T margins. A learned gate is not needed for this schedule-only comparison. The [user goal](../../reviews/gpt-sol-auto-routing-2026-09-27.md) remains one model selecting from the puzzle itself; task-aware snapshots and 1B chat work are outside this test.

Use the same fresh, code-generated practice streams and sealed panels for both arms, six fixed seeds, shuffled mixed-kind evaluation without a model-visible label, and the same device/step/batch and optimizer settings. Freeze the replay indices and exact pass/fail rules in a committed and pushed PASSMARKS before a run. The prior e4 panels were already read, so they can motivate this choice but cannot be relabeled as fresh confirmation. This review used no training, hyperparameter pilot, download, external model, or blind-panel data.

## Falsifiers and decision

- **Grid target fails:** candidate mean grids5 after C <180 or any seed <160. This would show that later replay did not recover enough first-skill performance under the fixed budget.
- **B skill or maze cost fails:** mean sums4 after B <195, or mean maze7 after C is more than 10 below the paired label-free baseline. This would show the reallocation compromised learning even if grids improve.
- **Total value fails:** mean T is below paired baseline T +40 or the candidate wins T on fewer than 5 of 6 seeds. An improved grid score alone would not earn the change.
- **Mechanism/capacity invalid:** either arm receives the true kind through `env` or another task label, uses more than 1,646,750 parameters, exceeds 400 replay batches or 6,500 steps, or changes anything beyond the predeclared replay allocation. Such a run cannot answer the single-change question.

If the registered schedule fails, the honest result is that shifting a fixed replay budget toward the last phase was insufficient at this size. The next idea would require its own mark; changing the B/C counts after seeing these six seeds would not be a continuation of this test.
