#!/usr/bin/env python3
"""gram-362 critic training (training prompts only; never a test panel).

  features: python -B scripts/claude_gram362_train.py feats DRAFTS.jsonl GEN_MODEL OUT.pt
  train:    python -B scripts/claude_gram362_train.py train DRAFTS.jsonl LABELS.jsonl OUT.pt HEAD.json
DRAFTS.jsonl rows: {pid, j, user_text, draft}; LABELS.jsonl rows: {key: "<pid>/<j>", ok: bool} from blind Opus
graders. Training: logistic regression (full-batch, L2) on standardised features; the L2 strength is chosen by
5-fold cross-validation grouped by prompt (all 4 drafts of a prompt stay in one fold), then refit on everything.
Prints cross-validated AUC and pick accuracy (how often the top-scored draft of a prompt is clean vs the first draft).
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))


def ld(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def feats(drafts: str, model_dir: str, out: str) -> None:
    import torch

    import claude_chat338_agent as C38
    import claude_cre333b_agent as C333B
    import claude_gram362 as G
    one_b = C333B.Gen333b(model_dir)
    rows = ld(drafts)
    xs, keys = [], []
    for i, r in enumerate(rows):
        msgs = [{"role": "system", "content": C38.SYSTEM338}, {"role": "user", "content": r["user_text"]}]
        xs.append(G.critic_features(one_b, msgs, r["draft"]))
        keys.append(f"{r['pid']}/{r['j']}")
        if i % 100 == 0:
            print(i, flush=True)
    torch.save({"keys": keys, "x": torch.stack(xs)}, out)


def stats(drafts: str, model_dir: str, out: str) -> None:
    """Token-probability and shape features (G.STATS362) for every draft, same context as feats."""
    import torch

    import claude_chat338_agent as C38
    import claude_cre333b_agent as C333B
    import claude_gram362 as G
    one_b = C333B.Gen333b(model_dir)
    xs, keys = [], []
    for i, r in enumerate(ld(drafts)):
        msgs = [{"role": "system", "content": C38.SYSTEM338}, {"role": "user", "content": r["user_text"]}]
        xs.append(G.critic_stats(one_b, msgs, r["draft"]))
        keys.append(f"{r['pid']}/{r['j']}")
        if i % 100 == 0:
            print(i, flush=True)
    torch.save({"keys": keys, "x": torch.stack(xs)}, out)


def auc(scores, ys) -> float:
    pos = [s for s, y in zip(scores, ys) if y]
    neg = [s for s, y in zip(scores, ys) if not y]
    if not pos or not neg:
        return float("nan")
    return sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / (len(pos) * len(neg))


def fit(x, y, l2: float, steps: int = 400):
    import torch
    w = torch.zeros(x.shape[1], requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([w, b], max_iter=steps, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(x @ w + b, y) + l2 * (w * w).sum()
        loss.backward()
        return loss
    opt.step(closure)
    return w.detach(), float(b.detach())


def train(drafts: str, labels: str, feat_path: str, head_out: str) -> None:
    import torch
    fs = [torch.load(fp) for fp in feat_path.split(",")]         # several feature files are joined side by side
    assert all(g["keys"] == fs[0]["keys"] for g in fs)
    f = {"keys": fs[0]["keys"], "x": torch.cat([g["x"].float() for g in fs], dim=1)}
    lab = {r["key"]: bool(r["ok"]) for r in ld(labels)}
    idx = [i for i, k in enumerate(f["keys"]) if k in lab]
    keys = [f["keys"][i] for i in idx]
    x = f["x"][idx].float()
    y = torch.tensor([1.0 if lab[k] else 0.0 for k in keys])
    pids = sorted({k.split("/")[0] for k in keys})
    random.Random(3621).shuffle(pids)
    fold = {p: i % 5 for i, p in enumerate(pids)}
    fk = torch.tensor([fold[k.split("/")[0]] for k in keys])
    best = None
    for l2 in (1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0):
        sc = torch.zeros(len(keys))
        for k in range(5):
            tr, te = fk != k, fk == k
            mu, sd = x[tr].mean(0), x[tr].std(0) + 1e-6
            w, b = fit((x[tr] - mu) / sd, y[tr], l2)
            sc[te] = torch.sigmoid(((x[te] - mu) / sd) @ w + b)
        a = auc(sc.tolist(), y.tolist())
        # pick: top-scored draft per prompt clean, vs draft 0 clean
        byp: dict = {}
        for s, k, yy in zip(sc.tolist(), keys, y.tolist()):
            byp.setdefault(k.split("/")[0], []).append((s, k.split("/")[1], yy))
        top = sum(max(v)[2] for v in byp.values())
        first = sum(dict((j, yy) for _s, j, yy in v).get("0", 0) for v in byp.values())
        anyc = sum(1 for v in byp.values() if any(yy for _s, _j, yy in v))
        print(json.dumps({"l2": l2, "cv_auc": round(a, 3), "prompts": len(byp), "top_clean": top,
                          "first_clean": first, "any_clean": anyc}))
        if best is None or a > best[0]:
            best = (a, l2)
    mu, sd = x.mean(0), x.std(0) + 1e-6
    w, b = fit((x - mu) / sd, y, best[1])
    Path(head_out).parent.mkdir(parents=True, exist_ok=True)
    Path(head_out).write_text(json.dumps({"mu": mu.tolist(), "sd": sd.tolist(), "w": w.tolist(), "b": b,
                                          "l2": best[1], "cv_auc": best[0], "n": len(keys),
                                          "features": [Path(fp).stem for fp in feat_path.split(",")],
                                          "clean": int(y.sum())}), encoding="utf-8")
    print(json.dumps({"chosen_l2": best[1], "cv_auc": round(best[0], 3), "n": len(keys), "clean": int(y.sum())}))


if __name__ == "__main__":
    if sys.argv[1] == "feats":
        feats(*sys.argv[2:5])
    elif sys.argv[1] == "stats":
        stats(*sys.argv[2:5])
    else:
        train(*sys.argv[2:6])
