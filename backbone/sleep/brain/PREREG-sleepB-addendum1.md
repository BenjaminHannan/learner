# Sleep-B addendum 1: the slept model reads its diary worse (written 2026-10-24 ~05:50Z, before any addendum run)

Labels: shown / suggested / untested. Same model, data, tests and scoring as `PREREG-sleepB.md`.

## What stage 1 showed (shown; Vast 57467248, one seed)
| arm | weights only: C4 / C2 / C1 fwd | two-hop | changed new / stale | routine | pooled | + diary search: pooled | ARC-Easy |
|---|---|---|---|---|---|---|---|
| A0 base | 0 / 0 / 0 | 0 | 0 / 0 | 0 | 0 | - | 89.6 |
| AD base + diary | - | - | - | - | - | **84.6** (two-hop 7.4) | - |
| AB brain sleep | **67.5 / 52.5 / 0** | 11.1 | 70 / 15 | 66.7 | 39.8 | 65.9 | 89.6 |
| AF flat sleep (same steps) | 45 / 30 / 15 | 0 | 75 / 0 | 58.3 | 26.1 | 32.1 | 90.6 |

So brain sleep moves the recurring facts into the weights better than flat sleep. It keeps one-day facts out, as Ben's
rule wants, and leaves general knowledge alone. But a slept model with the diary in front of it scores far below the plain
model with the same diary (65.9 vs 84.6; flat sleep 32.1). Training on closed-book questions seems to teach the model to
answer from memory and stop reading the notes it is given (suggested; examples to be checked in the result JSONs).
That breaks Ben's design, where the weights and the diary work together.

## Two candidate fixes, each one change from AB (same step schedule as AB via `--schedule`)
- **ab_ob, open-book rehearsal.** Each Q&A training example (NREM and REM) is shown with probability 0.5 in the same format as the diary test. The format is: the BM25 top-8 user turns from days <= tonight for the dreamed question, labelled by day, then the question. The target is the verified answer. Brain analogy (suggested): recall practice while the hippocampus is still active, so the cortex learns to work alongside it, not instead of it.
- **ab_klctx, read-the-notes leash.** Each night the KL guard also covers about 100 diary-format prompts. Each prompt is BM25 top-8 turns from days <= tonight for one of tonight's dreamed questions, paired with the base model's answer. This keeps the slept model's note-reading close to the base model's.

## Two-system answering (no training change; computed inside the ab_ob and ab_klctx runs)
Router R, "familiarity first, recollection if unsure":
- If the slept model answers with the diary absent and its first answer token has probability >= 0.5, use that answer.
- Otherwise use the base model (adapter off) with diary search.
- The 0.5 threshold is fixed now. Per-question answers and confidences are saved for every mode.

## Pass marks (fixed now)
- **Q1:** the better fix arm, + diary, pooled >= AD + 5 (>= 89.6). Both arms are reported.
- **Q2:** that arm, weights only, C2+C4 forward >= AB - 5 (>= 55.0), and ARC-Easy >= base - 2.
- **Q3:** router R, pooled >= AD + 5, using the ab_ob adapter.
- **Wrong if** both fix arms, + diary, score <= AB + diary + 5 (neither repairs note-reading).

Compute: one Vast A100, within the thread's $3 cap (stage 1 costs about $1.5).
