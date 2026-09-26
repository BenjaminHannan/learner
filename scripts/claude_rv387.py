#!/usr/bin/env python3
"""rv-387 DRAFT (thought-memory thread, 2026-09-26): guess, and go back, around the loop reasoner on grids. Not sealed.

Why: Ben, 09-25 19:28 UTC: "if it doesn't like where it is right now in its internal representation, it can revert to an
old one ... and go a different direction". rv-385 (plain 1B, registered FAIL for the note) showed going back with a code
ban solved 100 of 160 grids where starting over solved 0. This moves going back into the small loop reasoner, as agreed
with Sleep research (09-25 19:37 and 09-26 12:53 UTC): my file, my number, test time only, their nets untouched,
reported apart from the 3x goal and never counted toward it (it is search around the net, not skill inside it).

Arms, same budget of loop rounds per grid, same checker (the grid checker, check_latin, reads no answer key):
  KEEP   the loop runs on; solved if the grid passes the checker at any round within the budget.
  GUESS  as KEEP, but when the net is unsure (stop head q below a cut at a check round) the code writes the net's top
         symbol for one empty cell onto the page as if it were a given, and the loop runs on. Never goes back.
  BACK   as GUESS, but a snapshot (h, page, written cells) is kept before each guess; if q after the guess falls below
         q at the snapshot, the snapshot is restored, that symbol is banned there in code, and the next one is tried;
         a cell with every candidate used up sends the search back one more guess.
One change between neighbours: KEEP -> GUESS adds writing guesses; GUESS -> BACK adds going back.

Mechanics (Sleep research, 12:53 UTC): a written cell is set exactly as latin_item sets a given (tokens = E.SYM + name,
slot = 0); loop_rounds embeds the page once, so after writing, the page is re-embedded and Net.step is called here; h
after step is the whole carried state, so h + page + written cells is a complete snapshot; the net's output at a written
cell is never trained, so written symbols are put into the final grid before the checker; only the top s rows are
written (legend rows untouched).

  python -B scripts/claude_rv387.py rehearse-train --out DIR      (tiny loop net from Sleep research's 358i trial code)
  python -B scripts/claude_rv387.py rehearse --ckpt F --n 50 --size 6
  python -B scripts/claude_rv387.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "artifacts/claude-rsn358i-20260926/trial"))

ARMS = ["keep", "guess", "back"]
SURE = 0.99          # a cell whose top symbol has at least this probability is not guessed


def modules():
    """358i trial code (rehearsal); the registered run will use 358i's own script and load()."""
    import attn_trial as A           # installs the 358g legend grids and the trial nets
    return A, A.R, A.E


class Page:
    """The page plus the cells the search has written."""

    def __init__(self, it):
        self.it = it
        self.tokens = [row[:] for row in it.tokens]
        self.slot = [row[:] for row in it.slot]
        self.written = {}

    def copy(self):
        p = Page.__new__(Page)
        p.it, p.tokens, p.slot, p.written = self.it, [r[:] for r in self.tokens], [r[:] for r in self.slot], \
            dict(self.written)
        return p

    def write(self, r, c, tok):
        self.tokens[r][c], self.slot[r][c] = tok, 0
        self.written[(r, c)] = tok

    def open_cells(self):
        s = self.it.size
        return [(r, c) for r in range(s) for c in range(s) if self.it.meta["puz"][r][c] < 0 and (r, c) not in self.written]

    def visible(self, r, c):
        """symbols already on the page in this cell's row or column (givens and written cells)."""
        s, E = self.it.size, modules()[2]
        seen = {self.tokens[r][k] for k in range(s)} | {self.tokens[k][c] for k in range(s)}
        return {t for t in seen if t >= E.SYM}


