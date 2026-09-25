#!/usr/bin/env python3
"""lis-319 reader: the lis-300 reader code, with the earlier conversation in the prompt.

Library:  r = Reader319(model_dir); frame, confs, raw, ms = r.read(turn, prev_reply, history)
          history = [(user_text, assistant_reply), ...] for earlier turns, oldest first (last 6 used).
          r.read_dialog(pairs) reads a whole day offline (for sleep's night re-read): pairs = [(user_text,
          assistant_reply)]; returns one (frame, confs) per user turn, each read with its own history.
CLI:      python claude_lis319_read.py --model DIR --rows ROWS.jsonl --out OUT.jsonl
          ROWS rows need {"id","turn","prev_reply"} and optionally "history" (list of [user, reply]);
          OUT rows = {"id","frame","conf","raw","ms"} as claude_lis300_read.py writes.
Confidence is computed exactly as lis-300 (min token probability over act + fact JSON).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_common import parse_frame  # noqa: E402
from claude_lis300_read import Reader, object_spans  # noqa: E402
from claude_lis319_common import build_prompt_hist  # noqa: E402


class Reader319(Reader):
    @torch.no_grad()
    def read(self, turn, prev_reply="", history=None):
        t0 = time.perf_counter()
        p = self.tok(build_prompt_hist(turn, prev_reply, history), add_special_tokens=False)["input_ids"]
        if self.tok.bos_token_id is not None:
            p = [self.tok.bos_token_id] + p
        ids = torch.tensor([p], device=self.dev)
        out = self.model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=self.max_new,
                                  do_sample=False, output_scores=True, return_dict_in_generate=True,
                                  eos_token_id=self.tok.eos_token_id, pad_token_id=self.tok.eos_token_id,
                                  stop_strings=["<END>"], tokenizer=self.tok)
        gen = out.sequences[0, ids.shape[1]:].tolist()
        probs = [torch.softmax(s[0].float(), -1)[t].item() for s, t in zip(out.scores, gen)]
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
        return frame, confs, text, (time.perf_counter() - t0) * 1000

    def read_dialog(self, pairs):
        """Offline read of a whole conversation: pairs = [(user_text, assistant_reply_to_it), ...]."""
        out = []
        for k, (u, _a) in enumerate(pairs):
            prev = pairs[k - 1][1] if k > 0 else ""
            fr, cf, _raw, _ms = self.read(u, prev, pairs[:k])
            out.append((fr, cf))
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    r = Reader319(a.model)
    rows = [json.loads(x) for x in Path(a.rows).read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = rows[: a.limit] if a.limit else rows
    with open(a.out, "w", encoding="utf-8") as fh:
        for row in rows:
            fr, cf, raw, ms = r.read(row["turn"], row.get("prev_reply", ""), row.get("history"))
            fh.write(json.dumps({"id": row["id"], "frame": fr, "conf": cf, "raw": raw,
                                 "ms": round(ms, 1)}, ensure_ascii=False) + "\n")
    print("read", len(rows), "rows on", r.dev)


if __name__ == "__main__":
    main()
