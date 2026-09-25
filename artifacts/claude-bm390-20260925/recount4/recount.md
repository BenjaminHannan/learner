# bm390 blind recount 4 (2026-09-25)

This recount was written from scratch using the registered rules and the LoCoMo repo's `task_eval/evaluation.py` and `task_eval/hf_llm_utils.py`. It did not read the first scorer's script, its output, or `recount3/`. This file and `recount.json` contain only counts, scores, ids and hashes. To reproduce, run `<scratchpad>/venv/bin/python -B recount.py` (Python 3.11.15, numpy 2.4.6, nltk 3.10.3). It takes about 8 s.

## LoCoMo: mean F1 x 100

The headline covers categories 1-4 (n = 1,540). The reply is cleaned first as in `hf_llm_utils.get_hf_answers`.

| arm | headline cat 1-4 | cat 1 (n=282) | cat 2 (n=321) | cat 3 (n=96) | cat 4 (n=841) |
|---|---|---|---|---|---|
| T   | **27.4976** | 24.3718 | 19.4644 | 16.0658 | 32.9168 |
| C   | **3.2652**  | 3.6465  | 0.6517  | 9.7067  | 3.3995  |
| L12 | **19.0116** | 19.4585 | 22.9118 | 15.2395 | 17.8037 |
| Q2  | **47.8691** | 36.2879 | 34.3732 | 14.7194 | 60.6878 |

Q2 is parts 1-5 joined: 304 + 453 + 400 + 429 + 400 = 1,986 rows with 1,986 unique qids. The set of qids equals the data set.

Two variants are reported for reference only (neither is the headline):

| arm | repo stores per-item F1 rounded to 3 dp | no reply clean-up (raw reply) |
|---|---|---|
| T   | 27.4982 | 26.4708 |
| C   | 3.2656  | 3.2652  |
| L12 | 19.0114 | 19.0116 |
| Q2  | 47.8697 | 47.8811 |

Category 5 is not part of the headline (n = 446). It uses the repo's rule that the reply contains "no information available" or "not mentioned", applied to the cleaned reply. See interpretation 3 for caveats.

| arm | hits | % |
|---|---|---|
| T | 13 | 2.91 |
| C | 68 | 15.25 |
| L12 | 35 | 7.85 |
| Q2 | 12 | 2.69 |

## Paired bootstrap, LoCoMo categories 1-4 (F1 x 100)

Settings: 10,000 resamples, `numpy.random.default_rng(390)`, n = 1,540, 95% percentile interval.

| comparison | point difference | 95% CI | share of resamples <= 0 |
|---|---|---|---|
| Q2 - T  | +20.3715 | [18.4279, 22.3205] | 0.0000 |
| L12 - T | -8.4860  | [-10.0341, -6.9085] | 1.0000 |

The following choices change the interval by at most 0.05:

- **Separate draws per comparison** (Q2 first, then L12, from one generator): L12 - T becomes [-10.0639, -6.9156] and Q2 - T is unchanged.
- **Items sorted by qid string:** Q2 - T becomes [18.4728, 22.3508] and L12 - T becomes [-10.0795, -6.8800].
- **Sampler:** `rng.choice` gives the same indices as `rng.integers`.

## MMLU (n = 300)

| arm | right / 300 | % | no pickable letter | picked by "answer/option" pattern | picked by fallback |
|---|---|---|---|---|---|
| T   | 50  | 16.67 | 234 | 3 | 63 |
| Q2  | 201 | 67.00 | 0   | 0 | 300 |
| L12 | 159 | 53.00 | 2   | 0 | 298 |

The counts are the same under two looser readings: (a) at most one space around the optional ':' or '-'; (b) treating Unicode letters as "letters" for adjacency.

## GSM8K (n = 300)

| arm | right / 300 | % | number after last "The answer is" | no phrase, used last number | phrase present, no number after it |
|---|---|---|---|---|---|
| T   | 190 | 63.33 | 289 | 10 | 1  |
| Q2  | 209 | 69.67 | 292 | 8  | 0  |
| L12 | **165** | 55.00 | 217 | 10 | **73** |

