#!/usr/bin/env python3
"""Experiment 160c -- G3 redteam136 + redteam143 through loop160c vs loop160b.

Follows the base-folder patterns (scripts/fable_fix150_redteam136.py for 136:
fresh daemon dir per case, mailbox process_file, triples via
notebook_triples, verdicts vs sealed cases; scripts/fable_loop138b_redteam143
.py for 143: sealed cases + judge from scripts/fable_redteam143_run.py by
import with the daemon factory swapped per arm). Both arms (loop160c under
test, loop160b base) run live in this script; per-case verdicts are diffed
160c vs 160b. ZERO moves predicted (pre-seal scan: parse_bare_correction
fires on 0 of 145 cases136 strings and 0 of 124 redteam143 case strings, so
no turn is ever a bare correction and the 160c branch is unreachable; see
PASSMARKS.md). 0 new WRONG/WRONG-WRITE. Outputs go into
artifacts/fable-twohop160c-20260922/ only.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix160c_redteam.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_common as C129  # noqa: E402 (mailbox driver, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop160b_agent as L160b  # noqa: E402 (base arm, read-only)
import fable_loop160c_agent as L160c  # noqa: E402 (this experiment)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)

ROOT = SCRIPTS.parent
ART160C = ROOT / "artifacts" / "fable-twohop160c-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"


def run_case136(row: dict, workroot: Path, daemon_cls,
                base_cfg: dict) -> dict:
    root = Path(tempfile.mkdtemp(prefix=row["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        cfg = copy.deepcopy(base_cfg)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = daemon_cls(root, cfg=cfg, idle_seconds=3600.0)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"], "text": row["text"],
                "expect": row["expect"], "stored": [],
                "reply": f"BOOT-FAILED {type(exc).__name__}: {exc}",
                "verdict": "HARNESS-ERROR", "seconds": round(time.time() - t0, 3)}
    (root / "inbox" / "msg_00.txt").write_text(row["text"], encoding="utf-8")
    log: list = []
    try:
        C129.process_pending(daemon, root, log)
        stored = [list(t) for t in L90.notebook_triples(daemon.loop.nb)]
        reply = log[-1]["reply"] if log else "NO-LOG"
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"], "text": row["text"],
                "expect": row["expect"], "stored": [],
                "reply": f"HARNESS-CAUGHT {type(exc).__name__}: {exc}",
                "verdict": "HARNESS-ERROR", "seconds": round(time.time() - t0, 3)}
    exp = row["expect"]
    if exp == "nowrite":
        verdict = "OK" if not stored else "WRONG-WRITE"
    else:
        want = [list(exp)]
        if stored == want:
            verdict = "OK"
        elif not stored:
            verdict = "MISSED"
        else:
            verdict = "WRONG-WRITE"
    return {"id": row["id"], "group": row["group"], "text": row["text"],
            "expect": exp, "stored": stored, "reply": reply,
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def run_arm143(tag: str, daemon_cls, base_cfg: dict) -> list[dict]:
    R143.Loop132Daemon = daemon_cls  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(base_cfg)  # type: ignore[method-assign]
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART160C / f"scratch143-{tag}"
    rows: list[dict] = []
    for case in suite["cases"]:
        rows.append(R143.run_case(case, scratch / case["id"], markers))
    return rows


def main() -> int:
    t0 = time.time()
    ART160C.mkdir(parents=True, exist_ok=True)

    cfg160c = copy.deepcopy(L160c.DEFAULT_CONFIG160C)
    cfg160b = copy.deepcopy(L160b.DEFAULT_CONFIG160B)

    cases136 = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    workroot = ART160C / "redteam136-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    out136c = [run_case136(r, workroot, L160c.Loop160cDaemon, cfg160c)
               for r in cases136]
    out136b = [run_case136(r, workroot, L160b.Loop160bDaemon, cfg160b)
               for r in cases136]
    b136 = {r["id"]: r for r in out136b}
    moves136 = [{"id": r["id"], "loop160b": b136[r["id"]]["verdict"],
                 "loop160c": r["verdict"],
                 "reply160b": str(b136[r["id"]].get("reply", ""))[:120],
                 "reply160c": str(r.get("reply", ""))[:120]}
                for r in out136c if b136[r["id"]]["verdict"] != r["verdict"]]
    new_wrong136 = sum(
        1 for r in out136c
        if r["verdict"] in ("WRONG-WRITE", "WRONG")
        and b136[r["id"]]["verdict"] not in ("WRONG-WRITE", "WRONG"))
    (ART160C / "redteam136-loop160c.json").write_text(
        json.dumps({"counts160c": dict(Counter(r["verdict"] for r in out136c)),
                    "counts160b": dict(Counter(r["verdict"] for r in out136b)),
                    "moves_vs_loop160b": moves136,
                    "new_wrong_vs_loop160b": new_wrong136,
                    "cases": out136c}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"136: n={len(out136c)} 160c={Counter(r['verdict'] for r in out136c)} "
          f"moves={len(moves136)} new_wrong={new_wrong136}", flush=True)

    cfg160c["sleep_threshold"] = 100000
    cfg160b["sleep_threshold"] = 100000
    rows143c = run_arm143("loop160c", L160c.Loop160cDaemon, cfg160c)
    rows143b = run_arm143("loop160b", L160b.Loop160bDaemon, cfg160b)
    b143 = {r["id"]: r for r in rows143b}
    moves143, new_wrong143 = [], 0
    for r in rows143c:
        b = b143.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves143.append({"id": r["id"], "family": r.get("family"),
                             "loop160b": b["verdict"],
                             "loop160c": r["verdict"]})
            if r["verdict"] == "WRONG-ANSWER" \
                    and b["verdict"] != "WRONG-ANSWER":
                new_wrong143 += 1
    (ART160C / "redteam143-loop160c.json").write_text(
        json.dumps({"counts160c": dict(Counter(r["verdict"] for r in rows143c)),
                    "counts160b": dict(Counter(r["verdict"] for r in rows143b)),
                    "moves_vs_loop160b": moves143,
                    "new_wrong_vs_loop160b": new_wrong143,
                    "rows": rows143c}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"143: n={len(rows143c)} "
          f"160c={dict(Counter(r['verdict'] for r in rows143c))} "
          f"moves={len(moves143)} new_wrong={new_wrong143}", flush=True)

    import shutil
    shutil.rmtree(workroot, ignore_errors=True)
    total = round(time.time() - t0, 1)
    print(f"TOTAL seconds={total}")
    ok = (not moves136 and not moves143 and new_wrong136 == 0
          and new_wrong143 == 0)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
