#!/usr/bin/env python3
"""mu-402: does 0.2c's sleep adapter make the chat path make up things about the user? ("Making things up about you"
thread, 2026-09-26. Marks: artifacts/claude-mu402-20260926/PASSMARKS.md.) New file only; imports everything else
read-only.

Why: in 0.2c (VERIFY-02c.md, row S1) the joined build X made up more about the user than the plain twin. A blind
auditor (counts only) put every extra claim in ordinary 1B-written chat replies, not in the notebook's template
lines, and between X and G the only thing that changes those 1B calls is the sleep adapter.

The one change between arms A and B: A runs claude_e2e02c:build_02c with SLEEP02C_ADAPTER set to 0.2c's adapter;
B runs the same build without it (the LoRA is still installed, with B = 0, so it adds exactly zero). Same code,
same panel, same per-turn seeds.

Two helpers, so the test runs on a rental without the 2 GB reader:
  NullReader        stands in for the lis-319 reader: every turn reads as {"act": "CHAT", "facts": [], "ask": null},
                    the reader's own frame for plain chat. The dev panel has no teach or ask turns, so this only
                    removes a download; the notebook stays empty and every reply comes from the 1B layers
                    (creative 333d, think 299b, chat 338b) exactly as in X.
  build_null02c     puts a NullReader into claude_lis319_arms' reader cache under --model NULL, builds
                    build_02c unchanged, then wraps its turn so that torch and random are seeded from
                    (turn number in this conversation, user text) before every turn. Both arms see the same seed
                    on the same turn.

  python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel chat \
      --panel-dir artifacts/claude-mu402-20260926/devchat --arm claude_mu402:build_null02c --name A \
      --model NULL --gen-model BASE --out OUT            (arm A: with SLEEP02C_ADAPTER=<adapter02c.pt>)
  python -B scripts/claude_mu402.py --selftest         (CPU, no model)
"""
from __future__ import annotations

import json
import random
import sys
import zlib
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

NULL_MODEL = "NULL"
SEED402 = 402
CHAT_FRAME = {"act": "CHAT", "facts": [], "ask": None}
_PRINTED: list = []


class NullReader:
    """Reader stand-in with Reader319.read's signature and return shape (frame, confs, text, ms)."""

    def __init__(self):
        self.calls = 0

    def read(self, turn, prev_reply="", history=None):
        self.calls += 1
        return dict(CHAT_FRAME, facts=[]), [], json.dumps(CHAT_FRAME) + "<END>", 0.0


def turn_seed(n: int, text: str) -> int:
    return (zlib.crc32(f"{n}|{text}".encode("utf-8")) ^ SEED402) & 0x7FFFFFFF


def install_seed402(loop) -> None:
    """Outermost: seed torch and random before every turn from (turn number, text)."""
    inner = loop.turn
    count = [0]

    def seeded402(text: str):
        s = turn_seed(count[0], text)
        count[0] += 1
        random.seed(s)
        try:
            import torch
            torch.manual_seed(s)
        except ImportError:
            pass
        return inner(text)

    seeded402.__name__ = "seeded402"
    loop.turn = seeded402


def build_null02c(state_dir, args):
    import claude_e2e02c as E
    import claude_lis319_arms as L319
    if args.model != NULL_MODEL:
        raise SystemExit(f"mu402: --model must be {NULL_MODEL} (the NullReader), got {args.model!r}")
    if E.READER02C != "r319":
        raise SystemExit("mu402: build_02c no longer uses the lis-319 reader path; the NullReader would not be used")
    L319._R319.setdefault(NULL_MODEL, NullReader())
    loop = E.build_02c(state_dir, args)
    install_seed402(loop)
    loop.layers330c = list(getattr(loop, "layers330c", [])) + ["seed402"]
    loop.null402 = L319._R319[NULL_MODEL]
    if not _PRINTED:
        _PRINTED.append(1)
        print(f"mu402: adapter loaded = {getattr(loop, 'sleep02c', None) or 'none (B = 0, base 1B)'}; "
              f"layers = {loop.layers330c}", flush=True)
    return loop


def selftest() -> None:
    import claude_lis300_common as C300
    ok = 0
    r = NullReader()
    frame, confs, text, ms = r.read("hey how's it going", "", [])
    assert frame == CHAT_FRAME and confs == [] and ms == 0.0; ok += 1
    assert C300.parse_frame(text) == CHAT_FRAME; ok += 1                      # the reader's own parser agrees
    frame["facts"].append("x")
    assert r.read("again")[0]["facts"] == []; ok += 1                          # no shared mutable state
    assert turn_seed(0, "hi") == turn_seed(0, "hi") != turn_seed(1, "hi"); ok += 1

    class Loop:
        def __init__(self):
            self.seen = []

        def turn(self, text):
            self.seen.append(random.random())
            return [text]

    a, b = Loop(), Loop()
    install_seed402(a)
    install_seed402(b)
    random.seed(1)
    a.turn("one"), a.turn("two")
    random.seed(99)
    b.turn("one"), b.turn("two")
    assert a.seen == b.seen; ok += 1                                           # same seeds whatever came before
    assert a.turn.__name__ == "seeded402"; ok += 1

    class Args:
        model = "lis319-merged"
    try:
        build_null02c("/nonexistent", Args())
        raise AssertionError("build_null02c accepted a real reader path")
    except SystemExit:
        ok += 1
    print(f"mu402 selftest {ok}/7 ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        raise SystemExit(__doc__)
