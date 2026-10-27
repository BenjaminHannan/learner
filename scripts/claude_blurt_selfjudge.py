#!/usr/bin/env python3
"""Can the 1B pick its own good idea blurts? (creative research thread, 2026-09-25; DEV only)

Scores every labelled idea blurt with MiniCPM5-1B's own yes/no judgement (thinking off):
  P(yes) from the first-token logits of "Yes" vs "No" after a short judging prompt.
Compares with blind Opus labels (good / invented) from the blurt-1 idea run. Reports AUC, and per request whether the
top-scored blurt is good (pick@1) against the chance rate and an oracle (any good blurt among the 30).

  python -B scripts/claude_blurt_selfjudge.py --model M --dev DEVDIR --blurts ideas_t10.jsonl --labels L0,L1 --out F
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

JUDGE = ("A user asked a personal assistant for help. Earlier messages from the user:\n{chat}\n\nRequest: {req}\n\n"
         "Proposed idea: {idea}\n\nIs this proposed idea specific, sensible and useful for this exact request? "
         "Answer Yes or No.")


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--blurts", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, dtype=torch.bfloat16).to(dev).eval()
    yes = [tok.encode(w, add_special_tokens=False)[0] for w in ("Yes", " Yes", "yes")]
    no = [tok.encode(w, add_special_tokens=False)[0] for w in ("No", " No", "no")]
    items = {it["item_id"]: it for it in load(Path(a.dev) / "items.jsonl")}
    blurts = {r["item_id"]: r["blurts"] for r in load(a.blurts)}
    labels = [x for p in a.labels.split(",") for x in load(p)]
    rows = []
    for lab in labels:
        it, idea = items[lab["item_id"]], blurts[lab["item_id"]][lab["n"]]
        msg = JUDGE.format(chat="\n".join("- " + t for t in it["turns"]), req=it["last"], idea=idea)
        s = tok.apply_chat_template([{"role": "user", "content": msg}], tokenize=False, add_generation_prompt=True,
                                    enable_thinking=False)
        ids = tok(s, return_tensors="pt").to(dev)
        with torch.no_grad():
            lg = m(**ids).logits[0, -1].float()
        py = torch.logsumexp(lg[yes], 0) - torch.logsumexp(torch.stack([torch.logsumexp(lg[yes], 0),
                                                                          torch.logsumexp(lg[no], 0)]), 0)
        rows.append({**lab, "p_yes": round(float(py.exp()), 4)})
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    pos = [r["p_yes"] for r in rows if r["good"]]
    neg = [r["p_yes"] for r in rows if not r["good"]]
    auc = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / max(1, len(pos) * len(neg))
    per, pick, chance, oracle = {}, 0, 0.0, 0
    for r in rows:
        per.setdefault(r["item_id"], []).append(r)
    for rs in per.values():
        top = max(rs, key=lambda r: r["p_yes"])
        pick += int(top["good"])
        chance += sum(r["good"] for r in rs) / len(rs)
        oracle += int(any(r["good"] for r in rs))
    print(json.dumps({"blurts": len(rows), "good": len(pos), "auc_self_judge": round(auc, 3), "items": len(per),
                      "pick1_self_judge": pick, "pick1_chance_expected": round(chance, 2), "oracle_any_good": oracle}))


if __name__ == "__main__":
    main()
