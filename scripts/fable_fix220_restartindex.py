#!/usr/bin/env python3
"""Exp 220 -- RESTART MUST NOT DOUBLE THE FAST INDEX (one change on loop138i).

Diagnosis (director-verified on loop138i): IndexedContractNotebook._load
(scripts/fable_perf128_index.py:86-89) calls super()._load(), whose loop
already runs self._apply(event) for every log line
(scripts/fable_notebook_contract.py:143-161). self._apply IS
IndexedContractNotebook._apply, which indexes each event
(scripts/fable_perf128_index.py:91-93). _load then runs
`for ev in self.events: self._index_event(ev)` a SECOND time. After any
restart every fact id sits twice in _sr/_rel, every taught triple twice in
_triples/_sro/_rev, and every mention count is doubled. _triple_remove only
removes ONE copy, so a forget-after-restart leaves a stale indexed copy and
the forgotten value is still served.

THE ONE CHANGE (this file only; fable_perf128_index.py is NOT edited):
  FixedIndexedContractNotebook overrides _load to C.Notebook._load(self):
  self._apply indexes each event exactly once; there is no second pass.
  FixedIndexedLoopNotebook mirrors IndexedLoopNotebook.__init__ line for
  line with the fixed inner notebook. Same log format, same API, same
  decision logic; only the in-memory index cardinality changes.

index_state(inner) returns a canonical snapshot of the nine index
structures R1 compares.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix77_core as F77  # noqa: E402 (seal verify, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_perf128_index as P128  # noqa: E402 (wrapped base, read-only)


class FixedIndexedContractNotebook(P128.IndexedContractNotebook):
    """IndexedContractNotebook whose load indexes every event exactly once."""

    def _load(self) -> None:
        # C.Notebook._load calls self._apply per log line; self._apply is
        # IndexedContractNotebook._apply, which already calls
        # self._index_event. No second pass (the removed loop indexed every
        # event a second time).
        C.Notebook._load(self)


class FixedIndexedLoopNotebook(P128.IndexedLoopNotebook):
    """IndexedLoopNotebook shape with the fixed inner notebook."""

    def __init__(self, root) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.nb = FixedIndexedContractNotebook(root)
        self.marks: dict = {}
        self._rebuild_marks()
        self._rebuild_index()
        if self.torn_tail:
            return
        F77.verify_full(self.root)


def index_state(inner) -> dict:
    """Canonical snapshot of the nine index structures R1 compares."""
    return {
        "_sr": sorted((str(k[0]), str(k[1]), list(v))
                      for k, v in inner._sr.items()),
        "_rel": sorted((str(k), list(v)) for k, v in inner._rel.items()),
        "_rel_known": sorted(inner._rel_known),
        "_triples": [tuple(t) for t in inner._triples],
        "_triples_pos": sorted(inner._triples_pos.items()),
        "_sro": sorted((str(k[0]), str(k[1]), list(v))
                       for k, v in inner._sro.items()),
        "_srel": sorted((str(k), list(v)) for k, v in inner._srel.items()),
        "_rev": sorted((str(k[0]), str(k[1]), sorted(v))
                       for k, v in inner._rev.items()),
        "_ment_ref": sorted(inner._ment_ref.items()),
    }
