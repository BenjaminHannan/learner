# Fable test on the WIDE 10M question: error overlap, per-term loss, call rate

Scope: small card experiments only (34 question families, pooled-5 dev rows). It says nothing about a larger final model.

Inputs: 6200 dev rows in both runs (yes: identical (id, split, family) rows and gold_mode). Train sample: identical: train_sample.jsonl has the same sha256 in both runs. Models: s400 = run A tag 3M, deep = run A tag 10M, s401 = run B tag 3M, wide = run B tag 10M.

## Verdict by mark

| Mark | What is measured | Value | Threshold (pre-registered) | Result | Counts |
|---|---|---|---|---|---|
| P1a | WIDE miss overlap with 3M s400 (share of WIDE misses that s400 also misses), pooled-5 | 88.7% (1434/1617) | at least 80% | **PASS** | yes |
| P1b | WIDE overlap within 5 points of the seed baseline (s401 vs s400 overlap), pooled-5 | abs(88.7 - 87.8) = 0.9 points | at most 5 points | **PASS** | yes |
| P1c | deep overlap with s400 LOWER than the seed baseline (s401 vs s400) by 8 points, 21 non-calc families (primary reading) | 87.0 - 89.0 = -2.0 points | at least 8 points lower | **FAIL** | yes |
| P1c-alt | same, but lower than WIDE overlap with s400 on the 21 non-calc families (alternative reading) | 88.4 - 89.0 = -0.5 points | at least 8 points lower | **FAIL** | no |
| P2a | task-row (non-web) total train loss, s400 / deep / wide | 0.1115 / 0.1037 / 0.0895 | at most 0.10 for each | **FAIL** | yes |
| P2b | task-row total loss cross-size differences (deep minus s400, wide minus s400) | -0.0078 / -0.0220 | absolute value at most 0.02 | **FAIL** | yes |
| P2c | web-fill GEN loss cross-size differences (deep minus s400, wide minus s400) | -0.0084 / 0.0257 | absolute value at most 0.03 | **PASS** | yes |
| P3a | call rate (chosen mode == NUM) pooled over the 4 zero-coverage families, every checkpoint (s400 / deep / s401 / wide) | 0.0% / 0.0% / 0.0% / 0.1% | at most 10% for each | **PASS** | yes |
| P3a-raw | same with the raw mode head (raw_mode == NUM) | 0.0% / 0.0% / 0.0% / 0.1% | at most 10% for each | **PASS** | no |
| P3b | family accuracy difference to s400, deep and wide, each of the 4 families and pooled (largest shown) | 13.0 points (deep on rule_apply) | at most 2 points | **FAIL** | yes |

**E1 (capacity is not the binding limit on this card) is NOT SUPPORTED by the pre-registered marks: 4 of 8 counted marks pass, fail: P1c, P2a, P2b, P3b.**

- P1c-alt: shown for completeness; the verdict uses P1c
- P3a: raw_mode==0 agrees within 5 points
- P3a-raw: shown for completeness; the verdict uses chosen
- P3b: all differences must pass; s401 minus s400 is in the Part 3 table as a noise reference

Results that Fable said would prove E1 wrong:

| Rule | Condition | Value | Applies? |
|---|---|---|---|
| W1 | miss overlap < 60%: the models fail on different rows, seed-noise-limited, the only honest spend is seeds | WIDE vs s400 88.7%; deep vs s400 89.7%; s401 vs s400 87.8% | no |
| W2 | task-row loss >= 0.25 for all sizes and still equal: schedule-limited (E3), a longer or hotter 3M run is next | s400 0.1115 / deep 0.1037 / wide 0.0895 | no |
| W3 | 10M task-row loss >= 0.05 below 3M while dev misses are unchanged: capacity is used for memorisation only | deep: loss lower by 0.0078, dev gain 1.66 points; wide: loss lower by 0.0220, dev gain 0.20 points | no |

Failing a mark does not prove E1 wrong; only the rows above do. Overall flag: wrong rules that apply = none.

## Claims

