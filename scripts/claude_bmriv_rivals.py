#!/usr/bin/env python3
"""bm-riv: the rival arms for 0.2d's headline row A (benchmarks thread, 2026-09-26; Month-end's
design/v3/30-modes/02d-gates-ADDENDUM-7.md). The same blind chat-asked puzzle panel that the joined build answers is
put to the rival models, with the same message text, and the replies go to the panel owner's scorer unchanged.

Arms (bm-390's pinned models): plain MiniCPM5-1B @87179e5c, Qwen3.5-2B @15852e8c, LFM2.5-1.2B-Instruct @0f604ada.
Each item: system "You are a helpful assistant." (claude_bm390.GENERAL_SYSTEM), the panel message verbatim as the one
user turn, the model's own chat template, greedy, thinking off, at most 512 new tokens. Report-only extra: a model
with thinking on (--think on, e.g. 4096 new tokens); the reply is the text after </think>.
The panel is TEST-ONLY: this script reads only each item's "id" and "message", never prints either, and never
prints a reply. It prints counts only.

  python -B scripts/claude_bmriv_rivals.py run --panel PANEL.jsonl --model DIR --name NAME --out OUT
      [--think off|on] [--max-new 512]
  python -B scripts/claude_bmriv_rivals.py selftest --tok DIR   (a tiny random model with DIR's tokenizer, CPU)
Writes OUT/rival_<NAME>.jsonl: {"id", "reply", "prompt_tokens", "new_tokens", "hit_max", "ms"} per item, in panel order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402

SYSTEM = B.GENERAL_SYSTEM
MAX_NEW = 512


def panel_items(path: str) -> list[tuple[str, str]]:
    out, seen = [], set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["id"] in seen:
            raise SystemExit("bmriv: duplicate panel id")
        seen.add(r["id"])
        out.append((str(r["id"]), str(r["message"])))
    return out


def prompt_ids(tok, message: str, think: bool):
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": message}]
    return tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=think,
                                   return_dict=True, return_tensors="pt")


def answer(model_dir: str, message: str, think: bool, max_new: int) -> tuple[str, int, int]:
    import torch
    tok, model, dev, _ = B.plain_model(model_dir)
    enc = prompt_ids(tok, message, think).to(dev)
    n = int(enc["input_ids"].shape[1])
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=max_new, do_sample=False,
                             pad_token_id=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id)
    new = out[0][n:]
    return B.strip_think(tok.decode(new, skip_special_tokens=True)), n, int(new.shape[0])


def run(a) -> int:
    items = panel_items(a.panel)
    think = a.think == "on"
    rows, t_all = [], time.time()
    for k, (iid, msg) in enumerate(items):
        t0 = time.time()
        reply, n, new = answer(a.model, msg, think, a.max_new)
        rows.append({"id": iid, "reply": reply, "prompt_tokens": n, "new_tokens": new, "hit_max": new >= a.max_new,
                     "ms": round((time.time() - t0) * 1000, 1)})
        if (k + 1) % 25 == 0:
            print(f"[bmriv] {a.name} {k + 1}/{len(items)} seconds={time.time() - t_all:.0f}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"rival_{a.name}.jsonl"
    B._write(f, rows)
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    print(json.dumps({"name": a.name, "rows": len(rows), "think": a.think, "max_new": a.max_new,
                      "hit_max": sum(r["hit_max"] for r in rows),
                      "median_new_tokens": statistics.median(r["new_tokens"] for r in rows) if rows else 0,
                      "median_ms": statistics.median(r["ms"] for r in rows) if rows else 0,
                      "seconds": round(time.time() - t_all), "sha256": sha}), flush=True)
    return 0


def selftest(a) -> int:
    import tempfile
    import torch
    from transformers import AutoTokenizer, LlamaConfig, LlamaForCausalLM
    ok = {}
    tok = AutoTokenizer.from_pretrained(a.tok)
    with tempfile.TemporaryDirectory() as d:
        torch.manual_seed(0)
        cfg = LlamaConfig(vocab_size=len(tok), hidden_size=16, intermediate_size=32, num_hidden_layers=1,
                          num_attention_heads=2, num_key_value_heads=1, max_position_embeddings=4096,
                          bos_token_id=tok.bos_token_id, eos_token_id=tok.eos_token_id,
                          pad_token_id=tok.pad_token_id)
        LlamaForCausalLM(cfg).save_pretrained(Path(d) / "m")
        tok.save_pretrained(Path(d) / "m")
        panel = Path(d) / "panel.jsonl"
        panel.write_text("".join(json.dumps({"id": f"p{i}", "message": f"Finish this square {i}", "truth": "x"}) + "\n"
                                 for i in range(3)), encoding="utf-8")
        ns = argparse.Namespace(panel=str(panel), model=str(Path(d) / "m"), name="FAKE", out=str(Path(d) / "o"),
                                think="off", max_new=8)
        run(ns)
        rows = [json.loads(x) for x in (Path(d) / "o" / "rival_FAKE.jsonl").read_text().splitlines()]
        ok["one row per item, panel order"] = [r["id"] for r in rows] == ["p0", "p1", "p2"]
        ok["rows carry reply and token counts only"] = all(
            set(r) == {"id", "reply", "prompt_tokens", "new_tokens", "hit_max", "ms"} for r in rows)
        ok["new tokens capped"] = all(0 < r["new_tokens"] <= 8 for r in rows)
        off = prompt_ids(tok, "hello", False)["input_ids"][0].tolist()
        on = prompt_ids(tok, "hello", True)["input_ids"][0].tolist()
        ok["message and system are in the prompt"] = ("hello" in tok.decode(off) and SYSTEM in tok.decode(off))
        ok["think flag reaches the chat template"] = off != on
        dup = Path(d) / "dup.jsonl"
        dup.write_text('{"id": "a", "message": "x"}\n{"id": "a", "message": "y"}\n', encoding="utf-8")
        try:
            panel_items(str(dup))
            ok["duplicate ids refused"] = False
        except SystemExit:
            ok["duplicate ids refused"] = True
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("BMRIV-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "selftest"])
    ap.add_argument("--panel", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--think", choices=["off", "on"], default="off")
    ap.add_argument("--max-new", type=int, default=MAX_NEW)
    ap.add_argument("--tok", default="")
    a = ap.parse_args()
    return {"run": run, "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
