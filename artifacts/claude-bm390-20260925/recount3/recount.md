# bm-390 blind recount

Independent recount of the bm-390 run files. I did not open the other scorer's outputs (score390/, VERIFY*, score.json, per_question.json) and did not run claude_bm390_score.py. From that file I read only the ABSTAIN regex, `mmlu_pick` and `gsm_pick` (with the three regexes they use, `MMLU_FIRST`, `MMLU_ANY` and `NUM`). This report and recount.json hold only counts, scores, hashes and ids. They contain no question, gold answer or reply text.

Script: `out/recount.py` (sha256 c16cd5575e4505ed7cccbe79455d2161a568b1059c150a4268fd2087869969ac). Full numbers: `out/recount.json`.

## 1. Validity

All 7 run files match RESULTS-benspc3.md on sha256, bytes, rows and CRLF count.

| file | rows | unique qids | CRLF | sha256 (first 16) | matches report |
|---|---|---|---|---|---|
| locomo_P.jsonl | 1986 | 1986 | 0 | 01df3f97943911a3 | yes |
| locomo_P_bare.jsonl | 1986 | 1986 | 0 | 6cc23aa16c855030 | yes |
| locomo_Rb.jsonl | 1986 | 1986 | 0 | af15f49e14d89669 | yes |
| mmlu_P.jsonl | 300 | 300 | 0 | 81aef79fe0cd78b5 | yes |
| gsm8k_P.jsonl | 300 | 300 | 0 | 1b94b4507be7b816 | yes |
| sleep_P.jsonl | 272 | n/a | 0 | 7694e95e8a655e6f | yes |
| locomo_P_reading.jsonl | 10 | n/a | 0 | 255f8ca78925b0f7 | yes |

- LoCoMo gold: 10 conversations and 1,986 questions (cat 1: 282, cat 2: 321, cat 3: 96, cat 4: 841, cat 5: 446), so 1,540 questions in categories 1-4.
- Every LoCoMo arm (P, P_bare, Rb) has 0 missing gold qids, 0 extra rows, 0 duplicate qids, 0 category mismatches against the gold file and 0 empty replies. Each file's rows are in gold order, and no reply is empty after the official clean-up.
- MMLU and GSM8K: 300 of 300 gold qids present in each, with 0 extra rows, 0 duplicates and 0 empty replies.
- sleep_P.jsonl: 272 rows. checkpoint_exists is true in 272 rows, attempted is true in 0 and accepted is true in 272. There is 1 distinct reason in all 272 rows, a system log string: "0 word episodes (< 8); kept queued, nothing to gate".
- locomo_P_reading.jsonl sums: stored_triples_after_reading 18, sessions 272, sleeps 272, check_questions_asked 2,334 (turns_fed 6,164).

## 2-3. LoCoMo official F1 (categories 1-4, mean F1 x100)

Method: each reply is cleaned as in `get_hf_answers` (hf_llm_utils.py): replace `\"`, keep the first line, lower-case, strip `(a)`, `(b)`, `a)`, `b)` and `answer:`. It is then scored with the category 1-4 rules of `eval_question_answering` in evaluation.py: `normalize_answer`, Porter stemming, multi-answer F1 for category 1, and the first ';' part of the gold for category 3. The abstain regex is matched against the raw reply, lower-cased. "Confident wrong" means the reply does not match the abstain regex and its official F1 is 0.

| arm | cat 1 (282) | cat 2 (321) | cat 3 (96) | cat 4 (841) | all 1-4 (1540) | abstain | confident wrong |
|---|---|---|---|---|---|---|---|
| P | 3.05 | 1.73 | 5.31 | 3.17 | 2.98 | 923 | 450 |
| P_bare | 0.89 | 0.12 | 1.81 | 1.66 | 1.21 | 1285 | 197 |
| Rb | 13.63 | 26.93 | 12.06 | 29.65 | 25.06 | 48 | 615 |

