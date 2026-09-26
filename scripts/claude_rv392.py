#!/usr/bin/env python3
"""rv-392 (thought-memory thread, 2026-09-26): between messages, do fresh starts that write guesses beat fresh starts
alone? One change from rv-390's RESTART arm.

Why: rv-390 (artifacts/claude-rv390-20260926/RESULTS.md) on 358i's loop nets: carrying on was PROVED WRONG against
restarting (hard 7x7 puzzles: KEEP 5/1/11/0 vs RESTART 17/18/24/17), and writing guesses PASSED against carrying on
(GUESS 24/34/32/14). Its note fixed before the result (NOTE-fallback-before-result.md): the worker then starts fresh
and writes guesses by default, and the next single change is RESTART + GUESS vs RESTART.

Arms, per unfinished day puzzle (same day pass, same 48-round v2 stop rule, same checker as rv-390):
  RESTART   rv-390's RESTART, unchanged: 10 loops of 48 rounds from h0 = sigma x noise (fixed per puzzle and restart).
  RG        the same 10 loops from the SAME noise, each on a fresh page, running rv-387's GUESS inside each loop
            (every 8th round while q < 0.5, write the net's surest-but-unsure symbol as a given; never go back).
            Guesses from one loop are not carried to the next. The only difference from RESTART: the guesses.
  GUESS480  report only: rv-390's GUESS (one 480-round loop from h = 0), for comparison.
Sigma is picked on practice grids (rv-390's p-grids6/p-grids7) by RESTART solves, as in rv-390; RG uses the same sigma.

  python -B scripts/claude_rv392.py make-day --out artifacts/claude-rv392-20260926/day
  python -B scripts/claude_rv392.py all --ckpt F --out DIR/rv392-sN     (selftest, pick-sigma, run)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import claude_rv390 as W  # noqa: E402

V = W.V
DAY = [("grids6", "grids", 6, 39203), ("grids7", "grids", 7, 39204)]
RV390_DAY = ROOT / "artifacts/claude-rv390-20260926/day"


class Worker(W.Worker):
    """rv-390's pausable GUESS worker, starting from a given h0 instead of zeros (h0=None gives rv-390's exactly)."""

    @torch.no_grad()
    def guess_from(self, it, budget, h0=None):
        E, net = self.E, self.net
        names = [E.SYM + n for n in it.meta["names"]]
        page = W.AnyPage(it, E)
        e, (dr, dc) = self.embed(page)
        h = torch.zeros_like(e) if h0 is None else h0.to(e.device, e.dtype).reshape(e.shape)
        used, since, guesses, q = 0, 0, 0, 0.0
        while used < budget:
            h = net.step(h, e, dr, dc)
            used += 1
            since += 1
            lg, qq = net.read(h)
            q = float(torch.sigmoid(qq.float())[0])
            grid = self.final(page, lg.argmax(-1)[0].tolist())
            if E.check(it, grid):
                return {"solved": True, "rounds": used, "guesses": guesses, "q": round(q, 4), "answer": grid}
            if since >= V.CHECK_EVERY:
                since = 0
                if q < V.CUT:
                    cell, cands = self.pick(page, lg[0], names)
                    if cell is not None:
                        page.write(*cell, cands[0])
                        guesses += 1
                        e, (dr, dc) = self.embed(page)
        return {"solved": False, "rounds": used, "guesses": guesses, "q": round(q, 4), "answer": None}


def restart_guess(w, R, items, dev, sigma, tag):
    """RG: the RESTART loops (same noise: W.noise(tag, k, j)), each a fresh 48-round GUESS run."""
    out = []
    for k, it in enumerate(items):
        t, s, _, env = R.tensors([it], dev)
        e, _ = w.net.embed(t, s, env)
        got, guesses = (None, None), 0
        for j in range(W.RESTARTS):
            r = w.guess_from(it, W.DAY_ROUNDS, W.noise(tag, k, j, e.shape[1:], sigma))
            guesses += r["guesses"]
            if r["solved"]:
                got = (j * W.DAY_ROUNDS + r["rounds"], r["answer"])
                break
        out.append((got[0], got[1], guesses))
    return out


def make_day(a):
    _, R, E = W.mods()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    reserved = set()
    for f in sorted(W.RESERVED_TEST_DIR.glob("*.jsonl")) + sorted(RV390_DAY.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            reserved.add(json.dumps(json.loads(line)["tokens"]))
    report = {"reserved_items": len(reserved)}
    for name, env, size, seed in DAY:
        items = W.make_items(E, env, size, seed)
        clash = sum(json.dumps(i.tokens) in reserved for i in items)
        items = [i for i in items if json.dumps(i.tokens) not in reserved]
        (out / f"{name}.jsonl").write_text("".join(json.dumps(R.item_to_json(i)) + "\n" for i in items))
        report[name] = {"seed": seed, "kept": len(items), "clash_with_358i_tests_or_rv390_day": clash}
        print(name, report[name])
    (out / "make-day.json").write_text(json.dumps(report, indent=1) + "\n")


def selftest(a):
    """practice grids only: guess_from(h0=None) equals rv-390's Worker.guess at 48 rounds; guess_from(h0=noise) with every
    guess suppressed equals rv-390's RESTART loop on the same noise (checked through the first accepted round)."""
    _, R, E = W.mods()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    its = W.load(R, RV390_DAY, ["p-grids7"])["p-grids7"]
    d = W.day_pass(net, R, E, its, dev)
    unf = [it for it, r in zip(its, d) if not r["right"]][:a.n]
    w = Worker(net, E, dev)
    same = sum(w.guess_from(it, W.DAY_ROUNDS) == w.guess(it, budget=W.DAY_ROUNDS)[0] for it in unf)
    old_cut, V.CUT = V.CUT, -1.0          # q < -1 never holds: no guesses, so RG's loop must equal RESTART's
    try:
        rg = restart_guess(w, R, unf, dev, 0.3, "selftest")
    finally:
        V.CUT = old_cut
    rs = W.restart(net, R, E, unf, dev, 0.3, "selftest")
    same_rs = sum((x[0] is None) == (y[0] is None) for x, y in zip(rg, rs))
    out = {"n": len(unf), "guess_from_same_as_rv390": same, "no_guess_rg_same_solved_as_restart": same_rs}
    print(json.dumps(out))
    if a.out:
        Path(a.out + ".selftest.json").write_text(json.dumps(out, indent=1) + "\n")
    assert same == len(unf), "guess_from differs from rv-390's worker"


