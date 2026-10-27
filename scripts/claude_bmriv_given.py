#!/usr/bin/env python3
"""bm-riv arm (ii), "grid-given" (benchmarks thread, 2026-09-26; asked for by Month-end, 0.2d ADDENDUM-26). The joined
build's reasoner gets the square as read by the shared code reader (claude_puzzle_reader.read_latin, a hand-written
stand-in for the learned grid reader, which is still owed). For a fair row A, each rival gets the same input: that
code-read grid, written out in plain text, above the panel message. Everything else is claude_bmriv_rivals.py
unchanged (same system prompt, chat template, greedy decoding, --max-new, --think, --shard). That file is left as it
is (601d86c46), so arm (i), raw, stays exactly as before.

What a rival sees when the reader finds a square (GIVEN below; "_" is an empty cell, as in the panels):
    A code reader found this S by S grid in the message below (_ = empty cell):
    <S rows of S cells>

    Message:
    <the panel message, verbatim>
When the reader finds no square (read_latin returns None), the message goes in unchanged, exactly as in arm (i).
The panel is TEST-ONLY: this script reads only each item's "id" and "message", never prints either, never prints a
grid or a reply, and prints counts only (including how many messages had a grid given). Rows have the same fields as
arm (i), so the panel owner's scorer reads them unchanged. Join shards with `claude_bmriv_rivals.py merge`.

  python -B scripts/claude_bmriv_given.py run --panel PANEL.jsonl --model DIR --name NAME --out OUT
      [--think off|on] [--max-new 512] [--shard K/N]
  python -B scripts/claude_bmriv_given.py selftest --tok DIR   (a tiny random model with DIR's tokenizer, CPU)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bmriv_rivals as R  # noqa: E402
import claude_puzzle_reader as PR  # noqa: E402

GIVEN = "A code reader found this {s} by {s} grid in the message below (_ = empty cell):\n{grid}\n\nMessage:\n{message}"


def grid_text(grid) -> str:
    return "\n".join(" ".join("_" if v == 0 else str(v) for v in row) for row in grid)


def given(message: str) -> tuple[str, bool]:
    g = PR.read_latin(message)
    if g is None:
        return message, False
    return GIVEN.format(s=g["size"], grid=grid_text(g["grid"]), message=message), True


def run(a) -> int:
    items = R.panel_items(a.panel)
    k_sh, n_sh = R.shard_of(a.shard)
    items = [x for i, x in enumerate(items) if i % n_sh == k_sh]
    think = a.think == "on"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"rival_{a.name}.jsonl"
    rows, found, t_all = [], 0, time.time()
    with f.open("w", encoding="utf-8") as fh:
        for k, (iid, msg) in enumerate(items):
            text, ok = given(msg)
            found += ok
            t0 = time.time()
            reply, n, new, closed = R.answer(a.model, text, think, a.max_new)
            row = {"id": iid, "reply": reply, "prompt_tokens": n, "new_tokens": new, "hit_max": new >= a.max_new,
                   "think_closed": closed, "ms": round((time.time() - t0) * 1000, 1)}
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            if (k + 1) % 5 == 0:
                print(f"[bmriv-given] {a.name} {k + 1}/{len(items)} seconds={time.time() - t_all:.0f}", flush=True)
    print(json.dumps(R.summary(a.name, rows, f, arm="grid-given", grids_given=found, think=a.think,
                               max_new=a.max_new, shard=a.shard, seconds=round(time.time() - t_all))), flush=True)
    return 0


def selftest(a) -> int:
    import tempfile
    import torch
    from transformers import AutoTokenizer, LlamaConfig, LlamaForCausalLM
    ok = {}
    sq = "Can you finish this square? Use 1 to 4.\n1 _ 3 _\n_ 3 _ 1\n3 _ 1 _\n_ 1 _ 3\nThanks!"
    text, found = given(sq)
    ok["a square is found and given"] = found and text.startswith("A code reader found this 4 by 4 grid")
    ok["the grid is written with _ for empty cells"] = "\n1 _ 3 _\n_ 3 _ 1\n3 _ 1 _\n_ 1 _ 3\n\nMessage:\n" in text
    ok["the message follows verbatim, last"] = text.endswith("Message:\n" + sq)
    rows = "Row 1: 2, _, 1\nRow 2: _, 1, _\nRow 3: 1, _, 2"
    t2, f2 = given("Please solve:\n" + rows)
    ok["other layouts are rewritten the same way"] = f2 and "3 by 3 grid" in t2 and "\n2 _ 1\n_ 1 _\n1 _ 2\n" in t2
    plain = "My son is 4 and my daughter is 7. Any gift ideas under 20 dollars?"
    ok["no square: message unchanged"] = given(plain) == (plain, False)
    two = "1 2 3\n2 3 1\n3 1 2\n\nor\n\n2 3 1\n3 1 2\n1 2 3"
    ok["a message the reader refuses (two squares) goes in unchanged"] = given(two) == (two, False)
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
        msgs = [sq, plain, "Please solve:\n" + rows]
        panel.write_text("".join(json.dumps({"id": f"p{i}", "message": m, "truth": "x"}) + "\n"
                                 for i, m in enumerate(msgs)), encoding="utf-8")
        ns = argparse.Namespace(panel=str(panel), model=str(Path(d) / "m"), name="G", out=str(Path(d) / "o"),
                                think="off", max_new=8, shard="0/1")
        run(ns)
        g = [json.loads(x) for x in (Path(d) / "o" / "rival_G.jsonl").read_text().splitlines()]
        R.run(argparse.Namespace(**{**vars(ns), "name": "RAW"}))
        raw = [json.loads(x) for x in (Path(d) / "o" / "rival_RAW.jsonl").read_text().splitlines()]
        ok["one row per item, panel order"] = [r["id"] for r in g] == ["p0", "p1", "p2"]
        ok["rows have exactly arm (i)'s fields"] = all(set(r) == set(s) for r, s in zip(g, raw))
        ok["given items have longer prompts; the no-square item matches arm (i)"] = (
            g[0]["prompt_tokens"] > raw[0]["prompt_tokens"] and g[2]["prompt_tokens"] > raw[2]["prompt_tokens"]
            and g[1]["prompt_tokens"] == raw[1]["prompt_tokens"] and g[1]["reply"] == raw[1]["reply"])
        ids = R.prompt_ids(tok, given(sq)[0], False)["input_ids"][0].tolist()
        ok["the given grid and the message reach the prompt"] = ("1 _ 3 _" in tok.decode(ids)
                                                                  and "Thanks!" in tok.decode(ids))
        for k in range(2):
            run(argparse.Namespace(**{**vars(ns), "name": f"S{k}", "shard": f"{k}/2"}))
        R.merge(argparse.Namespace(panel=str(panel), name="SM", parts="S0,S1", out=str(Path(d) / "o")))
        sm = [json.loads(x) for x in (Path(d) / "o" / "rival_SM.jsonl").read_text().splitlines()]
        ok["shards merge back to the one-process run"] = sm == [{**r, "ms": s["ms"]} for r, s in zip(g, sm)]
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("BMRIV-GIVEN-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "selftest"])
    ap.add_argument("--panel", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--think", choices=["off", "on"], default="off")
    ap.add_argument("--max-new", type=int, default=R.MAX_NEW)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--tok", default="")
    a = ap.parse_args()
    return {"run": run, "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
