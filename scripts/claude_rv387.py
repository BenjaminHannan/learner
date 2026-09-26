#!/usr/bin/env python3
"""rv-387: guess, and go back, around the loop reasoner on grids (thought-memory thread, 2026-09-26).

Why: Ben, 09-25 19:28 UTC: "if it doesn't like where it is right now in its internal representation, it can revert to an
old one ... and go a different direction". rv-385 (plain 1B, registered FAIL for the note) showed going back with a code
ban solved 100 of 160 grids where starting over solved 0. This moves going back into the small loop reasoner, as agreed
with Sleep research (09-25 19:37, 09-26 12:53 and 13:36 UTC): my file, my number, test time only, their nets untouched,
run on 358i's rental after its own sealed steps, reported apart from the 3x goal and never counted toward it (it is
search around the net, not skill inside it). Marks: artifacts/claude-rv387-20260926/PASSMARKS.md.

Arms, same budget of loop rounds per grid, same checker (358's check_latin: any complete grid that keeps the givens and
has every symbol once per row and column; it reads no answer key):
  KEEP   the loop runs on; solved if the grid passes the checker at any round within the budget.
  GUESS  as KEEP, but at every check round where the stop head q is below the cut, the code writes the net's top symbol
         for one open cell onto the page as if it were a given, and the loop runs on. Never goes back.
  BACK   as GUESS, but a snapshot (h, page, written cells, q) is kept before each guess; if q at a later check round is
         below q at the snapshot, the snapshot is restored, the next candidate symbol is written there instead (the
         tried one stays ruled out by code), and a cell with every candidate used up sends the search back one more
         guess. If every candidate of the first guess fails, BACK stops guessing and keeps refining.
One change between neighbours: KEEP -> GUESS adds writing guesses; GUESS -> BACK adds going back.
Which cell: the open cell whose top symbol the net is surest about without being sure (lowest entropy over the
puzzle's symbols among cells with top probability below 0.99); candidates in the net's order, minus symbols already on
the page in that row or column (the visible rule, as in rv-385).

Mechanics (Sleep research, 12:53 UTC): a written cell is set exactly as latin_item sets a given (tokens = E.SYM + name,
slot = 0); loop_rounds embeds the page once, so after writing, the page is re-embedded and Net.step is called here; h
after step is the whole carried state, so h + page + written cells is a complete snapshot; the net's output at a written
cell is never trained, so written symbols are put into the final grid before the checker; only the top s rows are
written (legend rows untouched).

  python -B scripts/claude_rv387.py make-tests --out artifacts/claude-rv387-20260926/tests
  python -B scripts/claude_rv387.py run --ckpt W/loop-s1/final.pt --tests DIR --out F.json     (358i nets)
  python -B scripts/claude_rv387.py check-load --ckpt W/loop-s1/final.pt --tests DIR
  python -B scripts/claude_rv387.py rehearse-train --out DIR | rehearse --ckpt F | selftest     (358i trial code, CPU)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

ARMS = ["keep", "guess", "back"]
SURE = 0.99          # a cell whose top symbol has at least this probability is not guessed
BUDGET = 48          # loop rounds per grid (358a's TEST_ROUNDS)
CHECK_EVERY = 8      # rounds between check rounds
CUT = 0.5            # q below this at a check round = unsure (358's own stop rule stops at q > 0.5)
TESTS = [("grids7", 7, 387107, 300, "primary"), ("grids6", 6, 387106, 300, "secondary")]


def modules(mode):
    """mode 'net': 358i's script (installs its attention design and the 358g legend grids into the 358a modules);
    mode 'trial': Sleep research's unregistered 358i trial code (rehearsal only; it patches Net.offsets)."""
    if mode == "trial":
        sys.path.insert(0, str(ROOT / "artifacts/claude-rsn358i-20260926/trial"))
        import attn_trial as A
        return A, A.R, A.E
    if mode == "legend":
        import claude_rsn358g_run as G     # the legend fix only (for making test grids)
        return G, G.R, G.E
    import claude_rsn358i_run as M          # noqa: F401
    return M, sys.modules["claude_rsn358a_run"], sys.modules["claude_rsn358a_envs"]


class Page:
    """The page plus the cells the search has written."""

    def __init__(self, it, E):
        self.it, self.E = it, E
        self.tokens = [row[:] for row in it.tokens]
        self.slot = [row[:] for row in it.slot]
        self.written = {}

    def copy(self):
        p = Page.__new__(Page)
        p.it, p.E = self.it, self.E
        p.tokens, p.slot, p.written = [r[:] for r in self.tokens], [r[:] for r in self.slot], dict(self.written)
        return p

    def write(self, r, c, tok):
        assert r < self.it.size and self.it.meta["puz"][r][c] < 0
        self.tokens[r][c], self.slot[r][c] = tok, 0
        self.written[(r, c)] = tok

    def open_cells(self):
        s = self.it.size
        return [(r, c) for r in range(s) for c in range(s)
                if self.it.meta["puz"][r][c] < 0 and (r, c) not in self.written]

    def visible(self, r, c):
        """symbols already on the page in this cell's row or column (givens and written cells)."""
        s = self.it.size
        seen = {self.tokens[r][k] for k in range(s)} | {self.tokens[k][c] for k in range(s)}
        return {t for t in seen if t >= self.E.SYM}


