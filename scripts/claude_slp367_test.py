#!/usr/bin/env python3
"""slp-367 card test: idle sleep vs the forced end-of-day sleep (marks: artifacts/claude-slp367-20260925/PASSMARKS.md).

A simulated daemon: user turns arrive in bursts of 5; between bursts the daemon makes one idle step
(loop.step() with an empty inbox, exactly what fable_daemon74_run.py does after idle_seconds). A fake clock
advances 60 s per idle step. Both arms have slp-360.
  IDLE    = 360 + 367: sleeps only when its pressure rule says so, on idle steps
  FORCED  = 360: the 336 harness's forced end-of-day sleep after the last turn
World: exp-104 (75 turns: 50 teaches, 20 grandmother questions, 5 fillers), then the 5 new-people probes.
  python3 -B scripts/claude_slp367_test.py --out artifacts/claude-slp367-20260925/results.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_sleep104_drive as D104  # noqa: E402
import claude_slp360_test as X  # noqa: E402
import claude_slp367_idle as I367  # noqa: E402


class Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def __call__(self) -> float:
        return self.t


def run_arm(seed: int, arm: str, root: Path) -> dict:
    d = root / f"{arm}-s{seed}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    loop = X.build(str(d), seed, "P")
    clock = Clock()
    st = I367.install_idle367(loop, clock=clock) if arm == "IDLE" else None
    sleeps_in_turn = [0]
    inner_sleep = loop._sleep_tick

    def watch():
        if st is not None and st["in_turn"]:
            sleeps_in_turn[0] += 1
        return inner_sleep()

    loop._sleep_tick = watch
    turns, _ = D104.build_turns()
    body = [t for t in turns if t["kind"] != "probe"]
    probes = [t for t in turns if t["kind"] == "probe"]
    replies, idle_log = [], []
    for i in range(0, len(body), 5):
        for t in body[i:i + 5]:
            replies.append(X.say(loop, t["text"]))
        if arm == "IDLE":
            clock.t += 60
            ev = loop.step()
            idle_log.append({"after_turn": i + 5, "mode": ev["mode"], "new_rows": len(loop.experience)})
    if arm == "FORCED":
        X.force_sleep(loop)
    else:                                   # the evening: idle steps until a sleep has run with the day's episodes
        for _ in range(3):
            clock.t += 60
            ev = loop.step()
            idle_log.append({"after_turn": len(body), "mode": ev["mode"], "new_rows": len(loop.experience)})
    p = X.probe_block(loop, probes)
    out = {"arm": arm, "seed": seed, "replies": replies, "probes": p, "idle_log": idle_log,
           "sleeps_in_turn": sleeps_in_turn[0], "installed": X.word_installed(str(d)),
           "sleeps": (st or {}).get("sleeps", 1 if arm == "FORCED" else 0)}
    # quiet-period checks (fresh loop, fake clock): < min_new rows and short idle -> no sleep; long idle -> sleep
    if arm == "IDLE":
        d2 = root / f"quiet-s{seed}"
        if d2.exists():
            shutil.rmtree(d2)
        q = X.build(str(d2), seed, "P")
        c2 = Clock()
        st2 = I367.install_idle367(q, clock=c2)
        for text in ["Vero's mother is Wynn.", "Wynn's mother is Xia.", "Hello!"]:
            X.say(q, text)
        c2.t += 60
        m1 = q.step()["mode"]
        c2.t += I367.LONG_IDLE367
        m2 = q.step()["mode"]
        out["quiet"] = {"short_idle_mode": m1, "long_idle_mode": m2, "sleeps": st2["sleeps"]}
    return out


KINDS = [t["kind"] for t in D104.build_turns()[0] if t["kind"] != "probe"]


def score(res: dict) -> dict:
    marks = {}
    for seed in (1, 2):
        I, F = res[f"IDLE-s{seed}"], res[f"FORCED-s{seed}"]
        marks[f"s{seed}"] = {
            "P367.1": I["sleeps_in_turn"] == 0,
            "P367.2": I["installed"] and [p["verdict"] for p in I["probes"][:5]].count("correct") >= 4,
            "P367.3": [r for r, k in zip(I["replies"], KINDS) if k != "episode"]
                      == [r for r, k in zip(F["replies"], KINDS) if k != "episode"],
            "P367.4": I["quiet"]["short_idle_mode"] != "SLEEP",
            "P367.5": I["quiet"]["long_idle_mode"] == "SLEEP",
            "detail": {"episode_replies_changed": sum(a != b for a, b, k in zip(I["replies"], F["replies"], KINDS)
                                                      if k == "episode"),
                       "idle_sleeps": I["sleeps"], "forced_installed": F["installed"],
                       "idle_probes": [p["verdict"] for p in I["probes"][:5]],
                       "forced_probes": [p["verdict"] for p in F["probes"][:5]],
                       "idle_modes": [x["mode"] for x in I["idle_log"]]}}
    return marks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    root = Path(tempfile.mkdtemp(prefix="slp367-"))
    res = {}
    for seed in (1, 2):
        for arm in ("IDLE", "FORCED"):
            res[f"{arm}-s{seed}"] = run_arm(seed, arm, root)
            print(arm, seed, flush=True)
    res["marks"] = score(res)
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res["marks"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
