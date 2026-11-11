# Fable's pre-registered test for the WIDE 10M question (join of two g1diag runs)

Small card experiments only (34 question families, pooled-5 dev rows). Nothing here says anything about a larger final model.

`fable_join.py` reads two finished `g1diag.py` runs and scores the three-part test that Fable pre-registered in
`api-opinions/answers/fable-wide.md` section 2 (marks copied from there, none tuned). Pure standard library: no torch, no GPU, no network, no scipy
(the McNemar p-value is the exact binomial test built from `math.comb`). It trains nothing and does not touch `g1diag.py`.

    python3 -I fable_join.py --runA DIR_A --runB DIR_B --out OUTDIR [--result-wide RESULT.json]
    python3 -I test_fable_join.py                     # or: python3 -m unittest -q   (44 tests, about 3 seconds)

Each `DIR_x` is a g1diag `--out` folder: it must hold `rows.jsonl` and `g1diag.json`, and should also hold `train_sample.jsonl` (g1diag writes it there).
Writes `OUTDIR/FABLE-TEST.json` (everything) and `OUTDIR/FABLE-TEST.md` (the verdict table first, then claims labelled shown / suggested / untested,
then a plain-language summary for Ben, then limits, then the detail tables).

| model name | run | g1diag tag | what it is |
|---|---|---|---|
| s400 | A | 3M | G1 3M seed 400 |
| deep | A | 10M | G1 deep 10M seed 400 (8 blocks) |
| s401 | B | 3M | G1 3M seed 401 (the seed-noise baseline) |
| wide | B | 10M | WIDE 10M seed 400 (d 448, 2 blocks) |

The tag names inside each run are always `3M` and `10M`; the script maps them as in the table.

## How to produce the two inputs on the Mac (follows the Run A recipe in `results/8a-g/pc-job-cards/g1-causes/d/README.md`)

