#!/usr/bin/env python3
"""Experiment 167e -- G1 bench through loop167e vs frozen loop167c rows.

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped (same pattern as
scripts/fable_fix167c_bench.py, read-only). Compares per-item verdict AND
reply AND teach_replies against the base loop167c's FROZEN rows
(artifacts/fable-label167c-20260922/fable_bench167c_loop167c_*_rows.jsonl,
read-only).

Predicted moves (in writing, before the run): verdict ZERO moves on all
600 items (the mouth never touches statuses, writes, or matching);
teach_replies ZERO moves (Saved lines are already spaced in the frozen
167c rows and the 167e render is idempotent on them); reply moves
EXACTLY on MISSING_FACT "I don't know" replies whose relation key
contains an underscore -- pre-seal scan of the frozen base rows finds
37 such replies, all in edit200 (bench65-abs-absent-01/03/.../23 odd ids
+ bench65-abs-broken-00..24, relation never_taught_rel_N), each moving
by exactly key.replace("_", " ") in the relation slot; ZERO reply
moves in old_s2fresh_4hop/new_121_4hop. Any other move, or any new
wrong vs the base, fails G1 honestly. Outputs go into
artifacts/fable-label167e-20260922/ only.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_bench.py
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
import fable_fix167e_label as F167E  # noqa: E402 (shared move rule)
import fable_loop167e_agent as L167E  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART167C = ROOT / "artifacts" / "fable-label167c-20260922"
ART167E = ROOT / "artifacts" / "fable-label167e-20260922"

allowed_render = F167E.label_render_move


def main(argv=None) -> int:
    cfg = copy.deepcopy(L167E.DEFAULT_CONFIG167E)
    ART167E.mkdir(parents=True, exist_ok=True)
    workroot = ART167E / "scratch-bench-loop167e"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop167e",
                 "arms": {}}
    diffs: dict = {}
    ok_all = True
    for split, path, f167c in (
            ("edit200", B129.DATA_EDIT200,
             "fable_bench167c_loop167c_edit200_rows.jsonl"),
            ("old_s2fresh_4hop", B129.DATA_OLD,
             "fable_bench167c_loop167c_old_s2fresh_4hop_rows.jsonl"),
            ("new_121_4hop", B129.DATA_NEW,
             "fable_bench167c_loop167c_new_121_4hop_rows.jsonl")):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / split, L167E.Loop167eDaemon,
                              cfg) for it in items]
        (ART167E / f"fable_bench167e_loop167e_{split}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop167e", {})[split] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop167e {split}: {B129.totals(table)}", flush=True)
        sealed = [json.loads(l) for l in
                  (ART167C / f167c).read_text(
                      encoding="utf-8").splitlines() if l.strip()]
        base = {r["id"]: r for r in sealed}
        verdict_moves = [r["id"] for r in rows
                         if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        reply_moves, reply_bad = [], []
        for r in rows:
            b = base.get(r["id"], {})
            if b.get("reply") != r["reply"]:
                if allowed_render(b.get("reply", ""), r["reply"]):
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
                    if not allowed_render(bt[i], nt[i]):
                        teach_bad.append(f"{r['id']}[{i}]")
        new_wrong = [r["id"] for r in rows
                     if r["verdict"] not in ("OK", "ABSTAIN")
                     and base.get(r["id"], {}).get("verdict") in ("OK", "ABSTAIN")]
        ok = (not verdict_moves and not reply_bad and not teach_moves
              and not teach_bad and not new_wrong)
        ok_all = ok_all and ok
        diffs[split] = {"verdict_moves": verdict_moves,
                        "reply_moves": reply_moves,
                        "reply_bad": reply_bad,
                        "teach_reply_moved_rows": len(teach_moves),
                        "teach_reply_bad": teach_bad,
                        "new_wrong_vs167c": new_wrong}
        print(f"  vs loop167c: verdict_moves={verdict_moves} "
              f"reply_moves={len(reply_moves)} "
              f"reply_bad={reply_bad[:5]} "
              f"teach_moved_rows={len(teach_moves)} "
              f"teach_bad={teach_bad[:5]} new_wrong={new_wrong}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_base"] = diffs
    (ART167E / "fable_bench167e_loop167e_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']} G1 {'PASS' if ok_all else 'FAIL'}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
