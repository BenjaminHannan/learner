"""One run of the two-doors test: arm A/B/C/W/BW, one seed. Marks: PASS-MARKS.md (fixed before any run)."""
import argparse, json, math, random, time
from pathlib import Path
import torch
from torch.nn import functional as F
import gen_story as G
from model_ptr import StoryReasoner

HERE = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument("--arm", choices=["A", "B", "C", "W", "BW"], required=True)
p.add_argument("--seed", type=int, required=True)
p.add_argument("--steps", type=int, default=3000)
p.add_argument("--batch", type=int, default=16)
p.add_argument("--lr", type=float, default=1e-3)
p.add_argument("--lm", default="LiquidAI/LFM2.5-1.2B-Instruct")
p.add_argument("--out", default=str(HERE / "results"))
p.add_argument("--device", default="cuda")
p.add_argument("--eval-n", type=int, default=0, help="dry run: score only the first N eval rows")
args = p.parse_args()

from transformers import AutoTokenizer, AutoModelForCausalLM
dev = args.device
tok = AutoTokenizer.from_pretrained(args.lm)
lm = AutoModelForCausalLM.from_pretrained(args.lm, dtype=torch.bfloat16 if dev == "cuda" else torch.float32).to(dev).eval()
for q_ in lm.parameters():
    q_.requires_grad_(False)
LMW = lm.config.hidden_size
BOS, EOS = tok.bos_token_id, tok.eos_token_id
emb = lm.get_input_embeddings()


def word_id(w):
    ids = tok(" " + w, add_special_tokens=False).input_ids
    assert len(ids) == 1, w
    return ids[0]


def encode(rows):
    seqs = [[BOS] + tok(r["text"], add_special_tokens=False).input_ids + [EOS] for r in rows]
    T = max(len(s) for s in seqs)
    ids = torch.zeros(len(rows), T, dtype=torch.long); mask = torch.zeros(len(rows), T, dtype=torch.bool)
    for i, (s, r) in enumerate(zip(seqs, rows)):
        ids[i, :len(s)] = torch.tensor(s); mask[i, :len(s)] = True
        assert word_id(r["answer"]) in s, (r["text"], r["answer"])  # the answer token is in the story
    return ids.to(dev), mask.to(dev)


@torch.no_grad()
def lm_states(ids, mask):
    out = lm(input_ids=ids, attention_mask=mask.long(), output_hidden_states=True)
    return out.hidden_states[-1][:, 1:], mask[:, 1:], emb(ids[:, 1:])


def run_batch(model, rows, lesion=False):
    ids, mask = encode(rows)
    feats, qm, te = lm_states(ids, mask)
    ans = torch.tensor([word_id(r["answer"]) for r in rows], device=dev)
    with torch.autocast(dev, dtype=torch.bfloat16, enabled=dev == "cuda"):
        prefix, pw = model(feats, qm, te, lesion)
        B = len(rows)
        inp = torch.cat([emb(torch.full((B, 1), BOS, device=dev)), prefix.to(emb.weight.dtype), emb(ans[:, None])], 1)
        logits = lm(inputs_embeds=inp).logits.float()
    return logits, ans, pw, ids[:, 1:]


def evaluate(model, rows, lesion=False, bs=32):
    model.eval(); out = []
    P = model.n_prefix()
    with torch.no_grad():
        for i in range(0, len(rows), bs):
            chunk = rows[i:i + bs]
            logits, ans, pw, ids = run_batch(model, chunk, lesion)
            pred = logits[:, P].argmax(-1)
            for j, r in enumerate(chunk):
                row = {"id": r.get("id"), "cell": r.get("cell"), "qkind": r["qkind"], "answer": r["answer"],
                       "pred": tok.decode([int(pred[j])]).strip(), "ok": int(pred[j]) == int(ans[j])}
                if pw is not None:  # does any pointer slot put its top weight on an answer-token position?
                    top = pw[j].argmax(-1)
                    row["ptr_hit"] = bool((ids[j][top] == ans[j]).any())
                out.append(row)
    model.train(); return out


