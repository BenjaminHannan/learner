"""Notebook: host-side slots (plain software, no weights). The model proposes writes; the host validates and writes.

Entries are supersedable (edit keeps history), snapshot-hashable, and lockable (sleep holds the lock).
claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import copy
import hashlib
import json

MAX_SLOTS, MAX_ENTRY_TOKENS = 8, 12


class NotebookError(Exception):
    pass


@dataclass
class Slot:
    slot_id: int
    text: str
    source: str = "taught"      # "taught" | "model_write"
    version: int = 0
    history: list = field(default_factory=list)


class Notebook:
    def __init__(self, slots=None):
        self.slots: list[Slot] = list(slots or [])
        self._locked = False

    @classmethod
    def from_facts(cls, facts):
        return cls([Slot(i, t) for i, t in enumerate(facts)])

    def texts(self): return [s.text for s in self.slots]

    def with_fact_changed(self, slot: int, text: str) -> "Notebook":
        nb = copy.deepcopy(self); nb._locked = False
        nb.slots[slot].text = text
        return nb

    @contextmanager
    def write_lock(self):
        self._locked = True
        try: yield self
        finally: self._locked = False

    def apply_write(self, slot_choice: int, span, question: str, offsets, tok) -> Slot:
        """slot_choice == len(slots) means NEW. span = (start_tok, end_tok) inclusive, into the question."""
        if self._locked: raise NotebookError("notebook is locked (sleep night)")
        s, e = span
        if not (0 <= s <= e < len(offsets)) or e - s + 1 > MAX_ENTRY_TOKENS: raise NotebookError("bad span")
        text = question[offsets[s][0]:offsets[e][1]]
        if slot_choice >= len(self.slots):
            if len(self.slots) >= MAX_SLOTS: raise NotebookError("notebook full")
            self.slots.append(Slot(len(self.slots), text, "model_write"))
            return self.slots[-1]
        slot = self.slots[slot_choice]
        slot.history.append((slot.version, slot.text))   # an edit supersedes and keeps history
        slot.text, slot.source, slot.version = text, "model_write", slot.version + 1
        return slot

    def snapshot(self):
        return [(s.slot_id, s.text, s.source, s.version) for s in self.slots]

    def hash(self) -> str:
        return hashlib.sha256(json.dumps(self.snapshot()).encode()).hexdigest()

    def to_json(self) -> str:
        return json.dumps([{"slot_id": s.slot_id, "text": s.text, "source": s.source,
                            "version": s.version, "history": s.history} for s in self.slots])

    @classmethod
    def from_json(cls, blob: str):
        return cls([Slot(d["slot_id"], d["text"], d["source"], d["version"], [tuple(h) for h in d["history"]])
                    for d in json.loads(blob)])
