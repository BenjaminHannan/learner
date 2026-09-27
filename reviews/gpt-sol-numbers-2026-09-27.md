# Sol task: teach the small reasoner the number puzzle (2026-09-27)

For GPT-6 Sol in Codex on Ben's **M3 Pro** Mac. You can read and push to this repo and use that Mac's GPU (MPS). This is a different Mac from the one running the auto-routing task (artifacts/codex-autoroute-20260927/). Leave that task and its folder alone. If the repo is not on the M3 Pro yet, clone it first. The Thread manager wrote this for Ben on 2026-09-27. Every number below was checked against the repo.

## The problem (small puzzle nets only)
- **The puzzle.** Use each given number once, with + - * /, to hit the target (the 24 game). It is the "numbers" kind in scripts/claude_rsn358a_envs.py:11-14 and :218-315. The grid has three rows: row 0 holds the numbers, row 1 the target, and row 2 the answer slots in postfix (2k-1 tokens for k numbers).
- **The data.** Practice is 3 numbers (1-9, targets 5-40) and 4 numbers (1-13, target 24). The practised-size test is 300 held-out 4-number hands (split seed 35801, `split_four`). The bigger test is 5-number hands with target 24 (`five_hands`). Counted with `number_hands()` and `split_four()` on main:
  - 1,362 solvable 4-number hands in total: 1,062 for practice, 300 held out;
  - 1,346 solvable 3-number hand and target pairs.
  So the practice pool holds only about 2,400 distinct items.
