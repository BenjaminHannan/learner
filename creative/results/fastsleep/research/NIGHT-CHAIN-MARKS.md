# Night chaining: does recombining notes at night grow the notebook usefully? Marks (written 9:45 AM ET 10-07 before any run; commit 08c70a881)

This is part of Ben's request (9:34 AM ET 10-07) for more research into fast sleep. The question: can memory sleep learn more per night at
the same low compute, especially on the multi-step rules?

## What we already know
These are read-only probes on DEV, with the key read only to score. They are not marked.
- **Literal recall ceiling.** A stored program solves a DEV question exactly as written:
  - square: 100%
  - last_digit: 100%
  - double_add: about 65%
  - sq_plus: 27-39%
  - affine: 0-8%

  The notebook can only replay whole programs, and the multi-step kinds need parameter values the night never stored.
- **Chaining two stored notes.** Take a program from tonight's W notes and one of the 512 old add/mult notes, chain them, and take the
  shortest chain that fits the 3 examples. Its answer is right on 100% of DEV, for all five kinds and all eight parents.
  - With old notes alone, only affine is solved.
  - With W notes alone, chaining adds nothing.
- **Blind search with no notes.** A breadth-first search over x and the constants 1/2/10/100, taking the first program that fits:

  | Candidates per question | DEV right |
  |---|---|
  | 1,000 | 64.5% |
  | 6,000 | 77.3% |
  | 50,000 | 94.9% |

  So C2's held-out kinds are easy for any search that can check against the examples. Chaining notes reaches 100% with at most
  |library|^2 (about 5,000) candidates. That is better than blind search at the same budget, but not by a huge margin.

## Test (8 parents: s100, s101, s200-s205; DEV only)
Every arm is memory sleep exactly as C2b's arm M: memory + 512 old notes, answer note off, c 50, theta 0.9, cal 0.99, k 16, tau 0.05.
Only the records written in differ:
- **M:** the night's W records, as in the confirm.
- **MC:** W plus C. For each pool question with no W record, C holds the shortest chain P2(P1(x)) of two library programs that fits that
  question's 3 examples. The library is this parent's W programs plus the 512 old notes. Chains are at most 7 steps, with at most one record
  per question, and the key is never read.
- **MB (control):** W plus B. For each pool question with no W record, B holds the first program that fits the 3 examples from a blind
  breadth-first search with no notes. The budget is 5,000 candidates per question, matched to the chain library's |library|^2 order. Programs
  are at most 7 steps, and the key is never read.

## Measures
- **DEV gain:** greedy first try minus N's, pooled over the 8 parents and per kind.
- **Chain-5 harm:** the nightly guard's measure, data_big dev in_dist chain-5.
- **Records written** and memory FLOPs, measured.

## Marks
1. **Notebook grows usefully:** pooled DEV gain of MC minus M is at least +5 points, and MC is ahead of M on at least 6 of the 8 parents.
2. **Learning, not just search:** pooled DEV gain of MC minus MB is at least +3 points. If not, the gain comes from search, not from what the
   night learned, and that is reported plainly.
3. **Safe:** MC's chain-5 harm is at most 2 points on every parent.
4. **Cheap:** MC's memory FLOPs are at most 1/10 of each parent's job-6 B dose.

- **Recommend MC to the roadmap** only if 1, 3 and 4 pass. Mark 2 decides how it is described ("recombining learned notes" or "search at
  night").
- **Proved wrong:** MC minus M pooled < +1 point.

DEV is the tuning split. The fresh test of any adopted change is C2b's sealed split, run by the roadmap thread.

## Result (10:08 AM ET 10-07): PROVED WRONG

| Parent | M | MC | MB | MC minus M | MC minus MB | MC chain-5 harm | MC memory TF | B dose TF | MC / B |
|---|---|---|---|---|---|---|---|---|---|
| s100 | 34.0 | 25.8 | 29.7 | -8.2 | -3.9 | 0.0 | 2.42 | 34.2 | 0.071 |
| s101 | 28.1 | 36.3 | 36.7 | +8.2 | -0.4 | 0.0 | 2.29 | 19.7 | 0.116 |
| s200 | 31.2 | 36.3 | 38.7 | +5.1 | -2.3 | 0.0 | 2.42 | 39.4 | 0.061 |
| s201 | 37.5 | 36.3 | 36.7 | -1.2 | -0.4 | 0.0 | 2.36 | 32.3 | 0.073 |
| s202 | 16.4 | 18.0 | 19.1 | +1.6 | -1.2 | 0.0 | 2.29 | 19.3 | 0.119 |
| s203 | 28.9 | 27.3 | 25.8 | -1.6 | +1.6 | 0.0 | 2.37 | 33.4 | 0.071 |
| s204 | 40.6 | 35.9 | 32.4 | -4.7 | +3.5 | 0.0 | 2.30 | 30.4 | 0.076 |
| s205 | 32.0 | 38.3 | 35.2 | +6.2 | +3.1 | 0.0 | 2.31 | 30.2 | 0.076 |
| **Pooled** | **31.1** | **31.8** | **31.8** | **+0.7** | **0.0** | | | | |

The columns M, MC and MB are DEV gain in points over N.

DEV right by kind, mean over the 8 parents (%):

| Arm | affine | square | sq_plus | last_digit | double_add |
|---|---|---|---|---|---|
| N | 1.0 | 0.0 | 0.0 | 0.0 | 4.4 |
| M | 0.0 | 83.6 | 0.0 | 73.0 | 4.9 |
| MC | 0.2 | 61.0 | 9.3 | 71.6 | 22.8 |
| MB | 0.2 | 73.8 | 3.9 | 73.5 | 13.5 |

- **Records.** The chain search found a fitting program for every unsolved pool question on every parent: 701-843 questions, about 200 affine and 200 sq_plus each, in 13-22 seconds of CPU. The blind search found 409-551 of them in about 17 seconds.
- **Mark 1, notebook grows usefully: FAIL.** MC minus M is +0.7 pooled, against +5 needed. MC is ahead on 4 of 8 parents, against 6 needed.
- **Mark 2, learning, not just search: FAIL.** MC minus MB is 0.0 pooled.
- **Mark 3, safe: PASS.** Chain-5 harm is 0 on every parent.
- **Mark 4, cheap: FAIL on 2 parents.** MC's memory cost is 0.116 of B on s101 and 0.119 on s202, against at most 0.1. The cost grows with the number of records, which roughly triples here.
- **Proved wrong:** MC minus M is below +1 point, so night chaining is proved wrong as written.
- **What happened:** the extra records lift sq_plus (0 to 9%) and double_add (5 to 23%), but square drops from 84% to 61%. Affine stays at 0% even with about 200 correct affine records per parent. A notebook replays a stored program with its own constants, and a new affine question needs different constants, so its records cannot be reused.
