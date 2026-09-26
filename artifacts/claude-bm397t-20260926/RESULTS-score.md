# bm-397t RESULTS: short-answer training on made-up chats (benchmarks thread, 2026-09-26 ~05:20 UTC)

Verdict: **registered FAIL.** A1 and A4 pass. A2 fails on GSM8K, and A3 misses by 2. Every LoCoMo number here is
"after using LoCoMo for development". Counts only; no question, answer or reply is quoted.

## Where it ran
- One RTX 5090 rental; builder-outbox holds RESULTS-rent.md and run/.
  - Seals 10/10 OK and 8/8 OK; selftests 8/8 and 5/5; both data hashes match; the fetch hashes match.
  - Cost about $0.64 over two rentals. The first box's SSH was broken and nothing ran on it.
- The training ran once, taking 189.7 s over 225 steps; it is fully reported in RESULTS-rent.md.
  - Training loss: first 10 steps 0.7709, last 10 steps 0.078.
  - Code-made dev set: right 116 → 199 of 200; median words 6 → 2. The merged model matches the LoRA on dev.
- Scoring ran once per command with no relaunch. The run/ files' sha256 were checked here against RESULTS-rent.md:
  - locomo_TS: 30eb5dc4…0f9e
  - mmlu_TS: fa830d32…2257
  - gsm8k_TS: c6bb2f14…65a1
- The baselines are T's run2 files, matching bm-391's baselines.sha256.txt:
  - locomo_T: 35bdf151…b3db
  - mmlu_T: ef1b4e6b…fd62
  - gsm8k_T: 29e814f5…244e
- Scored here on CPU with the sealed scorer (score/), bm-396's audit and bm-391's prf script.

## Marks
| Mark | Bar | TS | Verdict |
|---|---|---|---|
| A1 gain | TS − T ≥ +5.0, conversation CI > 0 | +9.57 (27.50 → 37.07), conversation CI +7.62..+11.73 | PASS |
| A2 no harm | MMLU ≥ 41, GSM8K ≥ 182 | MMLU 171, GSM8K 42 | FAIL (GSM8K) |
| A3 still right, blind | TS A-count ≥ T A-count − 3 (≥ 109) | T 112, TS 107 | FAIL |
| A4 not a refuser | cat 1-4 abstentions ≤ 27 | 0 | PASS |

- A1 detail:
  - The question-level interval is +7.75..+11.34.
  - All 10 conversations went up: +12.88, +12.04, +7.62, +6.34, +5.42, +13.21, +11.27, +9.43, +5.91, +15.08.
  - By category, T → TS: cat 1 24.37 → 29.55, cat 2 19.46 → 36.09, cat 3 16.07 → 14.64, cat 4 32.92 → 42.53.
- A3 detail:
  - 300 cat 1-4 questions were sampled; 300 pairs were judged, none missing.
  - Six blind Opus judges were used, and no judge saw both replies to one question. Labels and key are in audit/.
  - T labels: A 112, B 2, C 68, D 113, E 5. TS labels: A 107, B 2, C 65, D 126, E 0.
  - T → TS: A→A 71, A→C 14, A→D 26, A→B 1, C→A 10, D→A 26, C→D 27, D→C 18, and the rest unchanged or minor.
    See audit/A3-score.json.
  - Relabel agreement: 59 of 60.

## Report only
- Answer length and overlap (bm-391 prf), T → TS:
  - median words 8 → 4;
  - token precision 23.7 → 38.5;
  - token recall 43.6 → 40.5;
  - replies over 3× the gold length 638 → 170.
- Confident wrong (cat 1-4, answered with F1 = 0): 467 → 562. Half right: 333 → 575.
- bm-396 columns, T → TS:
  - all_gold_tokens 402 → 349;
  - zero_overlap 475 → 563;
  - best_span_f1 48.30 → 45.14.
- Category 5:
  - The strict reading fell from 14 to 4.
  - The official reading rose from 15 to 240, but this is an artifact of the official rule. It counts a reply
    without "(a)" as choosing option (b), and (b) is the no-information option half the time. TS almost never
    writes a letter.
- GSM8K:
  - The median reply fell from 103 words to 4: the model stopped showing its working.
  - Under the strict pick ("answer is N" only), T 189 and TS 30.
