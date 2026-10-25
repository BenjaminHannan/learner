# Guess-1: can we get the assistant to make many genuinely different guesses, and do the extra guesses solve more jobs?

Fixed 2026-10-25 ~22:20Z, before any run. Thread "Make the creative model work" (Ben 21:51Z: "How do we make the model
make a lot of guesses? ... all models just give you one guess"). Separate from the puzzle/village models and from tau2.
Labels in reports: shown / suggested / untested.

## Why (shown, our data)
- Puzzle model (Qwen3.5-0.8B, Leap-1 pairs file): when a prompt was sampled twice, 405 of 474 pairs (85%) gave the
  identical program. Repeat samples mostly repeat the same guess.
- Multistep puzzle model: search over many samples found affine fits for ~36/205 questions, while greedy first try
  stayed ~0. More guesses helped there; the single guess was the bottleneck.

## Setting
- Model: K2-Horizon-3.7B (small tier), thinking off (swap/templates/k2_nothink.jinja), behind any OpenAI-compatible
  server. Serving build and quantization logged in run_meta.json. One server, one model for every arm.
- Jobs: the Reach-1 copy of the RLAIF sandbox (creative/reach1/rlaif_copy, unchanged), fixed subset = every second task
  in file order (210 tasks, all scenario types). Success = every end-state check passes. Up to 6 turns.
- No API calls; deterministic checks only.

## Stage 1: screen (picks the tasks; its tries are never scored again)
8 plain tries per task, temperature 0.7, top_p 0.95 (identical to Reach-1's screen, arm name `plain`).
Target set T = tasks with 0-3 successes out of 8. If |T| > 48, keep the first 48 in file order. If |T| < 20, stop and
report "K2 already solves almost everything here". Selection uses only the screen tries, so the IND arm below is fresh
and not biased by the selection.

## Stage 2: arms on T, 12 tries each, seed 1
- IND (plain retries): 12 fresh independent tries, temp 0.7, top_p 0.95. The baseline every model gives today.
- HOT (louder dice): 12 independent tries, temp 1.0, top_p 1.0, min_p 0.1 where the server supports it (logged).
  Tests whether turning up the sampler is enough.
- LIST (see your earlier guesses): tries run in order. Try k sees, in the system prompt, a one-line summary of each of
  its own earlier tries in this arm (the sequence of tool calls with arguments truncated to 80 chars, plus the first
  120 chars of the final reply), labelled "Your earlier attempts at this job (each was a fresh start):", and the line
  "Do the job in a way that is clearly different from every one of these." No success/failure or check information is
  shown. Try 1 has no list (it is a plain try). Same sampler as IND.
- MENU (plan the spread first): one call asks "List 6 genuinely different ways to do this job (different tools,
  different order, or a different reading of what the user wants). One per line, numbered." Then 12 tries, 2 per
  approach, with "Approach to use: <line>" in the system prompt. Same sampler as IND. The menu call's tokens count.

Equal compute: generated tokens are counted per arm (MENU includes its menu call). If LIST's or MENU's generated tokens
exceed IND's by more than 15%, IND gets extra plain tries (cap 16) until within 15%, and the decisive comparison uses
that topped-up IND. Prompt tokens are reported per arm (LIST's prompts grow; on a prefix-cached server that cost is
small but it is shown).

## Metrics (per task, then summed over T)
- Cracked: at least one success among the arm's tries.
- Distinct plans: number of distinct plan signatures, where a signature is the ordered list of (tool name, arguments
  with whitespace/case normalised) plus whether the episode ended with a final reply or a question. Reported for every
  arm, success or not.
- Distinct correct plans: distinct signatures among successful tries.
- Top-share: fraction of tries equal to the arm's most common signature (1.0 = total collapse).

## Pass marks (fixed now; seed 1)
Let BEST = whichever of LIST and MENU cracks more tasks (ties: LIST).
- P1 (more right answers): BEST cracked >= IND cracked + 4.
- P2 (not just a hotter sampler): BEST cracked >= HOT cracked + 3.
- P3 (really different guesses): BEST distinct correct plans (summed over T) >= 1.5 x IND's.
- P4 (consistent): tasks only BEST cracks outnumber tasks only IND cracks at least 2:1.
PASS = P1-P4 all hold.
PROVED WRONG: LIST and MENU both crack <= IND + 1. Then asking the model to spread its guesses does not give more right
answers on this test bed, and the next step is a trained route (forks or set training) rather than more prompting.
INCONCLUSIVE (anything between): run seed 2 of Stage 2 (same T) and decide on the sum of both seeds with the marks
doubled.
DIAGNOSTIC (does not decide): if BEST raises distinct plans >= 2x IND but P1 fails, the guesses got different but not
better: diversity without quality. Record it; it points to Doubt Forks (diversity at the model's own decision points)
over prompt spreading.

## Cost
Screen 1,680 episodes; arms about 48 x 4 x 12 = 2,304 episodes plus <= 48 menu calls and any IND top-up. No API spend.

## What comes after (not part of this test)
- Doubt Forks Step 0 gate (INVENT-2) uses Guess-1's failed transcripts for free.
- If PASS: "guess-list training", a LoRA trained so that guess k, seeing guesses 1..k-1, lands on a new correct plan
  (reward = distinct correct plans in the set). Its own prereg comes later, against BEST as the bar.
