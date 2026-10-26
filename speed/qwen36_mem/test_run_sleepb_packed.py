"""CPU test of run_sleepb_packed.py on a tiny random Qwen3.5-MoE (hidden 256 so the experts and the 256x256 Linears really get packed; fp32). python speed/qwen36_mem/test_run_sleepb_packed.py -> one JSON line, exit 1 on failure.
(a) one sleepb.Trainer.step (CE + KL guard, 2 steps, split micro-batches): plain qdq base vs the runner's packed base + gradient checkpointing: CE, KL and every LoRA grad. Pass: abs diff < 1e-5 (fp32).
(b) a whole tiny `--arm ab_ob_b4_nb --smoke --q4-base --q4-mlx-moe` run through the runner's main() (all nights, dreams, eval) completes, packs the model, and gives the same scores as the plain sleepb run.
(c) generation after a checkpointed train step still works (use_cache path) and equals the plain model's greedy output."""
import contextlib
import io
import json
import os
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "../qwen36_step"), os.path.join(HERE, "../../backbone/sleep/brain"), os.path.join(HERE, "../../backbone/sleep"), os.path.join(HERE, "../../backbone")]
import torch  # noqa: E402

import packed as P  # noqa: E402
import run_sleepb_packed as R  # noqa: E402
import sleepb as sb  # noqa: E402
import test_packed as tp  # noqa: E402
from peft import LoraConfig, get_peft_model  # noqa: E402
from sleep1 import Lang  # noqa: E402
from train import LORA_TARGETS, ByteTok  # noqa: E402

tp.DT = torch.float32
CPU = torch.device("cpu")
LOAD0 = sb.load_model


def tiny_load(args, device, dtype):  # sleepb.load_model stand-in: the 256-hidden tiny Qwen3.5-MoE of test_packed (fp32), byte tokenizer
    lm = tp.tiny()
    return lm, ByteTok(512)


def build(packed, ckpt):
    """(L, pm): tiny model with the q4 recipe applied the plain way or through the runner's hooked q4_apply; LoRA with a fixed non-zero init."""
    sb.load_model = tiny_load
    undo = R.install(sb, grad_ckpt=ckpt, packed_min_numel=0) if packed else (lambda: None)
    try:
        args = Namespace(smoke=True, seed=0, q4_base=True, q4_mlx_moe=True)
        lm, tok = sb.load_model(args, CPU, torch.float32)
        st = sb.q4_apply(lm, 64, 4, sb.Q4_MLX_MOE_BITS, sb.Q4_MLX_MOE_PARAMS)
    finally:
        undo()  # the model is built; hooks off (they are re-installed around the step)
        sb.load_model = LOAD0
    cfg = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=LORA_TARGETS + r"|.*\.layers\.\d+\.mlp\.shared_expert\.(gate_proj|up_proj|down_proj)", bias="none")
    pm = get_peft_model(lm, cfg)
    g = torch.Generator().manual_seed(0)
    for n, p in pm.named_parameters():
        if "lora_B" in n:
            p.data.normal_(0, 0.05, generator=g)
    return Lang(tok, True, CPU), pm, st


def steps(L, pm, batches, replay, ckpt, packed):
    undo = R.install(sb, grad_ckpt=ckpt, packed_min_numel=0) if packed else (lambda: None)
    old = sb.TOK_BUDGET
    sb.TOK_BUDGET = max(len(e) for e, *_ in batches[0]) * 3  # forces the split (micro-batch) path
    try:
        tr = sb.Trainer(L, pm, Namespace(lr=0.0, kl_weight=1.0, replay_bsz=5), replay, 20, 0)
        out = []
        for b in batches:
            tr.step(b)
            c = tr.curve[-1]
            out.append((c["ce"], c["kl"], [p.grad.clone() for p in tr.params]))
        return out, tr
    finally:
        sb.TOK_BUDGET = old
        undo()