def run(a):
    _, R, E = W.mods()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    items = W.load(R, a.day, [d[0] for d in DAY])
    w = Worker(net, E, dev)
    res = {"ckpt": str(a.ckpt), "sha256": V.sha256(a.ckpt), "sigma": a.sigma, "device": dev,
           "torch": torch.__version__, "sets": {}}
    finds = []
    for name, *_ in DAY:
        t0 = time.time()
        d = W.day_pass(net, R, E, items[name], dev)
        idx = [i for i, r in enumerate(d) if not r["right"]]
        unf = [items[name][i] for i in idx]
        hard = [d[i]["any_round"] is None for i in idx]
        rs = W.restart(net, R, E, unf, dev, a.sigma, f"test|{name}")
        rg = restart_guess(w, R, unf, dev, a.sigma, f"test|{name}")
        g = [w.guess(it)[0] for it in unf]
        rec = {"n": len(d), "day_right": sum(r["right"] for r in d), "unfinished": len(unf), "hard": sum(hard),
               "restart": {"solved": sum(r is not None for r, _ in rs),
                           "hard_solved": sum(r is not None and hd for (r, _), hd in zip(rs, hard))},
               "rg": {"solved": sum(r is not None for r, _, _ in rg),
                      "hard_solved": sum(r is not None and hd for (r, _, _), hd in zip(rg, hard)),
                      "solved_in_first_loop": sum(r is not None and r <= W.DAY_ROUNDS for r, _, _ in rg),
                      "guesses": sum(x for _, _, x in rg)},
               "guess480_report_only": {"solved": sum(x["solved"] for x in g),
                                        "hard_solved": sum(x["solved"] and hd for x, hd in zip(g, hard)),
                                        "guesses": sum(x["guesses"] for x in g)}}
        for i, (rr, ra), (gr, ga, _), gx in zip(idx, rs, rg, g):
            for arm, r, ans in (("restart", rr, ra), ("rg", gr, ga),
                                ("guess480", gx["rounds"] if gx["solved"] else None, gx["answer"])):
                if r is not None:
                    ans = W.clean(items[name][i], ans)
                    assert E.check(items[name][i], ans)
                    finds.append({"set": name, "idx": i, "arm": arm, "round": r, "answer": ans})
        rec["sec"] = round(time.time() - t0)
        res["sets"][name] = rec
        print(name, json.dumps(rec), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    Path(a.out).with_suffix(".finds.jsonl").write_text("".join(json.dumps(f) + "\n" for f in finds))


def all_steps(a):
    base = a.out
    selftest(a)
    a.out, a.day_saved = base + ".sigma.json", a.day
    a.day = str(RV390_DAY)
    W.pick_sigma(a)                       # rv-390's rule on rv-390's practice grids
    a.day = a.day_saved
    a.sigma = json.loads(Path(a.out).read_text())["sigma"]
    a.out = base + ".json"
    run(a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["make-day", "selftest", "run", "all"])
    ap.add_argument("--out", default="")
    ap.add_argument("--day", default=str(ROOT / "artifacts/claude-rv392-20260926/day"))
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--sigma", type=float, default=0.3)
    ap.add_argument("--n", type=int, default=30)
    a = ap.parse_args()
    {"make-day": make_day, "selftest": selftest, "run": run, "all": all_steps}[a.cmd](a)


if __name__ == "__main__":
    main()
