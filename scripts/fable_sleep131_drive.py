#!/usr/bin/env python3
"""Experiment 131 driver -- registered wave T1..T5 (additive only).

Reuses scripts/fable_sleep116_drive.py BY IMPORT plus a daemon class
swap (D104.PY pointed at scripts/fable_sleep131_agent.py); neither
sealed file is modified. Three sub-runs, each with its own report under
artifacts/fable-sleep131-20260922/:

  e116 : full exp-116 redteam wave through Sleep131Daemon
         (T1 = E1-E4 taughtwin run; T2 = the other 33 verdict keys vs
         artifacts/fable-sleep116-20260922/wave-report-rescored.json).
  z104 : full exp-104 wave (seeds 1-3 + Z4 + Z5 noise4/noise8) through
         the daemon class swap into the 131 artifact dir (T3).
  t4   : NEW case teach-after-sleep (T4): clean chains taught, sleep
         installs, THEN "T01's maternal grandmother is Z01." is taught;
         probe T01 must answer Z01 with source taught (0 overwrites)
         while untaught control T02 still answers derived H02
         sleep-derived.

Usage (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep131_drive.py --only e116
  (--only selects a comma-separated subset of: e116,z104,t4; default: all)

Nothing outside this file and artifacts/fable-sleep131-20260922/ is
written. The driver never calls sleep and never touches a notebook
except read-only (notebook opens are reads of daemon-owned dirs).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_sleep104_drive as D104  # noqa: E402 (mailbox helpers, read-only)
import fable_sleep116_drive as D116  # noqa: E402 (redteam logic, read-only)

# THE daemon class swap: every spawn in D104/D116 boots Sleep131Daemon.
D104.PY = [sys.executable, "-B", str(SCRIPTS / "fable_sleep131_agent.py")]

ART131 = SCRIPTS.parent / "artifacts" / "fable-sleep131-20260922"


# ------------------------------------------------------------ sub-run: e116
def run_e116() -> int:
    return D116.main(["--root", str(ART131 / "runs-116"),
                      "--report", str(ART131 / "wave-report-116.json")])


# ------------------------------------------------------------ sub-run: z104
def run_z104() -> int:
    return D104.main(["--root", str(ART131 / "runs-104"),
                      "--report", str(ART131 / "wave-report-104.json")])


# -------------------------------------------------------------- sub-run: t4
def b_teachafter() -> list[str]:
    pre = []
    for i in range(1, 9):
        k, m, g = f"K{i:02d}", f"M{i:02d}", f"G{i:02d}"
        pre.append(f"{k}'s mother is {m}.")
        pre.append(f"{m}'s mother is {g}.")
    for i in range(1, 5):
        t, n, h = f"T{i:02d}", f"N{i:02d}", f"H{i:02d}"
        pre.append(f"{t}'s mother is {n}.")
        pre.append(f"{n}'s mother is {h}.")
    for i in range(1, 9):
        pre.append(f"Who is K{i:02d}'s maternal grandmother?")
    pre.extend(["Hi, how are you?", "Thanks, that helps."])
    return pre


def run_t4() -> int:
    root = ART131 / "runs-t4"
    root.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out: dict = {}
    pre = b_teachafter()
    r = D116.drive_run(root, "teachafter", 31, pre)
    d, proc, replies = r["dir"], r["proc"], r["replies"]
    # AFTER the sleep installed: teach the gran fact, then probe + control.
    teach = D116.ask(d, replies, "s01",
                     "T01's maternal grandmother is Z01.")
    p_taught = D116.ask(d, replies, "p01",
                        "Who is T01's maternal grandmother?")
    p_ctrl = D116.ask(d, replies, "p02",
                      "Who is T02's maternal grandmother?")
    si = D116.sleep_info(d)
    log = si["log"]
    D116.finish(d, proc)
    nb = C.Notebook(d / "notebook")
    rec_t = D116.get_record(log, "p01")
    rec_c = D116.get_record(log, "p02")
    src_t = rec_t.get("fields", {}).get("source", "")
    src_c = rec_c.get("fields", {}).get("source", "")
    stored = D116.taught_pair_ok(nb, "T01", "maternal_grandmother", "Z01")
    ow = D104.sleep_overwrites(nb)
    out.update({
        "installed": si["installed"], "attempted": si["attempted"],
        "episodes": si["episodes"], "oof": si["oof"], "agree": si["agree"],
        "teach_reply": teach.strip()[:120], "stored_taught": stored,
        "probe_taught": p_taught.strip()[:120], "probe_taught_source": src_t,
        "probe_control": p_ctrl.strip()[:120],
        "probe_control_source": src_c, "overwrite": ow,
    })
    ta_ok = bool(si["installed"] and stored and D116.has(p_taught, "Z01")
                 and not D116.has(p_taught, "H01") and src_t == "taught"
                 and ow == 0)
    tb_ok = bool(si["installed"] and D116.has(p_ctrl, "H02")
                 and src_c == "sleep-derived")
    out["TA_taught_wins"] = "PASS" if ta_ok else "FAIL"
    out["TB_control_derived"] = "PASS" if tb_ok else "FAIL"
    out["T4"] = "PASS" if (ta_ok and tb_ok) else "FAIL"
    out["wave_seconds"] = round(time.time() - t0, 1)
    (ART131 / "t4.json").write_text(json.dumps(out, indent=1, sort_keys=True),
                                    encoding="utf-8")
    print(f"TA {out['TA_taught_wins']} -- taught={p_taught.strip()[:80]} "
          f"src={src_t} stored={int(stored)} ow={ow}", flush=True)
    print(f"TB {out['TB_control_derived']} -- control={p_ctrl.strip()[:80]} "
          f"src={src_c}", flush=True)
    print(f"T4 {out['T4']} {out['wave_seconds']}s -> {ART131 / 't4.json'}",
          flush=True)
    return 0 if out["T4"] == "PASS" else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 131 registered wave")
    ap.add_argument("--only", default="e116,z104,t4")
    args = ap.parse_args(argv)
    want = set(c.strip() for c in args.only.split(",") if c.strip())
    rc = 0
    if "e116" in want:
        rc |= run_e116()
    if "z104" in want:
        rc |= run_z104()
    if "t4" in want:
        rc |= run_t4()
    return rc


if __name__ == "__main__":
    sys.exit(main())
