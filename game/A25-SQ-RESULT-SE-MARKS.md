# A25 (7:55 PM ET 10-14): SQ result (instrument check failed, no verdict) and the replacement gate SE: how well does the search play by itself? (marks fixed before the SE run)

## SQ result (A24 as written; code commit 5c78dcfbd3; all **shown**)
2,283 decisions over 48 practice worlds (run seed 392), 2.84 s a decision (4 cores, 36 min); the uniform-rollout control on the same states, 2.87 s, 36 min.
| | sticky rollouts (primary) | uniform rollouts (control) |
|---|---|---|
| SQ-0: labelled `act` views where search = oracle (bar 80%) | **68.4%** (320 of 497 views labelled) | 45.0% |
| SQ-1: `nav` views that got a label (pass 25%, wrong < 10%) | 70.4% (846 of 1,201) | 67.0% |
| SQ-2: labelled `nav` views where search = oracle (pass 60%, wrong < 35%) | **1.4%** (12 of 846) | 5.7% |
| best fixed word's agreement on the same labelled `nav` views | 27.5% (`up`) | 26.8% |
- **Verdict: the instrument check failed (SQ-0 68.4% < 80%): no verdict on SQ-1 or SQ-2**, exactly as A24 said ("fix it, say so, rerun, no tuning of the marks"). Read literally, SQ-2 is far below the 35% "proved wrong" line,
  but the pre-registered rule is that a failed instrument check is not a verdict.
- Words the search chose (primary, 1,463 labelled): `do` 820, `sleep` 227, `stone` 109, `furnace` 66, `table` 41, `wsword` 35, `ssword` 21, `spick` 22, moves 81 in all (`right` 28, `down` 19, `up` 19, `left` 15). The oracle's `nav` answers are moves.

## Why (post-hoc, not marked; 8 of the 48 worlds, 384 decisions, searched a second time with a different rng, and the achievements the player already had)
- **Not noise (shown):** when both searches gave a label for the same view they gave the same word 80.8% of the time (`act` 81.6%, `nav` 85.6%), and agreed on whether a label exists for 86.5%. The labels are reliable; they just are not the labeller's.
- **What the search follows (shown on these 220 `nav` views):** the game's one-time achievement rewards that are in reach. Of 220 `nav` views the player already had collect_wood in 208. Where wake_up was still open (86 views) the search said `do` (35) or `sleep` (27); where it
  was done it said `do`, `stone` (place stone, with stone in hand), `furnace`, `ssword` or `table` when the ingredients are in hand, and gave no label on 62 of 134. Move words were 8 of the 220 `nav` views' search answers (73 had no label).
- **Suggested, untested:** a reward-only search with a 24-move look-ahead takes whatever new achievement is closest (sleep for wake_up takes two moves) and cannot see value beyond the horizon (wood number 3 earns nothing once collect_wood is unlocked; walking toward a tree earns nothing until the tree is reached).
  A24's yardstick, agreement with the hand-written labeller, is therefore the wrong test of a teacher: SQ-0's premise ("target next to the player and faced means `do`") is false once that achievement is unlocked.
  A search can disagree with the labeller and still be the better teacher, or the worse one; agreement cannot say which.
- Not shown: that the search is a bad teacher. Not shown: that it is a good one.

## The replacement gate (one change): the search expert plays whole games; its score is the teacher's quality
The teacher's value is how well it plays, so measure that, with the labeller as the reference. **SE:** the search of A24 (K = 16, H = 24, GAMMA = 0.95, P_REPEAT = 0.75, the signal rule of A24, all unchanged) plays practice worlds by itself: every step it searches a copy of the world
(`search_means`, `pick`) and takes the labelled first move; with no label it takes the sticky random policy's next action (repeat the last action with chance 0.75, else a uniform word). The act rule is the scored arms' (explore 0.10 from `game/constants.json`; act stream `default_rng([7, i])`,
one uniform and one random action drawn every step, tested to match `play.play`). Nothing about the view text or the labeller is used. Cap 1000 steps (the scored cap).
Worlds: practice run seed 393, day 0, worlds 0 to 15 (16 worlds, never sealed). The same worlds and act streams are played by the hand-written labeller and by the uniform random policy (`play.play`), as reference arms, so the comparison is paired.
Reference points from sealed worlds (different worlds, so not paired): reward-trained GW-P8 After 4.15 / 4.19, the labeller 8.23, random 2.31, the A23 students at 64,000 labels 6.50 / 7.10.
- **SE pass:** the search expert's mean unlocks a game >= 6.0. Reason: a student reaches about 80 to 85% of its teacher's score here (6.50 / 7.10 against 8.23), so a 6.0 teacher is the least that could produce a student clearly above the 4.2 plateau.
- **SE proved wrong:** <= 4.5 (no better than the reward-trained runs, so labels from it cannot be worth more than the reward-trained runs' own signal).
- **No verdict:** between; then 16 more worlds (16 to 31), same bars on all 32.
Reported, not marked: the labeller and random arms on the same worlds, paired 95% bootstrap intervals (game.analyze.boot_diff), achievements, game length, share of steps from search / fallback / explore, seconds a step.
One set of worlds and one search rng stream: SE is a screen (project rule: >= 6 paired seeds to confirm); a pass says the search is a good enough teacher to build labels from, nothing about students.

## What each verdict does next
- Pass: write A26 (distillation marks: label the states the expert visits, N = 16,000 labels, the GW-L 16k training constants, sealed play against GW-L's 16k students 4.88 / 4.62 and GW-P8 After) before generating a single label.
- Proved wrong: the reward-only search is not a teacher beyond the reward-trained ceiling. Next candidate: a search whose horizon or reward is not reward-only, which has to come from something the model learns (a learned value, option C), with its own marks; no distillation is built on this.
- No verdict: the 16 more worlds; no other change.

## Pros and cons of this change (before acting)
| | Pros | Cons |
|---|---|---|
| Play value of the search expert | measures what matters (teacher quality), independent of the labeller's choices; fixed bars from known numbers; about 1.5 h of free CPU; the labeller and random arms come for free on the same worlds | a 24-move look-ahead at 2.8 s a step makes the teacher slow (distilling it later costs hours per 10,000 labels); one set of 16 worlds is a screen with wide intervals (about +-1.1); a high score would still not show the student learns it |
| Rerun SQ with more rollouts and the oracle yardstick | keeps A24 unchanged | answers a question (agreement) whose answer cannot decide anything: shown above that the search follows rewards the labeller ignores |
Verdict: do the play test. Disagreement with the labeller was the symptom; the teacher's own score is the test.
