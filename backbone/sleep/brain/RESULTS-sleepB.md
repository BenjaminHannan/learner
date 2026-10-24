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
| ab_klctx (KL on diary prompts) | KLC4 | KLC2 | KLC1 | KL2H | KLCHG | KLRT | KLINT | KLPOOL | not read |

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
| ab_klctx | KLDC4 | KLDC2 | KLDC1 | KLD2H | KLDCHG | KLDRT | KLDINT | KLDPOOL |
| router R (ab_ob adapter) | | | | | | | 62 | 60 |

## Verdicts (marks fixed before the runs)
- P1 FAIL. AB C4 is 67.5, short of 70. C2 is 52.5 and passes its mark of 50. The four stage-2 runs reached 82-85 on C4, so 67.5 may be a low draw. This is a guess from one seed.
- P2 FAIL. Integration is +4.9 over AF, short of +10. Recall on C2+C4 is 60 against AF's 37.5, which passes its part.
- P3 PASS. ARC is 89.6, equal to base.
- P4 FAIL, and its wrong-if fires. AB with the diary scores 65.9, against 84.6 for AD. Two-hop with the diary is 4 against 7.4.
- P5 PASS. Changed-new is 70 and stale is 15.
- Wrong-if on integration (AB <= AF) does not fire: 49 vs 44.
- Q1 FAIL. ab_ob with the diary scores 85, short of 89.6. It does repair note-reading, from 65.9 to 85, which equals AD.
- Q2 recall part PASS. ab_ob C2+C4 is 60, above the mark of 55. The ARC part has not been read.
- Q3 FAIL. The router scores 60 pooled.
- The addendum wrong-if does not fire: ab_ob with the diary is 85, above AB + diary + 5 = 70.9.

## Plain reading
- Brain-like sleep moves recurring facts into the weights better than flat sleep at equal steps. C2 and C4 average 60 against 37.5.
- It keeps one-day facts out, so C1 stays at 0, which is what Ben's rule asks. General knowledge does not move.
- Closed-book rehearsal hurts reading of the diary: 66 vs 85 for the plain model, and 32 for flat sleep (shown). Our guess is that the model learns to answer from memory and skip the context (suggested).
- Open-book rehearsal fixes this. Half the practice questions come with the diary pages. The diary score is back to 85, and 80% of C4 is still known from memory (shown, one seed).
- Removing downscaling hurt note-reading the most: 40 vs 66 with the diary (shown, one seed). Switching Ben's rule off scored best overall, 53 from memory and 77 with the diary. But it also trains on more items, so it gets more steps, and the comparison is not at equal compute.
- Two-hop stays at 0-15 in every arm and mode. Sleep does not make facts chain.
- The "memory when sure" router scores 60, below diary search alone at 85. A confidence of 0.5 or more on the first token does not mean the answer is right.

## Cost
GPU (Vast A100s): about COST of the $3 cap. Writing the chat week with the Claude API: $1.85.
