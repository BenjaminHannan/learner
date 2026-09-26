#!/usr/bin/env python3
"""bm-397t training (benchmarks thread, 2026-09-26): teach the plain MiniCPM5-1B to answer questions about a chat in
few words, from code-made practice only (scripts/claude_bm397t_data.py). One change: a LoRA (claude_blurt2.add_lora,
rank 16, alpha 32, dropout 0.05, on q/k/v/o), trained 1 epoch with AdamW lr 2e-4, 8 examples a step, seed 3970. The
loss is on the answer tokens and the end-of-turn token only. Thinking stays off (enable_thinking=False).

Then the LoRA is merged into a copy of the weights and saved as a normal model folder, so the sealed bm-390 harness
can score it as `plain:<folder>` exactly as it scored the base 1B (arm T).
Dev sanity (report only; 200 held-out code-made questions, another seed): the share answered right and the
median words, before and after training, greedy, at most 32 new tokens.

  python -B scripts/claude_bm397t_train.py --base BASE --train train.jsonl --dev dev.jsonl --out OUT
      [--limit N --dev-limit N --no-save]   (smoke only)
  python -B scripts/claude_bm397t_train.py selftest   (a tiny random Llama: LoRA merge is exact, save/load round trip)
Writes OUT/merged/ (model + tokenizer), OUT/adapter397t.pt (the LoRA weights), OUT/train397t.json (counts only).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_bm397t_data as D  # noqa: E402

SEED = 3970
RANK, ALPHA, DROPOUT = 16, 32, 0.05
LR, BATCH, EPOCHS = 2e-4, 8, 1
MAX_NEW = 32
END = "<|im_end|>"


def _rows(p: str, limit: int) -> list[dict]:
    rows = [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows[:limit] if limit else rows


def _prompt_ids(tok, r: dict) -> list[int]:
    msgs = [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["user"]}]
    return list(tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False,
                                        return_dict=True)["input_ids"])


def _target_ids(tok, answer: str) -> list[int]:
    return list(tok(answer, add_special_tokens=False)["input_ids"]) + [tok.convert_tokens_to_ids(END)]


def answer(model, tok, dev: str, r: dict) -> str:
    import torch
    import claude_bm390 as B
    ids = torch.tensor([_prompt_ids(tok, r)], device=dev)
    with torch.no_grad():
        out = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), max_new_tokens=MAX_NEW,
                             do_sample=False, pad_token_id=tok.pad_token_id if tok.pad_token_id is not None
                             else tok.eos_token_id)
    return B.strip_think(tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True))


def dev_check(model, tok, dev: str, rows: list[dict]) -> dict:
    model.eval()
    replies = [answer(model, tok, dev, r) for r in rows]
    right = [D.correct(x, r["answer"]) for x, r in zip(replies, rows)]
    by = {}
    for r, ok in zip(rows, right):
        by.setdefault(r["kind"], [0, 0])
        by[r["kind"]][0] += int(ok)
        by[r["kind"]][1] += 1
    return {"n": len(rows), "right": sum(right), "by_kind": {k: f"{v[0]}/{v[1]}" for k, v in sorted(by.items())},
            "median_words": statistics.median(len(x.split()) for x in replies) if replies else 0}


def merge_lora(model) -> int:
    """Fold each LoRALinear (W + scale * B@A) back into a plain Linear. Returns the number merged."""
    import torch
    n = 0
    for _, mod in list(model.named_modules()):
        for child, sub in list(mod.named_children()):
            if hasattr(sub, "A") and hasattr(sub, "B") and hasattr(sub, "base"):
                with torch.no_grad():
                    w = sub.base.weight
                    w.copy_((w.float() + sub.scale * (sub.B.float() @ sub.A.float())).to(w.dtype))
                setattr(mod, child, sub.base)
                n += 1
    return n


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def selftest() -> None:
    import tempfile
    import torch
    from transformers import AutoModelForCausalLM, LlamaConfig
    import claude_blurt2 as BL
    ok, total = 0, 0

    def check(name, cond):
        nonlocal ok, total
        total += 1
        ok += int(cond)
        print(f"{'PASS' if cond else 'FAIL'} {name}")

    torch.manual_seed(0)
    cfg = LlamaConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
                      num_key_value_heads=2, max_position_embeddings=64)
    m = AutoModelForCausalLM.from_config(cfg).eval()
    x = torch.randint(0, 64, (1, 12))
    base = m(input_ids=x).logits
    BL.add_lora(m, r=4, alpha=8, dropout=0.0)
    for mod in m.modules():
        if hasattr(mod, "B") and hasattr(mod, "base"):
            torch.nn.init.normal_(mod.B, std=0.05)
    m.eval()
    lora = m(input_ids=x).logits
    check("the LoRA changes the output", (lora - base).abs().max().item() > 1e-3)
    check("8 layers wrapped (q,k,v,o x 2)", merge_lora(m) == 8)
    merged = m(input_ids=x).logits
    check("merged output equals the LoRA output", (merged - lora).abs().max().item() < 1e-4)
    check("no LoRA modules left", not any(hasattr(mod, "A") for mod in m.modules()))
    with tempfile.TemporaryDirectory() as d:
        m.save_pretrained(d, safe_serialization=True)
        back = AutoModelForCausalLM.from_pretrained(d).eval()
        check("saved folder reloads with the same output", (back(input_ids=x).logits - merged).abs().max().item() < 1e-5)
    print(f"BM397T-TRAIN-SELFTEST {'PASS' if ok == total else 'FAIL'} {ok}/{total}")
    if ok != total:
        raise SystemExit(1)


def main() -> int:
    if sys.argv[1:] == ["selftest"]:
        selftest()
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dev-limit", type=int, default=0)
    ap.add_argument("--no-save", action="store_true")
    a = ap.parse_args()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import claude_blurt2 as BL
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    tok = AutoTokenizer.from_pretrained(a.base)
    model = AutoModelForCausalLM.from_pretrained(a.base, dtype=dtype).to(dev)
    train, devrows = _rows(a.train, a.limit), _rows(a.dev, a.dev_limit)
    res = {"device": dev, "dtype": str(dtype), "train_rows": len(train), "dev_rows": len(devrows),
           "recipe": {"rank": RANK, "alpha": ALPHA, "dropout": DROPOUT, "lr": LR, "batch": BATCH, "epochs": EPOCHS,
                      "seed": SEED}}
    res["dev_before"] = dev_check(model, tok, dev, devrows)
    print(json.dumps({"dev_before": res["dev_before"]}), flush=True)

    torch.manual_seed(SEED)
    BL.add_lora(model, r=RANK, alpha=ALPHA, dropout=DROPOUT)
    params = [p for p in model.parameters() if p.requires_grad]
    res["lora_params"] = sum(p.numel() for p in params)
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)
    order = list(range(len(train)))
    random.Random(SEED).shuffle(order)
    model.train()
    losses, steps = [], 0
    for ep in range(EPOCHS):
        for i in range(0, len(order), BATCH):
            batch = [train[j] for j in order[i:i + BATCH]]
            tot = 0.0
            for r in batch:
                p, t = _prompt_ids(tok, r), _target_ids(tok, r["answer"])
                ids = torch.tensor([p + t], device=dev)
                lab = ids.clone()
                lab[0, :len(p)] = -100
                loss = model(input_ids=ids, labels=lab).loss / len(batch)
                loss.backward()
                tot += float(loss.detach())
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            opt.zero_grad()
            losses.append(tot)
            steps += 1
            if steps % 25 == 0:
                print(json.dumps({"step": steps, "loss": round(tot, 4), "s": round(time.time() - t0)}), flush=True)
    res["steps"] = steps
    res["loss_first10"] = round(sum(losses[:10]) / max(1, len(losses[:10])), 4)
    res["loss_last10"] = round(sum(losses[-10:]) / max(1, len(losses[-10:])), 4)
    torch.save({k: v.detach().cpu() for k, v in model.state_dict().items() if k.endswith(".A") or k.endswith(".B")},
               out / "adapter397t.pt")
    res["adapter_sha256"] = _sha(out / "adapter397t.pt")
    res["dev_after_lora"] = dev_check(model, tok, dev, devrows)
    print(json.dumps({"dev_after_lora": res["dev_after_lora"]}), flush=True)

    res["merged_layers"] = merge_lora(model)
    model.eval()
    res["dev_after_merged"] = dev_check(model, tok, dev, devrows)
    print(json.dumps({"dev_after_merged": res["dev_after_merged"]}), flush=True)
    if not a.no_save:
        model.save_pretrained(out / "merged", safe_serialization=True)
        tok.save_pretrained(out / "merged")
        res["merged_files"] = {p.name: _sha(p) for p in sorted((out / "merged").glob("*.safetensors"))}
    res["seconds"] = round(time.time() - t0, 1)
    (out / "train397t.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("steps", "loss_first10", "loss_last10", "lora_params", "merged_layers",
                                          "seconds")}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
