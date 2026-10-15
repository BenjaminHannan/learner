# A26 (9:22 PM ET 10-14): GW-F, learn from the model's own fastest stretches between achievements (the outside answer, with my checks) and its marks, fixed before any code ran on a game

## The outside answer (Fable 5.1, effort xhigh, Message Batches, batch msgbatch_017wBcrHwsMkYKQNEQ16scJU, 9:10 to 9:18 PM ET 10-14; 3,372 tokens in, 26,871 out; **cost $0.69**)
Prompt: `reviews/gpt-diagnose-labels-2026-10-14.md` (stand-alone, with all GW-L sizes, the search result and the question "is there a learned, deployable way past the long-chain wall that does not need the 10M learned drive first?").
Full answer: `/mnt/project-files/api-opinions/answers/fable-chain.md` (thinking summary beside it). Its claims are hypotheses; I checked the ones that decide the plan against the code and my own files:
- **Checked, true:** each link of the chain is a +1 reward of its own (collect_wood, place_table, make_wood_pickaxe, collect_stone): crafter's step gives +1.0 when a not-yet-unlocked achievement has a count above 0 (`crafter/env.py`, `step`), the player's per-achievement counter goes up **on every repeat** (`crafter/objects.py`, lines ~229, 249, 261), and `info['achievements']` hands the counters back every step (`game/play.py` reads them). So **my own wording "nothing pays off until the end of the chain" (A25 and the reply to Ben) was wrong**: each link pays, but only after the walk to it and only if the previous link happened. The wall is the unrewarded walk between links and the rarity of each prerequisite (the product of small chances), as Fable says. Corrected here.
- **Checked, true:** the old copy rules had no speed filter and no rarity weighting (`game/mode.py`, `keep_windows`: the last 8 moves before each **first** unlock, non-overlapping; variants: awake-only, learned guess). No variant used repeat increments.
- **Checked, partly wrong:** (1) "the PPO plateau is shown only for <= 90k moves": the PPO network ran to 230k (4.40); the add-on PPO-clipped night ran about 87k moves. (2) "~2M moves a night is feasible": playing yes (about 25 to 60 moves a second), PPO updates on the add-on no (10 s per 256-view update), so a big-budget PPO arm would be the small PPO network, not the add-on. (3) "the search teacher's labels were a random walk on 81 to 91% of steps" mixes two experiments: in SE the shares were 9.1% searched, 80.7% fallback walk and 10.2% the act rule's random move (these sum to 100%); the 81% re-search agreement belongs to SQ's states, where 64 to 70% of views got a label.
- **Not checked / untested:** that fastest-30% segments carry the chain at 3M. That is the experiment.
Pros of the answer: it asks for no hand-written chain, no copy of the world, no second model, no 10M drive; it is cheap on free CPU; it fails fast (a leading indicator at iteration 8). Cons: it is close to the old copy rule plus two filters, so it may reproduce the habit plateau; the pickaxe link starts from about 16 games in 400.

