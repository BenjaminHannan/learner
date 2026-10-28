# Prompt for GPT (web): a training-free "extra lap" test where the control block beat the pre-chosen block

Paste everything below the line into GPT. It cannot see our code, so the prompt stands alone.

---

I need a careful second opinion on a small experiment. Label every claim you make as **shown** (follows from the numbers below),
**suggested** (plausible but not shown) or **untested**. Please end with a plain-language summary of a few sentences for a
high-school senior who is running this project.

## The setup

- Model: Qwen3.6-35B-A3B (a mixture-of-experts model with about 3B active parameters), quantized to 3 bits, run with Apple's MLX on
  a laptop. No training of any kind. 40 layers, in 10 repeating periods of 4: three Gated DeltaNet (linear-attention) layers and then
  one full-attention layer.
- "Extra lap": take a block of whole periods (4, 8 or 12 layers, starting at a period edge from layer 4, ending at least 4 layers
  below the top) and run it again on its own output before running the layers above it. Lap 2 = the block twice in a row. Each pass
  is a full-sequence pass, so the linear-attention layers restart their recurrent state from zero on the repeat. 21 possible blocks.
- Task ("pointer chains"): 64 shuffled fact lines such as "The key is in the box.", "The box is in the bag.", "The bag is at the mill.".
  Each prompt has 7 chains that end at 7 different places. The question asks where one object is, and the answer is read as the
  highest next-token log-prob among the 7 places after a pre-filled "The {object} is at the". So guessing scores 1/7 = 14.3%. Depth =
  the number of links from the object to its place (1-16). This is a synthetic bed, separate from our other benchmarks.
- Pre-registered procedure:
  1. calib (dev rows, 40 per depth): D = the depths where the plain model's dev accuracy is in [24.3, 80].
  2. sweep (dev rows in D): each of the 21 blocks at lap 2. C* = the best dev accuracy on D. Ties go to the higher mean log-prob of the
     right answer, then the smaller block, then the earlier one.
  3. test (fresh rows, 100 per depth, other seed): the plain model, C* at laps 2-4, and a control block (same size as C*, the start
     farthest from C*'s) at lap 2.
  - Pass (H1): C* lap 2 minus plain on D at least +5 points, with the 95% paired-bootstrap CI above 0. Proved wrong below +1.
    H2: no worse than -2 on depths below D. Anything in between = NOT SHOWN.

## Results

Dev (plain): depth 1 97.5%, 2 57.5%, 3 32.5%, 4-16 between 7.5% and 15%. So D = {2, 3}.

Dev sweep, lap-2 accuracy on D (80 rows; plain = 45.0%): s4k12 62.5, s16k12 62.5, s4k8 55.0, s8k8 55.0, s4k4 53.8, s16k8 53.8,
s24k4 51.2, s8k12 50.0, s16k4 48.8, s12k12 48.8, s12k4 47.5, s8k4 46.2, s28k4 46.2, s12k8 45.0, s24k8 45.0, s20k8 43.8, s20k12 43.8,
s20k4 40.0, s32k4 36.2, s28k8 36.2, s24k12 33.8. (sSkK = start at layer S, K layers.) C* = s16k12 won the tie with s4k12 on mean
answer log-prob (-1.78 vs -1.96). The control is therefore s4k12, the other tied block.

Test (fresh rows), accuracy % by depth:

| depth | plain | C* s16k12 lap 2 | lap 3 | lap 4 | control s4k12 lap 2 |
|---|---|---|---|---|---|
| 1 | 96 | 97 | 98 | 95 | 99 |
| 2 | 73 | 72 | 68 | 65 | 84 |
| 3 | 28 | 37 | 39 | 38 | 41 |
| 4 | 21 | 23 | 22 | 21 | 25 |
| 5 | 11 | 16 | 16 | 16 | 12 |
| 6-16 | 9-18 | 7-18 | 6-16 | 6-17 | 6-17 |

- H1: C* lap 2 minus plain on D = +4.0 [-1.0, +9.0], n = 200 -> NOT SHOWN.
- H2 (depth 1): +1.0 [-2.0, +5.0].
- Control lap 2 minus plain on D: +12.0 [+7.0, +17.0] (reported, no mark). C* and the control give the same answer on 76.5% of D rows.
- Stop rule (stop at the first lap whose answer equals the previous lap's): 2.0-2.5 laps at every depth, Spearman(depth, laps) 0.04.
- Hidden-state RMS at the last position: 0.43 plain, 0.48-0.50 at laps 2-4 of C*, 0.40 for the control at lap 2.

Separately, and not to be mixed with this: we are also training a small model (0.8B) to loop, on a related chain task. Please keep
your answer about the training-free test above.

## Questions

1. How much of the control's +12 (vs C*'s +4) is likely selection noise between two blocks that tied on 80 dev rows, and how much
   might be a real difference between repeating early layers (4-15) and middle layers (16-27)? What does the per-depth pattern
   (the control's gain sits mostly at depth 2; C*'s at depth 3) suggest?
2. Is there a mechanism story for why repeating early layers would help 2-hop lookups in a hybrid DeltaNet/attention model,
   given the recurrent state restarts on the repeat? What would distinguish that story from noise?
3. Propose exactly ONE next experiment, with its pass mark and its "proved wrong" line fixed in advance, and the single result
   that would show the idea is wrong. It must run with no training, on a laptop, in about 2 hours. Say how many fresh rows it needs
   for an honest test of a +5-point bar.
4. Is anything in the procedure itself likely to bias these numbers (the D rule, the tie-break, reading log-probs over 7 candidates,
   the full-sequence repeat)?

Then the plain-language summary for the student.
