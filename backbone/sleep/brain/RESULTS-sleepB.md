# Sleep-B results (2026-10-24, Qwen/Qwen3.5-2B; preregs `PREREG-sleepB.md` and `PREREG-sleepB-addendum1.md`)

World: Week-1 (`data/week1.json`, seed 1). 982 diary turns over 7 days. 120 base facts: 40 seen on 1 day (C1), 40 on 2 days (C2), 40 on 4 days (C4).
Also 20 facts that change mid-week and 12 routines. Each score comes from one run. Results were read from the Vast instance labels
(`backbone/label_report.py`), because the log and copy services on Vast failed. Boxes: 57467248 ran stage 1 and stage 2;
57479670 ran addendum 1, after 57473371 crashed (likely out of memory) and 57477625 never left "loading". Scores are percent correct. "pool" is forward, reverse,
two-hop, changed and routine questions together. "int" is the integration score: the mean of two-hop, routine and changed-new.

## Weights only (no diary)
| arm | C4 | C2 | C1 | two-hop | changed new / stale | routine | int | pool | ARC-Easy |
|---|---|---|---|---|---|---|---|---|---|
| A0 base | 0 | 0 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | 89.6 |
| AB brain sleep | **67.5** | **52.5** | 0 | 11.1 | 70 / 15 | 66.7 | 49 | 39.8 | 89.6 |
| AF flat sleep, same steps | 45 | 30 | 15 | 0 | 75 / 0 | 58.3 | 44 | 26.1 | 90.6 |
| ab_norem | 85 | 48 | 0 | 4 | 65 | 67 | 45 | 42 | - |
| ab_noshy | 82 | 42 | 0 | 4 | 60 | 75 | 46 | 41 | - |
| ab_flatprio | 82 | 32 | 0 | 15 | 65 | 67 | 49 | 39 | - |
| ab_all (Ben's rule off) | 85 | 55 | 40 | 4 | 65 | 75 | 48 | 53 | - |
| ab_ob (open-book rehearsal) | 80 | 40 | 0 | 11 | 70 | 75 | 52 | 38 | not read |
| ab_klctx (KL on diary prompts) | 75 | 42 | 0 | 22 | 60 | 67 | 50 | 38 | not read |

Stage-2 and addendum numbers are rounded integers from the instance labels. The labels do not carry ARC, so ARC for those arms
needs the result JSONs (`result_<arm>.json`, `arc_easy`).

## With diary search (BM25 top-8 user turns)
| arm | C4 | C2 | C1 | two-hop | changed new | routine | int | pool |
|---|---|---|---|---|---|---|---|---|
| AD base + diary | 100 | 92 | 80 | 7.4 | 100 | 100 | 69 | **84.6** |
| AB | 82 | 80 | 55 | 4 | 75 | 83 | 54 | 65.9 |
| AF | 35 | 35 | 15 | 4 | 40 | 75 | 40 | 32.1 |
| ab_norem | 92 | 85 | 55 | 11 | 75 | 75 | 54 | 71 |
| ab_noshy | 68 | 52 | 10 | 4 | 40 | 92 | 45 | 40 |
| ab_flatprio | 98 | 82 | 72 | 11 | 75 | 100 | 62 | 76 |
| ab_all | 90 | 92 | 75 | 11 | 80 | 92 | 61 | 77 |
| ab_ob | 100 | 98 | 80 | 11 | 95 | 100 | 69 | **85** |
| ab_klctx | 100 | 90 | 78 | 7 | 100 | 100 | 69 | 83 |
| router R (ab_ob adapter) | | | | | | | 62 | 60 |
| router R (ab_klctx adapter) | | | | | | | 60 | 57 |

## Verdicts (marks fixed before the runs)
- P1 FAIL. AB C4 is 67.5, short of 70. C2 is 52.5 and passes its mark of 50. The four stage-2 runs reached 82-85 on C4, so 67.5 may be a low draw. This is a guess from one seed.
- P2 FAIL. Integration is +4.9 over AF, short of +10. Recall on C2+C4 is 60 against AF's 37.5, which passes its part.
- P3 PASS. ARC is 89.6, equal to base.
- P4 FAIL, and its wrong-if fires. AB with the diary scores 65.9, against 84.6 for AD. Two-hop with the diary is 4 against 7.4.
- P5 PASS. Changed-new is 70 and stale is 15.
- Wrong-if on integration (AB <= AF) does not fire: 49 vs 44.
- Q1 FAIL. The better fix arm is ab_ob, which scores 85 with the diary; ab_klctx scores 83. Both are short of 89.6. Both repair note-reading, from 65.9 up to the level of AD.
- Q2 recall part PASS. ab_ob C2+C4 is 60, above the mark of 55. The ARC part has not been read.
- Q3 FAIL. The router scores 60 pooled.
- The addendum wrong-if does not fire. ab_ob scores 85 and ab_klctx 83, both above AB + diary + 5 = 70.9.

## Plain reading
- Brain-like sleep moves recurring facts into the weights better than flat sleep at equal steps. C2 and C4 average 60 against 37.5.
- It keeps one-day facts out, so C1 stays at 0, which is what Ben's rule asks. General knowledge does not move.
- Closed-book rehearsal hurts reading of the diary: 66 vs 85 for the plain model, and 32 for flat sleep (shown). Our guess is that the model learns to answer from memory and skip the context (suggested).
- Both fixes repair this. With the KL leash on diary-format prompts, the diary score is 83 and C4 from memory is 75 (shown, one seed).
- Open-book rehearsal also fixes it. Half the practice questions come with the diary pages. The diary score is back to 85, and 80% of C4 is still known from memory (shown, one seed).
- Removing downscaling hurt note-reading the most: 40 vs 66 with the diary (shown, one seed). Switching Ben's rule off scored best overall, 53 from memory and 77 with the diary. But it also trains on more items, so it gets more steps, and the comparison is not at equal compute.
- Two-hop stays at 0-22 in every arm and mode. The highest, 22, is ab_klctx from memory alone, about 6 of 27 questions. Sleep does not make facts chain.
- The "memory when sure" router scores 60, below diary search alone at 85. A confidence of 0.5 or more on the first token does not mean the answer is right.

## Cost
GPU (Vast A100s): about $2.70 of the $3 cap for stage 1 and addendum 1, and about $1.61 of a $2 cap for addendum 2 (estimated from run times). All boxes are destroyed. Writing the chat week with the Claude API: $1.85.

## Addendum 2: sleep that changes the whole model (prereg `PREREG-sleepB-addendum2.md`, seed 1, AB stage-1 schedule)
Boxes:
- 57521298 (A100 40GB) ran the control.
- 57522280 (A100 80GB) ran ab_ob_full. The first try, 57521297, crashed at startup: a CPU-model self-check is refused by the GPU's Triton kernels.
- ab_ob_merge hit the same crash on 57521298 after the control finished. It is deferred to the next budget.

Scores come from the instance labels.

| arm (seed 1) | C4 | C2 | C1 | recall (C2+C4) | two-hop | changed new | routine | int | pool | + diary pool | ARC-Easy (500) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control | 80 | 32 | 0 | 56 | 4 | 70 | 67 | 47 | 37 | 82 | 92.4 |
| ab_ob_full (every matrix full-rank, lr 2e-5) | 75 | 40 | 0 | 57.5 | 0 | 40 | 58 | 33 | 33 | 47 | **82.2** |
| (ab_ob seed 0, addendum 1) | 80 | 40 | 0 | 60 | 11 | 70 | 75 | 52 | 38 | 85 | not read |

The full arm's diary scores were C4 85, C2 55, C1 2, two-hop 7, changed 40 and routine 75. The router scored 56 for it and 54 for the control.

Verdicts:
- F1 FAIL: recall is 57.5, against a mark of control + 10 = 66.
- F2 FAIL: diary pooled is 47, against a mark of 77.
- F3 FAIL: ARC is 82.2, against a mark of 87.6.
- F4 PASS: C1 is 0.
- **Wrong-if fires:** ARC 82.2 is below 84.6. The other wrong-if needs the full arm to be no better on both recall and integration. It does not fire, because recall is 57.5 against 56, although integration is 33 against 47.
- Seed spread on recall is |56 - 60| = 4, under 10, so these results count as shown.
- M1-M4 (merge) were not run.

Plain reading:
- Changing every weight at lr 2e-5, with the same steps, the same KL guard and the same morning gate, did not put more facts into memory (57.5 vs 56).
- It cost general knowledge (82.2 vs 92.4 for the control and 89.6 for base), diary reading (47 vs 82) and updates (changed-new 40 vs 70) (shown, one seed).
- The 100-item ARC validation gate did not stop this drift. Whether nights were reverted needs the result JSON, which is not recovered.
- Suggested reasons:
  - The full-rank change has far more room to drift in directions the generic-prompt KL guard never probes.
  - lr 2e-5 over 1,596 steps may be too large a step.
- A smaller step size is untested.

## Checks
- Softmax Cancellation (arXiv 2610.31642) checked 2026-10-24, PR #109: reachable at night start but negligible (2e-7 of the update); numbers unchanged. The KL guard is in `Trainer.step`, and so is the ab_klctx leash, which uses the same code. When the add-on (or the delta) is fresh, cur == ref and the KL gives a spurious gradient of about 6.6e-7. That is swamped by the CE gradient of 0.14-0.66. For future runs, the drop-in fix is `fixed_kl(cur, ref, reduction="sum")/n` from `backbone/think/xent.py`.

## Addendum 3: gentler every-weight step, and targeted plasticity (prereg `PREREG-sleepB-addendum3.md`, seed 1)
Boxes: 57543171 (ab_ob_local) and 57543172 (ab_ob_full_s), both A100 80GB. Each was destroyed when its result reached its label. Spend was about $1.80 of a $2.50 cap.

| arm (seed 1) | C4 | C2 | C1 | recall | two-hop | changed new | routine | int | pool | + diary pool | router | ARC-Easy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ab_ob control (add-on) | 80 | 32 | 0 | 56 | 4 | 70 | 67 | 47 | 37 | 82 | 54 | 92.4 |
| ab_ob_full, every weight, lr 2e-5 | 75 | 40 | 0 | 57.5 | 0 | 40 | 58 | 33 | 33 | 47 | 56 | 82.2 |
| **ab_ob_full_s, every weight, lr 5e-6** | 82 | 45 | 0 | **63.5** | 0 | 65 | 67 | 44 | **41** | 81 | **64** | 92.4 |
| **ab_ob_local, tagged top-K (K = LoRA size), lr 2e-5** | 72 | 35 | 0 | 53.5 | 7 | 45 | 67 | 40 | 34 | 82 | 56 | **92.0** |

Verdicts:
- ab_ob_local:
  - L1 PASS: ARC is 92.0, against a mark of 87.6, and diary is 82, against 77.
  - L2 FAIL: recall is 53.5, against a mark of 61.
  - L3 PASS: ARC is 92.0, against ab_ob_full's 82.2 + 5.
  - Neither wrong-if fires.
- ab_ob_full_s:
  - S1 PASS: ARC is 92.4 and diary is 81.
  - S2 PASS: recall is 63.5, against a mark of 61. That is +7.5 over the same-seed control, which clears the 4-point seed-spread rule. But it is only +3.5 over seed-0 ab_ob (60), so the gain is small (suggested).

Plain reading (one seed):
- Changing every weight is safe when the step is small. At lr 5e-6, general knowledge and note-reading match the add-on, and recall is a little higher. At lr 2e-5 they broke.
- Restricting each night's change to the most-tagged 1.2% of weights fully protects general knowledge and note-reading, even at the harmful lr 2e-5 (shown). It stored slightly fewer facts (53.5 vs 56) and fewer updates (changed-new 45 vs 70).
- Untested:
  - Targeted plasticity at the small step.
  - A larger K.
  - Tagging that also counts the update items.
- Per-night tag locations (which layers and module types hold the tagged weights) are in the result JSON, which was not recovered (labels only).

## Addenda 4 and 5: choices made after sealing, before any run (2026-10-24 19:10Z)
- ab_ob_twist: a scene is also dropped if it names an older value of the fact (`twist_dropped_stale`), so a dream never restates a stale fact. The research note `research/sleep-arm-designs-2026-10-24.md` flagged this risk.
- ab_ob_twist: the arm adds 2 extra texts per item, so it changes both "twisted" and "more texts". A T2 pass is labelled suggested until an equal-count plain-paraphrase control is run.
- ab_ob_ther: 2x priority times 0.5 loss weight keeps each salient item's expected push the same. H2 therefore tests spreading the push over more steps, and a null result is likely (suggested, from the same note).
- ab_ob_rot: the quarters are layers [0,6), [6,12), [12,18) and [18,24) of Qwen3.5-2B's 24 layers. A strided split (layer mod 4) is a candidate for the next round.
- ab_ob_b2: the dream generation length also scales (400 x s tokens), so 8 paraphrases and 8 Q&A are not cut off. Update-detection checks and REM sampling lengths are not scaled. Read the gate-revert count before reading B1.
- The new arms record peak GPU memory (`peak_mem_gb`, `peak_mem_train_gb`). The CPU smoke showed that ab_ob and the older arms are bit-identical to before.
