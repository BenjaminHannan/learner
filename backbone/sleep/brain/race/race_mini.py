"""Race-mini (PROTOCOL-mini.md in /mnt/project-files/sleep-race/mini/): race only the STORAGE of sleep on a fixed, shared dream tape.

Each night d of the week: the item values seen on >= 2 days up to d (C2, C4, changing facts at their value as of day d, routines; C1 never) are
studied for --steps Trainer steps (sleepb.Trainer: fresh AdamW, cosine lr, CE + KL guard on generic replay vs the base), batches of --bsz drawn
uniformly over tonight's values, half sentences (the item sentence or a tape paraphrase) and half tape Q&A (closed book). Then the side's own
morning step: --storage lora: sleepb SHY on the LoRA (x0.85, small singular values zeroed); --storage qs: sleepb qs_morning (u, v x0.85, scales /
offsets rounded to --qs-store). No morning gate. Scores (weights only, greedy, sleepb.score_week rows) after night 4 and after the last night;
ARC-Easy 500 at the end (base ARC-Easy 500 once, cached next to --out), mean KL on 32 held-out generic prompts.

  python backbone/sleep/brain/race/race_mini.py --tape tape_week2.json --week backbone/sleep/brain/data/week2.json --storage lora --seed 1 --out out/rm/lora_s1
  python backbone/sleep/brain/race/race_mini.py ... --storage qs --lr 3e-3 --out out/rm/qs_s1
  python backbone/sleep/brain/race/race_mini.py ... --base bf16                          # validity check: the add-on on the bf16 base
  python backbone/sleep/brain/race/race_mini.py --smoke --out /tmp/rm                     # CPU, tiny random model, built-in fixture
"""
import argparse
import json
import os
import random
import sys
import time
from argparse import Namespace
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent), str(HERE.parent.parent.parent)]
import sleepb as sb  # noqa: E402
from sleep1 import Lang, generic_prompts, load_arc, score_arc  # noqa: E402
from train import K2_TYPE, LORA_TARGETS  # noqa: E402

K2 = "IFM/K2-Horizon-3.7B"
K2_REV = "9d280ff742235796925c9fe3cf243dc1beea5c08"


def curriculum(week, d):
    """{value key: item id} studied on night d: facts / routines seen on >= 2 days <= d; a changing fact likewise, at its new value once a new day <= d, else its old value."""
    out = {}
    for it in week["items"]:
        seen = [x for x in it["days"] if x <= d]
        if len(seen) < 2:
            continue
        if it["kind"] == "changing":
            out[f"{it['id']}:new" if any(x <= d for x in it.get("new_days", it["days"][-1:])) else f"{it['id']}:old"] = it["id"]
        else:
            out[f"{it['id']}:new"] = it["id"]
    return out


def smoke_tape(week):
    tape = {}
    for it in week["items"]:
        for which, text, b in (("new", it["text"], it["b"]),) + ((("old", it.get("old_text", it["text"].replace(it["b"], it["old_b"])), it["old_b"]),) if it.get("old_b") else ()):
            tape[f"{it['id']}:{which}"] = {"item": it["id"], "which": which, "text": text, "paraphrases": [text], "qa": [(f"Tell me about {it['a']}.", b)]}
    return tape


