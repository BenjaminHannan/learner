# PASSMARKS — Exp 89 web-quarantine fixes (Muse, 2026-09-22, sealed before run)

Sealed: `shasum -a 256 PASSMARKS.md > SEAL.sha256.txt` before any registered run.
Module under test: `scripts/fable_webfix89_thinking.py` (class `QuarantinedThinking89`),
additive subclass of `Thinking` in `scripts/fable_thinking_m2.py` (that file untouched).
Runner: `scripts/fable_webfix89_run.py` (imports the 56-case list from
`scripts/fable_redteam79_probe.py`; before = original `Thinking`, after = fixed class).

| id | mark | bar | rule |
|----|------|-----|------|
| X1 | BUG-1 reproducer stores nothing | kept=0, dropped=['missing field'], 0 rows | None/empty/whitespace/"None"/"null" values dropped before the copy-rule check, never coerced to str |
| X2 | three site-pairs count as 1 site, NOT believed | RT79-09, RT79-53, RT79-11 each web-verified=0 | registrable-domain counting + non-ASCII hosts map to a REJECTED site that never counts |
| X3 | 56/56 red-team cases OK or explicitly classified | 0 unclassified BUG/UNCLEAR | any verdict change vs before run gets a written rule in RESULTS.md |
| X4 | thinking_m2 selftest count unchanged through wrapper | before count == after count | everything else inherited byte-identical |

Environment: Mac CPU only, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B`.
Every seed/case reported, never averaged. Claims never exceed evidence.
