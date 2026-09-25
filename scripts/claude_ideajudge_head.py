#!/usr/bin/env python3
"""A trained idea judge on the 1B's own hidden state (creative research thread, 2026-09-25; DEV only).

Why: the 1B's own yes/no judgement picked a good idea on 2/10 DEV requests (RESULTS-selfjudge.md). The teacher
z-ai/glm-5.3 (open weights) agreed with the blind Opus judges on 256/300 blurts (kappa 0.568), passing the rule for a
label source. So: label the blurts of the 30 DEV requests that have NO Opus labels with the teacher, train a small
logistic head on the 1B's hidden state at the end of the judging prompt, and test it once on the 10 requests the Opus
judges labelled (the teacher's labels for those 10 are never used here).

  python -B scripts/claude_ideajudge_head.py --model M --dev artifacts/claude-cre333e-dev-20260924 \
     --blurts artifacts/claude-blurt1-dev-20260925/run/ideas_t10.jsonl \
     --teacher artifacts/claude-blurt2-20260925/teacher-glm53/labels_teacher.jsonl \
     --labels artifacts/claude-blurt1-dev-20260925/labels/labels0.jsonl,artifacts/claude-blurt1-dev-20260925/labels/labels1.jsonl \
     --out artifacts/claude-blurt2-20260925/ideahead
Layer and regularisation are chosen by 5-fold cross-validation grouped by request, on the 30 training requests only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_blurt_selfjudge import JUDGE, load  # noqa: E402
from claude_cre333e_train import fit_lr, predict  # noqa: E402

LAYERS = [8, 12, 16, 20, 24]
L2S = [1.0, 30.0, 300.0]


def auc(pos, neg):
    return sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / max(1, len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--blurts", required=True)
    ap.add_argument("--teacher", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    opus = {(x["item_id"], x["n"]): x["good"] for p in a.labels.split(",") for x in load(p)}
    test_items = {k[0] for k in opus}
    teach = {(x["item_id"], x["n"]): x["good"] for x in load(a.teacher) if x["item_id"] not in test_items}
    items = {it["item_id"]: it for it in load(Path(a.dev) / "items.jsonl")}
    blurts = {r["item_id"]: r["blurts"] for r in load(a.blurts)}
    keys = sorted(teach) + sorted(opus)
    fp = out / "feats.npz"
    if fp.exists():
        X = np.load(fp)["X"]
    else:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        m = AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, dtype=torch.bfloat16).to(dev).eval()
        X = []
        for i, (iid, n) in enumerate(keys):
            it = items[iid]
            msg = JUDGE.format(chat="\n".join("- " + t for t in it["turns"]), req=it["last"], idea=blurts[iid][n])
            s = tok.apply_chat_template([{"role": "user", "content": msg}], tokenize=False, add_generation_prompt=True,
                                        enable_thinking=False)
            ids = tok(s, return_tensors="pt").to(dev)
            with torch.no_grad():
                hs = m(**ids, output_hidden_states=True).hidden_states
            X.append(np.stack([hs[k][0, -1].float().cpu().numpy() for k in LAYERS]))
            if i % 100 == 0:
                print(f"[feats] {i}/{len(keys)}", flush=True)
        X = np.stack(X)
        np.savez_compressed(fp, X=X)
    ntr = len(teach)
    Xtr, ytr = X[:ntr], np.array([float(teach[k]) for k in keys[:ntr]])
    Xte, yte = X[ntr:], np.array([opus[k] for k in keys[ntr:]])
    groups = sorted({k[0] for k in keys[:ntr]})
    fold = np.array([groups.index(k[0]) % 5 for k in keys[:ntr]])
    cv = {}
    for li, L in enumerate(LAYERS):
        for l2 in L2S:
            sc = np.zeros(ntr)
            for f in range(5):
                h = fit_lr(Xtr[fold != f, li], ytr[fold != f], l2=l2)
                sc[fold == f] = predict(h, Xtr[fold == f, li])
            cv[(L, l2)] = auc(sc[ytr == 1].tolist(), sc[ytr == 0].tolist())
            print(f"[cv] layer {L} l2 {l2}: AUC vs teacher {cv[(L, l2)]:.3f}", flush=True)
    L, l2 = max(cv, key=cv.get)
    li = LAYERS.index(L)
    h = fit_lr(Xtr[:, li], ytr, l2=l2)
    p = predict(h, Xte[:, li])
    per = {}
    for (iid, n), s, g in zip(keys[ntr:], p, yte):
        per.setdefault(iid, []).append((float(s), bool(g)))
    pick = sum(max(rs)[1] for rs in per.values())
    top3 = sum(any(g for _, g in sorted(rs, reverse=True)[:3]) for rs in per.values())
    rep = {"train_requests": len(groups), "train_blurts": ntr, "train_teacher_good": int(ytr.sum()),
           "layer": L, "l2": l2, "cv_auc_vs_teacher": round(cv[(L, l2)], 3),
           "test_requests": len(per), "test_blurts": len(yte), "test_opus_good": int(yte.sum()),
           "test_auc_vs_opus": round(auc(p[yte].tolist(), p[~yte].tolist()), 3),
           "pick1_good": pick, "top3_has_good": top3,
           "oracle_any_good": sum(any(g for _, g in rs) for rs in per.values())}
    (out / "head.json").write_text(json.dumps({"layer": L, "l2": l2, "b": float(h["b"]), "w": h["w"].tolist(),
                                               "mean": h["mean"].tolist(), "std": h["std"].tolist()}),
                                   encoding="utf-8")
    (out / "result.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