class Runner:
    def __init__(self, net, E, device):
        self.net, self.E, self.dev = net, E, device

    def embed(self, page):
        t = torch.tensor([page.tokens], device=self.dev)
        s = torch.tensor([page.slot], device=self.dev)
        env = torch.full((1,), self.E.ENVS.index("grids"), device=self.dev)
        return self.net.embed(t, s, env)

    def final(self, page, pred):
        W = len(page.tokens[0])
        g = [pred[r * W:(r + 1) * W] for r in range(len(page.tokens))]
        for (r, c), tok in page.written.items():
            g[r][c] = tok
        return g

    @torch.no_grad()
    def solve(self, it, arm, budget=BUDGET, check_every=CHECK_EVERY, cut=CUT):
        E, net = self.E, self.net
        page = Page(it, E)
        e, (dr, dc) = self.embed(page)
        h = torch.zeros_like(e)
        stack, used, guesses, backs, since, q, exhausted = [], 0, 0, 0, 0, 0.0, False
        names = [E.SYM + n for n in it.meta["names"]]
        while used < budget:
            h = net.step(h, e, dr, dc)
            used += 1
            since += 1
            lg, qq = net.read(h)
            q = float(torch.sigmoid(qq.float())[0])
            pred = lg.argmax(-1)[0].tolist()
            if E.check(it, self.final(page, pred)):
                return {"solved": True, "rounds": used, "guesses": guesses, "backs": backs, "q": round(q, 4)}
            if arm == "keep" or since < check_every:
                continue
            since = 0
            if arm == "back" and stack and q < stack[-1]["q"]:
                # the last guess made things worse: restore and try the next candidate, going further back if needed
                backs += 1
                while stack:
                    fr = stack[-1]
                    page, h = fr["page"].copy(), fr["h"].clone()
                    if fr["cands"]:
                        page.write(*fr["cell"], fr["cands"].pop(0))
                        break
                    stack.pop()
                exhausted = not stack
                e, (dr, dc) = self.embed(page)
                continue
            if q >= cut or exhausted:
                continue
            cell, cands = self.pick(page, lg[0], names)
            if cell is None:
                continue
            if arm == "back":
                stack.append({"page": page.copy(), "h": h.clone(), "q": q, "cell": cell, "cands": cands[1:]})
            page.write(*cell, cands[0])
            guesses += 1
            e, (dr, dc) = self.embed(page)
        return {"solved": False, "rounds": used, "guesses": guesses, "backs": backs, "q": round(q, 4)}

    def pick(self, page, logits, names):
        W = len(page.tokens[0])
        best = None
        for r, c in page.open_cells():
            p = torch.softmax(logits[r * W + c, names].float(), -1)
            if float(p.max()) >= SURE:
                continue
            ent = float(-(p * p.clamp_min(1e-9).log()).sum())
            order = [names[j] for j in p.argsort(descending=True).tolist()]
            cands = [t for t in order if t not in page.visible(r, c)]
            if cands and (best is None or ent < best[0]):
                best = (ent, (r, c), cands)
        return (None, None) if best is None else (best[1], best[2])


# ---------------- tests ----------------
def make_tests(a):
    _, R, E = modules("legend")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, size, seed, n, role in TESTS:
        rng = random.Random(seed)
        items = [E.latin_item(rng, *E.make_latin_base(rng, size)) for _ in range(n)]
        (out / f"{name}.jsonl").write_text("".join(json.dumps(R.item_to_json(i)) + "\n" for i in items))
        print(f"{name}: {n} grids, seed {seed} ({role})")


def load_tests(R, d):
    return {name: [R.item_from_json(json.loads(l)) for l in (Path(d) / f"{name}.jsonl").read_text().splitlines()]
            for name, *_ in TESTS}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_load(a):
    """before the run: the net loads, is a loop net, and stepping it here matches its own loop_rounds exactly."""
    _, R, E = modules("net")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    assert net.arm == "loop", net.arm
    it = load_tests(R, a.tests)["grids6"][0]
    run = Runner(net, E, dev)
    e, (dr, dc) = run.embed(Page(it, E))
    t, s, _, env = R.tensors([it], dev)
    preds, qs = net.loop_rounds(t, s, env, 5)
    h = torch.zeros_like(e)
    with torch.no_grad():
        for _ in range(5):
            h = net.step(h, e, dr, dc)
        lg, q = net.read(h)
    assert lg.argmax(-1)[0].tolist() == preds[0, 4].tolist()
    print(json.dumps({"ckpt": str(a.ckpt), "sha256": sha256(a.ckpt), "arm": net.arm, "device": dev,
                      "weights": sum(p.numel() for p in net.parameters()), "check": "OK"}))