## The change (one): GW-F, iterated fastest-segment self-imitation, replacing the PPO-clipped night
Nothing in the model, add-on rank, scorer or act rule changes (T1SDR 3M parents `glprobe/run/parents/s200.pt` and `s201.pt`; fresh rank-8 / alpha-16 add-on, 135,488 numbers, exactly as GW-L; explore 0.10; episode cap 1000). Code: `game/imitate.py` (new). One loop per seed (200, 201), both run side by side (2 threads each).
**Iteration k = 1, 2, ... (every constant below is fixed here):**
1. **Play** 400 games on practice worlds with the current policy: run seed 394 (seed 200's loop) or 395 (seed 201's loop), day = 4(k-1) + c for c = 0..3, worlds i = 0..99 (never a sealed world). Act stream `default_rng([9, run seed, day, i])`, one uniform and one random action per step, as `game/play.py`. Sampling: **iteration 1 uses the untrained parent at its learned temperature T0** (19.69 for seed 200, 20.37 for seed 201, the temperatures of the 3.75 / 3.61 "Before" arm); **every later iteration samples the current add-on at T = 1**, the way the GW-L students were scored.
2. **Events**: every step where any of the 22 achievement counters goes up (repeats count). One event per (step, type).
3. **Segments**: the moves since the previous event of any type (or since the game's start), inclusive of the event's own move. Row = (view before the move, the move executed); the executed move includes the act rule's random substitutions.
4. **Keep**: for each event type, sort that iteration's segments of the type by length (ties: earlier game first) and take the first ceil(0.3 n); drop any of those longer than 12 moves.
5. **Weight**: w(type) = n^(-1/2) with n = that type's segment count this iteration (before the keep step), then each type's weight raised to at least (largest weight present)/20; a row on several types takes the largest weight; weights are divided by their mean over the iteration's training rows.
6. **Buffer**: kept rows of earlier iterations, with their type and segment length. This iteration, for each type that has a kept segment, buffer rows of that type from segments longer than the longest kept length of the type this iteration are dropped for good. The buffer keeps at most the newest 20,000 rows. Buffer rows keep the weight they were given when they were added (the whole training set is then divided by its mean weight).
7. **Train**: the new kept rows plus a uniform random sample of buffer rows of the same size (all of them if fewer); 3 epochs; weighted cross entropy of the executed word under the softmax of the 17 word log-probs (T = 1); minibatch 256 in chunks of 64, Adam lr 1e-3, gradient clip 0.5; the add-on and the optimiser persist across iterations.
8. Log: games unlocking each of collect_wood, place_table, make_wood_pickaxe, collect_stone (g_wood, g_table, g_pick, g_stone); segments and kept rows by type; mean unlocks a game of the 400 practice games; and, only as an instrument report, the share of kept rows whose move equals the hand-written labeller's on `nav` and `act` views (the labeller is never a teacher here).
The checkpoint at iterations 8, 16 and 24 is saved (merged) for sealed scoring. Resumable after every iteration (the box restarts).
Baselines on the sealed maps (Mac pair counts, A18): untrained parent at T0 3.75 / 3.61 (wood pickaxe 4 / 4%), GW-P8 After 4.15 / 4.19 (3 / 2%). About 16 pickaxe games in 400 are expected at iteration 1.

## Marks (both seeds, 200 and 201; two seeds is a screen; fixed now)
- **Gate A (iteration 8, about 9 h).** Pass: on **both** seeds g_pick(8) >= max(3 x g_pick(1), 40). Proved wrong: on both seeds g_pick(8) < 1.5 x g_pick(1). Anything else: continue to the iteration-16 gate. At iteration 8 the merged checkpoints are also scored on the 100 sealed maps (sample, T = 1): reported, not marked.
- **Gate B (iteration 16).** Pass: on both seeds g_stone(16) >= 10 (of 400 games). Proved wrong: g_stone(16) < 3 on both seeds. Anything else: stop and report, no verdict. A pass continues to iteration 24.
- **Final (the last iteration run, 24 at most): sealed screen, 100 sealed maps, sample T = 1 (`game.score --arm model --picker sample --temp 1.0`), both seeds.** Pass: both >= 5.2 unlocks a game **and** wood pickaxe on >= 25% of the maps on both. Proved wrong: both < 4.6. Otherwise no verdict. A pass is then confirmed only by >= 6 paired seeds against GW-P8, with the view-blind habit control (a fixed habit from the final model's average move odds, `game.blind`, must score >= 1.0 below the model) and the three-number fairness rule where it applies; none of that is part of this screen.
- **Stopping a run for gate A or B proved-wrong is final for GW-F as specified:** it means the model's own fastest stretches do not carry the chain at 3M. Next would be the expert-iteration instrument (a search whose confident steps are imitated) to measure whether any reward-only source bootstraps the chain, with its own marks.
Reported, not marked: practice-world mean unlocks per iteration, g_wood / g_table per iteration, kept rows by type, the instrument report of step 8, sealed scores at iterations 8 and 16, wall-clock per iteration.

## What this can and cannot show
Shown if it passes: a deployable, hand-written-chain-free label source (the game's own achievement counters and the model's own play) lifts a 3M model above the reward-trained plateau. It does not show the model plays well beyond stone, that it transfers to Minecraft, or that it beats PPO given the same moves (the PPO arms in this thread used 87k to 230k moves; this loop plays about 75,000 moves an iteration, so a fair comparison would need a larger PPO budget: untested, noted). It may reproduce the habit (checked by the habit control at confirmation). Two seeds and 100 maps are noisy: the seed spread in GW-L was 0.7 to 0.9 unlocks.

## Pros and cons (before acting) and the verdict
| | Pros | Cons |
|---|---|---|
| GW-F | no hand-written chain, no world copy, no extra model; free CPU; uses only signals the game itself gives; a leading indicator at iteration 8 stops it early; deployable shape (the finished agent is the LM alone) | near to the old copy rule, which plateaued at 3.3 to 3.5; sharpening can kill exploration; the pickaxe link may start from too few events; about 9 h to the first gate, 24 h if it keeps passing; 400 games an iteration is about 75,000 moves, so eight iterations play about 600,000 moves, seven times the 87,000 of the whole PPO-clipped run: a different move budget |
Verdict: do it. Reason: it is the only candidate on the table that is both deployable and cheap, and the first gate is nine hours of free CPU.

## Gate A result (rounds 1 to 8; read 7:16 AM ET 10-15; code commit d8d93de149, nothing changed since the marks; all **shown**)
Per round, games of 400 (practice worlds, the policy's own sampling with 10% random moves; round 1 is the untrained parent at T0). Each round took about 1 h on 2 threads (play about 40 min, training 10 to 22 min).
| round | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| seed 200: games with wood pickaxe | 3 | 3 | 10 | 16 | 12 | 16 | 20 | **1** | 10 |
| seed 201: games with wood pickaxe | 7 | 4 | 5 | 21 | 13 | 19 | 34 | **24** | 25 |
| seed 200: games with table | 70 | 51 | 78 | 86 | 61 | 78 | 96 | 49 | 59 |
| seed 201: games with table | 55 | 44 | 32 | 91 | 81 | 79 | 119 | 113 | 140 |
| seed 200: mean unlocks of the 400 games | 3.73 | 3.28 | 3.65 | 3.81 | 3.68 | 3.82 | 3.84 | 3.31 | 3.56 |
| seed 201: mean unlocks of the 400 games | 3.57 | 3.58 | 3.18 | 3.84 | 3.67 | 3.69 | 4.01 | 4.10 | 4.24 |
Stone games stayed at 0 to 7 of 400 on both seeds (seed 201: 7 in round 9). Kept rows are mostly the cheap events (round 8, seed 201: sapling 1,453, drink 1,506, wood 572, plant 389, zombie 168; wood pickaxe 33 rows, stone 6); the kept moves agree with the hand-written labeller on its `nav` / `act` views 21 to 22% (round 1: 10%; all moves played: 6 to 9%), an instrument report only.
- **Gate A by the marks (round 8): no pass** (needed >= 40 pickaxe games on both seeds; got 1 and 24) **and not proved wrong** (needed both seeds below 1.5 x their round-1 count; seed 201 has 24 against 7). "Anything else: continue to the round-16 gate." Both loops are running to round 16.
- Round-8 sealed scores (100 maps, sample, T = 1; reported, not marked): seed 200 **3.65** (GW-P8 After -0.50, 95% -0.85 to -0.16; untrained T0 -0.10); seed 201 **4.37** (+0.18, -0.19 to +0.57; T0 +0.76, +0.36 to +1.19). Wood pickaxe 2% and 11% of maps, stone 0% and 5%.
- Reading (suggested, untested): seed 201 is climbing (table 55 -> 140 games, mean unlocks 3.57 -> 4.24, round-9 sealed not scored) and seed 200 fell back at round 8 (wood 122: a bad round, partly recovered at 9). Two seeds, 400 games a round and counts of 1 to 34 pickaxe games are noisy; a rise from 7 to 34 and a fall to 1 are both inside what a few lucky games do. Nothing here yet beats the reward-trained level on the sealed maps by the screen's bar (5.2).

## Gate B result (rounds 10 to 16; read 2:20 PM ET 10-15; code commit d8d93de149, nothing changed since the marks; all **shown**)
Games of 400 (practice worlds), rounds 10 to 16 (round 1 is the untrained parent):
| round | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|
| seed 200: games with wood pickaxe | 16 | 16 | 10 | 16 | 16 | 17 | 18 |
| seed 201: games with wood pickaxe | 15 | 27 | 17 | 11 | 24 | 21 | **49** |
| seed 200: games with stone | 0 | 0 | 0 | 2 | 2 | 0 | **1** |
| seed 201: games with stone | 1 | 3 | 4 | 2 | 3 | 1 | **4** |
| seed 200: games with table | 80 | 129 | 91 | 153 | 117 | 120 | 134 |
| seed 201: games with table | 101 | 118 | 163 | 83 | 156 | 168 | 155 |
| seed 200: mean unlocks | 3.70 | 3.92 | 3.75 | 3.92 | 3.85 | 3.85 | 4.00 |
| seed 201: mean unlocks | 3.80 | 3.90 | 4.24 | 3.76 | 4.28 | 4.20 | 4.10 |
- **Gate B by the marks (round 16): no pass** (needed g_stone >= 10 on both; got 1 and 4) **and not proved wrong** (needed < 3 on both; seed 201 has 4). The marks say "anything else: stop and report, no verdict". **GW-F as specified is stopped here, with no verdict.** Nothing is claimed beyond that.
- Round-16 sealed scores (100 maps, sample, T = 1; reported, not marked; the final screen's bars were 5.2 pass and < 4.6 proved wrong, which would apply to the last round run): seed 200 **3.93** (GW-P8 After -0.22, 95% -0.59 to +0.14; untrained T0 +0.18, -0.22 to +0.58; wood pickaxe on 3% of maps, stone 0%); seed 201 **3.93** (-0.26, -0.61 to +0.09; T0 +0.32, -0.08 to +0.73; pickaxe 6%, stone 0%). Round 8 for comparison: 3.65 and 4.37. So after 16 rounds both loops sit at the level of the reward-trained runs (4.15 / 4.19) or a little under it, and far under the 5.2 bar.
- Both loops are on the **table** link and not past it: games with a table rose from 70 / 55 (round 1) to 134 / 155 (round 16), but games with stone stayed 0 to 7 of 400.

## Why it stalls (post-hoc diagnosis on the saved play files; instruments only, not marks; **shown**)
1. **The "pickaxe rule" is barely learned, although the state it needs is reached more often.** A "pickaxe-ready" state: a table within one cell (crafter's `nearby`, 3x3), wood >= 1, no wood pickaxe (the state where the hand-written labeller always says `wpick`). Games that reach one, and how often the moves played in those states were `wpick`:
| | round 1 | round 8 | round 16 |
|---|---|---|---|
| seed 200: games reaching a ready state / games that made the pickaxe | 34 / 3 | 19 / 1 | 55 / 18 |
| seed 200: share of ready-state moves that were `wpick` | 0.3% | 0.6% | 4.3% |
| seed 201: games reaching a ready state / games that made the pickaxe | 35 / 7 | 56 / 24 | 75 / 49 |
| seed 201: share of ready-state moves that were `wpick` | 1.4% | 3.0% | 7.9% |
   The rule is moving the right way but slowly: after 16 rounds the model still plays `wpick` in under 8% of the ready-state moves where the labeller plays it 100% of the time.
2. **The training set has almost no rows for it.** In round 16 the loops kept: seed 200, 7 of 21 wood-pickaxe segments (9 rows) and 3 of 9 stone segments (8 rows); seed 201, 23 of 74 pickaxe segments (24 rows) and 10 of 31 stone segments (10 rows), out of 3,800 to 3,900 new rows a round, of which 1,800 to 2,100 are sapling rows. About 90 updates a round. For comparison, GW-L's 64,000 labels took 2,500 updates to reach 62 to 65% agreement. The keep rule (fastest 30% of each type's segments) discards 70% of the rare events themselves: 17 of 21 and 66 of 74 pickaxe segments are within the 12-move cap, so almost everything that is dropped is dropped by the 30% rule. Seed 201's 74 pickaxe events include repeats (the counter rises on every craft).
3. **Suggested, untested:** the loop is a slow snowball for the pickaxe link (ready-state share and pickaxe games are rising on seed 201), starved by a keep rule that was fixed with common events in mind. Whether the stone link follows is not shown: stone events are 9 to 31 a round.
4. **What it does not say:** that a larger keep share fixes it (the rows would go from about 9 to 24 up to about 17 to 66 a round, a factor of about 3, still tiny next to the sapling rows), that seed 201's 49 in round 16 is more than a lucky round (it is far above its previous seven rounds, 11 to 27, but it is one round on one seed), or that the plateau is not capacity (the GW-L result says capacity is fine when the rows exist).

## Correction (added 3:13 PM ET 10-15, after the outside answer; see game/A28-FABLE-STALL-CENSUS.md)
The Gate B section above says GW-F "is stopped here, with no verdict" and calls the round-16 sealed scores "reported, not marked". Read literally, the marks' final line ("Final (the last iteration run, 24 at most): ... Proved wrong: both < 4.6") applies to the last iteration run, which is round 16: 3.93 and 3.93, both under 4.6. So **GW-F as specified is proved wrong at screen level** (two seeds, 100 maps, the marks' own words); gate B alone was no verdict. The A27 follow-up changes the specification after seeing the data and is a rescue of a falsified run (a screen at best, as its marks say). The text above is left as written; this note is the record.
