#!/usr/bin/env python3
"""Exp 128 C3: exp-102 marks P2/P3/P4 re-run with the wrapped agent swapped in."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fable_loop102_marks as M102
import fable_loop96_agent as L96
import fable_loop96_marks as M96
import fable_perf128_index as F128

def new_fast_daemon(root: Path):
    return F128.FastLoop102Daemon(root, cfg={"sleep_threshold": 100000},
                                  idle_seconds=3600.0)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/fable-perf128-20260922/c3")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "p4-tmp").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    M102.new_daemon102 = new_fast_daemon
    L96.build_agent96 = F128.build_fast_agent102
    L96.DEFAULT_CONFIG96 = F128.DEFAULT_CONFIG128
    M96.PY96 = [sys.executable, "-B", str(SCRIPTS / "fable_perf128_daemon.py")]
    def daemon_cfg128(state_dir: Path) -> dict:
        cfg = dict(F128.DEFAULT_CONFIG128)
        cfg["state_dir"] = str(state_dir)
        cfg["sleep_threshold"] = 10 ** 9
        return cfg
    M96.daemon_cfg96 = daemon_cfg128
    p2 = M102.run_p2(out)
    p4 = M102.run_p4(out)
    p3 = {}
    ok = True
    for name in ("l1", "l2", "l3", "l4", "l5z1", "l5z2", "l6"):
        rep = M102.run_p3(out, name)
        p3[name] = {"pass": bool(rep["pass"]), "seconds": rep.get("seconds")}
        ok = ok and bool(rep["pass"])
    res = {"p2": {"ok_to_bug": p2["ok_to_bug"], "bug_to_ok": p2["bug_to_ok"],
                  "still_bug": p2["still_bug"],
                  "reply_changed_ok_ok": p2.get("reply_changed_ok_ok", []),
                  "pass": bool(p2["pass"])},
           "p4": {"false_refusals": p4["false_refusals"], "nonpass": p4["nonpass"],
                  "pass": bool(p4["pass"])},
           "p3": p3, "p3_pass": bool(ok),
           "pass": bool(p2["pass"]) and bool(p4["pass"]) and bool(ok),
           "seconds": round(time.time()-t0, 1)}
    (out / "c3-summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("C3", "PASS" if res["pass"] else "FAIL", f"({res['seconds']}s)", flush=True)
    return 0 if res["pass"] else 1

if __name__ == "__main__":
    sys.exit(main())