def summarize(res, train_words):
    def rate(sel):
        sel = list(sel); return [round(sum(r["ok"] for r in sel) / max(1, len(sel)), 4), len(sel)]
    s = {c: rate(r for r in res if r["cell"] == c) for c in sorted({r["cell"] for r in res})}
    s["unseen"] = rate(r for r in res if r["cell"].startswith("unseen"))
    s["seen"] = rate(r for r in res if r["cell"].startswith("seen"))
    s["two_hop"] = rate(r for r in res if r["cell"].endswith("two"))
    s["seen_two_hop"] = rate(r for r in res if r["cell"].startswith("seen") and r["cell"].endswith("two"))
    s["one_hop"] = rate(r for r in res if r["cell"].endswith("one"))
    s["all"] = rate(res)
    wrong_unseen = [r for r in res if r["cell"].startswith("unseen") and not r["ok"]]
    s["wrong_unseen_is_train_word"] = [sum(r["pred"] in train_words for r in wrong_unseen), len(wrong_unseen)]
    if res and "ptr_hit" in res[0]:
        s["ptr_hit"] = round(sum(r["ptr_hit"] for r in res) / len(res), 4)
    return s


def main():
    torch.manual_seed(args.seed); random.seed(args.seed)
    sp = G.split()
    words = {k: v["train"] for k, v in sp.items()}
    train_words = set(sum(words.values(), []))
    form = json.loads((HERE / "EVAL-FORM.json").read_text())
    if args.eval_n:
        form = form[::max(1, len(form) // args.eval_n)][:args.eval_n]
    n_total = args.steps * args.batch
    data = G.stream(1000 + args.seed, n_total, words, {r["text"] for r in form})
    held = set(sum((v["heldout"] for v in sp.values()), []))
    assert not any(w in held for r in data for w in r["text"].replace(".", " ").replace("?", " ").replace(",", " ").split())
    model = StoryReasoner(LMW, args.arm).to(dev)
    nparam = sum(p_.numel() for p_ in model.parameters())
    P = model.n_prefix()
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(i, args.steps) / args.steps)))
    name = f"arm{args.arm}-seed{args.seed}"
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    logf = open(outdir / f"{name}.log", "w")
    t0 = time.time()
    fit_rows = data[-192:]
    for step in range(args.steps):
        rows = data[step * args.batch:(step + 1) * args.batch]
        logits, ans, _, _ = run_batch(model, rows)
        ce = F.cross_entropy(logits[:, P], ans) + 0.5 * F.cross_entropy(logits[:, P + 1], torch.full_like(ans, EOS))
        loss = ce + model.aux()
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step()
        if step % 100 == 0 or step == args.steps - 1:
            msg = f"{name} step {step} loss {loss.item():.4f} ce {ce.item():.4f} t {time.time()-t0:.0f}s"
            if step % 500 == 0 or step == args.steps - 1:
                fr = evaluate(model, fit_rows[:64]); msg += f" | trainfit64 {sum(r['ok'] for r in fr)/64:.3f}"
            print(msg, flush=True); logf.write(msg + "\n"); logf.flush()
    fit = evaluate(model, fit_rows)
    ev = evaluate(model, form)
    res = {"arm": args.arm, "seed": args.seed, "steps": args.steps, "batch": args.batch, "params": nparam,
           "seconds": round(time.time() - t0), "eval": summarize(ev, train_words),
           "train_fit_192": sum(r["ok"] for r in fit) / 192}
    if model.pointer:
        evl = evaluate(model, form, lesion=True)
        res["lesion_uniform_pointer"] = summarize(evl, train_words)
        (outdir / f"{name}-lesion-rows.json").write_text(json.dumps(evl))
    (outdir / f"{name}.json").write_text(json.dumps(res, indent=1))
    (outdir / f"{name}-rows.json").write_text(json.dumps(ev))
    print("RESULT-JSON " + name + " " + json.dumps(res), flush=True)


main()
