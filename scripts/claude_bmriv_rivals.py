#!/usr/bin/env python3
"""bm-riv: the rival arms for chat-asked puzzle panels (benchmarks thread, 2026-09-26). One runner for Sleep research's
rsn-358b3 gate panel and Month-end's 0.2d headline row A (design/v3/30-modes/02d-gates-ADDENDUM-7.md). The same blind
panel that the joined build answers is put to the rival models, with the same message text, and the replies go to the
panel owner's scorer unchanged (358b3: joined on id; truth lives in a separate answers file this script never opens).
Format agreed with Sleep research at 14:48 UTC: they use this prompt for every non-build arm of 358b3, plain
MiniCPM5-1B included, and Qwen3.5-2B with thinking on (4096 new tokens) is a report-only arm.

Arms (bm-390's pinned models): plain MiniCPM5-1B @87179e5c, Qwen3.5-2B @15852e8c, LFM2.5-1.2B-Instruct @0f604ada.
Each item: system "You are a helpful assistant." (claude_bm390.GENERAL_SYSTEM), the panel message verbatim as the one
user turn, the model's own chat template, greedy, thinking off, at most 512 new tokens. Report-only extra: a model
with thinking on (--think on, e.g. 4096 new tokens); the reply is the text after </think>.
The panel is TEST-ONLY: this script reads only each item's "id" and "message", never prints either, and never
prints a reply. It prints counts only.
Thinking on: the reply is what follows the last </think> token. A reply whose thinking never closed within the
token cap is "" (no answer), with think_closed false; the thinking text is never scored.
Long arms can be split across processes on one GPU with --shard K/N (items whose panel index % N == K), then
joined by `merge`, which refuses a missing or repeated id. Rows are written as they finish, so a run stopped at a
time cap keeps every finished item.

  python -B scripts/claude_bmriv_rivals.py run --panel PANEL.jsonl --model DIR --name NAME --out OUT
      [--think off|on] [--max-new 512] [--shard K/N]
  python -B scripts/claude_bmriv_rivals.py merge --panel PANEL.jsonl --name NAME --parts P1,P2,.. --out OUT
  python -B scripts/claude_bmriv_rivals.py selftest --tok DIR   (a tiny random model with DIR's tokenizer, CPU)
Writes OUT/rival_<NAME>.jsonl: {"id", "reply", "prompt_tokens", "new_tokens", "hit_max", "think_closed", "ms"} per
item, in panel order.
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


def final_reply(tok, new: list[int], think: bool) -> tuple[str, bool]:
    end = tok.get_vocab().get("</think>")
    if end is not None and end in new:
        k = len(new) - 1 - new[::-1].index(end)
        return tok.decode(new[k + 1:], skip_special_tokens=True).strip(), True
    if think:
        return "", False
    return B.strip_think(tok.decode(new, skip_special_tokens=True)), False


def answer(model_dir: str, message: str, think: bool, max_new: int) -> tuple[str, int, int, bool]:
    import torch
    tok, model, dev, _ = B.plain_model(model_dir)
    enc = prompt_ids(tok, message, think).to(dev)
    n = int(enc["input_ids"].shape[1])
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=max_new, do_sample=False,
                             pad_token_id=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id)
    new = out[0][n:].tolist()
    reply, closed = final_reply(tok, new, think)
    return reply, n, len(new), closed


def shard_of(spec: str) -> tuple[int, int]:
    k, n = (int(x) for x in spec.split("/"))
    if not (n >= 1 and 0 <= k < n):
        raise SystemExit("bmriv: --shard must be K/N with 0 <= K < N")
    return k, n


def summary(name: str, rows: list[dict], f: Path, **extra) -> dict:
    return {"name": name, "rows": len(rows), **extra, "hit_max": sum(r["hit_max"] for r in rows),
            "think_closed": sum(r["think_closed"] for r in rows),
            "empty_replies": sum(not r["reply"].strip() for r in rows),
            "median_new_tokens": statistics.median(r["new_tokens"] for r in rows) if rows else 0,
            "median_ms": statistics.median(r["ms"] for r in rows) if rows else 0,
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}


def run(a) -> int:
    items = panel_items(a.panel)
    k_sh, n_sh = shard_of(a.shard)
    items = [x for i, x in enumerate(items) if i % n_sh == k_sh]
    think = a.think == "on"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"rival_{a.name}.jsonl"
    rows, t_all = [], time.time()
    with f.open("w", encoding="utf-8") as fh:
        for k, (iid, msg) in enumerate(items):
            t0 = time.time()
            reply, n, new, closed = answer(a.model, msg, think, a.max_new)
            row = {"id": iid, "reply": reply, "prompt_tokens": n, "new_tokens": new, "hit_max": new >= a.max_new,
                   "think_closed": closed, "ms": round((time.time() - t0) * 1000, 1)}
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            if (k + 1) % 5 == 0:
                print(f"[bmriv] {a.name} {k + 1}/{len(items)} seconds={time.time() - t_all:.0f}", flush=True)
    print(json.dumps(summary(a.name, rows, f, think=a.think, max_new=a.max_new, shard=a.shard,
                             seconds=round(time.time() - t_all))), flush=True)
    return 0


def merge(a) -> int:
    ids = [iid for iid, _ in panel_items(a.panel)]
    got: dict[str, dict] = {}
    out = Path(a.out)
    for part in a.parts.split(","):
        for line in (out / f"rival_{part}.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["id"] in got:
                raise SystemExit("bmriv: merge found a repeated id")
            got[r["id"]] = r
    if set(got) != set(ids):
        raise SystemExit(f"bmriv: merge has {len(set(ids) - set(got))} missing and {len(set(got) - set(ids))} "
                         "unknown ids")
    rows = [got[i] for i in ids]
    f = out / f"rival_{a.name}.jsonl"
    B._write(f, rows)
    print(json.dumps(summary(a.name, rows, f, parts=a.parts)), flush=True)
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
                                think="off", max_new=8, shard="0/1")
        run(ns)
        rows = [json.loads(x) for x in (Path(d) / "o" / "rival_FAKE.jsonl").read_text().splitlines()]
        ok["one row per item, panel order"] = [r["id"] for r in rows] == ["p0", "p1", "p2"]
        ok["rows carry reply and token counts only"] = all(
            set(r) == {"id", "reply", "prompt_tokens", "new_tokens", "hit_max", "think_closed", "ms"} for r in rows)
        ok["new tokens capped"] = all(0 < r["new_tokens"] <= 8 for r in rows)
        for k in range(2):
            run(argparse.Namespace(**{**vars(ns), "name": f"S{k}", "shard": f"{k}/2"}))
        ok["shards split the panel"] = [[json.loads(x)["id"] for x in (Path(d) / "o" / f"rival_S{k}.jsonl")
                                         .read_text().splitlines()] for k in range(2)] == [["p0", "p2"], ["p1"]]
        merge(argparse.Namespace(panel=str(panel), name="SM", parts="S1,S0", out=str(Path(d) / "o")))
        sm = [json.loads(x) for x in (Path(d) / "o" / "rival_SM.jsonl").read_text().splitlines()]
        ok["merge restores panel order and matches the one-process run"] = sm == [
            {**r, "ms": s["ms"]} for r, s in zip(rows, sm)]
        try:
            merge(argparse.Namespace(panel=str(panel), name="SX", parts="S0", out=str(Path(d) / "o")))
            ok["merge refuses a missing id"] = False
        except SystemExit:
            ok["merge refuses a missing id"] = True
        end = tok.get_vocab()["</think>"]
        a1, a2 = tok.encode("alpha", add_special_tokens=False), tok.encode("beta", add_special_tokens=False)
        ok["thinking on: reply is the text after </think>"] = final_reply(tok, a1 + [end] + a2, True) == ("beta", True)
        ok["thinking on, never closed: empty reply"] = final_reply(tok, a1 + a2, True) == ("", False)
        ok["thinking off: whole text"] = final_reply(tok, a2, False) == ("beta", False)
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
    ap.add_argument("cmd", choices=["run", "merge", "selftest"])
    ap.add_argument("--panel", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--think", choices=["off", "on"], default="off")
    ap.add_argument("--max-new", type=int, default=MAX_NEW)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--parts", default="")
    ap.add_argument("--tok", default="")
    a = ap.parse_args()
    return {"run": run, "merge": merge, "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
