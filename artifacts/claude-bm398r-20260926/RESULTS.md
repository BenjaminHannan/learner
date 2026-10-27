# bm-398r RESULTS: reader adapter trained on made-up long chats (benchmarks thread, written 2026-09-26 16:45 UTC)

**Verdict: FAIL, and proved wrong.**
- The adapter made the plain 1B's answers shorter and raised its word-overlap score by 8.6 points.
- It added no right answers. Blind judges counted 110 right with the adapter against 111 without, on the same 297
  questions.
- Qwen3.5-2B, the same-size bar, had 142. Training on made-up chats teaches the answer's form, not better reading.
- As with bm-397t, the F1 gain is wording.

Every LoCoMo number is "after using LoCoMo for development". Counts only: no question, answer or reply is quoted.
The rental report is on builder-outbox: RESULTS-rent.md and run/.

## Marks (PLAN.md, fixed before the run)

| Mark | Needed | Result |
|---|---|---|
| R1: more right answers, blind | TR's A-count ≥ T's + 15, and the conversation interval of TR − T above 0 | TR 110, T 111. TR − T = −0.3 points, 95% interval −5.43 to +5.26. **Fail** |
| R2: better scored | TR's F1 on categories 1-4 ≥ 32.50, and the interval above 0 | 36.09 against 27.50 (+8.59, interval +6.69 to +10.76). Pass |
| R3: not a refuser | TR's abstentions ≤ T's + 20 (27) | 5 against 7. Pass |
| Proved wrong | TR − T ≤ 0 points blind | −0.3. **Yes** |

## Blind check (7 judges, then an independent recount)

| Arm | A right | B | C partly | D wrong | E don't know |
|---|---|---|---|---|---|
| T: plain 1B, whole chat | 111 | 3 | 58 | 120 | 5 |
| TR: 1B plus adapter, whole chat | 110 | 0 | 51 | 135 | 1 |
| Q2: Qwen3.5-2B, whole chat | 142 | 1 | 66 | 88 | 0 |

- **TR against T:** 38 gained and 39 lost.
- **TR against Q2:** −10.8 points (interval −17.28 to −3.94), with 27 gained and 59 lost.
- **By category, A-count for T / TR / Q2:**
  - 1, multi-hop (53): 9 / 11 / 12
  - 2, dates (58): 5 / 9 / 11
  - 3, open (19): 4 / 3 / 6
  - 4, single fact (167): 93 / 87 / 113
- **T label to TR label:** A→A 72, A→C 6, A→D 33, C→A 10, D→A 27, D→D 75; other cells 74.
- **Relabel agreement: 60 of 60.** This is higher than bm-398d's 114 of 120. A paths-only check of the relabel
  judge's tool calls shows it opened only its own folder, so the result stands.
- **Recount:** a separate agent read only key.json and the labels, wrote its own code, and got every count above.
- **Size counts (Ben's rule):**
  - TR: biggest single model 1B (MiniCPM5-1B plus a 4.1M-parameter adapter, merged), 1B resident.
  - Qwen3.5-2B: 2B biggest and resident.

## Report only
- **F1 by category, T → TR:**
  - 1: 24.37 → 26.33
  - 2: 19.46 → 35.44
  - 3: 16.07 → 12.72
  - 4: 32.92 → 42.28
- **Other scored counts:** confident-wrong 467 → 629; half-right 333 → 565. Median words in the first line:
  10 → 4.
- **Adapter always on (the misroute cost):**
  - GSM8K 20 of 300, against the base's 191 in bm-390;
  - MMLU 137 of 300, against the base's 50, which mostly measures answer format.
  - This is why the bm-398i switch matters.
- **Evidence arms on the 297, adapter against base on the same GPU (F1):**
  - right lines only: 52.81 vs 46.99;
  - right lines plus store: 45.35 vs 39.49;
  - store top 20: 36.62 vs 29.83.
- **Dev (made-up chats, held-out names and wordings):** 114 → 186 of 240 (+72). Dates stayed hardest: 4 → 14 of 61.
- **Training:** 225 steps, 1,241 s, 13.4M tokens, loss 1.20 → 0.20 (first and last 10 steps), peak 7.1 GB.
  - Adapter sha256 f98c54a9…cfdf, kept on the Mac, never pushed.
  - Rental cost about $0.65 of the $1.50 cap.

## Predictions
- P1 (35%) R1 passes: wrong.
- P2 (85%) R2 passes: right.
- P3 (85%) R3 passes: right.
- P4 (30%) PASS: wrong.
- P5 (10%) TR's A-count ≥ Q2's: wrong.
- P6 (70%) not proved wrong: **wrong**.
- P7 (80%) dev rises by 30 or more: right (+72).
- P8 (60%) GSM8K with the adapter always on drops by 20 or more: right (191 → 20).

## Corrections and deviations
- **Training text.** The PLAN says "No model output, teacher or Claude-written text is used." That was too strong.
  - No model wrote any text, and code made every chat and every answer.
  - But the building blocks in scripts/claude_bm398r_data.py were written by Claude: about 15 small-talk templates,
    142 fill-in phrases, 14 question-wording sets and the fact sentences.
  - Under the 16:39 UTC rule on the goals page (nothing a model trains on is written by Claude), this adapter stays
    out of every build whatever it scored. The Thread manager was told at 16:44.
- **Header time.** The PLAN header says ~14:50 UTC; the sealing commit cf7301f5d is at 14:36 UTC.
- **Rental:** the first training launch lacked nltk. It was installed on the rental only and the identical command
  relaunched once. No code was edited.

## What follows
- **This route stops.** The PLAN's "proved wrong" line applies: training the 1B on made-up chats does not add right
  answers. That's two adapters now (bm-397t, bm-398r) that changed the wording but not the correctness.
- **Brain first:** recall is finding the episode and then re-reading it. This adapter learned what an answer looks
  like, not how to find and re-read the right lines in a real chat. On LoCoMo, 20 lines gave a 1B the answer 137
  times against 109 for the whole chat (bm-398d).
- **Problem #4 now rests on three things:**
  - bm-398n (sealed 94833d852): do the reader's notes give more right answers?
  - bm-398e: the trimmer. Its verdict stands, but it will not be extended under the Redirect.
  - The rival harness, where the headline comparison lives.
- **Size is the bar.** Qwen3.5-2B is right 31 more times than the plain 1B on the same questions.
