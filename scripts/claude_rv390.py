#!/usr/bin/env python3
"""rv-390 DRAFT (thought-memory thread, 2026-09-26): keep working on unfinished puzzles between messages. Not sealed.

Why: Ben, 13:57 UTC (Sleep research thread): the reasoner should keep working on unfinished problems between messages.
Agreed with Sleep research (13:59 UTC): this thread owns the unfinished list and the between-messages worker (search
around a fixed 358i loop net; no weights change); Sleep research supplies the nets, the day's puzzle rule and the
night's fixed test states (58600-59999 only), and its night pool takes the checked solutions. Runs after rv-387's
verdict, because BACK is rv-387's guess-and-go-back wrapper.

Day: fresh bigger puzzles (seeds 39101-39104: sums6, sums8, grids6, grids7, 300 each, made through 358i's script so
grids carry the legend). The net answers each at the normal budget (48 rounds, 358's own v2 stop rule). Unfinished =
every day puzzle whose own-stop answer the checker rejects.
Downtime, per unfinished puzzle, 480 rounds each, the checker allowed (like running tests):
  NOTHING  0 solved by definition (the headline's floor).
  KEEP     one loop of 480 rounds from h = 0; solved if the checker accepts any round. Solves at round <= 48 are
           counted apart: those are the checker catching an answer the stop rule passed over, not longer thinking.
  RESTART  same-compute control (Sleep research, 13:59): 10 loops of 48 rounds from h0 = sigma * Gaussian noise (a fixed
           seed per puzzle and restart; sigma picked on practice grids only); solved if the checker accepts any round.
  BACK     grids only: rv-387's guess and go back, 480 rounds (at most 60 guesses, the same cap for every puzzle).
Headline: does thinking between messages solve more than not thinking, and more than the same compute spent on fresh
restarts. Second: BACK vs KEEP on grids.

  python -B scripts/claude_rv390.py make-day --out artifacts/claude-rv390-20260926/day
  python -B scripts/claude_rv390.py pick-sigma --ckpt F         (practice grids, seeds 39111-39114)
  python -B scripts/claude_rv390.py run --ckpt F --day DIR --sigma S --out F.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import claude_rv387 as V  # noqa: E402  (rv-387's Page/Runner)

DAY = [("sums6", "sums", 6, 39101), ("sums8", "sums", 8, 39102), ("grids6", "grids", 6, 39103),
       ("grids7", "grids", 7, 39104)]
PRACTICE = [("p-grids6", "grids", 6, 39113), ("p-grids7", "grids", 7, 39114)]
N_DAY, DAY_ROUNDS, DOWN, RESTARTS, MAX_GUESSES = 300, 48, 480, 10, 60
SIGMAS = (0.1, 0.3, 1.0)
RESERVED_TEST_DIR = ROOT / "artifacts/claude-rsn358i-20260926/tests"


def mods():
    return V.modules("net")


def make_items(E, env, size, seed, n=N_DAY):
    rng = random.Random(seed)
    if env == "sums":
        return [E.make_sum(rng, size) for _ in range(n)]
    return [E.latin_item(rng, *E.make_latin_base(rng, size)) for _ in range(n)]


def make_day(a):
    _, R, E = mods()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    reserved = set()
    for f in sorted(RESERVED_TEST_DIR.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            reserved.add(json.dumps(json.loads(line)["tokens"]))
    report = {"reserved_items": len(reserved)}
    for name, env, size, seed in DAY + PRACTICE:
        items = make_items(E, env, size, seed)
        clash = sum(json.dumps(i.tokens) in reserved for i in items)
        items = [i for i in items if json.dumps(i.tokens) not in reserved]
        (out / f"{name}.jsonl").write_text("".join(json.dumps(R.item_to_json(i)) + "\n" for i in items))
        report[name] = {"seed": seed, "kept": len(items), "clash_with_358i_tests": clash}
        print(name, report[name])
    (out / "make-day.json").write_text(json.dumps(report, indent=1) + "\n")


def load(R, d, names):
    return {n: [R.item_from_json(json.loads(l)) for l in (Path(d) / f"{n}.jsonl").read_text().splitlines()]
            for n in names}


@torch.no_grad()
def rounds_batch(net, R, items, n, dev, h0=None):
    """predictions and stop-head values for every round, batched (as 358's evaluate does)."""
    t, s, _, env = R.tensors(items, dev)
    e, (dr, dc) = net.embed(t, s, env)
    h = torch.zeros_like(e) if h0 is None else h0
    preds, qs = [], []
    for _ in range(n):
        h = net.step(h, e, dr, dc)
        lg, q = net.read(h)
        preds.append(lg.argmax(-1))
        qs.append(torch.sigmoid(q.float()))
    return torch.stack(preds, 1).tolist(), torch.stack(qs, 1).tolist()


def first_right(E, R, it, preds):
    return next((r + 1 for r, p in enumerate(preds) if E.check(it, R.grid_of(p, it))), None)


def day_pass(net, R, E, items, dev):
    import claude_rsn358a2_run as V2
    out = []
    for i in range(0, len(items), 100):
        chunk = items[i:i + 100]
        P, Q = rounds_batch(net, R, chunk, DAY_ROUNDS, dev)
        for it, p, q in zip(chunk, P, Q):
            stop = V2.stop_round(p, q, DAY_ROUNDS)
            out.append({"right": bool(E.check(it, R.grid_of(p[stop], it))), "stop": stop + 1,
                        "any_round": first_right(E, R, it, p)})
    return out


def keep(net, R, E, items, dev):
    res = []
    for i in range(0, len(items), 50):
        chunk = items[i:i + 50]
        P, _ = rounds_batch(net, R, chunk, DOWN, dev)
        res += [first_right(E, R, it, p) for it, p in zip(chunk, P)]
    return res


def restart(net, R, E, items, dev, sigma, tag):
    res = []
    for k, it in enumerate(items):
        got = None
        for j in range(RESTARTS):
            g = torch.Generator(device="cpu").manual_seed(int(hashlib.sha256(f"{tag}|{k}|{j}".encode()).hexdigest()[:8], 16))
            t, s, _, env = R.tensors([it], dev)
            e, _ = net.embed(t, s, env)
            h0 = (sigma * torch.randn(e.shape, generator=g)).to(dev)
            P, _ = rounds_batch(net, R, [it], DAY_ROUNDS, dev, h0)
            r = first_right(E, R, it, P[0])
            if r is not None:
                got = j * DAY_ROUNDS + r
                break
        res.append(got)
    return res


def pick_sigma(a):
    _, R, E = mods()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    items = load(R, a.day, [p[0] for p in PRACTICE])
    out = {}
    for name, its in items.items():
        d = day_pass(net, R, E, its, dev)
        unf = [it for it, r in zip(its, d) if not r["right"]]
        out[name] = {"unfinished": len(unf)}
        for sg in SIGMAS:
            out[name][str(sg)] = sum(x is not None for x in restart(net, R, E, unf, dev, sg, f"practice|{name}|{sg}"))
    best = max(SIGMAS, key=lambda sg: sum(out[n][str(sg)] for n in out))
    out["sigma"] = best
    print(json.dumps(out))
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")


def run(a):
    _, R, E = mods()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    items = load(R, a.day, [d[0] for d in DAY])
    runner = V.Runner(net, E, dev)
    res = {"ckpt": str(a.ckpt), "sha256": V.sha256(a.ckpt), "sigma": a.sigma, "sets": {}}
    for name, env, *_ in DAY:
        t0 = time.time()
        d = day_pass(net, R, E, items[name], dev)
        unf = [it for it, r in zip(items[name], d) if not r["right"]]
        rec = {"n": len(d), "day_right": sum(r["right"] for r in d), "unfinished": len(unf),
               "day_right_any_round": sum(r["any_round"] is not None for r in d)}
        k = keep(net, R, E, unf, dev)
        rs = restart(net, R, E, unf, dev, a.sigma, f"test|{name}")
        rec["keep"] = {"solved": sum(x is not None for x in k), "solved_by_48": sum(x is not None and x <= 48 for x in k)}
        rec["restart"] = {"solved": sum(x is not None for x in rs)}
        if env == "grids":
            b = [runner.solve(it, "back", budget=DOWN) for it in unf]
            rec["back"] = {"solved": sum(x["solved"] for x in b), "guesses": sum(x["guesses"] for x in b),
                           "backs": sum(x["backs"] for x in b)}
        rec["sec"] = round(time.time() - t0)
        res["sets"][name] = rec
        print(name, json.dumps(rec), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["make-day", "pick-sigma", "run"])
    ap.add_argument("--out", default="")
    ap.add_argument("--day", default=str(ROOT / "artifacts/claude-rv390-20260926/day"))
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--sigma", type=float, default=0.3)
    a = ap.parse_args()
    {"make-day": make_day, "pick-sigma": pick_sigma, "run": run}[a.cmd](a)


if __name__ == "__main__":
    main()
