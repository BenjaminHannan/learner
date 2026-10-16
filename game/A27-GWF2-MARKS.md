# A27 (2:21 PM ET 10-15): GW-F2, one change to the GW-F loop (do not thin the rare events), warm start from round 16; marks fixed before any code is changed or run

## Why this and nothing else
A26 stopped GW-F at gate B with no verdict (rounds 1 to 16: pickaxe games of 400 flat at about 10 to 27 apart from one 49; stone games 0 to 7; round-16 sealed 3.93 / 3.93). The diagnosis in `game/A26-GWF-MARKS.md` ("Why it stalls", all shown): the model reaches a pickaxe-ready state (table within one cell, wood in hand, no pickaxe) in more games every round (seed 201: 35 -> 75 of 400) but plays `wpick` in only 4.3% / 7.9% of those states at round 16 (labeller: 100%), and each round's training set holds only 9 to 24 pickaxe rows and 8 to 10 stone rows out of about 3,800, because the keep rule takes the fastest 30% of every event type's segments, which cuts 70% of the rare events themselves. A27 changes only that.
Outside-opinion note: the diagnosis has a second plausible reading (the plateau is exploration or capacity, not the rare-row starvation); the A26 prompt file is refreshed for Ben to relay if wanted (`reviews/gpt-diagnose-labels-2026-10-14.md`, "Update 10-15"). This follow-up is cheap free-CPU work, so it does not wait for that.

## The change (one)
In `keep_segments` (`game/imitate.py`): **for an event type with fewer than 100 segments in the iteration, keep every segment of at most 12 moves, not only the fastest 30%.** Types with 100 or more segments (sapling, plant, wood, table, drink at these play levels) are unchanged: fastest ceil(0.3 n) within the 12-move cap. Everything else is the A26 spec to the letter: weights n^(-1/2) with n counted before the keep step and the 20:1 floor, the buffer prune rule, 20,000-row buffer, 3 epochs, minibatch 256, Adam 1e-3, 400 games an iteration on practice worlds, explore 0.10, sample T = 1, the same add-on, optimiser and parents. The flag defaults to the A26 behaviour, so the stopped GW-F files stay reproducible.
**Warm start:** both loops (seeds 200, 201) continue from their own iteration-16 state (a copy of the A26 output folders, which stay untouched), iterations 17 to 24, run seeds 394 / 395 and days 64 to 95 (never used, never sealed). About 9 h on the same 4 free CPU threads.
Why a warm start and no unchanged-continuation control: rounds 9 to 16 of the A26 loops are the control (flat); a re-run of the unchanged loop for 8 more rounds would cost the same 9 h for a known answer ("flat") and would delay the test. The cost is that a rise has to be told apart from the trend by the marks below, not by a paired twin.