def run(a):
    _, R, E = modules("net")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    assert net.arm == "loop", net.arm
    tests = load_tests(R, a.tests)
    runner = Runner(net, E, dev)
    res = {"ckpt": str(a.ckpt), "sha256": sha256(a.ckpt), "device": dev, "budget": BUDGET, "check_every": CHECK_EVERY,
           "cut": CUT, "tests": {}}
    for name, *_ in TESTS:
        res["tests"][name] = {}
        for arm in ARMS:
            t0 = time.time()
            rows = [runner.solve(it, arm) for it in tests[name]]
            assert all(r["rounds"] <= BUDGET for r in rows)
            rec = {"n": len(rows), "solved": sum(r["solved"] for r in rows),
                   "rounds": sum(r["rounds"] for r in rows), "guesses": sum(r["guesses"] for r in rows),
                   "backs": sum(r["backs"] for r in rows), "sec": round(time.time() - t0), "per_grid": rows}
            res["tests"][name][arm] = rec
            print(name, arm, json.dumps({k: v for k, v in rec.items() if k != "per_grid"}), flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res) + "\n")


# ---------------- rehearsal on the 358i trial code (CPU, unregistered) ----------------
def rehearse_train(a):
    A, R, E = modules("trial")
    torch.manual_seed(1)
    torch.set_num_threads(2)
    rng, rr = random.Random(5001), random.Random(9001)
    latin = {s: [E.make_latin_base(rng, s) for _ in range(3000)] for s in (4, 5)}
    net = A.make_net("loop", "base")
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=0.1, betas=(0.9, 0.95))
    sch = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda i: min(1, (i + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(i, a.steps) / a.steps)))
    t0 = time.time()
    for step in range(1, a.steps + 1):
        net.train()
        s = rng.choice([4, 5])
        items = [E.latin_item(rng, *E.augment_latin(rng, *rng.choice(latin[s]))) for _ in range(64)]
        t, sl, y, env = R.tensors(items, "cpu")
        tot = rr.randint(1, R.TRAIN_ROUNDS)
        k = rr.randint(1, min(tot, R.GRAD_ROUNDS))
        ls = []
        for lg, q in net.loop_train(t, sl, env, tot - k, k):
            c_, ex = R.ce_and_exact(lg, sl, y)
            ls.append(c_ + 0.5 * torch.nn.functional.binary_cross_entropy_with_logits(q.float(), ex))
        loss = torch.stack(ls).mean()
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sch.step()
        if step % 250 == 0:
            print(step, round(loss.item(), 4), f"{(time.time() - t0) / 60:.1f}m", flush=True)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    torch.save(net.state_dict(), Path(a.out) / "tiny-loop.pt")


def rehearse(a):
    A, R, E = modules("trial")
    torch.set_num_threads(2)
    net = A.make_net("loop", "base")
    net.load_state_dict(torch.load(a.ckpt))
    net.eval()
    runner = Runner(net, E, "cpu")
    rng = random.Random(a.seed)
    items = [E.latin_item(rng, *E.make_latin_base(rng, a.size)) for _ in range(a.n)]
    for arm in ARMS:
        t0 = time.time()
        res = [runner.solve(it, arm) for it in items]
        print(json.dumps({"arm": arm, "size": a.size, "n": a.n, "solved": sum(r["solved"] for r in res),
                          "guesses": sum(r["guesses"] for r in res), "backs": sum(r["backs"] for r in res),
                          "rounds": sum(r["rounds"] for r in res), "sec": round(time.time() - t0)}), flush=True)


def selftest():
    A, R, E = modules("trial")
    torch.manual_seed(0)
    net = A.make_net("loop", "base").eval()
    runner = Runner(net, E, "cpu")
    rng = random.Random(3)
    it = E.latin_item(rng, *E.make_latin_base(rng, 5))
    page = Page(it, E)
    e, (dr, dc) = runner.embed(page)
    t, s, _, env = R.tensors([it], "cpu")
    preds, _ = net.loop_rounds(t, s, env, 3)
    h = torch.zeros_like(e)
    with torch.no_grad():
        for _ in range(3):
            h = net.step(h, e, dr, dc)
    assert net.read(h)[0].argmax(-1)[0].tolist() == preds[0, 2].tolist()
    for (r, c) in page.open_cells():
        page.write(r, c, it.target[r][c])
    assert E.check(it, runner.final(page, [0] * (len(it.tokens) * len(it.tokens[0]))))
    assert all(v == 0 for row in page.slot[:it.size] for v in row)
    assert page.tokens[it.size:] == it.tokens[it.size:]           # legend rows untouched
    for arm in ARMS:
        assert runner.solve(it, arm, 12, 4, 0.5)["rounds"] <= 12
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["make-tests", "check-load", "run", "rehearse-train", "rehearse", "selftest"])
    ap.add_argument("--out", default="")
    ap.add_argument("--tests", default=str(ROOT / "artifacts/claude-rv387-20260926/tests"))
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--size", type=int, default=6)
    ap.add_argument("--seed", type=int, default=77100)
    a = ap.parse_args()
    {"make-tests": make_tests, "check-load": check_load, "run": run, "rehearse-train": rehearse_train,
     "rehearse": rehearse, "selftest": lambda _a: selftest()}[a.cmd](a)


if __name__ == "__main__":
    main()
