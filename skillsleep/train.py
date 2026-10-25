"""Night step 4: LoRA sleep for one arm, then merge into a full bf16 model dir for vLLM.
Usage: train.py ARM(A1|A2) BASE_DIR NIGHT_JSONL ANCHOR_JSONL OUT_DIR
Memory rule: the vocab is 250,624 and untied, so full-sequence logits are never built; lm_head runs only on loss positions, in checkpointed chunks.
  A1: SFT NLL on positives (assistant tokens) + ANCHOR_W * KL(base || lora) on the anchor set.
  A2: A1 + DPO on (pass, fail) pairs + KTO-style undesirable term on lone negatives. Each step sees one positive; DPO/KTO items cycle alongside.
DPO: reference = adapter disabled (precomputed once). Both sides of a pair are run with grad and backpropagated together."""
import json, math, os, random, shutil, sys, time
import torch, torch.nn.functional as F
from torch.utils.checkpoint import checkpoint
from transformers import AutoModelForCausalLM
from peft import LoraConfig, get_peft_model

arm, base, nightp, anchorp, outd = sys.argv[1:6]
E = os.environ.get
LR = float(E("LR", 5e-5)); EPOCHS = int(E("EPOCHS", 2)); ACCUM = int(E("ACCUM", 8)); BETA = float(E("BETA", 0.1)); ANCHOR_W = float(E("ANCHOR_W", 0.1))
DPO_W = float(E("DPO_W", 1.0)); KTO_W = float(E("KTO_W", 1.0)); CHUNK = int(E("CHUNK", 1024)); CLIP = float(E("CLIP", 1.0)); SEED = int(E("SEED", 1))
dev = "cuda" if torch.cuda.is_available() else "cpu"; dt = torch.bfloat16 if dev == "cuda" else torch.float32
random.seed(SEED); torch.manual_seed(SEED)
log = open(outd + ".log", "a")


def P(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); log.write(s + "\n"); log.flush()


rows = [json.loads(l) for l in open(nightp)]
pos = [r for r in rows if r["kind"] == "pos"]; pairs = [r for r in rows if r["kind"] == "pair"]; negs = [r for r in rows if r["kind"] == "neg"]
anchors = [json.loads(l) for l in open(anchorp)]
P(f"arm={arm} pos={len(pos)} pairs={len(pairs)} negs={len(negs)} anchors={len(anchors)} lr={LR} epochs={EPOCHS} accum={ACCUM}")
assert pos, "no positives to learn from"

model = AutoModelForCausalLM.from_pretrained(base, dtype=dt, trust_remote_code=True, attn_implementation="sdpa").to(dev)
model.config.use_cache = False; model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False}); model.train()
pm = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, bias="none",
                                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
pm.print_trainable_parameters()
inner = pm.base_model.model  # K2HorizonForCausalLM; LoRA layers are injected in place, so calling its parts uses the adapter
params = [p for p in pm.parameters() if p.requires_grad]
opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)
n_micro = len(pos) * EPOCHS; n_opt = math.ceil(n_micro / ACCUM)
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 0.5 * (1 + math.cos(math.pi * min(s, n_opt) / n_opt)))  # cosine to 0, no warmup


def T(x, dtype=torch.long):
    return torch.tensor(x, dtype=dtype, device=dev)


def hidden(ids):  # final-norm hidden states [T, H]; no logits
    return inner.model(input_ids=T([ids]), use_cache=False).last_hidden_state[0]


def positions(mask):  # token j is predicted from hidden j-1
    return [j for j, m in enumerate(mask) if m and j > 0]


def _lp(hc, tc):
    return -F.cross_entropy(inner.lm_head(hc).float(), tc, reduction="none")


def _kl(ht, hs):
    lt = F.log_softmax(inner.lm_head(ht).float(), -1); ls = F.log_softmax(inner.lm_head(hs).float(), -1)
    return (lt.exp() * (lt - ls)).sum(-1)


def chunked(fn, *tensors):
    return torch.cat([checkpoint(fn, *[t[i:i + CHUNK] for t in tensors], use_reentrant=False) for i in range(0, len(tensors[0]), CHUNK)])


def tok_logps(ex):  # log-prob of every trained token, [n]
    idx = positions(ex["mask"]); h = hidden(ex["ids"])
    return chunked(_lp, h[T([i - 1 for i in idx])], T([ex["ids"][i] for i in idx]))


def seq_logp(ex, grad):
    if grad:
        return tok_logps(ex).sum()
    with torch.no_grad():
        return tok_logps(ex).sum().item()


def ref_logp(ex):
    with pm.disable_adapter():
        return seq_logp(ex, False)


