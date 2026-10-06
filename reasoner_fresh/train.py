"""One run: arm A (fixed 256-question pool, repeated) or arm B (never-repeating stream)."""
import argparse, json, math, random, time, sys
from pathlib import Path
import torch
from torch.nn import functional as F
import gen
from model import Reasoner, LOOPS, LO, HI

HERE = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument("--arm", choices=["A", "B"], required=True)
p.add_argument("--seed", type=int, required=True)
p.add_argument("--steps", type=int, default=3000)
p.add_argument("--batch", type=int, default=16)
p.add_argument("--lr", type=float, default=1e-3)
p.add_argument("--lm", default="LiquidAI/LFM2.5-1.2B-Instruct")
p.add_argument("--out", default=str(HERE / "results"))
p.add_argument("--copy", action="store_true", help="arm C: add the calculator result token embedding as a 9th prefix vector (direct copy path)")
p.add_argument("--call-loop", type=int, default=0, help="first loop at which the calculator may be called (0 = original)")
p.add_argument("--wording", choices=["old", "mix"], default="old", help="mix: half old 4 templates, half procedurally composed frames (gen2), disjoint from eval new wording")
p.add_argument("--eval-form", default="EVAL-FORM-v1.json")
p.add_argument("--device", default="cuda")
p.add_argument("--probe", action="store_true", help="fit check on arm A only: no eval-form scoring, no result files")
args = p.parse_args()

from transformers import AutoTokenizer, AutoModelForCausalLM
dev = args.device
tok = AutoTokenizer.from_pretrained(args.lm)
lm = AutoModelForCausalLM.from_pretrained(args.lm, torch_dtype=torch.bfloat16 if dev == "cuda" else torch.float32).to(dev).eval()
for q_ in lm.parameters():
    q_.requires_grad_(False)
LMW = lm.config.hidden_size
POS = 9 if args.copy else 8
BOS, EOS = tok.bos_token_id, tok.eos_token_id
emb = lm.get_input_embeddings()
NUM = {v: tok(str(v), add_special_tokens=False).input_ids for v in range(LO, HI + 1)}
assert all(len(x) == 1 for x in NUM.values())
NUMID = torch.tensor([NUM[v][0] for v in range(LO, HI + 1)], device=dev)
digit_ids = {i for i in range(len(tok)) if tok.decode([i]).strip().isdigit()} if False else None


def embed_numbers(vals):
    return emb(NUMID[(vals - LO).clamp(0, HI - LO)])


def encode(rows):
    seqs = [[BOS] + tok(r["text"], add_special_tokens=False).input_ids + [EOS] for r in rows]
    T = max(len(s) for s in seqs)
    ids = torch.zeros(len(rows), T, dtype=torch.long); mask = torch.zeros(len(rows), T, dtype=torch.bool)
    lit = torch.zeros(len(rows), 2, dtype=torch.long); vals = torch.zeros(len(rows), 2, dtype=torch.long)
    for i, (s, r) in enumerate(zip(seqs, rows)):
        ids[i, :len(s)] = torch.tensor(s); mask[i, :len(s)] = True
        pos = [j for j, t in enumerate(s) if j > 0 and tok.decode([t]).strip().isdigit()]
        assert len(pos) == 2, (r["text"], pos)
        lit[i] = torch.tensor([x - 1 for x in pos])  # index after dropping the BOS position
        vals[i] = torch.tensor([int(tok.decode([s[x]]).strip()) for x in pos])
        assert vals[i].tolist() == [r["x"], r["y"]], (r["text"], vals[i].tolist())
    return ids.to(dev), mask.to(dev), lit.to(dev), vals.to(dev)


@torch.no_grad()
def lm_states(ids, mask):
    out = lm(input_ids=ids, attention_mask=mask.long(), output_hidden_states=True)
    h = out.hidden_states[-1][:, 1:]  # drop BOS position
    return h, mask[:, 1:]


