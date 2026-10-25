"""CPU test of fast_experts (frozen routed-expert grouped GEMM) on sleepb's tiny random Qwen3.5-MoE, fp32, LoRA, experts_implementation=grouped_mm.
(1) loss and LoRA grads of Trainer.step with fast_experts vs the original path (backends "torch" = per-expert loop in one autograd.Function, "triton" = the kernel run by the Triton
interpreter on CPU), alone and with kl_cache; pass: CE/KL abs diff < 1e-5, grad abs diff < 1e-5 x max|grad|. (2) aten::mm / aten::_grouped_mm call counts of one step under torch.profiler:
original path, "torch" backend (= the structure of torch 2.9's sm_120 fallback: one mm per expert in forward and in the grad_input backward), "triton" backend (0 mm from the experts).
The CPU counts show the structure only; the 143k/step figure is from the GPU profile. Needs triton: pip install triton; the test sets TRITON_INTERPRET=1 itself.
  python test_fast_experts.py     # prints one JSON line; exit 1 on failure"""
import json
import os
import sys
from argparse import Namespace
from pathlib import Path

os.environ.setdefault("TRITON_INTERPRET", "1")
import torch

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parents[1] / "backbone" / "sleep" / "brain"
sys.path[:0] = [str(HERE), str(BRAIN), str(BRAIN.parent), str(BRAIN.parent.parent)]
import fast_experts as fe  # noqa: E402
import fast_step as fs  # noqa: E402
import sleepb as sb  # noqa: E402
from peft import LoraConfig, get_peft_model  # noqa: E402
from sleep1 import Lang  # noqa: E402
from train import LORA_TARGETS, load_model  # noqa: E402
from torch.profiler import ProfilerActivity, profile  # noqa: E402


def build():
    cpu = torch.device("cpu")
    lm, tok = load_model(Namespace(smoke=True, seed=0, model="tiny-a3b-moe"), cpu, torch.float32)
    lm.set_experts_implementation("grouped_mm")
    L = Lang(tok, True, cpu)
    pm = get_peft_model(lm, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
    g = torch.Generator().manual_seed(0)
    for n, p in pm.named_parameters():
        if "lora_B" in n:
            p.data.normal_(0, 0.05, generator=g)
    exp = [p for n, p in pm.named_parameters() if "experts" in n]
    return L, pm, exp


def run(L, pm, batches, replay, opts, prof=False):
    undo = fs.install(sb, **opts)
    old = sb.TOK_BUDGET
    sb.TOK_BUDGET = 10 ** 6
    try:
        tr = sb.Trainer(L, pm, Namespace(lr=0.0, kl_weight=1.0, replay_bsz=5), replay, 20, 0)
        out = []
        for i, b in enumerate(batches):
            if prof and i == 0:
                with profile(activities=[ProfilerActivity.CPU]) as p:
                    tr.step(b)
                cnt = {e.key: e.count for e in p.key_averages() if e.key in ("aten::mm", "aten::_grouped_mm", "aten::bmm", "aten::item")}
            else:
                tr.step(b)
            c = tr.curve[-1]
            out.append((c["ce"], c["kl"], [q.grad.clone() for q in tr.params]))
        return (out, cnt) if prof else out
    finally:
        sb.TOK_BUDGET = old
        undo()
        fs.clear_cache()


def main():
    L, pm, exp = build()
    assert exp and not any(p.requires_grad for p in exp), "routed experts must be frozen"
    base = [sb.ex_text(L, f"Zelmir lives in Kelmira number {i}, near the old harbour.") if i % 2 else sb.ex_qa(L, f"Where does Zelmir{'x' * (3 * i)} live?", "Kelmira") for i in range(8)]
    replay = [sb.ex_text(L, f"A generic sentence number {i} about the weather" + " today" * (i * 3)) for i in range(7)]
    batches = [base[:8], base[1:8] + base[:1]]
    fe._BLOCK.update(BM=16, BN=32, BK=16)  # small tiles: the tiny model has ~10 rows per expert
    res, ok = {}, True
    ref = run(L, pm, batches, replay, {})
    mg = max(float(x.abs().max()) for x in ref[0][2])
    for name, opts in {"torch_backend": {"fast_experts": True, "experts_backend": "torch"}, "triton_backend": {"fast_experts": True, "experts_backend": "triton"},
                       "kl_cache+fast_experts": {"kl_cache": True, "fast_experts": True, "experts_backend": "triton"}}.items():
        got = run(L, pm, batches, replay, opts)
        r = {"max_grad": mg, "ce_abs": max(abs(a[0] - b[0]) for a, b in zip(ref, got)), "kl_abs": max(abs(a[1] - b[1]) for a, b in zip(ref, got)),
             "grad_abs": max(float((x - y).abs().max()) for a, b in zip(ref, got) for x, y in zip(a[2], b[2]))}
        r["pass"] = bool(r["ce_abs"] < 1e-5 and r["kl_abs"] < 1e-5 and r["grad_abs"] < 1e-5 * mg and mg > 0)
        ok &= r["pass"]
        res[name] = r
    counts = {}
    for name, opts in {"original": {}, "sm120_fallback_structure(torch backend)": {"fast_experts": True, "experts_backend": "torch"}, "fast_experts(triton)": {"fast_experts": True, "experts_backend": "triton"}}.items():
        counts[name] = run(L, pm, batches[:1], replay, opts, prof=True)[1]
    res["calls_per_step_cpu"] = counts
    ok &= counts["fast_experts(triton)"].get("aten::mm", 0) < counts["sm120_fallback_structure(torch backend)"].get("aten::mm", 0)
    res["ok"] = bool(ok)
    print(json.dumps(res))
    sys.exit(0 if ok else 1)


main()
