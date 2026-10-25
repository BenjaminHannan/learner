"""Sleep race fast-track feasibility probe (add-on thread): can K2-Horizon-3.7B with the MLX 4-bit fake-quant base sleep in fp16 on a Kaggle T4?

Writes --out/probe.json with:
  finite: per decoder layer, the largest |hidden state| on 40 prompts (ARC + chat-week style) and whether any value was inf/nan, fp16 vs fp32 reference
          on the same prompts is not possible on 15 GB, so the check is absolute: fp16 max is 65504; anything above 3e4 is flagged as near-overflow.
  arc_val: ARC-Easy validation accuracy (first 100) of the q4 base in fp16 (the 5090 bf16 runs read 0.82 for the q4 base, 0.90 for bf16).
  step: seconds per Trainer-like forward+backward of a 16-example batch (sleepb.bench_chip, LoRA r16 fp32 adapters), and one generation batch.
  peak_gb: peak CUDA memory.
Usage (repo root): python backbone/sleep/brain/race/k2_fp16_probe.py --out /kaggle/working/probe [--gen-bs 16] [--tok-budget 1024]
"""
import argparse
import json
import sys
import time
from argparse import Namespace
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent.parent.parent))
import sleepb as S  # noqa: E402

K2 = "IFM/K2-Horizon-3.7B"
K2_REV = "9d280ff742235796925c9fe3cf243dc1beea5c08"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--gen-bs", type=int, default=16)
    ap.add_argument("--tok-budget", type=int, default=1024)
    ap.add_argument("--bsz", type=int, default=16)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {"gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"}
    dev = torch.device("cuda")
    t0 = time.time()
    args = Namespace(model=K2, revision=K2_REV, smoke=False, seed=1)
    lm, tok = S.load_model(args, dev, torch.float16)
    res["load_s"] = time.time() - t0
    res["q4"] = {k: v for k, v in S.q4_apply(lm, 64, 4).items() if k != "per_tensor"}
    L = S.Lang(tok, False, dev, k2=True)
    S.TOK_BUDGET = a.tok_budget

    # 1. finiteness of every decoder layer's output
    stats = {}

    def hook(i):
        def f(_m, _inp, o):
            h = o[0] if isinstance(o, tuple) else o
            st = stats.setdefault(i, {"max": 0.0, "nonfinite": False})
            st["nonfinite"] |= not bool(torch.isfinite(h).all())
            st["max"] = max(st["max"], float(h.detach().abs().float().nan_to_num(posinf=7e4).max()))
        return f

    layers = lm.model.layers
    hs = [m.register_forward_hook(hook(i)) for i, m in enumerate(layers)]
    arc = S.load_arc_val(False)
    week = json.loads((HERE.parent / "data" / "week2.json").read_text())
    turns = [t["text"] for t in week["diary"] if t["role"] == "user"][:20]
    prompts = [L.render(S.SYS, r["question"]) for r in arc[:20]] + [L.render(S.SYS, t) for t in turns]
    with torch.no_grad():
        for i in range(0, len(prompts), 4):
            ids, mask = L.pad_right([L.ids(p) for p in prompts[i:i + 4]])
            lm(input_ids=ids, attention_mask=mask)
    for h in hs:
        h.remove()
    res["finite"] = {"layers": stats, "any_nonfinite": any(v["nonfinite"] for v in stats.values()),
                     "max_abs": max(v["max"] for v in stats.values()), "near_overflow_layers": [i for i, v in stats.items() if v["max"] > 3e4],
                     "n_prompts": len(prompts)}
    (out / "probe.json").write_text(json.dumps(res, indent=1))

    # 2. ARC-Easy val (100) on the q4 fp16 base
    t1 = time.time()
    res["arc_val"] = S.score_arc(L, lm, arc, bs=max(a.gen_bs // 2, 1))["acc"]
    res["arc_s"] = time.time() - t1
    (out / "probe.json").write_text(json.dumps(res, indent=1))

    # 3. train step + generation speed with fp32 LoRA r16 on all 7 targets
    from peft import LoraConfig, get_peft_model
    pm = get_peft_model(lm, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules=S.LORA_TARGETS, bias="none"))
    res["lora_dtype"] = str(next(p for n, p in pm.named_parameters() if "lora_A" in n).dtype)
    torch.cuda.reset_peak_memory_stats()
    try:
        res["step"] = S.bench_chip(L, pm, Namespace(bsz=a.bsz, gen_bs=a.gen_bs), ref_steps=1200)
    except torch.cuda.OutOfMemoryError as e:
        res["step"] = {"oom": str(e)[:300]}
    res["peak_gb"] = torch.cuda.max_memory_allocated() / 2**30
    res["total_s"] = time.time() - t0
    (out / "probe.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1)[:4000])


if __name__ == "__main__":
    main()
