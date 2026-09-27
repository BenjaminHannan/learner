#!/usr/bin/env python3
"""lis-320 wording through GPT-6 Luna (Ben's Codex plan) instead of GLM (reading thread, 2026-09-27; ADDENDUM-9).
New file; claude_lis320_glm_oc.py and claude_lis320_glm_oclow.py stay as sealed.

The one change is the writer: each wording call goes to scripts/claude_luna_codex.py call() (the Director's helper,
sha 342a0fb7..., model gpt-6-luna, live check passed 03:54 UTC 09-27). The prompt (claude_lis320_glm.build_prompt), parser,
key guard, batching, time/failure stops and row format are claude_lis320_glm_oc's, run unchanged; rows record model
"gpt-6-luna" and temperature null. The helper already refuses empty or error-like replies (retries, then raises); a
refused call is written as an empty unparsed row and counted as failed, as before. No key or ~/.codex file is read.
Same flags as claude_lis320_glm_oc.py.
    python -B scripts/claude_lis320_luna.py --seeds S.jsonl --out raw.jsonl --workers 3 --max-minutes 70
    python -B scripts/claude_lis320_luna.py --selftest        (no network)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis320_glm_oc as B  # noqa: E402

MODEL = "gpt-6-luna"


def call_luna(text):
    import claude_luna_codex as L
    try:
        out = L.call(text, model=MODEL) or ""
    except Exception as e:                            # a failed call is logged and counted, never guessed
        print(f"[lis320luna] call failed: {type(e).__name__} {str(e)[:160]}", flush=True)
        out = ""
    if not out:
        with B._LOCK:
            B.FAILED["n"] += 1
    return out, {}


def selftest():
    import json
    import tempfile
    import claude_luna_codex as L
    from claude_lis320_seed import make_seeds
    B.MODEL = MODEL
    seeds = make_seeds(2, 3)
    n_turns = {d["dialog_id"]: len(d["turns"]) for d in seeds}
    sent = []

    def fake_call(text, model=None, timeout=300):
        d = next(x for x in seeds if B.G.build_prompt(x) == text)
        sent.append((d["dialog_id"], model))
        if len(sent) == 2:
            raise RuntimeError("luna call failed after 3 tries: error-like reply")
        return json.dumps({"turns": [{"n": i + 1, "reply_before": "" if i == 0 else "ok", "user": f"msg {i}"}
                                     for i in range(n_turns[d["dialog_id"]])]})

    real = L.call
    L.call = fake_call
    try:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "raw.jsonl"
            B.FAILED["n"] = 0
            tot = B.run_batches(seeds, out, call_luna, workers=1, batch=2, max_minutes=0, max_failed=50)
            rows = B.G.load(out)
    finally:
        L.call = real
        B.FAILED["n"] = 0
    assert all(m == MODEL for _, m in sent), sent
    assert tot["calls"] == 3 and tot["parsed"] == 2 and tot["failed_calls"] == 1, tot
    assert len(rows) == 3 and all(r["model"] == MODEL and r["temperature"] is None for r in rows), rows
    assert sum(1 for r in rows if not r["raw"]) == 1
    print("lis320 luna selftest ok (writer gpt-6-luna; failed call -> empty unparsed row; no network)")


def main():
    B.MODEL = MODEL
    B.call_opencode = call_luna
    if "--selftest" in sys.argv:
        return selftest()
    return B.main()


if __name__ == "__main__":
    sys.exit(main())
