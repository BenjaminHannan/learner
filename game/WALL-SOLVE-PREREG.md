# The game-world wall: theories, $0 tests and the GW-O reading, written before the tests run (Oct 16 2026)

Solve session for Muse's packet (Ben's direction, Oct 16). Commit time = seal. Labels: **shown** = read in code or files;
**suggested** = reasoned; **untested**. Nothing here changes, re-bars or re-aims GW-O (A29); GW-O numbers had not been pushed when this
was written (branch `claude/game-world-mac-results`, newest commit Oct 12 = GW-PC).

## 0. Packet claims checked against the record before theorising

1. **Wrong (shown): "every attempt to push past the labeller-trained level by learning from its own play has failed."** No self-play
   run started from GW-L. GW-F (A26), GW-F2 (A27, warm start from GW-F round 16) and GW-O (A29) all start from a **fresh rank-8 add-on on
   the untrained parent** (sealed 3.75 / 3.61). They were trying to climb from about 3.7 to 5.2, not from 6.5 / 7.1 past 8.23. The
   question "can own-play learning go beyond the labeller-trained student" has **never been run**.
2. **Wrong framing (shown): "a wall somewhere around 4 to 7 unlocks".** These are two different numbers from two different processes:
   (a) self-imitation from the untrained parent sits at 3.9 to 4.6 (the reward-trained level, GW-P8 4.15 / 4.19); (b) GW-L sits at
   6.50 / 7.10 and is **not walled**: its training accuracy was still rising at the last epoch (0.71 / 0.72) and sealed play rose
   +1.6 from 16k to 64k labels (A23, "these are floors"). Nothing on record shows a plateau at 6.5 to 7.
3. **Closed by existing evidence (shown): "the student's ceiling under partial sight may be near GW-L".** The labeller is a memoryless
   pure function of the same 9x7 text view, stats and items that the student reads (`game/oracle.py` docstring; A22), and it scores
   8.23 under the same act rule (explore 0.10). So the best view-only memoryless policy scores at least 8.23. The partial-sight
   ceiling is above GW-L by at least 1.1 unlocks; it cannot be the 4-to-7 wall.
4. **Numbering slip (shown):** GW-F's marks are A26 (`game/A26-GWF-MARKS.md`); A28 is the stall census. The packet's "GW-F (A28)" is a
   label slip, not a fact error.
5. **"Ready-state wpick share stayed low (6.2% / 7.7% at round 24)": true but partial (shown, A27-RESULT.json).** Seed 201's share was
   12.9, 10.6, 10.2, 11.0% in rounds 20 to 23, above its round-16 7.9%; round 24 (7.7%) is its lowest since round 19.
6. **"Ceiling 22" is the achievement count; the unlock score counts cheap and deep achievements equally (shown, `game/score.py`
   shares).** The labeller collects no saplings and plants nothing (A23); GW-P8 After does both on 86 to 100% of maps. So a student
   could pass 8.23 by adding the sapling / plant / wake-up habits to labeller-level play, with no deeper chain. "Past the labeller"
   must be read on non-habit, chain-depth achievements, not on the total alone.

## 1. Candidate theories and what separates them

Settled facts every theory must cover: **F1** GW-F proved wrong (3.93 / 3.93); **F2** GW-F2 proved wrong (4.03 / 4.55);
**F3** the census conflict (ready-state kept rows wpick : other 0.145 / 0.335 weighted; the A27 rule lowers it to 0.133 / 0.151);
**F4** seed 201 rose +0.62 r16 -> r24 with a low ready-state share.

One exploratory observation was made before this file was written and is **not** usable as confirmation of any theory (it shaped T6):
the seed-201 sealed rise decomposes by achievement (maps of 100, r16 -> r24) as wood 52 -> 70, table 30 -> 51, wood sword 2 -> 14,
wood pickaxe 6 -> 19, zombie 29 -> 24, others within +-3; seed 200: table 35 -> 29, pickaxe 3 -> 4, zombie 23 -> 32, drink 20 -> 12. Also:
played moves agree with the labeller on its nav / act views 7 to 10% in every A27 round (kept rows 20 to 24%); GW-F round 8 sealed for
seed 201 was 4.37, so its round-16 3.93 was a low point.

