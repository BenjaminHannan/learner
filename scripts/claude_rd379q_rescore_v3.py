#!/usr/bin/env python3
"""rd-379q addendum B (report only): rescore notes on the store 0.2c ships (v3, v2's ranking), not v1.

rd-378L's scorer (claude_rd378L_recall.py, sealed) builds its stores with claude_ep382_store (v1, "<speaker>: <text>"
ranking). 0.2c uses claude_ep382_store_v3: v2's '<speaker> said, "<text>"' ranking (bm-393b: ~+5 points MiniLM
evidence recall over v1) and heard-only recall by default. This runs the SAME score() with v3 swapped in and notes
asked for explicitly (sources = heard + note), so it answers: does a notes gain seen on v1 hold on v3's ranking?
Nothing else changes: same questions, same found@k / anyT@k, same outputs (to a different folder). Marks stay on v1.

python claude_rd379q_rescore_v3.py score --data DATA --convs 0-4 --notes NOTES.jsonl --out OUT_DIR
python claude_rd379q_rescore_v3.py selftest   (CPU, BM25 only, no model)
"""
from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ep382_store_v3 as V3  # noqa: E402
import claude_rd378L_recall as R  # noqa: E402


class HeardAndNotes(V3.MemoryStore):
    """v3 with notes asked for on every recall (v3's own default is heard only)."""

    def recall(self, query, *, k=10, sources=None, before=None, mode="fused"):
        return super().recall(query, k=k, sources={"heard", "note"} if sources is None else sources,
                              before=before, mode=mode)


R.M = types.SimpleNamespace(MemoryStore=HeardAndNotes)


def selftest():
    conv = {"sample_id": "x", "qa": [], "conversation": {"session_1_date_time": "1 May 2023", "session_1": [
        {"speaker": "Wren", "dia_id": "D1:1", "text": "I moved to Oakvale in May."},
        {"speaker": "Tobin", "dia_id": "D1:2", "text": "Nice, my dog Pip loves the beach."}]}}
    turns = R.chat_turns(conv)
    ok = {}
    with tempfile.TemporaryDirectory() as d:
        s = R.build_store(d, turns, [(1, "x#0", {"text": "What is the name of Tobin's dog?", "cites": [0]})], True)
        ok["store_is_v3"] = isinstance(s, V3.MemoryStore)
        hits = s.recall("name of Tobin's dog", k=3, mode="bm25")
        ok["note_recalled"] = any(h["source"] == "note" and h["turn_ids"] == [1] for h in hits)
        ok["heard_recalled"] = any(h["source"] == "heard" for h in s.recall("Oakvale", k=3, mode="bm25"))
    with tempfile.TemporaryDirectory() as d:
        a = R.build_store(d, turns, [], False)
        ok["heard_only_store"] = all(h["source"] == "heard" for h in a.recall("dog Pip", k=3, mode="bm25"))
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("RD379Q-V3-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        sys.exit(selftest())
    R.main()
