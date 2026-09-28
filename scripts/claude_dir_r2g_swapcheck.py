#!/usr/bin/env python3
"""Credit check for R2g on the DEV panel (never the holdout): does the design treat a maze and its transpose alike?

Scores a checkpoint on the 300 dev 9x9 mazes and on the same 300 with rows and columns swapped (made by code: tokens, slots and
targets transposed, start and goal swapped; the checker accepts the transposed answer). Reports right counts of 300 and the gap
(original minus transposed). Judged as ADDENDUM-style wording only, never a verdict mark (PASSMARKS.md of this folder).

  python3 -B scripts/claude_dir_r2g_swapcheck.py selftest                      (needs torch; no checkpoint)
  python3 -B scripts/claude_dir_r2g_swapcheck.py score --plugin claude_dir_r2g_net --run-dir <run> [--k 1024] --out <json>
  python3 -B scripts/claude_dir_r2g_swapcheck.py score --plugin claude_fewex_net  --run-dir <loop run> ...     (the loop, if its k1024.pt exists)
  python3 -B scripts/claude_dir_r2g_swapcheck.py read --design <json> --loop <json>                             (pure python)
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HEADROOM = 20          # if the loop's own swap gap is 20 of 300 or less there is no headroom: INCONCLUSIVE


def transpose_item(it):
    import claude_rsn358a_envs as E
    tr = lambda g: [list(r) for r in zip(*g)]
    meta = dict(it.meta)
    meta["start"], meta["goal"] = tuple(reversed(tuple(it.meta["start"]))), tuple(reversed(tuple(it.meta["goal"])))
    return E.Item(it.env, it.size, tr(it.tokens), tr(it.slot), tr(it.target), meta)


def read(design, loop):
    """Wording only. Returns the sentence a PASS may carry about symmetry."""
    d = json.loads(Path(design).read_text())
    if loop is None or not Path(loop).exists():
        return f"symmetry credit not checked (no loop swap gap); design gap {d['gap']} of 300"
    l = json.loads(Path(loop).read_text())
    if l["gap"] <= HEADROOM:
        return f"symmetry credit INCONCLUSIVE (loop gap {l['gap']} of 300, no headroom); design gap {d['gap']}"
    if d["gap"] <= l["gap"] / 2:
        return f"the swap gap shrank (design {d['gap']} of 300, loop {l['gap']}): the gain can be read as symmetry"
    return f"the swap gap did not shrink to half (design {d['gap']}, loop {l['gap']}): a gain is NOT from symmetry"


def score(plugin, run_dir, k, out, threads):
    import torch
    import claude_fewex_bench as B
    import claude_fewex_data as D
    torch.set_num_threads(threads)
    B.N = importlib.import_module(plugin)
    run = json.loads((run_dir / "adapt.json").read_text())
    net = B.load_model(run_dir / f"k{k}.pt", run["arm"])
    dev = D.panels()[0]["dev"][9]
    orig = B.score(net, dev, run["fixed_depth"])
    swapped = B.score(net, [transpose_item(x) for x in dev], run["fixed_depth"])
    res = {"plugin": plugin, "run": str(run_dir), "k": k, "seed": run["seed"], "original_right": orig["right"],
           "swapped_right": swapped["right"], "n": orig["n"], "gap": orig["right"] - swapped["right"]}
    Path(out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps(res))


def selftest():
    import random
    import claude_fewex_data as D
    import claude_rsn358m_maze as M
    rng = random.Random(3)
    for s in (7, 9, 11):
        for _ in range(20):
            it = D.make_maze(rng, s)
            t = transpose_item(it)
            assert M.check_maze(it, it.target) and M.check_maze(t, t.target)
            assert D.layout_key(t) != D.layout_key(it) or all(a == b for a, b in zip(it.tokens, zip(*it.tokens)))
            assert transpose_item(t).tokens == it.tokens and tuple(transpose_item(t).meta["start"]) == tuple(it.meta["start"])
    a = rng and D.make_maze(rng, 9)
    wrong = [[M.OFF if x == M.ON else x for x in r] for r in a.target]
    assert not M.check_maze(a, wrong)
    print(json.dumps({"swapcheck_selftest": "ok", "sizes": [7, 9, 11], "mazes": 60}))


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
        sys.exit(0)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("--plugin", required=True)
    s.add_argument("--run-dir", type=Path, required=True)
    s.add_argument("--k", type=int, default=1024)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--threads", type=int, default=1)
    r = sub.add_parser("read")
    r.add_argument("--design", required=True)
    r.add_argument("--loop", default=None)
    a = p.parse_args()
    if a.cmd == "score":
        score(a.plugin, a.run_dir, a.k, a.out, a.threads)
    else:
        print(read(a.design, a.loop))
