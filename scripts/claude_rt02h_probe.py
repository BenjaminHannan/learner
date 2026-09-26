#!/usr/bin/env python3
"""rt-02h step 2 (Plain-English puzzles thread, 2026-09-26; marks artifacts/claude-rt02h-20260926/PASSMARKS-rt02h.md): a small yes/no head on
the plain 1B's inner state decides "is this message asking for a number puzzle?"; the 1B then copies out the numbers
and target (rt-02g's V1 forced reading, 156 of 159 exact on practice).

Features: the 1B (every LoRA scale 0) reads a zero-shot yes/no question about the message; the hidden state of the last
prompt token at several layers is the feature. Head: logistic regression (standardised, L2), trained ONLY on the 1B's
own code-labelled drafts (scripts/claude_rt02h_drafts.py). Layer, L2 and cut are picked by 5-fold cross-validation over
draft prompts (all samples of one prompt stay in one fold); the cut is the lowest one whose held-out drafts fire on at
most 1% of negatives. rt-02d's dev set and the blind agent's practice set are used ONLY to report, never to pick.
Never reads any TEST panel.

  python -B scripts/claude_rt02h_probe.py feats --model BASE --drafts D.jsonl --out FEATS.pt
  python -B scripts/claude_rt02h_probe.py fit --feats FEATS.pt --v1 artifacts/claude-rt02g-20260926/dev/margins_V1.jsonl \
      --head artifacts/claude-rt02h-20260926/head.pt
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ASK = ("Message: {text}\n\nQuestion: is this person asking you to solve a number puzzle, that is, to find a way to "
       "combine the numbers they give with + - * / so that the result is a target number they name? Answer yes or no.")
LAYERS = [6, 9, 12, 15, 18, 21, 24]


def features(one_b, text: str, layers=LAYERS):
    """Hidden state of the last prompt token of ASK at each layer (every LoRA scale 0 during the call)."""
    import claude_sleep02c as SL
    tok, model, torch = one_b.tok, one_b.model, one_b.torch
    prompt = tok.apply_chat_template([{"role": "user", "content": ASK.format(text=text)}], tokenize=False,
                                     add_generation_prompt=True, enable_thinking=False)
    ids = tok(prompt, return_tensors="pt").to(one_b.dev)
    mods = SL.lora_mods(model)
    saved = [x.scale for x in mods]
    for x in mods:
        x.scale = 0.0
    try:
        with torch.no_grad():
            hs = model(**ids, output_hidden_states=True).hidden_states
    finally:
        for x, sc in zip(mods, saved):
            x.scale = sc
    return torch.stack([hs[l][0, -1].float().cpu() for l in layers])


def load_head(path):
    import torch
    return torch.load(path)


def head_score(head, feat_all_layers) -> float:
    x = feat_all_layers[head["layer_index"]]
    return float(((x - head["mu"]) / head["sd"]) @ head["w"] + head["b"])


def feats(a) -> None:
    import torch
    import claude_rt02g as G
    one_b = G.load_one_b(a.model)
    items = []                                           # (source, group, label or None, text, extra)
    for r in (json.loads(x) for x in Path(a.drafts).read_text().splitlines()):
        if r["keep"]:
            items.append(("draft", r["pi"], int(r["kind"] == "pos"), r["text"], None))
    for k, (src, text, want) in enumerate(G.dev_sets()):
        if G.pre_gate(text):
            items.append((src, k, int(want is not None), text, want))
    X = []
    for i, (_, _, _, text, _) in enumerate(items):
        X.append(features(one_b, text))
        if i % 50 == 0:
            print(i, len(items), flush=True)
    torch.save({"X": torch.stack(X), "meta": [(s, g, y, w) for s, g, y, _, w in items],
                "texts": [t for *_, t, _ in items]}, a.out)


def _fit(X, y, l2, steps=300):
    import torch
    mu, sd = X.mean(0), X.std(0) + 1e-4
    Z = (X - mu) / sd
    w = torch.zeros(Z.shape[1], requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([w, b], max_iter=steps, line_search_fn="strong_wolfe")
    yt = y.float()

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(Z @ w + b, yt) + l2 * (w * w).sum()
        loss.backward()
        return loss
    opt.step(closure)
    h = lambda Xn: ((Xn - mu) / sd) @ w.detach() + b.detach()
    h.params = {"mu": mu, "sd": sd, "w": w.detach().clone(), "b": float(b.detach())}
    return h


def fit(a) -> None:
    import torch
    d = torch.load(a.feats)
    X, meta = d["X"], d["meta"]
    tr = [i for i, m in enumerate(meta) if m[0] == "draft"]
    ev = [i for i, m in enumerate(meta) if m[0] != "draft"]
    y = torch.tensor([meta[i][2] for i in tr])
    groups = sorted({meta[i][1] for i in tr})
    fold = {g: k % 5 for k, g in enumerate(groups)}
    print(f"drafts: {len(tr)} ({int(y.sum())} pos), report items: {len(ev)}")
    best = None
    for li, layer in enumerate(LAYERS):
        for l2 in (1e-3, 1e-2, 1e-1):
            s = torch.zeros(len(tr))
            for f in range(5):
                a_idx = [j for j, i in enumerate(tr) if fold[meta[i][1]] != f]
                b_idx = [j for j, i in enumerate(tr) if fold[meta[i][1]] == f]
                h = _fit(X[tr][a_idx, li], y[a_idx], l2)
                s[b_idx] = h(X[tr][b_idx, li])
            neg = s[y == 0].sort(descending=True).values
            cut = float(neg[max(0, int(0.01 * len(neg)))]) + 1e-6      # held-out drafts fire on <= 1% of negatives
            rec = float(((s >= cut) & (y == 1)).sum() / y.sum())
            print(f"layer {layer:2d} l2 {l2:g}: cv recall at <=1% neg fires {rec:.3f}")
            if best is None or rec > best[0]:
                best = (rec, li, l2, cut)
    rec, li, l2, cut = best
    h = _fit(X[tr][:, li], y, l2)
    if a.head:
        torch.save({**h.params, "layer": LAYERS[li], "layer_index": li, "l2": l2, "cut": cut, "cv_recall": rec,
                    "n_drafts": len(tr), "n_pos": int(y.sum())}, a.head)
    se = h(X[ev][:, li])
    v1 = {r["k"]: r for r in (json.loads(x) for x in Path(a.v1).read_text().splitlines())}
    out = {}
    for j, i in enumerate(ev):
        src, k, lab, want = meta[i]
        key = f"{src}_{'puzzle' if lab else 'negative'}"
        o = out.setdefault(key, {"n": 0, "fire": 0, "exact": 0})
        on = bool(se[j] >= cut) and v1[k]["got"] is not None
        o["n"] += 1
        o["fire"] += int(on)
        o["exact"] += int(on and v1[k]["got"] == want)
    print(json.dumps({"layer": LAYERS[li], "l2": l2, "cv_recall": round(rec, 3), "cut": round(cut, 3), "report": out}))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["feats", "fit"])
    ap.add_argument("--model", default="")
    ap.add_argument("--drafts", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--feats", default="")
    ap.add_argument("--v1", default="")
    ap.add_argument("--head", default="")
    a = ap.parse_args()
    {"feats": feats, "fit": fit}[a.cmd](a)


if __name__ == "__main__":
    main()