- **shown**: Pooled-5, 6040 rows. WIDE misses 1617; 1434 of them (88.7%) are also misses of 3M s400. The seed baseline (s401 vs s400) is 87.8% (1390/1583). Deep vs s400 is 89.7% (1372/1529).
- **shown**: Discordant rows (X wrong, base right / X right, base wrong) with exact two-sided binomial p: WIDE vs s400 183/195 (p 0.572); deep vs s400 157/257 (p 0.000); s401 vs s400 193/239 (p 0.030).
- **shown**: 21 non-calculator families (3600 rows): overlap with s400 is deep 89.0%, WIDE 88.4%, s401 87.0%. Deep is lower than the seed baseline by -2.0 points and lower than WIDE by -0.5 points.
- **shown**: Task-row (non-web) total train loss: 3M s400 0.1115, deep 10M 0.1037, 3M s401 0.1001, WIDE 10M 0.0895. Web-fill GEN loss: 3M s400 1.7153, deep 10M 1.7069, 3M s401 1.7244, WIDE 10M 1.7410.
- **shown**: Four zero-coverage families (720 pooled-5 rows, gold mode NUM in 3.9% of them). Rate of chosen mode == NUM: 3M s400 0.0%, deep 10M 0.0%, 3M s401 0.0%, WIDE 10M 0.1%. Accuracy: 3M s400 30.3%, deep 10M 35.3%, 3M s401 31.0%, WIDE 10M 33.1%.
- **shown**: WIDE pooled-5 recomputed here: 4423/6040 = 73.228% against the readout's 4429/6040 = 73.328% (difference -6 rows).
- **suggested**: WIDE misses nearly the same rows as 3M s400, about as many as a second 3M seed does, so on this card it looks like one more seed of the small model.
- **suggested**: On the 21 non-calculator families deep shows no clear extra change in which rows are missed compared with a new seed (P1c fails at the pre-registered 8 points).
- **suggested**: The task-row loss is above 0.10 for at least one size, so "the training rows are solved" does not hold in this teacher-forced measurement.
- **suggested**: A row-level McNemar p-value compares two fixed checkpoints; it is not a measure of training-seed noise. With one training run per condition the s401 vs s400 pair is the better yardstick.
- **untested**: Whether the data manifests differ in content. Recorded hashes: 3M s400 and deep 133e463e, 3M s401 4ad1440e, WIDE 8ee0b3ee (copied from the RESULT.json files, not recomputed here). The seed baseline therefore differs in seed and manifest, and WIDE differs from deep in manifest.
- **untested**: Whether the runs are schedule-limited (E3): no learning-curve slope is measured here.
- **untested**: Whether the "do not call" weighting of rows without a program causes the low zero-coverage scores: only call rates and accuracies are measured, no change is made.
- **untested**: Anything about a larger final model.

## Plain-language summary for Ben (a high-school senior)

We took four saved small models and checked, question by question, which ones get the same questions wrong. Two of them differ only in their random start, and of the questions one of them gets wrong, about 88 out of every 100 are also wrong for the other, so that is the overlap plain luck gives. The wide model shares 89 out of 100 of its wrong answers with the first small model, which is close to that luck level, so it acts like one more random start. The deep model shares only 89 out of 100 on the 21 question types that need no calculator, against 87 for the luck level, so depth did not clearly change which questions it misses. On the practice questions that need a skill, the three models make mistakes scoring 0.11, 0.10, 0.09 (0 would be perfect), and the sizes differ by more than we allowed. On the four question types that never use the calculator in training, the models print a calculator-style number in at most 0 out of every 100 rows, and their scores move by more than 2 points across sizes. Of the 8 checks we fixed before looking, 4 passed, so the idea that making the model bigger is not what limits it on this card is not supported. This covers only the small card experiments with one training run each, so it says nothing about a bigger final model.

## Limits

