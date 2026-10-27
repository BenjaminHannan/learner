#!/usr/bin/env python3
"""lis-300 reader: the fine-tuned MiniCPM5-1B listener, with a confidence per fact.

Confidence of fact i = the lowest probability the model gave any token it emitted inside
the turn's "act" value or inside fact i's JSON object (greedy decoding). The compiler asks
back when this is below the threshold fixed on dev.

Library:  r = Reader(model_dir); frame, confs, raw, ms = r.read(turn, prev_reply)
CLI:      python claude_lis300_read.py --model DIR --rows ROWS.jsonl --out OUT.jsonl
          ROWS rows need {"id","turn","prev_reply"}; OUT rows = {"id","frame","conf","raw","ms"}.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_common import build_prompt, parse_frame  # noqa: E402


def object_spans(text: str):
    """Char spans of the act value and of each object inside the facts array."""
    act = None
    i = text.find('"act"')
    if i >= 0:
        j = text.find(",", i)
        act = (i, j if j > 0 else len(text))
    facts = []
    k = text.find('"facts"')
    if k >= 0:
        k = text.find("[", k)
        depth, start, instr, esc = 0, None, False, False
        for p in range(k + 1, len(text)):
            ch = text[p]
            if instr:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    instr = False
                continue
            if ch == '"':
                instr = True
            elif ch == "{":
                if depth == 0:
                    start = p
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    facts.append((start, p + 1))
            elif ch == "]" and depth == 0:
                break
    return act, facts


class Reader:
    def __init__(self, model_dir, device=None, max_new_tokens=200):
        self.dev = device or ("cuda" if torch.cuda.is_available() else
                              "mps" if torch.backends.mps.is_available() else "cpu")
        dtype = torch.float32 if self.dev == "cpu" else torch.bfloat16 if self.dev == "cuda" else torch.float16
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=dtype).to(self.dev).eval()
        self.max_new = max_new_tokens

    @torch.no_grad()
    def read(self, turn, prev_reply=""):
        t0 = time.perf_counter()
        p = self.tok(build_prompt(turn, prev_reply), add_special_tokens=False)["input_ids"]
        if self.tok.bos_token_id is not None:
            p = [self.tok.bos_token_id] + p
        ids = torch.tensor([p], device=self.dev)
        out = self.model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=self.max_new,
                                  do_sample=False, output_scores=True, return_dict_in_generate=True,
                                  eos_token_id=self.tok.eos_token_id, pad_token_id=self.tok.eos_token_id,
                                  stop_strings=["<END>"], tokenizer=self.tok)
        gen = out.sequences[0, ids.shape[1]:].tolist()
        probs = [torch.softmax(s[0].float(), -1)[t].item() for s, t in zip(out.scores, gen)]
        # char offset where each generated token ends
        ends, text = [], ""
        for n in range(1, len(gen) + 1):
            text = self.tok.decode(gen[:n], skip_special_tokens=True)
            ends.append(len(text))
        starts = [0] + ends[:-1]
        frame = parse_frame(text)
        act, fspans = object_spans(text)

        def minp(spans):
            vals = [pr for s, e, pr in zip(starts, ends, probs)
                    if any(s < b and e > a for a, b in spans if a is not None)]
            return min(vals) if vals else 0.0
        confs = [minp([act, fs] if act else [fs]) for fs in fspans]
        ms = (time.perf_counter() - t0) * 1000
        return frame, confs, text, ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    r = Reader(a.model)
    rows = [json.loads(l) for l in Path(a.rows).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = rows[: a.limit] if a.limit else rows
    with open(a.out, "w", encoding="utf-8") as fh:
        for row in rows:
            fr, cf, raw, ms = r.read(row["turn"], row.get("prev_reply", ""))
            fh.write(json.dumps({"id": row["id"], "frame": fr, "conf": cf, "raw": raw,
                                 "ms": round(ms, 1)}, ensure_ascii=False) + "\n")
    print("read", len(rows), "rows on", r.dev)


if __name__ == "__main__":
    main()
