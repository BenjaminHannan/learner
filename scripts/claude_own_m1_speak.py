#!/usr/bin/env python3
"""own-M1 mouth: the fine-tuned MiniCPM5-1B speaker with the slot gate.

Library:  m = Mouth(model_dir); text, info = m.say(record, user_turn, tag)
  Tries the greedy reply, then up to --samples sampled replies; the first one that passes
  slot_check is filled and returned. If none passes, returns (None, info) and the caller
  must fall back to the 241b rewriter. info = {"tries", "raw", "problems", "ms"}.
CLI (dev evaluation):
  python claude_own_m1_speak.py --model DIR --data DIR/dev.jsonl --out OUT.jsonl [--limit N]
  prints: rows, spoke, fell back, distinct replies, top reply share, per-status counts, median/p90 ms.
"""
import argparse, collections, json, statistics, sys, time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_own_m1_common import build_prompt, fill, slot_check, slot_values  # noqa: E402


class Mouth:
    def __init__(self, model_dir, device=None, samples=4, max_new_tokens=60, seed=1):
        self.dev = device or ("cuda" if torch.cuda.is_available() else
                              "mps" if torch.backends.mps.is_available() else "cpu")
        dtype = torch.float32 if self.dev == "cpu" else torch.bfloat16 if self.dev == "cuda" else torch.float16
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=dtype).to(self.dev).eval()
        self.samples, self.max_new = samples, max_new_tokens
        torch.manual_seed(seed)

    @torch.no_grad()
    def _gen(self, ids, sample):
        kw = dict(do_sample=True, temperature=0.8, top_p=0.95) if sample else dict(do_sample=False)
        out = self.model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=self.max_new,
                                  eos_token_id=self.tok.eos_token_id, pad_token_id=self.tok.eos_token_id,
                                  stop_strings=["<END>"], tokenizer=self.tok, **kw)
        text = self.tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)
        return text.split("<END>")[0].strip()

    def say(self, record, user_turn, tag):
        t0 = time.perf_counter()
        p = self.tok(build_prompt(record, user_turn, tag), add_special_tokens=False)["input_ids"]
        if self.tok.bos_token_id is not None:
            p = [self.tok.bos_token_id] + p
        ids = torch.tensor([p], device=self.dev)
        raws, probs = [], []
        for i in range(1 + self.samples):
            raw = self._gen(ids, sample=i > 0)
            pr = slot_check(raw, record) if raw else ["empty"]
            raws.append(raw)
            probs.append(pr)
            if not pr:
                ms = (time.perf_counter() - t0) * 1000
                return fill(raw, slot_values(record)), {"tries": i + 1, "raw": raws, "problems": probs, "ms": ms}
        return None, {"tries": len(raws), "raw": raws, "problems": probs,
                      "ms": (time.perf_counter() - t0) * 1000}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--samples", type=int, default=4)
    a = ap.parse_args()
    m = Mouth(a.model, samples=a.samples)
    rows = [json.loads(l) for l in Path(a.data).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = rows[: a.limit] if a.limit else rows
    spoke, fell, first_try, texts, ms = 0, 0, 0, collections.Counter(), []
    per = collections.defaultdict(lambda: [0, 0])
    with open(a.out, "w", encoding="utf-8") as fh:
        for r in rows:
            text, info = m.say(r["record"], r.get("user_turn", ""), r["tag"])
            st = r["record"].get("status", "")
            per[st][0] += 1
            if text is None:
                fell += 1
            else:
                spoke += 1
                per[st][1] += 1
                first_try += info["tries"] == 1
                texts[[x for x in info["raw"] if x][-1]] += 1
            ms.append(info["ms"])
            fh.write(json.dumps({"record": r["record"], "user_turn": r.get("user_turn", ""), "tag": r["tag"],
                                 "reply": text, **info}, ensure_ascii=False) + "\n")
    top = texts.most_common(1)[0][1] if texts else 0
    ms.sort()
    print(json.dumps({"rows": len(rows), "spoke": spoke, "fell_back": fell, "first_try_pass": first_try,
                      "distinct_slotted_replies": len(texts), "top_reply_count": top,
                      "per_status_rows_spoke": {k: v for k, v in per.items()}, "device": m.dev,
                      "median_ms": round(statistics.median(ms), 1) if ms else None,
                      "p90_ms": round(ms[int(0.9 * (len(ms) - 1))], 1) if ms else None}))


if __name__ == "__main__":
    main()