class Runner:
    def __init__(self, net, R, E):
        self.net, self.R, self.E = net, R, E

    def embed(self, page):
        t = torch.tensor([page.tokens])
        s = torch.tensor([page.slot])
        env = torch.full((1,), self.E.ENVS.index("grids"))
        return self.net.embed(t, s, env)

    def final(self, page, pred):
        W = len(page.tokens[0])
        g = [pred[r * W:(r + 1) * W] for r in range(len(page.tokens))]
        for (r, c), tok in page.written.items():
            g[r][c] = tok
        return g

    @torch.no_grad()
    def solve(self, it, arm, budget, check_every, cut):
        E, net = self.E, self.net
        page = Page(it)
        e, (dr, dc) = self.embed(page)
        h = torch.zeros_like(e)
        stack, used, guesses, backs = [], 0, 0, 0
        names = [E.SYM + n for n in it.meta["names"]]
        since, q, exhausted = 0, 0.0, False
        while used < budget:
            h = net.step(h, e, dr, dc)
            used += 1
            since += 1
            lg, qq = net.read(h)
            q = float(torch.sigmoid(qq.float())[0])
            pred = lg.argmax(-1)[0].tolist()
            if E.check(it, self.final(page, pred)):
                return {"solved": True, "rounds": used, "guesses": guesses, "backs": backs}
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
                exhausted = not stack        # every candidate at the first guess failed: stop guessing, keep refining
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
        return {"solved": False, "rounds": used, "guesses": guesses, "backs": backs}

    def pick(self, page, logits, names):
        """the open cell the net is surest about without being sure (lowest entropy below SURE); candidates in
        probability order, minus symbols already visible in its row or column."""
        W = len(page.tokens[0])
        best = None
        for r, c in page.open_cells():
            p = torch.softmax(logits[r * W + c, names].float(), -1)
            top = float(p.max())
            if top >= SURE:
                continue
            ent = float(-(p * p.clamp_min(1e-9).log()).sum())
            order = [names[j] for j in p.argsort(descending=True).tolist()]
            cands = [t for t in order if t not in page.visible(r, c)]
            if cands and (best is None or ent < best[0]):
                best = (ent, (r, c), cands)
        return (None, None) if best is None else (best[1], best[2])


def rehearse_train(a):
    A, R, E = modules()
    torch.manual_seed(1)
    torch.set_num_threads(4)
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
    A, R, E = modules()
    torch.set_num_threads(4)
    net = A.make_net("loop", "base")
    net.load_state_dict(torch.load(a.ckpt))
    net.eval()
    run = Runner(net, R, E)
    rng = random.Random(a.seed)
    items = [E.latin_item(rng, *E.make_latin_base(rng, a.size)) for _ in range(a.n)]
    for arm in ARMS:
        t0 = time.time()
        res = [run.solve(it, arm, a.budget, a.check_every, a.cut) for it in items]
        print(json.dumps({"arm": arm, "size": a.size, "n": a.n, "solved": sum(r["solved"] for r in res),
                          "guesses": sum(r["guesses"] for r in res), "backs": sum(r["backs"] for r in res),
                          "rounds": sum(r["rounds"] for r in res), "sec": round(time.time() - t0)}), flush=True)


def selftest():
    A, R, E = modules()
    torch.manual_seed(0)
    net = A.make_net("loop", "base").eval()
    run = Runner(net, R, E)
    rng = random.Random(3)
    it = E.latin_item(rng, *E.make_latin_base(rng, 5))
    # the page with nothing written embeds exactly like loop_rounds' first round
    page = Page(it)
    e, (dr, dc) = run.embed(page)
    t, s, _, env = R.tensors([it], "cpu")
    preds, _ = net.loop_rounds(t, s, env, 3)
    h = torch.zeros_like(e)
    for _ in range(3):
        h = net.step(h, e, dr, dc)
    assert net.read(h)[0].argmax(-1)[0].tolist() == preds[0, 2].tolist()
    # a written cell looks exactly like a given; the key's symbols written everywhere pass the checker
    for (r, c) in page.open_cells():
        page.write(r, c, it.target[r][c])
    assert E.check(it, run.final(page, [0] * (len(it.tokens) * len(it.tokens[0]))))
    assert all(v == 0 for row in page.slot[:it.size] for v in row)
    # every arm stays inside the budget
    for arm in ARMS:
        out = run.solve(it, arm, 12, 4, 0.5)
        assert out["rounds"] <= 12
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["rehearse-train", "rehearse", "selftest"])
    ap.add_argument("--out", default="")
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--size", type=int, default=6)
    ap.add_argument("--seed", type=int, default=77100)
    ap.add_argument("--budget", type=int, default=48)
    ap.add_argument("--check-every", type=int, default=6)
    ap.add_argument("--cut", type=float, default=0.5)
    a = ap.parse_args()
    {"rehearse-train": rehearse_train, "rehearse": rehearse, "selftest": lambda _a: selftest()}[a.cmd](a)


if __name__ == "__main__":
    main()
