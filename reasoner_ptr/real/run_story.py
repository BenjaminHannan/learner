"""Real-pipeline pointer test (two-doors round 2). One run = one arm, one seed. Marks: PASS-MARKS-R2.md.

Real modules from PR #33 (commit 34608a1): HumanInputProjection reader fed the frozen LM's contextual last-layer
states (the --ctx recipe), the real ordered fresh 9.0M core (begin_latent + 4 advance_latent, 8 notebook slots set
to role/PENDING as in the calculator recipe, no tool calls here), the real StatePrefix exit (8 pooled vectors),
prefix before BOS as in run_arm.py. Story questions answered by one word from the story (gen_story2.py).

Arms (one change each vs pool):
  pool  today's real exit: 8 pooled prefix vectors.
  ptr   pool + 8 pointer vectors: Linear(256->8) on the core's final state, softmax over question positions,
        value = the frozen LM's input embedding of the token there. The LM never sees the story itself.
  emb   pool + the frozen LM's input embeddings of every question token (my reading of the PC session's
        "prompt token embeddings in the prefix" fix). The LM sees the whole story, so the core can be bypassed.
Lesions at test (reported): ptr with uniform pointer weights; ptr and emb with the 8 pooled vectors zeroed.
"""
import argparse, json, math, os, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (ROOT, ROOT / "scripts", ROOT / "scripts" / "cap256_launch", HERE):
    sys.path.insert(0, str(p))

import torch
from torch import nn
from torch.nn import functional as F
from calculator_runtime import CalculatorPath, STATUS_IDS
from sol_translator_grounding import HumanInputProjection
from sol_translator_english_v6 import StatePrefix
from sol_spatial_poc_ordered_v2 import OrderedAttentionReasoner
import claude_fewex_net as base
from sol_stop_ordered_api2 import ordered_attention_math
import gen_story2 as GS
import gen_story as G

p = argparse.ArgumentParser()
p.add_argument("--arm", choices=["pool", "ptr", "emb"], required=True)
p.add_argument("--seed", type=int, required=True)
p.add_argument("--steps", type=int, default=3000)
p.add_argument("--batch", type=int, default=16)
p.add_argument("--lr", type=float, default=1e-3)
p.add_argument("--lm", default="LiquidAI/LFM2.5-1.2B-Instruct")
p.add_argument("--revision", default="0f604ada3f766f9f257460c4c9f0b5d6f69d431b")
p.add_argument("--out", default=str(HERE / "results"))
p.add_argument("--device", default="cuda")
p.add_argument("--eval-n", type=int, default=0)
args = p.parse_args()
dev = args.device

from transformers import AutoTokenizer, AutoModelForCausalLM
kw = {} if os.path.isdir(args.lm) else {"revision": args.revision}
tok = AutoTokenizer.from_pretrained(args.lm, **kw)
lm = AutoModelForCausalLM.from_pretrained(args.lm, dtype=torch.float32, **kw).to(dev).eval().requires_grad_(False)
if dev == "cuda":
    torch.backends.cuda.matmul.allow_tf32 = True; torch.backends.cudnn.allow_tf32 = True
LMW = lm.config.hidden_size
BOS, EOS = tok.bos_token_id, tok.eos_token_id
emb = lm.get_input_embeddings()
K = 8


def word_id(w):
    ids = tok.encode(" " + w, add_special_tokens=False); assert len(ids) == 1, w; return ids[0]


def build_core(seed):
    with torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(seed)
        core = OrderedAttentionReasoner(base.Net("loop"), experts=8, active=2)
    core.halt.requires_grad_(False)
    assert sum(q.numel() for q in core.parameters()) == 9007790
    return core


