#!/usr/bin/env python3
"""lis-317 (report only): what does the lis-301 reader read before any gate?

For every row it records
  - the greedy read exactly as the live stack sees it (claude_lis300_read.Reader.read):
    frame, confs (lis-300 min-token confidence per fact), raw text;
  - the greedy tokens with their probabilities (so other confidence rules can be tried on CPU);
  - K sampled reads (temperature --temp, same prompt) as parsed frames, for an agreement check:
    does the same fact come back when the reader is asked again?
No gate, compiler, notebook or agent is run. Sealed lis-300/301 code is imported, never edited.

Usage (GPU): python -B scripts/claude_lis317_sample.py --model READER --rows ROWS.jsonl --out OUT.jsonl --k 8
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_common import build_prompt, parse_frame  # noqa: E402
from claude_lis300_read import Reader  # noqa: E402


@torch.no_grad()
def greedy_tokens(r: Reader, turn, prev):
    p = r.tok(build_prompt(turn, prev), add_special_tokens=False)["input_ids"]
    if r.tok.bos_token_id is not None:
        p = [r.tok.bos_token_id] + p
    ids = torch.tensor([p], device=r.dev)
    out = r.model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=r.max_new,
                           do_sample=False, output_scores=True, return_dict_in_generate=True,
                           eos_token_id=r.tok.eos_token_id, pad_token_id=r.tok.eos_token_id,
                           stop_strings=["<END>"], tokenizer=r.tok)
    gen = out.sequences[0, ids.shape[1]:].tolist()
    probs = [torch.softmax(s[0].float(), -1)[t].item() for s, t in zip(out.scores, gen)]
    return [[r.tok.decode([t]), round(pr, 6)] for t, pr in zip(gen, probs)], ids


@torch.no_grad()
def samples(r: Reader, ids, k, temp, seed):
    torch.manual_seed(seed)
    out = r.model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=r.max_new,
                           do_sample=True, temperature=temp, top_p=1.0, top_k=0, num_return_sequences=k,
                           eos_token_id=r.tok.eos_token_id, pad_token_id=r.tok.eos_token_id,
                           stop_strings=["<END>"], tokenizer=r.tok)
    texts = [r.tok.decode(s[ids.shape[1]:], skip_special_tokens=True) for s in out]
    return [parse_frame(t) for t in texts]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--temp", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=317)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-tokens", action="store_true", help="skip the greedy token list (keeps big files < 5 MB)")
    a = ap.parse_args()
    r = Reader(a.model)
    rows = [json.loads(x) for x in Path(a.rows).read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = rows[: a.limit] if a.limit else rows
    done = set()
    outp = Path(a.out)
    if outp.exists():                       # resume after an ssh drop
        done = {json.loads(x)["id"] for x in outp.read_text(encoding="utf-8").splitlines() if x.strip()}
    with open(outp, "a", encoding="utf-8") as fh:
        for n, row in enumerate(rows):
            if row["id"] in done:
                continue
            t0 = time.perf_counter()
            fr, cf, raw, ms = r.read(row["turn"], row.get("prev_reply", ""))
            toks, ids = greedy_tokens(r, row["turn"], row.get("prev_reply", ""))
            smp = samples(r, ids, a.k, a.temp, a.seed + n)
            fh.write(json.dumps({"id": row["id"], "frame": fr, "conf": cf, "raw": raw, "ms_read": round(ms, 1),
                                 "tokens": None if a.no_tokens else toks, "samples": smp,
                                 "ms_total": round((time.perf_counter() - t0) * 1000, 1)},
                                ensure_ascii=False) + "\n")
            fh.flush()
            if n % 50 == 0:
                print(f"[317] {n}/{len(rows)}", flush=True)
    print("done", len(rows), "rows on", r.dev)


if __name__ == "__main__":
    main()
