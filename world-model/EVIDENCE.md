# PROBLEM-7 evidence: 4 wide layers + DreamerV3-style world model + Minecraft/Bedwars

Worker: PROBLEM-7 (Opus 5.5). Written 2026-11-24. Every line checked against code or a result file named here.
Labels: shown = measured / read in code; suggested = points that way, not proved; untested.
Advisor: the advisor tool was rate-limited at the first call (not advisor-checked yet).

## A. The shape race (4 wide blocks vs tall stack)

A1 (shown, code `premonition_core_v2/board_swarm.py` `BoardSwarmConfig.production`): the production trunk is
16 blocks x d 896, 14 heads, 16 experts top-2, expert hidden 896. Each block = attention over board rows + context,
then a sparse MoE feed-forward. `moe.SparseMoE.forward` training path loops over experts in Python and calls
`counts.tolist()` (one device->host sync per block call).

A2 (shown, 5070 Ti probes, `unsolved-5/5-scale-recipe/RESULT.md` section 1-2): step time is ~21 ms per block x tick
at S/M/L'/L and 26 ms at P, almost independent of width (6.6M -> 48.4M active = 7.3x params, 2.1x step time).
P: 1.686 s/step batch 32, 12.0 GB; 1.401 s batch 16. Achieved 1.9-3.1 TFLOP/s = overhead-bound.

A3 (shown, `PROBLEM-7/shape/counts.json`, meta build of the vendored v2 code, `count_shapes.py`):
| shape | d x blocks | heads | total M | active M |
|---|---|---|---|---|
| S tall | 320 x 6 | 5 | 23.84 | 6.64 |
| S 4-wide | 384 x 4 | 6 | 23.07 | 6.55 |
| P tall | 896 x 16 | 14 | 465.58 | 105.92 |
| P 4-wide | 1792 x 4 | 28 | 467.09 | 107.43 |
Total and active both match within 3.3% (S) and 0.4% (P). The 4-wide shape needs only a SIZES entry; no core edit.

A4 (shown, Mac M1 Pro, shared, fp32, batch 32, 4 ticks, 10 timed steps, AdamW, two repeats each,
`PROBLEM-7/shape/mac/probe_*.jsonl`; harness copy in `~/learner-ops/ds-copies/problem-7/shape-harness`):
| device | S tall step s | S 4-wide step s | wide/tall |
|---|---|---|---|
| MPS | 1.392, 1.228 | 1.183, 1.131 | 0.88 |
| CPU | 2.710, 2.275 | 1.625, 1.698 | 0.67 |
Train peak MPS: tall 2,348 MiB, 4-wide 2,004 MiB. Mac speed does not validate the 5070 Ti (rule), and the Mac
was shared (other workers), so treat these as direction only.

A5 (suggested): if the card stays overhead-bound per block-tick (A2), P 4-wide does 4 block-ticks per tick instead of
16, so a step could drop toward ~1/3-1/4 of 1.686 s, minus the extra arithmetic at d 1792 (each matmul 4x larger).
This is the thing the 5070 Ti ticket measures. Untested.

A6 (shown, BEN-NEON-SESSION-2026-11-23 + VERDICT-LOG line ~672): the ACCURACY half of the race is queued "after
family B passes". Family B is PROBLEM-1's; this worker does the speed/shape half only and does not touch family B code.

A7 risk (suggested): 4 blocks = 4 serial attention+MoE steps per tick. The board is recurrent over ticks (4-40 ticks),
so depth per answer is blocks x ticks; tall gives 64 serial layers in 4 ticks, wide gives 16. Accuracy cost unknown.

## B. The world model today (v2 code)

B1 (shown, code `board_swarm.py` `BoardCell.imagine/_imagine_impl/world_model_loss`): the world model IS the thinking
trunk ("unified"). Input = board rows + one extra action row (`action_in(action_embed)`), mode embedding
IMAGINE_NEXT_STATE, clock. Output = `z_pred = mean(slow rows) + imagine_head(action row)` and `next_rows`.
Loss = MSE(z_pred, detached real next board summary). Planning uses `wm_grad=False` (all weights, context and start
board detached) so plan value cannot train the world model.

B2 (shown, code `dryrun/run_dryrun_50m.py:284-286`, `model.py:671-673`): the only training signal the world model
gets anywhere in v2 is: previous think-tick board + action WAIT -> board summary after the last think tick, weight 0.1.
No real outside observation, no real outside action, no multi-step rollout, no copy baseline. "Real transitions" in
the DreamerV3 sense do not exist in v2 yet.

B3 (shown, `dryrun/results/run1_lr1e-3/dryrun.log`): world_model term (x0.1) 0.022 at the start -> 0.001 later.
Suggested: this target is near trivial (one internal tick, fixed action), so a low loss says nothing about grounding.

B4 (shown, `unsolved-5/1-honest-imagination/RESULT.md`, toy Bait Grid, PILOT INCONCLUSIVE): the "model learned" gate
failed (abs error k=4 0.314 vs mark 0.243 = 0.7 x best constant 0.347). Arms that let plan value reach live inputs or a
free "intention" vector became over-hopeful (bias k4 +0.35 .. +7.97; all 12 candidates tied 66-100%). Walled-off arms
were near unbiased (+0.04 / -0.06). Led to v2 fixes (detached z/pooled before plan; detached imagination).

B5 (shown, `world-model-planning/FAILS.txt`, word-room toys, separate nets, NOT v2): a copy-head world model with
1-deep try-every-command planning passed (test 3: 100 / 94.5 / 100). A learned critic ranking a beam (K 8, depth 6)
passed at tight search budgets (test 8: +51 / +64.5 / +37.5 points on 4-6-move goals; test 9: +38.3 mean on 7-9-move
goals). An actor taught by the critic-ranked beam passed (test 10). A bug made every depth>1 number in tests 1-2 invalid.

B6 (shown, MODEL-IDEAS item 22): Ben's rule: world model trains only on real observed transitions, never on its own
dreams; the policy may train in short dreams (5-15 steps) that start from real observed states with the world model
frozen; no invented UI/world variations from one demo.

## C. Minecraft / Bedwars demo

C1 (shown, MODEL-IDEAS item 3 + 24): demo = Minecraft survival ladder (wood -> tools -> iron/diamonds -> dragon) and
local-server Bedwars with a "predicted vs actual" split view. Comes after (a) and (b). No Minecraft server on the PC
without the lead's OK. Ben's desktop is never controlled: headless only.

C2 (suggested): a cheap stand-in with real transitions on the Mac is an open Minecraft-like 2D survival benchmark
(Crafter: 64x64 pixels, 17 actions, wood/table/pickaxe/iron/diamond achievements; the DreamerV3 paper reports on it).
Not installed on this Mac (checked: `import crafter` fails in the project venvs). Untested here.

## D. What is NOT known (gaps the test must close)
1. 4-wide step time and peak memory on the 5070 Ti at S and P (ticket below).
2. Whether the v2 unified trunk can predict REAL next observations from real actions better than "nothing changes"
   (copy) and better than the same model with shuffled actions, at 1..5 steps.
3. Whether the latent-only target (board summary) collapses or stays trivially predictable once real observations
   drive the board.
