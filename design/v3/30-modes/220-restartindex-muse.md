# 220 — Restart must not double the fast index (Muse)

## Problem
Teach "Kim's boss is Lee." and "Lee's city is Oslo.", restart, say "Forget Lee's
city." Loop138i replies "Forgotten: Lee's city." — then "Whose city is Oslo?"
answers "Oslo is the city of Lee." The forgotten fact is served. Without the
restart the reply is "I don't know anyone whose city is Oslo."

## Diagnosis
`IndexedContractNotebook._load` (fable_perf128_index.py:86-89) calls
`super()._load()`. That loop (fable_notebook_contract.py:143-161) calls
`self._apply(event)` per log line — and `self._apply` IS the indexed override,
which already calls `self._index_event`. `_load` then runs a second pass,
`for ev in self.events: self._index_event(ev)`. Every fact id lands twice in
`_sr`/`_rel`, every taught triple twice in `_triples`/`_sro`/`_rev`, every
mention count is doubled. `_triple_remove` removes only one copy, so after a
forget-after-restart a stale copy keeps serving: the reverse-question path
(`rev_subjects`/`_sro` residue) answers from it, and the 170-cached
`notebook_triples` (which reads `inner._triples`, not facts+active) still lists
('Lee', 'city', 'Oslo'). Forward asks look clean because `current()` filters by
the log-derived `active()` flag — which is why the bug hid: only reverse
questions and triple listings exposed it.

## Fix (one change, additive only)
`scripts/fable_fix220_restartindex.py`: `FixedIndexedContractNotebook` overrides
`_load` with `C.Notebook._load(self)` — `self._apply` indexes each event exactly
once; no second pass. `FixedIndexedLoopNotebook` mirrors
`IndexedLoopNotebook.__init__` with the fixed inner. `scripts/fable_loop220_agent.py`
builds loop138i unchanged except a process-local patch of the single
construction site (`L138d.IndexedLoopNotebook`, which every lineage `__init__`
resolves to) during construction — the same override pattern loop134/138b/138d
use. Log format, API, and decision logic are untouched.

## Why sleep is safe
Sleep replay (`Sleep130Reasoner._queue130`, generalised by `Sleep145Reasoner`)
reads only `notebook.current()` — facts plus `active()`, both log-derived and
immune to index doubling (R2 probes: `current()` empty after forget on both
arms). It never reads `_triples/_sro/_rev`. So a forgotten fact cannot be
replayed into weights on base 138i either; the ghost was serving-only. R5 smoke
marks match 138i exactly (install, 5/5 probes, 0 overwrites).

## Evidence
R1 60/60 index-equal (base 20/60); R2 11/11 clean (base 0/11); R3 20/20
byte-identical replies; R4 0 moves on rt136/rt143/sessions152/bench-800;
R5 identical smoke; R6 load within bound (see RESULTS.md for the one noisy
wall rep note). Verdict: PASS.

## What it does not cover
Fresh-session behaviour is byte-identical by construction (single indexing is
what a fresh session always did); the fix only repairs the reload path. Torn-tail
repair reuses the same `_load`, so it is fixed too (not separately marked).
