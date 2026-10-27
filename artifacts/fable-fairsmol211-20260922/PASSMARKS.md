# PASSMARKS — Experiment 211: FAIR-PROMPT SmolLM ARM (2026-09-22)

Benchmark fairness; no agent change. Same model (SmolLM2-360M-Instruct),
splits (fable_edit_200, s2fresh_4hop), greedy decoding (<= 16 tokens) and
scorer (bench125 classify_v2 + contains-gold) as bench125's in-context arm —
all imported, never re-implemented. Difference under test is the prompt only:
facts numbered in teaching order, each edit marked "(this replaces fact N)",
"newer facts win" + "say I don't know if the facts don't say" + one abstain
example. Plus a scorer variant whose abstain markers match whole phrases
only (no bare-"not" substring rule).

Registered run (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1; uv run --offline --no-project --python
3.12 --with torch --with numpy --with transformers python -B
scripts/fable_fairsmol211.py --run`, no --limit; pre-registration smoke on
5 four-hop items measured 0.81 s/item -> 400 fresh generations project ~323 s,
far below the 25 min budget).

| Mark | Pass condition |
|---|---|
| F1 fair arm beside old arm | fair SmolLM rows (fresh runs, v2 scorer) reported per-item (right / wrong / abstain) on BOTH splits, beside bench125's old in-context arm (edit200 52/0/148, 4hop 52/0/148) |
| F2 "not"-abstain audit | bench66's old in-context answers (200) re-scored with the whole-phrase detector; reported: old abstain count, phrase abstain count, how many old abstains merely contained "not" |
| F3 wrong-rate beside loop | loop wrong-answer rates from bench125 JSON (edit200: 0.0 all three loops; 4hop: loop102 0.65, loop113/113b 0.025) reported beside fair SmolLM's wrong rate on both splits |

Verdict VALID iff F1–F3 are all reported (every seed/case, never averaged).
A registered FAIL is recorded as FAIL with one diagnosis note, never
re-run into a pass. No agent code, config, or case files change in this
experiment (new driver file only); any post-seal edit forces FAIL.
