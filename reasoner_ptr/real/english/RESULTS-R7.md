# Round 7: question-first reuse and a thin talker (marks: PASS-MARKS-R7.md)

Ask: Ben 18:36 UTC 10-04 asked, "why would the second language model read the question? Shouldn't it just output a sentence?" Six paired seeds were run, three runs per RTX 3090 box, with the round-6 "six" recipe (`--gen 8000 --kinds 6 --block-r6`). The full numbers are in ANALYSIS-R7.json, and the results are in results7/. All six copy-backs had a matching sha256. Cost was about $2.30, including a first attempt paused for credit.

## Judged
| test | result | verdict |
|---|---|---|
| A: qfirst − allptr, pooled exact (576 Qs) | −7.6 (CI −8.7 to −6.5), every seed −6 to −9 | **FALSIFIED** (mark: lower bound > −5) |
| S: qfirst first-token time / bare | 2.96x (allptr 2.97x) | **FALSIFIED** (mark: ≤ 1.5x) |
| B: ptr − allptr, pooled exact | −63.9 (CI −68.6 to −59.3) | **FALSIFIED** (mark: lower bound > −5) |

## Accuracy (exact %, mean of 6 seeds)
| arm | pooled | FRESH | NEW-KINDS-R5 | NEW-KINDS2-R6 |
|---|---|---|---|---|
| allptr (today) | 82.9 | 92.4 | 80.8 | 75.3 |
| qfirst (question first, reused cache) | 75.2 | 82.6 | 74.6 | 68.5 |
| ptr (core vectors only, no question words) | 18.9 | 37.9 | 11.1 | 7.7 |
| bare LM, 8 examples (rounds 5 and 6) | — | 75.0 | 67.7 | 77.6 |

Lesions on FRESH:
- **Zero pool:** allptr 0.0, qfirst 4.8, ptr 0.2.
- **qfirst zero core** (all 16 vectors zeroed): 0.0.

So every version leans fully on the core's vectors.

## Speed: batch 1 on RTX 3090, median over 48 questions, then over 6 boxes
| | time to first answer token, vs bare | time to 8 answer tokens, vs bare |
|---|---|---|
| allptr | 2.97x | 1.30x |
| qfirst | 2.96x | 1.29x |
| ptr | 2.97x | 1.29x |

- On the fast boxes, the bare LM takes about 10 ms to its first token and our model takes about 30 ms.
- The extra ~20 ms is the same whether the second pass sees 65 inputs (allptr), 16 inputs on a reused cache (qfirst), or 16 inputs with no question (ptr).
- **Inferred, not measured part by part:** at batch 1 a forward pass of a 1.2B model costs about the same for 16 or 65 tokens, because it is bound by fixed per-layer overhead rather than by token count. So the cost is one extra LM forward (any length) plus the reader and the 4 core loops, not the re-reading of the question.

## What this says
1. **The talker needs the question's words.** With only the core's 16 vectors (pool + pointer), English drops from 83% to 19%, and to 8 to 11% on new kinds. Round 3 trained this kind of talker on 48 examples; this round gave it 8000 practice questions, and it still fails. A state-only talker would need a far stronger copy path than the 8-slot pointer.
2. **Putting the question first costs ~8 points and saves no time at batch 1.** The words have to come after the core's vectors to be used well. A likely reason (suggested, untested) is that, in question-first order, the question tokens are processed before the core speaks and can't be read "in light of" the core's output.
3. **Speed:** our first token is ~3x the bare model, and an 8-token answer takes ~1.3x as long. The overhead is the core plus one extra pass, not the double read. Making it faster means a cheaper core step or folding the core into the first pass, not cache reuse.

Next step if speed matters (untested): measure the reader + core alone against one LM forward at batch 1 to split the 20 ms.
