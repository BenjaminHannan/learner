#!/usr/bin/env python3
"""xfer-1 benchmark (research-loop thread, 2026-09-27). LOCKED while the research loop runs.

Question (Ben's goals page, design/v3/30-modes/ben-goals-2026-09-26.md:24-26): after practising sums and grids, how few
examples does the looping reasoner need to learn a NEW kind of puzzle (mazes)? Compared with a fresh loop, and with a
plain net of the same size that had the same practice. Solving mazes with no examples is reported, not required.

Small nets on CPU (sizes in scripts/claude_xfer1_net.py). No kind labels: a net sees only the puzzle's tokens and which
cells to fill (Ben 11:34 09-27: "It should for each request be able to automatically decide what").

What this file fixes (the loop may not change it):
  practice   PRACTICE_STEPS batches of PRACTICE_BATCH puzzles, each batch all sums (1-4 digits) or all Latin grids
             (4x4 or 5x5, with the 358g legend row so every needed symbol is visible). Fresh puzzles every batch.
  new kind   perfect mazes in the rsn-358m format (scripts/claude_rsn358m_maze.py: walls, open cells, start, goal; mark
             every open cell on the start-goal path; its exact checker), but carved here by Wilson's algorithm (a uniform
             random spanning tree): the 358m carver (depth-first from a fixed corner) makes only about 322 different
             9x9 layouts (20,000 draws), so its test mazes repeat practice layouts. Batches of MAZE_BATCH, all 7x7 or all 9x9,
             fresh mazes every batch, never a panel maze. "Examples" = mazes handed to the learner; the learner never
             gets any other maze.
  checks     after 0 (report: solving cold) and after each count in CHECKS, the learner answers a fixed panel of 9x9
             mazes (dev: 200, holdout: 300), graded by the exact maze checker. At the end also 200 11x11 mazes
             (report: a bigger size). Why 9x9 and not 7x7: only 13,824 different 7x7 mazes exist (192 layouts x 72
             start/goal pairs), so a 7x7 panel would be seen in training; 9x9 has about 24 million (100,352 x 240).
  metric     maze_auc = mean fraction right over CHECKS (log-spaced counts, so it rewards needing few examples).
  guard      practice_acc = the practised net's fraction right on 200 fresh 4-digit sums + 200 fresh 5x5 grids.
  guard      learn_min = minutes the practised net spends inside learn() over all mazes (compute per example; the
             learner may reuse what it was handed, but not at unlimited cost).
  report     with --inits pre,fresh (the holdout command): fresh_auc (a fresh net of the same arm, same maze stream,
             same recipe), transfer = maze_auc - fresh_auc. Always:
             examples_to_bar (first count with >= 75% right, log-interpolated; 131072 if never), cold, big11.
Seeds: the harness's seed picks the maze stream and init; practice nets are cached per (net code, arm, practice seed)
under ~/xfer1-cache (outside the repo). Dev and holdout use different panels, maze streams and practice seeds.
Kept clear of rsn-358x (sleep research): own seeds 6270701+ and 6300000+, own panels, no 358x file is read.

  python -B scripts/claude_xfer1_bench.py eval --split dev|holdout --seed S [--arm loop|plain] [--inits pre|fresh|pre,fresh]
  python -B scripts/claude_xfer1_bench.py adapt --split dev --seed S --arm loop --init pre|fresh --out F.json
  python -B scripts/claude_xfer1_bench.py practice --arm loop --pseed P
  python -B scripts/claude_xfer1_bench.py selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_rsn358a_envs as E  # noqa: E402  (sums, Latin grids, checkers)
import claude_rsn358m_maze as M  # noqa: E402  (perfect mazes, maze checker)

CACHE = Path(os.environ.get("XFER1_CACHE", str(Path.home() / "xfer1-cache")))
PRACTICE_STEPS, PRACTICE_BATCH = 6000, 64
MAZE_BATCH = 32
CHECKS = [1024, 2048, 4096, 8192, 16384, 32768, 65536]
NEVER = 131072
BAR = 0.75
MAX_ROUNDS = 48
PANEL = {"dev": (6270701, 200), "holdout": (6270702, 300)}
PANEL_BIG = {"dev": 6270704, "holdout": 6270705}
TEST_SIZE, BIG_SIZE, STREAM_SIZES = 9, 11, [7, 9]
PRACTICE_PANEL = 6270703
STREAM_BASE = {"dev": 6300000, "holdout": 6400000}


# ---------------- puzzles ----------------
def latin_legend(rng, s):
    """358g grid: the Latin puzzle, one blank row, then a legend row with the puzzle's s symbols (never written)."""
    it = E.latin_item(rng, *E.make_latin_base(rng, s))
    legend = [E.SYM + n for n in it.meta["names"]]
    rng.shuffle(legend)
    return E.Item("grids", s, it.tokens + [[E.BLANK] * s, legend], it.slot + [[0] * s, [0] * s],
                  it.target + [[0] * s, [0] * s], it.meta)