- One training run per condition (s400, deep, s401, wide). The seed baseline is a single pair (s401 vs s400), and s401 also has a different data manifest from s400.
- g1diag recomputed every row (run A on cpu/fp32, run B on cpu/fp32) while the original numbers come from GPU runs in bf16, so a few rows can differ; the WIDE cross-check in the detail tables shows the size of that difference.
- Per-term losses are g1diag numbers, which it describes as batch means weighted by rows (approximate; batches of 64), teacher forced in eval mode on a sample of 2,000 web + 2,000 task rows. They are not the logged training loss. On my reading of loss() in ledger.py at 612f5c5b01, each of the six terms used here is a sum over rows divided by the batch size, so the row weighting gives their exact row mean; only op_acc and copy_share (not used here) are truly approximate.
- "Overlap(X|base)" = rows both miss / rows X misses: the share of X's misses that the base also misses. It depends on how many misses X has and is not symmetric. Jaccard is also given.
- "Call rate" is the share of rows whose chosen output mode is NUM (the value of the number slot the answer pointer picks is printed). That includes pointing at a number that was in the prompt, so it is not a literal count of calculator calls. The raw mode head (raw_mode == NUM) is shown next to it.
- Part 3 uses the 5 pooled-5 splits (720 rows in the 4 families in the real dev set), so a 2-point accuracy mark is a few rows per family and is tight compared with seed noise.
- The 13 calculator and 21 non-calculator blocks are the pooled-5 rows whose family is (or is not) in the g1diag list of 13; the held-out families of the sixth dev split are in neither block.
- P1c has two readings; the verdict flag uses the seed baseline, the other is printed as P1c-alt and does not count.

## Detail tables

### Part 1: miss overlap and McNemar (rows are pooled-5)

Overlap(X|base) = rows both miss / rows X misses. b = X wrong and base right, c = X right and base wrong; p is the exact two-sided binomial test on b vs c.

**pooled-5 (all 12 ordered pairs; the six that matter first)**, 6040 rows

| X | base | misses X | misses base | both | overlap % | Jaccard % | b | c | p |
|---|---|---|---|---|---|---|---|---|---|
| WIDE 10M | 3M s400 | 1617 | 1629 | 1434 | 88.7 | 79.1 | 183 | 195 | 0.5716 |
| deep 10M | 3M s400 | 1529 | 1629 | 1372 | 89.7 | 76.8 | 157 | 257 | 0.0000 |
| 3M s401 | 3M s400 | 1583 | 1629 | 1390 | 87.8 | 76.3 | 193 | 239 | 0.0303 |
| WIDE 10M | 3M s401 | 1617 | 1583 | 1372 | 84.8 | 75.1 | 245 | 211 | 0.1222 |
| deep 10M | 3M s401 | 1529 | 1583 | 1330 | 87.0 | 74.6 | 199 | 253 | 0.0126 |
| WIDE 10M | deep 10M | 1617 | 1529 | 1354 | 83.7 | 75.6 | 263 | 175 | 0.0000 |
| 3M s400 | deep 10M | 1629 | 1529 | 1372 | 84.2 | 76.8 | 257 | 157 | 0.0000 |
| 3M s400 | 3M s401 | 1629 | 1583 | 1390 | 85.3 | 76.3 | 239 | 193 | 0.0303 |
| 3M s400 | WIDE 10M | 1629 | 1617 | 1434 | 88.0 | 79.1 | 195 | 183 | 0.5716 |
| deep 10M | WIDE 10M | 1529 | 1617 | 1354 | 88.6 | 75.6 | 175 | 263 | 0.0000 |
| 3M s401 | deep 10M | 1583 | 1529 | 1330 | 84.0 | 74.6 | 253 | 199 | 0.0126 |
| 3M s401 | WIDE 10M | 1583 | 1617 | 1372 | 86.7 | 75.1 | 211 | 245 | 0.1222 |

**13 calculator families (pairs that matter)**, 2440 rows

