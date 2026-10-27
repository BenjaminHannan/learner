# Exp 81 pass marks — RED TEAM listening-doorway probe (sealed before the run, 2026-09-22)

Under test (read-only import, never edited): scripts/fable_listening_m1.py
(LISTENING doorway, milestone 1) driven through scripts/fable_agent_loop.py
with its FakeEars template parser, over scripts/fable_notebook_contract.py.
Docstrings + selftests + design docs 36 (notebook contract) and 54 read first.

Registered run (Mac CPU, offline, one process):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_redteam81_probe.py --out artifacts/fable-redteam81-20260921

| id | mark | pass bar |
|----|------|----------|
| R1 | adversarial ENGLISH turns in sequences via AgentLoop+FakeEars | >= 60 turns, every seed/case reported, never averaged |
| R2 | each turn records expected + observed + verdict | 100% of turns have all three; every BUG has a <= 15-line reproducer + severity |
| R3 | no fixes, no edits to files not created by exp 81 | probe + report only; under-test modules imported read-only |
| R4 | report filed | design/v3/30-modes/81-redteam-listening-doorway-findings-muse.md <= 1,200 words with integer summary + every BUG reproducer |

Rules under test: a turn is either written, answered, clarified, or refused —
never silently dropped, never written wrong; corrections supersede; ambiguous
names ask; questions never write; a statement contradicting a taught fact
triggers clarify/correction, never a silent second value; nothing personal
about the user is inferred; <= 3 hops. Only doorway/contract violations count
as BUG; FakeEars scaffolding limits are classified separately, not as BUGs.

Predictions: ledger P81.1-P81.4.
A registered FAIL is recorded as FAIL, never re-run into a pass. Claims never exceed evidence.
