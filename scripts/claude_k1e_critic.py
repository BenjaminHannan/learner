#!/usr/bin/env python3
"""k1e DEV pilot: a small learned critic picks among the creative writer's 4 drafts (Creative answers in chat thread,
2026-09-26). Readable practice data only. Not a registered run.

Why: on DEV the 1B could not tell its useful drafts apart when asked cold (k1c's P 15 of 40, k1d's listener 14, first
draft 12, any draft 26; artifacts/claude-k1d-20260926/PILOT-k1d.md). Brain picture (textbook-level, mapping guessed):
the value of a reply is learned from how listeners respond, not read off by a fixed rule. Here the 1B stays frozen and
reads each draft through k1d's listener prompt; only a linear head on that reading is trained, on blind judges'
useful yes/no for the 1B's own drafts on a separate practice set (never DEV, never a test panel).

Fixed before any critic score was computed:
  features  the 1B's hidden state at the last prompt position of k1d's listener chat (claude_k1d_pilot.listen_msgs,
            the writer's template, thinking off), from layer num_layers // 2 and from the last layer, concatenated.
  head      logistic regression on standardized features, L2 strength picked from {1e-3, 1e-2, 1e-1, 1, 10} by
            5-fold cross-validation over practice chats (all drafts of a chat in one fold), by mean log-loss; then
            fitted on all practice drafts. Full-batch LBFGS, 200 steps, no random draws except the fold split (seed 4555).
  pick      among the drafts that pass the guards, the highest critic probability; ties keep draw order.
DEV check: goes forward only if the pick beats P (15 of 40) on DEV.

  python -B scripts/claude_k1c_pilot.py samples --form W1 --items TRAIN/items.jsonl --model M --out TRN --seed 4222
  python -B scripts/claude_k1c_pilot.py packets --items TRAIN/items.jsonl --out TRN        (blind judges on packet)
  python -B scripts/claude_k1e_critic.py feats --items I --samples S/samples.jsonl --model M --out F.pt
  python -B scripts/claude_k1e_critic.py train --feats TRN_F.pt --samples TRN/samples.jsonl --verdicts TV.json --out H.pt
  python -B scripts/claude_k1e_critic.py eval  --feats DEV_F.pt --samples DEV/samples.jsonl --verdicts DV.json \
      --head H.pt [--pmi DEV/pmi.jsonl]
  python -B scripts/claude_k1e_critic.py --selftest
Verdict files map "item_id<TAB>draft text" -> true/false (useful).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

L2S = (1e-3, 1e-2, 1e-1, 1.0, 10.0)
FOLDS, FOLD_SEED = 5, 4555


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def feats(a):
    import torch
    import claude_chat338_agent as C38
    import claude_cre333b_agent as CB
    import claude_k1d_pilot as KD
    g = CB.Gen333b(a.model)
    gen = C38.Gen338(share=g)
    items = {it["item_id"]: it for it in load(a.items)}
    keys, rows = [], []
    for r in load(a.samples):
        t0 = time.time()
        it = items[r["item_id"]]
        for k, s in enumerate(r["samples"]):
            if s["guard"] is not None:
                continue
            ids = g.tok(gen._render(KD.listen_msgs(it["turns"], it["last"], s["trimmed"])),
                        return_tensors="pt")["input_ids"].to(g.dev)
            with torch.no_grad():
                hs = g.model(input_ids=ids, output_hidden_states=True).hidden_states
            mid = len(hs) // 2
            rows.append(torch.cat([hs[mid][0, -1].float(), hs[-1][0, -1].float()]).cpu())
            keys.append([r["item_id"], k])
        print(f"[k1e-feats] {r['item_id']} {time.time() - t0:.0f}s", flush=True)
    torch.save({"keys": keys, "X": torch.stack(rows), "layers": "mid+last"}, a.out)


def labels_for(keys, samples, verdicts):
    text = {(r["item_id"], k): s["trimmed"] for r in samples for k, s in enumerate(r["samples"])}
    ys = [verdicts.get(f"{i}\t{text[(i, k)]}") for i, k in keys]
    return ys


def fit(X, y, l2):
    import torch
    w = torch.zeros(X.shape[1], requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([w, b], max_iter=200, line_search_fn="strong_wolfe")
    yt = torch.tensor(y, dtype=torch.float32)

    def closure():
        opt.zero_grad()
        z = X @ w + b
        loss = torch.nn.functional.binary_cross_entropy_with_logits(z, yt) + l2 * (w @ w) / 2
        loss.backward()
        return loss
    opt.step(closure)
    return w.detach(), b.detach()


def logloss(X, y, w, b):
    import torch
    z = X @ w + b
    return float(torch.nn.functional.binary_cross_entropy_with_logits(z, torch.tensor(y, dtype=torch.float32)))


def train(a):
    import torch
    d = torch.load(a.feats)
    ys = labels_for(d["keys"], load(a.samples), json.loads(Path(a.verdicts).read_text(encoding="utf-8")))
    keep = [n for n, v in enumerate(ys) if v is not None]
    X = d["X"][keep]
    y = [float(bool(ys[n])) for n in keep]
    groups = [d["keys"][n][0] for n in keep]
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Xs = (X - mu) / sd
    chats = sorted(set(groups))
    random.Random(FOLD_SEED).shuffle(chats)
    fold = {c: n % FOLDS for n, c in enumerate(chats)}
    cv = {}
    for l2 in L2S:
        losses = []
        for f in range(FOLDS):
            tr = [n for n, g in enumerate(groups) if fold[g] != f]
            te = [n for n, g in enumerate(groups) if fold[g] == f]
            w, b = fit(Xs[tr], [y[n] for n in tr], l2)
            losses.append(logloss(Xs[te], [y[n] for n in te], w, b))
        cv[l2] = sum(losses) / len(losses)
    best = min(L2S, key=lambda l: (cv[l], -l))
    w, b = fit(Xs, y, best)
    torch.save({"w": w, "b": b, "mu": mu, "sd": sd, "l2": best, "cv": cv}, a.out)
    print(json.dumps({"drafts": len(y), "useful": int(sum(y)), "unjudged": len(ys) - len(keep), "chats": len(chats),
                      "cv_logloss": {str(k): round(v, 4) for k, v in cv.items()}, "l2": best}))


def auc(scores, ys):
    pos = [s for s, v in zip(scores, ys) if v]
    neg = [s for s, v in zip(scores, ys) if not v]
    if not pos or not neg:
        return None
    return sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / (len(pos) * len(neg))


def evaluate(a):
    import torch
    d = torch.load(a.feats)
    h = torch.load(a.head)
    prob = torch.sigmoid(((d["X"] - h["mu"]) / h["sd"]) @ h["w"] + h["b"]).tolist()
    pr = {tuple(k): p for k, p in zip(d["keys"], prob)}
    verdict = json.loads(Path(a.verdicts).read_text(encoding="utf-8"))
    pm = {r["item_id"]: r["pmi"] for r in load(a.pmi)} if a.pmi else {}
    res = {"items": 0, "no_passing": 0, "unjudged": 0, "first": 0, "oracle": 0, "critic": 0,
           "critic_gained_vs_first": 0, "critic_lost_vs_first": 0, "critic_picked_not_first": 0}
    if pm:
        res["P"] = 0
    all_s, all_y = [], []
    for r in load(a.samples):
        res["items"] += 1
        ok = [k for k, s in enumerate(r["samples"]) if s["guard"] is None]
        if not ok:
            res["no_passing"] += 1
            continue
        v = [verdict.get(f"{r['item_id']}\t{r['samples'][k]['trimmed']}") for k in ok]
        if any(x is None for x in v):
            res["unjudged"] += 1
            continue
        c = [pr[(r["item_id"], k)] for k in ok]
        all_s += c
        all_y += [bool(x) for x in v]
        j = min(range(len(ok)), key=lambda i: (-c[i], i))
        res["first"] += bool(v[0])
        res["oracle"] += any(v)
        res["critic"] += bool(v[j])
        res["critic_gained_vs_first"] += bool(v[j]) and not v[0]
        res["critic_lost_vs_first"] += bool(v[0]) and not v[j]
        res["critic_picked_not_first"] += j != 0
        if pm:
            p = [pm[r["item_id"]][k] for k in ok]
            res["P"] += bool(v[min(range(len(ok)), key=lambda i: (-p[i], i))])
    au = auc(all_s, all_y)
    res["draft_auc"] = None if au is None else round(au, 3)
    print(json.dumps(res))


def selftest():
    import torch
    ok = 0
    g = torch.Generator().manual_seed(0)
    X = torch.randn(200, 6, generator=g)
    y = [float(x) for x in (X[:, 0] + 0.1 * torch.randn(200, generator=g) > 0).tolist()]
    w, b = fit(X, y, 1e-2)
    assert w[0] > 1 and abs(float(w[1])) < abs(float(w[0])) / 3
    assert logloss(X, y, w, b) < logloss(X, y, torch.zeros(6), torch.zeros(1))
    ok += 1
    assert auc([3, 2, 1], [True, False, False]) == 1.0 and auc([1, 2], [True, False]) == 0.0
    assert auc([1, 1], [True, False]) == 0.5 and auc([1], [True]) is None
    ok += 1
    s = [{"item_id": "a", "samples": [{"trimmed": "x", "guard": None}, {"trimmed": "y", "guard": "G1"}]}]
    assert labels_for([["a", 0], ["a", 1]], s, {"a\tx": True}) == [True, None]
    ok += 1
    print(f"k1e critic selftest {ok}/3 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", choices=["feats", "train", "eval"])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--items", default="")
    ap.add_argument("--samples", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--feats", default="")
    ap.add_argument("--verdicts", default="")
    ap.add_argument("--head", default="")
    ap.add_argument("--pmi", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    {"feats": feats, "train": train, "eval": evaluate}[a.mode](a)


if __name__ == "__main__":
    main()
