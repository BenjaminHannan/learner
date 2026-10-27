#!/usr/bin/env python3
"""y1r: a trained retriever for the memory store (Answering-from-memory thread, 2026-09-26). New file.
Plan and marks: artifacts/claude-y1r-20260926/PLAN.md.

bm-398d (bb265e4a9) showed that on LoCoMo the plain 1B reading only the right lines scores 137/297 (Qwen3.5-2B on the
whole chat: 138), while the store's top 20 gives 88: finding the lines is a large loss. The store (scripts/
claude_ep382_store_v2.py) ranks with the off-the-shelf MiniLM-L6-v2 fused with BM25; nothing in it was ever trained
on finding the line that answers a question. The textbook fix is a retriever trained on question-to-evidence pairs.
The one change here: the MiniLM weights inside the store's fused ranking. BM25, the fusion, the key text
('<speaker> said, "<text>"'), the store and the harness stay as they are.

Practice pairs, no LoCoMo and no Claude text: y1t's GLM practice items (code chose every fact, GLM wrote every word,
lis-320's check kept the turns, y1t's data gate checked the labels). For each answerable item and its never-told twin,
the positives are the earlier turns that carry a fact on the asked (owner, relation): the answerable item's turns
minus the twin's turns (build_items removes exactly those). The negatives are the twin's turns: the same chat's other
turns. Turns are keyed as the store keys them, with the speaker "User".

Training (CPU): the stack's MiniLM through fable_bert_loader (fable_self122_train.load_encoder), mean-pooled and
normalised as the store embeds, multi-positive InfoNCE over each batch (a query against its own positives, up to 7
of its own chat's negatives, and every other query's turns), temperature 0.05, AdamW lr 2e-5, weight decay 0.01,
batch 16, 2 epochs, seed 4035. Held-out practice-dev (y1t's items_dev): positive-at-1 before and after (report).

  python -B scripts/claude_y1r_retriever.py pairs --items ITEMS.jsonl --out PAIRS.jsonl
  python -B scripts/claude_y1r_retriever.py train --pairs PAIRS.jsonl --dev DEV_PAIRS.jsonl --out DIR
      -> DIR/encoder.pt (weights: never pushed), DIR/train.json (counts)
  python -B scripts/claude_y1r_retriever.py locomo --data DATA --out OUT [--encoder DIR/encoder.pt]
      -> bm-393b's run (store v2, recall k=20, fused/minilm/bm25) with the MiniLM swapped when --encoder is given
  python -B scripts/claude_y1r_retriever.py --selftest
Prints counts only.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SEED = 4035
TAU, LR, WD, BATCH, EPOCHS, MAX_NEG = 0.05, 2e-5, 0.01, 16, 2, 7
SPEAKER = "User"


def load(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def key(text: str) -> str:
    import claude_ep382_store_v2 as M2
    return M2._key_text({"speaker": SPEAKER, "text": text})


def pairs(items: list[dict]) -> tuple[list[dict], dict]:
    twins = {(it["dialog_id"], it["k"]): it for it in items if it["kind"] == "never_told"}
    out, c = [], {"answerable": 0, "no_twin": 0, "no_positive": 0, "no_negative": 0}
    for it in items:
        if it["kind"] != "answerable":
            continue
        c["answerable"] += 1
        t = twins.get((it["dialog_id"], it["k"]))
        if t is None:
            c["no_twin"] += 1
            continue
        keep = {r["id"] for r in t["rows"]}
        pos = [key(r["text"]) for r in it["rows"] if r["id"] not in keep]
        neg = [key(r["text"]) for r in it["rows"] if r["id"] in keep]
        if not pos:
            c["no_positive"] += 1
            continue
        c["no_negative"] += not neg
        out.append({"dialog_id": it["dialog_id"], "k": it["k"], "query": it["question"], "pos": pos, "neg": neg})
    c["pairs"] = len(out)
    return out, c


def info_nce(q, d, posmask, tau: float = TAU):
    """Multi-positive InfoNCE: -log(sum over positives / sum over all), mean over queries."""
    import torch
    s = q @ d.T / tau
    pos = s.masked_fill(~posmask, float("-inf"))
    return (torch.logsumexp(s, 1) - torch.logsumexp(pos, 1)).mean()


def _embed(enc, tok, texts: list[str], max_len: int = 128):
    import torch.nn.functional as F
    ids, mask, _ = tok.batch(texts, max_len)
    h = enc(ids, mask)
    m = mask.unsqueeze(-1).float()
    return F.normalize((h * m).sum(1) / m.sum(1).clamp_min(1e-6), dim=1)


def batch_tensors(batch: list[dict], rng: random.Random):
    import torch
    docs = []
    for p in batch:
        docs += p["pos"] + rng.sample(p["neg"], min(MAX_NEG, len(p["neg"])))
    docs = list(dict.fromkeys(docs))               # a turn shown once; it is positive for every query it answers
    posmask = torch.tensor([[d in set(p["pos"]) for d in docs] for p in batch])
    return docs, posmask


def pos_at_1(enc, tok, prs: list[dict]) -> dict:
    """Practice-dev: does a positive rank first among that chat's turns (MiniLM cosine alone)?"""
    import torch
    hit = 0
    with torch.no_grad():
        for p in prs:
            docs = p["pos"] + p["neg"]
            s = _embed(enc, tok, [p["query"]]) @ _embed(enc, tok, docs).T
            hit += int(s[0].argmax()) < len(p["pos"])
    return {"n": len(prs), "pos_at_1": hit}


