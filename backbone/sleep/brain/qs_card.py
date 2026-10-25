"""Sleep race round 1, card test (Week-1 world only; never the Week-2 scoreboard): can whole-model 4-bit scale sleep (--storage qs in sleepb.py)
store facts as well as the LoRA add-on at equal steps, and at which lr?

One model load (K2-Horizon-3.7B by default, 4-bit fake-quantized base exactly as sleepb.py --q4-base), then for each arm (fresh start each time):
  lora:LR   the add-on (rank 16, alpha 32, sleepb's LoRA targets), qs frozen at zero
  qs:LR     the per-group 4-bit scale / offset changes u, v of every target layer, LoRA frozen
Training: --steps steps of sleepb's Trainer (fresh AdamW, cosine lr, CE + KL guard on generic replay vs the base, as in a sleep night) on batches of
--bsz examples drawn from: the Week-1 fact sentences (item text) and the Week-1 forward test questions with their answers (closed-book Q&A).
Scores per arm: recall on the trained forward questions (greedy, answer contained), the reverse questions of the same facts (not trained),
ARC-Easy validation 100 vs the base, mean KL on 32 held-out generic prompts. qs arms are scored again after rounding the stored scales / offsets
to bf16 (nearest): the served 4-bit file.

Pick rule (fixed before the run, PREREG-race-r1.md): on the served copy with fp16 nearest rounding (race rule 3; sleepb.py --storage qs --qs-store fp16),
the qs lr with the highest trained-question recall among those whose ARC drop is <= 3 points; ties -> the lower lr.

  python backbone/sleep/brain/qs_card.py --out out/qs_card                         # K2, fp32 across the visible GPUs (2 x T4 on Kaggle)
  python backbone/sleep/brain/qs_card.py --smoke --out /tmp/qc                       # CPU, tiny random model
"""
import argparse
import json
import random
import sys
import time
from argparse import Namespace
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import sleepb as sb  # noqa: E402
from sleep1 import SYS, Lang, generic_prompts, score_arc  # noqa: E402
from train import K2_TYPE, LORA_TARGETS, load_model  # noqa: E402

K2 = "IFM/K2-Horizon-3.7B"
K2_REV = "9d280ff742"


def load(args, device, dtype):
    if args.smoke or device.type != "cuda" or torch.cuda.device_count() < 2:
        return load_model(args, device, dtype)
    from transformers import AutoModelForCausalLM, AutoTokenizer  # several GPUs (Kaggle 2 x T4): split the layers across them
    kw = {"revision": args.revision, "trust_remote_code": True} if args.revision else {"trust_remote_code": True}
    tok = AutoTokenizer.from_pretrained(args.model, **kw)
    lm = AutoModelForCausalLM.from_pretrained(args.model, dtype=dtype, device_map="auto", **kw)
    return lm, tok


@torch.no_grad()
def recall(L, model, qs, bs):
    outs, _ = sb.generate_p(L, model, [L.render(SYS, t["q"]) for t in qs], max_new=20, bs=bs)
    return sum(sb.has_ans(t["target"], o) for t, o in zip(qs, outs)) / max(len(qs), 1)


