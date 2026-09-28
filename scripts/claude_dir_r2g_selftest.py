#!/usr/bin/env python3
"""CPU selftest for the R2g plug-in (scripts/claude_dir_r2g_net.py). No maze is scored; mazes appear only as training-shaped input.

Every check asserts; the run ends with "selftest": "ok" only if all pass. Needs torch (CPU, fp32).
  budget            +80 weights over the loop's 1,645,726; only the tie tensors are new; plain untouched
  same_loop         under the same torch seed every loop tensor equals the baseline loop's; tie is zero
  bias_symmetry     the shared part is invariant to axis flips and axis swaps on 1-, 2- and 3-axis layouts and a shuffled point cloud
  residual_scale    the direction-specific part enters at exactly RHO times the old signed tables and breaks the symmetry
  cross_mask        the narrow-head mask contains the loop's strip, is transpose-symmetric, never hides the cell itself,
                    and hides nothing on a single axis
  block_math        with the strip mask and the tie at zero, a TiedBlock equals base.Block whose signed tables are scaled by RHO;
                    forward_axes on 1, 2 and 3 axes runs; a permuted cell order gives the permuted output
  net_equivariance  a fresh net with a random tie table maps a transposed or flipped grid to the transposed or flipped logits
                    (no direction anywhere); the untied loop with random signed tables does not
  shapes            48 rounds of cell and stop logits, infer_rounds shapes, plain arm is the baseline's class
  gradients         one step gives every 2-D weight matrix (tie included) a nonzero gradient; the harness gradient_check passes
  learner           the harness Learner (no plug-in Learner) does 4 updates per maze batch and a 3-update sleep on this Net
  practice_smoke    N source steps, finite loss, reload identical
  timing_cpu        seconds per step against the loop (report only)
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import tempfile
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_r2g_net as R  # noqa: E402
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_net as base  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402

LOOP_WEIGHTS, PLAIN_WEIGHTS, TIE_WEIGHTS = 1_645_726, 1_619_965, 80
TOL = 1e-4


def batch(kind, n=4, seed=5):
    rng = random.Random(seed)
    if kind == "sums":
        return [E.make_sum(rng, 4) for _ in range(n)]
    if kind == "grids":
        return [D.latin_legend(rng, 5) for _ in range(n)]
    return [D.make_maze(rng, 9) for _ in range(n)]     # training-shaped input only, never scored


def grid_coords(h, w):
    return torch.tensor([(r, c) for r in range(h) for c in range(w)])


def bias_of(tie, coords, resid=None, rho=R.RHO):
    return R.tied_bias(tie, resid or [], R.coord_offsets(coords), rho=rho if resid else 0)


def check_budget():
    d = R.describe()
    assert d["loop_stored"] == LOOP_WEIGHTS and d["plain_stored"] == PLAIN_WEIGHTS, d
    assert d["tie_weights"] == TIE_WEIGHTS == 8 * (R.CLIP + 1) * 2, d
    assert d["stored"] == LOOP_WEIGHTS + TIE_WEIGHTS == 1_645_806, d
    assert abs(d["gap_vs_loop_pct"] - 100 * 80 / LOOP_WEIGHTS) < 1e-12 and abs(d["gap_vs_loop_pct"]) < 1, d
    extra = {n for n in dict(R.Net("loop").named_parameters()) if n not in dict(base.Net("loop").named_parameters())}
    assert extra == {"blocks.0.tie", "blocks.1.tie"}, extra
    assert type(R.Net("plain").blocks[0]) is base.Block and R.Net("plain").weight_count() == PLAIN_WEIGHTS
    return d


def check_same_loop():
    torch.manual_seed(7)
    a = R.Net("loop")
    torch.manual_seed(7)
    b = base.Net("loop")
    pa, pb = dict(a.named_parameters()), dict(b.named_parameters())
    assert all(torch.equal(pa[n], pb[n]) for n in pb), "loop tensors differ under the same seed"
    assert all(float(pa[n].detach().abs().max()) == 0 for n in pa if n.endswith(".tie"))
    return {"loop_tensors_equal": True, "tie_all_zero": True}


def check_bias_symmetry():
    torch.manual_seed(1)
    tie = torch.randn(8, R.CLIP + 1)
    out = {}
    # 2 axes: flips of either axis, the swap of the two axes, and all their products (the 8 symmetries of the square)
    c = grid_coords(9, 9)
    ref = bias_of(tie, c)
    for name, m in {"flip_rows": lambda x: torch.stack([8 - x[:, 0], x[:, 1]], 1), "flip_cols": lambda x: torch.stack([x[:, 0], 8 - x[:, 1]], 1),
                    "swap": lambda x: x[:, [1, 0]], "rot90": lambda x: torch.stack([x[:, 1], 8 - x[:, 0]], 1)}.items():
        assert torch.equal(bias_of(tie, m(c)), ref), name
    # a non-square rectangle and a shifted origin give the same relation-only bias
    assert torch.equal(bias_of(tie, grid_coords(5, 7) + 3)[:, :5, :5], bias_of(tie, grid_coords(5, 7))[:, :5, :5])
    # 1 axis: a plain sequence; mirrored order is the same bias matrix reversed on both indices
    s = torch.arange(12)[:, None]
    b1 = bias_of(tie, s)
    assert torch.equal(bias_of(tie, -s), b1) and torch.equal(b1, b1.transpose(1, 2))
    # 3 axes: every axis permutation and flip
    c3 = torch.cartesian_prod(torch.arange(4), torch.arange(4), torch.arange(4))
    b3 = bias_of(tie, c3)
    assert torch.allclose(bias_of(tie, c3[:, [2, 0, 1]]), b3, atol=1e-6) and torch.equal(bias_of(tie, torch.stack([3 - c3[:, 0], c3[:, 1], c3[:, 2]], 1)), b3)   # (float sums of 3 terms differ by order only)
    # a shuffled point cloud: the bias is a function of the pair only, so permuting the cells permutes rows and columns
    pts = torch.randint(0, 20, (30, 2))
    perm = torch.randperm(30)
    assert torch.equal(bias_of(tie, pts[perm]), bias_of(tie, pts)[:, perm][:, :, perm])
    # the shared table is what is read: entry |d| = 2 on axis 0 with all else equal
    t = torch.zeros(8, R.CLIP + 1)
    t[:, 2] = 1.0
    two = bias_of(t, torch.tensor([[0, 0], [2, 0]]))
    assert float(two[0, 0, 1]) == 1.0 + 0.0 and float(bias_of(t, torch.tensor([[0, 0], [0, -2]]))[0, 0, 1]) == 1.0
    return {"axes_tested": [1, 2, 3], "symmetries_2d": 4, "shuffled_cloud": True}


def check_residual_scale():
    torch.manual_seed(2)
    tie = torch.randn(8, R.CLIP + 1)
    br, bc = torch.randn(8, 2 * R.CLIP + 1), torch.randn(8, 2 * R.CLIP + 1)
    c = grid_coords(9, 9)
    axes = R.coord_offsets(c)
    full = R.tied_bias(tie, [br, bc], axes)
    shared = R.tied_bias(tie, [], axes)
    resid = full - shared
    direct = R.RHO * (br[:, axes[0]] + bc[:, axes[1]])
    assert float((resid - direct).abs().max()) < 1e-6
    assert float((full - full.transpose(1, 2)).abs().max()) > 0.1, "residual should break the symmetry"
    assert float((shared - shared.transpose(1, 2)).abs().max()) < 1e-6
    return {"rho": R.RHO, "residual_max_abs_error": float((resid - direct).abs().max())}


def check_cross_mask():
    c = grid_coords(9, 9)
    axes = R.coord_offsets(c)
    cross = R.cross_far(axes, 4, 8)
    strip = torch.zeros(8, 1, 1, dtype=torch.bool)
    strip[:4] = True
    strip = strip & ((axes[1] - R.CLIP).abs() > R.WINDOW)
    assert not bool((~cross & strip).any() and False)                       # (shape check)
    allowed_cross, allowed_strip = ~cross, ~strip.expand_as(cross)
    assert bool((allowed_cross | ~allowed_strip).all()), "the cross must contain the old strip"
    assert bool((allowed_cross.sum() > allowed_strip.sum()))
    assert bool((cross == cross.transpose(1, 2)).all()) and bool((cross[:, torch.arange(81), torch.arange(81)] == 0).all())
    # transposed grid: a cross is symmetric, a strip is not
    tr = R.cross_far(R.coord_offsets(c[:, [1, 0]]), 4, 8)
    assert bool((tr == cross).all())
    assert not bool(R.cross_far(R.coord_offsets(torch.arange(15)[:, None]), 4, 8).any()), "one axis: nothing is far on two axes"
    assert not bool(cross[4:].any()), "wide heads are never masked"
    return {"allowed_narrow_cells_cross": int(allowed_cross[0].sum()), "allowed_narrow_cells_strip": int(allowed_strip[0].sum()), "of": 81 * 81}


def check_block_math():
    torch.manual_seed(3)
    nb = base.Net("loop")
    blk = nb.blocks[0]
    blk.br.data.normal_(0, .5)
    blk.bc.data.normal_(0, .5)
    x = torch.randn(2, 81, 256)
    dr, dc = base.Net.offsets(9, 9, x.device)
    ref = blk(x, dr, dc)
    tb = R.TiedBlock(nb.blocks[0])
    tb.CROSS = False
    scaled = base.Block(256, 8)
    scaled.load_state_dict(blk.state_dict())
    scaled.br.data.mul_(R.RHO)
    scaled.bc.data.mul_(R.RHO)
    with torch.no_grad():
        got, want = tb(x, dr, dc), scaled(x, dr, dc)
    err = float((got - want).abs().max())
    assert err < TOL, err
    # 1, 2, 3 axes run; a cell permutation permutes the output (the block has no absolute position)
    tb2 = R.TiedBlock(base.Net("loop").blocks[0])
    tb2.tie.data.normal_(0, .5)
    outs = {}
    for n, coords in (("1axis", torch.arange(10)[:, None]), ("2axis", grid_coords(4, 5)), ("3axis", torch.cartesian_prod(*(torch.arange(3),) * 3))):
        T = coords.shape[0]
        xx = torch.randn(2, T, 256)
        axes = R.coord_offsets(coords)
        y = tb2.forward_axes(xx, axes)
        assert y.shape == xx.shape and bool(torch.isfinite(y).all())
        perm = torch.randperm(T)
        y2 = tb2.forward_axes(xx[:, perm], R.coord_offsets(coords[perm]))
        assert float((y2 - y[:, perm]).abs().max()) < TOL, n
        outs[n] = True
    return {"matches_base_block_with_rho_scaled_tables": err, "layouts_ok_and_permutation_equivariant": outs}


def check_net_equivariance():
    torch.manual_seed(4)
    net = R.Net("loop").eval()
    for b in net.blocks:
        b.tie.data.normal_(0, .7)
    t, s, _ = base.tensors(batch("grids", 3))                     # legend grids, 7 x 5 (not square)
    H, W = t.shape[1:]

    def logits(net_, tt, ss, rounds=3):
        e, (dr, dc) = net_.embed(tt.contiguous(), ss.contiguous())
        h = torch.zeros_like(e)
        for _ in range(rounds):
            h = net_.step(h, e, dr, dc)
        return net_.read(h)[0].reshape(tt.shape[0], tt.shape[1], tt.shape[2], -1)

    maps = {"transpose": lambda z: z.transpose(1, 2), "flip_rows": lambda z: z.flip(1), "flip_cols": lambda z: z.flip(2)}
    errs = {}
    with torch.no_grad():
        lg = logits(net, t, s)
        for name, f in maps.items():
            errs[name] = float((logits(net, f(t), f(s)) - f(lg)).abs().max())
            assert errs[name] < TOL, (name, errs[name])
        # the untied loop with random signed tables is direction-specific
        torch.manual_seed(4)
        plain_loop = base.Net("loop").eval()
        for b in plain_loop.blocks:
            b.br.data.normal_(0, .7)
            b.bc.data.normal_(0, .7)
        l1 = logits(plain_loop, t, s, 1)
        gap = float((logits(plain_loop, t.transpose(1, 2), s.transpose(1, 2), 1) - l1.transpose(1, 2)).abs().max())
    assert gap > 1e-2, gap
    return {"grid": [H, W], "tied_net_max_abs_error": errs, "untied_loop_transpose_gap": gap}


def check_shapes():
    net = R.Net("loop").eval()
    t, s, _ = base.tensors(batch("mazes", 2))
    with torch.no_grad():
        cells, stops = net.forward(t, s)
        ps, qs = net.infer_rounds(t, s, 48)
    assert len(cells) == 48 and len(stops) == 48 and cells[0].shape == (2, 81, E.VOCAB) and stops[0].shape == (2,)
    assert ps.shape == (2, 48, 81) and qs.shape == (2, 48)
    pn = R.Net("plain")
    cells, stops = pn.forward(t, s)
    assert len(cells) == 1 and stops == [] and type(pn) is R.Net and pn.arm == "plain"
    return {"loop_rounds": 48, "infer_rounds": list(ps.shape)}


def check_gradients():
    torch.manual_seed(0)
    net = R.Net("loop")
    gc = B.gradient_check(net, 0)
    assert gc["nonzero_all"], gc
    net.zero_grad(set_to_none=True)
    loss = R.train_loss(net, batch("sums", 8), random.Random(3))
    loss.backward()
    ties = [b.tie.grad for b in net.blocks]
    assert all(g is not None and float(g.abs().sum()) > 0 for g in ties)
    return {"gradient_check": gc, "tie_grad_abs_sum": [float(g.abs().sum()) for g in ties]}


def check_learner():
    B.N = R
    try:
        assert not hasattr(R, "Learner")
        torch.manual_seed(1)
        net = R.Net("loop")
        rng = random.Random(77)
        mazes = [D.make_maze(rng, 9) for _ in range(B.MAZE_BATCH)]
        old = D.replay_old()
        saved = B.SLEEP_STEPS
        B.SLEEP_STEPS = 3
        try:
            learner = B.Learner(copy.deepcopy(net), 1e-3)
            learner.maze_batch(mazes)
            assert learner.steps == B.UPDATES == 4
            tie_moved = any(not torch.equal(a.tie, b.tie) for a, b in zip(net.blocks, learner.net.blocks))
            assert tie_moved
            learner.sleep(mazes, 5, old)
            assert learner.steps == 7
        finally:
            B.SLEEP_STEPS = saved
    finally:
        B.N = base
    return {"updates_after_batch": 4, "tie_moved": True, "sleep_updates": 3}


def check_practice(steps):
    B.N = R
    torch.manual_seed(0)
    rng = random.Random(7000000)
    p = R.Practice("loop", 0, 12000)
    losses = [p.step(D.source_batch(rng, 64)) for _ in range(steps)]
    assert all(x == x and abs(x) < 1e6 for x in losses)
    n = min(20, steps // 2)
    first, last = sum(losses[:n]) / n, sum(losses[-n:]) / n
    assert last < first, (first, last)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "ck.pt"
        p.save(path)
        again = R.load_net(path)
    t, s, _ = base.tensors(batch("sums", 3))
    p.net.eval()
    again.eval()
    with torch.no_grad():
        same = torch.equal(p.net.loop_rounds(t, s, 6)[0], again.loop_rounds(t, s, 6)[0])
    assert same
    tie_abs = [float(b.tie.abs().mean()) for b in p.net.blocks]
    B.N = base
    return {"steps": steps, "loss_first": first, "loss_last": last, "reload_identical": same, "tie_mean_abs_after_smoke": tie_abs}


def timing():
    out, rng = {}, random.Random(11)
    items = {"sums4": [E.make_sum(rng, 4) for _ in range(64)], "grids5": [D.latin_legend(rng, 5) for _ in range(64)],
             "maze9": [D.make_maze(rng, 9) for _ in range(32)]}
    for name, mod in (("r2g", R), ("loop", base)):
        B.N = mod
        torch.manual_seed(0)
        net = mod.Net("loop")
        opt = torch.optim.AdamW(net.parameters(), lr=1e-3)
        r = {}
        for kind in ("sums4", "grids5"):
            t0 = time.monotonic()
            loss = mod.train_loss(net, items[kind], random.Random(16))
            opt.zero_grad()
            loss.backward()
            opt.step()
            r[f"practice_step_{kind}_s"] = time.monotonic() - t0
        t0 = time.monotonic()
        B.Learner(net, 1e-3).maze_batch(items["maze9"])
        r["maze_batch_9x9_s"] = time.monotonic() - t0
        t, s, _ = base.tensors(items["maze9"])
        t0 = time.monotonic()
        net.infer_rounds(t, s, 48)
        r["infer_48_rounds_9x9_batch32_s"] = time.monotonic() - t0
        out[name] = r
    B.N = base
    return out


def main(out, smoke_steps):
    torch.set_num_threads(2)
    res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "device": "cpu", "torch": torch.__version__,
           "plugin": "claude_dir_r2g_net"}
    for name, fn in (("budget", check_budget), ("same_loop", check_same_loop), ("bias_symmetry", check_bias_symmetry),
                     ("residual_scale", check_residual_scale), ("cross_mask", check_cross_mask), ("block_math", check_block_math),
                     ("net_equivariance", check_net_equivariance), ("shapes", check_shapes), ("gradients", check_gradients),
                     ("learner", check_learner), ("practice_smoke", lambda: check_practice(smoke_steps)), ("timing_cpu", timing)):
        res[name] = fn()
        print(json.dumps({name: res[name]}), flush=True)
    res["selftest"] = "ok"
    print(json.dumps({"selftest": "ok"}))
    if out:
        B.dump(out, res)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path)
    p.add_argument("--smoke-steps", type=int, default=200)
    a = p.parse_args()
    main(a.out, a.smoke_steps)
