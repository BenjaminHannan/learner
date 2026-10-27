#!/usr/bin/env python3
"""rv-390 DRAFT (thought-memory thread, 2026-09-26): keep working on unfinished puzzles between messages. Not sealed.
Revised 16:2x UTC after rv-387's verdict (artifacts/claude-rv387-20260926/RESULTS.md): its going back never fired, so
BACK here would only be GUESS under another name. BACK is replaced by GUESS; going back moves to its own test.

Why: Ben, 13:57 UTC (Sleep research thread): the reasoner should keep working on unfinished problems between messages.
Ben, 14:49 UTC: that work must be interruptible at any time. Agreed with Sleep research (13:59 UTC): this thread owns the
unfinished list and the between-messages worker (search around a fixed 358i loop net; no weights change); Sleep research
supplies the nets and the night's fixed test states (58600-59999 only), and its night pool takes the checked solutions
(written to <out>.finds.jsonl).

Day: fresh bigger puzzles (seeds 39101-39104: sums6, sums8, grids6, grids7, 300 each, made through 358i's script so
grids carry the legend). The net answers each at the normal budget (48 rounds, 358's own v2 stop rule). Unfinished =
every day puzzle whose own-stop answer the checker rejects.
Downtime, per unfinished puzzle, 480 rounds each, the checker allowed (like running tests):
  NOTHING  0 solved by definition.
  KEEP     one loop of 480 rounds from h = 0; solved if the checker accepts any round. Solves at round <= 48 are
           counted apart: those are the checker catching an answer the stop rule passed over, not longer thinking.
  RESTART  same-compute control (Sleep research, 13:59): 10 loops of 48 rounds from h0 = sigma * Gaussian noise (a fixed
           seed per puzzle and restart; sigma picked on practice grids only); solved if the checker accepts any round.
  GUESS    rv-387's GUESS, unchanged in logic, 480 rounds: every 8th round while the stop head q < 0.5, the code writes
           the net's top symbol for the open cell it is surest about (below 0.99) as if it were given, and never goes
           back. Disclosed code parts: the checker, and on grids the candidate list skips symbols already in the cell's
           row or column (rv-387's pick). On sums it is a report-only transfer row (built on grids).
Headline: KEEP vs RESTART on grids7 (does carrying on beat starting over with the same compute). Second: GUESS vs KEEP
on grids7. Interruptibility (interrupt_check): pauses change nothing and a message waits under 1 s.

  python -B scripts/claude_rv390.py make-day --out artifacts/claude-rv390-20260926/day
  python -B scripts/claude_rv390.py all --ckpt F --out DIR/rv390-sN   (selftest, pick-sigma, run; practice grids for
                                                                       the first two only)
  (or one at a time: selftest --ckpt F; pick-sigma --ckpt F --out S.json; run --ckpt F --sigma S --out F.json)
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
N_DAY, DAY_ROUNDS, DOWN, RESTARTS = 300, 48, 480, 10
PAUSES, INTERRUPT_N, INTERRUPT_SEED, WAIT_LIMIT_SEC = 5, 40, 39090, 1.0
SIGMAS = (0.1, 0.3, 1.0)
RESERVED_TEST_DIR = ROOT / "artifacts/claude-rsn358i-20260926/tests"


def mods():
    return V.modules("net")


# ---------------- the worker's GUESS arm (any kind; stops after any round and resumes) ----------------
class AnyPage(V.Page):
    """rv-387's page for any kind: open cells are the item's answer slots; no visible rule outside grids."""

    def open_cells(self):
        return [(r, c) for r, row in enumerate(self.it.slot) for c, v in enumerate(row)
                if v == 1 and (r, c) not in self.written]

    def copy(self):
        p = AnyPage.__new__(AnyPage)
        p.it, p.E = self.it, self.E
        p.tokens, p.slot, p.written = [r[:] for r in self.tokens], [r[:] for r in self.slot], dict(self.written)
        return p

    def write(self, r, c, tok):
        assert self.it.slot[r][c] == 1
        self.tokens[r][c], self.slot[r][c] = tok, 0
        self.written[(r, c)] = tok

    def visible(self, r, c):
        return super().visible(r, c) if self.it.env == "grids" else set()


def sync(dev):
    if dev == "cuda":
        torch.cuda.synchronize()


class Worker(V.Runner):
    """rv-387's GUESS, unchanged in logic (every 8th round while q < 0.5, write the net's top symbol for the open cell
    it is surest about without being sure; never go back), for any kind, written so it can stop after any round: its
    whole state is the dict `st` (page, h, counters), which a pause copies to the CPU and a resume copies back."""

    def embed(self, page):
        t = torch.tensor([page.tokens], device=self.dev)
        s = torch.tensor([page.slot], device=self.dev)
        env = torch.full((1,), self.E.ENVS.index(page.it.env), device=self.dev)
        return self.net.embed(t, s, env)

    @torch.no_grad()
    def guess(self, it, budget=DOWN, pauses=(), message=None):
        E, net = self.E, self.net
        names = [E.SYM + n for n in it.meta["names"]] if it.env == "grids" else [E.BLANK] + [E.DIG + d for d in range(10)]
        st = {"page": AnyPage(it, E), "h": None, "used": 0, "since": 0, "guesses": 0, "q": 0.0, "answer": None}
        e, (dr, dc) = self.embed(st["page"])
        st["h"] = torch.zeros_like(e)
        tm = {"step": 0.0, "pause": 0.0, "pauses": 0}
        while st["used"] < budget and st["answer"] is None:
            if st["used"] in pauses:
                t0 = time.perf_counter()
                saved = dict(st, page=st["page"].copy(), h=st["h"].cpu().clone())
                sync(self.dev)
                tm["pause"], tm["pauses"] = max(tm["pause"], time.perf_counter() - t0), tm["pauses"] + 1
                del st, e, dr, dc
                message()
                st = dict(saved, page=saved["page"].copy(), h=saved["h"].to(self.dev))
                e, (dr, dc) = self.embed(st["page"])
            t0 = time.perf_counter()
            st["h"] = net.step(st["h"], e, dr, dc)
            st["used"] += 1
            st["since"] += 1
            lg, qq = net.read(st["h"])
            st["q"] = float(torch.sigmoid(qq.float())[0])
            grid = self.final(st["page"], lg.argmax(-1)[0].tolist())
            if E.check(it, grid):
                st["answer"] = grid
            elif st["since"] >= V.CHECK_EVERY:
                st["since"] = 0
                if st["q"] < V.CUT:
                    cell, cands = self.pick(st["page"], lg[0], names)
                    if cell is not None:
                        st["page"].write(*cell, cands[0])
                        st["guesses"] += 1
                        e, (dr, dc) = self.embed(st["page"])
            sync(self.dev)
            tm["step"] = max(tm["step"], time.perf_counter() - t0)
        return {"solved": st["answer"] is not None, "rounds": st["used"], "guesses": st["guesses"],
                "q": round(st["q"], 4), "answer": st["answer"]}, tm


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
def rounds_batch(net, R, items, n, dev, h0=None, pauses=(), message=None, timing=None):
    """predictions and stop-head values for every round, batched (as 358's evaluate does). With pauses, the batch's
    whole state (h and the round number) goes to the CPU before those rounds, message() runs, and it comes back."""
    t, s, _, env = R.tensors(items, dev)
    e, (dr, dc) = net.embed(t, s, env)
    h = torch.zeros_like(e) if h0 is None else h0
    preds, qs, tm = [], [], {"step": 0.0, "pause": 0.0, "pauses": 0}
    for r in range(n):
        if r in pauses:
            t0 = time.perf_counter()
            saved = h.cpu().clone()
            sync(dev)
            tm["pause"], tm["pauses"] = max(tm["pause"], time.perf_counter() - t0), tm["pauses"] + 1
            del h, e, dr, dc
            message()
            e, (dr, dc) = net.embed(t, s, env)
            h = saved.to(dev)
        t0 = time.perf_counter()
        h = net.step(h, e, dr, dc)
        lg, q = net.read(h)
        preds.append(lg.argmax(-1))
        qs.append(torch.sigmoid(q.float()))
        sync(dev)
        tm["step"] = max(tm["step"], time.perf_counter() - t0)
    if timing is not None:
        timing.update(tm)
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
    """KEEP: one loop of DOWN rounds from h = 0. Returns (first accepted round or None, that round's answer)."""
    res = []
    for i in range(0, len(items), 50):
        chunk = items[i:i + 50]
        P, _ = rounds_batch(net, R, chunk, DOWN, dev)
        for it, p in zip(chunk, P):
            r = first_right(E, R, it, p)
            res.append((r, None if r is None else R.grid_of(p[r - 1], it)))
    return res


def clean(it, grid):
    """the page with the net's answer in the answer slots only (the checker ignores the read-out anywhere else)."""
    return [[grid[r][c] if it.slot[r][c] == 1 else it.tokens[r][c] for c in range(len(it.tokens[0]))]
            for r in range(len(it.tokens))]


def noise(tag, k, j, shape, sigma):
    g = torch.Generator(device="cpu").manual_seed(int(hashlib.sha256(f"{tag}|{k}|{j}".encode()).hexdigest()[:8], 16))
    return sigma * torch.randn(shape, generator=g)


def restart(net, R, E, items, dev, sigma, tag):
    """RESTART: up to RESTARTS loops of DAY_ROUNDS from h0 = sigma * noise (fixed per puzzle and restart), batched.
    Returns (first accepted round counting all restarts, or None; that round's answer)."""
    got = [(None, None)] * len(items)
    for j in range(RESTARTS):
        todo = [k for k in range(len(items)) if got[k][0] is None]
        for i in range(0, len(todo), 50):
            ks = todo[i:i + 50]
            chunk = [items[k] for k in ks]
            t, s, _, env = R.tensors(chunk, dev)
            e, _ = net.embed(t, s, env)
            h0 = torch.stack([noise(tag, k, j, e.shape[1:], sigma) for k in ks]).to(dev)
            P, _ = rounds_batch(net, R, chunk, DAY_ROUNDS, dev, h0)
            for k, it, p in zip(ks, chunk, P):
                r = first_right(E, R, it, p)
                if r is not None:
                    got[k] = (j * DAY_ROUNDS + r, R.grid_of(p[r - 1], it))
    return got


def pick_sigma(a):
    _, R, E = mods()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    items = load(R, a.day, [p[0] for p in PRACTICE])
    out = {"ckpt": str(a.ckpt), "sha256": V.sha256(a.ckpt)}
    for name, its in items.items():
        d = day_pass(net, R, E, its, dev)
        unf = [it for it, r in zip(its, d) if not r["right"]]
        out[name] = {"unfinished": len(unf)}
        for sg in SIGMAS:
            out[name][str(sg)] = sum(x is not None for x, _ in restart(net, R, E, unf, dev, sg, f"practice|{name}|{sg}"))
    best = max(SIGMAS, key=lambda sg: sum(out[n][str(sg)] for n, _, _, _ in PRACTICE))
    out["sigma"] = best
    print(json.dumps(out))
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")


def interrupt_check(net, R, E, w, unf, other, dev):
    """Ben, 14:49 UTC: work between messages must be interruptible at any time. For the first INTERRUPT_N unfinished
    puzzles: run KEEP and GUESS straight, and again with PAUSES pauses at fixed rounds; at each pause the worker's state
    goes to the CPU, a message is answered (the day pass on another puzzle), and the state comes back. Identical =
    every round's predictions and stop values (KEEP) and every result (GUESS) match the straight run, and every message
    answer matches the message answered with no worker running. Wait = the longest round plus the longest pause."""
    pauses = set(random.Random(INTERRUPT_SEED).sample(range(1, DOWN), PAUSES))
    base = day_pass(net, R, E, [other], dev)
    same_msg = []

    def message():
        same_msg.append(day_pass(net, R, E, [other], dev) == base)

    items = unf[:INTERRUPT_N]
    P0, Q0 = rounds_batch(net, R, items, DOWN, dev)
    tk = {}
    P1, Q1 = rounds_batch(net, R, items, DOWN, dev, pauses=pauses, message=message, timing=tk)
    g_same, g_paused, step, pause = 0, 0, tk["step"], tk["pause"]
    for it in items:
        a, _ = w.guess(it)
        b, tg = w.guess(it, pauses=pauses, message=message)
        g_same += a == b
        g_paused += tg["pauses"] > 0
        step, pause = max(step, tg["step"]), max(pause, tg["pause"])
    return {"n": len(items), "pause_rounds": sorted(pauses), "keep_identical": P0 == P1 and Q0 == Q1,
            "keep_pauses": tk["pauses"], "guess_identical": g_same, "guess_puzzles_paused": g_paused,
            "messages": len(same_msg), "messages_identical": sum(same_msg),
            "max_round_sec": round(step, 4), "max_pause_sec": round(pause, 4), "max_wait_sec": round(step + pause, 4),
            "device": dev}


def run(a):
    _, R, E = mods()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    items = load(R, a.day, [d[0] for d in DAY])
    w = Worker(net, E, dev)
    res = {"ckpt": str(a.ckpt), "sha256": V.sha256(a.ckpt), "sigma": a.sigma, "device": dev, "sets": {}}
    finds = []
    for name, env, *_ in DAY:
        t0 = time.time()
        d = day_pass(net, R, E, items[name], dev)
        idx = [i for i, r in enumerate(d) if not r["right"]]
        unf = [items[name][i] for i in idx]
        rec = {"n": len(d), "day_right": sum(r["right"] for r in d), "unfinished": len(unf),
               "day_right_any_round": sum(r["any_round"] is not None for r in d)}
        k = keep(net, R, E, unf, dev)
        rs = restart(net, R, E, unf, dev, a.sigma, f"test|{name}")
        g = [w.guess(it)[0] for it in unf]
        # hard = unfinished puzzles where no round of the day's 48 was accepted (the marks count these only)
        hard = [d[i]["any_round"] is None for i in idx]
        rec["hard"] = sum(hard)
        rec["keep"] = {"solved": sum(r is not None for r, _ in k),
                       "solved_by_48": sum(r is not None and r <= DAY_ROUNDS for r, _ in k),
                       "solved_after_48": sum(r is not None and r > DAY_ROUNDS for r, _ in k),
                       "hard_solved": sum(r is not None and hd for (r, _), hd in zip(k, hard))}
        rec["restart"] = {"solved": sum(r is not None for r, _ in rs),
                          "hard_solved": sum(r is not None and hd for (r, _), hd in zip(rs, hard))}
        rec["guess" if env == "grids" else "guess_transfer_report_only"] = {
            "solved": sum(x["solved"] for x in g), "solved_by_48": sum(x["solved"] and x["rounds"] <= DAY_ROUNDS for x in g),
            "hard_solved": sum(x["solved"] and hd for x, hd in zip(g, hard)), "guesses": sum(x["guesses"] for x in g)}
        for i, (kr, ka), (rr, ra), gx in zip(idx, k, rs, g):
            for arm, r, ans in (("keep", kr, ka), ("restart", rr, ra), ("guess", gx["rounds"] if gx["solved"] else None,
                                                                         gx["answer"])):
                if r is not None:
                    ans = clean(items[name][i], ans)
                    assert E.check(items[name][i], ans)
                    finds.append({"set": name, "idx": i, "arm": arm, "round": r, "answer": ans})
        if name == "grids7":
            rec["interrupt"] = interrupt_check(net, R, E, w, unf, items[name][0], dev)
        rec["sec"] = round(time.time() - t0)
        res["sets"][name] = rec
        print(name, json.dumps(rec), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    Path(a.out).with_suffix(".finds.jsonl").write_text("".join(json.dumps(f) + "\n" for f in finds))


def selftest(a):
    """On practice grids only: the pausable GUESS worker gives exactly rv-387's sealed GUESS (claude_rv387.Runner, arm
    'guess') at DOWN rounds, and the interrupt check runs."""
    _, R, E = mods()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    its = load(R, a.day, ["p-grids7"])["p-grids7"]
    d = day_pass(net, R, E, its, dev)
    unf = [it for it, r in zip(its, d) if not r["right"]][:a.n]
    w, old = Worker(net, E, dev), V.Runner(net, E, dev)
    same = 0
    for it in unf:
        x, _ = w.guess(it)
        y = old.solve(it, "guess", budget=DOWN)
        same += all(x[k] == y[k] for k in ("solved", "rounds", "guesses", "q"))
    out = {"n": len(unf), "guess_same_as_rv387": same, "interrupt": interrupt_check(net, R, E, w, unf, its[0], dev)}
    print(json.dumps(out))
    if a.out:
        Path(a.out + ".selftest.json").write_text(json.dumps(out, indent=1) + "\n")
    assert same == len(unf), "the worker differs from rv-387's GUESS"


def all_steps(a):
    """for one net: selftest, then sigma from practice grids, then the run with that sigma (outputs <out>.*.json)."""
    base = a.out
    selftest(a)
    a.out = base + ".sigma.json"
    pick_sigma(a)
    a.sigma = json.loads(Path(a.out).read_text())["sigma"]
    a.out = base + ".json"
    run(a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["make-day", "pick-sigma", "run", "selftest", "all"])
    ap.add_argument("--out", default="")
    ap.add_argument("--day", default=str(ROOT / "artifacts/claude-rv390-20260926/day"))
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--sigma", type=float, default=0.3)
    ap.add_argument("--n", type=int, default=30)
    a = ap.parse_args()
    {"make-day": make_day, "pick-sigma": pick_sigma, "run": run, "selftest": selftest, "all": all_steps}[a.cmd](a)


if __name__ == "__main__":
    main()