@torch.no_grad()
def mean_kl(L, pm, prompts_ids):
    tot = n = 0.0
    for e in prompts_ids:
        ids = torch.tensor([e], device=L.device)
        cur = F.log_softmax(pm(input_ids=ids).logits[0].float(), -1)
        with pm.disable_adapter():
            ref = F.log_softmax(pm(input_ids=ids).logits[0].float(), -1)
        tot += float(F.kl_div(cur, ref, log_target=True, reduction="sum"))
        n += cur.shape[0]
    return tot / max(n, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=K2)
    ap.add_argument("--revision", default=K2_REV)
    ap.add_argument("--week", default=str(HERE / "data" / "week1.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--arms", default="lora:2e-4,qs:1e-3,qs:3e-3,qs:1e-2,qs:3e-2")
    ap.add_argument("--steps", type=int, default=150)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--replay-n", type=int, default=64)
    ap.add_argument("--gen-bs", type=int, default=8)
    ap.add_argument("--tok-budget", type=int, default=1024)
    ap.add_argument("--dtype", choices=["fp32", "fp16", "bf16"], default="fp32")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        args.model, args.revision, args.steps, args.replay_n, args.bsz = "Qwen/Qwen3.5-2B", None, 6, 4, 4
    sb.TOK_BUDGET = args.tok_budget
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    logf = open(out / "log_qs_card.txt", "a")

    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")
        logf.flush()
    t0 = time.time()
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    dtype = {"fp32": torch.float32, "fp16": torch.float16, "bf16": torch.bfloat16}[args.dtype] if device.type == "cuda" else torch.float32
    lm, tok = load(args, device, dtype)
    q4 = sb.q4_apply(lm, 64, 4)
    log(f"[q4] {q4}")
    L = Lang(tok, args.smoke, device, k2=lm.config.model_type == K2_TYPE)
    from peft import LoraConfig, get_peft_model
    pm = get_peft_model(lm, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
    lora0 = {n: p.detach().clone() for n, p in pm.named_parameters() if "lora_" in n}
    qs_setup = sb.setup_qs(pm, 64, 4, dtype)
    log(f"[qs] {qs_setup}")
    mods = sb.qs_mods(pm)
    week = json.loads(Path(args.week).read_text())
    if args.smoke:
        week = sb.smoke_week()
    items = {it["id"]: it for it in week["items"]}
    fwd = [t for t in week["tests"]["forward"] if t["item"] in items]
    rev = [t for t in week["tests"]["reverse"] if t["item"] in {f["item"] for f in fwd}]
    texts = sorted({items[t["item"]]["text"] for t in fwd})
    pool = [sb.ex_text(L, x) for x in texts] + [sb.ex_qa(L, t["q"], t["target"]) for t in fwd]
    log(f"[data] {len(fwd)} forward Qs (trained), {len(rev)} reverse Qs (not trained), {len(texts)} fact sentences; pool {len(pool)}")
    gp = generic_prompts()
    tr_prompts, ho_prompts = [L.render(None, g) for g in gp[:args.replay_n]], [L.render(None, g) for g in gp[-32:]]
    with pm.disable_adapter():
        resp = L.generate(pm, tr_prompts, max_new=8 if args.smoke else 32, bs=args.gen_bs)
    replay = [(L.ids(p) + L.ids(r) + [L.eos], len(L.ids(p))) for p, r in zip(tr_prompts, resp)]
    ho_ids = [L.ids(p) for p in ho_prompts]
    arc_rows = sb.load_arc_val(args.smoke)
    for n, p in pm.named_parameters():
        p.requires_grad_(False)
    with pm.disable_adapter():
        base = {"arc": score_arc(L, pm, arc_rows, bs=args.gen_bs)["acc"], "fwd": recall(L, pm, fwd, args.gen_bs), "rev": recall(L, pm, rev, args.gen_bs)}
    log(f"[base] {base}")
    res = {"args": vars(args), "q4": q4, "qs_setup": qs_setup, "base": base, "n_fwd": len(fwd), "n_rev": len(rev), "arms": {}}
    for spec in args.arms.split(","):
        kind, lr = spec.split(":")
        lr = float(lr)
        with torch.no_grad():  # fresh start: LoRA back to its init (B = 0), u = v = 0
            for n, p in pm.named_parameters():
                if n in lora0:
                    p.copy_(lora0[n])
            for _, bl in mods:
                bl.qs_u.zero_()
                bl.qs_v.zero_()
        for n, p in pm.named_parameters():
            p.requires_grad_(("lora_" in n) if kind == "lora" else (n.endswith("qs_u") or n.endswith("qs_v")))
        targs = Namespace(lr=lr, kl_weight=1.0, replay_bsz=8, freeze_lora=kind == "qs")
        tr = sb.Trainer(L, pm, targs, replay, args.steps, args.seed)
        rng = random.Random(args.seed)
        ta = time.time()
        for _ in range(args.steps):  # qs arms: the Trainer re-freezes the LoRA (freeze_lora), which leaving disable_adapter() makes trainable again
            tr.step(rng.sample(pool, min(args.bsz, len(pool))))
        r = {"kind": kind, "lr": lr, "train_s": round(time.time() - ta, 1), "trainable": sum(p.numel() for p in tr.params), "curve": tr.curve,
             "fwd": recall(L, pm, fwd, args.gen_bs), "rev": recall(L, pm, rev, args.gen_bs), "arc": score_arc(L, pm, arc_rows, bs=args.gen_bs)["acc"], "kl_heldout": mean_kl(L, pm, ho_ids)}
        if kind == "qs":  # the served 4-bit file: stored scales / offsets rounded once, three ways, each from the same trained u, v
            r["qs_norm"] = sb.qs_norm(pm)
            uv = [(bl.qs_u.detach().clone(), bl.qs_v.detach().clone()) for _, bl in mods]
            for tag, dt, mode in (("bf16_nearest", torch.bfloat16, "nearest"), ("bf16_stochastic", torch.bfloat16, "stochastic"), ("fp16_nearest", torch.float16, "nearest")):
                with torch.no_grad():
                    for (_, bl), (u0, v0) in zip(mods, uv):
                        bl.qs_u.copy_(u0)
                        bl.qs_v.copy_(v0)
                m = sb.qs_morning(pm, 1.0, dt, mode, torch.Generator().manual_seed(args.seed))
                r["served_" + tag] = {"fwd": recall(L, pm, fwd, args.gen_bs), "arc": score_arc(L, pm, arc_rows, bs=args.gen_bs)["acc"],
                                      **{k: m[k] for k in ("mean_abs_u", "mean_abs_v_steps", "share_S_changed", "share_B_changed", "round_err_energy_frac")}}
        res["arms"][spec] = r
        log(f"[arm {spec}] " + json.dumps({k: v for k, v in r.items() if k != "curve"}))
        (out / "result_qs_card.json").write_text(json.dumps(res, indent=1))
    ok = [(v["served_fp16_nearest"]["fwd"], -v["lr"], k) for k, v in res["arms"].items() if v["kind"] == "qs" and v["served_fp16_nearest"]["arc"] >= base["arc"] - 0.03 - 1e-9]
    res["pick"] = max(ok)[2] if ok else None
    res["wall_s"] = round(time.time() - t0, 1)
    (out / "result_qs_card.json").write_text(json.dumps(res, indent=1))
    log(f"[pick] {res['pick']} wall {res['wall_s']}s")


if __name__ == "__main__":
    main()