**Sensitivity:** if a reply that has the phrase but no number after it falls back to the last number in the reply, the results become T 191, Q2 209, L12 **217**. See interpretation 6.

## Rules I had to interpret

1. **LoCoMo clean-up.** I copied the non-category-5 branch of `get_hf_answers` exactly:
   - replace backslash-quote with an apostrophe, then strip;
   - keep the first line (the repo's `isspace()` filter never removes anything, so this is simply line 1);
   - lowercase and remove `(a)`, `(b)`, `a)`, `b)` and `answer:`;
   - strip again.

   This matters only for T: 130 of its cat 1-4 replies are multi-line (+1.03 on the headline compared with the raw reply). Q2 has 8 multi-line replies, and C and L12 have none.
2. **LoCoMo scoring.** I used the repo's `eval_question_answering` rules, with `str(gold)` (6 golds are integers). Category 3 keeps only the gold before ';'. Category 1 uses `f1` (split on commas and take the best match for each gold part). Categories 2-4 use `f1_score`. The headline is the mean of the unrounded per-item F1. The repo rounds each item to 3 dp before averaging, which shifts each headline by less than 0.001. I checked my version against the repo's own `evaluation.py` functions, imported with a dummy `bert_score` stub: 7,944 of 7,944 item scores match, with 0 mismatches.
3. **Category 5.** The repo turns category 5 into an (a)/(b) choice and maps the letter back to the option text before scoring. Our runs did not use that setup. I applied the repo's substring test to the cleaned reply, so these numbers are indicative only.
4. **MMLU pattern.** The pattern is `(?i:answer is|answer|option)\s*[:\-]?\s*\(?([A-D])(?![A-Za-z])`, with no word boundary before the keyword. The fallback is the first `[A-D]` with no ASCII letter on either side.
   - Q2 and L12 replies are almost all a bare letter.
   - T replies are prose of about 80-140 characters. 234 of them contain no uppercase A-D letter at all, so they cannot be picked under any reading.
   - 11 of T's 63 fallback picks come from prose rather than a bare letter, and only 3 of those 11 are right. This is probably a sentence-initial article "A".
5. **GSM8K gold.** `gsm8k300.jsonl` already holds the final answer, with no "####". I checked it against the text after "####" in `gsm8k_test.parquet`, row = qid index: 300 of 300 match. Numbers are matched with `-?\d[\d,]*(?:\.\d+)?`, commas are stripped, and values are compared as floats (tolerance 1e-9). The "number after" the phrase is the first number anywhere after the last occurrence.
6. **GSM8K: phrase present but no number after it.** Under the registered rule as written, these replies count as wrong. The rule's fallback to the last number applies only when the phrase is absent.
   - All 73 such L12 replies end with the same 3-character non-numeric tail right after the phrase: a space, a capital letter and one non-letter. This looks like an echoed format placeholder.
   - In 52 of the 73, the last number before the phrase equals the gold.
   - The choice moves L12 from 165 to 217 (55.0% to 72.3%), so it should be settled explicitly.
7. **Bootstrap.**
   - Items are in `locomo10.json` order (conversation, then qa index), categories 1-4 only.
   - One index matrix, `rng.integers(0, n, (10000, n))`, is shared by both comparisons.
   - The difference is computed per resample as mean(arm) - mean(T), x 100.
   - The interval is `np.percentile(..., [2.5, 97.5])`.

## Integrity checks

- LoCoMo: 1,986 questions in total. Categories 1/2/3/4/5 have 282/321/96/841/446, so categories 1-4 total 1,540.
- Every LoCoMo arm file has exactly 1,986 unique qids. They match the data set, and none of the `category` fields disagree with the data.
- MMLU gold letters match the `answer` index in `data390/mmlu/<subject>.arrow` for 300 of 300 questions.

Per-item sha256 digests are in `recount.json`. Each digest is taken over lines of the form "qid\tscore(%.6f)", in data order for LoCoMo categories 1-4 and in sorted qid order for MMLU and GSM8K. The file also has input-file sha256s and the per-item LoCoMo F1 for all 1,986 qids and 4 arms, for diffing against the first scorer.
