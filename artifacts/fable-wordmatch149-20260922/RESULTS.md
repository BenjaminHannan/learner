# RESULTS — Experiment 149: whole-word entity matching (Muse)

One-change fix for exp-143 class 5 (O3): taught "Norland" matched inside
"Norlandia" by substring and answered "Aldport". Fix: entities count as
mentioned only on word boundaries (case-insensitive; trailing "'s" and
punctuation allowed; longer names still win). New files only, nothing
else edited. PASSMARKS + 33-case probe sealed first (`SEAL.sha256.txt`:
`4ad51cd0…`, `808a58a3…`); ledger P149.1–P149.6 written before any run.

## Marks (Mac CPU, OMP=1/MKL=1; every case reported)

| mark | bar | result |
|---|---|---|
| W1-A 143 vs loop134+149 | O3 abstains; 0 other worse | FAIL: O3 WRONG→OK ✓, but F5/H4 OK→MISSED (see diagnosis) |
| W1-B 143 vs loop132+149 | same | PASS: exactly 1 move, O3 WRONG→OK; other 123 identical |
| W2 probe 33/33, both variants | all as sealed, 0 wrong | PASS: 33/33 OK + 33/33 OK |
| W3 benches per-item, both variants | 0 unpredicted diffs | PASS: 0 diffs on 4/4 suites × 2 variants |
| W4 marks123 vs sealed marks134 | identical suite verdicts | PASS: all 10 suites identical (p2/rt81 suite-FAILs inherited verbatim) |
| W5 time + shape | each run < 25 min; idle_seconds | PASS: slowest run 152.8 s; both daemons take idle_seconds |

W1 detail (variant A: OK 92 / WRONG 20 / MISSED 12; variant B: 93 / 21 /
10; sealed loop132 rows: 92 / 22 / 10). Variant-A moves vs sealed: O3
WRONG→OK (the fix), F5/H4 OK→MISSED, H5 WRONG→OK (matches sealed
"abstain"; the sealed expectation itself was the documented H5 error).
Variant-B moves: O3 only.

DIAGNOSIS NOTE (W1-A FAIL, single): F5/H4 are loop132-rewriter island wins
(doc 143: "rewriter F5/H4 fire correctly"); variant A is loop134-lineage
and has no rewriter, so it cannot answer them by construction. Proof: an
unregistered loop134-base 143 re-run (`diag143_loop134base_results.json`)
shows the IDENTICAL three moves (F5/H4 OK→MISSED, H5→OK) with O3 still
WRONG. Variant A vs its true base differs in exactly O3: the wordmatch
change itself moves nothing else. FAIL stays FAIL per the sealed letter.

W2: 13 untaught look-alikes abstain (Norlandia/Anna/Annabel/Romeo/Limassol/
Dara-Fenner-either-direction/Perugia/Norlandia's/Romeo's/Norlandia??/
Notre-Dam/O'Neil); 20 taught answers incl. possessives ("Norland's",
"O'Neill's", "Notre-Dame's"), "??", inner quotes, comma phrase, lowercase,
SHOUTED, hyphen/apostrophe names, longer-wins (Annabel→Dunmore with both
taught). 0 WRONG-ANSWER either variant.

W3: variant A reproduces sealed loop134 rows exactly (bench121-new
136/63/1, old 157/43/0, edit200 150/50/0-split-A) and matches a
same-process loop134 baseline 200/200 on bench132-new; variant B matches
sealed loop132 bench132 rows 200/200 and a same-process loop132 baseline
600/600 on the rest. 0 verdict diffs anywhere (1,400 variant item-runs).

W4: p2 same ids (B7/D8, C2/C5/D8) 0 per-case diffs; p3 7/7; p4/q1/bench/
soak/q4 reports identical; rt110 62/62 rows identical; rt81 61/0/13 per-case
identical; bench rows 400/400 verdicts + 0 reply diffs; sleep SKIP both.

## What it means

Substring entity matching was the whole O3 bug: bounding mentions by word
boundaries removes it with zero measured regressions across 124 red-team
cases, 33 probes, 800 bench items × 2 variants, and the full marks123 set.

## What it does not mean

It does not fix negation, qualifier, prefix-answer, or answer-type
blindness (all 20 remaining variant-A wrong answers stand), and variant A
does not inherit the loop132 rewriter (F5/H4) — that is lineage, not this
fix.

## Deviations

Probe driver mkdir fix (own unsealed file, before its first run);
unregistered loop134-base 143 diagnostic (labeled `diag*`, for the W1-A
note only). Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run
--offline --no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_wordmatch149_run143.py --variant 149|qrewrite`,
`scripts/fable_wordmatch149_probe.py --variant ...`,
`scripts/fable_wordmatch149_bench.py --variant ...`,
`scripts/fable_marks123_all.py --agent scripts/fable_loop149_agent.py
--config artifacts/fable-wordmatch149-20260922/loop149-config.json --out
artifacts/fable-wordmatch149-20260922/marks149 --workers 4`.
