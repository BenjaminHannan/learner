#!/usr/bin/env python3
"""Merge 138l -- scorer for marks L2..L6 (L1 has its own judge in
scripts/claude_138l_l1.py). Reads only row files; runs nothing.

Run dir layout (all produced by the registered commands in PASSMARKS.md):
  sd/                 fable_suitediff218 vs 138k's saved rows
                      (--base-dir artifacts/claude-merge138k-20260922/run/sd)
  rt143nogate-l.json  claude_138l_rt143nogate.py on 138l
  smoke-{k,l}.json    fable_sleepsmoke206.py
  bench{1,2,3}/       fable_suitediff218 --only bench, three back-to-back runs
  lat-{k,l}-{1,2,3}.json  claude_merge138k_latency.py, alternating processes
  probe/{k,l}-p3-dialogs.json  claude_merge138k_probe.py on the 138j
                      verifier's 15 dialogs

usage: claude_138l_score.py <run_dir> <predicted_moves138l.json> <out.json>
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
K_RUN = ROOT / "artifacts/claude-merge138k-20260922/run"
A222 = ROOT / "artifacts/fable-ofteachb222-20260922"
BENCH_FILES = ("bench132_4hop", "edit200", "new_121_4hop", "old_s2fresh_4hop")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def jsonl(p: Path) -> dict:
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def l2(run: Path, pred: dict) -> dict:
    res = {}
    ok_all = True
    sdir = {"rt136": run / "sd136", "sessions152": run / "sd",
            "bench": run / "sd", "marks123": run / "sd"}
    skipped = [s for s, d in sdir.items() if not (d / f"{s}-diff.json").exists()]
    res["suites_skipped"] = skipped
    ok_all &= not skipped
    if skipped:
        res["pass"] = False
        return res
    for suite in ("rt136", "sessions152", "bench", "marks123"):
        d = jl(sdir[suite] / f"{suite}-diff.json")
        got = {(m["id"], m["class"]) for m in d["moves"]}
        want = {(m["id"], m["class"]) for m in pred["L2"][suite]}
        unpred = sorted(got - want)
        missing = sorted(want - got)
        exc = set(pred["L2_literal_bar_exceptions"].get(suite, []))
        bad_new = sorted(m["id"] for m in d["moves"]
                         if m["class"] in ("new WRONG", "new WRONG-WRITE",
                                           "new junk write", "lost OK")
                         and m["id"] not in exc)
        ok = not unpred and not missing and not bad_new
        res[suite] = {"n_moves": len(got), "class_counts": d.get("class_counts"),
                      "unpredicted": unpred, "predicted_not_seen": missing,
                      "new_bad_outside_exceptions": bad_new, "pass": ok}
        ok_all &= ok
    # exception rows must equal 222's sealed rows
    a = jsonl(A222 / "rt136" / "rt136-rows.json")
    b = jsonl(run / "sd136" / "rt136-rows.json")
    keys = ("reply", "stored", "verdict")
    # direct row check against 138k's own saved rt136 rows
    kr = jsonl(K_RUN / "sd" / "rt136-rows.json")
    moved = sorted(i for i in kr if any(kr[i][k] != b[i][k] for k in keys))
    want136 = sorted(m["id"] for m in pred["L2"]["rt136"])
    res["rt136_direct_vs_138k_rows"] = {"moved": moved,
                                        "pass": moved == want136
                                        and len(kr) == len(b)}
    ok_all &= res["rt136_direct_vs_138k_rows"]["pass"]
    rt136_same = [i for i in pred["L2_literal_bar_exceptions"]["rt136"]
                  if all(a[i][k] == b[i][k] for k in keys)]
    a = jsonl(A222 / "bench" / "bench-edit200-rows.jsonl")
    b = jsonl(run / "sd" / "bench-edit200-rows.jsonl")
    bench_same = [i for i in pred["L2_literal_bar_exceptions"]["bench"]
                  if a[i]["reply"] == b[i]["reply"]
                  and a[i]["verdict"] == b[i]["verdict"]
                  and a[i].get("teach_replies") == b[i].get("teach_replies")]
    exc_ok = (len(rt136_same) == len(pred["L2_literal_bar_exceptions"]["rt136"])
              and len(bench_same) == len(pred["L2_literal_bar_exceptions"]["bench"]))
    res["exceptions_identical_to_222_rows"] = {
        "rt136": f"{len(rt136_same)}/{len(pred['L2_literal_bar_exceptions']['rt136'])}",
        "bench": f"{len(bench_same)}/{len(pred['L2_literal_bar_exceptions']['bench'])}",
        "pass": exc_ok}
    ok_all &= exc_ok
    # rt143 no-gate vs 138k's saved rows
    base = {r["id"]: r for r in jl(K_RUN / "rt143nogate-k.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-l.json")}
    moves = []
    for cid, r in base.items():
        f = [k for k in ("teach_replies", "triples", "reply") if r[k] != new[cid][k]]
        if f:
            moves.append({"id": cid, "fields": f, "base_reply": r["reply"],
                          "new_reply": new[cid]["reply"]})
    want = {m["id"]: m for m in pred["L2"]["rt143_nogate"]}
    rt_bad = [m["id"] for m in moves if m["id"] not in want
              or m["fields"] != want[m["id"]]["fields"]
              or m["new_reply"] != want[m["id"]]["new_reply"]]
    rt_missing = sorted(set(want) - {m["id"] for m in moves})
    rt_ok = not rt_bad and not rt_missing and len(new) == len(base)
    res["rt143_nogate"] = {"n": len(base), "moves": moves, "bad": rt_bad,
                           "predicted_not_seen": rt_missing, "pass": rt_ok}
    ok_all &= rt_ok
    res["pass"] = ok_all
    return res


def _walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            _walk(a.get(k), b.get(k), f"{path}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _walk(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append(path)


def l3(run: Path) -> dict:
    diffs = []
    _walk(jl(run / "smoke-k.json"), jl(run / "smoke-l.json"), "", diffs)
    allowed = {".agent", ".config", ".label", ".seconds", ".root", ".report"}
    bad = [d for d in diffs if d not in allowed]
    return {"differing_fields": diffs, "bad": bad, "pass": not bad}


def l4(run: Path) -> dict:
    same = []
    for f in BENCH_FILES:
        blobs = [(run / f"bench{i}" / f"bench-{f}-rows.jsonl").read_bytes()
                 for i in (1, 2, 3)]
        same.append(f if blobs[0] == blobs[1] == blobs[2] else None)
    n = sum(1 for x in same if x)
    return {"identical_files": f"{n}/4", "pass": n == 4}


def l5(run: Path) -> dict:
    lk, ll = [], []
    for i in (1, 2, 3):
        lk += jl(run / f"lat-k-{i}.json")["times_ms"]
        ll += jl(run / f"lat-l-{i}.json")["times_ms"]
    mk, ml = statistics.median(lk), statistics.median(ll)
    return {"median_k_ms": round(mk, 3), "median_l_ms": round(ml, 3),
            "delta_ms": round(ml - mk, 3), "n_k": len(lk), "n_l": len(ll),
            "pass": ml - mk <= 5.0}


def l6(run: Path) -> dict:
    k = jl(run / "probe" / "k-p3-dialogs.json")["rows"]
    l = jl(run / "probe" / "l-p3-dialogs.json")["rows"]
    changes, bad_writes = [], []
    for a, b in zip(k, l):
        for i, (ta, tb) in enumerate(zip(a["turns"], b["turns"])):
            if ta != tb:
                changes.append({"dialog": a["dialog"], "turn": i,
                                "k": ta, "l": tb})
        extra = [t for t in b["stored"] if t not in a["stored"]]
        if extra or len(b["stored"]) > len(a["stored"]):
            bad_writes.append({"dialog": a["dialog"], "extra": extra})
        if not b.get("dup_ok_all", True):
            bad_writes.append({"dialog": b["dialog"], "dup_ok_all": False})
    return {"dialogs": len(l), "reply_or_turn_changes": changes,
            "bad_writes": bad_writes,
            "pass": len(k) == len(l) == 15 and not bad_writes and not changes}


def main() -> int:
    run, pred_p, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    pred = jl(pred_p)
    marks = {"L2": l2(run, pred), "L3": l3(run), "L4": l4(run),
             "L5": l5(run), "L6": l6(run)}
    for k, v in marks.items():
        print(k, "PASS" if v["pass"] else "FAIL",
              json.dumps({x: y for x, y in v.items() if x != "pass"})[:900],
              flush=True)
    out.write_text(json.dumps(marks, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    return 0 if all(v["pass"] for v in marks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