Sensitivity checks (not the headline numbers):
- The LoCoMo driver rounds each question's F1 to 3 decimals before averaging. Doing the same changes none of the numbers above at 2 decimals.
- Scoring the raw reply with no clean-up gives P 3.00, P_bare 1.21 and Rb 25.02 overall.
- Replies of more than one line in categories 1-4 (the clean-up keeps only the first line): P 85, P_bare 1, Rb 10.

## 4. Paired bootstrap, categories 1-4 (1,540 questions)

| comparison | mean diff x100 | 95% CI | wins / losses / ties |
|---|---|---|---|
| P minus Rb | -22.07 | [-23.63, -20.54] | 109 / 836 / 595 |
| P_bare minus Rb | -23.85 | [-25.37, -22.35] | 61 / 868 / 611 |

Method: a fresh `numpy.random.default_rng(390)` for each comparison, one call to `rng.integers(0, n, size=(10000, n))`, and `np.percentile` at 2.5 and 97.5 with the default linear method. Drawing the 10,000 resamples one at a time in a loop gives the same intervals. Reusing one generator for both comparisons, P first, changes only the P_bare interval, to [-25.38, -22.34].

## 5. MMLU and GSM8K (arm P), with my reimplementation of the registered picking rules

| task | right / 300 | % | no pick | abstain regex hits |
|---|---|---|---|---|
| MMLU | 85 | 28.33 | 134 | 61 |
| GSM8K | 29 | 9.67 | 257 | 251 |

- MMLU counts a question right when `mmlu_pick(reply)` equals the gold letter. Picks: A 49, B 40, C 42, D 35, none 134.
- GSM8K counts a question right when `gsm_pick(reply)` equals float(gold). A tolerance of 1e-6 gives the same 29. The rule that compares the pick with gold lives in a part of the scorer I was not allowed to read, so this comparison is my assumption.

## 6. What looked wrong or surprising (counts)

1. **Sleep never ran in P.** All 272 sleep rows have attempted = false, yet accepted = true (272 of 272 rows where attempted is false and accepted is true). Every row gives the same reason: 0 word episodes (< 8), so nothing was queued to learn.
2. **Very little stored while reading.** Reading 6,164 turns across 10 conversations stored 18 triples in total, and 1 conversation stored 0. P also asked 2,334 check questions.
3. **P abstains on most questions.**
   - LoCoMo categories 1-4: 923 of 1,540 P replies match the abstain regex (P_bare 1,285, Rb 48).
   - GSM8K: 251 of 300 replies match it and 257 contain no number to pick.
   - MMLU: 134 of 300 replies have no letter to pick, 58 of which match the abstain regex. 85 of 300 right is close to the 25% chance rate.
4. **P_bare wrote memory during a question.** P_bare has question_turn_writes > 0 in 1 row (sum 2), while P has 0 such rows. A "bare" arm might be expected never to write.
5. **Category 5 is not scored here.** Each arm has 446 category 5 rows, and all are present. Abstain-regex hits among them: P 110, P_bare 313, Rb 34.
6. **Structural checks were all clean.** There were no duplicate qids, missing or extra rows, category mismatches, empty replies, CRLF sequences or hash mismatches in any file.

## Commands run

```
R=/tmp/claude-0/-home-user-learner/7058353c-6d6a-5191-a096-07082a743674/scratchpad/recount390
PY=/tmp/claude-0/-home-user-learner/7058353c-6d6a-5191-a096-07082a743674/scratchpad/venv/bin/python   # numpy 2.4.6, regex 2026.9.10, nltk 3.10.3
# read the rules (only these lines of the other scorer)
sed -n '37,42p;179,200p' /home/user/learner/scripts/claude_bm390_score.py
cat .../locomo_code/repo/task_eval/evaluation.py .../hf_llm_utils.py .../evaluate_qa.py
# key/type probe of every file (counts only), gold-answer type counts
python3 - <<EOF ... EOF ; $PY - <<EOF ... EOF
# the recount
cd $R/out && $PY -B recount.py $R > recount_stdout.txt
# extra count-only checks (reply lengths, abstain hits on MMLU/GSM8K/cat 5, per-conversation reading counts, synthetic-string tests of f1/clean-up)
$PY -B - <<EOF ... EOF
```