| X | base | misses X | misses base | both | overlap % | Jaccard % | b | c | p |
|---|---|---|---|---|---|---|---|---|---|
| WIDE 10M | 3M s400 | 280 | 270 | 252 | 90.0 | 84.6 | 28 | 18 | 0.1839 |
| deep 10M | 3M s400 | 271 | 270 | 253 | 93.4 | 87.8 | 18 | 17 | 1.0000 |
| 3M s401 | 3M s400 | 277 | 270 | 254 | 91.7 | 86.7 | 23 | 16 | 0.3368 |
| WIDE 10M | 3M s401 | 280 | 277 | 259 | 92.5 | 86.9 | 21 | 18 | 0.7493 |
| deep 10M | 3M s401 | 271 | 277 | 253 | 93.4 | 85.8 | 18 | 24 | 0.4408 |
| WIDE 10M | deep 10M | 280 | 271 | 247 | 88.2 | 81.2 | 33 | 24 | 0.2892 |

**21 non-calculator families (pairs that matter)**, 3600 rows

| X | base | misses X | misses base | both | overlap % | Jaccard % | b | c | p |
|---|---|---|---|---|---|---|---|---|---|
| WIDE 10M | 3M s400 | 1337 | 1359 | 1182 | 88.4 | 78.1 | 155 | 177 | 0.2491 |
| deep 10M | 3M s400 | 1258 | 1359 | 1119 | 89.0 | 74.7 | 139 | 240 | 0.0000 |
| 3M s401 | 3M s400 | 1306 | 1359 | 1136 | 87.0 | 74.3 | 170 | 223 | 0.0086 |
| WIDE 10M | 3M s401 | 1337 | 1306 | 1113 | 83.2 | 72.7 | 224 | 193 | 0.1417 |
| deep 10M | 3M s401 | 1258 | 1306 | 1077 | 85.6 | 72.4 | 181 | 229 | 0.0202 |
| WIDE 10M | deep 10M | 1337 | 1258 | 1107 | 82.8 | 74.4 | 230 | 151 | 0.0001 |

### Part 2: teacher-forced train loss per term (means over the shared sample)

| rows | model | n | total | prog | mode | ans | word | gen |
|---|---|---|---|---|---|---|---|---|
| task rows | 3M s400 | 2000 | 0.1115 | -0.0055 | 0.0067 | 0.0039 | 0.0254 | 0.0810 |
| task rows | deep 10M | 2000 | 0.1037 | -0.0055 | 0.0073 | 0.0040 | 0.0243 | 0.0735 |
| task rows | 3M s401 | 2000 | 0.1001 | -0.0054 | 0.0055 | 0.0043 | 0.0206 | 0.0750 |
| task rows | WIDE 10M | 2000 | 0.0895 | -0.0055 | 0.0052 | 0.0032 | 0.0193 | 0.0673 |
| web fill-in rows | 3M s400 | 2000 | 2.4760 | 0.0000 | 0.4480 | 0.0000 | 0.3128 | 1.7153 |
| web fill-in rows | deep 10M | 2000 | 2.4685 | 0.0000 | 0.4493 | 0.0000 | 0.3124 | 1.7069 |
| web fill-in rows | 3M s401 | 2000 | 2.6345 | 0.0000 | 0.4811 | 0.0000 | 0.4290 | 1.7244 |
| web fill-in rows | WIDE 10M | 2000 | 2.5008 | 0.0000 | 0.4453 | 0.0000 | 0.3144 | 1.7410 |

Differences to 3M s400:

| rows | comparison | total | prog | mode | ans | word | gen |
|---|---|---|---|---|---|---|---|
| task rows | deep 10M minus 3M s400 | -0.0078 | 0.0000 | 0.0006 | 0.0001 | -0.0011 | -0.0075 |
| task rows | WIDE 10M minus 3M s400 | -0.0220 | 0.0000 | -0.0016 | -0.0006 | -0.0061 | -0.0138 |
| task rows | 3M s401 minus 3M s400 | -0.0114 | 0.0000 | -0.0012 | 0.0005 | -0.0047 | -0.0060 |
| web fill-in rows | deep 10M minus 3M s400 | -0.0075 | -0.0000 | 0.0013 | 0.0000 | -0.0004 | -0.0084 |
| web fill-in rows | WIDE 10M minus 3M s400 | 0.0248 | -0.0000 | -0.0026 | 0.0000 | 0.0017 | 0.0257 |
| web fill-in rows | 3M s401 minus 3M s400 | 0.1585 | -0.0000 | 0.0332 | 0.0000 | 0.1163 | 0.0091 |

