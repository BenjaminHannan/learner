# RESULTS — Experiment 151: no-question-mark fix (2026-09-22)

One single-change fix: a message containing NO "?" whose first word (after
openers hey/hi/ok/so/and/um) is a sealed question word/auxiliary and which
the teach parser rejects is answered exactly as its "?" twin. Mixin on
loop134 (variant A) + variant on the loop132+149 config (variant B).
Subclass/wrap only; no existing file edited.

Question-vs-statement site: `scripts/fable_loop121_agent.py:175`.

## Marks (integer counts, every case reported)

| Mark | Bar | Result |
|---|---|---|
| Q1 pairs, variant A | 32/32 equal | 32/32 byte-equal (4.0 s) |
| Q1 non-questions, variant A | 22/22 marker + 0 writes | 22/22 (0 writes each) |
| Q1 pairs, variant B | 32/32 equal | 32/32 byte-equal (2.5 s) |
| Q1 non-questions, variant B | 22/22 marker + 0 writes | 22/22 (0 writes each) |
| Q2 143, variant B | J5+J10 OK; 0/122 worse | J5 MISSED->OK ("Norland's capital is Aldport."), J10 MISSED->OK ("Bram Kite's spouse is Cora Lind."); worse=[] (5.1 s) |
| Q3 bench A vs loop134-base | 0 diffs x4 | 0 diffs; new 136/63/1, old 157/43/0 (35.3 s) |
| Q3 bench B vs 132+149-base | 0 diffs x4 | 0 diffs (68.5 s) |
| Q4 marks123 vs loop134 | verdicts identical | 10/10 suites verdict-identical (p2/p3/p4/rt110/q1/bench/rt81/sleep-SKIP/soak/q4); p2 FAIL-status and rt81 61ok/13unclear match sealed base exactly (135.0 s) |

SCORE: PASS (Q1–Q4). Sealed 143 rows had J5/J10 MISSED; both now answer.
No other 143 case moved (only J5/J10 changed of 124).

## What it means

Phone typists who skip "?" now get the same answer as with "?" whenever
the sentence starts with a question word and is not a teach.

## What it does not mean

It does not make the loop understand new question shapes: untaught answers
and non-questions still clarify exactly as their "?" twins do.

## Deviations

P151.5 predicted one reply-text-only allowance (rt81 D_q_vs_s-02 trailing
cleanup). Observed: 0 text diffs anywhere — the suite's dialogue leaves
Mira untaught, so the twin path yields the same reply. Verdict bar fully
held; the allowance was unused, not exceeded.

## Reproduce (Mac CPU, offline; PASSMARKS already sealed)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_qmark151_q1.py --variant 151  # or qrewrite
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_qmark151_run143.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_qmark151_bench.py --variant 151  # or qrewrite
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop151_agent.py --config artifacts/fable-qmark151-20260922/loop151-config.json --out artifacts/fable-qmark151-20260922/marks151 --workers 4
```

Seal: `artifacts/fable-qmark151-20260922/SEAL.sha256.txt` (PASSMARKS.md,
q1 case file, both configs). Ledger P151.1–P151.6 appended before runs,
outcomes appended after.
