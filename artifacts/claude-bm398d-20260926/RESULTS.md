# bm-398d RESULTS: the evidence diagnostic (benchmarks thread, 2026-09-26 ~13:15 UTC)

Verdicts under the sealed rules (PLAN.md, sealed in 79b2dbc09 at 12:05 UTC):
- **D1 = "both"**: finding and reading both cost right answers.
- **D2 = false**: distraction did not reach its −10 bar.
- **D3 = true**: retrieval misses cost right answers.
- Not INVALID, and the precision guard holds.

Every LoCoMo number here is "after using LoCoMo for development". Counts only; no question, answer, evidence or
reply text is quoted.

## Where it ran
- G and GD ran on this cloud machine's CPU (fp32) in 42 minutes, $0. The seal checked 9/9 OK before the run and
  again before scoring.
  - locomo_G sha256 593466f6…7a9f; locomo_GD 0f8c5790…4288; locomo_E20c 44930106…202a. The files stay in the
    scratchpad (they hold reply text).
- The inputs match inputs.sha256.txt.
- Twelve blind Opus judges ran as planned: ten main judges with three batches each from one group, and two
  relabel judges. Each had a private folder. 1,605 items, all labelled once.
- The sealed scorer gave score.json. key.json (ids and arms only) and labels/ are here.
- The PLAN header says "~12:40 UTC". The seal commit's time is 12:05 UTC; the header time is wrong, and the
  content is unchanged.

## Blind check: right and complete (label A) out of 297
| Arm | Lines the 1B saw | A | A % | cat 1 | cat 2 | cat 3 | cat 4 |
|---|---|---|---|---|---|---|---|
| G | only the annotated evidence lines | 137 | 46.1 | 22.6 | 17.2 | 26.3 | 65.9 |
| GD | evidence lines + store's other top lines, 20 lines | 119 | 40.1 | 22.6 | 10.3 | 21.1 | 58.1 |
| E20 | store's top 20 | 88 | 29.6 | 7.5 | 8.6 | 26.3 | 44.3 |
| T | whole chat | 109 | 36.7 | 13.2 | 8.6 | 21.1 | 55.7 |
| Q2 | whole chat, Qwen3.5-2B | 138 | 46.5 | 20.8 | 17.2 | 31.6 | 66.5 |

Questions per category: cat 1 = 53, cat 2 = 58, cat 3 = 19, cat 4 = 167. Full label counts are in score.json.

## The comparisons (A-rate points; conversation-level 95% interval, seed 398, 10,000 draws)
| Pair | Points | Interval | Gained / lost | Rule |
|---|---|---|---|---|
| G − T | +9.4 | +4.0..+14.7 | 59 / 31 | D1: between +5 and +15, so "both" |
| GD − G | −6.1 | −11.5..−0.8 | 28 / 46 | D2: bar −10 not reached, so false |
| GD − E20 | +10.4 | +6.6..+14.0 | 41 / 10 | D3: ≥ +10 and interval above 0, so true |
| T − E20 | +7.1 | +4.4..+10.1 | 50 / 29 | report only |
| Q2 − T | +9.8 | +5.0..+15.1 | 52 / 23 | report only |
| Q2 − G | +0.3 | −4.2..+4.1 | 37 / 36 | report only |

GD − E20, split:
- 186 questions where the store already had every evidence line in its top 20: −1.6 (interval −5.0..+1.9).
- 111 questions where retrieval missed at least one: +30.6 (interval +23.1..+37.3).

## Checks
- Precision guard: on the 186 same-lines questions, GD's A-rate is within 1.6 points of E20's, inside the ±5
  allowed. Holds.
  - 162 of 186 replies were byte-identical across CPU fp32 and GPU bf16.
  - E20c: 24 of 30 re-run replies identical.
- Judges:
  - Relabel agreement: 114 of 120.
  - Different judges gave the same label to 150 of the 162 identical GD and E20 replies.
- INVALID rule: G − T = +9.4, not ≤ −5, so LoCoMo's evidence labels were usable here.

## Predictions
| # | Prediction | Result |
|---|---|---|
| P1 (60%) | D1 = finding, point guess +20 | wrong: +9.4, "both" |
| P2 (25%) | D2 true | wrong: −6.1, false |
| P3 (45%) | D3 true, point guess +9 | right: +10.4 |
| P4 (85%) | not INVALID | right |
| P5 (70%) | Q2 − T ≥ +10 | wrong: +9.8 |
| P6 (50%) | G's A-rate ≥ Q2's | wrong: 137 vs 138 |
| P7 (80%) | precision guard holds | right |

## What it means (shown / suggested / untested)
- Shown: given only the right lines, the plain 1B is right on 137 of 297, against 109 reading the whole chat
  (+9.4, interval +4.0..+14.7). That ties Qwen3.5-2B reading the whole chat (138; Q2 − G +0.3).
- Shown: even with only the right lines, the 1B is not fully right on 160 of 297.
  - Reading the lines is the larger remaining loss.
  - It is worst on dates (cat 2: 17.2%) and multi-part questions (cat 1: 22.6%).
  - Single-fact questions reach 65.9%.
- Shown: the store's top 20 answers worse than the whole chat (88 vs 109).
  - Where the store missed evidence lines, adding them back gains 30.6 points on those 111 questions.
  - Where it had them all, nothing changes (−1.6).
- Suggested: distraction costs some answers.
  - Twenty lines holding the right ones score 6.1 points below the right ones alone. The interval is below zero,
    but the registered −10 bar was not reached.
- Shown: under a blind check that sees the evidence, Qwen leads the 1B's whole-chat reading by 9.8 points (138 vs
  109, interval +5.0..+15.1).
- Suggested: part of the 20.4-point F1 gap (47.87 vs 27.50, over all 1,540 questions) is wording, not right
  answers. The two numbers come from different measures and samples.
- Untested:
  - a fresh, independently written bank with code-made evidence labels, to confirm this;
  - whether a better reader also gains on GD and E20 inputs, not only G.

## Next, as the sealed plan says for "both"
1. The evidence-trained reader adapter comes first (398 follow-ups file, step 3).
   - Every condition feeds the reader, and reading is where most answers are lost even with perfect lines.
   - Dates and multi-part questions are the priority in its practice set.
   - Its test is this blind check on G, GD and E20 inputs.
2. A retrieval change is registered alongside at $0: neighbouring lines, speaker and date kept, and a second
   lookup for multi-part questions.
   - Pass: complete-evidence recall up, and the blind check on the new top 20 against E20.
   - The ceiling is GD's 119, or 41 gained against 10 lost.

## Blind recount: agrees (added ~13:25 UTC)
A separate agent recomputed every number above from the raw files with its own code. It did not see score(),
score.json or this file.
- Every count, pair, interval, relabel figure and precision number is equal.
- All 1,605 items carry one A-E label.
- No judge saw two arms of one question, and the relabel judges saw neither L0 nor L1.
- Every batch reply is byte-equal to the reply in its arm's file.
- Its caveat: D3 is close to the line. A net swing of 2 questions (to +9.8) would make it false. Nearly all of the
  gain is on the 111 retrieval-missed questions: 35 gained, 1 lost.
- On the 186 same-lines questions, 15 A/not-A flips separate GD and E20. 6 are judge disagreement on identical
  replies; 9 come from number precision.
