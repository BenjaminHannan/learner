#!/usr/bin/env python3
"""DEV only: how often does plain MiniCPM5-1B finish a number square (shared world scripts/claude_world_latin.py)?
(creative research thread, 2026-09-26). Sets the difficulty for the next blurt -> checker -> night test.

For each (size, blanks) setting: DEV items from seeds 900000-900999 only (test seeds will be 901000 and up), the
greedy reply, then n free samples at temperature T (thinking off, the chat template, no constrained decoding).
Reports cov@1 (greedy right), cov@30 (any of n samples right) and lucky samples. Writes one JSON summary.

  python -B scripts/claude_latin_dev.py --model M --out F.json --settings 4:4,4:6,4:8,5:5,5:8 --items 12 [--form blanks]
Form "square" (the world's own prompt: reply with the whole square) got 0 of 10 at 3x3 with 3 blanks, 30 samples: the
1B writes only some rows. Form "blanks" asks for the missing numbers only: 4x4 with 3/5/7 blanks got 0 of 12 each
(the 1B writes too many numbers). Form "game": --settings keys:1,recipes:1 (text games, DEV seeds only).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_textgames as G  # noqa: E402
import claude_world_latin as W  # noqa: E402

DEV_SEEDS = range(900000, 901000)


def blanks_form(item):
    """Reply form B: the shared world's blanks mode (claude_world_latin.prompt_blanks / check_blanks, exact count)."""
    return dict(item, prompt=W.prompt_blanks(item))


def check_b(item, reply):
    return W.check_blanks(item, reply)


class Sampler:
    def __init__(self, model_dir):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, trust_remote_code=True,
                                                          dtype=torch.bfloat16).to(self.dev).eval()

    def generate(self, item, n, temp, model=None):
        m = model or self.model
        text = self.tok.apply_chat_template([{"role": "user", "content": item["prompt"]}], tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False)
        ids = self.tok(text, return_tensors="pt").to(self.dev)
        cut = ids["input_ids"].shape[1]
        kw = {"do_sample": True, "temperature": temp, "top_p": 1.0, "num_return_sequences": n} if temp else \
             {"do_sample": False}
        s = item["size"]
        cap = item["cap"] if "cap" in item else \
            3 * item["blanks"] + 8 if "missing numbers" in item["prompt"] else 4 * s * s + 16
        with self.torch.no_grad():
            out = m.generate(**ids, max_new_tokens=cap, pad_token_id=self.tok.eos_token_id, **kw)
        return [self.tok.decode(o[cut:], skip_special_tokens=True).strip() for o in out]


def measure(smp, size, blanks, items, n, temp, form="square"):
    rows = []
    chk = W.check if form == "square" else check_b
    for seed in list(DEV_SEEDS)[:items]:
        it = W.make(seed, size, blanks)
        if form == "blanks":
            it = blanks_form(it)
        g = smp.generate(it, 1, None)[0]
        hits = [chk(it, t) for t in smp.generate(it, n, temp)]
        rows.append({"seed": seed, "greedy_ok": chk(it, g), "hits": sum(hits), "greedy": g})
    return {"form": form, "size": size, "blanks": blanks, "items": len(rows),
            "cov@1": sum(r["greedy_ok"] for r in rows),
            f"cov@{n}": sum(r["hits"] > 0 for r in rows), "lucky": sum(r["hits"] for r in rows),
            "greedy_examples": [r["greedy"] for r in rows[:3]]}


def measure_games(smp, kind, level, items, n, temp):
    """Sleep research's text games (claude_textgames.py): the game text is the prompt; check() simulates any plan."""
    rows = []
    for seed in list(DEV_SEEDS)[:items]:
        g = G.make_game(kind, seed, level)
        it = {"prompt": g["text"], "size": 0, "cap": 12 * len(g["plan"]) + 24}
        ok = lambda t: G.check(g, t)["ok"]  # noqa: E731
        gr = smp.generate(it, 1, None)[0]
        hits = [ok(t) for t in smp.generate(it, n, temp)]
        rows.append({"seed": seed, "greedy_ok": ok(gr), "hits": sum(hits), "greedy": gr, "plan_len": len(g["plan"])})
    return {"form": "game", "kind": kind, "level": level, "items": len(rows), "cov@1": sum(r["greedy_ok"] for r in rows),
            f"cov@{n}": sum(r["hits"] > 0 for r in rows), "lucky": sum(r["hits"] for r in rows),
            "plan_len": [r["plan_len"] for r in rows], "greedy_examples": [r["greedy"] for r in rows[:3]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--settings", default="4:4,4:6,4:8,5:5,5:8")
    ap.add_argument("--items", type=int, default=12)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--temp", type=float, default=1.0)
    ap.add_argument("--form", default="square", choices=["square", "blanks", "game"])
    a = ap.parse_args()
    t0 = time.time()
    smp = Sampler(a.model)
    res = {"n": a.n, "temp": a.temp, "settings": []}
    for st in a.settings.split(","):
        if a.form == "game":
            kind, level = st.split(":")
            r = measure_games(smp, kind, int(level), a.items, a.n, a.temp)
        else:
            size, blanks = (int(x) for x in st.split(":"))
            r = measure(smp, size, blanks, a.items, a.n, a.temp, a.form)
        res["settings"].append(r)
        print(json.dumps({k: v for k, v in r.items() if k != "greedy_examples"}), flush=True)
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    res["minutes"] = round((time.time() - t0) / 60, 1)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
