# Experiment 77 — PASSMARKS (core fixes for red-team 67 findings)

Sealed BEFORE the registered run. Additive only: no existing file is edited;
new files carry prefix `fable_fix77_`. Mac CPU, `OMP_NUM_THREADS=1
MKL_NUM_THREADS=1`, `uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B`. Every seed/case reported, never averaged. Claims
never exceed evidence. A registered FAIL stays a FAIL (never re-run into
a pass).

| Mark | Bar (integer counts) |
|------|----------------------|
| F1 reproducers fixed | 3/3 red-team reproducers (doc 72 findings 1-3) give the doc-56-correct result through the fixed classes: R1 qualified+unqualified same S+R answers "Ana" via `GatedThoughtNotebook`; R2 bool qualifier `{"open": True}` answers OK via both wrappers; R3 last-line value edit raises `LogCorrupt` via `open_verified` |
| F2 red-team re-run | 69/69 cases from `scripts/fable_redteam67_probe.py` CASES (imported, not copied) verdict OK or explicitly classified with a written rule; 0 BUG; 0 left UNCLEAR (RT40 and RT68 classified by written rules R-EMPTY and R-STUB) |
| F3 no regression | qual56 24/24 reasoner cases pass through `QualifierAwareReasoner77` (+ `GatedThoughtNotebook` notebook); thought62 5/5 marks (T1-T5) still PASS with its files untouched |
| F4 bench unchanged | `fable_bench65_notebook_arm.py` flow still 200/200 correct, 0 wrong, when its notebook is swapped for `GatedThoughtNotebook` (tiny driver, script itself unedited) |

Before-column: the sealed red-team result is 64 OK / 3 BUG / 2 UNCLEAR
(`artifacts/fable-redteam67-20260921/probe-results.json`); the conformance
script re-runs the unpatched classes first and must reproduce 3 BUG
(RT65, RT66, RT49b) and 2 UNCLEAR (RT40, RT68) before the patched run counts.

Classification rules (so no case is left unclear):
R-EMPTY: the contract specifies no empty-value validation; storing and
answering an empty literal is permitted behaviour, not a wrong status (RT40).
R-STUB: FakeEars' 3-hop limit is declared test scaffolding, not the core;
teach/ask roundtrip correct with the 4-hop refusal noted (RT68).

## What it means

If all four marks pass, the three confirmed red-team bugs are closed by
wrappers alone (rule-2 gate shared by both readers, bool qualifier equality,
tail-evident log loading) with no behaviour change anywhere else measured.

## What it does not mean

It does not mean the system is safe end to end: English ears, mouth wording,
and sleep mining were out of scope for redteam67 and remain unprobed here.
