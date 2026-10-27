#!/usr/bin/env python3
"""slp-361 card test: undo a whole sleep (marks: artifacts/claude-slp361-20260925/PASSMARKS.md).

Run from the combined tree (builder-outbox + main; see claude_slp360_test.py):
  python3 -B scripts/claude_slp361_test.py --out artifacts/claude-slp361-20260925/results.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_sleep104_drive as D104  # noqa: E402
import claude_slp360_scrap as S360  # noqa: E402
import claude_slp360_test as X360  # noqa: E402
import claude_slp361_undo as U361  # noqa: E402

SKIP_CMP = {"state.json"}


def build(d: str, seed: int, arm: str, judge=None):
    loop = X360.build(d, seed, "P")                  # every arm has 360
    if arm in ("A", "R", "R2"):
        U361.install_undo361(loop, judge=judge)
    return loop


def digests(d: Path) -> dict:
    out = {}
    for p in sorted(d.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(d))
        if rel.split("/")[0] == U361.UNDO_DIR361:
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def run_arm(seed: int, arm: str, root: Path) -> dict:
    d = root / f"{arm}-s{seed}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    t0 = time.time()
    reject = (lambda loop, ev: False)
    judge = {"A": None, "R": reject, "R2": reject}.get(arm)
    loop = build(str(d), seed, arm, judge)
    turns, _ = D104.build_turns()
    body = [t for t in turns if t["kind"] != "probe"]
    probes = [t for t in turns if t["kind"] == "probe"]
    replies = [{"text": t["text"], "reply": X360.say(loop, t["text"])} for t in body]
    exp_before = len(loop.experience)
    files_before = digests(d)
    if arm != "N":
        X360.force_sleep(loop)
    files_after = digests(d)
    exp_after = len(loop.experience)
    undo = dict(getattr(loop, "undo361_stats", {}) or {})
    p1 = X360.probe_block(loop, probes)
    installed_first = X360.word_installed(str(d))
    extra = {}
    if arm == "R2":                                  # redo the undone night, same process (no restart)
        loop.undo361_judge = U361.accept_all
        X360.force_sleep(loop)
        extra["second_sleep_installed"] = X360.word_installed(str(d))
        extra["probes_after_second_sleep"] = X360.probe_block(loop, probes)
    del loop
    loop2 = build(str(d), seed, arm, judge)
    p2 = X360.probe_block(loop2, probes)
    out = {"arm": arm, "seed": seed, "replies": replies, "probes_after_sleep": p1,
           "probes_after_restart": p2, "experience_before": exp_before, "experience_after": exp_after,
           "files_before": files_before, "files_after": files_after, "undo": undo,
           "installed_after_first": installed_first, **extra}
    stash = d / U361.UNDO_DIR361
    out["stash_files"] = sorted(str(p.relative_to(stash)).split("/", 1)[1]
                                for p in stash.rglob("*") if p.is_file()) if stash.exists() else []
    out["seconds"] = round(time.time() - t0, 1)
    return out


def _cmp_files(a: dict, b: dict) -> list[str]:
    keys = (set(a) | set(b)) - SKIP_CMP
    return sorted(k for k in keys if a.get(k) != b.get(k))


def _replies(x: dict) -> list[str]:
    return [r["reply"] for r in x["replies"] + x["probes_after_sleep"] + x["probes_after_restart"]]


def score(res: dict) -> dict:
    marks = {}
    for seed in (1, 2):
        N, S, A, R, R2 = (res[f"{a}-s{seed}"] for a in ("N", "S", "A", "R", "R2"))
        diff = _cmp_files(R["files_before"], R["files_after"])
        nb = [k for k in set(R["files_before"]) | set(R["files_after"]) if k.startswith("notebook/")]
        created = (R["undo"].get("last") or {}).get("moved", [])
        r_probes = [p["reply"] for p in R["probes_after_sleep"] + R["probes_after_restart"]]
        n_probes = [p["reply"] for p in N["probes_after_sleep"] + N["probes_after_restart"]]
        r2p = [p["verdict"] for p in R2.get("probes_after_second_sleep", [])[:5]]
        marks[f"s{seed}"] = {
            "P361.1": diff == [],
            "P361.2": all(R["files_before"].get(k) == R["files_after"].get(k) for k in nb) and bool(nb),
            "P361.3": r_probes == n_probes and len(r_probes) == 12,
            "P361.4": R["experience_after"] == R["experience_before"] == 75,
            "P361.5": _replies(A) == _replies(S) and len(_replies(A)) == 87
                      and A["installed_after_first"] == S["installed_after_first"],
            "P361.6": sorted(created) == R["stash_files"] and len(created) > 0,
            "P361.7": bool(R2.get("second_sleep_installed")) and r2p.count("correct") >= 4,
            "detail": {"R_changed_files": diff, "R_moved": created, "R_restored":
                       (R["undo"].get("last") or {}).get("restored"),
                       "R_not_restorable": (R["undo"].get("last") or {}).get("not_restorable"),
                       "R_main_changed": (R["undo"].get("last") or {}).get("main_notebook_changed"),
                       "S_installed": S["installed_after_first"],
                       "S_probes": [p["verdict"] for p in S["probes_after_sleep"][:5]],
                       "R_probes": [p["verdict"] for p in R["probes_after_sleep"][:5]],
                       "R2_probes": r2p}}
    return marks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    root = Path(tempfile.mkdtemp(prefix="slp361-"))
    res = {}
    for seed in (1, 2):
        for arm in ("N", "S", "A", "R", "R2"):
            res[f"{arm}-s{seed}"] = run_arm(seed, arm, root)
            print(arm, seed, res[f"{arm}-s{seed}"]["seconds"], "s", flush=True)
    res["marks"] = score(res)
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res["marks"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
