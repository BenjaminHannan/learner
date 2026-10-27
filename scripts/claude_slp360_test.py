#!/usr/bin/env python3
"""slp-360 card test: scrap layer vs the plain 0.1 base loop (marks: artifacts/claude-slp360-20260925/PASSMARKS.md).

Run from a tree made of `git archive origin/builder-outbox` overlaid with `git archive origin/main`
(the 292t builder lives on builder-outbox):
  python3 -B scripts/claude_slp360_test.py --out artifacts/claude-slp360-20260925/results.json
CPU only; no models are loaded (the 292t rule stages answer these turns).
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
import fable_sleep104_drive as D104  # noqa: E402
import claude_slp360_scrap as S360  # noqa: E402

BROKEN_Q = "Who is Q99's maternal grandmother?"


def build(state_dir: str, seed: int, arm: str):
    import claude_loop292t_agent as T292
    cfg = copy.deepcopy(T292.DEFAULT_CONFIG292T)
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    for key in ("sleep145_seed", "sleep130_seed", "sleep131_seed", "sleep115_seed", "sleep104_seed"):
        cfg[key] = seed
    loop = T292.build_agent292t(cfg)
    if arm == "P":
        S360.install_scrap360(loop)
    return loop


def force_sleep(loop) -> None:          # the 336 harness's end_day (claude_e2e336_run.py:93-106)
    old = loop.sleep_threshold
    loop.sleep_threshold = 0
    try:
        loop.step()
    finally:
        loop.sleep_threshold = old
        loop._save()


def inner_nb(loop):
    return getattr(loop.nb, "nb", loop.nb)


def kinds(loop) -> Counter:
    return Counter(e.get("kind") for e in inner_nb(loop).events)


def say(loop, text: str) -> str:
    return " ".join(loop.turn(text))


def probe_block(loop, probes) -> list[dict]:
    out = []
    for t in probes:
        r = say(loop, t["text"])
        out.append({"text": t["text"], "reply": r, "verdict": D104.classify(r, t["expect"])})
    r = say(loop, BROKEN_Q)
    out.append({"text": BROKEN_Q, "reply": r, "verdict": D104.classify(r, "Q99zzz-never-a-name")})
    return out


def word_installed(state_dir: str) -> bool:
    for p in Path(state_dir).glob("sleep145*words*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if "maternal_grandmother" in (data.get("words") or {}):
            return True
    return False


def run_arm(seed: int, arm: str, root: Path) -> dict:
    d = root / f"{arm}-s{seed}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    t0 = time.time()
    loop = build(str(d), seed, arm)
    turns, truth = D104.build_turns()
    body = [t for t in turns if t["kind"] != "probe"]
    probes = [t for t in turns if t["kind"] == "probe"]
    replies = [{"text": t["text"], "reply": say(loop, t["text"])} for t in body]
    before = kinds(loop)
    ev_before = len(inner_nb(loop).events)
    force_sleep(loop)
    ev_sleep = len(inner_nb(loop).events) - ev_before
    after = kinds(loop)
    p1 = probe_block(loop, probes)
    derived1 = S360.main_derived_rows(inner_nb(loop))
    good, dupes = D104.taught_ok(inner_nb(loop), truth)
    scrap = getattr(loop, "scrap360", None)
    scrap_derived = sum(1 for r in (scrap.rows if scrap else [])
                        if r.get("kind") == "FACT" and r.get("source") == "sleep-derived")
    del loop
    loop2 = build(str(d), seed, arm)                 # restart from the same state dir
    p2 = probe_block(loop2, probes)
    derived2 = S360.main_derived_rows(inner_nb(loop2))
    return {"arm": arm, "seed": seed, "seconds": round(time.time() - t0, 1),
            "replies": replies, "probes_after_sleep": p1, "probes_after_restart": p2,
            "main_events_written_during_sleep": ev_sleep,
            "main_event_kinds_added_by_sleep": dict(after - before),
            "main_derived_rows_after_sleep": derived1, "main_derived_rows_after_restart": derived2,
            "installed": word_installed(str(d)), "taught_good": good, "taught_total": len(truth),
            "taught_dupes": dupes, "scrap_sleep_derived_rows": scrap_derived,
            "scrap_rows": len(scrap.rows) if scrap else 0}


def unit_inferred(root: Path) -> dict:
    d = root / "unit-inferred"
    if d.exists():
        shutil.rmtree(d)
    loop = build(str(d), 1, "P")
    say(loop, "Tova's mother is Ursa.")
    nb = inner_nb(loop)
    tova = nb.resolve("Tova").detail["entity_id"]
    ursa = nb.resolve("Ursa").detail["entity_id"]
    n0 = len(nb.events)
    res = loop.nb.assert_fact("unit360-inf", "thinking", "inferred", ursa, "child",
                              {"entity": tova}, rule_id="R-unit", deps=("F00001",))
    return {"status": res.status, "main_events_added": len(nb.events) - n0,
            "in_scrap": any(r.get("event_id") == "unit360-inf" for r in loop.scrap360.rows),
            "main_derived_rows": S360.main_derived_rows(nb)}


def score(res: dict) -> dict:
    marks = {}
    for seed in (1, 2):
        P, T = res[f"P-s{seed}"], res[f"T-s{seed}"]
        pr = [x["verdict"] for x in P["probes_after_sleep"][:5]]
        tr = [x["verdict"] for x in T["probes_after_sleep"][:5]]
        pr2 = [x["verdict"] for x in P["probes_after_restart"][:5]]
        same = sum(a["reply"] == b["reply"] for a, b in zip(P["replies"], T["replies"]))
        same += sum(a["reply"] == b["reply"] for a, b in zip(P["probes_after_sleep"], T["probes_after_sleep"]))
        same += sum(a["reply"] == b["reply"] for a, b in zip(P["probes_after_restart"], T["probes_after_restart"]))
        total = len(P["replies"]) + len(P["probes_after_sleep"]) + len(P["probes_after_restart"])
        marks[f"s{seed}"] = {
            "P360.1": P["main_derived_rows_after_sleep"] == 0 and P["main_derived_rows_after_restart"] == 0,
            "P360.2": P["main_events_written_during_sleep"] == 0,
            "P360.3": P["installed"] and pr.count("correct") == tr.count("correct") and pr.count("correct") >= 4,
            "P360.4": pr.count("wrong") == 0 and pr2.count("wrong") == 0
                      and P["probes_after_sleep"][5]["verdict"] != "wrong"
                      and P["probes_after_restart"][5]["verdict"] != "wrong",
            "P360.5": same == total,
            "P360.6": P["taught_good"] == P["taught_total"] == 40,
            "P360.7": P["scrap_sleep_derived_rows"] >= 1,
            "detail": {"identical": f"{same}/{total}", "P_probes": pr, "P_probes_restart": pr2,
                       "T_probes": tr, "T_main_derived_rows": T["main_derived_rows_after_sleep"],
                       "T_main_events_during_sleep": T["main_events_written_during_sleep"],
                       "T_installed": T["installed"]}}
    u = res["unit"]
    marks["P360.8"] = u["in_scrap"] and u["main_events_added"] == 0 and u["main_derived_rows"] == 0
    return marks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    root = Path(tempfile.mkdtemp(prefix="slp360-"))
    res = {}
    for seed in (1, 2):
        for arm in ("T", "P"):
            res[f"{arm}-s{seed}"] = run_arm(seed, arm, root)
            print(arm, seed, res[f"{arm}-s{seed}"]["seconds"], "s", flush=True)
    res["unit"] = unit_inferred(root)
    res["marks"] = score(res)
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res["marks"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
