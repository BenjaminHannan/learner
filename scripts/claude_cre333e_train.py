#!/usr/bin/env python3
"""333e: train and check the 1B's write_creative tool-call head (creative research thread, 2026-09-24).

  feats  --model DIR --data A.jsonl[,B.jsonl] [--bank DIR --bank-lives 1,..,5] --out F.npz
                                                                  hidden states at the tool-call position, all layers
  fit    --feats F.npz --out head333e.json                        layer by 5-fold CV on TRAIN only, logistic head
  check  --model DIR --head head333e.json [--dev DIR] [--bank DIR --bank-lives 6,..,10]
                                                                  routed counts on DEV data (never the 333 panel)

The prompt is 333e's router prompt (claude_cre333e_agent.router_messages with the write_creative tool). Train data:
artifacts/claude-cre333e-train-20260924 (written blind; label 1 = the user wants something made). numpy only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_cre333e_agent as E  # noqa: E402

LAYERS = [8, 12, 16, 20, 24]


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def model(d):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    class G:
        pass
    g = G()
    g.torch, g.tok = torch, AutoTokenizer.from_pretrained(d, trust_remote_code=True)
    g.dev = "cuda" if torch.cuda.is_available() else "cpu"
    g.model = AutoModelForCausalLM.from_pretrained(d, trust_remote_code=True,          # bf16, as Gen333 on cuda
                                                   dtype=torch.bfloat16).to(g.dev).eval()
    return g


def hidden_all(g, prior, text):
    s = g.tok.apply_chat_template(E.router_messages(prior, text), tools=[E.TOOL333E], tokenize=False,
                                  add_generation_prompt=True, enable_thinking=False)
    ids = g.tok(s, return_tensors="pt").to(g.dev)
    with g.torch.no_grad():
        hs = g.model(**ids, output_hidden_states=True).hidden_states
    return np.stack([hs[k][0, -1].float().cpu().numpy() for k in LAYERS])


def bank_rows(bank, lives):
    rows, prev = [], {}
    for t in load(Path(bank) / "turns.jsonl"):
        pu = prev.setdefault(t["life_id"], [])
        if int(t["life_id"][-2:]) in lives:
            rows.append({"id": f"{t['life_id']}-{t['turn_index']}", "history": pu[-E.ROUTER_HISTORY333E:],
                         "text": t["user_text"], "label": int(t["kind"] == "creative"), "type": "bank_" + t["kind"]})
        pu.append(t["user_text"])
    return rows


def lives_arg(s):
    return {int(x) for x in s.split(",") if x} if s else set()


def feats(a):
    g = model(a.model)
    rows = [r for p in a.data.split(",") if p for r in load(p)]
    if a.bank:
        rows += bank_rows(a.bank, lives_arg(a.bank_lives))
    X = np.stack([hidden_all(g, r["history"], r["text"]) for r in rows])
    y = np.array([int(r["label"]) for r in rows])
    np.savez_compressed(a.out, X=X, y=y, ids=np.array([r["id"] for r in rows]),
                        types=np.array([r.get("type", "") for r in rows]))
    print(f"feats: {X.shape} positives {int(y.sum())}")


def fit_lr(X, y, l2=1.0, iters=400):
    m, s = X.mean(0), X.std(0) + 1e-6
    Z = (X - m) / s
    w, b = np.zeros(Z.shape[1]), 0.0
    for _ in range(iters):                                   # gradient descent on mean log loss + l2/n |w|^2
        p = 1 / (1 + np.exp(-(Z @ w + b)))
        gw = Z.T @ (p - y) / len(y) + l2 * w / len(y)
        gb = float((p - y).mean())
        w -= 0.5 * gw
        b -= 0.5 * gb
    return {"w": w, "b": b, "mean": m, "std": s}


def predict(h, X):
    return 1 / (1 + np.exp(-(((X - h["mean"]) / h["std"]) @ h["w"] + h["b"])))


def fit(a):
    d = np.load(a.feats)
    X, y = d["X"], d["y"]
    rng = np.random.default_rng(333)
    fold = rng.permutation(len(y)) % 5
    best = None
    for li, L in enumerate(LAYERS):
        tp = fp = fn = tn = 0
        for k in range(5):
            h = fit_lr(X[fold != k, li], y[fold != k])
            p = predict(h, X[fold == k, li]) >= 0.5
            t = y[fold == k] == 1
            tp += int((p & t).sum()); fn += int((~p & t).sum()); fp += int((p & ~t).sum()); tn += int((~p & ~t).sum())
        bal = (tp / (tp + fn) + tn / (tn + fp)) / 2
        print(f"layer {L}: CV recall {tp}/{tp + fn}, false calls {fp}/{fp + tn}, balanced {bal:.3f}")
        if best is None or bal > best[0]:
            best = (bal, li, L)
    _, li, L = best
    h = fit_lr(X[:, li], y)
    out = {"layer": L, "threshold": 0.5, "b": float(h["b"]), "w": h["w"].tolist(), "mean": h["mean"].tolist(),
           "std": h["std"].tolist(), "train": str(a.feats), "n": int(len(y)), "cv_balanced": round(best[0], 4)}
    Path(a.out).write_text(json.dumps(out), encoding="utf-8")
    print(f"head: layer {L}, CV balanced {best[0]:.3f} -> {a.out}")


def check(a):
    g = model(a.model)
    r = E.Router333e(g, a.head)
    res = {}
    if a.dev:
        items = load(Path(a.dev) / "items.jsonl")
        per = {}
        for it in items:
            call, p = r.calls_tool(it["turns"], it["last"])
            per.setdefault(it["kind"], [0, 0])
            per[it["kind"]][0] += int(call)
            per[it["kind"]][1] += 1
            if a.verbose:
                print(f"{it['item_id']} {it['kind']} p={p:.3f} call={call}")
        res["dev"] = {k: f"{v[0]}/{v[1]} called" for k, v in per.items()}
    if a.bank:
        per = {}
        for t in bank_rows(a.bank, lives_arg(a.bank_lives) or set(range(1, 11))):
            call, _p = r.calls_tool(t["history"], t["text"])
            k = t["type"]
            per.setdefault(k, [0, 0])
            per[k][0] += int(call)
            per[k][1] += 1
        res["bank"] = {k: f"{v[0]}/{v[1]} called" for k, v in per.items()}
    print(json.dumps(res, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["feats", "fit", "check"])
    ap.add_argument("--model", default="")
    ap.add_argument("--data", default="")
    ap.add_argument("--feats", default="")
    ap.add_argument("--head", default="")
    ap.add_argument("--dev", default="")
    ap.add_argument("--bank", default="")
    ap.add_argument("--bank-lives", default="", help="comma list of DEV-bank life numbers, e.g. 1,2,3,4,5")
    ap.add_argument("--out", default="")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    {"feats": feats, "fit": fit, "check": check}[a.cmd](a)


if __name__ == "__main__":
    main()
