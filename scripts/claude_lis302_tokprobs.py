#!/usr/bin/env python3
"""lis-302 field-level confidence census, GPU part: teacher-forced token probabilities of the
reader's OWN greedy output (the saved raw text), one forward pass per row, no generation.

python scripts/claude_lis302_tokprobs.py --model MERGED --rows DEV_ROWS --pred DEV_PRED --out tokprobs.jsonl
Each output row: {"id", "tokens": [[char_start, char_end, prob], ...], "check_minp": float}
check_minp re-derives lis-300's per-row minimum over the whole output as a sanity check.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_common import build_prompt  # noqa: E402


def load(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.bfloat16 if dev == "cuda" else torch.float16 if dev == "mps" else torch.float32
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=dtype).to(dev).eval()
    rows = {r["id"]: r for r in load(a.rows)}
    with open(a.out, "w", encoding="utf-8") as fh:
        for p in load(a.pred):
            r = rows[p["id"]]
            pr = tok(build_prompt(r["turn"], r.get("prev_reply", "")), add_special_tokens=False)["input_ids"]
            if tok.bos_token_id is not None:
                pr = [tok.bos_token_id] + pr
            gen = tok(p["raw"], add_special_tokens=False)["input_ids"]
            ids = torch.tensor([pr + gen], device=dev)
            logits = model(ids).logits[0, len(pr) - 1:-1].float()
            probs = torch.softmax(logits, -1)[torch.arange(len(gen)), torch.tensor(gen, device=dev)].tolist()
            spans, prev_len = [], 0
            for n in range(1, len(gen) + 1):
                e = len(tok.decode(gen[:n], skip_special_tokens=True))
                spans.append([prev_len, e, round(probs[n - 1], 6)])
                prev_len = e
            fh.write(json.dumps({"id": p["id"], "tokens": spans,
                                 "check_minp": round(min(probs), 6) if probs else None}) + "\n")
    print("done on", dev)


if __name__ == "__main__":
    main()
