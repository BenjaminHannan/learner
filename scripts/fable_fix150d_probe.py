#!/usr/bin/env python3
"""Exp 150d T1/T2 probe -- 44-case Title-Case-hedge probe + bench132-152.

T1: >=15 Title-Case song/film/book names starting with a hedge phrase
(subjects/values/chains save+answer like neutral names); >=15 real hedges
(phone form + all-caps) refused byte-identical to loop138b; >=10 others
unchanged. T2: bench132-4hop-152 flips to correct on loop150d.

Isolation: --arm loop150d runs the 150d arm in-process (fresh loop per
case); --arm loop138b runs the frozen base in-process. Default (no --arm)
spawns both arms as subprocesses (the 150d import patches S150
process-wide, so the arms must never share a process), joins, judges.
Outputs into artifacts/fable-hedgecase150d-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix150d_probe.py
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-hedgecase150d-20260922"


def run_arm(arm: str) -> dict:
    import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
    if arm == "loop150d":
        import fable_loop150d_agent as L  # noqa: E402 (agent under test)
        build, cfg0 = L.build_agent150d, L.DEFAULT_CONFIG150D
    else:
        import fable_loop138b_agent as L  # noqa: E402 (frozen base, read-only)
        build, cfg0 = L.build_agent138b, L.DEFAULT_CONFIG138B
    cases = json.loads((ART / "cases150d.json").read_text(
        encoding="utf-8"))["cases"]
    out: dict = {}
    for case in cases:
        tmp = tempfile.mkdtemp(prefix=f"p150d_{case['id']}_")
        cfg = copy.deepcopy(cfg0)
        cfg["state_dir"] = tmp
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        replies = [" ".join(loop.turn(t)) for t in case["steps"]]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        out[case["id"]] = {"replies": replies, "stored": stored}
    if arm == "loop150d":
        # T2: the registered bench132-152 item through the 150d daemon.
        import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
        item = [json.loads(l) for l in (
            ROOT / "data" / "open" / "bench132"
            / "fable_edit132_4hop.jsonl").read_text(
                encoding="utf-8").splitlines() if l.strip()]
        item = [x for x in item if x["id"] == "bench132-4hop-152"][0]
        work = Path(tempfile.mkdtemp(prefix="p150d_b152_"))
        cfg = copy.deepcopy(cfg0)
        row = B.run_item(item, work / "b152", cfg)
        out["T2-bench152"] = {
            "replies": [str(row.get("reply", ""))],
            "stored": [],
            "verdict": row["verdict"],
            "exact": bool(row.get("exact", False)),
            "expected": row.get("expected", ""),
        }
    (ART / f"probe150d-{arm}.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def judge(a150d: dict, a138b: dict) -> tuple[int, list[str]]:
    cases = {c["id"]: c for c in json.loads(
        (ART / "cases150d.json").read_text(encoding="utf-8"))["cases"]}
    fails, notes = 0, []
    t_ok = h_ok = o_ok = 0
    for cid, case in cases.items():
        r15, r13 = a150d[cid], a138b[cid]
        grp = case["group"]
        if grp == "title-single":
            exp = case["expect150d"]["stored"]
            ok15 = (r15["replies"][-1].strip().startswith("Saved:")
                    and [list(e) for e in [exp]] == [list(e) for e in r15["stored"]])
            if case["expect138b"] == "split":
                ok13 = ("split that" in r13["replies"][-1]
                        and r13["stored"] == [])
            else:  # value-side: identical save on both arms
                ok13 = (r13["replies"][-1] == r15["replies"][-1]
                        and r13["stored"] == r15["stored"]
                        and r15["stored"] != [])
            if ok15 and ok13:
                t_ok += 1
            else:
                fails += 1
                notes.append(f"{cid} title-single 150d={r15['replies'][-1][:80]!r} "
                             f"stored={r15['stored']} 138b={r13['replies'][-1][:80]!r}")
        elif grp == "title-chain":
            ok15 = case["ask_contains"] in r15["replies"][-1]
            notes.append(f"{cid} chain 150d-final={r15['replies'][-1][:100]!r} "
                         f"138b-final={r13['replies'][-1][:100]!r}")
            if ok15:
                t_ok += 1
            else:
                fails += 1
        elif grp in ("hedge", "other"):
            same = (r15["replies"] == r13["replies"]
                    and r15["stored"] == r13["stored"])
            if grp == "hedge":
                same = same and r15["stored"] == []
            if same:
                if grp == "hedge":
                    h_ok += 1
                else:
                    o_ok += 1
            else:
                fails += 1
                notes.append(f"{cid} {grp} MOVE 150d={r15['replies'][-1][:80]!r} "
                             f"stored={r15['stored']} 138b={r13['replies'][-1][:80]!r}")
        if grp == "other" and cid in ("O01", "O02", "O03"):
            if case["twin_ask_contains"] not in r15["replies"][-1]:
                fails += 1
                notes.append(f"{cid} twin broken: {r15['replies'][-1][:100]!r}")
    # T2
    t2 = a150d.get("T2-bench152", {})
    t2ok = t2.get("verdict") == "correct"
    notes.append(f"T2-bench152 verdict={t2.get('verdict')} "
                 f"exact={t2.get('exact')} reply={str(t2.get('replies', [''])[0])[:110]!r}")
    if not t2ok:
        fails += 1
    print(f"T1: title {t_ok}/16 hedge {h_ok}/16 other {o_ok}/12 "
          f"T2-bench152 {'correct' if t2ok else 'NOT-CORRECT'} fails={fails}",
          flush=True)
    return fails, notes


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Exp 150d T1/T2 probe")
    ap.add_argument("--arm", default=None, choices=("loop150d", "loop138b"))
    args = ap.parse_args(argv)
    if args.arm is not None:
        ART.mkdir(parents=True, exist_ok=True)
        run_arm(args.arm)
        print(f"arm {args.arm} done", flush=True)
        return 0
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    env = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
           "PATH": __import__("os").environ["PATH"]}
    base = ["uv", "run", "--offline", "--no-project", "--python", "3.12",
            "--with", "torch", "--with", "numpy", "python", "-B",
            "scripts/fable_fix150d_probe.py", "--arm"]
    for arm in ("loop150d", "loop138b"):
        p = subprocess.run(base + [arm], capture_output=True, text=True,
                           timeout=1500, env=env)
        print(f"--- arm {arm} rc={p.returncode} ---", flush=True)
        print((p.stdout or "")[-1500:], flush=True)
        if p.returncode != 0:
            print((p.stderr or "")[-3000:], flush=True)
            return 2
    a150d = json.loads((ART / "probe150d-loop150d.json").read_text(
        encoding="utf-8"))
    a138b = json.loads((ART / "probe150d-loop138b.json").read_text(
        encoding="utf-8"))
    fails, notes = judge(a150d, a138b)
    for n in notes:
        print(f"  {n}", flush=True)
    rep = {"seconds": round(time.time() - t0, 1), "fails": fails,
           "notes": notes}
    (ART / "probe150d-summary.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"T1/T2 {rep['seconds']}s fails={fails}", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