- **Grading and target.** The checker accepts **any** valid expression (`check_numbers` calls `claude_blurt1.check`). Training, though, uses **one** stored solution per hand: the first one `claude_blurt1.solve` finds.
- **What happened so far.** rsn-358i3 trained on sums, grids and numbers together. Setup: BensPC, torch 2.11, seeds 5-8, 60,000 steps, batch 256. The loop net was 2 x d512 and the plain net 8 x d256, about 6.4M weights each. Raw files: origin/builder-outbox:artifacts/claude-rsn358i3-20260926/runs/*/tests.json. Summary: artifacts/claude-rsn358i3-20260926/VERIFY-recount.md:5,37.
  - numbers4 (the 300 held-out hands) scored 2, 5, 1, 0 for the loop and 1, 1, 2, 1 for the plain net.
  - numbers5 scored 0 of 300 for every run.
  - In the same runs, sums4 was 300 and grids5 was 298-300.
  - Training exact at step 60,000 was 1.0 on numbers3 and numbers4 for both arms (train_log.jsonl). So both nets learned their practice hands by heart and solved almost no new ones. rsn-358a showed the same pattern (artifacts/claude-rsn358a-20260925/VERIFY.md:44-48). That this is memorising is suggested, not tested.
  - All of these nets were given the puzzle kind (next point), so every number above comes from kind-labelled nets.
- **An earlier fix that did not work: rsn-358d** (artifacts/claude-rsn358d-20260926/VERIFY.md). It gave both nets a much bigger number pool (75,972 puzzles). The plain net rose to 16 and 10 of 300 held-out hands. The loop net learned nothing on numbers4, even in training, and its other kinds fell badly. The verdict was INCONCLUSIVE. Caveat: 358d's loop trained on a torch 2.8 rental before the autocast-cache fix, so it was possibly hit by that bug (artifacts/claude-rsn358i2-20260926/PASSMARKS.md:32). So whether the loop's collapse came from the bigger pool or from the bug is untested. Don't repeat 358d unchanged.
- **No fresh 4-number hands.** Only 1,362 four-number hands to 24 exist (1-13), and every one is already a practice or held-out hand. So a sealed test must use 5 numbers, or other targets.
- **A kind label you must remove.** The net is told the puzzle kind. `R.tensors` sets `env` from the batch's first item (scripts/claude_rsn358a_run.py:172), and `Net.embed` adds it to every token (:97). Sol's earlier audit found this (artifacts/codex-autoroute-20260927/INPUT-AUDIT.md). Ben ruled out caller-given skill labels (11:34 UTC): "It should for each request be able to automatically decide what." So feed every arm the same fixed env for every item (the conservative option in INPUT-AUDIT.md), and rerun the baseline that way.

## The goal
The small learned reasoner should solve number puzzles it was never trained on. Ben's goals page says the reasoner is the model and reasoning comes first (design/v3/30-modes/ben-goals-2026-09-26.md:29,33,75). Solving new hands likely needs trying options and backing up. That is our reading, untested, and the loop net has not shown it.

**Brain first** (goals:61): start by asking how a person solves the 24 game. A person tries a pairing, checks the partial result against known facts (3 x 8, 4 x 6, 12 + 12), and backs up when a branch fails. Write that down before choosing a change. The brain comparison is a guess, not a claim.

## Step 1: diagnosis (report only, before any registered run)
- Find out why neither net carries over to new hands. Start with the likely causes:
  - It memorises the ~2,400 practice items. Training exact 1.0 against 0-5 of 300 held out suggests this; confirm it on your own baseline.
  - One stored answer is used as the target when many answers are right.
  - It has no way to try options and back up.
- Small diagnostic runs on code-made data are allowed. Label every finding shown, suggested or untested. Commit the diagnosis note before Step 2.

## Step 2: one change, registered first
- **The change.** Pick ONE change that the diagnosis supports. Examples, none prescribed:
  - training on every valid answer (the solver can list them, which makes them code-checked labels);
  - more varied practice, such as 4-number hands with other targets;
  - a learned way to keep and revise partial results;
  - sleep-style replay.
  The answer at test time must come from the net. There must be no search code, solver call or hand-written rule at inference; goals:37 stops hand-written reasoners and rule gates.
- **Arms.** Baseline = the 358i3 loop recipe, rerun by you on the M3 Pro with the fixed env. Candidate = the baseline plus your one change. Same weights within 1%, counting anything added. You may shrink the net or the steps to fit the M3 Pro, but both arms must use the same settings. Report the minutes for each run.
- **Kinds.** Train both arms on sums, grids and numbers together, as 358i3 did, so that "no harm" means something.
- **Seeds.** Use 4 or more training seeds, paired across the arms. Grep the repo first to confirm each seed is fresh, and record them.
- **Before any run,** commit and push PASSMARKS.md with the marks, your predictions, and the result that would prove the idea wrong. Pushed marks never change. An addendum can only add.

## Suggested marks (tighten them before any run if you like)
- **Panels.**
  - Design panel: you may look at it while developing. Use the old 300 held-out 4-number hands (seed 35801, already scored in 358i3).
  - Sealed panel: 300 fresh 5-number hands (`five_hands` with a new seed, drawn after PASSMARKS is pushed), read once.
  - Score by exact validity at the model's own stop, with the existing checker.
- **N1, practised size:** the candidate's mean on the 300 held-out 4-number hands is at least 100, and it beats the baseline by at least 60 on every seed.
- **N2, bigger:** the candidate's mean on the sealed 5-number panel is at least 30, and it beats the baseline on at least 3 of 4 seeds.
- **N3, no harm:** the candidate's mean sums4 and grids5 are each within 5 of the baseline's mean, and no seed falls more than 10 below its paired baseline seed.
- **N4, no label:** every item gets the same env in both arms. Include a software test: the outputs must be identical when the hidden kind field is changed.
- **Proved wrong:** the candidate's mean on the 300 held-out 4-number hands beats the baseline by 10 or less.

## Rules (hard)
- **Where you work.** Only in a new folder, artifacts/codex-numbers-20260927/, and in new scripts. Never touch repo-root notebook/. Never edit another thread's files, handoff/queue, handoff/held, the watcher, anything on BensPC, or your auto-routing folder.
- **Processes.** Never stop a process you did not start. Before each GPU run, check that nothing else is using the M3 Pro's GPU. Run one GPU job at a time.
- **Data.** Training data is made and checked by code only: no Claude-, Luna- or other model-written text. No blind panels from other threads.
- **brd-11.** The Creative thread's brd-11 tests the 1B chat model on make-24 puzzles (queued as handoff/queue/176-creative-brd11pc.md), and its panels are blind. Never open any file in artifacts/claude-brd11-20260926/. Your 5-number sealed panels are yours.
- **Money and downloads.** No model downloads and no money. The 1B chat model and the joined build are out of scope.
- **Usage.** Keep Ben's rule: stop if your usage falls under 20% remaining.
- **One change per experiment.** Commit to main with pull --rebase: no PR, no force push.
- **Approval.** A PASS is evidence only. Only Ben approves a design for the build (goals:96).

## What to hand back
- **For each experiment:** RESULTS.md with the verdict in the marks' own words, per-seed tables, a recount script, and every claim labelled shown, suggested or untested.
- **Scope.** Keep the small puzzle nets separate from the 1B chat model and the joined build. Claim nothing about either.
- **For Ben.** End with a plain-language summary for Ben, a high-school senior: what was tried, what happened, and what it means.