def run_batch(model, rows, train):
    ids, mask, lit, vals = encode(rows)
    feats, qm = lm_states(ids, mask)
    lit_ok = torch.ones_like(lit, dtype=torch.bool)
    ans = torch.tensor([NUM[r["answer"]][0] for r in rows], device=dev)
    gold = None
    if train:
        act = torch.tensor([1 if r["op"] == "ADD" else 2 for r in rows], device=dev)
        gold = {"action": act, "left": torch.zeros_like(act), "right": torch.ones_like(act)}
    with torch.autocast(dev, dtype=torch.bfloat16, enabled=dev == "cuda"):
        prefix, log = model(feats, qm, lit, lit_ok, vals, embed_numbers, gold, args.call_loop)
        B = len(rows)
        parts = [emb(torch.full((B, 1), BOS, device=dev)), prefix.to(emb.weight.dtype)]
        if args.copy:
            _, _, _, res0, ok0 = log["calls"][args.call_loop]
            copyv = emb(NUMID[(res0 - LO).clamp(0, HI - LO)]) * ok0[:, None].to(emb.weight.dtype)
            parts.append(copyv[:, None])
        inp = torch.cat(parts + [emb(ans[:, None])], 1)
        logits = lm(inputs_embeds=inp).logits.float()
    return logits, ans, log, gold


def evaluate(model, rows, bs=32):
    model.eval(); out = []
    with torch.no_grad():
        for i in range(0, len(rows), bs):
            chunk = rows[i:i + bs]
            logits, ans, log, _ = run_batch(model, chunk, False)
            pred = logits[:, POS].argmax(-1)
            act, li, ri, res, ok = log["calls"][args.call_loop]
            for j, r in enumerate(chunk):
                want = 1 if r["op"] == "ADD" else 2
                good_ops = {(0, 1), (1, 0)} if r["op"] == "ADD" else {(0, 1)}
                call_ok = int(act[j]) == want and (int(li[j]), int(ri[j])) in good_ops
                pnum = tok.decode([int(pred[j])]).strip()
                out.append({"id": r.get("id"), "cell": r.get("cell"), "op": r["op"], "answer": r["answer"],
                            "pred": pnum, "final_ok": int(pred[j]) == int(ans[j]), "call_ok": call_ok,
                            "op_ok": int(act[j]) == want, "calls_made": int(sum(int(c[0][j]) != 0 for c in log["calls"]))})
    model.train(); return out


def summarize(res, T):
    def rate(sel, key):
        sel = list(sel); return round(sum(r[key] for r in sel) / max(1, len(sel)), 4), len(sel)
    s = {}
    for cell in sorted({r["cell"] for r in res if r["cell"]}):
        sub = [r for r in res if r["cell"] == cell]
        s[cell] = {"final": rate(sub, "final_ok"), "call": rate(sub, "call_ok"), "op": rate(sub, "op_ok")}
    for name in ("unseen", "seen"):
        sub = [r for r in res if r["cell"] and r["cell"].startswith(name)]
        wrong = [r for r in sub if not r["final_ok"]]
        inT = sum(1 for r in wrong if r["pred"].isdigit() and int(r["pred"]) in T)
        # pairs both right
        byp = {}
        for r in sub: byp.setdefault(r["id"].rsplit("-", 1)[0], []).append(r["final_ok"])
        s[name] = {"final": rate(sub, "final_ok"), "call": rate(sub, "call_ok"), "op": rate(sub, "op_ok"),
                   "pairs_both_right": [sum(all(v) for v in byp.values()), len(byp)],
                   "wrong_answers": len(wrong), "wrong_equal_a_training_answer": inT}
    return s


