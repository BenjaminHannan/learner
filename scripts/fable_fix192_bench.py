#!/usr/bin/env python3
"""Experiment 192 -- bench through loop192 vs frozen loop167e rows.

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped (same pattern as
scripts/fable_fix167e_bench.py, read-only). Compares per-item verdict AND
reply AND teach_replies against loop167e's FROZEN rows
(artifacts/fable-label167e-20260922/fable_bench167e_loop167e_*_rows.jsonl,
read-only).

Predicted moves: see PASSMARKS.md (written before the run; verdict ZERO
moves on all 600 items; reply/teach_replies moves ONLY by the shared
correct-reply rule -- a Saved confirmation of a replacement turn moved
to the sealed Updated template). 0 new wrong vs loop167e; each run
< 25 min Mac CPU. Outputs go into
artifacts/fable-correctreply192-20260922/ only.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_bench.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop129b_bench as B129  # noqa: E402 (runners/scorer, read-only)
import fable_fix192_correctreply as F192  # noqa: E402 (shared move rule)
import fable_loop192_agent as L192  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART167E = ROOT / "artifacts" / "fable-label167e-20260922"
ART192 = ROOT / "artifacts" / "fable-correctreply192-20260922"

allowed_move = F192.correctreply_move


def main(argv=None) -> int:
    cfg = copy.deepcopy(L192.DEFAULT_CONFIG192)
    ART192.mkdir(parents=True, exist_ok=True)
    workroot = ART192 / "scratch-bench-loop192"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop192",
                 "arms": {}}
    diffs: dict = {}
    ok_all = True
    for split, path, f167e in (
            ("edit200", B129.DATA_EDIT200,
             "fable_bench167e_loop167e_edit200_rows.jsonl"),
            ("old_s2fresh_4hop", B129.DATA_OLD,
             "fable_bench167e_loop167e_old_s2fresh_4hop_rows.jsonl"),
            ("new_121_4hop", B129.DATA_NEW,
             "fable_bench167e_loop167e_new_121_4hop_rows.jsonl")):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / split, L192.Loop192Daemon,
                              cfg) for it in items]
        (ART192 / f"fable_bench192_loop192_{split}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop192", {})[split] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop192 {split}: {B129.totals(table)}", flush=True)
        sealed = [json.loads(l) for l in
                  (ART167E / f167e).read_text(
                      encoding="utf-8").splitlines() if l.strip()]
        base = {r["id"]: r for r in sealed}
        verdict_moves = [r["id"] for r in rows
                         if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        reply_moves, reply_bad = [], []
        for r in rows:
            b = base.get(r["id"], {})
            if b.get("reply") != r["reply"]:
                if allowed_move(b.get("reply", ""), r["reply"]):
                    reply_moves.append(r["id"])
                else:
                    reply_bad.append(r["id"])
        teach_moves, teach_bad = [], []
        for r in rows:
            b = base.get(r["id"], {})
            bt = b.get("teach_replies", [])
            nt = r.get("teach_replies", [])
            if len(bt) != len(nt):
                teach_bad.append(r["id"])
                continue
            moved = [i for i, (o, n) in enumerate(zip(bt, nt)) if o != n]
            if moved:
                teach_moves.append(r["id"])
                for i in moved:
                    if not allowed_move(bt[i], nt[i]):
                        teach_bad.append(f"{r['id']}[{i}]")
        new_wrong = [r["id"] for r in rows
                     if r["verdict"] not in ("OK", "ABSTAIN")
                     and base.get(r["id"], {}).get("verdict") in ("OK", "ABSTAIN")]
        ok = (not verdict_moves and not reply_bad and not teach_bad
              and not new_wrong)
        ok_all = ok_all and ok
        diffs[split] = {"verdict_moves": verdict_moves,
                        "reply_moves": reply_moves,
                        "reply_bad": reply_bad,
                        "teach_reply_moved_rows": teach_moves,
                        "teach_reply_bad": teach_bad,
                        "new_wrong_vs167e": new_wrong}
        print(f"  vs loop167e: verdict_moves={verdict_moves} "
              f"reply_moves={reply_moves} "
              f"reply_bad={reply_bad[:5]} "
              f"teach_moved_rows={teach_moves} "
              f"teach_bad={teach_bad[:5]} new_wrong={new_wrong}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_base"] = diffs
    (ART192 / "fable_bench192_loop192_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']} BENCH {'PASS' if ok_all else 'FAIL'}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