def train(prs: list[dict], dev: list[dict], out: Path, epochs: int = EPOCHS, seed: int = SEED, log=print) -> dict:
    import torch
    import fable_self122_train as T
    torch.manual_seed(seed)
    rng = random.Random(seed)
    enc, tok, info = T.load_encoder(T.resolve_snapshot(None))
    res = {"pairs": len(prs), "dev_pairs": len(dev), "params": info["params"],
           "recipe": {"tau": TAU, "lr": LR, "wd": WD, "batch": BATCH, "epochs": epochs, "max_neg": MAX_NEG,
                      "seed": seed}}
    enc.eval()
    res["dev_before"] = pos_at_1(enc, tok, dev)
    log(json.dumps({"dev_before": res["dev_before"]}))
    opt = torch.optim.AdamW(enc.parameters(), lr=LR, weight_decay=WD)
    losses, t0 = [], time.time()
    for ep in range(epochs):
        order = list(range(len(prs)))
        rng.shuffle(order)
        enc.train()
        for i in range(0, len(order), BATCH):
            b = [prs[j] for j in order[i:i + BATCH]]
            docs, posmask = batch_tensors(b, rng)
            loss = info_nce(_embed(enc, tok, [p["query"] for p in b]), _embed(enc, tok, docs), posmask)
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(loss.item())
            if len(losses) % 20 == 1:
                log(json.dumps({"epoch": ep, "step": len(losses), "loss": round(losses[-1], 4),
                                "s": round(time.time() - t0)}))
    enc.eval()
    res["steps"] = len(losses)
    res["loss_first10"] = round(sum(losses[:10]) / max(1, len(losses[:10])), 4)
    res["loss_last10"] = round(sum(losses[-10:]) / max(1, len(losses[-10:])), 4)
    res["train_seconds"] = round(time.time() - t0, 1)
    res["dev_after"] = pos_at_1(enc, tok, dev)
    out.mkdir(parents=True, exist_ok=True)
    torch.save(enc.state_dict(), out / "encoder.pt")
    (out / "train.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    log(json.dumps({k: res[k] for k in ("steps", "loss_first10", "loss_last10", "dev_before", "dev_after",
                                        "train_seconds")}))
    return res


def locomo(data: str, out: str, encoder: str = "") -> int:
    import torch
    import claude_bm393b_store_recall as R
    import claude_ep382_store_v2 as M2
    if encoder:
        import fable_self122_train as T
        enc, tok, _ = T.load_encoder(T.resolve_snapshot(None))
        enc.load_state_dict(torch.load(encoder, map_location="cpu"))
        M2._ENC.update(enc=enc.eval(), tok=tok)
    R.M = M2
    return R.run(Path(data), Path(out))


