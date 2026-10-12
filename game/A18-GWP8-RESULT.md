# A18 (6:07 AM ET 10-12): GW-P8 result, 8 fixed reward-driven nights

Runs that count (A16b rule: first machine to finish both seeds): Ben's Mac, finished training 4:44 / 5:09 AM ET; scoring, audit and
analysis on the Mac. Full files: branch claude/game-world-mac-results (runs/gwp8-s20X/analysis/RESULT.md, score/). Before on the Mac
equals the cloud Before map by map (3.75 / 3.61). Moves used: 139,389 / 140,790, so PPO = ppo_steps_147456 (sampled 3.88, top move
about 2.5; Q-2 uses the sampled one). Code e9028ece5 (game code = marks commit 4fb211347).

| | seed 200 | seed 201 |
|---|---|---|
| After (unlocks a game, 100 sealed maps) | 4.15 | 4.19 |
| After - Before (95%) | +0.40 (+0.05 to +0.75) | +0.58 (+0.24 to +0.92) |
| After - PPO sampled at 147k | +0.27 (-0.07 to +0.60) | +0.31 (+0.04 to +0.58) |
| After - GW-P (2-3 nights) | +0.28 (-0.06 to +0.62) | +0.22 (-0.07 to +0.52) |
| After - view-blind habit (GW-B) | +0.37 (+0.06 to +0.69) | +0.52 (+0.21 to +0.82) |
| wood pickaxe, % of maps | 3 | 2 |
| policy temperature, night 0 -> night 8 | 19.69 -> 19.82 | 20.37 -> 20.98 |
| sealed progress on 50 maps, nights 0..8 | 16.6 17.0 17.3 18.0 18.4 17.5 18.8 17.8 19.3 | 15.1 16.0 18.5 18.2 17.6 18.1 18.3 19.5 18.7 |

## Marks (A15)
- Q-1 After - Before >= +1.0 with interval low > 0: FAIL on both seeds (+0.40, +0.58). Proved wrong needed < +0.5 on both; seed 201
  is +0.58, so not proved wrong.
- Q-2 at least as good as the stronger PPO at equal moves: PASS on both (+0.27, +0.31). Caveat (suggested): sampled PPO checkpoints
  range 3.72-4.40 between 41k and 230k moves, so one checkpoint is a noisy yardstick; a fitted PPO curve would be fairer.
- Q-3 wood pickaxe on >= 10% of maps: FAIL (3%, 2%).
- GW4 old skills (routed by the run's switch): PASS both, drop 0.00, nothing fired. GW5 audit: PASS both. GW6: PASS both.

## Reading
- Shown: 8 fixed nights beat 2-3 quiz-stopped nights by only +0.22 to +0.28 (intervals include 0). The learning is real but slow,
  about +0.05 to +0.07 unlocks a night, mostly placing saplings (48 -> 86% on s200) and waking up.
- Shown: the temperature hardly moved (T stays ~20), and GW-B showed the T0 parent's start is a view-blind do/up habit.
- Suggested: at T ~20 each night's policy step is tiny (the API judge's point), so the slow learning is the temperature, not the
  number of nights. Untested.
- Next (A17): GW-PC, distil the T0 parent into the add-on at T = 1, then learn at T = 1. Marks before it runs. The pre-registered
  "smaller PG batches a day" (A15, if Q-1 were proved wrong) is not triggered.
- The cloud pair (same seeds, cloud box) is scored automatically when its seed 201 finishes and is reported as a repeat.
