#!/usr/bin/env python3
"""dir-h6 ADDENDUM-1 (helper H10, Claude, 2026-09-28, written between 21:04 and 21:10 UTC (`date -u`)): the report-only mid-night curve.

Plan and reading rule: artifacts/claude-dir-h6-sleeplen-20260928/ADDENDUM-1.md. This file changes NO existing file. It imports the
sealed scripts/claude_dir_h6_sleeplen.py (which imports the sealed slp-358n3 night code), patches two module-level names for
the length of one run, and puts them back afterwards:

  N3.train_step  called once per night step; the hook counts the steps of the arm that is training and, at each milestone, scores
  N3.night       the hook says which arm, which day and which day items the night is using, then calls the sealed night()

At every milestone (steps 300, 1,000, 2,000, 6,000 of the arms that have that many steps: L and B; S only at its own 300) it
scores the arm's net on two sets with the sealed judge (the same 48-round, v2 stop rule scorer as the morning tests):
  fresh  the sealed day_grids TEST (400 fresh puzzles the night never sees), the same set the morning marks use
  own    the night's own grid puzzles of that day (the ones half of the night's day batches are drawn from; about 300)
Nothing the run computes for the marks is changed: scoring runs under no_grad, in eval mode, and the torch (and CUDA) random state
is saved and put back around every scoring call, so the training batches, round draws and weights are the ones of an unhooked run.
`smoke` checks that on a tiny CPU run: every morning / day / lost number of the hooked run equals an unhooked run.

WRITTEN ON A BOX WITH NO TORCH: py_compile only, plus a stub-module logic check of the hook (not shipped). Nothing here has run
with torch. The first run is `smoke`; if it fails, stop and report the traceback (do not patch).

  python -B scripts/claude_dir_h6_sleeplen_add1.py run --ckpt ck/s13/final.pt --seed 13 --sizes W/sizes.json --out W/s13 [--save-final]
  python -B scripts/claude_dir_h6_sleeplen_add1.py smoke

`run` takes the same flags as claude_dir_h6_sleeplen.py and writes the same dirh6-seed{S}.json, plus dirh6-curve-seed{S}.json
(rewritten after every night, so an interrupted run still leaves the nights it finished). A scoring failure is written into the
curve file ("errors") and the night goes on. --save-final (off by default; the sealed script saves no weights) also writes
S-final.pt, L-final.pt and B-final.pt (about 26 MB each: 6,438,302 weights) so a later few-example test can start from the slept nets. The curve is read by
scripts/claude_dir_h6_curve_read.py.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
import tempfile
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_dir_h6_sleeplen as H6  # noqa: E402  (sealed; imported, never edited)

N3 = H6.N3
MILESTONES = (300, 1000, 2000, 6000)
MILESTONES_TINY = (2, 4, 6, 8)                 # for the tiny smoke config (night_steps 6, long_steps 8)
STATE = {}                                     # what the hooks share for the run in progress
CTX = {}                                       # the night in progress (empty between nights)


def marks_for(cfg, arm):
    base = MILESTONES if cfg["long_steps"] >= 6000 else MILESTONES_TINY
    return sorted({m for m in base if m <= arm.steps} | {arm.steps})


def judge_quiet(net, items, device, bs):
    """the sealed judge, with the torch random state put back afterwards (judge itself draws nothing; this is a guard)"""
    cpu = torch.get_rng_state()
    cuda = torch.cuda.get_rng_state_all() if device == "cuda" else None
    t0 = time.time()
    try:
        return N3.judge(net, items, device, bs)[1]
    finally:
        torch.set_rng_state(cpu)
        if cuda is not None:
            torch.cuda.set_rng_state_all(cuda)
        STATE["score_seconds"] += time.time() - t0
        STATE["judged_items"] += len(items)


def record(c):
    step = c["step"]
    try:
        row = {"fresh": judge_quiet(c["net"], STATE["fresh"], c["device"], c["bs"]),
               "own": judge_quiet(c["net"], c["own"], c["device"], c["bs"])}
    except Exception as e:      # report only: a scoring failure must never kill a night that the marks depend on
        c["out"].setdefault("errors", []).append(f"step {step}: {type(e).__name__}: {e}")
        print("curve ERROR", c["day"], c["arm"], step, type(e).__name__, e, flush=True)
        return
    c["out"]["steps"][str(step)] = row
    print("curve", c["day"], c["arm"], step, "fresh", row["fresh"]["right"], "of", row["fresh"]["n"],
          "own", row["own"]["right"], "of", row["own"]["n"], flush=True)


def train_step_hooked(net, opt, items, rr, device):
    STATE["train_step"](net, opt, items, rr, device)
    if CTX and net is CTX["net"]:
        CTX["step"] += 1
        if CTX["step"] in CTX["marks"]:
            record(CTX)


def night_hooked(arm, day, items, seed, cfg, device, **kw):
    if arm.name == "N":                                   # no night, nothing to score mid-night
        return STATE["night"](arm, day, items, seed, cfg, device, **kw)
    own = [i for i in items if i.env == "grids"]
    slot = STATE["curve"].setdefault(str(day), {})
    slot[arm.name] = {"night_steps": arm.steps, "lr": arm.lr, "own_n": len(own), "fresh_n": len(STATE["fresh"]), "steps": {}}
    CTX.update(net=arm.net, step=0, arm=arm.name, day=day, own=own, device=device, bs=cfg["eval_bs"],
               marks=marks_for(cfg, arm), out=slot[arm.name])
    s0 = STATE["score_seconds"]
    try:
        res = STATE["night"](arm, day, items, seed, cfg, device, **kw)
    finally:
        slot[arm.name]["score_minutes"] = round((STATE["score_seconds"] - s0) / 60, 3)   # the sealed night_minutes include this
        CTX.clear()
        write_curve()
    if STATE["save"] and day == cfg["days"]:      # opt in (--save-final): the morning net after the last night, for a later few-example test
        torch.save({"arm": "loop", "seed": seed, "state": arm.net.state_dict(), "night_arm": arm.name, "after_night": day},
                   Path(STATE["out"]) / f"{arm.name}-final.pt")
    return res


def write_curve():
    out = Path(STATE["out"])
    tmp = out / "dirh6-curve-seed{}.json.tmp".format(STATE["seed"])
    tmp.write_text(json.dumps({"seed": STATE["seed"], "milestones": list(MILESTONES if STATE["real"] else MILESTONES_TINY),
                               "fresh": "the sealed day_grids test (never trained on)", "own": "the night's own grid puzzles of that day",
                               "judged_items": STATE["judged_items"], "score_minutes": round(STATE["score_seconds"] / 60, 2),
                               "torch": torch.__version__, "curve": STATE["curve"]}, indent=1), encoding="utf-8")
    tmp.replace(out / "dirh6-curve-seed{}.json".format(STATE["seed"]))


@contextlib.contextmanager
def hooks(a, cfg):
    sizes = json.loads(Path(a.sizes).read_text())["sizes"]
    STATE.update(train_step=N3.train_step, night=N3.night, out=Path(a.out), seed=a.seed, real=cfg["long_steps"] >= 6000,
                 save=bool(getattr(a, "save_final", False)),
                 fresh=N3.make_tests(sizes, cfg)["day_grids"], curve={}, judged_items=0, score_seconds=0.0)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    N3.train_step, N3.night = train_step_hooked, night_hooked
    try:
        yield STATE
    finally:
        N3.train_step, N3.night = STATE["train_step"], STATE["night"]
        CTX.clear()


def run(a, cfg=N3.CFG):
    with hooks(a, cfg):
        H6.run(a, cfg)
        write_curve()


def smoke(_):
    """a tiny CPU run twice, hooks off then hooks on: identical numbers, and the curve has the milestones it should"""
    torch.set_num_threads(1)
    tmp = Path(tempfile.mkdtemp())
    torch.manual_seed(0)
    torch.save({"arm": "loop", "seed": 0, "state": H6.R.Net("loop").state_dict()}, tmp / "c.pt")
    (tmp / "sizes.json").write_text(json.dumps({"sizes": {"sums": 6, "grids": 6}}), encoding="utf-8")
    cfg = N3.TINY
    ns = lambda name, save=False: argparse.Namespace(ckpt=tmp / "c.pt", seed=13, sizes=tmp / "sizes.json", out=tmp / name, device="cpu",
                                                     save_final=save)
    H6.run(ns("off"), cfg)
    assert N3.train_step is not train_step_hooked and N3.night is not night_hooked
    run(ns("on", save=True), cfg)
    assert N3.train_step is not train_step_hooked and N3.night is not night_hooked, "hooks were not put back"
    off = json.loads((tmp / "off/dirh6-seed13.json").read_text())
    on = json.loads((tmp / "on/dirh6-seed13.json").read_text())
    for part in ("morning", "day", "lost", "arm_steps", "arm_lr", "plan_identical_L_B", "plan_first300_identical_S_L"):
        assert off[part] == on[part], f"hooked run differs from unhooked run in {part}"
    cv = json.loads((tmp / "on/dirh6-curve-seed13.json").read_text())
    assert cv["seed"] == 13 and set(cv["curve"]) == {"1"} and set(cv["curve"]["1"]) == {"S", "L", "B"}, cv["curve"].keys()
    want = {"S": ["2", "4", "6"], "L": ["2", "4", "6", "8"], "B": ["2", "4", "6", "8"]}
    for arm, w in want.items():
        got = cv["curve"]["1"][arm]
        assert sorted(got["steps"], key=int) == w, (arm, sorted(got["steps"]))
        last = got["steps"][w[-1]]["fresh"]
        m = on["morning"]["1"][arm]["day_grids"]
        assert last["right"] == m["right"] and last["n"] == m["n"], (arm, last, m)     # the curve's end is the morning's score
        assert got["own_n"] == on["day"]["1"][arm]["grids"]["n"], arm
        assert "errors" not in got, got["errors"]
        f = torch.load(tmp / f"on/{arm}-final.pt", map_location="cpu")                    # --save-final: S, L, B (N is the input checkpoint)
        assert f["night_arm"] == arm and set(f["state"]) == set(H6.R.Net("loop").state_dict()), arm
    assert not (tmp / "off/S-final.pt").exists() and not (tmp / "on/N-final.pt").exists()
    assert cv["judged_items"] > 0
    print("smoke ok", tmp)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--ckpt", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--sizes", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--device", default="")
    p.add_argument("--save-final", action="store_true", help="also save S-, L- and B-final.pt (the net after the last night) in --out")
    sub.add_parser("smoke")
    a = ap.parse_args()
    {"run": run, "smoke": smoke}[a.cmd](a)


if __name__ == "__main__":
    main()
