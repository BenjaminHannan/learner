#!/usr/bin/env python3
"""Listener wrapper stack, version b (2026-09-24). Changes from claude_lis_stack.py:
  - MemoReader keeps the Reader in a closure (fixes the MPS out-of-memory crash, see below);
  - layers 313 and 314 use claude_lis313b_agent.py and claude_lis314b_agent.py.

Listener wrapper stack: one reader call per turn, shared by every layer.

Layers, innermost first (each is its own sealed wrapper and file):
  310  scripts/claude_lis310_agent.py (builder-outbox)  reader + compiler, all-or-nothing saves
  313  scripts/claude_lis313_agent.py  answers a question from the reader's own ASK frame when
       the rule chain abstains (read-only notebook lookup)
  315  scripts/claude_lis315_agent.py  per-fact release: confident facts save even when another
       fact in the same turn is blocked
  314  scripts/claude_lis314_agent.py  confirm-at-use: unsure facts wait in a pending store that
       never answers; when the user later asks about one: "I think you told me X, is that right?"
  316  scripts/claude_lis316_agent.py  code guards: facts that trip a guard become unsure

build_stack(loop, reader, threshold, layers) installs the chosen layers on a built base loop
(292t in production). MemoReader memoises reader.read by (turn, prev) so an outer layer and
turn310 see the same read, and lets an outer layer hand an edited read to the inner layers.
"""
from __future__ import annotations

from pathlib import Path


class MemoReader:
    """Wraps a Reader. read(turn, prev) calls the real reader once per (turn, prev) key.

    The real reader is kept only inside a closure, never as an attribute. 292t's per-turn
    snapshot (claude_fix260_openers.snapshot260) walks the loop's helper objects and deep-copies
    their plain attributes; with the Reader reachable as an attribute that walk reached the 1B
    model's weights and copied them every turn until MPS ran out of memory (lis-313-f0 and
    lis-314-panel, 2026-09-24). A closure is not walked.
    """

    def __init__(self, reader):
        def _read(turn, prev_reply=""):
            return reader.read(turn, prev_reply)
        self._read = _read
        self.key = None
        self.value = None
        self.calls = 0

    def read(self, turn, prev_reply=""):
        k = (str(turn), str(prev_reply or ""))
        if self.key != k:
            self.value = self._read(turn, prev_reply)
            self.key = k
            self.calls += 1
        return self.value

    def override(self, turn, prev_reply, value):
        """Make the next read of (turn, prev) return value (an edited frame for inner layers)."""
        self.key = (str(turn), str(prev_reply or ""))
        self.value = value

    def forget(self):
        self.key = None
        self.value = None


def build_stack(loop, reader, threshold, layers=("313", "315", "314"), log_dir=None):
    """Install 310 plus the chosen layers. Returns (loop, memo)."""
    import claude_lis310_agent as L310

    memo = MemoReader(reader)
    log_dir = Path(log_dir) if log_dir else None
    lp = (lambda name: str(log_dir / name)) if log_dir else (lambda name: None)
    if "313" in layers:
        import claude_lis313b_agent as L313
        L313.install_turn313(loop, memo, threshold=threshold, log_path=lp("lis313_log.jsonl"),
                             log_path310=lp("lis310_log.jsonl"))
    else:
        L310.install_turn310(loop, memo, threshold=threshold, log_path=lp("lis310_log.jsonl"))
    if "315" in layers:
        import claude_lis315_agent as L315
        L315.install_turn315(loop, memo, threshold=threshold, log_path=lp("lis315_log.jsonl"))
    if "314" in layers:
        import claude_lis314b_agent as L314
        L314.install_turn314(loop, memo, threshold=threshold, log_path=lp("lis314_log.jsonl"))
    if "316" in layers:
        import claude_lis316_agent as L316
        L316.install_turn316(loop, memo)
    loop.lis_stack_layers = tuple(layers)
    loop.lis_memo = memo
    return loop, memo
