#!/usr/bin/env python3
"""rd-371b: run the rd-378 note writer over dialogs, greedy plus optional sampled drafts (for checker training data).

python claude_rd371b_sample.py --model DIR --dialogs D.jsonl --out OUT.jsonl [--samples 1] [--temp 0.8] [--seed 371]
OUT rows {"dialog","t","draft":"greedy"|"s1".., "notes":[...] or null, "raw", "ms"}. Prints counts only.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_rd378_common import build_nprompt, parse_notes  # noqa: E402
from claude_rd378_write import NoteWriter  # noqa: E402
from claude_rd371b_common import windows  # noqa: E402


@torch.no_grad()
def sample(w, kind, date, earlier, latest, temp):
    t0 = time.perf_counter()
    p = w.tok(build_nprompt(kind, date, earlier, latest), add_special_tokens=False)["input_ids"]
    if w.tok.bos_token_id is not None:
        p = [w.tok.bos_token_id] + p
    ids = torch.tensor([p], device=w.dev)
    out = w.model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=w.max_new, do_sample=True,
                           temperature=temp, top_p=0.95, pad_token_id=w.tok.eos_token_id)
    raw = w.tok.decode(out[0, len(p):], skip_special_tokens=True)
    return parse_notes(raw), raw, (time.perf_counter() - t0) * 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dialogs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=0)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--seed", type=int, default=371)
    a = ap.parse_args()
    torch.manual_seed(a.seed)
    w = NoteWriter(a.model)
    n = notes = unparsed = 0
    with open(a.out, "w", encoding="utf-8") as fh:
        for line in Path(a.dialogs).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            for t, earlier, latest in windows(d):
                runs = [("greedy", w.write(d["kind"], d.get("date", ""), earlier, latest))]
                for s in range(a.samples):
                    runs.append((f"s{s + 1}", sample(w, d["kind"], d.get("date", ""), earlier, latest, a.temp)))
                for tag, (nt, raw, ms) in runs:
                    fh.write(json.dumps({"dialog": d["dialog"], "t": t, "draft": tag, "notes": nt, "raw": raw,
                                         "ms": round(ms, 1)}, ensure_ascii=False) + "\n")
                    n += 1
                    notes += len(nt or [])
                    unparsed += nt is None
    print(json.dumps({"drafts": n, "notes": notes, "unparsed": unparsed, "device": w.dev}))


if __name__ == "__main__":
    main()
