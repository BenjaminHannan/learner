#!/usr/bin/env python3
"""Exp 241b REPORT-ONLY (no bar): the old 241 sweep re-rendered through A v2.

Reads 241's sealed sweep frames (dev material for 241b) and 241's own
registered M1 misses (artifacts/claude-mouth241-20260922/score241.json,
42 replies the director's 241 grader marked ungrammatical). Every frame's
legacy line goes through the sealed 241b render_line with the frame's
records. For each old miss the report gives the old text, the new text and
a MECHANICAL status only:
  not fixed (unchanged)  -- the 241b text is byte-identical to 241's
  changed                -- the text changed and every 241b mechanical
                            sub-mark is 0 on it; whether the grader's
                            complaint is gone is NOT judged here (the
                            builder never grades); the list is for the
                            director to confirm
  changed, sub-mark hit  -- changed but a 241b sub-mark still fires
Also: route counts, changed-reply counts by act, and the sub-marks over the
whole re-rendered sweep.

Output: artifacts/claude-mouth241b-20260922/rer241.json and a printout.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
REPO = SCRIPTS.parent

import claude_loop241b_agent as A  # noqa: E402 (sealed render path)
import claude_mouth241b_score as SC  # noqa: E402 (sealed sub-marks)

OLD = REPO / "artifacts/claude-mouth241-20260922"
OUT = REPO / "artifacts/claude-mouth241b-20260922/rer241.json"


def _jsonl(p):
    with open(p, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def main() -> int:
    frames = _jsonl(OLD / "sweep-frames.jsonl")
    old = {r["id"]: r["text"] for r in _jsonl(OLD / "sweep.jsonl")}
    misses = json.loads((OLD / "score241.json").read_text())["M1"][
        "ungrammatical"]
    new, fr2 = {}, {}
    routes, changed = Counter(), Counter()
    for f in frames:
        res = A.render_line(f["legacy_text"], f.get("records"), [])
        new[f["id"]] = res["text"]
        g = dict(f)
        g["frame"] = res.get("frame") or f["frame"]
        fr2[f["id"]] = g
        routes[(f["act"], res["route"])] += 1
        if res["text"] != old[f["id"]]:
            changed[f["act"]] += 1
    table = json.loads(Path(SC.SAY_TABLE).read_text())
    hits = SC.submarks(new, fr2, table)
    hit_ids = {}
    for k, v in hits.items():
        for x in v:
            i = x[0] if isinstance(x, (list, tuple)) else x
            hit_ids.setdefault(str(i), []).append(k)
    rows = []
    st = Counter()
    for m in misses:
        i, act, old_text, reason = m[0], m[1], m[2], m[3]
        nt = new[i]
        if nt == old[i]:
            s = "not fixed (unchanged)"
        elif hit_ids.get(i):
            s = "changed, sub-mark hit " + ",".join(hit_ids[i])
        else:
            s = "changed"
        st[s.split(" ")[0] if s.startswith("changed,") else s] += 1
        rows.append({"id": i, "act": act, "grader_reason_241": reason,
                     "old": old_text, "new": nt, "status": s})
    summ = {
        "n_frames": len(frames),
        "non_A_routes": {f"{a}/{r}": n for (a, r), n in routes.items()
                         if r != "A"},
        "changed_vs_241_by_act": dict(changed),
        "submarks_nonzero": {k: len(v) for k, v in hits.items() if v},
        "old_misses": len(misses),
        "old_miss_status": dict(st),
        "misses": rows,
    }
    OUT.write_text(json.dumps(summ, indent=1, ensure_ascii=False) + "\n")
    print(f"rer241: {len(frames)} frames; non-A routes "
          f"{summ['non_A_routes']}; changed vs 241 {dict(changed)}")
    print(f"sub-marks non-zero on the re-rendered sweep: "
          f"{summ['submarks_nonzero']}")
    print(f"old misses {len(misses)}: {dict(st)}")
    for r in rows:
        print(f"  {r['id']} {r['act']:15s} [{r['status']}]")
        print(f"     241 : {r['old']}")
        print(f"     241b: {r['new']}")
        print(f"     241 grader: {r['grader_reason_241']}")
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
