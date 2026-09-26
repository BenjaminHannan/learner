#!/usr/bin/env python3
"""rv-391 DEV 2 (thought-memory thread, 2026-09-26): can a small learned critic, reading the frozen loop net's own state,
tell a page that can no longer be finished from one that still can? Unregistered probe. It trains on fresh code-made
TRAINING puzzles and is checked on rv-390's PRACTICE puzzles. No test puzzle is touched. The net is never changed.

Why: rv-391 dev (NOTE-dev-result.md) found no untrained signal from the net that marks a wrong written guess, and 368 of
720 unsolved practice 7x7 puzzles were ruined by one wrong guess. The textbook fix for going back inside a search is a
learned critic (a value net, as in AlphaZero or Tree of Thoughts) trained on the states the search itself visits, with
outcome labels. Brain first: the anterior cingulate's error signal and dopamine prediction errors, both learned from
outcomes (textbook; the mapping to this net is a guess). Plan and marks: artifacts/claude-rv391-20260926/NOTE-critic-plan.md.

States: rv-387's GUESS (the rv-390 worker's rule: every 8th round while q < 0.5, write the net's surest-but-unsure
symbol; never go back) runs 96 rounds on each puzzle the day pass left unfinished. At every check round with at least
one written guess, before any new guess, it records the state:
  features  mean of h over the puzzle's answer cells, mean of h over the written cells, and q   (2 x width + 1 numbers)
  dead      1 if any written guess differs from the puzzle's one solution, else 0 (checked by code; a bare 0/1 target)
  k         how many guesses are written (the count-only baseline)
Critic: logistic regression on standardised features, fixed settings (Adam, lr 0.01, 400 full-batch steps, weight decay
1e-4), trained per net on its own training states, fp32 on CPU, no autocast. Nothing is tuned on practice states.

  python -B scripts/claude_rv391_critic.py make-train --out artifacts/claude-rv391-20260926/critic/train
  python -B scripts/claude_rv391_critic.py probe --ckpt F --out DIR/critic-sN.json
"""
from __future__ import annotations

import argparse
import bisect
import json
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import claude_rv390 as W  # noqa: E402

V = W.V
TRAIN = [("t-grids7", "grids", 7, 39311), ("t-grids6", "grids", 6, 39312)]
N_TRAIN = 1000
PRACTICE = ["p-grids7", "p-grids6"]
RV390_DAY = ROOT / "artifacts/claude-rv390-20260926/day"
TRAIN_DIR = ROOT / "artifacts/claude-rv391-20260926/critic/train"
RESERVED = [W.RESERVED_TEST_DIR, RV390_DAY, ROOT / "artifacts/claude-rv392-20260926/day"]
ROUNDS = 96
FLAG_LIVE = 0.20          # the cut flags at most this share of live TRAINING states


def make_train(a):
    _, R, E = W.mods()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    reserved = set()
    for d in RESERVED:
        for f in sorted(Path(d).glob("*.jsonl")):
            for line in f.read_text().splitlines():
                reserved.add(json.dumps(json.loads(line)["tokens"]))
    report = {"reserved_items": len(reserved)}
    for name, env, size, seed in TRAIN:
        items = W.make_items(E, env, size, seed, N_TRAIN)
        clash = sum(json.dumps(i.tokens) in reserved for i in items)
        items = [i for i in items if json.dumps(i.tokens) not in reserved]
        (out / f"{name}.jsonl").write_text("".join(json.dumps(R.item_to_json(i)) + "\n" for i in items))
        report[name] = {"seed": seed, "kept": len(items), "clash_with_tests_day_or_practice": clash}
        print(name, report[name])
    (out / "make-train.json").write_text(json.dumps(report, indent=1) + "\n")


@torch.no_grad()
def states(w, it, rounds=ROUNDS):
    """rv-387's GUESS on one puzzle, recording (features, dead, k) at each check round with a written guess."""
    E, net = w.E, w.net
    names = [E.SYM + n for n in it.meta["names"]]
    Wd = len(it.tokens[0])
    ans = torch.tensor([r * Wd + c for r, row in enumerate(it.slot) for c, v in enumerate(row) if v == 1])
    page = W.AnyPage(it, E)
    e, (dr, dc) = w.embed(page)
    h = torch.zeros_like(e)
    out, since = [], 0
    for _ in range(rounds):
        h = net.step(h, e, dr, dc)
        lg, qq = net.read(h)
        q = float(torch.sigmoid(qq.float())[0])
        if E.check(it, w.final(page, lg[0].argmax(-1).tolist())):
            break
        since += 1
        if since < V.CHECK_EVERY:
            continue
        since = 0
        if page.written:
            wr = torch.tensor([r * Wd + c for r, c in page.written])
            hf = h[0].float().cpu()
            feat = torch.cat([hf[ans].mean(0), hf[wr].mean(0), torch.tensor([q])])
            dead = int(any(tok != it.target[r][c] for (r, c), tok in page.written.items()))
            out.append((feat, dead, len(page.written)))
        if q >= V.CUT:
            continue
        cell, cands = w.pick(page, lg[0], names)
        if cell is None:
            continue
        page.write(*cell, cands[0])
        e, (dr, dc) = w.embed(page)
    return out


