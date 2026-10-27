#!/usr/bin/env python3
"""lis-320 GLM wording through Ben's opencode route (reading thread, 2026-09-26). New file; claude_lis320_glm.py stays.

The OpenRouter account ran out of funds at 18:38 UTC (full run stopped at 298 of 6000 dialogs). Ben (18:47 UTC) offered
GLM 5.3 Flash through his opencode subscription. The one change here: every wording call goes through
scripts/claude_glm_opencode.py call() (the Director's shared helper, sha 3b597086...) instead of OpenRouter. The prompt
(build_prompt), the parser, the key guard and the output rows are claude_lis320_glm's, run unchanged. The route sets no
temperature and no reasoning effort (opencode's defaults) and may add its own system text; rows record temperature null
and model "opencode-go/glm-5.3-flash". See artifacts/claude-lis320-20260926/ADDENDUM-2-opencode-route.md.
No key is read: opencode holds its own login, and this script never touches opencode config or auth files.

Runs in batches so a job can stop cleanly at its time cap and resume later (rows already in --out are skipped):
    python -B scripts/claude_lis320_glm_oc.py --seeds S.jsonl --out raw.jsonl [--workers 4] [--batch 40]
           [--max-minutes 160] [--max-failed 50] [--limit N]
It stops starting new batches after --max-minutes, or once more than --max-failed calls came back empty (a failed
call is written as an unparsed row, as in claude_lis320_glm). The last line printed is the totals JSON with
"stopped": "done" | "time" | "failed".
selftest (no network): python -B scripts/claude_lis320_glm_oc.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis320_glm as G  # noqa: E402

MODEL = "opencode-go/glm-5.3-flash"
FAILED = {"n": 0}
_LOCK = threading.Lock()


def call_opencode(text):
    import claude_glm_opencode as OC
    try:
        out = OC.call(text, model=MODEL) or ""
    except Exception as e:                            # a failed call is logged and counted, never guessed
        print(f"[glm320oc] call failed: {type(e).__name__} {str(e)[:120]}", flush=True)
        out = ""
    if not out:
        with _LOCK:
            FAILED["n"] += 1
    return out, {}


def run_batches(seeds, out, caller, workers, batch, max_minutes, max_failed):
    t0 = time.time()
    tot = {"calls": 0, "parsed": 0, "skipped": 0, "failed_calls": 0, "batches": 0, "stopped": "done"}
    for i in range(0, len(seeds), batch):
        if max_minutes and (time.time() - t0) / 60 >= max_minutes:
            tot["stopped"] = "time"
            break
        if FAILED["n"] > max_failed:
            tot["stopped"] = "failed"
            break
        b = G.run(seeds[i:i + batch], out, caller, MODEL, None, workers=workers)
        for k in ("calls", "parsed", "skipped"):
            tot[k] += b[k]
        tot["batches"] += 1
    if tot["stopped"] == "done" and FAILED["n"] > max_failed:
        tot["stopped"] = "failed"
    tot["failed_calls"] = FAILED["n"]
    tot["minutes"] = round((time.time() - t0) / 60, 1)
    return tot


def selftest():
    import tempfile
    from claude_lis320_seed import make_seeds
    seeds = make_seeds(1, 5)
    n_turns = {d["dialog_id"]: len(d["turns"]) for d in seeds}
    calls = []

    def fake(p):
        d = next(x for x in seeds if G.build_prompt(x) == p)
        calls.append(d["dialog_id"])
        if len(calls) == 2:                           # one failed call -> unparsed row, counted
            with _LOCK:
                FAILED["n"] += 1
            return "", {}
        n = n_turns[d["dialog_id"]]
        return json.dumps({"turns": [{"n": i + 1, "reply_before": "" if i == 0 else "ok", "user": f"msg {i}"}
                                     for i in range(n)]}), {}

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "raw.jsonl"
        tot = run_batches(seeds[:3], out, fake, workers=2, batch=2, max_minutes=0, max_failed=50)
        assert tot["calls"] == 3 and tot["parsed"] == 2 and tot["failed_calls"] == 1 and tot["stopped"] == "done", tot
        rows = G.load(out)
        assert len(rows) == 3 and all(r["model"] == MODEL and r["temperature"] is None for r in rows)
        tot = run_batches(seeds, out, fake, workers=2, batch=2, max_minutes=0, max_failed=50)
        assert tot["skipped"] == 3 and tot["calls"] == 2, tot           # resume skips rows already written
        FAILED["n"] = 99
        tot = run_batches(seeds, Path(td) / "b.jsonl", fake, workers=2, batch=2, max_minutes=0, max_failed=50)
        assert tot["stopped"] == "failed" and tot["calls"] == 0, tot   # stops before any batch once over the limit
        FAILED["n"] = 0
    try:
        G.guard("here you go sk-or-v1-xxxx")
        raise AssertionError("guard missed the key marker")
    except G.KeyLeak:
        pass
    print("lis320 glm_oc selftest 4/4 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds")
    ap.add_argument("--out")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--max-minutes", type=float, default=0)
    ap.add_argument("--max-failed", type=int, default=50)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    seeds = G.load(a.seeds)
    if a.limit:
        seeds = seeds[: a.limit]
    try:
        tot = run_batches(seeds, a.out, call_opencode, a.workers, a.batch, a.max_minutes, a.max_failed)
    except G.KeyLeak as e:
        raise SystemExit(f"[glm320oc] ABORT: {e}")
    print(json.dumps(tot))


if __name__ == "__main__":
    sys.exit(main())
