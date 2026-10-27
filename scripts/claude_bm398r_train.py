#!/usr/bin/env python3
"""bm-398r training (benchmarks thread, 2026-09-26): the evidence-trained reader adapter. One change to the plain
MiniCPM5-1B: a LoRA trained on code-made practice for answering from chat lines (scripts/claude_bm398r_data.py).

Recipe (bm-397t's, so the practice data is what differs): claude_blurt2.add_lora, rank 16, alpha 32, dropout 0.05,
on q/k/v/o; 1 epoch; AdamW lr 2e-4, no weight decay; 8 examples a step (one at a time, gradients summed); clip 1.0;
seed 3992. Thinking off (enable_thinking=False). The loss is on the answer tokens and the end-of-turn token only.
New here, for LoCoMo-length inputs (up to ~28k tokens): gradient checkpointing (non-reentrant), and logits are
computed only for the answer positions (logits_to_keep), which gives the same loss as full labels.

The adapter file has bm-397t's key names (".A" / ".B"), so claude_bm398i_switch.load_adapter can load it behind the
on/off switch. The LoRA is also merged into a copy of the weights (OUT/merged) so the sealed bm-390 harness can
score it as `plain:<folder>`, exactly as the base 1B was scored.
Dev check (report only): the held-out dev set, greedy, 50 new tokens (bm-390's ANS_TOKENS), before and after.
A reply is right when every word of every comma part of the answer appears in it (bm-397t's rule); for a
"missing" question, when it abstains by bm-390's scorer rule.

  python -B scripts/claude_bm398r_train.py --base BASE --train train.jsonl --dev dev.jsonl --out OUT
      [--limit N --dev-limit N --no-save]   (smoke only)
  python -B scripts/claude_bm398r_train.py selftest   (tiny random Llama, CPU)
Writes OUT/adapter398r.pt, OUT/merged/, OUT/train398r.json (counts only).
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

import claude_bm397t_data as P  # noqa: E402  (correct(): the dev rule)

SEED = 3992
RANK, ALPHA, DROPOUT = 16, 32, 0.05
LR, BATCH, EPOCHS = 2e-4, 8, 1
MAX_NEW = 50
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


def answer_loss(model, p: list[int], t: list[int], dev: str):
    """Mean cross-entropy of the target tokens t after the prompt p, computing logits only where needed."""
    import torch
    ids = torch.tensor([p + t], device=dev)
    logits = model(input_ids=ids, logits_to_keep=len(t) + 1).logits[0, :-1].float()
    return torch.nn.functional.cross_entropy(logits, torch.tensor(t, device=dev))


def right(reply: str, r: dict) -> bool:
    if r["kind"] == "missing":
        import claude_bm390_score as S
        return bool(S.ABSTAIN.search(reply.lower()))
    return P.correct(reply, r["answer"])


def dev_check(model, tok, dev: str, rows: list[dict]) -> dict:
    import torch
    import claude_bm390 as B
    model.eval()
    by: dict = {}
    words = []
    for r in rows:
        ids = torch.tensor([_prompt_ids(tok, r)], device=dev)
        with torch.no_grad():
            out = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), max_new_tokens=MAX_NEW,
                                 do_sample=False, pad_token_id=tok.pad_token_id if tok.pad_token_id is not None
                                 else tok.eos_token_id)
        reply = B.strip_think(tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True))
        words.append(len(reply.split()))
        for key in (r["kind"], "layout:" + r["layout"]):
            by.setdefault(key, [0, 0])
            by[key][0] += int(right(reply, r))
            by[key][1] += 1
    return {"n": len(rows), "right": sum(v[0] for k, v in by.items() if not k.startswith("layout:")),
            "by": {k: f"{v[0]}/{v[1]}" for k, v in sorted(by.items())},
            "median_words": statistics.median(words) if words else 0}


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
    import claude_bm397t_train as T7
    import claude_bm398i_switch as SW
    ok, total = 0, 0

    def check(name, cond):
        nonlocal ok, total
        total += 1
        ok += int(cond)
        print(f"{'PASS' if cond else 'FAIL'} {name}")

    torch.manual_seed(0)
    cfg = LlamaConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
                      num_key_value_heads=2, max_position_embeddings=128)
    m = AutoModelForCausalLM.from_config(cfg)
    base_sd = {k: v.clone() for k, v in m.state_dict().items()}
    BL.add_lora(m, r=RANK, alpha=ALPHA, dropout=0.0)
    for mod in m.modules():
        if hasattr(mod, "B") and hasattr(mod, "base"):
            torch.nn.init.normal_(mod.B, std=0.05)
    m.eval()
    p, t = list(range(3, 40)), [7, 9, 11, 2]
    ids = torch.tensor([p + t])
    lab = ids.clone()
    lab[0, :len(p)] = -100
    full = m(input_ids=ids, labels=lab).loss
    check("answer-only logits give the labels loss", abs(answer_loss(m, p, t, "cpu").item() - full.item()) < 1e-5)
    m.train()
    for q in m.parameters():
        q.grad = None
    answer_loss(m, p, t, "cpu").backward()
    g0 = [q.grad.clone() for q in m.parameters() if q.requires_grad]
    m.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    for q in m.parameters():
        q.grad = None
    answer_loss(m, p, t, "cpu").backward()
    g1 = [q.grad for q in m.parameters() if q.requires_grad]
    check("checkpointing gives the same gradients", all((a - b).abs().max().item() < 1e-6 for a, b in zip(g0, g1)))
    check("only LoRA weights train", all(n.endswith((".A", ".B")) for n, q in m.named_parameters() if q.requires_grad))
    m.gradient_checkpointing_disable()
    m.eval()
    x = torch.randint(0, 64, (1, 12))
    lora_out = m(input_ids=x).logits
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "a.pt"
        torch.save({k: v.detach().cpu() for k, v in m.state_dict().items() if k.endswith(".A") or k.endswith(".B")},
                   path)
        sw = AutoModelForCausalLM.from_config(cfg)
        sw.load_state_dict(base_sd)
        sw.eval()
        base_out = sw(input_ids=x).logits
        SW.wrap(sw)
        SW.load_adapter(sw, str(path))
        SW.set_on(sw, True)
        on_out = sw(input_ids=x).logits
        SW.set_on(sw, False)
        off_out = sw(input_ids=x).logits
    check("the adapter file loads behind bm-398i's switch; on = trained LoRA",
          (on_out - lora_out).abs().max().item() < 1e-5)
    check("switch off = base exactly", (off_out - base_out).abs().max().item() == 0.0)
    T7.merge_lora(m)
    check("merged = LoRA", (m(input_ids=x).logits - lora_out).abs().max().item() < 1e-4)
    print(f"BM398R-TRAIN-SELFTEST {'PASS' if ok == total else 'FAIL'} {ok}/{total}")
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
    import claude_bm397t_train as T7
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
                      "seed": SEED, "checkpointing": True, "answer_only_logits": True}}
    res["dev_before"] = dev_check(model, tok, dev, devrows)
    print(json.dumps({"dev_before": res["dev_before"], "s": round(time.time() - t0)}), flush=True)

    torch.manual_seed(SEED)
    BL.add_lora(model, r=RANK, alpha=ALPHA, dropout=DROPOUT)
    params = [p for p in model.parameters() if p.requires_grad]
    res["lora_params"] = sum(p.numel() for p in params)
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)
    order = list(range(len(train)))
    random.Random(SEED).shuffle(order)
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.config.use_cache = False
    model.train()
    losses, steps, n_tok, t_train = [], 0, 0, time.time()
    if dev == "cuda":
        torch.cuda.reset_peak_memory_stats()
    for ep in range(EPOCHS):
        for i in range(0, len(order), BATCH):
            batch = [train[j] for j in order[i:i + BATCH]]
            tot = 0.0
            for r in batch:
                p, t = _prompt_ids(tok, r), _target_ids(tok, r["answer"])
                n_tok += len(p) + len(t)
                loss = answer_loss(model, p, t, dev) / len(batch)
                loss.backward()
                tot += float(loss.detach())
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            opt.zero_grad()
            losses.append(tot)
            steps += 1
            if steps % 5 == 0 or steps == 1:
                el = time.time() - t_train
                print(json.dumps({"step": steps, "loss": round(tot, 4), "s": round(el),
                                  "projected_train_s": round(el / steps * len(range(0, len(order), BATCH))),
                                  "tokens": n_tok}), flush=True)
    model.gradient_checkpointing_disable()
    model.config.use_cache = True
    res["steps"] = steps
    res["train_seconds"] = round(time.time() - t_train, 1)
    res["train_tokens"] = n_tok
    res["peak_gpu_mb"] = round(torch.cuda.max_memory_allocated() / 2 ** 20) if dev == "cuda" else 0
    res["loss_first10"] = round(sum(losses[:10]) / max(1, len(losses[:10])), 4)
    res["loss_last10"] = round(sum(losses[-10:]) / max(1, len(losses[-10:])), 4)
    torch.save({k: v.detach().cpu() for k, v in model.state_dict().items() if k.endswith(".A") or k.endswith(".B")},
               out / "adapter398r.pt")
    res["adapter_sha256"] = _sha(out / "adapter398r.pt")
    res["dev_after_lora"] = dev_check(model, tok, dev, devrows)
    print(json.dumps({"dev_after_lora": res["dev_after_lora"], "s": round(time.time() - t0)}), flush=True)
    res["merged_layers"] = T7.merge_lora(model)
    model.eval()
    res["dev_after_merged_first40"] = dev_check(model, tok, dev, devrows[:40])
    print(json.dumps({"dev_after_merged_first40": res["dev_after_merged_first40"]}), flush=True)
    if not a.no_save:
        model.save_pretrained(out / "merged", safe_serialization=True)
        tok.save_pretrained(out / "merged")
        res["merged_files"] = {p.name: _sha(p) for p in sorted((out / "merged").glob("*.safetensors"))}
    res["seconds"] = round(time.time() - t0, 1)
    (out / "train398r.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("steps", "loss_first10", "loss_last10", "lora_params", "merged_layers",
                                          "train_seconds", "train_tokens", "peak_gpu_mb", "seconds")}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
