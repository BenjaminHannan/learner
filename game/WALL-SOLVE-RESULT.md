# The game-world wall: result of the solve session (Oct 16 2026)

For Muse's packet (Ben's direction, Oct 16). Pre-registration: `game/WALL-SOLVE-PREREG.md`. It was sealed at commit 27dd259 (20:19 UTC)
before any test ran; addenda 75ebd68 and 9086d19 were added before Z7 / Z8 reported. Labels: **shown** = measured here or read in code;
**suggested** = reasoned; **untested**. GW-O was not touched: no GW-O number existed on any branch while this was written, and nothing ran on the Mac.
Cost: $0 for runs (free container CPU, about 2 h). Two independent implementations agreed on every Z1 to Z5 number. An independent audit checked
the Z7 / Z8 code, and it reproduced A23's held-out accuracy exactly (62.44% / 64.79%).

## Plain summary for Ben
There is no single wall at 4 to 7 unlocks. There are two separate problems, and neither is a wall.
1. **Learning from its own play fails because it was started from a model that cannot read the map.** Self-imitation copies the model's
   own moves. When those moves are mostly blind habit (the model agrees with the labeller on only 7 to 10% of map moves), the copies teach
   the habit. The model improves very slowly (about +0.02 to +0.05 unlocks a round), so 16 or 24 rounds could never reach 5.2. The same
   copying rule run on the labeller-trained model's own play (which agrees about 37% of the time) gives clean rows. In the states where the
   pickaxe should be made, the rows say "make the pickaxe" 3 to 10 times more often than anything else. The "label conflict" belonged to
   the blind model, not to the rule.
2. **The labeller-trained model is below the labeller partly because it was trained on states it doesn't itself visit.** On its own
   states it agrees with the labeller 19 points less than on the held-out set it was graded on.
3. **Seed 201's rise in GW-F2 was not caused by GW-F2.** Seed 201 had been climbing at the same pace since round 1. GW-F2's rounds sit
   slightly *below* that trend line, and the +0.62 is inside what trend plus round-to-round noise produces.
So the own-play route has never been tested from a starting point where it could work. The one run worth doing is self-imitation started
from the labeller-trained model (section 3). Its marks are written below; it is not started.

## 0. Packet claims that the record contradicts (evidence)
| Packet claim | Record | Status |
|---|---|---|
| "every attempt to push past the labeller-trained level by learning from its own play has failed" | GW-F, GW-F2 and GW-O all start from a fresh add-on on the **untrained parent** (A26 l.13-15, A27 l.9, A29 l.7). None starts from GW-L (6.50 / 7.10). | **wrong**: never attempted |
| "a wall somewhere around 4 to 7 unlocks" | self-play sits at 3.9 to 4.6; GW-L at 6.5 / 7.1 is still rising with labels and its training accuracy was still rising (A23: "these are floors"). The phrase "4-7" is not in the record ("about 4.2", A22 l.13). | **wrong framing**: two different numbers from two processes |
| "student's ceiling under partial sight" may be near GW-L | the labeller is a memoryless function of the same 9x7 view, stats and items (`game/oracle.py` l.1-21) and scores 8.23 | **closed**: the view-only ceiling is >= 8.23 |
| "GW-F (A28)" | GW-F's marks are A26; A28 is the census | label slip |
| seed 201 "ready-state share stayed low (7.7% at r24)" | 12.9 / 10.6 / 10.2 / 11.0% in r20 to r23 (A27-RESULT.json) | partial |
| "ceiling 22", score = unlocks | cheap habit achievements count the same as chain achievements. The labeller collects no saplings (4% of maps); a student could pass 8.23 on habits alone | "past the labeller" must be read on non-habit and depth achievements |
| Track 10 / Environment v2 / Section 5.7 / B3 | no such document on any of 109 branches or in Drive | verdicts below rest on the packet's own description |

## 1. The theory, and the candidates it beat

**Lead theory: self-imitation is a weak improvement operator, and how strong it is depends on whether the base policy already reads the map.**
Event-segment self-imitation keeps the policy's own moves in the 12 moves before each achievement event. Its rows are only as good as
the policy that played them:
- From a map-blind policy, the rows are mostly habit and stumbling. Played moves agree with the labeller on nav / act views 7.0 to 9.9%,
  kept rows 20 to 24% (A27 rounds 17-24, shown). The policy drifts up slowly (+0.023 / +0.047 unlocks a round, Z2, shown), and changing
  which rare rows are kept does nothing detectable (Z2 step at round 17: -0.11 / -0.12, about 0.8 SE, shown).
