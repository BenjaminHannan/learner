#!/usr/bin/env python3
"""own-M1v mouth: sample-first decoding on the own-M1n weights (one change vs own-M1n).

own-M1n tried the greedy reply first; greedy always picks the single most likely wording, so 1,000 dev rows
got only 59 distinct replies. Here the mouth draws up to `samples` sampled replies first (temperature 0.8,
top-p 0.95) and keeps the first one that passes slot_check; greedy is the last try. The gate, prompt, fill
and fallback rule are the sealed own-M1 code, unchanged.

CLI: python claude_own_m1v_speak.py --model DIR --data DEV.jsonl --out OUT.jsonl [--samples 4] [--seed 1]
prints the same summary as claude_own_m1_speak.py, plus the try histogram.
"""
import argparse, collections, json, statistics, sys, time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_own_m1_common import build_prompt, fill, slot_check, slot_values  # noqa: E402
from claude_own_m1_speak import Mouth  # noqa: E402


class SampleFirstMouth(Mouth):
    def say(self, record, user_turn, tag):
        t0 = time.perf_counter()
        p = self.tok(build_prompt(record, user_turn, tag), add_special_tokens=False)["input_ids"]
        if self.tok.bos_token_id is not None:
            p = [self.tok.bos_token_id] + p
        ids = torch.tensor([p], device=self.dev)
        raws, probs = [], []
        order = [True] * self.samples + [False]  # sampled tries first, greedy last
        for i, sample in enumerate(order):
            raw = self._gen(ids, sample=sample)
            pr = slot_check(raw, record) if raw else ["empty"]
            raws.append(raw)
            probs.append(pr)
            if not pr:
                return fill(raw, slot_values(record)), {"tries": i + 1, "greedy": not sample, "raw": raws,
                                                        "problems": probs, "ms": (time.perf_counter() - t0) * 1000}
        return None, {"tries": len(raws), "greedy": None, "raw": raws, "problems": probs,
                      "ms": (time.perf_counter() - t0) * 1000}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    m = SampleFirstMouth(a.model, samples=a.samples, seed=a.seed)
    rows = [json.loads(l) for l in Path(a.data).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = rows[: a.limit] if a.limit else rows
    spoke, fell, texts, ms, tries = 0, 0, collections.Counter(), [], collections.Counter()
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
                tries[info["tries"]] += 1
                texts[info["raw"][info["tries"] - 1]] += 1
            ms.append(info["ms"])
            fh.write(json.dumps({"record": r["record"], "user_turn": r.get("user_turn", ""), "tag": r["tag"],
                                 "reply": text, **info}, ensure_ascii=False) + "\n")
    top = texts.most_common(1)[0][1] if texts else 0
    ms.sort()
    print(json.dumps({"rows": len(rows), "spoke": spoke, "fell_back": fell, "tries_hist": dict(sorted(tries.items())),
                      "distinct_slotted_replies": len(texts), "top_reply_count": top,
                      "top5": texts.most_common(5), "per_status_rows_spoke": dict(per), "device": m.dev,
                      "median_ms": round(statistics.median(ms), 1) if ms else None,
                      "p90_ms": round(ms[int(0.9 * (len(ms) - 1))], 1) if ms else None}, ensure_ascii=False))


if __name__ == "__main__":
    main()
