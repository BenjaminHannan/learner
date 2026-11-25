# Solve session: Premonition's world model (Problem 7). Full context, code included

Hi, I'm Ben, a high-school senior building my own AI from scratch. I want to use **this whole conversation** to get my world model as far as possible. You can't run code, but my coding agent (Claude) can. So we'll work in a loop: you think and check, I paste your experiment cards to my agent, and I paste the results back to you.

Everything is in this folder: my vision doc, a fact-checked briefing of every try, two diagnoses, another model's (Astra's) advice, the exact pass marks, and the **full source** of the model, trainer, scorer and practice-run driver. Paths are shortened (`<project>` = this folder), nothing else edited. Data, checkpoints and the sealed test worlds are NOT here.

## How to work (please follow exactly)
1. **Label every claim** shown (follows from the code or numbers here), suggested (your inference) or untested. Cite code by file + function name. If something isn't in the material, say "not in the material". Don't guess numbers.
2. **Keep separate:** the old shared "board" model history (closed) vs the current conv world model; past verdicts (final, never re-graded) vs future marks (we may change these before a run).
3. **Project rules:**
   - learned parts only, with no game-specific hand rules (the game's internal state may be used only by the scorer);
   - world-model gradient only from 1-step real pairs, with 3- and 5-step rollouts scored, never trained;
   - one change per experiment, with marks pinned before running;
   - an idea is dropped after 3 clean misses;
   - the sealed test worlds are opened once, only after a two-seed dev PASS;
   - each test wave takes about 30 minutes on one Apple M3 (PyTorch MPS or CPU) or one 16 GB consumer GPU, with no paid compute.
4. **Every experiment you propose must be an EXPERIMENT CARD** I can paste straight to my coding agent:
   - Name.
   - The question it answers.
   - Exact code change (file, function, what to change; or "no code change").
   - Exact settings: seeds, steps, data, device, repeats per arm.
   - Pinned pass marks, and the result that would prove it wrong.
   - Expected runtime.
   - What we do next if it passes, and what we do if it fails.
   - Prefer free diagnostics (no training, or under 5 minutes) before training runs.
5. **When I paste results back,** update the problem list (solved / narrowed / still open), then give the next card.
6. End every answer with a 5-line plain-English summary for me.

## Your first answer, in this order
A. **Thorough code check.**
   - Read model_v7.py, train_v7.py, scorer.py and pilot_driver.py end to end, looking for real bugs.
   - Include: leakage between train, eval and sealed data; rollout correctness (no real intermediate frames in k3/k5); the wall classifier and labels; the std gate maths; the Rel-PER sampler; the loss terms; the train/eval split; anything that could make a mark lie.
   - List each finding with severity and code location. "No bug found in X" is a useful answer.
B. **The problem list below.** For each problem, give your diagnosis with evidence from the code and numbers, and say whether it's a model problem, a data problem or a ruler (marking) problem.
C. **A ranked plan:** an ordered sequence of experiment cards that would solve as much as possible.
   - Start with the cheapest card that removes the most uncertainty. Then give card #1 in full.
   - Also say how the near-term work should line up with my vision doc. For example, its Rung 1 asks to compare 16×16 vs 64×64 inputs and to report paired 95% confidence intervals across worlds and training seeds; neither has been done yet.

## The open problems (my agent's list; challenge it)
1. **"Do" collapse.** After "do" the model predicts almost no change: std ratio 0.13–0.19 against a mark of ≥ 0.25. There are two parts:
   - (a) **Wake-ups** carry 55% of real "do" change energy on dev, but only 0.41% of training windows. At 16×16 the HUD energy digits 6 and 9 are pixel-identical, so one frame can't show when the player will wake.
   - (b) **Awake chop, collect and place** come out as a flat output, R² ≤ 0 even on training data, with 38–306× less gradient than moves. A kernel-ridge probe on 16×16 pixels gets R² 0.38, so the information is in the pixels.
   - Suspected but not shown: the scripted exploration rarely produces useful interactions, so most "do" presses change nothing.
2. **The place-pool mark measures almost nothing.** Dev has zero real furnace placements. One wake-up window carries 86.5% of action 9's change energy, and that alone can fail the pool. This is a ruler problem.
3. **Rollout drift at 5 steps.** Rank 7 scored 0.4953 and 0.5016 against the 0.4977 bar. Re-encoding between imagined steps helps.
4. **The trade-off.** Showing rare moments more often (Rel-PER) fixed "do" and wake-ups in both pilots but made the wall mark worse by +0.008 to +0.013. Non-wake "do" R² also fell, from −0.03 to −0.49 and −0.17, so the extra variation was not accurate.
5. **The ruler is noisier than the allowance.**
   - Training on the M3's MPS backend is not deterministic: gradients differ from step 1 with the same seed and batch, while CPU is bit-identical.
   - Same-setting uniform-arm wall error for seed 7 so far: 0.0604, 0.0504 and 0.0493. More repeats are running and I'll paste them.
   - The wall allowance was +0.005 on a single paired run.
6. **Budget of tries.** The conv line is at 2/3 with the last official try unspent, and Rel-PER is parked at 2/3. Any official try needs a two-seed dev PASS before the sealed worlds open.
7. **Drift from my vision.** The near-term work is a 16×16 pixel conv model. My vision wants meaning and pixels together, tracked "thing slots", audio, parallel dreaming and more. Is this rung still the right first step, and what's the shortest path from here toward the vision?


## Where things are (read in this order)
| What | File |
|---|---|
| My vision for the whole world model | `neon-audit/WORLD-MODEL-VISION.md` |
| Fact-checked briefing of every try, mark and result | `astra/q5-roadblock/CONTEXT.md` |
| Astra's advice on the roadblock | `astra/q5-roadblock/REPLY.md` |
| Running log of everything (newest at the bottom) | `STATUS.md` |
| Current model / trainer / scorer / pilot driver | `forecast8-pilot2/model_v7.py`, `train_v7.py`, `scorer.py`, `pilot_driver.py` |
| Diagnoses | `neon-audit/RANK6-DIAG.md`, `neon-audit/RANK7-DIAG.md`, `neon-audit/RELPER-PILOT2-DESIGN.md` |
| Pinned marks (Ruler C) | `forecast7/PLAN-AMENDMENT.md`; pilot marks `forecast8-pilot/PILOT-PLAN.md`, `forecast8-pilot2/PILOT2-PLAN.md` |
| Determinism audit (script, proof, results) | `forecast8-audit/` |
| Older tries (board model, Rank 3, Rank 6, Rank 7) | `forecast/` … `forecast7/`, `step0/`, `step6/`, `recon/`, `wm/` |