def practice_batch(rng):
    if rng.random() < 0.5:
        n = rng.choice([1, 2, 3, 4])
        return [E.make_sum(rng, n) for _ in range(PRACTICE_BATCH)]
    s = rng.choice([4, 5])
    return [latin_legend(rng, s) for _ in range(PRACTICE_BATCH)]


def make_maze(rng, s):
    """perfect maze on an s x s grid (s odd), uniform spanning tree over the k x k cells (Wilson); 358m item format"""
    k = (s - 1) // 2
    cells = [(i, j) for i in range(k) for j in range(k)]
    g = [[False] * s for _ in range(s)]
    root = rng.choice(cells)
    tree = {root}
    g[2 * root[0] + 1][2 * root[1] + 1] = True
    order = cells[:]
    rng.shuffle(order)
    for start in order:
        nxt, u = {}, start
        while u not in tree:
            nb = [(u[0] + a, u[1] + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= u[0] + a < k and 0 <= u[1] + b < k]
            nxt[u] = rng.choice(nb)
            u = nxt[u]
        u = start
        while u not in tree:
            tree.add(u)
            v = nxt[u]
            g[2 * u[0] + 1][2 * u[1] + 1] = True
            g[u[0] + v[0] + 1][u[1] + v[1] + 1] = True
            u = v
    a, b = rng.sample([(2 * i + 1, 2 * j + 1) for i, j in cells], 2)
    on = set(M.path_of(g, a, b))
    tokens, slot, target = [], [], []
    for r in range(s):
        tr, sr, yr = [], [], []
        for c in range(s):
            if (r, c) == a:
                tr.append(M.START); sr.append(0); yr.append(0)
            elif (r, c) == b:
                tr.append(M.GOAL); sr.append(0); yr.append(0)
            elif not g[r][c]:
                tr.append(M.WALL); sr.append(0); yr.append(0)
            else:
                tr.append(E.MASK); sr.append(1); yr.append(M.ON if (r, c) in on else M.OFF)
        tokens.append(tr); slot.append(sr); target.append(yr)
    return E.Item("mazes", s, tokens, slot, target, {"start": a, "goal": b, "path_len": len(on)})


def maze_key(it):
    return json.dumps(it.tokens)


_BANNED = None


def banned():
    global _BANNED
    if _BANNED is None:
        _BANNED = {maze_key(it) for sp in PANEL for it in maze_panel(sp)} | \
                  {maze_key(it) for sp in PANEL_BIG for it in big_panel(sp)}
    return _BANNED


def maze_batch(rng):
    s = rng.choice(STREAM_SIZES)
    out, ban = [], banned()
    while len(out) < MAZE_BATCH:
        it = make_maze(rng, s)
        if maze_key(it) not in ban:
            out.append(it)
    return out


def check(item, pred):
    return M.check_maze(item, pred) if item.env == "mazes" else E.check(item, pred)


def maze_panel(split):
    seed, n = PANEL[split]
    rng = random.Random(seed)
    return [make_maze(rng, TEST_SIZE) for _ in range(n)]


def big_panel(split):
    rng = random.Random(PANEL_BIG[split])
    return [make_maze(rng, BIG_SIZE) for _ in range(200)]


def practice_panel():
    rng = random.Random(PRACTICE_PANEL)
    return [E.make_sum(rng, 4) for _ in range(200)] + [latin_legend(rng, 5) for _ in range(200)]


def practice_seed(split, seed):
    if split == "holdout":
        return 500 + seed
    return seed if seed < 100000 else 2 + seed % 4          # fresh confirm seeds reuse a pool of 4 practice nets


# ---------------- learner plumbing ----------------
def learner_modules():
    import claude_xfer1_net as N  # noqa: E402
    import claude_xfer1_adapt as A  # noqa: E402
    return N, A


def net_key():
    h = hashlib.sha256((HERE / "claude_xfer1_net.py").read_bytes())
    h.update(f"{PRACTICE_STEPS},{PRACTICE_BATCH}".encode())
    return h.hexdigest()[:16]


def ckpt_path(arm, pseed):
    return CACHE / net_key() / f"{arm}-p{pseed}.pt"


def score(A, model, items):
    right = 0
    for i in range(0, len(items), 100):
        chunk = items[i:i + 100]
        preds = A.predict(model, chunk, MAX_ROUNDS)
        right += sum(bool(check(it, p)) for it, p in zip(chunk, preds))
    return right


def run_practice(arm, pseed):
    N, _ = learner_modules()
    out = ckpt_path(arm, pseed)
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rng = random.Random(7000000 + pseed)
    P = N.Practice(arm, pseed, PRACTICE_STEPS)
    for _ in range(PRACTICE_STEPS):
        P.step(practice_batch(rng))
    tmp = out.with_suffix(".tmp")
    P.save(tmp)
    os.replace(tmp, out)
    (out.with_suffix(".json")).write_text(json.dumps({"arm": arm, "pseed": pseed, "steps": PRACTICE_STEPS,
                                                      "minutes": round((time.time() - t0) / 60, 1)}))
    print(f"practice {arm} p{pseed}: {(time.time() - t0) / 60:.1f} min -> {out}", flush=True)
    return out


def log2_interp(curve):
    """first example count with acc >= BAR, interpolated in log2 between checks; NEVER if never."""
    prev_n, prev_a = None, None
    for n in CHECKS:
        a = curve[str(n)]
        if a >= BAR:
            if prev_n is None or prev_a is None:
                return float(n)
            f = (BAR - prev_a) / max(a - prev_a, 1e-9)
            return float(2 ** (math.log2(prev_n) + f * (math.log2(n) - math.log2(prev_n))))
        prev_n, prev_a = n, a
    return float(NEVER)


def run_adapt(split, seed, arm, init):
    N, A = learner_modules()
    t0 = time.time()
    ck = run_practice(arm, practice_seed(split, seed)) if init == "pre" else None
    res = {"split": split, "seed": seed, "arm": arm, "init": init, "net_key": net_key(),
           "practice_seed": practice_seed(split, seed) if init == "pre" else None}
    model = A.Adapter(arm, ck, seed, CHECKS[-1])
    if init == "pre":
        pp = practice_panel()
        res["practice_acc"] = score(A, model, pp) / len(pp)
    panel = maze_panel(split)
    curve = {"0": score(A, model, panel) / len(panel)}
    rng = random.Random(STREAM_BASE[split] + seed)
    seen, learn_s = 0, 0.0
    for n in CHECKS:
        while seen < n:
            items = maze_batch(rng)
            t1 = time.time()
            model.learn(items)
            learn_s += time.time() - t1
            seen += len(items)
        curve[str(n)] = score(A, model, panel) / len(panel)
        print(json.dumps({"arm": arm, "init": init, "examples": n, "acc": curve[str(n)],
                          "min": round((time.time() - t0) / 60, 1)}), flush=True)
    res.update(curve=curve, maze_auc=sum(curve[str(n)] for n in CHECKS) / len(CHECKS), cold=curve["0"],
               examples_to_bar=log2_interp(curve), big=score(A, model, big_panel(split)) / 200,
               learn_min=learn_s / 60, minutes=round((time.time() - t0) / 60, 1))
    return res


def cmd_adapt(a):
    import torch
    torch.set_num_threads(a.threads)
    res = run_adapt(a.split, a.seed, a.arm, a.init)
    Path(a.out).write_text(json.dumps(res), encoding="utf-8")


def cmd_practice(a):
    import torch
    torch.set_num_threads(a.threads)
    run_practice(a.arm, a.pseed)


def cmd_eval(a):
    """the harness command: the practised net of one arm (and, with --inits pre,fresh, a fresh net of the same arm in
    parallel, 2 threads each); prints metric lines. maze_auc is the first init's."""
    inits = a.inits.split(",")
    tmp = Path(tempfile.mkdtemp(prefix="xfer1-"))
    threads = str(max(1, 4 // len(inits)))
    procs = {}
    for init in inits:
        cmd = [sys.executable, "-B", str(Path(__file__).resolve()), "adapt", "--split", a.split, "--seed", str(a.seed),
               "--arm", a.arm, "--init", init, "--out", str(tmp / f"{init}.json"), "--threads", threads]
        procs[init] = subprocess.Popen(cmd, stdout=open(tmp / f"{init}.log", "w"), stderr=subprocess.STDOUT)
    rc = {k: p.wait() for k, p in procs.items()}
    for k in procs:
        print(f"--- {k} log ---\n" + (tmp / f"{k}.log").read_text()[-3000:])
    if any(rc.values()):
        print(f"error: adapt runs failed {rc}", flush=True)
        sys.exit(1)
    res = {k: json.loads((tmp / f"{k}.json").read_text()) for k in inits}
    print(json.dumps(res))
    first = res[inits[0]]
    out = [("maze_auc", first["maze_auc"]), ("examples_to_bar", first["examples_to_bar"]), ("cold", first["cold"]),
           ("big11", first["big"]), ("learn_min", first["learn_min"])]
    if "practice_acc" in first:
        out.append(("practice_acc", first["practice_acc"]))
    if "pre" in res and "fresh" in res:
        out += [("fresh_auc", res["fresh"]["maze_auc"]), ("transfer", res["pre"]["maze_auc"] - res["fresh"]["maze_auc"]),
                ("fresh_examples_to_bar", res["fresh"]["examples_to_bar"]), ("fresh_big11", res["fresh"]["big"])]
    for name, v in out:
        print(f"{name}: {v:.6f}")


def selftest():
    rng = random.Random(1)
    b = practice_batch(rng)
    assert len(b) == PRACTICE_BATCH and all(check(it, it.target) for it in b)
    for s in (4, 5):
        it = latin_legend(rng, s)
        vis = {t for row in it.tokens for t in row if t >= E.SYM}
        assert {t for row in it.target for t in row if t} <= vis and check(it, it.target)
    m = maze_batch(rng)
    assert all(check(it, it.target) for it in m)
    dev, ho = maze_panel("dev"), maze_panel("holdout")
    key = maze_key
    assert not ({key(i) for i in dev} & {key(i) for i in ho}), "dev and holdout panels overlap"
    stream = random.Random(STREAM_BASE["dev"] + 0)
    seen = set()
    for _ in range(CHECKS[-1] // MAZE_BATCH):
        seen |= {key(i) for i in maze_batch(stream)}
    print(f"selftest ok: {len(seen)} distinct stream mazes for seed 0; panel overlap dev "
          f"{len({key(i) for i in dev} & seen)}/{len(dev)}, holdout {len({key(i) for i in ho} & seen)}/{len(ho)}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("eval")
    p.add_argument("--split", choices=["dev", "holdout"], required=True)
    p.add_argument("--seed", type=int, default=int(os.environ.get("RL_SEED", 0)))
    p.add_argument("--arm", choices=["loop", "plain"], default="loop")
    p.add_argument("--inits", choices=["pre", "fresh", "pre,fresh"], default="pre")
    p = sub.add_parser("adapt")
    p.add_argument("--split", choices=["dev", "holdout"], required=True); p.add_argument("--seed", type=int, required=True)
    p.add_argument("--arm", choices=["loop", "plain"], required=True)
    p.add_argument("--init", choices=["pre", "fresh"], required=True); p.add_argument("--out", required=True)
    p.add_argument("--threads", type=int, default=4)
    p = sub.add_parser("practice")
    p.add_argument("--arm", choices=["loop", "plain"], required=True); p.add_argument("--pseed", type=int, required=True)
    p.add_argument("--threads", type=int, default=4)
    sub.add_parser("selftest")
    a = ap.parse_args()
    {"eval": cmd_eval, "adapt": cmd_adapt, "practice": cmd_practice, "selftest": lambda _: selftest()}[a.cmd](a)


if __name__ == "__main__":
    main()
