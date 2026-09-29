#!/usr/bin/env python3
"""S1 plug-in selftest. Part A (no torch) runs anywhere; part B (torch, random-init nets) runs on the Mac and is
reported SKIPPED, never faked, where torch is missing. Ends with a JSON line {"selftest": "ok", ...}."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_data as D  # noqa: E402
import claude_rsn358m_maze as M  # noqa: E402
import claude_s1_d4_aug as A  # noqa: E402

POOL_SEED, POOL_N = 9292700, 16384      # claude_fewex_eq_bench.make_pool, copied so part A needs no torch


def part_a():
    panels, banned = D.panels()
    rng = random.Random(5)
    for _ in range(100):
        it = D.make_maze(rng, 9)
        for t in range(8):
            v = A.d4_item(it, t)
            assert A.unturn(v.target, t) == it.target and A.unturn(v.tokens, t) == it.tokens and A.unturn(v.slot, t) == it.slot
            assert M.check_maze(v, v.target), "turned answer must be a valid path for the turned maze"
            if t:
                assert not M.check_maze(it, v.target) or v.target == it.target   # a turned answer is not the old answer
        assert len({json.dumps(A.turn(it.tokens, t)) for t in range(8)}) == 8
    leak = {}
    for seed in (0, 1):
        r = random.Random(POOL_SEED + seed)
        seen = set()
        pool = [D.unique_maze(r, 9, banned, seen) for _ in range(POOL_N)]
        raw = views = 0
        for it in pool:
            ok = A.allowed_views(it, banned)
            assert 0 in ok
            for t in ok:
                assert D.layout_key(A.d4_item(it, t)) not in banned or t == 0
            raw += 8 - len(ok)
            views += len(ok)
        leak[str(seed)] = {"support": len(pool), "turned_views_dropped_as_panel_layouts": raw, "views_left": views}
        assert views > 7.9 * POOL_N * 0.9
    return leak


def part_b():
    try:
        import torch  # noqa: F401
    except ModuleNotFoundError:
        return "SKIPPED: torch is not installed on this box"
    import claude_fewex_bench as B
    import claude_s1_d4 as P
    B.N = P
    torch.set_num_threads(1)
    panels, banned = D.panels()
    rng = random.Random(3)
    items = [D.make_maze(rng, 9) for _ in range(32)]
    out = {}
    for arm in ("loop", "plain"):
        torch.manual_seed(1)
        net = P.Net(arm)
        before = B.score(net, panels["dev"][9][:32], 16)["right"]
        lrn = P.Learner(net, 1e-3)
        lrn.maze_batch(items)
        assert lrn.steps == B.UPDATES and sum(lrn.views) == 32
        # identical augmentation stream for a second learner (deterministic, shared by arms)
        l2 = P.Learner(P.Net(arm), 1e-3)
        l2.maze_batch(items)
        assert l2.views == lrn.views
        # vote script, view 0 alone must equal the harness scorer
        import claude_s1_d4_vote as V
        sub = panels["dev"][9][:32]
        preds = V.predictions(net, sub, 16)
        assert sum(int(B.exact(it, p)) for it, p in zip(sub, preds)) == B.score(net, sub, 16)["right"]
        out[arm] = {"steps": lrn.steps, "views": lrn.views, "score_before": before}
    return out


if __name__ == "__main__":
    a = part_a()
    b = part_b()
    print(json.dumps({"part_a_leak_guard": a, "part_b": b}, sort_keys=True))
    print(json.dumps({"selftest": "ok", "part_b": "ran" if isinstance(b, dict) else b}))