class Model(nn.Module):
    def __init__(self, seed):
        super().__init__()
        torch.manual_seed(seed)
        self.core = build_core(seed)
        self.reader = HumanInputProjection(LMW)
        self.adapter = StatePrefix(256, LMW, 32, 8)
        self.tool = CalculatorPath(256)  # only its role/status vectors fill the 8 notebook slots, as in the recipe
        if args.arm == "ptr":
            self.ptr = nn.Linear(256, K)


_cache = {}


def ids_of(r):
    if r["text"] not in _cache:
        _cache[r["text"]] = tok.encode(r["text"], add_special_tokens=False) + [EOS]
    return _cache[r["text"]]


def forward(model, rows, lesion=None):
    ids = torch.tensor([ids_of(r) for r in rows], device=dev)
    B, n = ids.shape
    with torch.no_grad():
        bosc = torch.full((B, 1), BOS, device=dev, dtype=ids.dtype)
        e0 = lm(input_ids=torch.cat([bosc, ids], 1), output_hidden_states=True).hidden_states[-1][:, 1:].float()
        tok_e = emb(ids).float()
    mask = torch.ones(B, n, dtype=torch.bool, device=dev)
    query = model.reader(e0, mask)
    role = model.tool.role; pending = model.tool.status.weight[STATUS_IDS["PENDING"]]
    memo = query.new_zeros((B, 8, 256))
    for pair in range(4):
        memo[:, 2 * pair] = role; memo[:, 2 * pair + 1] = pending + role
    with ordered_attention_math():
        state = model.core.begin_latent(query, memo, query_mask=mask, notebook_mask=torch.ones((B, 8), dtype=torch.bool, device=dev))
        for _ in range(4):
            state = model.core.advance_latent(state)
    h = state["h"][:, :n]
    prefix = model.adapter.project_training(h, torch.ones_like(h, dtype=torch.bool), mask, (1, n))
    if lesion == "zero_pool":
        prefix = prefix * 0
    parts, pw = [prefix], None
    if args.arm == "ptr":
        s = model.ptr(h).float()  # [B,n,K]
        pw = s.softmax(1)
        if lesion == "uniform":
            pw = torch.full_like(pw, 1.0 / n)
        parts.append(torch.einsum("bnk,bnl->bkl", pw, tok_e))
    elif args.arm == "emb":
        parts.append(tok_e)
    prefix_all = torch.cat(parts, 1).to(emb.weight.dtype)
    P = prefix_all.shape[1]
    ans = torch.tensor([word_id(r["answer"]) for r in rows], device=dev)
    inp = torch.cat([prefix_all, emb(torch.full((B, 1), BOS, device=dev)), emb(ans[:, None])], 1)
    logits = lm(inputs_embeds=inp).logits.float()[:, P:]  # predicts ans, then EOS
    return logits, ans, pw, ids


def bucket_batches(rows, bs, rng, drop_last=True):
    by = {}
    for r in rows:
        by.setdefault(len(ids_of(r)), []).append(r)
    out = []
    for k, rs in by.items():
        rng.shuffle(rs)
        for i in range(0, len(rs), bs):
            c = rs[i:i + bs]
            if len(c) == bs or not drop_last: out.append(c)
    rng.shuffle(out); return out


@torch.no_grad()
def evaluate(model, rows, lesion=None):
    model.eval(); out = []
    for chunk in bucket_batches(rows, 32, random.Random(0), drop_last=False):
        logits, ans, pw, ids = forward(model, chunk, lesion)
        pred, pred2 = logits[:, 0].argmax(-1), logits[:, 1].argmax(-1)
        for b, r in enumerate(chunk):
            row = {"id": r.get("id"), "cell": r.get("cell"), "qkind": r["qkind"], "answer": r["answer"],
                   "pred": tok.decode([int(pred[b])]).strip(), "ok": bool(pred[b] == ans[b]),
                   "ok_eos": bool(pred[b] == ans[b] and pred2[b] == EOS)}
            if pw is not None:
                row["ptr_hit"] = bool((ids[b][pw[b].argmax(0)] == ans[b]).any())
            out.append(row)
    model.train(); return out


