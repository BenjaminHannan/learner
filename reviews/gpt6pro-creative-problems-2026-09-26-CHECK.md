# Check of GPT-6 Pro's answer to gpt6pro-creative-problems-2026-09-26.md (creative thread, 2026-09-26 ~01:10 UTC)

Ben pasted the answer in the Sleep research thread (00:51 UTC). Each factual claim below was checked against our code and run files.

| GPT claim | Check | Verdict |
|---|---|---|
| E kept the same won puzzles as W, so the loop's job of FINDING useful problems was not removed | claude_blurt5s.py: `ewins = [(p, solver_target(p, h)) for p, h in wins]` | Correct. Only the answers changed. |
| The rule keeper masks illegal tokens, so "learned the format" can't explain constrained gains, and blurts exclude "none" | claude_blurt2.RuleKeeper adds −inf to disallowed tokens; ask-24 blurts use allow_none=False | Correct |
| Every test puzzle gets 30 samples, not only greedy misses | claude_blurt5s.coverage_stream and claude_blurt2.luck sample all test puzzles | Correct. Coverage is well defined. |
| C's lucky samples are concentrated (about 17-22 per covered puzzle) | blurt-5s: C 237/14, 238/12, 237/11 gives 17-22; base 167/77 gives 2.2 | Correct |
| v+1 is a weak placebo, because it keeps a consistent numeric relation | claude_blurt4.py: `wt = v + 1 if v < VMAX else v - 1` | Correct. A shuffled-target placebo would be cleaner. |
| Padding raises updates per unique example | blurt-4: W was 185 unique examples repeated to 560, 3 epochs | Correct. So W's exposure differs from blurt-3r's (unpadded). |
| The judge's three seeds differ in data, not in initialisation | claude_feas24b.py: each seed trains on a different 85% subset; Newton fit is deterministic (the recount matched exactly) | Correct. Seeds are data resamples. |
| Reframing excludes fractional/negative/zero/>200 subtargets and balanced 2+2 splits | claude_reframe5.reframes(): whole targets 1..200, drop-one only | Correct, but it matters little. The oracle ceiling (below) shows the pieces can reach 52/52 three-number and 25/27 four-number test puzzles. The restriction is not what failed; generation or allocation is. |
| "Re-analyse the already-recorded A/B yes/no scores" | ask24ab_summary.json stores only totals, not per-hand scores | Not possible as stated. I re-scored the same frozen model on the same panel (diagnostic only; the registered verdict stands). Result: see the A/B line below. |
| Test B: "evaluate the exact padded-W checkpoints from the hindsight run" | claude_blurt4.py saves no adapters ("the run saves none") | Not possible as stated. B would need retraining, which is a new run. |
| Test A: "use archived base/W checkpoints from experiment 1" | claude_blurt5s.py saves no adapters | Not possible as stated. tgt-5 retrains W with the same recipe inside the run. |
| 165 unordered 3-number hands from 1-9 | C(11,3) = 165 | Correct |
| 458/1,820 = 25.2% of 4-card hands impossible | our selftest count | Correct |
| enable_thinking=False per the official example | Solver.prompt uses apply_chat_template(..., enable_thinking=False); the rendered prompt shows an empty <think></think> block | Correct |
| Papers cited: On-Policy Distillation (2306.13649), HER (1707.01495), LM self-evaluation (2207.05221), Codex pass@k (2107.03374), STaR (2203.14465), EvalPlus (2305.01210) | Known papers with those arXiv ids | Plausible. The abstracts were not re-read here. |

Oracle ceiling for reframe-5 (code only, no model): of the 79 test puzzles, 52/52 three-number and 25/27 four-number
have a solution reachable through at least one permitted sub-puzzle. Plain solved 7 four-number puzzles and reframe
solved 5, so the pieces were available and the model did not find them within about 2-3 samples per piece (11.9
pieces per four-number puzzle on average).

A/B yes-probability ranking (diagnostic, not a verdict; the same frozen model and seed-790 panel as ask-24ab,
artifacts/claude-ask24ab-20260925/rescore/): GPT's alternative ("useful scores under the threshold") does NOT hold.
The yes-share of the two letters ranks solvable above impossible hands with AUC 0.539 (AB1) and 0.455 (AB2), about
chance. It ranks the solvable twin higher in 66/120 and 52/120 matched pairs. The mean yes-share is 0.643 vs 0.642
(AB1) and 0.634 vs 0.636 (AB2), and every hand sits between 0.59 and 0.68. So the frozen 1B carries no usable
solvability signal in this answer, not just a badly placed threshold.

Adopted from the answer:
- Next test: GPT's A ("does sleep make the model match answers to their own targets?"). It scores fixed strings, so it
  needs no sampling on the test side. It is registered as tgt-5 (a rental, because W must be retrained).
- "Can't" comes from exact code on puzzles. Later tasks should separate "no solution exists", "I didn't find one in
  budget" and "I need information from you".
- The judge stays a research result. Exact code does the operational checking on these tiny states.
- Future panels: fix the eligible test set BEFORE registering, so none of it drops after registration (blurt-5s went
  240 → 184).
Not adopted now: B (it needs retrained padded-W checkpoints; later) and C (the scrambled-target placebo; after A).
