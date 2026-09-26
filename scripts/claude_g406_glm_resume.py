#!/usr/bin/env python3
"""g406 resume: mark the transcripts the first g406 run left without a usable answer ("Making things up about you",
2026-09-26). New file; scripts/claude_g406_glm.py stays as sealed. See artifacts/claude-g406-20260926/ADDENDUM-3-resume.md.

What is the same: the prompt (claude_g406_glm.build_prompt, the judges' rubric unchanged), the parser
(claude_g406_glm.parse), the packets and the row shape. What differs: calls go through the Director's helper v1.1
(scripts/claude_glm_opencode_v11.py, deletes only the session it made), a transcript counts as done only when an
earlier row for it is usable (ok true), and each row keeps "error": the first 200 characters of the helper's failure
message, or "unparsed reply" when the call worked but no usable JSON came back (then "reply_chars" is its length).
The reply text itself is not kept.

    python -B scripts/claude_g406_glm_resume.py --packets P1 --packets P2 --prev RUN1.jsonl --out RESUME.jsonl \
        [--workers 3] [--batch 30] [--max-minutes 150] [--max-failed 40]
    python -B scripts/claude_g406_glm_resume.py --selftest   (no network)
The count then reads the usable rows of both files (claude_g406_count.py --glm on their concatenation: for each
transcript the usable row wins; merge_rows below does it).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_g406_glm as G  # noqa: E402

MODEL = G.MODEL


def call_v11(text: str) -> str:
    import claude_glm_opencode_v11 as OC
    return OC.call(text, model=MODEL) or ""


def mark(p: dict, caller) -> dict:
    t0 = time.time()
    n = len(p["conversation"])
    err, raw = "", ""
    try:
        raw = caller(G.build_prompt(p["conversation"]))
    except Exception as e:  # noqa: BLE001
        err = str(e)[:200] or type(e).__name__
    flags = G.parse(raw, n) if not err else None
    row = {"src": p["src"], "pid": p["pid"], "n": n, "flags": flags, "ok": flags is not None,
           "seconds": round(time.time() - t0, 1), "error": err or ("" if flags is not None else "unparsed reply")}
    if not err and flags is None:
        row["reply_chars"] = len(raw)
    return row


def usable_keys(path: Path) -> set:
    if not path.exists():
        return set()
    return {(r["src"], r["pid"]) for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r["ok"]}


def merge_rows(*paths: Path) -> list[dict]:
    best: dict = {}
    for path in paths:
        if not path.exists():
            continue
        for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()):
            k = (r["src"], r["pid"])
            if k not in best or (r["ok"] and not best[k]["ok"]):
                best[k] = r
    return list(best.values())


def run(packets, prev: Path, out: Path, caller, workers, batch, max_minutes, max_failed) -> dict:
    done = usable_keys(prev) | usable_keys(out)
    todo = [p for p in packets if (p["src"], p["pid"]) not in done]
    t0, failed, written, stopped = time.time(), 0, 0, "done"
    out.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i in range(0, len(todo), batch):
            if (time.time() - t0) / 60 > max_minutes:
                stopped = "time"
                break
            if failed > max_failed:
                stopped = "failed"
                break
            rows = list(ex.map(lambda p: mark(p, caller), todo[i:i + batch]))
            with out.open("a", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
            failed += sum(1 for r in rows if not r["ok"])
            written += len(rows)
            print(f"[g406r] {len(done) + written - failed}/{len(packets)} usable so far, {failed} failed this run",
                  flush=True)
    return {"packets": len(packets), "usable_before": len(done), "written": written, "failed_this_run": failed,
            "minutes": round((time.time() - t0) / 60, 1), "stopped": stopped}


def selftest() -> None:
    import tempfile
    ok = 0
    conv = [{"user": "u", "assistant": "a"}, {"user": "u2", "assistant": "a2"}]
    pk = [{"src": "s", "pid": f"p{i}", "conversation": conv} for i in range(4)]
    with tempfile.TemporaryDirectory() as td:
        prev, out = Path(td) / "prev.jsonl", Path(td) / "out.jsonl"
        prev.write_text(json.dumps({"src": "s", "pid": "p0", "n": 2, "flags": [0, 1], "ok": True}) + "\n" +
                        json.dumps({"src": "s", "pid": "p1", "n": 2, "flags": None, "ok": False}) + "\n")

        def boom(t):
            raise RuntimeError("opencode call failed after 3 tries: exit 1: > build")
        res = run(pk, prev, out, boom, 2, 2, 5, 10)
        rows = [json.loads(x) for x in out.read_text().splitlines()]
        assert res["usable_before"] == 1 and res["written"] == 3; ok += 1
        assert all(r["error"].startswith("opencode call failed") for r in rows); ok += 1
        res = run(pk, prev, out, lambda t: "sure! no json here", 2, 2, 5, 10)
        rows = [json.loads(x) for x in out.read_text().splitlines()][3:]
        assert all(r["error"] == "unparsed reply" and r["reply_chars"] == 18 for r in rows); ok += 1
        res = run(pk, prev, out, lambda t: '{"flags": [1, 0]}', 2, 2, 5, 10)
        assert res["written"] == 3 and res["failed_this_run"] == 0; ok += 1
        m = merge_rows(prev, out)
        assert len(m) == 4 and all(r["ok"] for r in m); ok += 1
        assert G.build_prompt(conv) == G.build_prompt(conv) and "If yes, flag it." in G.build_prompt(conv); ok += 1
    print(f"g406 resume selftest {ok}/6 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packets", action="append", default=[])
    ap.add_argument("--prev")
    ap.add_argument("--out")
    ap.add_argument("--merge-to", help="write the merged rows (usable row wins) of --prev and --out here and exit")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--batch", type=int, default=30)
    ap.add_argument("--max-minutes", type=float, default=150)
    ap.add_argument("--max-failed", type=int, default=40)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.merge_to:
        rows = merge_rows(Path(a.prev), Path(a.out))
        Path(a.merge_to).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        print(json.dumps({"merged": len(rows), "usable": sum(r["ok"] for r in rows)}))
        return
    packets = G.load_packets(a.packets)
    print(json.dumps(run(packets, Path(a.prev), Path(a.out), call_v11, a.workers, a.batch, a.max_minutes,
                         a.max_failed)))


if __name__ == "__main__":
    main()
