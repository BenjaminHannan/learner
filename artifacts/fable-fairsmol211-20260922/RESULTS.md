# RESULTS — Experiment 211: FAIR-PROMPT SmolLM ARM (2026-09-22)

Registered verdict: **VALID** (F1–F3 all reported, every item, no averaging).

## Marks table (v2 scorer, same as bench125 in-context arm)

| Split | Arm | Correct | Abstain | Wrong | n | contains_gold |
|---|---|---|---|---|---|---|
| fable_edit_200 | old SmolLM in-context (bench125) | 52 | 0 | 148 | 200 | 67 |
| fable_edit_200 | **fair SmolLM (new)** | 17 | 84 | 99 | 200 | 24 |
| s2fresh_4hop | old SmolLM in-context (bench125) | 52 | 0 | 148 | 200 | 57 |
| s2fresh_4hop | **fair SmolLM (new)** | 47 | 40 | 113 | 200 | 49 |

F2 ("not"-abstain audit, bench66 old in-context answers, n=200): old abstains
11, whole-phrase abstains 11, old abstains merely containing "not" **0**,
per-item old-vs-phrase verdicts identical 200/200. Zero bench66 answers
(in-context or raglite) contain "not" even as a substring.

F3 (wrong rates): edit200 — fair 0.495 vs loop102/113/113b 0.0; 4hop — fair
0.565 vs loop102 0.65, loop113/113b 0.025.

## What it means

The fair prompt (numbered facts, "(this replaces fact N)", newer-wins cue,
"I don't know" instruction + example) turns silent wrong answers into
abstains: on edit200 wrong falls 148→99 while abstains rise 0→84. The
suspected "not"-substring bias never fired on these 200 items — all 11 old
abstains are genuine "unknown"s, so bench66's abstain counts stand.

## What it does not mean

It does not mean fair prompting fixes the baseline: edit200 correct drops
52→17 (the model now abstains on answerable items too), and the loop
(0.0 / 0.025 wrong) still beats fair SmolLM (0.495 / 0.565) on both splits.
One prompt, one model, one seed — no claim about other models or prompts.

## Deviations

None. Full run 473.6 s (< 1500 s), Mac CPU, OMP=1 MKL=1, no --limit.
Seal 4/4 OK after the run; no post-seal edits. Fictional names only in
pilots; no frozen-suite, bench, or agent-code changes (new driver file only).

Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1;
uv run --offline --no-project --python 3.12 --with torch --with numpy
--with transformers python -B scripts/fable_fairsmol211.py --run`
