# RESULTS — fix77 core fixes for the three redteam67 bugs (2026-09-22)

Result first: all four sealed marks PASS. The three confirmed bugs are closed
by wrappers alone — no existing file edited — and every other behaviour
measured is unchanged.

## Integer summary

| Mark | Bar | Observed |
|------|-----|----------|
| F1 3/3 reproducers fixed | R1 "Ana"/"Ana", R2 OK/OK, R3 LogCorrupt | 3/3 PASS |
| F2 69 red-team cases | 69 OK-or-classified, 0 BUG, 0 UNCLEAR | 69/69 (before-run 64/3/2 reproduced exactly) |
| F3 no regression | qual56 24/24, lifecycle 32/32, thought62 5/5 | 24/24, 32/32, 5/5 PASS |
| F4 bench65 swap | 200/200, 0 wrong | 200/200, 0 wrong, 0.3 s |

Before vs after (full 69-line table in `conformance.json`): only five rows
changed — RT65 BUG→OK, RT66 BUG→OK, RT49b BUG→OK, RT40 UNCLEAR→OK (R-EMPTY),
RT68 UNCLEAR→OK (R-STUB). All other 64 rows OK in both runs.

## What was built (all new files, prefix `fable_fix77_`)

- `scripts/fable_fix77_core.py` — `GatedThoughtNotebook` (rule-2 gate:
  unqualified taught row drops qualified competitors even on qualifier match),
  `QualifierAwareReasoner77` (bool True/False == "true"/"false",
  case-insensitive; everything else byte-identical logic),
  `verify_full` + `open_verified` + `VerifiedNotebook` (tail-evident loading
  via a sidecar seal, `events.fix77.seal.json`).
- `scripts/fable_fix77_conformance.py` — imports redteam CASES (never copied),
  runs unpatched then patched, classifies RT40/RT68 by written rule, runs F1,
  qual56-24, lifecycle-32, thought62-T1-T5, ingests bench77.json.
- `scripts/fable_fix77_bench.py` — bench65 flow with only the notebook class
  swapped (file itself untouched): 200/200, 0 wrong, 0 contract disagreements.

## Callers using the unfixed classes (for the director's swap decision)

- `scripts/fable_agent_loop.py:218` — `self.nb = C.Notebook(...)` (import
  at :46). Swap candidate: `open_verified(dir/NOTEBOOK_DIR)` or
  `VerifiedNotebook`. `:175` `LookupReasoner` asks the contract directly
  (qualifier-blind; safe while the loop teaches unqualified rows only).
- `scripts/fable_bench65_notebook_arm.py:63` — `C.Notebook(...)` → tested
  swap to `GatedThoughtNotebook`, 200/200 (`bench77.json`). `:87`
  `QualifierAwareReasoner()` → `QualifierAwareReasoner77` agrees 24/24 with
  the gate fix; swap safe.
- `scripts/fable_wire57_e2e.py:66` — imports the contract but constructs no
  notebook directly; exposure is transitive via `AgentLoop`, so the
  agent-loop swap covers it.

## What it means / what it does not mean

Means: both qualifier readers now share one gate (the critical silent-wrong-answer
is gone), bool qualifiers work through qual56, and last-line edits are
detectable on every verified load. Does not mean: end-to-end safety — ears,
mouth wording, and sleep mining were out of scope and remain unprobed.

## Deviations

Two additions beyond the letter of the brief, both additive: (1)
`VerifiedNotebook` (seal-maintaining writer) — without it no pure function
of `events.jsonl` can detect a canonical last-line rewrite, so the seal is
the honest mechanism; the report states this limit. (2) Written rules
R-EMPTY/R-STUB/R-PERF to classify the unclear cases instead of leaving them.
No deviations from the sealed bars.

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix77_bench.py`
then `... python -B scripts/fable_fix77_conformance.py`. Full JSON in this
folder (`conformance.json`, `bench77.json`). Seal `SEAL.sha256.txt` matches
`PASSMARKS.md`. Questions for Ben: none.
