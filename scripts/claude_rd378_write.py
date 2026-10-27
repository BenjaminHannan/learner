#!/usr/bin/env python3
"""rd-378 note writer: run the note LoRA (merged) over dialogs, one call per non-assistant turn (greedy).

Library:  w = NoteWriter(model_dir); notes, raw, ms = w.write(kind, date, earlier_turns, latest_turn)
CLI:      python claude_rd378_write.py --model DIR --dialogs DIALOGS.jsonl --out NOTES.jsonl
          DIALOGS rows {"dialog","kind","speakers","date","turns":[{"t","speaker","text"}]};
          OUT rows {"dialog","t","notes":[{"text","cites","when"}] or null (unparsed),"raw","ms"}.
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
from claude_rd378_common import build_nprompt, parse_notes  # noqa: E402


class NoteWriter:
    def __init__(self, model_dir, device=None, max_new_tokens=300):
        self.dev = device or ("cuda" if torch.cuda.is_available() else
                              "mps" if torch.backends.mps.is_available() else "cpu")
        dtype = torch.float32 if self.dev == "cpu" else torch.bfloat16 if self.dev == "cuda" else torch.float16
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=dtype).to(self.dev).eval()
        self.max_new = max_new_tokens

    @torch.no_grad()
    def write(self, kind, date, earlier, latest):
        t0 = time.perf_counter()
        p = self.tok(build_nprompt(kind, date, earlier, latest), add_special_tokens=False)["input_ids"]
        if self.tok.bos_token_id is not None:
            p = [self.tok.bos_token_id] + p
        ids = torch.tensor([p], device=self.dev)
        out = self.model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=self.max_new,
                                  do_sample=False, pad_token_id=self.tok.eos_token_id)
        raw = self.tok.decode(out[0, len(p):], skip_special_tokens=True)
        return parse_notes(raw), raw, (time.perf_counter() - t0) * 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dialogs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    w = NoteWriter(a.model)
    n = 0
    with open(a.out, "w", encoding="utf-8") as fh:
        for line in Path(a.dialogs).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            for k, t in enumerate(d["turns"]):
                if d["kind"] == "chat" and t["speaker"] == "assistant":
                    continue
                notes, raw, ms = w.write(d["kind"], d.get("date", ""), d["turns"][:k], t)
                fh.write(json.dumps({"dialog": d["dialog"], "t": t["t"], "notes": notes, "raw": raw,
                                     "ms": round(ms, 1)}, ensure_ascii=False) + "\n")
                n += 1
    print("wrote notes for", n, "turns on", w.dev)


if __name__ == "__main__":
    main()