Gold log-likelihood on the dev rows (teacher-forced loss, pooled-5; per family in the JSON):

| model | total | prog | mode | ans | word | gen |
|---|---|---|---|---|---|---|
| 3M s400 | 1.870 | 0.893 | 0.254 | 0.049 | 0.262 | 0.413 |
| deep 10M | 1.762 | 0.753 | 0.245 | 0.056 | 0.308 | 0.400 |
| 3M s401 | 1.858 | 0.956 | 0.156 | 0.050 | 0.307 | 0.389 |
| WIDE 10M | 1.954 | 1.004 | 0.192 | 0.060 | 0.301 | 0.398 |

### Part 3: the four zero-coverage families (pooled-5 rows)

gold NUM % is the share of rows whose label says the answer is a number slot. call % = chosen mode NUM; raw % = mode head says NUM; acc % = family accuracy. false call % = chosen NUM where the label is not NUM.

| family | n | gold NUM % | model | call % | raw % | acc % | false call % |
|---|---|---|---|---|---|---|---|
| table_lookup | 200 | 10.5 | 3M s400 | 0.0 | 0.0 | 27.0 | 0.0 |
| table_lookup | 200 | 10.5 | deep 10M | 0.0 | 0.0 | 31.0 | 0.0 |
| table_lookup | 200 | 10.5 | 3M s401 | 0.0 | 0.0 | 31.0 | 0.0 |
| table_lookup | 200 | 10.5 | WIDE 10M | 0.0 | 0.0 | 28.5 | 0.0 |
| seq_next | 160 | 0.0 | 3M s400 | 0.0 | 0.0 | 33.1 | 0.0 |
| seq_next | 160 | 0.0 | deep 10M | 0.0 | 0.0 | 35.0 | 0.0 |
| seq_next | 160 | 0.0 | 3M s401 | 0.0 | 0.0 | 30.0 | 0.0 |
| seq_next | 160 | 0.0 | WIDE 10M | 0.0 | 0.0 | 34.4 | 0.0 |
| rule_apply | 200 | 0.5 | 3M s400 | 0.0 | 0.0 | 47.0 | 0.0 |
| rule_apply | 200 | 0.5 | deep 10M | 0.0 | 0.0 | 60.0 | 0.0 |
| rule_apply | 200 | 0.5 | 3M s401 | 0.0 | 0.0 | 47.5 | 0.0 |
| rule_apply | 200 | 0.5 | WIDE 10M | 0.5 | 0.5 | 50.0 | 0.5 |
| fewshot_number_rule | 160 | 3.8 | 3M s400 | 0.0 | 0.0 | 10.6 | 0.0 |
| fewshot_number_rule | 160 | 3.8 | deep 10M | 0.0 | 0.0 | 10.0 | 0.0 |
| fewshot_number_rule | 160 | 3.8 | 3M s401 | 0.0 | 0.0 | 11.2 | 0.0 |
| fewshot_number_rule | 160 | 3.8 | WIDE 10M | 0.0 | 0.0 | 16.2 | 0.0 |
| pooled | 720 | 3.9 | 3M s400 | 0.0 | 0.0 | 30.3 | 0.0 |
| pooled | 720 | 3.9 | deep 10M | 0.0 | 0.0 | 35.3 | 0.0 |
| pooled | 720 | 3.9 | 3M s401 | 0.0 | 0.0 | 31.0 | 0.0 |
| pooled | 720 | 3.9 | WIDE 10M | 0.1 | 0.1 | 33.1 | 0.1 |

Accuracy minus 3M s400 (points):

| family | deep | wide | s401 (noise reference) |
|---|---|---|---|
| table_lookup | 4.0 | 1.5 | 4.0 |
| seq_next | 1.9 | 1.2 | -3.1 |
| rule_apply | 13.0 | 3.0 | 0.5 |
| fewshot_number_rule | -0.6 | 5.6 | 0.6 |
| pooled | 5.0 | 2.8 | 0.7 |

