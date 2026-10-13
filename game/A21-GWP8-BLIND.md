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
