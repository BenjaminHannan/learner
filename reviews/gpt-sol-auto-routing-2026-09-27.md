# Sol task: one reasoner that keeps old skills and decides the skill for itself (2026-09-27)

For GPT-6 Sol working in this repo on Ben's Mac (Codex). You can read the repo and use the Mac's GPU (MPS). Written by the Thread manager for Ben. Ben's words, 11:34 UTC: "It should for each request be able to automatically decide what."

## Why your last result doesn't count for the build
Your R2 (artifacts/codex-retention-20260927/r2/RESULTS.md) kept grids at 200/200. It did that by keeping a frozen copy of the whole model per skill and having the caller name the skill. Ben has ruled that out. The model must decide for itself from the request, with no task ID, no per-skill snapshot and no hand-written rule. R2 stays on record as a yardstick only.

## The problem (small puzzle nets only)
- The net is the project's small dense loop reasoner: 1,646,750 weights.
- It learns three kinds of puzzle in order: A grids5, then B sums4, then C maze7. The code is scripts/claude_rsn358e4_replayall.py and its sealed imports.
- The best recipe so far is dense plus full replay of earlier kinds: 250 grids batches in B, and 75 grids plus 75 sums batches in C. It still forgets.
  - Grids5 falls from 196.50 after A to 128.00 after C.
  - T = grids5 + sums4 + maze7 after C, out of 600. Its mean is 470.17 over seeds 3-8.
  - On the two old kinds alone (grids5 + sums4 after C, out of 400) it keeps 319.83. So the real gap is the first kind: 128 of 200 against about 197 learned. The frozen experts in 358e4 kept grids at 164.33 but learned the new kinds badly. Source: run/blind-recount-output.txt, Means.
  - Source: artifacts/claude-rsn358e4-20260927/RESULTS.md, on its dev set.
- Three expert layouts at equal size all did worse on T: rsn-358e4 (240, proved wrong for that recipe), 358e5 (252) and 358e6 (321). Read their RESULTS.md files, and design/v3/30-modes/ben-goals-2026-09-26.md, before choosing.
- Goal: one network of the same total size, fed a mixed stream of requests from all three kinds with nothing but the puzzle itself. It should keep grids5 near its level after A and still learn sums4 and maze7 as well as dense plus replay does. Any gate, router or context signal must be learned from the input.

## Rules (hard)
- Work only in a new folder, artifacts/codex-autoroute-20260927/, and in new scripts. Never touch repo-root notebook/. Never edit another thread's files, handoff/queue, handoff/held, the watcher, or anything on BensPC. Never stop a process you did not start.
- Training data is generated and checked by code only: no Claude-, Luna- or other model-written text. No blind panels. Use fresh panel seeds that appear nowhere in the repo (grep first), and record them.
- No model downloads and no money. The 1B chat model is out of scope for this task.
- Before each GPU run, check that nothing else is using the Mac GPU. Run one GPU job at a time.
- Same size: within 1% of 1,646,750 weights in total, counting any gate or router.
- A PASS is evidence only. Only Ben approves a design for the build (design/v3/30-modes/ben-goals-2026-09-26.md:96).
- Replay of earlier kinds' code-made practice is allowed, and brain-like tricks such as sleep replay, context gating or slow and fast weights are welcome. Keep the total replay batches and training steps within 10% of dense plus replay, and report the minutes.
- One change per experiment. Before any run, commit and push a PASSMARKS.md with the marks, the predictions, and the result that would prove the idea wrong. Commit to main with pull --rebase: no PR, no force push. Pushed marks are never changed; an addendum can only add to them.
- Run the dense plus replay baseline yourself, on the same machine with the same seeds and panels. Don't reuse the cloud numbers as the comparison.

## Suggested marks (tighten them if you like, before any run)
Use 6 seeds. Keep two sets of code-made panels: a design panel you may look at while developing, and a sealed panel per registered run, made from a fresh seed after its marks are pushed and read once. Use 200 items per kind. Score by exact correctness at the model's own stop. Every test item comes from a shuffled mixed stream with no label.
- M1 keep: mean grids5 after C is at least 180, and every seed is at least 160. This is a stretch bar. Only one dense plus replay seed (172) clears 160, and no same-size net here has met it (358e4 kept 164.33 on average, and 358e5 kept 161.50, but both barely learned mazes).
- M2 learn: mean sums4 after B is at least 195, and mean maze7 after C is at least dense plus replay's maze7 minus 10.
- M3 overall: mean T is at least dense plus replay's T + 40, and T is higher on at least 5 of 6 seeds.
- M4 no leak: the model never receives the kind label, at test or as a training target for any gate or router. Ben ruled out being told the skill (11:34 UTC). If you think a design needs kind labels in training, stop and write that up as a question for Ben instead of running it. Report routing agreement with the true kind, report only.
- Proved wrong: mean T at or below dense plus replay's, or mean grids5 after C at or below dense plus replay's.

## What to hand back
- For each experiment: RESULTS.md with the verdict in the marks' own words, per-seed tables, a recount script, and the claims labelled shown, suggested or untested.
- Keep the small puzzle nets separate from the 1B chat model and the joined build. Don't claim anything about either.
- End with a plain-language summary for Ben, a high-school senior: what was tried, what happened, and what it means.

## Note added 2026-09-27 12:16 UTC (Thread manager)
The baseline numbers above (470.17, 319.83, 128.00, 164.33, 161.50 and the 180 stretch bar) all come from nets that were given the puzzle kind as an input (scripts/claude_rsn358a_run.py:97,172; INPUT-AUDIT.md). AR1 reruns its baseline without that label, which is the fair comparison.
