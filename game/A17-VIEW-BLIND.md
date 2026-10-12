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
