#!/usr/bin/env python3
"""rd-371b sentence checker: P(yes) that the conversation window states a note.

Library:  c = Checker(model_dir); p = c.p_yes(kind, date, earlier, latest, sentence)
CLI:      python claude_rd371b_check.py --model DIR --notes-in JUDGE_IN.jsonl --out PRED.jsonl
          JUDGE_IN = dialogs whose non-assistant turns carry "notes"; PRED rows {"dialog","t","k","p_yes","ms"}.
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
from claude_rd371b_common import build_sprompt, windows  # noqa: E402


class Checker:
    def __init__(self, model_dir, device=None):
        self.dev = device or ("cuda" if torch.cuda.is_available() else
                              "mps" if torch.backends.mps.is_available() else "cpu")
        dtype = torch.float32 if self.dev == "cpu" else torch.bfloat16 if self.dev == "cuda" else torch.float16
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=dtype).to(self.dev).eval()
        self.yes = self.tok("yes", add_special_tokens=False)["input_ids"][0]
        self.no = self.tok("no", add_special_tokens=False)["input_ids"][0]

    @torch.no_grad()
    def p_yes(self, kind, date, earlier, latest, sentence):
        p = self.tok(build_sprompt(kind, date, earlier, latest, sentence), add_special_tokens=False)["input_ids"]
        if self.tok.bos_token_id is not None:
            p = [self.tok.bos_token_id] + p
        ids = torch.tensor([p], device=self.dev)
        logits = self.model(input_ids=ids, attention_mask=torch.ones_like(ids)).logits[0, -1].float()
        return float(torch.softmax(torch.stack([logits[self.yes], logits[self.no]]), dim=0)[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--notes-in", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    c = Checker(a.model)
    n = 0
    with open(a.out, "w", encoding="utf-8") as fh:
        for line in Path(a.notes_in).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            for t, earlier, latest in windows(d):
                for k, note in enumerate(latest.get("notes") or []):
                    t0 = time.perf_counter()
                    p = c.p_yes(d["kind"], d.get("date", ""), earlier, latest, note["text"])
                    fh.write(json.dumps({"dialog": d["dialog"], "t": t, "k": k, "p_yes": p,
                                         "ms": round((time.perf_counter() - t0) * 1000, 1)}) + "\n")
                    n += 1
    print(json.dumps({"notes_checked": n, "device": c.dev}))


if __name__ == "__main__":
    main()
