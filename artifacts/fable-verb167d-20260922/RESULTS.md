# Exp 167d RESULTS — widened verb table (Muse)

Loop167b clarified everyday job/language sentences. One change:
"X works at Y" and "X speaks Y" now save as the employer/language
facts their possessive twins save, and "Where does X work?" /
"What language(s) does X speak?" answer them. Everything else is
loop167b byte-for-byte.

## Marks (integer counts, every seed/case reported, never averaged)

| mark | bar | number | status |
|---|---|---|---|
| T1 sealed probe (32 rows) | 32/32 OK | 7/7 works-teach, 7/7 speaks-teach, 8/8 asks-after-possessive, 10/10 traps | PASS |
| T2 167b-probe identity (64 rows) | 64/64 IDENTICAL | stored+reply+asks identical | PASS |
| T2-safety | 0 wrong writes (96 rows); C033 bench73-owned | 0 wrong writes; C033 Saved languages_spoken_written_or_signed on both | PASS |
| G1 bench (600 items) | 0 moves, 0 new wrong vs loop167b | verdict+reply identical vs 167b and 162b rows | PASS |
| G2 marks123 vs marks167b | 0 case-moves | 11/11 reports identical/predicted (sleep names loop167d) | PASS |
| G3 rt136+rt143+s152 | 0 moves, 0 new wrong/writes | 0 moves vs live and frozen 167b | PASS |
| G4 time | each run < 1500 s | probe 2 s, bench 44 s, G3 17 s, marks123 179 s | PASS |

Note: the marks123 summary table shows suite FAILs (p2, q1, rt81, q4)
-- all per-case identical to the base marks167b run, i.e. pre-existing
base behavior, not regressions. G2 diff: G2 PASS, exit 0.

## What it means

Ben can now say "Tom works at Acme" or "Rana speaks Hindi" and get
the same save and answer as the "Tom's employer..." form, with traps
(negations, hedges, descriptions, "used to", reverse and yes/no
questions) still safely ignored.

## What it does not mean

It does not understand jobs or languages beyond these four shapes;
"the language of" sentences, multi-word names, and other verbs still
clarify or stay with their old owners.

## Deviations

One pre-seal design fix, done in the open before sealing: the first
scan found redteam136 C033 ("Tom speaks the language of French.") is
taught by bench73 today, so a "the language of" veto was added (the
167 "the city of" precedent); C033 re-verified byte-identical. No
edits after the seal (shasum -c: all OK).

## Questions for Ben

None. Conservative default kept: description objects ("a big firm",
"a dialect") clarify instead of guessing.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167d_probe.py --out artifacts/fable-verb167d-20260922/probe167d-loop167d.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167d_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167d_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167d_agent.py --config artifacts/fable-verb167d-20260922/loop167d-config.json --out artifacts/fable-verb167d-20260922/marks167d --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167d_marksdiff.py
