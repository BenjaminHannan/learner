# Addendum A22 (7:58 PM ET 10-13): can the 3M model read the map at all? A labelled-views capacity probe (GW-L)

Written before any number exists. Commit time = seal. Ben (7:47 PM ET 10-13 app message): "for the next candidate i don't care which one -
decide for yourself and go with it". This is the pick, with the reason the standing default (the sheet twin) was not taken.
Labels: **shown** = measured or read in code; **suggested** = reasoned; **untested** = not run.

## The pick, and why not the three held candidates (pros / cons / verdict)
| Candidate | Pros | Cons (evidence) | Verdict |
|---|---|---|---|
| Sheet twin of GW-P8's method | It is the standing rule for a game win | Shown from the code: a sheet answer comes from a chain of calculator calls the model writes digit by digit (op head + pointer writers, `custom_io/models/tool.py`), so a policy-gradient night needs new sampling and log-prob code over that chain, not the 17-word scorer. Shown: the sheet parent scores 2.14% (v2 panel near), so rewards are rare at the start (cold start). Shown (A21): about half of GW-P8's gain is a move habit, so there is no reading-the-map win yet to twin. A null would not tell "game-only" from "cold start" | Don't, for now. Revisit when a game method shows map reading |
| 6-seed confirm of GW-P8 | Would turn a screen into a confirm | Shown: about 10 h of Mac a seed pair, the Mac slept once; only parents 200 and 201 exist. A confirm of "+0.4 over an untrained habit" would not change what we do next | Don't |
| Opus's learning-rate arm | One knob | Suggested by GW-PC (A20, A21): the clip, not the temperature, set the step; more movement was already reached and did not help | Don't |
| **GW-L (this file)** | Splits the two live explanations for the plateau at about 4.2 unlocks: (C) the 3M model with a rank-8 add-on, read through the 17-word scorer, cannot hold a map-to-move rule; (S) it can, and 87,000 sparse-reward moves are too few to teach it. Free cloud CPU, a few hours. Either answer picks a different next step | A hand-written labeller stands in for a perfect teacher (allowed as a teaching label by the no-hard-coding rule, 10-07; lives only in the test harness; its checkpoints are never a parent and never enter the model) | **Do** |

## The test
- **Question.** Given the right move for a view, can the 3M model learn to give it for views from maps it has never seen?
- **Students.** Parents T1SDR 3M seeds 200 and 201 (the same two as every GW run). Rank-8 add-on (`domain.mode.AddOn`, rank 8, alpha 16, 135,488
  numbers; base frozen), read through the same 17-word scorer as GW-P (`play.move_logprobs_grad`). One change from GW-P8: the night is
  supervised (cross entropy of the labelled word under softmax of the 17 word log-probs, T = 1) instead of reward-driven.
- **Labeller (`game/oracle.py`).** A pure function of the view text O(view) -> (word, reason), reason in {nav, act, craft, sleep, wander}.
  It reads only the 9x7 map, the stats and the items; it never touches a world, a seed or the sealed range. Its priority list is written in its
  docstring (asleep -> sleep; adjacent zombie -> face/attack; drink or food low and water/cow in view -> go and drink/eat; craft by the items
  and a table in reach: place table (2 wood), wood pickaxe, wood sword; sapling in hand and grass faced -> plant; fewer than 4 wood -> nearest
  tree; wood pickaxe in hand -> nearest stone; otherwise wander = keep going the way it faces, else turn to the next walkable side). Movement
  labels are the first step of a shortest path over walkable cells (`.`, `:`, `_`; creatures and everything else block) to a cell next to the
  target; a move into a blocked target cell only turns the player, so "target adjacent, not facing" is the move toward it and "adjacent and
  facing" is `do`. Crafter rules read from its `data.yaml`.
- **Data (`game/probe.py gen`).** Practice worlds only: run seeds 390 (train) and 391 (held-out), never a quiz, practice or sealed world of any
  earlier run. Each step the episode takes the labeller's move with chance 0.5, else a uniform random move; every visited view is recorded with
  its label. Exact duplicate views are dropped within a set, and held-out views that also occur in train are dropped. Train sizes N = 1,000,
  4,000, 16,000 (prefixes of one fixed shuffled list, so nested); held-out = 2,000 views.
- **Training (`game/probe.py train`).** Fixed before any run, never tuned: Adam lr 1e-3 (the add-on rate of domain mode), minibatch 256, gradient
  norm 0.5, fresh optimiser, epochs 40 / 20 / 10 for N = 1k / 4k / 16k, seed = parent seed. No early stopping, no picking of the best epoch.
- **Held-out reading (`game/probe.py eval`).** Top-1 accuracy on all 2,000 held-out views and on the map-dependent subset S (reason nav or act);
  the best fixed word's accuracy on the same views (the most common label of the training set, ignoring the view); the untrained parent's and
  the GW-P8 night-8 checkpoint's accuracy; accuracy per label word.
- **Sealed play (`game.score --arm model --picker sample --temp 1.0`, and `--picker top`).** 100 sealed maps, act seed [7, k], explore 0.10 from
  `game/constants.json`, as every GW arm. Also the labeller itself under the same act rule (`game.score --arm oracle`, the ceiling for this act
  rule). The sealed worlds are played only by `game/score.py`.
- **Machine.** Free cloud CPU only (4 cores, 3 threads a job); a background waiter stays alive while the jobs run. No Mac, no PC, no money.

## Marks (each of seeds 200 and 201)
| Mark | Pass | Proved wrong |
|---|---|---|
| L-1 reads the map | at N = 16,000, held-out accuracy on subset S minus the best fixed word's accuracy on S >= +20 points | < +5 points on both seeds |
| L-2 turns reading into play | at N = 16,000, sealed unlocks a game (sampled, T = 1) minus GW-P8 After (4.15 for seed 200, 4.19 for seed 201) >= +1.0, paired 95% bootstrap interval low end > 0 (`game.analyze`) | <= +0.3 on both seeds |
Anything else on a mark: no verdict, reported as is. No hair-miss allowance (a capacity probe). Both seeds must meet L-1 and L-2 to pass.
Reported, not marks: **L-3 label cost** = the smallest N in {1,000; 4,000; 16,000} at which L-1's +20 holds, per seed (for scale, GW-P8 saw about
87,000 moves with sparse reward); the top-picker sealed play; held-out accuracy on all views; the untrained parent's and GW-P8's held-out
accuracy; the labeller's own sealed score; achievement shares; per-word accuracy.

## What each outcome means, and the pre-registered next step
- **L-1 pass and L-2 pass.** The model can learn map-to-move links; the plateau is the signal. Next (its own marks): a learned way to make
  labels without a teacher, for example labelling the moves along a path the model itself finished (hindsight) or a denser learned reward.
- **L-1 pass, L-2 not passed.** It can name the right move for a view but play does not follow (states it reaches that the labelled mix did not
  cover, or a low labeller ceiling: read the labeller's sealed score first). Next: the same labels gathered on the student's own states
  (DAgger style), its own marks.
- **L-1 proved wrong on both seeds.** Run once the whole-brain version (seed 200, N = 16,000, every weight trains, lr 1e-4 as domain nights),
  mark: held-out accuracy on S minus best fixed word >= +20 passes, < +5 proved wrong. Also wrong -> at 3M with this scorer the game cannot
  be learned even with perfect labels; park the game loop until the 10M / B3 models exist.
- **Anything between.** No verdict; one more run at N = 64,000 on seed 200, then read again.
