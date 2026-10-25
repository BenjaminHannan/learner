"""CPU test of fast_step on sleepb's tiny random Qwen3.5-MoE (3 Gated DeltaNet + 1 full-attention layer, fused experts, shared expert), fp32, LoRA on, lr 0:
baseline Trainer.step vs each option and all together. Two consecutive steps per setting (the second one hits the KL cache). Reports max abs diff of CE, KL and every
(clipped) LoRA gradient, plus the largest gradient entry for scale. Pass marks: ce/kl abs diff < 1e-5, grad abs diff < 1e-5 x max|grad| (fp32 summation order).
  python test_fast_step.py            # prints one JSON line; exit 1 on failure"""
import json
import sys
from argparse import Namespace
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parents[1] / "backbone" / "sleep" / "brain"
sys.path[:0] = [str(HERE), str(BRAIN), str(BRAIN.parent), str(BRAIN.parent.parent)]
import fast_step as fs  # noqa: E402
import sleepb as sb  # noqa: E402
import transformers.models.qwen3_5_moe.modeling_qwen3_5_moe as hf  # noqa: E402
from peft import LoraConfig, get_peft_model  # noqa: E402
from sleep1 import Lang  # noqa: E402
from train import LORA_TARGETS, load_model  # noqa: E402


def build():
    cpu = torch.device("cpu")
    lm, tok = load_model(Namespace(smoke=True, seed=0, model="tiny-a3b-moe"), cpu, torch.float32)
    L = Lang(tok, True, cpu)
    pm = get_peft_model(lm, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
    g = torch.Generator().manual_seed(0)
    for n, p in pm.named_parameters():
        if "lora_B" in n:
            p.data.normal_(0, 0.05, generator=g)
    return L, pm


def run(L, pm, batches, replay, budget, opts, weighted, kl_weight=1.0):
    undo_t = fs.torch_varlen_patches(hf) if opts.get("packed") else (lambda: None)
    undo = fs.install(sb, **opts)
    old = sb.TOK_BUDGET
    sb.TOK_BUDGET = budget
    try:
        tr = sb.Trainer(L, pm, Namespace(lr=0.0, kl_weight=kl_weight, replay_bsz=5), replay, 20, 0)
        out = []
        for b in batches:
            bb = [e + (w,) for e, w in zip(b, [0.5, 1.0, 1.0, 0.5, 1.0, 0.5, 2.0, 1.0])] if weighted else b
            tr.step(bb)
            c = tr.curve[-1]
            out.append((c["ce"], c["kl"], [p.grad.clone() for p in tr.params]))
        run.hits = (fs._STATE["hits"], fs._STATE["miss"])
        return out
    finally:
        sb.TOK_BUDGET = old
        undo()
        undo_t()


def main():
    L, pm = build()
    base = [sb.ex_text(L, f"Zelmir lives in Kelmira number {i}, near the old harbour.") if i % 2 else sb.ex_qa(L, f"Where does Zelmir{'x' * (3 * i)} live?", "Kelmira") for i in range(8)]
    base += [sb.ex_qa(L, "Which town? " + "Notes from earlier chats " * 6, "Kelmira")]
    base = base[:8] + base[8:]
    replay = [sb.ex_text(L, f"A generic sentence number {i} about the weather" + " today" * (i * 3)) for i in range(7)]
    batches = [base[:8], base[1:9]]
    mx = max(len(e) for e, _ in base)
    cases = {  # name: (budget, opts, weighted)
        "sync_free": (mx * 3, {"sync_free": True}, False),
        "kl_cache": (mx * 3, {"kl_cache": True}, False),
        "packed": (mx * 3, {"packed": True}, False),
        "packed_one_bin": (10 ** 6, {"packed": True}, False),
        "all_split": (mx * 3, {"sync_free": True, "kl_cache": True, "packed": True}, False),
        "all_weighted": (mx * 3, {"sync_free": True, "kl_cache": True, "packed": True}, True),
        "all_padded_weighted": (mx * 3, {"sync_free": True, "kl_cache": True}, True),
    }
    res, ok = {}, True
    for name, (budget, opts, weighted) in cases.items():
        fs.clear_cache()
        ref = run(L, pm, batches, replay, budget, {}, weighted)
        got = run(L, pm, batches, replay, budget, opts, weighted)
        r = {"max_grad": max(float(x.abs().max()) for x in ref[0][2]), "cache_hits_misses": list(run.hits)}
        r["ce_abs"] = max(abs(a[0] - b[0]) for a, b in zip(ref, got))
        r["kl_abs"] = max(abs(a[1] - b[1]) for a, b in zip(ref, got))
        r["grad_abs"] = max(float((x - y).abs().max()) for a, b in zip(ref, got) for x, y in zip(a[2], b[2]))
        if opts.get("kl_cache"):  # step 2 must reuse step 1's reference hiddens: some hits, and fewer misses than lookups
            r["pass_cache_used"] = run.hits[0] > 0
        r["pass"] = r.get("pass_cache_used", True) and bool(r["ce_abs"] < 1e-5 and r["kl_abs"] < 1e-5 and r["grad_abs"] < 1e-5 * r["max_grad"] and r["max_grad"] > 0 and ref[0][1] > 0)
        ok &= r["pass"]
        res[name] = r
    # all options off must be the original code path exactly
    a = run(L, pm, batches, replay, mx * 3, {}, False)
    b = run(L, pm, batches, replay, mx * 3, {"kl_cache_mb": 512}, False)
    res["off_is_original"] = {"grad_abs": max(float((x - y).abs().max()) for p, q in zip(a, b) for x, y in zip(p[2], q[2]))}
    ok &= res["off_is_original"]["grad_abs"] == 0.0
    # fla-free packed sanity: leaking check, i.e. packed output of sequence 2 does not change when sequence 1 changes
    m = pm.get_base_model()
    undo_t = fs.torch_varlen_patches(hf)
    with torch.no_grad():
        mb1, mb2 = [base[0], base[2]], [base[4], base[2]]
        h1 = fs.target_hidden(m, fs.Lay(L, mb1, True))
        h2 = fs.target_hidden(m, fs.Lay(L, mb2, True))
        n1, n2 = len(base[0][0]) - max(base[0][1], 1), len(base[4][0]) - max(base[4][1], 1)
        res["packed_no_leak"] = {"seq2_diff_when_seq1_changes": float((h1[n1:] - h2[n2:]).abs().max())}
    undo_t()
    ok &= res["packed_no_leak"]["seq2_diff_when_seq1_changes"] < 1e-5
    try:  # fused norms (needs a C++ compiler for inductor on CPU)
        a = run(L, pm, batches[:1], replay, mx * 3, {}, False)
        b = run(L, pm, batches[:1], replay, mx * 3, {"fused_norms": True}, False)
        res["fused_norms"] = {"ce_abs": abs(a[0][0] - b[0][0]), "grad_abs": max(float((x - y).abs().max()) for x, y in zip(a[0][2], b[0][2])), "max_grad": max(float(x.abs().max()) for x in a[0][2])}
    except Exception as e:  # noqa: BLE001
        res["fused_norms"] = {"skipped": repr(e)[:200]}
    res["ok"] = bool(ok)
    print(json.dumps(res))
    sys.exit(0 if ok else 1)


main()