@torch.no_grad()
def mean_kl(pm, L, ids_list):
    tot = n = 0.0
    for e in ids_list:
        ids = torch.tensor([e], device=L.device)
        cur = F.log_softmax(pm(input_ids=ids).logits[0].float(), -1)
        with pm.disable_adapter():
            ref = F.log_softmax(pm(input_ids=ids).logits[0].float(), -1)
        tot += float(F.kl_div(cur, ref, log_target=True, reduction="sum"))
        n += cur.shape[0]
    return tot / max(n, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tape")
    ap.add_argument("--week")
    ap.add_argument("--out", required=True)
    ap.add_argument("--storage", choices=["lora", "qs"], default="lora")
    ap.add_argument("--lr", type=float, default=None, help="default: 2e-4 (lora), 3e-3 (qs)")
    ap.add_argument("--lora-plus", type=float, default=1.0, help="lora: lora_B at lr x this (the add-on side's LoRA+)")
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--qs-store", choices=["model", "fp16"], default="fp16")
    ap.add_argument("--qs-round", choices=["stochastic", "nearest", "none"], default="nearest")
    ap.add_argument("--base", choices=["q4", "q4_0", "bf16"], default="q4", help="q4: packed MLX-affine 4-bit base, group 64 (K2 race); q4_0: llama.cpp Q4_0 fake-quantized base, group 32 "
                    "(the GGUF the Mac serves; qs then trains scales only); bf16: the full-precision base (validity check, lora only)")
    ap.add_argument("--q4-gguf", default="hf:LiquidAI/LFM3-1.7B-GGUF@b3f2ae5d73cd3c91bf40e8ba752c648aa05dffdf:LFM3-1.7B-QAD-Q4_0.gguf",
                    help="--base q4_0: the served GGUF whose dequantized weights are the base (a path, or hf:REPO@REV:FILE, downloaded once); 'none' = fake-quantize the bf16 weights")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--nights", type=int, default=None, help="stop after this many nights (lr scouting); default every day of the week")
    ap.add_argument("--mid", type=int, default=4, help="also score after this night")
    ap.add_argument("--arc-n", type=int, default=500, help="ARC-Easy test questions at the end (base once, cached)")
    ap.add_argument("--replay-n", type=int, default=64)
    ap.add_argument("--tok-budget", type=int, default=512)
    ap.add_argument("--gen-bs", type=int, default=24)
    ap.add_argument("--dtype", choices=["auto", "bf16", "fp16"], default="auto")
    ap.add_argument("--model", default=K2)
    ap.add_argument("--revision", default=K2_REV)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--mem-cap-gb", type=float, default=float(os.environ.get("SLEEPB_CUDA_CAP_GIB") or 0) or None,
                    help="cuda: cap GPU memory (sleepb.mem_cap; default $SLEEPB_CUDA_CAP_GIB). Under WSL an uncapped run spills into system memory and crawls instead of failing")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--smoke-k2", action="store_true", help="with --smoke: a tiny random K2 (real tokenizer and chat template) instead of the tiny Qwen")
    a = ap.parse_args()
    if a.lr is None:
        a.lr = 2e-4 if a.storage == "lora" else 3e-3
    if a.storage == "qs" and a.base == "bf16":
        ap.error("--storage qs needs the 4-bit base")
    if a.smoke:
        a.model, a.revision = (K2, K2_REV) if a.smoke_k2 else ("Qwen/Qwen3.5-2B", None)
        a.steps, a.bsz, a.replay_n, a.gen_bs, a.arc_n = 4, 4, 4, 4, 3
    elif not (a.tape and a.week):
        ap.error("--tape and --week are required unless --smoke")
    sb.TOK_BUDGET = a.tok_budget
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    logf = open(out / "log.txt", "a")

    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")
        logf.flush()
    t0 = time.time()
    random.seed(a.seed)
    torch.manual_seed(a.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not a.smoke else "cpu")
    dtype = {"auto": torch.bfloat16, "bf16": torch.bfloat16, "fp16": torch.float16}[a.dtype] if device.type == "cuda" else torch.float32
    sb.mem_cap(a, device, log)
    if a.dtype == "fp16" and device.type == "cuda":
        sb.LOSS_SCALE[0] = 128.0
    gguf = None
    if a.base == "q4_0" and not a.smoke and a.q4_gguf != "none":
        gguf = a.q4_gguf
        if gguf.startswith("hf:"):
            from huggingface_hub import hf_hub_download
            repo, rest = gguf[3:].split("@", 1)
            rev, fn = rest.split(":", 1)
            gguf = hf_hub_download(repo, fn, revision=rev)
        log(f"[base] served GGUF {gguf}")
    la = Namespace(q4_gguf=gguf, model=a.model, revision=a.revision, smoke=a.smoke, q4_base=a.base != "bf16", q4_packed=a.base == "q4" and not a.smoke, q4_group=32 if a.base == "q4_0" else 64,
                   q4_format="q4_0" if a.base == "q4_0" else "affine", q4_bits=4,
                   q4_mlx_moe=False, q4_packed_compile="auto", arm="race_mini", seed=a.seed)
    lm, tok, q4 = sb.load_base(la, device, dtype, log)
    L = Lang(tok, a.smoke, device, k2=lm.config.model_type == K2_TYPE)
    week = sb.smoke_week() if a.smoke else json.loads(Path(a.week).read_text())
    diary = sb.Diary(week)
    tape = smoke_tape(week) if a.smoke else json.loads(Path(a.tape).read_text())["tape"]
    days = sorted({t["day"] for t in diary.turns})[:a.nights] if a.nights else sorted({t["day"] for t in diary.turns})
    from peft import LoraConfig, get_peft_model
    pm = get_peft_model(lm, LoraConfig(r=a.rank, lora_alpha=a.alpha, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
    for n, p in pm.named_parameters():
        p.requires_grad_("lora_" in n and a.storage == "lora")
    res = {"args": vars(a), "q4": q4, "days": days, "nights": [], "scores": {}}
    if a.storage == "qs":
        res["qs_setup"] = sb.setup_qs(pm, 32, 4, torch.float16, fmt="q4_0") if a.base == "q4_0" else sb.setup_qs(pm, 64, 4, dtype)
        qs_dtype = torch.float16 if a.qs_store == "fp16" else dtype
        log(f"[qs] {res['qs_setup']}")
    res["trainable"] = sum(p.numel() for p in pm.parameters() if p.requires_grad)
    gp = generic_prompts()
    tr_p, ho_p = [L.render(None, g) for g in gp[:a.replay_n]], [L.render(None, g) for g in gp[-32:]]
    with pm.disable_adapter():
        resp = L.generate(pm, tr_p, max_new=8 if a.smoke else 48, bs=a.gen_bs)
    replay = [(L.ids(p) + L.ids(r) + [L.eos], len(L.ids(p))) for p, r in zip(tr_p, resp)]
    ho_ids = [L.ids(p) for p in ho_p]
    targs = Namespace(lr=a.lr, kl_weight=1.0, replay_bsz=8, freeze_lora=a.storage == "qs", lora_plus=a.lora_plus)
    rng, gen = random.Random(a.seed * 1000 + 7), torch.Generator().manual_seed(a.seed + 5)

    def score(tag):
        sc = sb.score_week(L, pm, week, diary, "weights", a.gen_bs, None, True)
        res["scores"][tag] = sc
        log(f"[score {tag}] C2+C4 fwd {sc['forward']['C24']} rev {sc['reverse']['C24']} C1 {sc['forward']['C1']} changed new {sc['changed']['new']} stale {sc['changed']['stale']} routine {sc['routine']['acc']}")
        (out / "result.json").write_text(json.dumps(res, indent=1))

    for d in days:
        tn = time.time()
        cur = curriculum(week, d)
        keys = sorted(cur)
        pool = {k: [sb.ex_text(L, x) for x in [tape[k]["text"], *tape[k]["paraphrases"]]] for k in keys}
        qa = {k: [sb.ex_qa(L, q, x) for q, x in tape[k]["qa"]] or pool[k] for k in keys}
        tr = sb.Trainer(L, pm, targs, replay, a.steps if keys else 0, a.seed * 100 + d)
        if keys:
            for _ in range(a.steps):
                ks = [rng.choice(keys) for _ in range(a.bsz)]
                tr.step([rng.choice(pool[k] if j % 2 == 0 else qa[k]) for j, k in enumerate(ks)])
            morning = sb.qs_morning(pm, 0.85, qs_dtype, a.qs_round, gen) if a.storage == "qs" else sb.shy_apply(pm, 0.85, 0.05, gen)
        else:
            morning = None
        rec = {"night": d, "values": len(keys), "steps": tr.i, "loss_curve": tr.curve[-4:], "morning": morning, "seconds": round(time.time() - tn, 1),
               "fp16_loss_scale": sb.LOSS_SCALE[0]}
        res["nights"].append(rec)
        log(f"[night {d}] values {len(keys)} steps {tr.i} {rec['seconds']}s last {tr.curve[-1] if tr.curve else None}")
        (out / "result.json").write_text(json.dumps(res, indent=1))
        if d == a.mid and d != days[-1]:
            score(f"night{d}")
    score("final")
    res["kl_heldout"] = mean_kl(pm, L, ho_ids)
    try:
        arc = load_arc(a.smoke)[:a.arc_n]
        bpath = out.parent / f"arc_base_{a.base}_{a.arc_n}.json"
        if bpath.exists() and not a.smoke:
            res["arc_base"] = json.loads(bpath.read_text())
        else:
            with pm.disable_adapter():
                res["arc_base"] = score_arc(L, pm, arc, bs=max(a.gen_bs // 2, 1))["acc"]
            bpath.write_text(json.dumps(res["arc_base"]))
        res["arc"] = score_arc(L, pm, arc, bs=max(a.gen_bs // 2, 1))["acc"]
    except Exception as e:
        res["arc"] = {"error": repr(e)}
    res["wall_s"] = round(time.time() - t0, 1)
    (out / "result.json").write_text(json.dumps(res, indent=1))
    (out / "DONE").write_text("ok\n")
    log(f"[done] arc {res.get('arc')} base {res.get('arc_base')} kl {res['kl_heldout']:.4g} wall {res['wall_s']}s")


if __name__ == "__main__":
    main()