def collect(w, net, R, E, items, dev):
    d = W.day_pass(net, R, E, items, dev)
    unf = [it for it, r in zip(items, d) if not r["right"]]
    X, y, k, where = [], [], [], []
    for i, it in enumerate(unf):
        for f, dd, kk in states(w, it):
            X.append(f)
            y.append(dd)
            k.append(kk)
            where.append(i)
    X = torch.stack(X) if X else torch.zeros(0, 1)
    return {"unfinished": len(unf), "X": X, "y": y, "k": k, "item": where}


def auc(pos, neg):
    """P(a dead state's score > a live state's), ties count half."""
    if not pos or not neg:
        return None
    ns = sorted(neg)
    tot = 0.0
    for x in pos:
        lo, hi = bisect.bisect_left(ns, x), bisect.bisect_right(ns, x)
        tot += lo + 0.5 * (hi - lo)
    return round(tot / (len(pos) * len(ns)), 4)


def fit(X, y):
    torch.manual_seed(0)
    mu, sd = X.mean(0), X.std(0).clamp_min(1e-6)
    Z = (X - mu) / sd
    lin = torch.nn.Linear(Z.shape[1], 1)
    opt = torch.optim.Adam(lin.parameters(), lr=0.01, weight_decay=1e-4)
    t = torch.tensor(y, dtype=torch.float32)
    for _ in range(400):
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(lin(Z).squeeze(1), t)
        loss.backward()
        opt.step()
    return lambda A: lin(((A - mu) / sd)).squeeze(1).detach(), loss.item()


def split(scores, y):
    return [s for s, d in zip(scores, y) if d], [s for s, d in zip(scores, y) if not d]


def probe(a):
    _, R, E = W.mods()
    dev = "cpu"                                  # fp32, no autocast
    net = R.load(a.ckpt, dev).eval()
    w = W.Worker(net, E, dev)
    res = {"ckpt": str(a.ckpt), "sha256": V.sha256(a.ckpt), "torch": torch.__version__, "rounds": ROUNDS, "sets": {}}
    t0 = time.time()
    tr = W.load(R, a.train, [t[0] for t in TRAIN])
    data = {n: collect(w, net, R, E, its, dev) for n, its in tr.items()}
    pr = W.load(R, RV390_DAY, PRACTICE)
    data.update({n: collect(w, net, R, E, its, dev) for n, its in pr.items()})
    Xtr = torch.cat([data[n]["X"] for n, *_ in TRAIN if len(data[n]["y"])])
    ytr = sum((data[n]["y"] for n, *_ in TRAIN), [])
    score, loss = fit(Xtr, ytr)
    s_tr = score(Xtr).tolist()
    dead_tr, live_tr = split(s_tr, ytr)
    cut = sorted(live_tr)[int((1 - FLAG_LIVE) * (len(live_tr) - 1))] if live_tr else None
    res["train"] = {"states": len(ytr), "dead": sum(ytr), "loss": round(loss, 4), "auc": auc(dead_tr, live_tr),
                    "cut": cut}
    rows = []
    for n in [t[0] for t in TRAIN] + PRACTICE:
        dd = data[n]
        rec = {"unfinished": dd["unfinished"], "states": len(dd["y"]), "dead": sum(dd["y"])}
        if dd["y"]:
            s = score(dd["X"]).tolist()
            pos, neg = split(s, dd["y"])
            kp, kn = split([float(x) for x in dd["k"]], dd["y"])
            rec.update(auc=auc(pos, neg), auc_count_only=auc(kp, kn),
                       dead_flagged=sum(x > cut for x in pos), live_flagged=sum(x > cut for x in neg))
            if n in PRACTICE:
                rows += [{"set": n, "item": i, "k": kk, "dead": d, "score": round(x, 5)}
                         for i, kk, d, x in zip(dd["item"], dd["k"], dd["y"], s)]
        res["sets"][n] = rec
        print(n, json.dumps(rec), flush=True)
    res["sec"] = round(time.time() - t0)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    Path(a.out).with_suffix(".rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["make-train", "probe"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--train", default=str(TRAIN_DIR))
    a = ap.parse_args()
    {"make-train": make_train, "probe": probe}[a.cmd](a)


if __name__ == "__main__":
    main()
