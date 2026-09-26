#!/usr/bin/env python3
"""fd-1: are the general questions that nights knock out the base's least confident right answers? (Fix-sleep,
2026-09-26; report-only diagnosis, prediction fixed in artifacts/claude-fd1-20260926/PLAN.md before it runs.)

For each of dl-1's 300 harm-panel items the plain base answers greedily (claude_dl1_nights.free_answer, 16 new tokens,
the same call the harm score uses) and we record the probability the base gave to each generated token; confidence =
the smallest token probability among the first 4 answer tokens (a weakly known name shows up as one unsure token).
Lost items = the union of items right at base and wrong after night 7 in any arm-seed of dl-4 (gpu/dl4_results.json).

  python -B scripts/claude_fd1_fragile.py --model M --out DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt2 as B2  # noqa: E402
import claude_dl1_nights as D1  # noqa: E402


def answer_conf(s, q, m, max_new=16):
    ids = s.tok(s.tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False,
                                          add_generation_prompt=True, enable_thinking=False),
                return_tensors="pt").to(s.dev)
    with s.torch.no_grad():
        out = m.generate(**ids, max_new_tokens=max_new, do_sample=False, pad_token_id=s.tok.eos_token_id,
                         output_scores=True, return_dict_in_generate=True)
    gen = out.sequences[0][ids["input_ids"].shape[1]:]
    probs = [float(sc[0].float().softmax(-1)[t]) for sc, t in zip(out.scores, gen)]
    return s.tok.decode(gen, skip_special_tokens=True).strip(), probs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dl4", default=str(Path(__file__).resolve().parent.parent /
                                         "artifacts/claude-dl4-20260926/gpu/dl4_results.json"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    r = json.loads(Path(a.dl4).read_text(encoding="utf-8"))
    base = r["base_harm_items"]
    lost = sorted({i for arm in r["arms"] for i, (b, n) in enumerate(zip(base, arm["nights"][-1]["harm_items"]))
                   if b and not n})
    s = B2.Solver(a.model)
    panel = D1.harm_panel()[:300]
    rows = []
    for i, it in enumerate(panel):
        reply, probs = answer_conf(s, it["q"], s.model)
        rows.append({"i": i, "kind": it["kind"], "right": int(D1.harm_right(it, reply)), "dl4_base_right": base[i],
                     "lost": i in lost, "conf": round(min(probs[:4]) if probs else 0.0, 4)})
    (out / "fd1_rows.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    right = [x for x in rows if x["dl4_base_right"]]
    order = sorted(right, key=lambda x: x["conf"])
    third = {x["i"] for x in order[:len(order) // 3]}
    lost_rows = [x for x in right if x["lost"]]
    summ = {"base_right": len(right), "lost_union": len(lost_rows),
            "lost_in_lowest_third": sum(x["i"] in third for x in lost_rows),
            "median_conf_lost": sorted(x["conf"] for x in lost_rows)[len(lost_rows) // 2] if lost_rows else None,
            "median_conf_kept": sorted(x["conf"] for x in right if not x["lost"])[(len(right) - len(lost_rows)) // 2],
            "right_agrees_with_dl4_base": sum(x["right"] == x["dl4_base_right"] for x in rows)}
    summ["share_lost_in_lowest_third"] = round(summ["lost_in_lowest_third"] / max(len(lost_rows), 1), 3)
    (out / "fd1_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