def anchor_kl(ex):
    idx = T([i - 1 for i in positions(ex["mask"])])
    with torch.no_grad(), pm.disable_adapter():
        ht = hidden(ex["ids"])[idx]
    return chunked(_kl, ht, hidden(ex["ids"])[idx]).mean()


def nll_probe(exs):  # mean NLL of a few positives under the current weights (base / adapter / merged check)
    with torch.no_grad():
        return sum(-tok_logps(e).mean().item() for e in exs) / len(exs)


probe = pos[:3]
with pm.disable_adapter():
    nll_base = nll_probe(probe)
P("probe NLL base:", round(nll_base, 4))

ref = {}
if arm == "A2":
    t0 = time.time()
    for r in pairs:
        ref[id(r["chosen"])] = ref_logp(r["chosen"]); ref[id(r["rejected"])] = ref_logp(r["rejected"])
    for r in negs:
        ref[id(r)] = ref_logp(r)
    P(f"reference log-probs done in {time.time() - t0:.0f}s")
cyc = pairs + negs; random.Random(SEED).shuffle(cyc)

order = []
for ep in range(EPOCHS):
    o = list(range(len(pos))); random.Random(SEED + ep).shuffle(o); order += o
t0 = time.time(); acc = {}
for m, pi in enumerate(order):
    sc = 1.0 / ACCUM
    l = -tok_logps(pos[pi]).mean(); (l * sc).backward(); acc["sft"] = acc.get("sft", 0) + l.item()
    a = anchors[m % len(anchors)]; k = anchor_kl(a); (ANCHOR_W * k * sc).backward(); acc["kl"] = acc.get("kl", 0) + k.item()
    if arm == "A2" and cyc:
        it = cyc[m % len(cyc)]
        if it["kind"] == "pair":
            c, r = it["chosen"], it["rejected"]
            lc, lr_ = seq_logp(c, True), seq_logp(r, True)  # both graphs are kept: checkpointed activations only (~4 GB each at 16k tokens)
            z = BETA * ((lc - ref[id(c)]) - (lr_ - ref[id(r)])); ld = -F.logsigmoid(z); (DPO_W * ld * sc).backward()
            acc["dpo"] = acc.get("dpo", 0) + ld.item(); acc["dpo_acc"] = acc.get("dpo_acc", 0) + float(z.item() > 0)
        else:
            x = BETA * (seq_logp(it, True) - ref[id(it)]); kt = torch.sigmoid(x); (KTO_W * kt * sc).backward()
            acc["kto"] = acc.get("kto", 0) + kt.item()
    if (m + 1) % ACCUM == 0 or m + 1 == len(order):
        gn = torch.nn.utils.clip_grad_norm_(params, CLIP).item(); opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
        step = math.ceil((m + 1) / ACCUM)
        P(f"step {step}/{n_opt} lr={sched.get_last_lr()[0]:.2e} gnorm={gn:.2f} " + " ".join(f"{k}={v / ACCUM:.4f}" for k, v in acc.items()) +
          f" mem={torch.cuda.max_memory_allocated() / 2**30 if dev == 'cuda' else 0:.1f}G t={time.time() - t0:.0f}s"); acc = {}

nll_ad = nll_probe(probe); P("probe NLL base / adapter:", round(nll_base, 4), round(nll_ad, 4))
merged = pm.merge_and_unload(); merged.eval(); inner = merged
nll_mg = nll_probe(probe); P("probe NLL merged (bf16 rounding check, should be ~adapter):", round(nll_mg, 4))
os.makedirs(outd, exist_ok=True); merged.save_pretrained(outd, safe_serialization=True, max_shard_size="5GB")
for f in os.listdir(base):  # config, tokenizer and the remote-code .py files come from the original snapshot
    if f.endswith((".py", ".json", ".jinja", ".model")) and "safetensors" not in f and "index" not in f:
        shutil.copy(os.path.join(base, f), os.path.join(outd, f))
want = set(json.load(open(os.path.join(base, "model.safetensors.index.json")))["weight_map"])
from safetensors import safe_open
have = set()
for f in os.listdir(outd):
    if f.endswith(".safetensors"):
        with safe_open(os.path.join(outd, f), "pt") as g:
            have |= set(g.keys())
P("merged weight names match base:", want == have, "missing", sorted(want - have)[:3], "extra", sorted(have - want)[:3])
json.dump({"arm": arm, "pos": len(pos), "pairs": len(pairs), "negs": len(negs), "opt_steps": n_opt, "probe_nll": [nll_base, nll_ad, nll_mg]}, open(outd + "/train_info.json", "w"))
P("TRAIN DONE", arm)