| | Theory | Mechanism | Covers F1-F3? | Covers F4? |
|---|---|---|---|---|
| T1 | **Ready-state label conflict** (census, Fable) | the fixed point is set by the pooled wpick : other ratio of kept rows in ready states; cheap-event `do` rows outvote `wpick` | yes | **no**: the A27 rule lowered the ratio (0.335 -> 0.151 on seed 201), so T1 predicts seed 201 flat or down |
| T2 | **Rare-row dose** (A26 diagnosis) | too few consistent `wpick` rows and updates (GW-L's clean dose was 630 rows / 2,500 updates) | F1 yes; F2 needs "3x more rows is still too few"; F3 compatible | partly: A27 raised the wpick-type rows about 3x on both seeds; T2 predicts both seeds rise in proportion to their wpick-row gain, seen in P(pickaxe given table) |
| T3 | **State coverage** (Track 10's premise) | the student never reaches the states where better play is decided | **no for F1-F3**: the self-play loops are on-policy by construction and reached ready states 420 / 684 times in round 16; coverage can only bind at deeper links (stone with a pickaxe) or for GW-L (off-policy) | no |
| T4 | **The trainer does not fit the rows** | weighted cross entropy with 20:1 type weights, about 108 updates a round, a persisting Adam at 1e-3: the kept rows are not learned | yes | weakly (noise) |
| T5 | **Partial-sight ceiling** | best view-only play is near GW-L | **killed** by item 0.3 (labeller 8.23, memoryless, same view) | — |
| **T6** | **Weak improvement operator on a map-blind policy** (this session's lead) | event-segment self-imitation keeps the policy's own moves in the 12 moves before an event; for a policy that does not read the map those walks are near-random, so the rows carry almost no consistent navigation signal (played nav agreement 7-10%). The policy stays map-blind; the chain is capped at its **entry** (wood on 52-75% of maps, table 29-51%, against GW-L's 97-100% and 89-99%), every later link is multiplied down, and the loop improves only by a slow drift (about +0.02 unlocks a round). The ready-state conflict is the same habit dominance seen in one state class: a map-blind policy standing near a table does its habit move | yes: F1, F2 = drift far short of +1.3; F3 = habit dominance | **yes**: F4 = seed 201's continuing drift (it was already the faster seed: table games 55 -> 155 over A26) plus checkpoint noise, and the gain sits at chain entry, which the ready-state share does not measure |
| T7 | **Checkpoint noise** (a component, not a whole theory) | the sealed score of one checkpoint varies from round to round by more than the paired map SE (0.16) shows, because the policy itself changes every round | — | yes if r16 -> r24 is inside trend + checkpoint noise |

**The discriminating predictions (what each says that the others do not):**
- **Where the gap to GW-L sits.** T1 / T2: mostly in P(pickaxe | table) and later links. T6: a large share already at chain entry
  (P(wood), P(table | wood)) and in navigation-dependent achievements (drink, cow, zombie), with P(pickaxe | table) also low.
- **What moves when a self-play loop improves.** T1: the ready-state ratio, then the share, then pickaxe. T2: the absolute wpick-row mass,
  then P(pickaxe | table). T6: the navigation agreement of played moves and chain entry (wood, table) move first and together;
  the ready-state share follows.
- **Seed 201 in A27.** T1: flat or down (ratio fell). T2: up on both seeds in proportion to wpick rows, seen in P(pickaxe | table).
  T6 + T7: continuation of seed 201's earlier trend, no break at round 17, gain at entry links.
- **A competent (map-reading) start.** T1, if the conflict is a property of the label rule: GW-L's own play, cut by the same event
  rule, gives ready-state wpick : other <= 0.5 again. T6: from a map-reading policy the ratio is high (>= 1), because a policy that
  reads the map does not linger by the table doing its habit move.
- **GW-O** (consistent one-step labels on the model's own states, no navigation labels): see section 4.

## 2. The $0 tests, in order, with readings fixed now

All on files in `game/results/` and the A26 / A28 tables, unless marked. None plays a sealed map. Tests Z1 and Z4 touch numbers I
have partly seen (above), so they are **exploratory**: they can kill a theory but cannot confirm T6.

**Z1. Chain-link decomposition of every available sealed per-world file** (A27 r16 and r24, both seeds; GW-P8 and any GW-L / labeller
per-world files that exist). Per arm: P(wood), P(table | wood), P(pickaxe | table), P(stone | pickaxe), mean length; and the gap
between arm pairs split into groups: entry {wood, table}, ready decision {wood pickaxe, wood sword}, depth {stone, place stone, coal,
furnace, stone tools}, navigation-dependent survival {drink, cow, zombie, skeleton}, habit {sapling, plant, eat plant, wake-up}.
- If the self-play-to-GW-L gap in **entry** links is >= 40% of the non-habit gap -> T6 supported (exploratory), T1 / T2 as the whole wall
  weakened. If the ready-decision and depth groups carry >= 70% -> T6 killed as the main account.
- If seed 201's r16 -> r24 gain sits >= 60% in entry links -> F4 is not a ready-state fact and T1's failure to cover it no longer
  counts against T1; if >= 60% in P(pickaxe | table) -> T2 supported, T6 weakened.

**Z2. Trend and checkpoint noise behind seed 201's rise.** Practice mean unlocks per round (400 games), rounds 1 to 16 from A26's
tables, 17 to 24 from the A27 round files, per seed. Fit a line on rounds 1 to 16; take the residual SD (minus the 400-game sampling
variance) as the checkpoint SD; ask whether rounds 17 to 24 sit above the extrapolated line by more than 2 SE of their mean, and
whether the sealed r16 -> r24 change (+0.62) is inside the band trend x 8 rounds +- 2 sqrt(2 checkpoint SD^2 + paired map SE^2).
Sealed r8 / r16 / r24 give a three-point check of the same thing.
- Inside the band -> F4 needs no mechanism of its own (T7); all theories are freed from it, and "A27's rule helped seed 201" is
  not on record. Outside the band (above) -> a real rule effect on seed 201; T2 or T6 must say why seed 200 did not get it.

**Z3. Ratio, dose or competence: what predicts the next round's ready-state share** (A28-census.json, rounds 1 to 16, both seeds,
A26 rule = what was trained). Share(r) = E / V. Rank-correlate share(r+1) - share(r) with (a) W_w / A_w at r (T1), (b) W_w at r (T2),
(c) table games at r and played nav agreement (T6's competence). 30 round pairs; low power, read only big effects (|rho| >= 0.45).
- Only (a) predicts -> T1. Only (b) -> T2. Only (c) -> T6. None -> no reading (most likely, and said so).

**Z4. Navigation agreement series.** Played and kept agreement with the labeller on nav / act views per round (A27 files 17 to 24;
A26 rounds 1, 8, 16 from its text), per seed; correlate with wood and table games per round.
- Played agreement rises with wood / table games across rounds and is higher on seed 201 -> T6 supported (exploratory). Played agreement
  flat while wood / table rise -> T6's mechanism (map reading) is not what drove the entry gain; T6 weakened.

**Z5. Where the training mass goes.** For rounds 17 to 24, the share of training weight by event type and by segment length 1 (pure
habit `do` rows) vs walk rows, and the wpick-type share of weight.
- Describes T4 / T2 inputs; no verdict by itself.

**Needs saved checkpoints or play files (CPU minutes, $0; only after GW-O frees the Mac, or on the cloud box; never on the Mac while
GW-O runs):**

**Z6. Map reading of the self-play checkpoints.** GW-F / GW-F2 merged checkpoints (rounds 8, 16, 24) scored on GW-L's 2,000 held-out
views (top-1 on the 1,491 map-dependent views S; always-`do` = 27.2%; GW-L 62-65%).
- S accuracy <= 33% on every checkpoint -> the self-play policies are map-blind: T6's premise shown. S accuracy >= 45% on round 24
  -> T6 killed (they read the map; the wall is elsewhere).

**Z7. Is GW-L's gap to the labeller a state-coverage gap?** The GW-L 64k checkpoints play 200 practice games; every visited view is
labelled by the labeller; top-1 agreement on own-visited map-dependent views vs on the off-policy held-out S (62-65%).
- Own-state agreement within 5 points of held-out -> coverage is not GW-L's gap; Track 10's on-policy distillation arm is not needed for
  this gap (more labels / updates is the cheaper test). >= 15 points lower -> coverage is real; keep that arm.

**Z8. The census on a competent policy (the T1-versus-T6 discriminator).** The GW-L 64k checkpoints play 400 practice games each
(new run seeds); build the GW-F rows with the committed code (`keep_segments`, `type_weights`, `rows_of`, A27 rule) and run
`census_ready.py`'s counts on them.
- Ready-state W_w / A_w <= 0.5 on both seeds -> the conflict is a property of the event label rule itself: T1 holds as a label-rule
  theory, T6 is wrong about where the conflict comes from, and self-imitation from GW-L is predicted to erode GW-L's pickaxe play.
- >= 1 on both seeds -> the conflict came from the map-blind policy (T6); self-imitation from GW-L is not predicted to erode it, and
  the run in section 3 becomes the decisive one. Between -> no reading.

## 3. The run, if one is still needed (written now; bars fixed before it starts; not started)

Decided after Z1 to Z8. Its form (to be finalised in its own marks file before any code runs):
**GW-LS: the GW-F2 loop started from GW-L.** One change per arm: arm S = the GW-L 64k checkpoint of each seed + 8 rounds of the A27
loop exactly as specified (rare-keep 100, weights, buffer from empty, fresh optimiser, 400 practice games a round, new run seeds).
Arm C = the same GW-L checkpoint with no further training (its recorded sealed scores 6.50 / 7.10 are the paired baseline; re-scoring it
is deterministic, so if its per-world file is lost it is re-scored once, not as a new read).

## 4. The GW-O reading per theory, fixed before any GW-O number exists

GW-O's own marks are untouched (round 3: wpick share pass >= 30% on both, proved wrong < 15% on both; round 7: pass-to-confirm both
>= 5.2 and pickaxe >= 40% and stone >= 15% of maps; proved wrong both < 4.6 or pickaxe < 20% on both). GW-O labels only the move that
gives a first unlock one step ahead: no walk, no navigation, ties `wpick` / `wsword`.

| Theory | Round-3 share | Round-7 screen |
|---|---|---|
| T1 conflict | predicts >= 30%. **< 15% kills T1 as sufficient** (consistent labels did not fix it). 15-30% leaves it open | if T1 is the wall: pass. **Share >= 30% with a final < 5.2 kills T1 as the wall** (it was a real defect, not the binding one) |
| T2 dose | by round 3 the wpick rows are about 50 to 150 (ready games x about one row x the 50% tie), far under 630: predicts 15-30% or lower. **>= 30% weakens T2** (consistency, not dose, was the limit) | a pass would need far more wpick rows than T2 thinks enough: pass weakens T2 |
| T4 trainer | predicts < 15% (A29's own "learnability" reading). **>= 30% kills T4 for the ready-state rule** (the add-on fits a consistent rule from about 100 rows at 10 epochs) | no extra prediction |
| T6 map-blind entry wall | no strong prediction (the rule is local; a lean to >= 15%). **< 15% does not touch T6** | predicts **no pass**: wood on <= 80% and table on <= 65% of sealed maps on both seeds, pickaxe maps <= table maps, total < 5.2. **A pass with wood <= 80% kills T6** (entry was not binding). A pass with wood >= 90% weakens T6 badly (navigation was learned without navigation labels). Share >= 30% and final < 4.6 = A29's own "walk between links" reading = T6's prediction |
| T7 noise | — | a seed-to-seed spread up to about 0.6 and a round-3 vs round-7 sealed change up to about 0.4 (if both are scored) are not evidence of a difference |
| T3 coverage | not tested at the pickaxe link (on-policy anyway) | stone >= 15% would show the stone states are reached on-policy |

## 5. Kill list and open list: in the final report (written after the tests).

## Addendum before Z7 / Z8 run (20:30 UTC Oct 16; no reading changed)
- Z1 to Z5 have run (results in the final report). Z6 cannot run: no GW-F / GW-F2 checkpoint exists on any branch (record search).
- Z7 and Z8 run in this cloud container (4 free CPU cores, $0), **not on the Mac** (GW-O untouched). Inputs from
  `origin/claude/project-thread-yha868:results/game-world/glprobe-run/` (GW-L 64k checkpoints s200 / s201, held-out views).
- Practice run seeds **398** (seed 200) and **399** (seed 201), unused anywhere in the record; days 0 to 3, worlds 0 to 99, act stream
  `default_rng([9, run seed, day, i])`, explore 0.10, sample T = 1, cap 1000: the A26 play rule with the GW-L checkpoint as the policy.
- One play pass serves both: Z8 uses all 400 games; Z7 uses the first 200 (days 0 and 1), as written, and also reports all 400.
- Check before any reading: the loaded checkpoints must reproduce A23's held-out S top-1 (62.4% / 64.8%) to 0.1 point.
- (20:56 UTC, run launched 20:54, no full-run number seen.) Reproduction check passed exactly: held-out S top-1 62.44% / 64.79%
  (A23 62.44 / 64.79). Z7's **primary** reading = top-1 on every visited nav / act view of the first 200 games (days 0-1), minus the
  held-out S top-1; unique-view and all-400 versions are secondary. A 4-game smoke test printed one number (seed 200: -14.4 points on
  470 views); it is not read. Z8 is read under the A27 rule as written; the A26-rule numbers are reported.
