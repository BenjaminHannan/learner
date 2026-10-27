"""Kaggle T4 probe for Think-1 (not part of the experiment): can Qwen3.5-0.8B + LoRA train in fp16 on a T4, how fast, and
does flash-linear-attention work there? Usage: python probe_t4.py MODE OUT   (MODE = fp16 or fp32; DATA env = data dir)."""
import json, math, os, random, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), "backbone"))
import torch, torch.nn.functional as F
import train as T

mode, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
res = {"mode": mode, "torch": torch.__version__, "gpu": torch.cuda.get_device_name(0), "bf16_supported": torch.cuda.is_bf16_supported()}
try:
    import fla, transformers, peft
    res["fla"] = fla.__version__; res["transformers"] = transformers.__version__; res["peft"] = peft.__version__
except Exception as e:
    res["import_error"] = repr(e)
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
dev = torch.device("cuda")
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-0.8B")
dtype = torch.float16 if mode == "fp16" else torch.float32
lm = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3.5-0.8B", dtype=dtype).to(dev).eval()
for p in lm.parameters(): p.requires_grad_(False)
D = os.environ.get("DATA", "")
train_rows = T.read_jsonl(os.path.join(D, "train.jsonl")); val_rows = T.read_jsonl(os.path.join(D, "validation.jsonl"))
enc = T.Encoder(tok, 2048)
from transformers.models.qwen3_5 import modeling_qwen3_5 as M
res["chunk_rule"] = getattr(M.torch_chunk_gated_delta_rule, "__module__", "?") + "." + getattr(M.torch_chunk_gated_delta_rule, "__name__", "?")

# 1. forward health: answer CE and logit range on 32 validation rows, this dtype vs an fp32 reference (fp16 mode only)
def answer_ce(model, rows):
    runner = T.Runner(model, loops=1); s, n, mx, bad = 0.0, 0, 0.0, 0
    with torch.no_grad():
        for i in range(0, len(rows), 4):
            batch = [enc.train_example(r) for r in rows[i:i + 4]]
            with torch.autocast("cuda", dtype=torch.float16, enabled=(mode == "fp16")):
                ids, mask = T.right_pad([p + a for p, a in batch]); ids, mask = ids.to(dev), mask.to(dev)
                h = runner.hidden(ids, mask, (mask.cumsum(1) - 1).clamp(min=0))
                sb = [b for b, (p, a) in enumerate(batch) for k in range(len(a))]
                st = [len(p) + k - 1 for p, a in batch for k in range(len(a))]
                lg = runner.logits(h[torch.tensor(sb, device=dev), torch.tensor(st, device=dev)]).float()
            bad += int((~torch.isfinite(lg)).sum()); mx = max(mx, float(lg.abs().max()))
            tg = torch.tensor([t for _, a in batch for t in a], device=dev)
            s += float(F.cross_entropy(lg, tg, reduction="sum")); n += len(tg)
    return s / n, mx, bad
t0 = time.time(); ce, mx, bad = answer_ce(lm, val_rows[:32])
res["fwd"] = {"answer_ce": ce, "max_abs_logit": mx, "nonfinite_logits": bad, "seconds": time.time() - t0}
if mode == "fp16":
    ref = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3.5-0.8B", dtype=torch.float32).to(dev).eval()
    mode_save = mode; mode = "fp32"; ce32, _, _ = answer_ce(ref, val_rows[:32]); mode = mode_save
    res["fwd"]["answer_ce_fp32_ref"] = ce32; del ref; torch.cuda.empty_cache()

# 2. LoRA training speed and stability: 30 steps, batch 16, micro 4, max-len 2048 (stage-1 arm A recipe)
pm = get_peft_model(lm, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules=T.LORA_TARGETS, bias="none"))
for n_, p in pm.named_parameters():
    if p.requires_grad: p.data = p.data.float()
params = [p for p in pm.parameters() if p.requires_grad]
opt = torch.optim.AdamW(params, lr=2e-4, weight_decay=0.0)
scaler = torch.amp.GradScaler("cuda", enabled=(mode == "fp16"))
runner = T.Runner(pm.base_model.model, loops=1); runner.checkpoint = True; pm.train()
rng = random.Random(0); order = list(range(len(train_rows))); rng.shuffle(order)
times, losses, skipped = [], [], 0
for step in range(30):
    batch = [enc.train_example(train_rows[order.pop()]) for _ in range(16)]
    n_ans = sum(len(a) for _, a in batch); torch.cuda.synchronize(); t = time.time(); tot = 0.0
    for k in range(0, 16, 4):
        with torch.autocast("cuda", dtype=torch.float16, enabled=(mode == "fp16")):
            s, _ = T.answer_loss_sum(runner, batch[k:k + 4], dev)
        scaler.scale(s / n_ans).backward(); tot += float(s)
    scaler.unscale_(opt); gn = torch.nn.utils.clip_grad_norm_(params, 1.0)
    if not torch.isfinite(gn): skipped += 1
    scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True)
    torch.cuda.synchronize(); times.append(time.time() - t); losses.append(tot / n_ans)
    print(f"step {step} loss {losses[-1]:.4f} {times[-1]:.2f}s gn {float(gn):.3f}", flush=True)
res["train"] = {"s_per_step_median": sorted(times[3:])[len(times[3:]) // 2], "loss_first": losses[0], "loss_last5": sum(losses[-5:]) / 5,
                "skipped_nonfinite": skipped, "peak_gb": torch.cuda.max_memory_allocated() / 2**30, "losses": losses}
res["train"]["proj_418_steps_h"] = res["train"]["s_per_step_median"] * 418 / 3600

# 3. greedy decode throughput on 128 validation rows
pm.eval(); runner.checkpoint = False; prompts = [enc.prompt(r)[0] for r in val_rows[:128]]
torch.cuda.synchronize(); t = time.time(); hits = 0
for i in range(0, 128, 32):
    with torch.autocast("cuda", dtype=torch.float16, enabled=(mode == "fp16")):
        gen = T.greedy(runner, prompts[i:i + 32], dev, enc.eos)
    for g, r in zip(gen, val_rows[i:i + 32]):
        hits += T.normalise(tok.decode(g, skip_special_tokens=True)) == T.normalise(r["answer"])
torch.cuda.synchronize(); dt = time.time() - t
res["eval"] = {"rows": 128, "seconds": dt, "proj_validation_8675_h": dt / 128 * 8675 / 3600, "acc_after_30_steps": hits / 128}
json.dump(res, open(os.path.join(out, f"probe_{mode}.json"), "w"), indent=1)
print("PROBE", json.dumps({k: v for k, v in res.items() if k != "train"}), json.dumps({k: v for k, v in res["train"].items() if k != "losses"}), flush=True)
