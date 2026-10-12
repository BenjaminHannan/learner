# Addendum A17 (2:07 AM ET 10-12): GW-B, does the untrained parent read the view at all?

Written 2:07 AM ET 10-12, before any GW-B number exists. Commit time = seal (the shared folder is unreadable tonight).
GW-P8 (A15/A16) is not changed by this.

## Why
The untrained parent, sampling its own odds at T0 (~20), scores 3.75 / 3.61 unlocks a game on the sealed maps, far above random play
(2.31) and above every copy loop (3.28-3.50). Outside opinions (Fable 5.1 and Opus 5.5 via the API thread, 10-12) suggest this is a
word-length artefact, not view reading: a move word's score is the SUM of per-letter log-probs plus EOS (game/play.py
`_chunk_logprobs`), so short words such as `do` (Crafter's most useful move) are favoured whatever the view says.
Shown from the code: the sum is not length-normalised. Untested: whether that, rather than the view, drives the 3.75.

## The test (one change: the view is ignored)
- q-bar = the parent's mean move distribution, softmax(log-probs / T0) averaged over the views it met in its own night-0 quiz of the
  GW-P8 cloud run (quiz worlds 3,000,000+, never sealed). T0 = the one in the Before file (s200 19.691660968372133; s201 as recorded).
- Blind arm: on the same 100 sealed maps with the same act seeds [7, k], the same 10% explore and the same per-episode sample stream,
  every move is drawn from q-bar, ignoring the view (`game.score --arm blind --probs Q.json`).
- Before_T0 = the existing cloud files before-T0-s200.json / before-T0-s201.json. Random = random.json (2.31).
- View dependence: mean over those views of KL(q(.|view) || q-bar), in nats.
- Difference and 95% interval: game.analyze's paired bootstrap over the 100 maps (Before_T0 minus Blind).

## Marks (from the API judge, adopted unchanged)
| Mark | Says "artefact" (pass) | Proved wrong (the parent reads the view) |
|---|---|---|
| B-1 | abs(Before_T0 - Blind) <= 0.3 on both seeds AND mean KL < 0.05 nats on both seeds | Before_T0 - Blind >= +0.5 with interval low > 0 on both seeds |
Anything else: no verdict, reported as is. No hair-miss allowance (this is a control, not a method screen).

## What each outcome means for the plan
- Artefact: the parent's head start, and GW-P's gain over the copy loops, come from a move habit; the next test is GW-PC (distil the
  T0 parent to T = 1, then learn at T = 1), with its own marks.
- Proved wrong: the parent's odds carry view information at T0; the T0 starting point stays, and the judge's temperature point
  (T0 ~20 shrinks each night's policy step) is the next thing to test.

## A17b (2:12 AM ET 10-12, still before any GW-B number): also read view dependence at T = 1
A note from the same API thread (Fable 5.1): at T0 ~20 a mean KL below 0.05 nats is nearly guaranteed by the temperature itself,
so B-1's KL part could pass for the wrong reason. B-1 is unchanged; reported next to it, not marks:
- mean KL(q(.|view) || q-bar) at T = 1 on the same views and log-probs (`mean_kl_t1`);
- how often the top word is the same across views (`top_share`, the most common top word's share; `top_counts` per word).
Reading: low view dependence at T0 but high at T = 1 means "the temperature hides the view", not "a word-length habit". Both T0
values are the Before files' own (s200 19.691660968372133, s201 20.368329685910396; the cloud GW-P8 runs reproduce them exactly).
Code: game/blind.py (fit), `game.score --arm blind`; views = runs-local/gwp8-s20X/moves/quiz_night_0.jsonl.gz of the cloud runs.

## Result (2:35 AM ET 10-12): B-1 says "artefact" on both seeds (shown)
| seed | Before_T0 | Blind | Before - Blind (95%) | mean KL at T0 | mean KL at T = 1 | top word the same | Blind - Random (95%) |
|---|---|---|---|---|---|---|---|
| 200 | 3.75 | 3.78 | -0.03 (-0.33 to +0.23) | 0.029 | 0.051 | 97.8% of views | +1.47 (+1.17 to +1.77) |
| 201 | 3.61 | 3.67 | -0.06 (-0.38 to +0.24) | 0.022 | 0.056 | 98.4% of views | +1.36 (+1.08 to +1.66) |
Views: 5,849 / 5,327 from the night-0 quizzes. The habit: s200 `do` 60%, `up` 23%; s201 `do` 53%, `up` 28%; every other word <= 4%.
`do` and `up` are the only two-letter words of the 17.
- Shown: the untrained parent at T0 does not use the view; a fixed habit with the same odds scores the same on the sealed maps,
  and the top word is `do` on ~98% of views even at T = 1, so this is not the temperature hiding a view-reading policy.
- Suggested (not tested): the habit comes from the unnormalised letter sum favouring two-letter words.
- So GW-P's After (3.87 / 3.97) is only +0.09 / +0.30 above a view-blind habit. Next, as planned in A17: GW-PC (distil the T0
  parent to T = 1, then learn at T = 1), marks written before it runs, after GW-P8 reads out. Files: game/results/gwb-RESULT.json.