- MMLU:
  - T gave no letter 234 times out of 300. TS always gives one, with a median of 1 word, which is why 50 → 171.
  - This is a format change, not new knowledge. It also shows that T's MMLU score of 50 mostly measures format.
- Speed, median ms per question (5090), T → TS: LoCoMo 1,584 → 618, MMLU 258 → 43, GSM8K 2,129 → 108.
- Resources: one 1B model resident, as for T, plus the merged weights (2.1 GB, not copied back). The adapter is
  ~/premonition-models/bm397t-adapter397t.pt, 16.6 MB, sha256 621edd16…7233.

## Predictions
| Prediction | Result |
|---|---|
| P1 (45%): A1 passes, point guess +6 | right (+9.57) |
| P2 (60%): A2 passes | wrong (GSM8K 42) |
| P3 (60%): A3 passes | wrong (107 vs 109) |
| P4 (85%): A4 passes | right |
| P5 (75%): dev right after ≥ before, median words after ≤ before | right |
| P6 (35%): all four pass | wrong |

The "proved wrong" line (TS − T < +2.0) was not reached: the practice did carry over to LoCoMo's F1.

## What it means (shown / suggested / untested)
- Shown: a little practice on made-up chats, 1,800 questions for 3 minutes, made the plain 1B answer in about half
  the words, and LoCoMo F1 rose by 9.6 points in every conversation.
- Shown: blind judges found the trained 1B right about as often as before (107 vs 112 of 300). The F1 gain comes
  from shorter wording (precision 23.7 → 38.5), not from more right answers. It is a scoring gain, not better
  memory.
- Shown: the model now answers everything in a few words. It dropped its working on math (GSM8K 191 → 42), and
  it never says it doesn't know (abstentions 7 → 0, confident wrong 467 → 562).
- Suggested: the remaining gap to Qwen3.5-2B (47.87) is mostly about being right, not length. After this change,
  length explains little more.
- Untested:
  - practice that also keeps working on made-up math problems (the base's own graded working) and includes
    unanswerable questions, as one change;
  - switching the adapter on only when answering from a chat (the memory path), never for math or general
    questions.
  Both are queued in design/v3/30-modes/398-benchmarks-followups-2026-09-26.md. Neither is in 0.2c.

## Blind recount: agrees (added ~05:35 UTC)
A separate agent recomputed every number above from the raw files. Its score.json and per_question.json are
byte-identical to score/, and its judge score equals audit/A3-score.json.
- Redrawing random.Random(3972) reproduces the judged sample exactly.
- No judge saw both arms of a question.
- Caveat on blindness: it saw this commit's subject line before computing. It did not open this file.
- One wording note: PLAN.md's "Why" gives T's median answer as 10 words. That is the scored first line (bm-397's
  measure). bm-391's prf script counts whole replies and gives 8. PLAN is sealed and stays as written.

## Outside review, checked against the code (added ~12:05 UTC)
Ben pasted an outside review at 11:50 UTC (saved as reviews/outside-review-bm397t-2026-09-26.md). Each claim was
rechecked here on CPU from the files above.
- True: of T's 112 A-labelled answers, 71 stayed A, 41 were lost (A→B 1, A→C 14, A→D 26) and 36 were gained
  elsewhere. 33 of the 41 losses are category 4 (single-hop); gains were 22 cat 4, 7 cat 2, 4 cat 1, 3 cat 3.
- True: the conversation-level 95% interval of the A-rate change (−1.67 points) is −8.2 to +5.3 (seed 396, 10k).
  So correctness was neither shown to improve nor shown to hold. A3's point-count mark failed, but the data cannot
  tell a small loss from no change.
- True: GSM8K with the sealed pick lost 156 of T's 191 and gained 7. All 300 TS replies contain a number, so this
  is not a parsing failure.
- True, and a correction to the dev lines above: claude_bm397t_data.correct() only checks that every answer word
  appears in the reply. It accepts "Not Varnholt" and "Varnholt or Eskbridge" for "Varnholt". The dev count 199/200
  is word coverage, not semantic accuracy.
- True: training chats are ~1.6k tokens against ~19k (chat text alone, measured here) to ~24k (with the harness
  framing) on LoCoMo. The trainer averages each example's token loss, then averages examples.
- True: best_span_f1 45.14 vs actual 37.07, and Qwen was never blind-judged here. So "the rest of the gap is
  correctness" is not shown. It was said too strongly in the chat and is withdrawn.