def test_step(res):
    Lr, pm_r, _ = build(False, False)
    Lp, pm_p, st = build(True, True)
    n_pk = sum(isinstance(m, P.PackedTensor) for m in pm_p.modules())
    assert st["packed"]["packed_experts"] == 8 and st["packed"]["packed_linear"] > 0, st  # fused experts (2 x 4 layers) and Linears really packed
    base = [sb.ex_text(Lr, f"Zelmir lives in Kelmira number {i}, near the old harbour.") if i % 2 else sb.ex_qa(Lr, f"Where does Zelmir{'x' * (3 * i)} live?", "Kelmira") for i in range(8)]
    replay = [sb.ex_text(Lr, f"A generic sentence number {i} about the weather" + " today" * (i * 3)) for i in range(7)]
    batches = [base[:8], base[1:8] + base[:1]]
    ref, tr_r = steps(Lr, pm_r, batches, replay, False, False)
    got, tr_p = steps(Lp, pm_p, batches, replay, True, True)
    base_p = pm_p.get_base_model()
    r = {"packed_tensors": n_pk, "ckpt_flag_on": bool(base_p.is_gradient_checkpointing), "max_grad": max(float(x.abs().max()) for x in ref[0][2]), "ref_kl": ref[0][1]}
    r["ce_abs"] = max(abs(a[0] - b[0]) for a, b in zip(ref, got))
    r["kl_abs"] = max(abs(a[1] - b[1]) for a, b in zip(ref, got))
    r["grad_abs"] = max(float((x - y).abs().max()) for a, b in zip(ref, got) for x, y in zip(a[2], b[2]))
    r["n_lora_grads"] = len(ref[0][2])
    r["pass"] = bool(r["ce_abs"] < 1e-5 and r["kl_abs"] < 1e-5 and r["grad_abs"] < 1e-5 and r["max_grad"] > 0 and r["ref_kl"] > 0 and r["ckpt_flag_on"])
    res["a_train_step"] = r
    # (c) generation after the checkpointed steps (eval mode, use_cache) equals the plain model's
    pm_r.eval(), pm_p.eval()
    prompts = [Lr.render(None, q) for q in ("Where does Zelmir live?", "What is the weather today?")]
    go_r, go_p = Lr.generate(pm_r, prompts, max_new=8), Lp.generate(pm_p, prompts, max_new=8)
    with torch.no_grad():
        ids = torch.tensor([Lr.ids(prompts[0])])
        kv = pm_p(input_ids=ids, use_cache=True).past_key_values is not None
    r2 = {"generate_equal": go_r == go_p, "past_key_values_returned_after_ckpt": bool(kv), "outputs": go_p}
    r2["pass"] = r2["generate_equal"] and r2["past_key_values_returned_after_ckpt"]
    res["c_generate_after_ckpt"] = r2
    return r["pass"] and r2["pass"]


def run_main(use_runner, out):
    argv = ["--arm", "ab_ob_b4_nb", "--smoke", "--out", str(out), "--q4-base", "--q4-mlx-moe", "--model", "tiny-a3b-moe"]
    buf = io.StringIO()

    class Tee(io.TextIOBase):
        def write(s, x):
            buf.write(x)
            return len(x)
    sb.load_model = tiny_load
    try:
        with contextlib.redirect_stdout(Tee()):
            if use_runner:
                R.main(["--grad-ckpt", "--kl-cache", "--packed-min-numel", "0", "--"] + argv)
            else:
                sys.argv = ["sleepb.py"] + argv
                sb.main()
    finally:
        sb.load_model = LOAD0
    return buf.getvalue(), json.loads((Path(out) / "result_ab_ob_b4_nb.json").read_text())


def test_e2e(res):
    with tempfile.TemporaryDirectory() as d:
        txt_p, r_p = run_main(True, Path(d) / "packed")
        txt_q, r_q = run_main(False, Path(d) / "plain")
    line = next((l for l in txt_p.splitlines() if l.startswith("[packed]")), None)
    ck = "[ckpt] gradient checkpointing on" in txt_p
    same = json.dumps(r_p["scores"], sort_keys=True) == json.dumps(r_q["scores"], sort_keys=True)
    r = {"completed": True, "packed_line": line, "ckpt_enabled": ck, "nights_packed": len(r_p.get("nights", [])), "nights_plain": len(r_q.get("nights", [])), "scores_equal_plain": same,
         "plain_has_no_packed_line": not any(l.startswith("[packed]") for l in txt_q.splitlines())}
    r["pass"] = bool(line and ck and same and r["nights_packed"] == r["nights_plain"] > 0 and r["plain_has_no_packed_line"])
    res["b_end_to_end_smoke"] = r
    return r["pass"]


def main():
    res = {"torch": torch.__version__}
    ok = test_step(res)
    ok &= test_e2e(res)
    res["ok"] = bool(ok)
    print(json.dumps(res, default=str))
    sys.exit(0 if ok else 1)


main()
