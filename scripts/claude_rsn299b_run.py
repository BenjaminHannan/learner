#!/usr/bin/env python3
"""rsn-299b: rsn-299's calculator arm, with ONE change: 5 samples and a majority vote.

  V  vote: the rsn-299 T arm (identical prompt; the exact calculator fills every "=") is run 5 times
     with sampling (temperature 0.7, top-p 0.95, a fixed seed per question and sample). The final
     answers are normalised (a number to 2 decimals, a clock time to HH:MM, "not sure", else the
     words) and counted. An answer with at least 3 of 5 votes is given, with the steps of its first
     sample. Otherwise the reply is "Answer: I'm not sure" (no answer had a clear majority).
  P  plain: exactly rsn-299's plain arm (greedy, one answer), for the bar.

  python claude_rsn299b_run.py run   --arm P|V --model DIR --items items.jsonl --out out.jsonl
  python claude_rsn299b_run.py score --items items.jsonl --p out-P.jsonl --t out-V.jsonl [--out f]
  python claude_rsn299b_run.py mock
The scorer is rsn-299's (claude_rsn299_run.score / judge / arith_errors), unchanged.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn299_run as R  # noqa: E402

N_SAMPLES = 5
MAJORITY = 3
TEMPERATURE = 0.7
TOP_P = 0.95
UNSURE_LINE = "Answer: I'm not sure (my worked answers did not agree)"


def vote_key(ans: str) -> str:
    """normalise a final answer so that equal answers written differently count as one vote."""
    a = (ans or "").strip()
    if not a:
        return ""
    if R.UNSURE.search(a):
        return "unsure"
    m = R.TIME.search(a)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower().replace(".", "")
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        return f"time:{h:02d}:{mi:02d}"
    nums = R.NUM.findall(a)
    if nums:
        return f"num:{float(nums[0].replace(',', '')):.2f}"
    return "text:" + " ".join(re.sub(r"[^a-z0-9 ]", " ", a.casefold()).split())


def decide(samples: list[str]) -> tuple[str, dict]:
    """samples: steps texts -> (chosen steps text, vote info)."""
    keys = [vote_key(R.answer_line(s)) for s in samples]
    counts = Counter(k for k in keys if k)
    top, n = (counts.most_common(1)[0] if counts else ("", 0))
    info = {"keys": keys, "top": top, "votes": n}
    if n >= MAJORITY and top != "unsure":
        return samples[keys.index(top)], info
    if n >= MAJORITY and top == "unsure":
        return samples[keys.index(top)], info
    # no clear majority: keep the first sample's steps, replace its answer line
    s = samples[0]
    body = s[:s.rfind("Answer:")] if "Answer:" in s else s + "\n"
    return body.rstrip("\n") + "\n" + UNSURE_LINE, info


def _gen_sample(tok, model, dev, text, max_new, stops, seed):
    import torch
    from transformers import StoppingCriteria, StoppingCriteriaList
    ids = tok(text, return_tensors="pt").input_ids.to(dev)
    n0 = ids.shape[1]

    class Stop(StoppingCriteria):
        def __call__(self, input_ids, scores, **kw):
            tail = tok.decode(input_ids[0, n0:][-12:], skip_special_tokens=True)
            return any(s in tail for s in stops)

    torch.manual_seed(seed)
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=max_new, do_sample=True, temperature=TEMPERATURE,
                             top_p=TOP_P, stopping_criteria=StoppingCriteriaList([Stop()]),
                             pad_token_id=tok.pad_token_id or tok.eos_token_id)
    new = out[0, n0:]
    return tok.decode(new, skip_special_tokens=True), len(new)


def solve_vote(question: str, gen_for_seed) -> tuple[str, list, dict]:
    samples, calls = [], []
    for k in range(N_SAMPLES):
        steps, c = R.solve("T", question, gen_for_seed(k))
        samples.append(steps)
        calls.append(c)
    chosen, info = decide(samples)
    info["samples"] = samples
    return chosen, calls, info


def _qseed(qid: str, k: int) -> int:
    return (sum(ord(c) for c in qid) * 1009 + k * 7919) % (2 ** 31)


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run"); r.add_argument("--arm", choices=["P", "V"], required=True)
    r.add_argument("--model", required=True); r.add_argument("--items", required=True)
    r.add_argument("--out", required=True)
    s = sp.add_parser("score"); s.add_argument("--items", required=True)
    s.add_argument("--p", required=True); s.add_argument("--t", required=True)
    s.add_argument("--out", default=None)
    sp.add_parser("mock")
    a = p.parse_args()
    if a.cmd == "run":
        items = [json.loads(l) for l in open(a.items) if l.strip()]
        tok, model, dev = R.load(a.model)
        with open(a.out, "w") as fh:
            for it in items:
                t0 = time.time()
                if a.arm == "P":
                    gen = lambda text, mx, stops: R._gen(tok, model, dev, text, mx, stops)
                    steps, calls = R.solve("P", it["question"], gen)
                    row = {"id": it["id"], "arm": "P", "steps": steps, "calls": calls}
                else:
                    def gfs(k, qid=it["id"]):
                        return lambda text, mx, stops: _gen_sample(tok, model, dev, text, mx, stops, _qseed(qid, k))
                    steps, calls, info = solve_vote(it["question"], gfs)
                    row = {"id": it["id"], "arm": "V", "steps": steps, "calls": calls, "vote": info}
                row["sec"] = round(time.time() - t0, 2)
                fh.write(json.dumps(row) + "\n"); fh.flush()
        rows = [json.loads(l) for l in open(a.out)]
        print(json.dumps(R.score(items, rows)["total"]))
    elif a.cmd == "score":
        items = [json.loads(l) for l in open(a.items) if l.strip()]
        sp_ = R.score(items, [json.loads(l) for l in open(a.p)])
        sv = R.score(items, [json.loads(l) for l in open(a.t)])
        n = sp_["total"]["n"]
        res = {"P": sp_, "V": sv, "n": n,
               "P299b.1_V_right_minus_P_right": sv["total"]["right"] - sp_["total"]["right"],
               "P299b.1": sv["total"]["right"] - sp_["total"]["right"] >= -(-20 * n // 100),
               "P299b.2": sv["total"]["arith_errors"] == 0,
               "P299b.3": sv["total"]["wrong"] <= sp_["total"]["wrong"]}
        out = json.dumps(res, indent=1)
        print(out)
        if a.out:
            Path(a.out).write_text(out)
    else:
        outs = {0: "Answer: 15.2", 1: "Answer: 15.20", 2: "Answer: 15.2 euros", 3: "Answer: 14", 4: "Answer: I'm not sure"}
        ch, info = decide([f"Total is 5 + 10.2 = 15.2.\n{outs[k]}" for k in range(5)])
        print(repr(ch), info["top"], info["votes"])
        ch, info = decide([f"x\nAnswer: {v}" for v in ["10:17", "10:17 am", "9", "3", "4"]])
        print(repr(ch), info["top"], info["votes"])
        ch, info = decide([f"x\nAnswer: {v}" for v in ["Kello", "kello.", "Moss", "Moss", "Moss"]])
        print(repr(ch), info["top"], info["votes"])
        print(vote_key("I'm not sure (missing)"), vote_key("Train A"), vote_key("21:55"), vote_key("1,500 g"))


if __name__ == "__main__":
    main()
