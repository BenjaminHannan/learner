# Skills curriculum (generated, never-repeating, checkable)

A program that writes an endless supply of small skill problems, easy to hard, to pretrain Premonition's thinking core.
Every answer is computed by code and re-checked by a second piece of code. Nothing reads GOLD-PRIVATE-v1.json or any
reserved, blind or fresh-eval data.

## Run it
```bash
python -m skills_curriculum.build --out OUT --train 200000 --dev-per-cell 40 --seed 1 [--tokenizer tokenizer.json]
python -m unittest skills_curriculum.tests.test_curriculum          # 16 tests, about 25 s
python -m skills_curriculum.token_report --tokenizer tokenizer.json --rows OUT/train.jsonl [--frames-out frames.jsonl]
```
`from skills_curriculum.build import iter_train` gives an endless clean stream with no file at all
(`iter_train(seed, levels={1,2,3})`). 200,000 rows build in about a minute. `FULL-BUILD-MANIFEST-200k-seed1.json` holds the
file hashes for that exact build, so anyone can confirm they got the same bytes. `sample/` is a small build (2,400 rows).

## What is in it
38 skill families in 8 levels (1 copy and look-up, 2 arithmetic, 3 sequences, 4 tracking and binding, 5 logic,
6 multi-step, 7 learning a rule from examples in the prompt, 8 reading and composing). Each row has `prompt`, `answer`,
`accepted`, `steps` (the worked solution, for calculator calls or step rewards), `meta` (the facts it was built from),
`flags`, `layout`, `wrap`, `level`, `stage`. Answers are short strings; the 1.2B tokenizer sees max 62 input tokens
(cap 64) and at most 7 target tokens.

`train.jsonl` is ordered in 9 stages. Stages 1-8 each add one level (half the rows new, half review of earlier levels);
stage 9 is a uniform mix of everything. Each row is a fresh prompt: no prompt repeats in train, and none appears in dev.

## Structure, not only wording (from the PR #29 findings)
- **Layouts**: facts first, question first, and two labeled forms ("Facts: ... Question: ..."). One layout is held out.
- **Chains with every operation in every position**: `chain_ops` draws add / subtract / multiply / divide for each step of
  2- and 3-step stories, with variants that force a subtraction in the second or first position.
- **Tables** (`table_lookup`, `table_calc`), **distance with units** (`distance_units`), distractor sentences,
  reassigned variables, swaps, two-hop conversions.
- **Wording**: every prompt may get an opener (12 options) and a closer (8 options); sentence pieces are composed per family.

## What is held out (split seed 2026100377, set before generating; decided by SHA-256 so draw order never matters)
| shift | rule | dev file |
|---|---|---|
| answer | a fixed 15% of numeric answers per family are never trained on | `dev/answer.jsonl` |
| frame | the last 20% (by hash) of every pool of sentence pieces, openers and closers | `dev/frame.jsonl` |
| vocab | 20% of names, nouns, words, category words, places, colors and made-up-word syllables | `dev/vocab.jsonl` |
| variant | a third of each family's structural variants, and one of the four layouts | `dev/variant.jsonl` |
| family | `unit_convert`, `clock_date`, `string_transform`, `op_define`: whole skills never in train | `dev/family.jsonl` |
| none | fresh rows built exactly like train | `dev/in_dist.jsonl` |
Each single-shift dev file isolates exactly one shift (tests check that). Fraction held out is a knob in `core.py`.

## How answers are checked (`verify.py`)
1. every number or word the answer depends on appears in the prompt; 2. every `a op b = c` line in `steps` is true;
3. for 19 of 38 families the answer is **re-solved from the prompt text alone** (layout and wrapper undone) by separate
parsing code and must match; 4. length. The other 19 families get checks 1, 2 and 4 only (their answers come from
`meta`, which the same function wrote). The manifest reports `rows_failing` (0 for all
206,200 rows of the 200k build).

## Known limits
- Induction families (`group_induct` especially, also 2-shot `string_transform`) can have more than one rule that fits the
  examples; they are not filtered for a unique rule yet.
- Yes/no, true/false and A/B answers cannot have a held-out answer, so those families have no `dev/answer` rows.
- The estimator that keeps rows under the token cap is conservative; the real count needs the pinned tokenizer file
  (`token_report.py`, or `--tokenizer` on build). It came out at 62 max for the 200k build.
- Not run on any model yet. This is data, not a result.
