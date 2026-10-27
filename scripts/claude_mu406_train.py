#!/usr/bin/env python3
"""mu-406 training: a LoRA on GPT-6 Luna's teaching replies, with the talker's U0 input ("Making things up about you",
2026-09-27). New file. Plan: artifacts/claude-mu406-20260926/PLAN-draft-3.md (draft; the sealed plan decides).

It imports claude_k1h_train and runs its training loop (run_train) and fixed recipe unchanged: LoRA rank 16, alpha
32, dropout 0.05, every linear layer; AdamW lr 2e-4; 2 epochs; batch 8; 5% warmup then cosine; rows over 1,536 tokens
dropped; 10% of chats held back for dev loss only; the last step's adapter is kept; the first-step gradient check.
Two k1h functions are swapped, and nothing else:
  - pair_rows reads mu-406's rows (one per kept turn) and splits dev by chat with k1h's seed and share;
  - render uses the talker's own template call (claude_mu405_talk.Talker.reply: add_generation_prompt, thinking off).
A row's messages are exactly what claude_mu407_talk.run gives the talker on arm U0 at that turn, with Luna's earlier
replies as the history. The target is Luna's reply; k1h adds the end-of-turn text. Loss is on the target only.
Its printed lines keep k1h's "k1h-train" labels.

  rows  --items I --facts F --teach T --frames FR --heldout H --out ROWS   (no model) one row per kept turn
  train --model BASE --rows ROWS --out OUT [--limit N --max-steps S]      (BensPC, CUDA) k1h's run_train
  merge --model BASE --adapter OUT/adapter --out MERGED                   a merged copy for the talk arms and bm-390
  selftest                                                                CPU, no model
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import types
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_k1h_train as K  # noqa: E402
import claude_mu407_talk as M7  # noqa: E402


def jl(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def build_rows(items: list[dict], teach: dict, fr: dict) -> list[dict]:
    rows = []
    for it in items:
        t = teach.get(it["item_id"])
        if not t:
            continue
        hist: list[dict] = []
        for i, r in enumerate(t["replies"]):
            u = it["session2"][i]
            msgs = [{"role": "system", "content": fr["system"]}] + hist + [
                {"role": "user", "content": M7.latest("U0", fr, it, u["text"])}]
            rows.append({"item_id": it["item_id"], "turn_i": i, "kind": u["kind"], "msgs": msgs, "target": r})
            hist += [{"role": "user", "content": u["text"]}, {"role": "assistant", "content": r}]
    return rows


def pair_rows(rows_path: str, _prompts=None, _kept=None):
    """k1h's pair_rows contract: (train_rows, dev_rows, counts). Dev is 10% of chats (k1h's seed and share)."""
    rows = jl(rows_path)
    ids = sorted({r["item_id"] for r in rows})
    shuffled = list(ids)
    random.Random(K.DEV_SEED).shuffle(shuffled)
    dev_ids = set(shuffled[:round(K.DEV_SHARE * len(ids))])
    counts = {"chats": len(ids), "rows": len(rows), "dev_chats": len(dev_ids),
              "by_kind": dict(Counter(r["kind"] for r in rows))}
    return [r for r in rows if r["item_id"] not in dev_ids], [r for r in rows if r["item_id"] in dev_ids], counts


def render(tok, msgs) -> str:
    """claude_mu405_talk.Talker.reply's template call, character for character."""
    try:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


def cmd_rows(a) -> dict:
    items, held = jl(a.items), {h["item_id"] for h in jl(a.heldout)}
    clash = held & {it["item_id"] for it in items}
    if clash:
        raise SystemExit(f"mu406 rows: {len(clash)} held-out chats are in the training items")
    fr = M7.load_frames(a.frames)
    teach = {t["item_id"]: t for t in jl(a.teach)}
    rows = build_rows(items, teach, fr)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    res = {"items": len(items), "chats_with_rows": len({r["item_id"] for r in rows}), "rows": len(rows),
           "by_kind": dict(Counter(r["kind"] for r in rows)), "heldout_excluded": len(held)}
    print(json.dumps(res))
    return res


def cmd_train(a) -> dict:
    K.pair_rows = pair_rows
    K.render = render
    ns = types.SimpleNamespace(items=a.rows, prompts=None, kept=None, model=a.model, out=a.out, limit=a.limit,
                               max_steps=a.max_steps)
    return K.run_train(ns)


