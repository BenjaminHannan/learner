# Astra: why does the guarded main brain still slowly forget? (diagnosis only)

**Rules for this task:** read only. Do not edit files, train, run tests, or use a GPU. Label every claim as **shown** (you
checked it in code or results), **suggested** (fits the evidence, not checked), or **untested**. Keep the small card
experiments and the village model separate: this question is only about the 3M domain-mode model below. If you propose a
change, give exactly ONE change, with pass marks fixed in advance and the result that would prove it wrong. End with a
plain-language summary for Ben (a high-school senior), at most 8 sentences.

## What to read (branch `claude/project-thread-trabt2`, PR #60)
- `mainbrain/kf.py`: the guard (K-FAC). Input factor A and output-gradient factor G per Linear/Conv1d, measured on the
  model's own old answers (a 4,096-row diary). Each night's AdamW step is projected so that the weight directions holding
  97% of the importance (a_i * g_j) do not move. `norm='example'` (arm N) scales each example's output-gradient block to
  unit size before it enters G.
- `mainbrain/fullrun.py`: runs `domain/mode.py` unchanged. Before every night it re-measures the guard on the current weights.
- `domain/mode.py` `train_night` and the undo rule. Each batch is 32 new-lesson rows plus 32 diary replay rows. lr is 3e-4.
  A night is undone if agreement with the original answers on 512 check prompts falls below 97%.
- Results and marks: `/mnt/project-files/main-brain/MARKS-2026-10-10.md`, Results 4-13 and Diagnostics. Per-night harm:
  `/mnt/project-files/main-brain/screens/harm-nights-*.json`. Run folders: `/mnt/project-files/main-brain/runs/`.

## The puzzle
Learning a spreadsheet tool (near gain, bar >= +30) without old skills slipping. "Slipping" means the in_dist drop is at most
1.5 points and no family of 40 old questions drops with its interval below 0.

| Run (seed) | Kept nights | Near gain | in_dist drop | Families fired |
|---|---|---|---|---|
| v2, no guard (200) | | +66.9 | 4.2 | 7 |
| A: guard, empirical G (200) | 5 | +42.1 | 1.03 | seq_next |
| E: same at 99% (200) | 4 | +41.7 | 1.10 | seq_next |
| N: per-example G (200) | 4 | +42.1 | 0.66 | none (PASS) |
| N on reading Python (200) | 3 | +47.7 | 0.44 | none (PASS) |
| N (201) | 8 | +59.5 | 1.47 | cipher_map, fewshot_number_rule |

Night by night (arm B, same guard as A but undo judged per night), the drop creeps up: 0.37, 0.59, 1.32, ... 2.72 by night 12.
Which families fire changes with seed and arm. The 512-prompt check barely moves while this happens.

## Questions
1. Where is the remaining leak most likely coming from? Candidates: (a) the 3% of importance left unprotected; (b) the
   Kronecker approximation's errors (directions that matter but whose a_i * g_j product looks small); (c) re-measuring the
   guard every night at the current weights, so what was protected before can move later; (d) A including padded positions
   (A differs by up to 0.81 relative between batch 64 and batch 1); (e) the replay half being projected too, so it cannot
   repair; (f) the measurement itself (40 questions per family, intervals) making single-seed calls noisy. Rank them, and say
   what in the code or results supports each.
2. Arm N99 (per-example G at 99%) is running now on seeds 200 and 201. What result would you predict, and why?
3. Give the one next change you would make if N99 fails, with pass marks and the result that would prove it wrong.