def summarize(res, train_words):
    def rate(sel):
        sel = list(sel); return [round(sum(r["ok"] for r in sel) / max(1, len(sel)), 4), len(sel)]
    s = {c: rate(r for r in res if r["cell"] == c) for c in sorted({r["cell"] for r in res if r["cell"]})}
    for name, f in (("unseen", lambda c: c.startswith("unseen")), ("seen", lambda c: c.startswith("seen")),
                    ("two_hop", lambda c: c.endswith("two")), ("one_hop", lambda c: c.endswith("one")),
                    ("new_wording", lambda c: "-new-" in c), ("train_wording", lambda c: "-train-" in c), ("all", lambda c: True)):
        s[name] = rate(r for r in res if r["cell"] and f(r["cell"]))
    wu = [r for r in res if r["cell"] and r["cell"].startswith("unseen") and not r["ok"]]
    s["wrong_unseen_is_train_word"] = [sum(r["pred"] in train_words for r in wu), len(wu)]
    if res and "ptr_hit" in res[0]:
        s["ptr_hit"] = round(sum(r["ptr_hit"] for r in res) / len(res), 4)
    return s


def main():
    random.seed(args.seed)
    sp = G.split(); train_words = set(sum((v["train"] for v in sp.values()), []))
    held = set(sum((v["heldout"] for v in sp.values()), []))
    form = GS.eval_form()
    if args.eval_n: form = form[::max(1, len(form) // args.eval_n)][:args.eval_n]
    n_total = int(args.steps * args.batch * 1.4) + 64
    data = GS.stream(2000 + args.seed, n_total, {r["text"] for r in GS.eval_form()})
    assert not any(w.strip(".,?") in held for r in data for w in r["text"].split())
    batches = bucket_batches(data, args.batch, random.Random(100 + args.seed))
    assert len(batches) >= args.steps, (len(batches), args.steps)
    batches = batches[:args.steps]
    fit_rows = [r for b in batches[-12:] for r in b][:192]
    model = Model(args.seed).to(dev)
    params = [q for q in model.parameters() if q.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(i, args.steps) / args.steps)))
    name = f"{args.arm}-seed{args.seed}"
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for step, rows in enumerate(batches):
        logits, ans, _, _ = forward(model, rows)
        loss = F.cross_entropy(logits.transpose(1, 2), torch.stack([ans, torch.full_like(ans, EOS)], 1))  # mean over [ans, EOS], as run_arm.py
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0); opt.step(); sched.step()
        if step % 100 == 0 or step == args.steps - 1:
            print(f"{name} step {step} loss {loss.item():.4f} t {time.time()-t0:.0f}s", flush=True)
    fit = evaluate(model, fit_rows)
    res = {"arm": args.arm, "seed": args.seed, "steps": args.steps, "batch": args.batch,
           "params": sum(q.numel() for q in params), "seconds": round(time.time() - t0),
           "train_fit_192": round(sum(r["ok"] for r in fit) / len(fit), 4)}
    ev = evaluate(model, form); res["eval"] = summarize(ev, train_words)
    (outdir / f"{name}-rows.json").write_text(json.dumps(ev))
    lesions = (["uniform", "zero_pool"] if args.arm == "ptr" else ["zero_pool"] if args.arm == "emb" else [])
    for les in lesions:
        evl = evaluate(model, form, les); res["lesion_" + les] = summarize(evl, train_words)
        (outdir / f"{name}-lesion-{les}-rows.json").write_text(json.dumps(evl))
    (outdir / f"{name}.json").write_text(json.dumps(res, indent=1))
    print("RESULT-JSON " + name + " " + json.dumps({k: res[k] for k in ("arm", "seed", "train_fit_192")}) + " unseen " + str(res["eval"]["unseen"]) + " seen " + str(res["eval"]["seen"]), flush=True)


main()