## New instrument (logged each iteration, never a teacher)
`ready`: the games in the iteration that reach a pickaxe-ready state and the share of moves played in ready states that were `wpick` (computed from the saved play file with the labeller's view parser, as in the A26 diagnosis).

## Marks (both seeds; two seeds are a screen; fixed now)
- **Gate C (round 20; the means of rounds 17 to 20).** Proved wrong and stop: on **both** seeds mean g_pick(17 to 20) < 25 **and** mean ready-state `wpick` share < 12%. (Round 16 had pickaxe games 18 and 49, shares 4.3% and 7.9%; rounds 9 to 16 of seed 200: 10 to 18 games.) Anything else: continue to round 24.
- **Final (round 24): sealed screen**, 100 sealed maps, sample T = 1 (`game.score --arm model --picker sample --temp 1.0`), both seeds. Pass-to-confirm: both >= 5.2 unlocks a game **and** wood pickaxe on >= 25% of maps on both **and** mean g_stone(21 to 24) >= 10 on both. Proved wrong: both < 4.6. Otherwise no verdict.
- A pass is a screen only: confirmation needs >= 6 paired seeds against GW-P8 with the view-blind habit control (the final model's marginal move odds as a fixed habit must score >= 1.0 below the model) and the three-number fairness rule where it applies (A26).
- Reported, not marked: the sealed scores at iteration 20 (scored when round 20 ends), practice mean unlocks, g_wood / g_table, ready-state shares and games, kept rows by type, seconds a round.
- The change is chosen after seeing 16 rounds (post-hoc): so a pass counts as a screen result, nothing more, and a no-verdict leaves the question open, not closed.

## What this can and cannot show
Shown if it passes: the A26 loop was starved of rare rows and the snowball starts when they are not thinned. Not shown even then: that it transfers to a real game, that it beats a PPO with the same moves, that it is not a habit (the habit control), anything for 10M. If it is proved wrong: the starvation reading is wrong at this scale (the A26 prompt's second reading, exploration or capacity, stays), and the next candidate is the expert-iteration instrument (a search whose confident steps are imitated, A25's search), with its own marks; I expect the same wall there (the search expert made the pickaxe in 1 of 32 worlds), which is why it is second.

## Pros and cons (before acting) and the verdict
| | Pros | Cons |
|---|---|---|
| A27 | one change aimed at a shown defect; free CPU; warm start saves 16 rounds; the rows that matter go up about threefold; an early stop at round 20 | chosen after seeing the data; three times more rows may still be too few (about 17 to 66 pickaxe rows a round); no paired control (the rounds 9 to 16 trend is the control); slow segments that pass the 12-move cap are noisier labels; two seeds |
| stop here and wait for the 10M learned drive | zero cost | learns nothing new for 9 h of free CPU; the 10M drive has a long queue |
| expert-iteration first | the other outside-answer candidate | the search expert is no better than the model at the pickaxe (1 of 32 worlds), 2.8 s a step |
Verdict: do A27. Reason: it is the only candidate whose failure would also say something clear (rare rows are not the problem) and the cost is free CPU.

## Result (round 24 done, sealed screen scored 1:29 AM ET 10-16)
Rounds 17 to 24 ran as marked on both seeds (the loops were killed and restarted three times by container restarts; each restart resumed from the saved state and the per-chunk play files, so no round was changed). Files: `game/results/A27/` (`A27-RESULT.json`, the four sealed per-world files, the 16 round files).

| seed | sealed r16 (A26) | sealed r24 | paired change (SE) | pickaxe maps r16 -> r24 | mean g_stone r21-24 | practice unlocks r17 -> r24 | ready-state wpick share r24 |
|---|---|---|---|---|---|---|---|
| 200 | 3.93 | **4.03** | +0.10 (0.16) | 3 -> 4 of 100 | 1.25 | 3.81 -> 4.14 | 6.2% |
| 201 | 3.93 | **4.55** | +0.62 (0.17) | 6 -> 19 of 100 | 5.75 | 3.97 -> 4.62 | 7.7% (10 to 13% in r20 to 23) |

**Marks read literally (shown):** pass needed both >= 5.2, pickaxe >= 25% on both, mean g_stone(21 to 24) >= 10 on both: none met. Proved wrong needed both < 4.6: 4.03 and 4.55, so **A27 is PROVED WRONG by the rule fixed in advance.** Gate C at round 20 had not stopped it (seed 201 mean g_pick(17 to 20) 38.5, above 25), so it ran the full 24.

**Plain reading.** Keeping every rare segment did not start the snowball. Seed 200 did not move (+0.10 against a standard error of 0.16). Seed 201 did move: +0.62 on the same 100 sealed maps (about 3.6 standard errors paired), and its pickaxe maps went from 6 to 19, so the change helped one seed, partly, and was far from the 5.2 line. Seed 201's score of 4.55 sits 0.05 under the 4.6 proved-wrong line, which is inside the 100-map noise (SE 0.16); the mark was fixed in advance and I do not move it.

**Prediction scored (A28 census: "A27 flat").** Right for seed 200, wrong for seed 201 (shown). The census said the rule does not raise the pickaxe-to-other ratio in ready states, and the ready-state `wpick` share stayed low (2 to 6% seed 200, 8 to 13% seed 201, labeller 100%), so conflict is still alive; but seed 201 rose anyway, so the conflict reading does not explain everything. Why seed 201 rose is **untested**; the two seeds differ from the start (A28 census, round 16: seed 201 had 684 ready-state visits and seed 200 420), so a seed effect is as likely as a rule effect and two seeds cannot tell them apart.

**What this leaves.** Shown: rare-row starvation is not the whole wall at this scale (the same result as the stopped A26 loop, with a small partial lift on one seed). Suggested: the wall also includes the ready-state label conflict (the model sees `do` and `wsword` rows in the same state and picks them about 90% of the time). Untested: anything about a different label rule on the model's own states. The next candidate remains the one-step lookahead instrument, GW-O (A29, marks `game/A29-GWO-MARKS.md`, code ready and tested). It is on hold: Ben's handover (10-15) says no new runs without a Muse packet, so it starts only when one arrives.