def selftest() -> None:
    import torch
    import claude_y1t_data as Y1T
    fr = lambda act, facts=(), ask=None: {"act": act, "facts": list(facts), "ask": ask}  # noqa: E731
    fa = lambda o, rel, v, mode="ASSERT", **kw: {"owner": o, "rel": rel, "value": v, "mode": mode, **kw}  # noqa: E731
    seeds = [{"dialog_id": "d1", "turns": [
        {"k": 1, "intent": "smalltalk", "gold": fr("CHAT")},
        {"k": 2, "intent": "teach", "gold": fr("TELL", [fa("Mira", "dog", "Rolo")])},
        {"k": 3, "intent": "correct", "gold": fr("TELL", [fa("Mira", "dog", "Tansy", "CORRECT", old="Rolo")])},
        {"k": 4, "intent": "teach", "gold": fr("TELL", [fa("me", "city", "Varno")])},
        {"k": 5, "intent": "ask", "gold": fr("ASK", [], {"owner": "Mira", "rel": "dog", "inverse": False})}]}]
    kept = [{"id": "glm320-d1-t1", "turn": "long day lol"},
            {"id": "glm320-d1-t2", "turn": "my sister Mira got a dog called Rolo"},
            {"id": "glm320-d1-t3", "turn": "wait no mira's dog is Tansy not rolo"},
            {"id": "glm320-d1-t4", "turn": "we moved to Varno last spring"},
            {"id": "glm320-d1-t5", "turn": "whats mira's dog called again"}]
    items, _ = Y1T.build_items(seeds, kept)
    prs, c = pairs(items)
    assert c == {"answerable": 1, "no_twin": 0, "no_positive": 0, "no_negative": 0, "pairs": 1}, c
    p = prs[0]
    assert p["pos"] == [key("my sister Mira got a dog called Rolo"), key("wait no mira's dog is Tansy not rolo")], p
    assert p["neg"] == [key("long day lol"), key("we moved to Varno last spring")], p
    assert p["pos"][0].startswith('User said, "') and p["query"] == "whats mira's dog called again"
    assert pairs([it for it in items if it["kind"] == "answerable"])[1]["no_twin"] == 1
    q = torch.nn.functional.normalize(torch.randn(2, 8), dim=1)
    d = torch.cat([q[:1], q[1:], torch.nn.functional.normalize(torch.randn(3, 8), dim=1)])
    good = info_nce(q, d, torch.tensor([[1, 0, 0, 0, 0], [0, 1, 0, 0, 0]]).bool())
    bad = info_nce(q, d, torch.tensor([[0, 0, 1, 0, 0], [0, 0, 0, 1, 0]]).bool())
    assert float(good) < float(bad), (good, bad)
    both = info_nce(q, d, torch.tensor([[1, 0, 1, 0, 0], [0, 1, 0, 0, 0]]).bool())
    assert float(both) <= float(good) + 1e-6                    # more positives never raise the loss
    b = [{"pos": ["a", "b"], "neg": ["c", "d"]}, {"pos": ["c"], "neg": ["a", "e"]}]
    docs, pm = batch_tensors(b, random.Random(0))
    assert sorted(docs) == ["a", "b", "c", "d", "e"] and len(docs) == 5
    assert [docs[j] for j in range(5) if pm[0, j]] == [x for x in docs if x in ("a", "b")]
    assert [docs[j] for j in range(5) if pm[1, j]] == ["c"]
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("pairs")
    s.add_argument("--items", required=True)
    s.add_argument("--out", required=True)
    t = sub.add_parser("train")
    for k in ("--pairs", "--dev", "--out"):
        t.add_argument(k, required=True)
    lo = sub.add_parser("locomo")
    lo.add_argument("--data", required=True)
    lo.add_argument("--out", required=True)
    lo.add_argument("--encoder", default="")
    a = ap.parse_args()
    if a.cmd == "pairs":
        prs, c = pairs(load(a.items))
        Path(a.out).write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in prs), encoding="utf-8")
        print(json.dumps(c))
    elif a.cmd == "train":
        train(load(a.pairs), load(a.dev), Path(a.out), log=lambda s: print(s, flush=True))
    else:
        sys.exit(locomo(a.data, a.out, a.encoder))


if __name__ == "__main__":
    main()
