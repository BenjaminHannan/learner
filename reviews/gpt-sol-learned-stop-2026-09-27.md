# Sol task: let the thinking loop learn when to stop (2026-09-27)

For GPT-6 Sol working in this repo on Ben's Mac (Codex). You can read the repo and use the Mac's GPU (MPS). Written by the Thread manager for Ben. Run it after your current tasks (numbers, auto-routing), one GPU job at a time.

Ben asked for a problem no one is working on yet. This one was checked against every open line: 358t keeps the hand rule below (scripts/claude_rsn358t_run.py:23), and learned stopping appears only on a backup list (artifacts/claude-rsn358i-20260926/EXIT-RULE-ADDENDUM-1.md). Sleep research owns carry-over (358x), depth (358t, 358y) and fact cards (358k). Don't overlap them.

## The problem (small puzzle nets only)
The project's reasoner is a weight-shared loop: 2 layers applied again and again, up to 48 rounds at test (scripts/claude_rsn358a_run.py:40-41). After every round a small stop head guesses whether the current answer is fully right. It is trained with a binary cross-entropy loss against "exact right at this round" (claude_rsn358a_run.py:292-300).

**How it stops today is a hand-written rule** (scripts/claude_rsn358a2_run.py:27-29, "v2"): stop at the first round from round 3 on where the stop head says p > 0.5 **and** the answer is the same as in the two rounds before. If that never happens, answer at round 48.
- The stop head alone (the v1 rule: stop at the first round with p > 0.5) stopped after about 1 round. In one unregistered CPU preview (a smaller loop, 2 x d256, 4,000 steps, sums only, 1 seed, 200 dev items) it got 185/200 on the practised 4-digit sums, against 200/200 by round 4 (claude_rsn358a2_run.py:4-10; artifacts/claude-rsn358a-20260925/preview/preview_sums_4000.json). The "answer unchanged for 3 rounds" guard and the round-3 minimum were added by hand to fix that.
- Ben's goals stop new hand-written stand-ins for thinking and allow one only as disclosed test scaffolding (design/v3/30-modes/ben-goals-2026-09-26.md:36-41). This guard is listed that way, with "learned stop head owed" (design/v3/30-modes/02d-gates-ADDENDUM-24.md:25). This task is that owed replacement, inside the part Ben calls "the model".
- How long the loop thinks also sets its cost. In rsn-358i3 (artifacts/claude-rsn358i3-20260926/VERIFY-recount.md) the loop beat a same-size plain net (sums6 +124.00, grids6 +52.00 of 300, 4 seeds). Its mean rounds under the v2 rule were 7.16-7.85 on sums6 and 10.61-14.13 on grids6, which is roughly 7-14x a plain net's compute per answer (inferred from layer shapes, not measured).
- These nets are also given the puzzle kind as an input embedding (`env`, claude_rsn358a_run.py:78, :97, :172). Ben has ruled that out ("It should for each request be able to automatically decide what", 11:34 UTC 09-27). Drop it in **both** arms, so the kind label is not a second difference.

**Goal:** the net decides for itself when it has thought enough, with no hand-written guard. It should stay as accurate as the v2 rule, think longer on harder puzzles, and not waste rounds.

## Rules (hard)
- Work only in a new folder, artifacts/codex-learnedstop-20260927/, and in new scripts. Build on scripts/claude_rsn358i2_run.py and its imports, the code rsn-358i3 ran (autocast cache off: artifacts/claude-stage0-autocast-20260926/CPU-RESULT.md). Import it and never edit it. Never touch repo-root notebook/. Never edit another thread's files, handoff/queue, handoff/held, the watcher, or anything on BensPC. Never stop a process you did not start.
- Puzzles are generated and checked by code only: no Claude-, Luna- or other model-written data. No blind panels. Don't read other runs' sealed test folders. Make your own panels from fresh seeds that appear nowhere in the repo (grep first), and record them.
- No model downloads and no money. The 1B chat model is out of scope.
- Before each GPU run, check that nothing else is using the Mac GPU. Use float32 on MPS for both arms, with the same torch version.
- Never train or tune on the test panels. Only the design panel may be looked at while developing.
- **One change:** how the net decides to stop, and whatever training its stop signal needs (for example a compute cost, as in PonderNet or ACT, or TRM's halting). Size (within 1% of weights, counting any stop parts), puzzles, steps, batch, learning rate, schedule and the 48-round cap stay the same as the baseline arm. A single fixed number such as a 0.5 threshold is fine if it is written in PASSMARKS.md before any sealed panel exists. Tuning it on a sealed panel, a minimum round count or an "answer unchanged" check is not.
- **Size for the Mac:** rsn-358i3's net (2 layers x d512, 6,438,302 weights, 60,000 steps) took 75-82 min per run on BensPC's RTX 5070 Ti. If that is too slow here, use a smaller loop (for example 2 x d256), the same for both arms, and say so.
- **Baseline first:** train the v2-rule arm (H) first, with no kind input, on your machine and seeds. Before the learned-stop arm runs, H must reach at least 290 of 300 on sums4 and grids5 and at least 200 of 300 on sums6 and grids6 (means over seeds), so there is something to match. If it misses, stop and report. Don't change the task to make it fit. No one has run this baseline without the kind input yet (your auto-routing task replaced it with a learned front end instead: artifacts/codex-autoroute-20260927/PASSMARKS.md:16-20), so missing this gate is a real result to report, not something to tune around.
- Before any run, commit and push a PASSMARKS.md with the marks, your predictions, and the result that would prove the idea wrong. Commit to main with pull --rebase: no PR, no force push. Pushed marks are never changed; an addendum can only add to them.
- A PASS is evidence only. Only Ben approves a design for the build (ben-goals-2026-09-26.md:96).

## Suggested marks (tighten them if you like, before any run)
Arms: H = the v2 hand rule on H's nets; L = your learned stop, no hand guard. 4 seeds each. Practice sums4 and grids5 as in rsn-358i. Sealed test panels of 300 items each for sums4, grids5, sums6 and grids6, made from a fresh seed after the marks are pushed and read once. Score is exact right at the net's own stop.
- M1 as right: L >= H - 5 on sums6 and on grids6, on at least 3 of 4 seeds.
- M2 longer on harder: L's mean rounds are higher on sums6 than sums4, and higher on grids6 than grids5, on every seed.
- M3 no waste: L's mean rounds, averaged over seeds, are no more than H's on sums6 and on grids6.
- M4 no hand rule: L's stop comes from the net's own output alone. Show the stop code in RESULTS.md.
- Proved wrong: L is below H by more than 20 of 300 on sums6 or grids6 on at least 3 of 4 seeds.
- Report only: the v1 rule (stop head alone at p > 0.5) on H's nets; right at any round (the ceiling); sums8, sums10, sums12 and grids7 with rounds used; minutes per run.

## What to hand back
- RESULTS.md with the verdict in the marks' own words, per-seed tables, a recount script, and every claim labelled shown, suggested or untested.
- Keep the small puzzle nets separate from the 1B chat model and the joined build (the "village model"). Don't claim anything about either.
- End with a plain-language summary for Ben, a high-school senior: what was tried, what happened, and what it means for "how long should the model think".

## Changes (2026-09-27, Thread manager, after the coordinator's check)
The 185/200 preview is described as the small one-seed preview it was; the v2 guard is described as disclosed scaffolding with a learned stop head owed (02d-gates-ADDENDUM-24.md:25); added float32 on MPS, "never train or tune on the test panels", and the note that the no-kind-input baseline has never been run. The marks are unchanged.