With all six dev splits (720 rows in the 4 families) the pooled call rate (chosen NUM) is 3M s400 0.0%, deep 10M 0.0%, 3M s401 0.0%, WIDE 10M 0.1%.

### Part 4: accuracy, recomputed here next to the original figures

| model | pooled-5 correct | pooled-5 % | original % | misses | original misses | 13 calc % (rows) | 13 calc % (family mean) | original 13 | 21 non-calc % (rows) | 21 non-calc % (family mean) | original 21 | RESULT.json via g1diag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3M s400 | 4411/6040 | 73.03 | 73.01 | 1629 | 1630 | 88.93 | 88.54 | 88.54 | 62.25 | 62.70 | 62.64 | 4410/6040 |
| deep 10M | 4511/6040 | 74.69 | 74.65 | 1529 | 1531 | 88.89 | 88.63 | 88.64 | 65.06 | 65.45 | 65.38 | 4509/6040 |
| 3M s401 | 4457/6040 | 73.79 | 73.68 | 1583 | n/a | 88.65 | 88.32 | n/a | 63.72 | 64.37 | n/a | 4450/6040 |
| WIDE 10M | 4423/6040 | 73.23 | 73.33 | 1617 | 1611 | 88.52 | 88.15 | 88.14 | 62.86 | 63.30 | 63.48 | 4429/6040 |

The original 13 and 21 figures are unweighted family means, so compare them with the family-mean columns. Families found in pooled-5: 13 calculator, 21 other (expected 13 and 21).

WIDE cross-check: recomputed 4423/6040 (73.228%); readout 4429/6040 (73.328%); difference -6 rows (-0.100 points).
Against the given RESULT.json: 4429/6040 (73.328%); difference -6 rows (-0.099 points).

Numbers quoted in the WIDE prompt, recomputed:

| quantity | quoted | recomputed | difference |
|---|---|---|---|
| 3M s400 misses, pooled-5 | 1630 | 1629 | -1 |
| deep 10M misses, pooled-5 | 1531 | 1529 | -2 |
| WIDE 10M misses, pooled-5 | 1611 | 1617 | +6 |
| 3M s400 misses, 13 calculator families | 270 | 270 | +0 |
| 3M s400 misses, 21 non-calculator families | 1360 | 1359 | -1 |
| WIDE 10M misses, 13 calculator families | 280 | 280 | +0 |
| WIDE 10M misses, 21 non-calculator families | 1331 | 1337 | +6 |
| 3M s400 misses in the 4 zero-coverage families | 501 | 502 | +1 |

### Alignment checks

- rows per split: {'in_dist': 1360, 'answer': 1200, 'frame': 1360, 'vocab': 800, 'variant': 1320, 'family': 160}
- train sample: {"status": "identical: train_sample.jsonl has the same sha256 in both runs", "sha256": "7e7443172169f4cb80a2c77427b99bec61b25d05134029182dd885404172db19", "k": 2000, "rows_per_group": {"web": 2000, "skill": 2000}, "seen_A": {"web": 2000, "skill": 2000}, "seen_B": {"web": 2000, "skill": 2000}, "source_A": "train-sample.jsonl", "source_B": "train-sample.jsonl"}
- rows.jsonl vs g1diag.json oracle table: {"A": {"3M/pooled5": "ok (4411/6040)", "3M/block13": "ok (2170/2440)", "3M/block21": "ok (2241/3600)", "10M/pooled5": "ok (4511/6040)", "10M/block13": "ok (2169/2440)", "10M/block21": "ok (2342/3600)"}, "B": {"3M/pooled5": "ok (4457/6040)", "3M/block13": "ok (2163/2440)", "3M/block21": "ok (2294/3600)", "10M/pooled5": "ok (4423/6040)", "10M/block13": "ok (2160/2440)", "10M/block21": "ok (2263/3600)"}}
- device / precision: {'A': ['cpu', 'fp32'], 'B': ['cpu', 'fp32']}