def main():
    torch.manual_seed(args.seed); random.seed(args.seed)
    Tans, Hans = gen.answer_split(); Tset = set(Tans)
    form = json.loads((HERE / args.eval_form).read_text())
    ex = gen.eval_pair_set(form) | gen.eval_pair_set(json.loads((HERE / "EVAL-FORM-v1.json").read_text()))
    n_total = args.steps * args.batch
    if args.arm == "A":
        pool = json.loads((HERE / "ARM-A-POOL-v1.json").read_text())
        order = []
        rng = random.Random(1000 + args.seed)
        while len(order) < n_total:
            perm = list(range(len(pool))); rng.shuffle(perm); order += perm
        data = [pool[i] for i in order[:n_total]]
    else:
        if args.wording == 'mix':
            import gen2
            data = gen2.stream_w(ex, args.seed, n_total)
        else:
            data = gen.stream_b(ex, args.seed, n_total)
        assert len({r["text"] for r in data}) == len(data)
    assert all(r["answer"] in Tset for r in data) and not ({(r["x"], r["y"]) for r in data} & ex)
    model = Reasoner(LMW).to(dev)
    nparam = sum(p_.numel() for p_ in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(i, args.steps) / args.steps)))
    name = f"arm{args.arm}{'copy' if args.copy else ''}{'-delay%d' % args.call_loop if args.call_loop else ''}{'-mix' if args.wording == 'mix' else ''}-seed{args.seed}"
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    logf = open(outdir / f"{name}.log", "w")
    t0 = time.time()
    fit_rows = data[-192:] if args.arm == "B" else random.Random(5).sample(json.loads((HERE / "ARM-A-POOL-v1.json").read_text()), 192)
    for step in range(args.steps):
        rows = data[step * args.batch:(step + 1) * args.batch]
        logits, ans, log, gold = run_batch(model, rows, True)
        ce = F.cross_entropy(logits[:, POS], ans) + 0.5 * F.cross_entropy(logits[:, POS + 1], torch.full_like(ans, EOS))
        act0 = gold["action"]
        cl = args.call_loop
        ca = F.cross_entropy(log["act"][cl], act0) + sum(F.cross_entropy(a, torch.zeros_like(act0)) for i_, a in enumerate(log["act"]) if i_ > cl) / max(1, LOOPS - 1 - cl) if cl < LOOPS - 1 else F.cross_entropy(log["act"][cl], act0)
        cp = F.cross_entropy(log["left"], gold["left"]) + F.cross_entropy(log["right"], gold["right"])
        loss = ce + ca + cp + model.aux()
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step()
        if step % 100 == 0 or step == args.steps - 1:
            msg = f"step {step} loss {loss.item():.4f} ce {ce.item():.4f} act {ca.item():.4f} ptr {cp.item():.4f} t {time.time()-t0:.0f}s"
            if step % 500 == 0 or step == args.steps - 1:
                fr = evaluate(model, fit_rows[:64]); msg += f" | trainfit64 final {sum(r['final_ok'] for r in fr)/64:.3f} call {sum(r['call_ok'] for r in fr)/64:.3f}"
            print(msg, flush=True); logf.write(msg + "\n"); logf.flush()
    fit = evaluate(model, fit_rows)
    if args.probe:
        print(f"PROBE {name} lr {args.lr} trainfit192 final {sum(r['final_ok'] for r in fit)/192:.4f} call {sum(r['call_ok'] for r in fit)/192:.4f}", flush=True)
        return
    ev = evaluate(model, form)
    res = {"arm": args.arm, "seed": args.seed, "steps": args.steps, "batch": args.batch, "params": nparam,
           "seconds": round(time.time() - t0), "eval": summarize(ev, Tset),
           "train_fit_192": {"final": sum(r["final_ok"] for r in fit) / 192, "call": sum(r["call_ok"] for r in fit) / 192},
           "calls_made_dist": {k: sum(1 for r in ev if r["calls_made"] == k) for k in range(5)}}
    (outdir / f"{name}.json").write_text(json.dumps(res, indent=1))
    (outdir / f"{name}-rows.json").write_text(json.dumps(ev))
    import base64, gzip
    print("RESULT-JSON " + name + " " + json.dumps(res), flush=True)
    for r in ev:
        print("ROW " + name + " " + json.dumps(r), flush=True)
    print(json.dumps(res["eval"]["unseen"]), json.dumps(res["eval"]["seen"]), res["train_fit_192"], flush=True)


main()
