# bm-390 VERIFY (benchmarks thread, 2026-09-25 ~17:45 UTC): registered FAIL on M1; run partial

Source: origin/builder-outbox commit 6821223ed, RESULTS-benspc3.md and run/ (7 files, copied unchanged to main).
Scored with the sealed scorer (SEAL-code.sha256.txt 8/8 OK in this tree), then recounted blind by an Opus agent that
did not see my numbers and wrote its own scorer from the LoCoMo repo's evaluation code (recount3/). Every number
below agrees between the two. Counts only; no question, answer or reply is quoted.

## Verdict
**FAIL (M1), final for Premonition 0.1.** PASSMARKS: "a FAIL of M1 against any arm that ran is final for this
build." The BM25 baseline Rb (plain MiniCPM5-1B reading only the 10 best-matching chat turns) ran in full, and
0.1 scored 22 points below it. The run is partial: T, C, Q2 and L12 did not run (below), so M4 (no harm) is not
judged and the rival comparison is still missing.

## Validity (arms that ran)
| Check | Result |
|---|---|
| Seals on BensPC | SEAL-code 8/8, SEAL-winnl2 3/3, 336b 229/229 OK |
| Data | LoCoMo, MMLU-Redux and GSM8K files match data-manifest.json; the two 300-item samples equal BensPC's byte for byte once line endings are matched (below) |
| Rows | P, P_bare, Rb: 1,986 each, 0 missing, 0 duplicate, 0 category mismatch, 0 empty; mmlu_P, gsm8k_P: 300 each |
| Sleep (P) | 272 rows, checkpoint_exists true in 272, learning attempted in 0 |
| Tracebacks | none in P, Pm, Pg, Rb; "\r\n" in run files: 0 |
| sha256 of run files | equal to RESULTS-benspc3.md (recount) |

Not run: T (plain MiniCPM5-1B, whole chat) crashed with CUDA out-of-memory on its first question, so it produced
no rows; I read the "no traceback" validity rule per arm and report T as NOT RUN rather than voiding P and Rb.
C was killed with no output when the Mac's ssh client timed out on its last conversation. Q2 was stopped at the
7-hour cap before its first conversation finished. L12 and all plain general tests (Tm, Tg, Q2m, Q2g, L12m, L12g)
never started.

## LoCoMo, official F1 x100 (categories 1-4 = 1,540 questions)
| Arm | cat 1 multi-hop (282) | cat 2 temporal (321) | cat 3 open (96) | cat 4 single-hop (841) | **1-4** | abstained | confident wrong |
|---|---|---|---|---|---|---|---|
| P (0.1) | 3.05 | 1.73 | 5.31 | 3.17 | **2.98** | 923 | 450 |
| P_bare (report only) | 0.89 | 0.12 | 1.81 | 1.66 | **1.21** | 1,285 | 197 |
| Rb (plain 1B + BM25 top 10) | 13.63 | 26.93 | 12.06 | 29.65 | **25.06** | 48 | 615 |

Category 5 (report only, 446 each): official right P 260, P_bare 244, Rb 51; strict right P 144, P_bare 309, Rb 50.

## Marks
| Mark | Result |
|---|---|
| M1 P - Rb | -22.07 points, paired bootstrap 95% interval [-23.61, -20.54] (recount [-23.63, -20.54]); per question 109 wins, 836 losses, 595 ties. **FAIL** |
| M1 P - T, Q2, L12 | not run |
| M3 confident wrong | P 450 < Rb 615. Passes against Rb, but P abstains on 923 of 1,540, and M3 is "never a win on its own" |
| M4 no harm | not judged (T's MMLU and GSM8K did not run). P alone: MMLU-Redux 85/300 (28.33%; 134 replies name no letter; chance is 25%), GSM8K 29/300 (9.67%; 257 replies contain no number) |

## Predictions (registered before the run)
- P390.1 (P's 1-4 F1 is 3 to 15): P = 2.98, just under the range. T half untested.
- P390.2 (M3 passes against T and Rb): passes against Rb; T untested.
- P390.3 (M4 a coin flip): untested; the no-letter and no-number counts above point toward harm.
- P390.4, P390.5: untested (C and T did not run).
- P390.6 (P_bare beats P by 2+): wrong. P_bare 1.21 < P 2.98.

## Why 0.1 scores so low (counts shown; cause inferred)
- Shown: while reading 10 chats (6,164 turns fed: 5,882 chat turns plus one date line per session and one opener
  per chat) 0.1 stored **18 facts in total** (0 to 4 per chat). 2,334 of its 6,164 replies were "am I sure?"
  check questions. Sleep ran 272 times and never tried to learn (every row: "0 word episodes (< 8)").
- Shown: with 18 facts it answered "I don't know" (or similar) on 923 of 1,540 questions and was right on few of
  the rest; Rb, which keeps every raw turn and pulls back the 10 most relevant, answers almost everything.
- Inferred, not tested: 0.1's reader was built to save facts a user teaches it about people, and it confirms an
  unsure fact by asking the speaker. In LoCoMo it overhears two other people; nobody answers its check questions,
  and its fixed relation list does not cover most of what LoCoMo asks (events, plans, dates). So almost nothing is
  saved, and there is no fallback to the raw words it heard.
- P is one sampled draw (AMEND-winnl.md "Clarification"); a second draw would move it a little, not 22 points.

## Line endings of the samples (why the data hash differs off Windows)
BensPC ran `fetch` without the line-ending wrapper, as registered, so Windows wrote mmlu300.jsonl and gsm8k300.jsonl
with "\r\n". Rebuilt here with the sealed fetch from the same pinned raw files: Linux bytes hash e294f5fc...c049
(MMLU) and df57d09b...b949 (GSM8K); the same bytes with "\n" -> "\r\n" hash 1a44e304...3850 and 073acc01...555b,
exactly BensPC's. Same 300 items, same order.

## Deviations
- T: out of memory on BensPC's 16 GB card. transformers asks PyTorch for grouped-query attention directly; without
  the flash kernel (Windows) PyTorch falls back to the math kernel, which builds the full score matrix for a
  14k-27k-token chat. Fix for the finishing run: AMEND-finish.md.
- C lost to a monitoring timeout; Q2 to the time cap; P's monitor lost its ssh link once (no relaunch).
- Hardware: P, Pm, Pg and Rb ran on BensPC (RTX 5070 Ti, Windows, Python 3.10.9, winnl2 wrapper).

## What this does and does not mean
It means 0.1, as sealed, is not a long-term-memory system for conversations it overhears: it saves too little and
has nothing to fall back on. It does not measure the reasoner, sleep or grammar, and it says nothing yet about how
the rivals do. LoCoMo is now practice data for later builds (bm-391 must say "after using LoCoMo for development").
