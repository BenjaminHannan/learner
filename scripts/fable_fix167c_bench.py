#!/usr/bin/env python3
"""Experiment 167c -- G1 bench through loop167c vs frozen loop167b rows.

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped (same pattern as
scripts/fable_fix167b_bench.py, read-only). Compares per-item verdict AND
reply AND teach_replies against the base loop167b's FROZEN rows
(artifacts/fable-verb167b-20260922/fable_bench167b_loop167b_*_rows.jsonl,
read-only).

Predicted moves (in writing, before the run): verdict ZERO moves on all
600 items (the mouth never touches statuses, writes, or matching); reply
ZERO moves (no frozen loop167b bench reply is a Saved confirmation -- the
37 edit200 reply hits are MISSING_FACT "never_taught_rel_N" lines, which
the narrow Saved-only render leaves byte-identical); teach_replies move
EXACTLY on the Saved-confirmation entries whose relation key contains an
underscore -- pre-seal scan of the frozen base rows counts 415 (edit200) +
640 (new_121_4hop) + 668 (old_s2fresh_4hop) = 1723 such entries -- each
moving by exactly key.replace("_", " ") in the relation slot. Any other
move, or any new wrong vs the base, fails G1 honestly. Outputs go into
artifacts/fable-label167c-20260922/ only.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_bench.py
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
import fable_fix167c_label as F167C  # noqa: E402 (shared move rule)
import fable_loop167c_agent as L167C  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART167B = ROOT / "artifacts" / "fable-verb167b-20260922"
ART167C = ROOT / "artifacts" / "fable-label167c-20260922"

allowed_render = F167C.saved_render_move


def main(argv=None) -> int:
    cfg = copy.deepcopy(L167C.DEFAULT_CONFIG167C)
    ART167C.mkdir(parents=True, exist_ok=True)
    workroot = ART167C / "scratch-bench-loop167c"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop167c",
                 "arms": {}}
    diffs: dict = {}
    ok_all = True
    for split, path, f167b in (
            ("edit200", B129.DATA_EDIT200,
             "fable_bench167b_loop167b_edit200_rows.jsonl"),
            ("old_s2fresh_4hop", B129.DATA_OLD,
             "fable_bench167b_loop167b_old_s2fresh_4hop_rows.jsonl"),
            ("new_121_4hop", B129.DATA_NEW,
             "fable_bench167b_loop167b_new_121_4hop_rows.jsonl")):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / split, L167C.Loop167cDaemon,
                              cfg) for it in items]
        (ART167C / f"fable_bench167c_loop167c_{split}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop167c", {})[split] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop167c {split}: {B129.totals(table)}", flush=True)
        sealed = [json.loads(l) for l in
                  (ART167B / f167b).read_text(
                      encoding="utf-8").splitlines() if l.strip()]
        base = {r["id"]: r for r in sealed}
        verdict_moves = [r["id"] for r in rows
                         if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        reply_moves = [r["id"] for r in rows
                       if base.get(r["id"], {}).get("reply") != r["reply"]]
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
                    if not allowed_render(bt[i], nt[i]):
                        teach_bad.append(f"{r['id']}[{i}]")
        new_wrong = [r["id"] for r in rows
                     if r["verdict"] not in ("OK", "ABSTAIN")
                     and base.get(r["id"], {}).get("verdict") in ("OK", "ABSTAIN")]
        ok = (not verdict_moves and not reply_moves and not teach_bad
              and not new_wrong)
        ok_all = ok_all and ok
        diffs[split] = {"verdict_moves": verdict_moves,
                        "reply_moves": reply_moves,
                        "teach_reply_moved_rows": len(teach_moves),
                        "teach_reply_bad": teach_bad,
                        "new_wrong_vs167b": new_wrong}
        print(f"  vs loop167b: verdict_moves={verdict_moves} "
              f"reply_moves={reply_moves} "
              f"teach_moved_rows={len(teach_moves)} "
              f"teach_bad={teach_bad[:5]} new_wrong={new_wrong}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_base"] = diffs
    (ART167C / "fable_bench167c_loop167c_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']} G1 {'PASS' if ok_all else 'FAIL'}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