- From a map-reading policy (GW-L 64k), the same rule's rows are clean. Played agreement is 36 / 37% and kept 62 / 64%. The ready-state
  wpick : other ratio is **3.0 / 10.6** against 0.145 / 0.335 on the self-play loops (Z8, shown).

How it covers the four settled facts:
- **F1 GW-F proved wrong:** from a map-blind start, a drift of 0.02 to 0.05 a round needs about 15 to 60 rounds to gain the 1.3 the bar asked for.
- **F2 GW-F2 proved wrong:** the rare-keep rule changes which of the blind policy's rows are kept, not what kind of rows they are. Z2 finds
  no step above trend.
- **F3 census conflict:** the blind policy stands next to the table doing its habit `do`. A map-reading policy does not (Z8).
- **F4 seed 201's rise:** seed 201 is the faster-drifting seed (slope t of about 4). Its +0.62 is inside the trend-plus-noise band
  [-0.30, +1.05] (Z2, shown), and the gain sits mostly at chain entry (wood 52 -> 70, table 30 -> 51 maps; 60% of the non-habit gain, Z1).
  The ready-state share does not measure that.

**The candidates, with their discriminating prediction and what the tests did to them:**
| Theory | Discriminating prediction (unlike the others) | Result |
|---|---|---|
| T1 ready-state label conflict, as a property of the event label rule | the same rule on any policy's play gives ready-state wpick : other <= 0.5 | **killed as a label-rule theory** by Z8 (3.0 / 10.6). Survives only as a description of the blind loops |
| T2 rare-row dose | more consistent wpick rows produce a step up in share and P(pickaxe given table) | **weakened**: A27 tripled pickaxe-type rows (9-24 -> 37-273 a round) with no step above trend (Z2). Not tested for clean rows (GW-O) |
| T3 state coverage (Track 10's premise) | on-policy labels beat off-policy ones because the student's own states are unlike the training states | **not the self-play wall** (those loops are on-policy and reached ready states 420 / 684 times in round 16, 527 in a typical A27 round), but **real for GW-L's gap to the labeller**: -19.5 / -19.3 points on own states (Z7, shown) |
| T4 the trainer does not fit the rows | consistent rows on own states still leave the share under 15% | **untested** here (GW-O round 3 tests it). The logged losses are single minibatches and do not show fit either way (Z5) |
| T5 partial-sight ceiling | best view-only play is near GW-L | **killed** (the labeller's 8.23) |
| T6 strong form, "the wall is chain entry" | >= 40% of the self-play-to-GW-L non-habit gap sits at wood / table | **not supported** (21 to 30%; ready decision 37 to 38%, depth 15 to 21%, survival 17 to 20%; Z1 no verdict). The gap is spread over every link that needs the view read, which the lead theory expects |
| T7 checkpoint noise behind F4 | seed 201's r16 -> r24 change is inside trend + noise | **confirmed** by its pre-registered rule (Z2) |

## 2. The $0 tests that ran, and what they decided (all pre-registered; numbers shown)
| Test | Measured on | Result | Reading by the sealed rule |
|---|---|---|---|
| Z1 chain links | A27 sealed per-world files; GW-L and labeller per-world files (branch `claude/project-thread-yha868`) | P(wood) / P(table given wood) / P(pickaxe given table): self-play 0.52-0.70 / 0.56-0.73 / 0.09-0.37; GW-L 0.97-1.00 / 0.99 / 0.86-0.92; labeller 1.00 / 1.00 / 0.98. Non-habit gap: entry 21-30%, ready decision 37-38%, depth 15-21%, survival 17-20% | rule 1 no verdict; rule 2 (seed 201 gain >= 60% at entry) fires exactly at 60.0%, a knife-edge (exploratory) |
| Z2 trend and noise | A26 tables r1-16, A27 r17-24, sealed r8/16/24 | slopes +0.023 (SE 0.010) / +0.047 (SE 0.012) a round; r17-24 sit -0.05 / -0.11 below the extrapolated line; step at r17 -0.11 / -0.12 (SE 0.14 / 0.15); seed 201's +0.62 is inside [-0.30, +1.05] | **inside the band**: F4 needs no mechanism; "A27 helped seed 201" is not on record |
| Z3 ratio vs dose vs competence | A28-census.json, 30 round pairs | every pooled abs(rho) is under 0.45; all are negative (mean reversion) | no reading |
| Z4 nav agreement | A27 rounds | seed 201 played agreement is higher (9.1% vs 7.8%); seed 200's wood / table rose while agreement stayed flat | no clean branch |
| Z5 training mass | A27 rounds | the pickaxe type gets 4-8% of the weight; one-move rows 11-26% | descriptive |
| Z6 map reading of GW-F checkpoints | — | **could not run**: no GW-F / GW-F2 checkpoint exists on any branch | — |
| **Z7** GW-L on its own states | 200 / 400 practice games, run seeds 398 / 399 | top-1 on own-visited nav / act views 43.0% / 45.5% vs held-out S 62.4% / 64.8%: **-19.5 / -19.3** points (unique views -15.1 / -15.6) | **coverage is real** for GW-L's gap (>= 15 points lower on both) |
| **Z8** census on GW-L's play | the same 400 games per seed, A27 rule | ready-state W_w / A_w **3.0 / 10.6** (A26 rule the same); W / A rows 115 / 82 and 122 / 16; the other rows are mostly walks to trees and `do`, not habit; practice 6.92 / 7.13 | **>= 1 on both**: the conflict came from the map-blind policy; self-imitation from GW-L is not predicted to erode it; GW-LS is the decisive run |

## 3. The one run still needed: GW-LS, self-imitation started from GW-L (marks fixed here; NOT started)
Needs Muse's packet and Ben's go (Ben's 10-15 handover: no new runs without a Muse packet). It does not touch GW-O and does not run on the Mac.
- **Question.** Can the model's own play lift a competent policy, so that the own-play route is not capped by the labeller?
- **Arms (one change).** Arm C = GW-L 64k checkpoint, seeds 200 / 201, no further training. Its sealed per-world files (6.50 / 7.10) are the
  paired baseline, already on record, with no new read. Arm S = the same checkpoint as the parent, a fresh rank-8 add-on, and 8 rounds of
  the A27 loop exactly as in `game/imitate.py` (`rare_below` 100, n^(-1/2) weights with a 20:1 floor, 20,000-row buffer from empty, 3 epochs,
  Adam 1e-3, minibatch 256, 400 practice games a round, explore 0.10). Every round samples at T = 1, because GW-L is played at T = 1.
  Practice run seeds 398 / 399, days 4 to 35 (days 0-3 were Z8's games; run seeds must be under 400 in `play.practice_seed`).
- **Seeds and pairing.** 200 and 201 (a screen). The final screen is paired by world and act seed with arm C on the 100 sealed maps:
  one read, round 8, `game.score --arm model --picker sample --temp 1.0`.
- **Non-habit unlocks** = unlocks excluding collect_sapling, place_plant, eat_plant and wake_up. GW-L sealed non-habit is 5.46 / 5.85;
  stone is 40 / 43% of maps. The labeller is 7.80 non-habit, stone 83%.
- **Leading indicator, round 4 (practice games, means of rounds 3 and 4).** Stop as proved wrong early if, on both seeds, the ready-state
  W_w / A_w is <= 0.5 **or** practice non-habit unlocks fall 0.5 or more below round 1's (5.72 / 5.87, Z8). Otherwise continue.
- **Final (round 8, sealed).**
  - **Pass (screen):** on both seeds all three of: non-habit unlocks >= arm C + 0.3, with the paired 95% bootstrap low end > 0;
    total >= arm C + 0.5; stone maps >= arm C + 10 points.
  - **Proved wrong:** on both seeds non-habit unlocks <= arm C - 0.5, **or** stone maps <= arm C - 15 points on both. This means
    self-imitation erodes a competent policy.
  - Anything else: no verdict, with no extension without new marks.
  - A pass is a screen: confirmation needs 6 or more paired seeds and the view-blind habit control (A26).
- **Venue and cost.** This kind of free cloud container (4 cores, $0). Measured here: about 7.5 s a game, so about 50 min of play a round
  per seed at 2 threads. Training was 1 to 1.7 h a round in A27. So about 2 to 3 h a round with both seeds in parallel, about 16 to 24 h for
  8 rounds; it is resumable. Fallback: a Vast CPU box (8 to 16 cores, about $0.20 to $0.40 an hour, about $5 to $10 total), inside the
  $50 / week cap. Not the Mac (GW-O). Not the PC GPU (not needed).
- **What each outcome means.** Pass: the own-play route works from a competent start and is not capped by the labeller (on depth, not
  habits). The bottleneck was the cold start, which points to "distil first, then self-improve". No verdict: the operator neither erodes
  nor lifts. Self-imitation is then a stable but useless operator at 3M, and long-horizon credit (a progress signal) is needed.
  Proved wrong: the operator erodes competence. The habit attractor is a property of the operator itself, and the own-play route needs a
  different label source.

## 4. GW-O: the reading written before its numbers (sealed in the pre-registration, section 4; restated, nothing changed)
The pre-registration's T6 row is the lead theory's prediction. GW-O starts map-blind and labels only the last move of each link, so it
teaches no walks.
- **Round 3, share of `wpick` in ready states.**
  - **>= 30% on both:** kills T4 (the trainer) for the ready rule and weakens T2 (pure dose). It does not confirm the lead theory, which
    makes no strong round-3 prediction.
  - **< 15% on both:** supports T4 / learnability (A29's own reading). It does not touch the lead theory.
  - **15 to 30%:** open.
- **Round 7 sealed screen.** The lead theory predicts **no pass**: wood on 80% or fewer of maps and table on 65% or fewer, on both seeds;
  pickaxe maps no more than table maps; total under 5.2.
  - **A pass with wood on 80% or fewer kills the lead theory.**
  - A pass with wood on 90% or more badly weakens it.
  - Share >= 30% with a final under 4.6 is both A29's own "walk between links" reading and the lead theory's prediction.
  - T1 already lost its label-rule form to Z8. If GW-O passes, T1 survives only as "consistent last-move labels are enough".
- **Noise (T7).** A spread up to about 0.6 between seeds, and up to about 0.4 between the round-3 and round-7 sealed scores, is not evidence.

## 5. Kill list and open list
**Made unnecessary (shown or decided by the tests above):**
1. Any further keep / weight / balance / label-rule variant of event-segment self-imitation started from the untrained parent (a GW-F3).
   A27's change had no effect detectable above trend (Z2), and the conflict belongs to the blind base policy (Z8).
2. The label-rule swap: it stays dropped (A28's counterfactual, now also Z8).
3. A 6-seed confirmation of GW-F2's seed-201 rise: there is nothing to confirm (Z2).
4. Any experiment on the partial-sight ceiling: closed by the labeller (8.23 from the same view).
5. Z6 (map-reading probe of the GW-F checkpoints): the checkpoints are gone, and played agreement (7-10%) plus Z8 already settle its premise.
6. Waiting for the 10M learned drive before testing the own-play route: GW-LS tests it at 3M first.

**Track 10 arms (judged on the packet's description; the spec is not in the repo or Drive):**
- **On-policy labeller distillation: keep, re-aimed.** Z7 shows coverage is real for GW-L's gap to the labeller. But that gap is
  labeller-capped and is not the self-play wall. Its marks must compare against more off-policy labels at matched updates (A23's L-3
  confounds labels with updates). The frozen student-state bank is useful here, and only here.
- **Privileged (full-information) teacher: not needed for this problem; change its aim.** A view-only teacher already reaches 8.23, so
  partial sight does not bind at this level. Keep it only for depth beyond the labeller (stone -> furnace -> iron), with an audit that a
  view-only student can imitate its labels.
- **Verifier-guided labels: hold until GW-O reads.** GW-O is its one-step instance, and the lead theory predicts one-step verified labels
  do not teach the walks. A multi-step verifier is close to search labelling, which stays closed absent the Section 5.7 burden and Ben's decision.

**Left open on purpose:**
- Whether own play lifts a competent policy (GW-LS).
- Whether the GW-L-to-labeller gap is coverage (Z7: real) or undertraining (A23: still rising), and in what proportion. Z7 cannot rule out
  that own states are simply harder views rather than unseen ones.
- Whether the add-on learns the ready rule from about 100 consistent rows (GW-O round 3).
- Whether a map-blind start would ever reach 5.2 by drift (not worth testing).
- Anything past stone, transfer to other games, the 10M model.

## Single next action, and the first result that would prove this framing wrong
- **Next action:** with Muse's packet and Ben's go, start GW-LS (section 3) on the free cloud CPU. Its marks are fixed above, and the code
  path is `game/imitate.py` with the GW-L checkpoint as the parent.
- **First result that would prove the framing wrong:** GW-LS's round-4 leading indicator. If self-imitation started from GW-L drives the
  ready-state ratio back to 0.5 or below, or loses 0.5 or more practice non-habit unlocks on both seeds, then the habit attractor belongs
  to the operator, not to the cold start, and the own-play route is blocked for a reason this theory does not cover. (On GW-O's side, a
  round-7 pass with wood on 80% of maps or fewer would also kill the lead theory.)

Artifacts: `game/results/wall-solve/`: the Z1 to Z5 outputs of both independent implementations, the Z7 / Z8 result and reproduction JSONs, and the Z7 / Z8 code as it ran (its paths point at the session scratchpad). The 400-game play files are not committed (3 MB a seed); they can be rebuilt from run seeds 398 / 399.
