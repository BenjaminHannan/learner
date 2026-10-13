# A20 (8:45 PM ET 10-12): GW-PC stopped at night 6 of 8; what the six nights show

Written after the numbers below existed; the marks are A19b, fixed 6:13 AM ET before any GW-PC run. The registered readout
(night 8, 100 sealed maps) does not exist: both Mac runs died in night 7 at about 12:05 PM ET (shown: no file in either run folder
changed after 12:03 PM ET, and none in the 1 h 46 min the Mac was awake again; cause not known, the Mac slept). game.mode cannot
resume a run, so finishing means a fresh 8-night run (about 9 h on the Mac). Code dc349958b; files: Mac ~/gw8/runs/gwpc-s20X,
cloud scoring in the session scratchpad.

## What was measured
| | seed 200 | seed 201 |
|---|---|---|
| PC-0: distilled night-0 policy at T = 1, 100 sealed maps (Before_T0 3.75 / 3.61, bar +-0.3) | 3.79 (+0.04, -0.27 to +0.35) | 3.69 (+0.08, -0.26 to +0.41) |
| PC-2: mean approx KL per night, nights 1-6 (GW-P8 0.00853 / 0.00835; bar 3x on nights 1-8) | 0.0189 = 2.2x | 0.0209 = 2.5x |
| ratios clipped by the PPO rule per night (GW-P8: 3-11%) | 17-26% | 17-26% |
| policy temperature, night 0 to night 6 | 1.000 to 1.048 | 1.000 to 1.048 |
| night-32-world quiz progress, nights 0..6 (GW-P8: 16.6 to 18.8 / 15.1 to 18.3) | 17.0 14.8 16.3 15.3 16.2 14.9 16.1 | 17.5 15.3 16.5 15.2 17.6 17.2 16.1 |
| night 6, 50 sealed maps | 3.54 | 3.56 |
| GW-P8 night 6, same 50 maps | 4.14 | 4.02 |
| GW-PC night 6 - GW-P8 night 6 (paired, 95%) | -0.60 (-1.0 to -0.2) | -0.46 (-0.82 to -0.10) |
| GW-PC night 6 - Before_T0, first 50 maps | -0.10 (-0.54 to +0.34) | +0.24 (-0.28 to +0.80) |

## Verdicts (A19b)
- PC-0 (validity): PASS on both seeds. The distilled policy is a fair stand-in for the T0 parent (shown).
- PC-2 (mechanism): not passed. Through night 6 the step is 2.2x / 2.5x, under the 3x bar on both seeds (shown). Reaching a 3x
  mean over 8 nights would need nights 7 and 8 to average 5.4x (s200) and 4.5x (s201) of GW-P8's step; the best night so far is
  2.7x and 3.4x. I treat it as failing, but the registered 8-night mean was never computed (untested). The second half of PC-2
  (view dependence of the final policy) was not measured.
- PC-1 (the idea): not the registered readout. At night 6 GW-PC is behind GW-P8's night 6 on both seeds with intervals below
  zero (shown), and no better than Before_T0. The proved-wrong clause needs KL >= 3x, which did not happen, so the formal
  label is "not completed", not "proved wrong".

## Reading
- Shown: moving the flat start into the add-on did make the policy valid (PC-0) and the steps about 2.2-2.5x bigger, but the
  quiz and the sealed score did not rise, while GW-P8's did at the same nights. Learning got no faster.
- Shown: the PPO clip fires 17-26% of the time (GW-P8: 3-11%), so steps at T = 1 run into the clip, not only into the temperature.
- Suggested (untested): the 1/T story was not the main limit; the limit is the signal (few rewarded moves, credit across
  ~170 steps) or the clip and the learning rate, not the step size alone. This is the "limit is the signal" branch of A19b, reached
  by a different route, and PC-1 was not formally proved wrong.
- Suggested (untested): T = 1 policies may explore worse than the T ~ 20 policy, whose flat odds are a free exploration bonus.

## What happens next
- No rerun of the 8 nights: GW-P8 gained about +0.05 to +0.07 unlocks a night, and a +0.5 gap cannot close in two nights.
  If anyone wants the registered readout anyway, it is one command on the Mac: GW8_TAG=gwpc bash ~/gw8/code/game/mac_gwp8.sh start
  after moving the two dead run folders aside.
- GW-P8 (4.15 / 4.19) stays the best game-world result. The A19b "limit is the signal" outcome points at a cross-night archive of
  unlock moves; its marks must be written before any code.
- Outside opinion offered (CLAUDE.md): two explanations remain for why T = 1 did not help (clip/learning rate versus signal and
  exploration); a prompt is saved under reviews/.
