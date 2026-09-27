# R1 complete-snapshot retention results

**Verdict: INCONCLUSIVE for mastery plus retention under the preregistered [PASSMARKS](../PASSMARKS.md).** Both seeds were required to reach at least 190/200 on grids5 after grid practice and sums4 after sum practice. Seed 29 reached only **174/200** on grids5; seed 30 reached **197/200**. Both reached **200/200** on sums4. No threshold, checkpoint, seed, or training budget was changed after seeing scores.

## Shown

Each run used the existing 1,646,750-parameter small dense loop, 2,500 grid steps then 2,500 sum steps, batch 64, no replay, independent 200-item held-out panels. Counts below are exact items right out of 200. **Own stop** is the registered primary score; fixed round 16 and right at any of 48 rounds are descriptive.

| Seed / held-out seed | Evaluation point and serving model | Grids5 own stop / fixed16 / any48 | Sums4 own stop / fixed16 / any48 |
| --- | --- | ---: | ---: |
| 29 / 92029 | After grids, current and frozen grid model | 174 / 179 / 184 | 0 / 0 / 0 (current only) |
| 29 / 92029 | After sums, latest mutable model | 0 / 0 / 0 | 200 / 200 / 200 |
| 29 / 92029 | After sums, task-routed frozen snapshots | 174 / 179 / 184 | 200 / 200 / 200 |
| 30 / 92030 | After grids, current and frozen grid model | 197 / 198 / 198 | 0 / 0 / 0 (current only) |
| 30 / 92030 | After sums, latest mutable model | 0 / 0 / 0 | 200 / 200 / 200 |
| 30 / 92030 | After sums, task-routed frozen snapshots | 197 / 198 / 198 | 200 / 200 / 200 |

On each seed, **zero previously correct grid items were lost** through the frozen route; zero previously incorrect items changed. The saved grid weights and state hash, the predictions and stop probabilities at **all 48 rounds** on the fixed 16-item audit subset, and per-item own-stop correctness on the full 200-item panel were identical before and after sum training. Serialization/reload preserved all-round outputs. Alternating grid/sum/grid requests after restart returned exactly the same outputs and stop probabilities, and unknown task IDs were rejected. Thus the scoped isolation mechanism worked on both runs, including the seed with valid mastery. The newest mutable model fell from 174/200 to 0/200 grids on seed 29 and from 197/200 to 0/200 on seed 30, so these trajectories did reproduce catastrophic forgetting without task-aware snapshots.

Seed 29 had 0 exact training/panel collisions rejected in grids and 3 in sums; seed 30 had 0 and 2. Replacements kept the original batch's puzzle size. No held-out panel was used for early stopping or adaptation.

| Run | Device | UTC interval | Wall time | Snapshot bytes | Two-snapshot bytes | Two-snapshot parameters |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Seed 29 | MPS | 2026-09-27 03:55:34–04:02:38 | 424.7 s | 6,599,145 grid; 6,599,100 sum | 13,198,245 | 3,293,500 |
| Seed 30 | MPS | 2026-09-27 04:02:58–04:10:02 | 424.4 s | 6,599,145 grid; 6,599,100 sum | 13,198,245 | 3,293,500 |

The runs used PASSMARKS commit `c7c8221a0a1617ddcbfad5fc30517da86573b8e5` and software HEAD `697f18b58057a6b4f376acc65abb5cd3e24fb5f8` on MacBook-Pro. Their generated [seed29 RUN-NOTE](seed29/RUN-NOTE.md), [seed30 RUN-NOTE](seed30/RUN-NOTE.md), [seed29 result](seed29/result.json), [seed30 result](seed30/result.json), training logs, and full checkpoints hold the raw evidence. The four reasoner unit tests passed before the registered runs in [software-tests.log](software-tests.log). The earlier interrupted seed-27 pilot is [exploratory only](EXPLORATORY-INTERRUPTED.md) and is excluded here.

## Suggested by the observations

The frozen, task-selected full snapshots prevented overwriting of grid behavior while a cloned model learned sums on the same trajectory. The seed-29 grid model did not reach the registered mastery threshold, so the two-seed R1 claim remains inconclusive even though the engineering isolation checks succeeded. A separately preregistered experiment could test stronger initial grid mastery; these results do not authorize reinterpreting or rerunning R1.

## Untested

This is **task-aware serving**: the caller supplies the existing `Item.env` skill identity. It does not learn which model to select, preserve old skills in one fixed-size network, cover unknown task identities, demonstrate transfer to new puzzle families, or establish general language-model retention. Storage and serving capacity grow by one complete model per skill.
