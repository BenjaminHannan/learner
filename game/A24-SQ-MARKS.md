# A24 (6:16 PM ET 10-14): SQ, can a search through copies of the game supply practice labels without the hand-written labeller? (marks fixed before any number)

Written after GW-L (A22/A23) and before any search code ran on a state. Context (all **shown**, A23): the 3M model with the rank-8 add-on learns a map-to-move rule from
64,000 labelled views (held-out S accuracy 62.4% / 64.8% against 27.2% for the best fixed word; sealed 6.50 / 7.10 unlocks against GW-P8 After 4.15 / 4.19), but every label came
from the hand-written labeller `game/oracle.py`. Everything the finished model does must be learned; a hand-written teacher is not allowed at run time. The open question is a
label source with no hand-written game knowledge. Ben, 7:47 PM ET 10-13: "decide for yourself and go with it". The outside-opinion prompt (`reviews/gpt-diagnose-labels-2026-10-14.md`)
is with Ben; its answer, when it comes back, is checked against this design and may change what is built after SQ, not SQ itself.

## What I checked first (shown, 6:00 PM ET 10-14)
`copy.deepcopy(TextEnv)` takes 2 ms; a copy stepped with the same actions gives identical text, reward and end flag for 200 steps (so a copy is an exact simulator); 200 steps on a copy
take 0.10 s (about 2,000 steps a second a core, view text included). All creatures and the terrain share one numpy `RandomState` (`world.random`), so `world.random.seed(x)` on a copy
gives the copy a fresh random future without breaking anything else.

## The change (one): label = first move of the best of many random look-aheads, scored by the game's own reward only
`game/search.py` (new). For a world state, for each of the 17 first moves a, run K rollouts on fresh copies: take a, then keep acting for H - 1 more steps with a **sticky random policy**
(each step repeats the previous action with chance P_REPEAT, else draws one of the 17 words uniformly), after giving the copy a fresh random future (`world.random.seed(draw)`).
The return of a rollout = sum over t of GAMMA^t * (the game's reward at step t), t = 0 for the first move. Reward = crafter's own (+1 for each new achievement, +-0.1 per health point).
Nothing about trees, water, cows, tables or the view text is used: the search sees only the world copy and its reward.
- K = 16, H = 24, GAMMA = 0.95, P_REPEAT = 0.75. Fixed here; not tuned.
- m[a] = mean return of first move a. **Signal rule** (the label exists only if both hold): max m >= 0.20 and max m - mean of the 17 values of m >= 0.10. Then the label is the argmax (ties to the lowest
  index, `play.WORDS` order). No signal = no label (the view is skipped, not labelled with a guess).
- The hand-written labeller is used **only to score this test** (what the oracle says for the same view); it never produces a training label in the search arm.

## The measurement
States: the probe's own state distribution, so the numbers read against A23. Practice worlds, run seed 392 (unused before; disjoint from 390 / 391), day 0, worlds i = 0, 1, 2, ...; each step takes the
oracle's move with chance 0.5, else a uniform random move (as `probe.episode`), episode cap from `game/constants.json`; the decision states are steps 3, 7, 11, ... (every 4th) of each episode. Worlds are
added in order until at least 300 views whose oracle reason is `nav` have been searched (stop at the end of the world that reaches it; at least 48 worlds). Never a sealed seed.
Per decision record: the view, the oracle word and reason, the 17 means, the search word or none, seconds. Reasons: sleep, act, nav, craft, wander (A22).

Three numbers on the sampled states (primary = the sticky policy above):
- **SQ-0 (instrument check, not a verdict):** among views with oracle reason `act` that got a label, share where the search word = the oracle word (the target is next to the player and faced; `do` is the answer). Needs >= 80%; below that the
  instrument is broken: fix it, say so, rerun, no tuning of the marks.
- **SQ-1 (coverage):** share of `nav` views that get a label. Pass >= 25%; proved wrong < 10%.
- **SQ-2 (agreement):** among `nav` views that got a label, share where the search word = the oracle word. Pass >= 60%; proved wrong < 35%.
Reported, not marked: the same three for all of S (nav + act), by reason; the best fixed word's agreement on the same labelled views; the signal-rule pass rate by reason; seconds a decision; distribution of search words;
the uniform control (P_REPEAT = 0) on the same states.

## Verdicts
- **Pass** (SQ-0 ok, SQ-1 >= 25% and SQ-2 >= 60%): a search through copies of the game finds the right move on a quarter of the map-dependent views without any game knowledge. Next: A25, the distillation marks (N = 16,000 search labels, trained exactly as GW-L's 16k
  students, sealed play against GW-L 16k 4.88 / 4.62, GW-P8 After and the fixed-habit control), fixed before the labels are generated. SQ passing does not show that the students learn; it shows labels exist.
- **Proved wrong** (SQ-1 < 10% or SQ-2 < 35%, SQ-0 ok): random look-ahead at this budget is not a label source for navigation. Next: a smarter rollout (learned value or inverse-dynamics, option C) or hindsight (option A) with its own marks; no distillation run is built on this.
- **No verdict** (anything else): one rerun on the same states with K = 32, H = 40 (about 3.3x the cost), then the same bars; no other change.
Only one seed of states (the states are one random draw of 48+ worlds; the search rng is fixed): SQ is a screen of whether labels exist. A pass is followed by A25's seed rule; it is not a claim about play.

## Pros and cons (project rule: before acting)
| | Pros | Cons |
|---|---|---|
| Search with the game as a tool (this) | no hand-written labeller; the game is an outside tool the model could call (the way a calculator is); free CPU (a decision is about 3 s on one core); labels come from the game's own reward, so they can exceed any teacher's knowledge; a cheap gate (about an hour) before any 10-hour run | the real world (Minecraft, a spreadsheet) cannot be copied and replayed, so this is a research instrument for the game world, not a deployable method by itself (a learned model of the world would be needed); sparse reward means far-from-target views get no label; random rollouts are inefficient |
| Hindsight windows (option A) | no copying needed | GW-S tried the 8 moves before an unlock: 3.3 to 3.5 |
| Learned value (option C) | deployable shape | GW-D tried a value guesser: 1.8 and 3.2 |
| The hand-written labeller again | works (7.1) | is the thing to remove |
Verdict: do the cheap gate first. Disagreement with an outside view is welcome here: if the prompt's answer says a different first change is better, it goes to A25 as a competing candidate, not into SQ.

## Not claimed
Agreement with the labeller is not play value. Two optimal first moves can exist (a diagonal target), so 100% is not reachable; the 60% bar is set below that ceiling. The state sample is the mixed policy's, not the finished model's own play.
