#!/usr/bin/env python3
"""rd-371 verifier: P(yes) that the user's turn states a fact, from the verifier LoRA (merged).

Library:  v = Verifier(model_dir); p = v.p_yes(turn, prev_reply, fact)
CLI:      python claude_rd371_verify.py --model DIR --rows ROWS.jsonl --reads READS.jsonl --out OUT.jsonl
          ROWS {"id","turn","prev_reply"}; READS = reader output {"id","frame","conf",...}.
          OUT = READS rows with "conf" replaced by P(yes) per fact (0.0 for a non-dict fact) and the reader's
          min-token confidences kept as "conf_min"; "ms_verify" = time spent verifying that row.
          So any lis-300/318 scorer can gate on the verifier with --threshold.
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
from claude_rd371_common import build_vprompt  # noqa: E402


class Verifier:
    def __init__(self, model_dir, device=None):
        self.dev = device or ("cuda" if torch.cuda.is_available() else
                              "mps" if torch.backends.mps.is_available() else "cpu")
        dtype = torch.float32 if self.dev == "cpu" else torch.bfloat16 if self.dev == "cuda" else torch.float16
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=dtype).to(self.dev).eval()
        self.yes = self.tok("yes", add_special_tokens=False)["input_ids"][0]
        self.no = self.tok("no", add_special_tokens=False)["input_ids"][0]

    @torch.no_grad()
    def p_yes(self, turn, prev_reply, fact):
        p = self.tok(build_vprompt(turn, prev_reply, fact), add_special_tokens=False)["input_ids"]
        if self.tok.bos_token_id is not None:
            p = [self.tok.bos_token_id] + p
        ids = torch.tensor([p], device=self.dev)
        logits = self.model(input_ids=ids, attention_mask=torch.ones_like(ids)).logits[0, -1].float()
        two = torch.softmax(torch.stack([logits[self.yes], logits[self.no]]), dim=0)
        return float(two[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--reads", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    v = Verifier(a.model)
    rows = {r["id"]: r for r in map(json.loads, Path(a.rows).read_text(encoding="utf-8").splitlines()) if r}
    n = 0
    with open(a.out, "w", encoding="utf-8") as fh:
        for line in Path(a.reads).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rd = json.loads(line)
            row = rows[rd["id"]]
            t0 = time.perf_counter()
            fr = rd.get("frame")
            facts = (fr.get("facts") or []) if isinstance(fr, dict) else []
            conf = [v.p_yes(row["turn"], row.get("prev_reply", ""), f) if isinstance(f, dict) else 0.0 for f in facts]
            n += len(facts)
            out = dict(rd, conf=conf, conf_min=rd.get("conf"), ms_verify=round((time.perf_counter() - t0) * 1000, 1))
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
    print("verified", n, "facts on", v.dev)


if __name__ == "__main__":
    main()
