# Addendum A21 (9:01 PM ET 10-12): does GW-P8's gain come from reading the map, or from a better habit?

Written before any number exists. Commit time = seal. Prompted by both outside judges (Fable 5.1 and Opus 5.5, via the batch API,
10-12 night), who each said to run this evaluation-only check before spending training time (their premise was untested).
Nothing here trains anything.

## The test
- q-bar = the GW-P8 final policy's (night-8 checkpoint, its own T: 19.818454 / 20.977978) mean move distribution,
  softmax(log-probs / T), over the views it met in its own night-8 practice quiz (quiz worlds, never sealed), made by game.blind.
- Blind arm: on the same 100 sealed maps, every move drawn from that q-bar, ignoring the view (game.score --arm blind), same act
  seeds and explore rate as A17. Before = the Mac GW-P8 After files (4.15 / 4.19); the GW-B habit of the untrained parent was 3.78 / 3.67.
- Difference and 95% interval: game.analyze's paired bootstrap over the 100 maps.

## Marks
| Mark | Says "habit, no map reading shown" | Says "reads the map" |
|---|---|---|
| H-1 | abs(After_GW-P8 - Blind_final) <= 0.3 on both seeds | After_GW-P8 - Blind_final >= +0.5 with interval low > 0 on both seeds |
Anything else: no verdict, reported as is. No hair-miss allowance (a control).
Also reported, not a mark: Blind_final - Blind_untrained (A17: 3.78 / 3.67) and the view dependence (mean KL to q-bar) of the final policy.

## What each outcome means
- Habit: the +0.40 / +0.58 is move-frequency tuning; training knobs (credit, step size) have not yet shown map learning, and the
  next question is how to make the signal teach map-to-move links at all.
- Reads the map: part of the gain is map reading, and the next change is chosen from the judges' two proposals (discount gamma 0.99 to 0.95,
  or learning rate x1.5-2.5 at T0), with their marks, before anything runs.

## Result (9:09 PM ET 10-12): H-1 gives no verdict; about half of GW-P8's gain is a habit (shown), the rest is within noise
| | seed 200 | seed 201 |
|---|---|---|
| GW-P8 After (Mac, 100 sealed maps) | 4.15 | 4.19 |
| Blind habit from GW-P8's final policy (same maps) | 3.96 | 3.87 |
| After - Blind_final (95%) | +0.19 (-0.11 to +0.48) | +0.32 (+0.02 to +0.62) |
| Blind_final - untrained blind habit (A17: 3.78 / 3.67) | +0.18 | +0.20 |
| view dependence at its own T (mean KL to q-bar; untrained parent in A17: 0.029 / 0.022, other view set) | 0.066 | 0.061 |
| top word the same across views | 100% | 99.8% |
H-1: the "habit" clause needs both within 0.3 (s201 is +0.32, a hair over, no allowance), the "reads the map" clause needs +0.5 on both
(not met). So no verdict, as written.
- Shown: a fixed habit with GW-P8's final move odds already scores 3.96 / 3.87, +0.18 / +0.20 over the untrained habit, so roughly
  half of GW-P8's +0.40 / +0.58 is move-frequency tuning ("up" fell from 24% to 16% and from 29% to 16-18%).
- Suggested: the other half (+0.19 / +0.32 over the habit) is map reading; the final policy is about 2-3x more view-dependent than the
  parent, but the intervals reach 0 (seed 200) or barely clear it (seed 201). Untested.

## Premise checks on the two judges' answers (shown from the code or the moves files)
- Fable's one change (discounted reward-to-go, gamma 0.99 to 0.95) assumed the credit is the episode's unlock count spread over all
  ~170 steps. It is not: the advantage is GAE(lambda 0.95, gamma 0.99) under a learned value (game/guess.py:7,17,35), an effective
  horizon of about 1 / (1 - 0.99 x 0.95) = 17 steps. Gamma 0.95 would make it about 10, a small tweak, not a test of "credit spread over a
  whole game".
- Opus's "weight decay erodes the distilled copy" is false: plain Adam, no weight decay (game/pg.py:9).
- Fable's explanation C (the policy drifts away from "do") is false: in GW-PC's own quiz play "do" rose from 65% to 68% (s200) and 61% to
  64% (s201) between nights 0 and 6; GW-P8's stayed about 60% / 53%. Both runs cut "up" (GW-P8 24% to 14%, 29% to 18%; GW-PC 19% to 11%,
  21% to 9%).
- Consistent with Fable's note on the clip (suggested): GW-PC's per-night KL 0.016-0.029 sits near the clip's own scale (eps^2 / 2 = 0.02,
  17-26% of ratios clipped), so the clip, not the temperature, set the step; "more movement" was already reached and did not help.

## What this changes
- Neither judge's one change is supported by a true premise, so no new game-world training run is started on their say-so. A screen is
  about 10 h of the Mac a seed pair, and the Mac slept once already.
- Held for later, cheapest first: (1) the sheet twin of GW-P8's method (the standing default: a game win ships if learned and does not hurt
  the spreadsheet skill; the twin labels it general or game-only); (2) the 6-seed confirm of GW-P8 itself, which needs parents beyond
  seeds 200 and 201; (3) Opus's learning-rate arm at T0, marks as in answer-opus.md, if a free Mac slot appears.
- The two answers are kept in the session scratchpad (opinions/answer-fable.md, answer-opus.md) and in reviews/gwpc-judges-2026-10-12.md.