Folder `g1d/` as in that README: `src/custom_io` (repo at `612f5c5b01` plus the overlay `caps.py`, sha256 `3da2dfbb0ddde64f0b4a263ccc025a01e70ca35c7c69fd9e9fdbb9c2d2325f78`),
`g1diag.py`, `pool/` (`dev/`, `charvocab.json`, `caps.json` from `work\g8a\pools\p10-rung30-s400-a64\`), `eg2/` (EmbeddingGemma), plus the four checkpoints:

    ckpt-s400.pt   <- PC work\results\8aG1d-pc\8aG1d-3M-s400\B2\checkpoint.pt
    ckpt-deep.pt   <- PC work\results\8aG1f-pc\8aG1f-10M-s400\B2\checkpoint.pt
    ckpt-s401.pt   <- PC work\results\8aG1e-pc\8aG1e-3M-s401\B2\checkpoint.pt      (path inferred from the results folder name; check it)
    ckpt-wide.pt   <- repo copy whole-model-roadmap/wide-modal/8aWIDE-10MW-s400/B2-full/checkpoint.pt
    RESULT-s400.json RESULT-deep.json RESULT-s401.json RESULT-wide.json     (the B2 RESULT.json of each; optional, but they fill `compare_g1`)

ONE shared train sample for both runs. Make it once on the PC from the 3M/deep side (pure python, about a minute), then copy it to the Mac as `train-sample.jsonl`:

    set PYTHONUTF8=1
    "C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe" g1diag.py --train C:\Users\benja\custom-io\work\g8a\pools\p10-rung30-s400-a64\train.jsonl --sample-only C:\Users\benja\custom-io\work\g1diag-train-sample.jsonl

Then, from `g1d/` (first a quick `--max-rows 100 --out out-debug-A` is sensible; fable_join prints a warning for a `--max-rows` run):

    export CUSTOM_IO_EG2=$PWD/eg2 PYTHONUTF8=1
    # Run A: tag 3M = s400, tag 10M = deep
    python g1diag.py --src src --data pool --train train-sample.jsonl --ckpt3 ckpt-s400.pt --ckpt10 ckpt-deep.pt \
        --result3 RESULT-s400.json --result10 RESULT-deep.json --out out-A --device cpu
    # Run B: tag 3M = s401, tag 10M = wide
    python g1diag.py --src src --data pool --train train-sample.jsonl --ckpt3 ckpt-s401.pt --ckpt10 ckpt-wide.pt \
        --result3 RESULT-s401.json --result10 RESULT-wide.json --out out-B --device cpu
    # the join (seconds)
    python3 -I fable_join.py --runA out-A --runB out-B --out out-fable --result-wide RESULT-wide.json

Because `--train` is a pre-made 2,000 web + 2,000 task row file, g1diag's reservoir takes every row in file order, so both `out-A/train_sample.jsonl` and
`out-B/train_sample.jsonl` are byte-identical; fable_join checks their sha256 and stops if they differ. Ignore the R1/R2/R3 rules in `out-B/G1DIAG.md`:
they were written for 3M vs deep and mean nothing for s401 vs WIDE.

## What is read from g1diag (real key names, checked against `g1diag.py` and a `--selftest` run)

`rows.jsonl`, one record per dev row (6,200 rows: the six splits `in_dist answer frame vocab variant family`): `id`, `split`, `family`, `gold_mode` (0 NUM, 1 WORD, 2 GEN),
and for each tag `T` in `3M`, `10M`: `hitT` (0/1), `chosenT` (mode actually printed), `raw_modeT` (mode head's argmax); also `cand_hitsT`, `cand_availT`,
`ws_goldT`, `ws_gold_result_slotsT` (not used). `id` repeats across splits, so rows are joined on (split, id, occurrence number).

`g1diag.json`:
- `train_loss.groups.web.n`, `.web.<3M|10M>.<total|prog|mode|ans|word|gen|op_acc|copy_share>`, the same under `.skill`; `train_loss.k`, `.seen`, `.source`, `.note`.
  "web" = rows with family `cloze`; "skill" = every other row, which the test calls the "task rows".
- `dev_loss.pooled5.<3M|10M>.<term>` and `dev_loss.by_family.<family>.<3M|10M>.<term>` (the gold log-likelihood, teacher-forced loss on the five dev splits).
- `oracle.<pooled5|block13|block21>.<3M|10M>.{n, correct, exact, oracle_correct, oracle_exact}` (and `oracle.block_families`, `oracle.by_split`): used to check that
  `rows.jsonl` and `g1diag.json` come from the same run (the script stops if the counts disagree).
- `compare_g1.<3M|10M>.{g1_pooled5, g1_correct, g1_n, ...}` when `--result3/--result10` were given: shown next to the recomputed accuracy.
- `meta.{device, amp, blocks, trained_params, max_rows, caps}`: warnings if the two runs differ in device or precision, or if a model does not look like the
  checkpoint it should be (block counts 2 / 8 / 2 / 2, parameter counts 3,544,913 / 10,496,537 / 3,544,913 / 10,173,509).

## Step 0: alignment (the script stops with `ALIGNMENT ERROR` and writes nothing if any of these fail)

- both `rows.jsonl` hold the same multiset of (id, split, family) rows and the same `gold_mode` per row (row order may differ); all five pooled-5 splits are present;
- both runs recorded the same train-loss sample: equal `train_loss.k` and `groups.<g>.n`, and the same sha256 of `train_sample.jsonl`. If a run folder has no
  `train_sample.jsonl`, equal `train_loss.seen` is accepted but reported as "consistent but not verified"; if `train_loss` is missing the report says "nothing recorded"
  and the Part 2 marks are n-a;
- in each run, `rows.jsonl` agrees with the `oracle` counts in its `g1diag.json`.

## The marks and the reading choices made (all numbers from Fable's section 2, except the two marked "Ben")

| id | mark | counted in the verdict |
|---|---|---|
| P1a | overlap(WIDE given s400) on pooled-5 is at least 80% | yes |
| P1b | and it is within 5 points (absolute difference) of overlap(s401 given s400) | yes |
| P1c | overlap(deep given s400) on the 21 non-calc families is lower by at least 8 points than overlap(s401 given s400) on the same families | yes (primary reading) |
| P1c-alt | the same, but lower than overlap(WIDE given s400) on the 21 families | no, printed |
| P2a | task-row total train loss at most 0.10 for s400, deep and wide | yes |
| P2b | (deep minus s400) and (wide minus s400) task-row total loss at most 0.02 in absolute value | yes |
| P2c | web-fill GEN loss: the same two differences at most 0.03 | yes |
| P3a | rate of chosen mode NUM, pooled over table_lookup, seq_next, rule_apply, fewshot_number_rule, at most 10% for s400, deep, s401 and wide | yes |
| P3a-raw | the same with `raw_mode` NUM | no, printed (Ben: flag when it differs from chosen by more than 5 points) |
| P3b | accuracy of deep and of wide within 2 points of s400, for each of the four families and pooled (the largest difference is shown; all must pass) | yes |

Wrong-rules (Fable's "what proves E1 wrong"), each reported as applies / does not apply / n-a:
- W1 overlap(WIDE given s400) below 60% (tested on pooled-5; the deep and s401 values are shown);
- W2 task-row loss at least 0.25 for s400, deep and wide and "still equal" (read as largest minus smallest at most 0.02, the same tolerance as P2b);
- W3 a 10M model's task-row loss at least 0.05 below s400 while its pooled-5 gain over s400 is within +-0.7 points (Ben: 0.67 is the 3M seed gap); both parts are
  printed for deep and for wide.

Verdict: `SUPPORTED` if all 8 counted marks pass, `NOT SUPPORTED` if any fails (Fable says E1 wins only if all hold; a failed mark is not proof that E1 is wrong),
`UNDECIDED` if none fails but some cannot be computed. Comparisons use 1e-9 of slack so that a value sitting exactly on a mark is not flipped by rounding.

Definitions: overlap(X given base) = rows both miss / rows X misses (the share of X's misses that the base also misses; not symmetric). Jaccard = both / either.
b = X wrong and base right, c = X right and base wrong; p is the exact two-sided binomial test of b against c (twice the smaller tail, at most 1).
The 13 calculator families are the g1diag list `B13`; the 21 non-calc families are the other families in pooled-5. The report also gives, for each model, the accuracy pooled
over rows and as the unweighted mean of per-family accuracies; the original 13/21 figures in the WIDE prompt are the unweighted means, so compare those columns.
"Call rate" = share of rows whose `chosen` mode is 0 (NUM). Part 3 uses the pooled-5 splits; a second pooled number over all six splits is printed too.

## Things in `g1diag.py` that looked wrong or ambiguous (not fixed)

1. `oracle.block_families.block21` and the "other N families" sentence in `G1DIAG.md` are built from all six dev splits, so they also list the four held-out families of the
   `family` split (clock_date, op_define, string_transform, unit_convert): 25 names, not 21. The scores themselves use pooled-5 rows only and are right.
2. "Call rate" is a proxy: `chosen == NUM` means the mode head said NUM and the pointed slot was valid (otherwise it falls back to WORD or GEN). NUM also covers pointing at a
   number that was already in the prompt, not only at a calculator result (`ws_gold_result_slots` is the field that tells them apart).
3. `train_loss.seen` differs between a run that streamed the full train file and a run that was given a pre-made sample, even when the sampled rows are identical; that is why
   fable_join trusts the `train_sample.jsonl` hash first.
4. The R1/R2/R3 rules, the hard-coded G1 gain 1.64 and the "blocks 3-8" knockout assume 3M vs deep; in Run B they are meaningless (WIDE has 2 blocks, so its knockouts are only skip_0 and
   skip_1) and the knockouts there cost time for nothing.
5. `install_eg_cache` points every model at the first model's EmbeddingGemma holder; fine when all checkpoints use the same EG settings (all four use `eg_embed: true`).
6. One `--data` serves both models of a run and the check `ck['chars'] == vocab.chars` must hold for both; if s401 and WIDE were trained with different `charvocab.json` files, Run B cannot be done in one call.
7. The per-term losses are teacher-forced in eval mode on a sample, so they are not comparable with the logged final train loss (1.13); the note in g1diag calls them batch means weighted by rows (approximate).
   In `loss()` at `612f5c5b01` the six terms used here are sums over rows divided by the batch size, so the weighting makes them exact row means; only `op_acc` and `copy_share` are truly approximate.
8. `blocks = {...}` in `pipeline()` is an unused variable. The sample is 2,000 web + 2,000 non-cloze rows (Fable wrote "a fixed 2,000-row sample").
9. Which `train.jsonl` counts as "the 3M/deep manifest" is unclear: the g1diag README uses `p10-rung30-s400-a64` on the PC; the WIDE run used a pool of the same name on Modal whose recorded
   manifest hash differs (8ee0b3ee vs 133e463e), and 3M s401 has its own seed-401 pool. The recipe above takes the sample on the PC, which is the 3M/deep side.

## Limits

One training run per condition; the seed baseline is one pair and also differs in data manifest (4ad1440e for s401, 133e463e for s400 and deep, 8ee0b3ee for WIDE, copied from the RESULT.json
files). CPU fp32 here against GPU bf16 originally, so a few rows can differ (the WIDE cross-check prints the difference to 4429/6040 = 73.328%). The test says nothing about a larger final model.