def cmd_merge(a) -> dict:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    base = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.float32, trust_remote_code=True).eval()
    x = tok("The quick brown fox jumps over the lazy dog.", return_tensors="pt")["input_ids"]
    pm = PeftModel.from_pretrained(base, a.adapter).eval()
    with torch.no_grad():
        want = pm(input_ids=x).logits
    merged = pm.merge_and_unload().eval()
    with torch.no_grad():
        diff = (merged(input_ids=x).logits - want).abs().max().item()
    if diff > 1e-3:
        raise SystemExit(f"mu406 merge: merged logits differ from base+adapter by {diff}")
    out = Path(a.out)
    merged.save_pretrained(out, safe_serialization=True)
    tok.save_pretrained(out)
    from claude_k1h_cre import sha256_file
    res = {"merged": str(out), "max_logit_diff": diff,
           "adapter_sha256": sha256_file(Path(a.adapter) / "adapter_model.safetensors")}
    (out / "mu406_merged.json").write_text(json.dumps(res, indent=1), encoding="utf-8")   # claude_mu406_talk checks it
    print(json.dumps(res))
    return res


def selftest() -> None:
    ok = 0
    fr = {"system": "SYS", "memory_header": "Earlier:", "line_prefix": "They said", "current_label": "Now:"}
    kinds = ("smalltalk", "feelings", "advice", "followup", "ask")
    it = {"item_id": "c1", "session1": [{"text": "my dog Pim"}, {"text": "welder here"}, {"text": "from Boise"}],
          "session2": [{"kind": k, "text": f"hi {k}"} for k in kinds]}
    teach = {"c1": {"item_id": "c1", "ok": True, "replies": [f"r{i}" for i in range(5)]},
             "c2": {"item_id": "c2", "ok": False, "replies": ["a", "b"]}}
    it2 = dict(it, item_id="c2")
    rows = build_rows([it, it2, dict(it, item_id="c3")], teach, fr)
    assert len(rows) == 7 and [r["turn_i"] for r in rows if r["item_id"] == "c2"] == [0, 1]; ok += 1

    class Fake:   # replays Luna's replies through mu-407's own run loop and records what the talker is given
        def __init__(self):
            self.seen, self.n = [], 0

        def reply(self, system, msgs):
            self.seen.append([{"role": "system", "content": system}] + msgs)
            self.n += 1
            return f"r{self.n - 1}"
    f = Fake()
    M7.run(f, "U0", fr, [it])
    assert [r["msgs"] for r in rows if r["item_id"] == "c1"] == f.seen; ok += 1
    assert rows[4]["target"] == "r4" and rows[4]["kind"] == "ask" and "They said \"my dog Pim\"" in rows[4]["msgs"][-1][
        "content"]; ok += 1
    assert all(m["content"] == f"hi {kinds[k // 2]}" for k, m in enumerate(rows[4]["msgs"][1:-1]) if k % 2 == 0); ok += 1
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rp = Path(td) / "rows.jsonl"
        many = build_rows([dict(it, item_id=f"k{j:02d}") for j in range(20)],
                          {f"k{j:02d}": dict(teach["c1"], item_id=f"k{j:02d}") for j in range(20)}, fr)
        rp.write_text("".join(json.dumps(r) + "\n" for r in many), encoding="utf-8")
        tr, dv, c = pair_rows(str(rp))
        assert c["chats"] == 20 and c["dev_chats"] == 2 and len(dv) == 10 and len(tr) == 90; ok += 1
        assert not ({r["item_id"] for r in tr} & {r["item_id"] for r in dv}); ok += 1
    tok = K._Tok()
    s = render(tok, rows[0]["msgs"])
    assert s.startswith("<system>SYS<end>") and s.endswith("<assistant>"); ok += 1
    K.render = render
    enc = K.encode(tok, rows[0]["msgs"], "r0", "<end>", 10_000)
    assert enc is not None and enc[1].count(-100) == len(tok(s)["input_ids"]) and enc[1][-1] == 1; ok += 1
    print(f"mu406 train selftest {ok}/8 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["rows", "train", "merge", "selftest"])
    for k in ("--items", "--facts", "--teach", "--frames", "--heldout", "--out", "--model", "--rows", "--adapter"):
        ap.add_argument(k)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-steps", type=int, default=0)
    a = ap.parse_args()
    {"rows": cmd_rows, "train": cmd_train, "merge": cmd_merge, "selftest": lambda _a: selftest()}[a.cmd](a)


if __name__ == "__main__":
    main()
