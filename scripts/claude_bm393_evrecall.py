#!/usr/bin/env python3
"""bm-393: evidence recall on LoCoMo practice (benchmarks thread, 2026-09-25). New file only. $0, CPU, no language
model. Development measurement: every number from it is labelled "after using LoCoMo for development"; nothing here
is trained on LoCoMo, and no question, answer or turn text is printed.

LoCoMo marks, for each question, the chat turns that hold its answer ("evidence", dia_id like "D3:7"). For every
question this asks: are those turns among a retriever's top k turns of the same chat?
  R1 bm25:   bm-390's Rb retriever (claude_bm390 tokens, Okapi k1 1.5 b 0.75, same item text, same query text).
  R2 minilm: the stack's frozen MiniLM-L6-v2 (fable_self122_train loader), mean-pooled, cosine, max 128 wordpieces;
             turn text = claude_bm390.turn_text, query = the question as asked in bm-390.
Reports recall_any@k (at least one evidence turn found) and recall_all@k (every evidence turn found) for k 5, 10,
20, per category, and joins Rb's per-question official F1 from bm-390 (score3/per_question.json) to split Rb's score
into "evidence found in its top 10" versus "not found".

  python -B scripts/claude_bm393_evrecall.py --data DATA --score artifacts/claude-bm390-20260925/score3/per_question.json \
      --out artifacts/claude-bm393-20260925
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_bm390 as B  # noqa: E402

KS = (5, 10, 20)
MAX_LEN = 128


def turns_of(conv: dict) -> list[dict]:
    out = []
    for date, turns in B.sessions(conv):
        for t in turns:
            out.append({"id": t.get("dia_id"), "text": B.turn_text(t),
                        "toks": B._toks(t["text"] + " " + t.get("blip_caption", ""))})
    return out


def bm25_rank(items: list[dict], query: str) -> list[int]:
    """Same scoring and tie order as claude_bm390.bm25_context, returning item indices best first."""
    n = len(items)
    avg = sum(len(x["toks"]) for x in items) / max(1, n)
    df = Counter(w for x in items for w in set(x["toks"]))
    q = B._toks(query)
    scored = []
    for i, x in enumerate(items):
        tf = Counter(x["toks"])
        s = 0.0
        for w in q:
            if w not in tf:
                continue
            idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * tf[w] * 2.5 / (tf[w] + 1.5 * (0.25 + 0.75 * len(x["toks"]) / avg))
        scored.append((s, i))
    return [i for _, i in sorted(scored, key=lambda z: (-z[0], z[1]))]


class MiniLM:
    def __init__(self):
        import torch
        import torch.nn.functional as F
        import fable_self122_train as T
        torch.set_num_threads(4)
        self.torch, self.F = torch, F
        self.enc, self.tok, _ = T.load_encoder(T.resolve_snapshot(None))

    def embed(self, texts: list[str]):
        outs = []
        with self.torch.no_grad():
            for i in range(0, len(texts), 64):
                ids, mask, _ = self.tok.batch(texts[i:i + 64], MAX_LEN)
                h = self.enc(ids, mask)
                m = mask.unsqueeze(-1).float()
                outs.append(self.F.normalize((h * m).sum(1) / m.sum(1).clamp_min(1e-6), dim=1))
        return self.torch.cat(outs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--score", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lc = json.loads((Path(a.data) / "locomo10.json").read_text(encoding="utf-8"))
    rb = json.loads(Path(a.score).read_text(encoding="utf-8"))["Rb"]["locomo"]
    ml = MiniLM()
    rows = []
    for conv in lc:
        cid = conv["sample_id"]
        items = turns_of(conv)
        pos = {x["id"]: i for i, x in enumerate(items)}
        emb = ml.embed([x["text"] for x in items])
        qs = [(i, qa) for i, qa in enumerate(conv["qa"])]
        qtexts = [B.question_text(cid, i, qa) for i, qa in qs]
        qemb = ml.embed([qa["question"] for _, qa in qs])
        sims = qemb @ emb.T
        for (i, qa), qt, srow in zip(qs, qtexts, sims):
            ev = [e for e in qa.get("evidence", []) if e in pos]
            r = {"qid": f"{cid}#{i}", "cat": qa["category"], "n_ev": len(ev),
                 "unmatched_ev": len(qa.get("evidence", [])) - len(ev)}
            if ev:
                want = {pos[e] for e in ev}
                ranks = {"bm25": bm25_rank(items, qt), "minilm": srow.argsort(descending=True).tolist()}
                for name, order in ranks.items():
                    for k in KS:
                        top = set(order[:k])
                        r[f"{name}_any@{k}"] = int(bool(want & top))
                        r[f"{name}_all@{k}"] = int(want <= top)
            rows.append(r)
    summary: dict = {}
    for cat in ("1", "2", "3", "4", "1-4", "5"):
        sel = [r for r in rows if (str(r["cat"]) == cat or (cat == "1-4" and r["cat"] in (1, 2, 3, 4))) and r["n_ev"]]
        s = {"questions": len(sel), "no_usable_evidence": sum(1 for r in rows if r["n_ev"] == 0
                                                             and (str(r["cat"]) == cat or (cat == "1-4" and r["cat"] in (1, 2, 3, 4))))}
        for name in ("bm25", "minilm"):
            for k in KS:
                for kind in ("any", "all"):
                    key = f"{name}_{kind}@{k}"
                    s[key] = round(100 * sum(r[key] for r in sel) / max(1, len(sel)), 1)
        summary[cat] = s
    # Rb's official F1 split by whether its retriever had an evidence turn in the top 10 it was shown
    split = {}
    for kind in ("any", "all"):
        found = [rb[r["qid"]]["f1"] for r in rows if r["cat"] in (1, 2, 3, 4) and r["n_ev"] and r[f"bm25_{kind}@10"]]
        miss = [rb[r["qid"]]["f1"] for r in rows if r["cat"] in (1, 2, 3, 4) and r["n_ev"] and not r[f"bm25_{kind}@10"]]
        split[kind] = {"found_n": len(found), "found_f1": round(100 * sum(found) / max(1, len(found)), 2),
                       "missed_n": len(miss), "missed_f1": round(100 * sum(miss) / max(1, len(miss)), 2)}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {"label": "after using LoCoMo for development", "summary": summary, "rb_f1_by_bm25_top10": split,
           "unmatched_evidence_ids": sum(r["unmatched_ev"] for r in rows)}
    (out / "evrecall.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (out / "evrecall_per_question.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"1-4": summary["1-4"]}))
    print(json.dumps({"rb_f1_by_bm25_top10": split}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
