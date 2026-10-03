"""Two-step run: chained calls + copy path. One-step items (30%) mixed into training. Eval on EVAL-TWO-v1.json (two-step only)."""
import argparse, json, math, random, time
from pathlib import Path
import torch
from torch.nn import functional as F
import gen, gen_two
from model2 import Reasoner2, LOOPS, LO, HI

HERE = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, required=True); p.add_argument("--steps", type=int, default=3000)
p.add_argument("--batch", type=int, default=16); p.add_argument("--lr", type=float, default=1e-3)
p.add_argument("--lm", default="LiquidAI/LFM2.5-1.2B-Instruct"); p.add_argument("--out", default=str(HERE / "results2"))
p.add_argument("--device", default="cuda"); p.add_argument("--no-copy", action="store_true")
args = p.parse_args()
from transformers import AutoTokenizer, AutoModelForCausalLM
dev = args.device
tok = AutoTokenizer.from_pretrained(args.lm)
lm = AutoModelForCausalLM.from_pretrained(args.lm, dtype=torch.bfloat16 if dev == "cuda" else torch.float32).to(dev).eval()
for q_ in lm.parameters(): q_.requires_grad_(False)
LMW = lm.config.hidden_size; BOS, EOS = tok.bos_token_id, tok.eos_token_id; emb = lm.get_input_embeddings()
NUMID = torch.tensor([tok(str(v), add_special_tokens=False).input_ids[0] for v in range(LO, HI + 1)], device=dev)
POS = 8 if args.no_copy else 9


def embed_numbers(v): return emb(NUMID[(v - LO).clamp(0, HI - LO)])


def encode(rows):
    seqs = [[BOS] + tok(r["text"], add_special_tokens=False).input_ids + [EOS] for r in rows]
    T = max(map(len, seqs)); B = len(rows)
    ids = torch.zeros(B, T, dtype=torch.long); mask = torch.zeros(B, T, dtype=torch.bool)
    lit = torch.zeros(B, 3, dtype=torch.long); ok = torch.zeros(B, 3, dtype=torch.bool); vals = torch.zeros(B, 3, dtype=torch.long)
    for i, (s, r) in enumerate(zip(seqs, rows)):
        ids[i, :len(s)] = torch.tensor(s); mask[i, :len(s)] = True
        pos = [j for j, t in enumerate(s) if j > 0 and tok.decode([t]).strip().isdigit()]
        want = [r["x"], r["y"]] + ([r["z"]] if r["steps"] == 2 else [])
        got = [int(tok.decode([s[j]]).strip()) for j in pos]
        assert got == want, (r["text"], got, want)
        for k in range(len(pos)): lit[i, k] = pos[k] - 1; vals[i, k] = got[k]; ok[i, k] = True
        for k in range(len(pos), 3): lit[i, k] = pos[-1] - 1
    return ids.to(dev), mask.to(dev), lit.to(dev), ok.to(dev), vals.to(dev)


def gold_of(rows):
    B = len(rows); act = torch.zeros(B, LOOPS, dtype=torch.long); l = torch.zeros(B, LOOPS, dtype=torch.long); r = torch.zeros(B, LOOPS, dtype=torch.long)
    for i, row in enumerate(rows):
        op1 = row["op1"] if row["steps"] == 2 else row["op"]
        act[i, 0] = 1 if op1 == "ADD" else 2; l[i, 0], r[i, 0] = 0, 1
        if row["steps"] == 2:
            act[i, 1] = 1 if row["op2"] == "ADD" else 2; l[i, 1], r[i, 1] = 3, 2
    return {"action": act.to(dev), "left": l.to(dev), "right": r.to(dev)}


def run_batch(model, rows, train):
    ids, mask, lit, lok, vals = encode(rows)
    with torch.no_grad():
        h = lm(input_ids=ids, attention_mask=mask.long(), output_hidden_states=True).hidden_states[-1][:, 1:]
    qm = mask[:, 1:]
    gold = gold_of(rows) if train else None
    ans = torch.tensor([int(tok(str(r["answer"]), add_special_tokens=False).input_ids[0]) for r in rows], device=dev)
    with torch.autocast(dev, dtype=torch.bfloat16, enabled=dev == "cuda"):
        prefix, log, fres, fok = model(h, qm, lit, lok, vals, embed_numbers, gold)
        B = len(rows)
        parts = [emb(torch.full((B, 1), BOS, device=dev)), prefix.to(emb.weight.dtype)]
        if not args.no_copy:
            parts.append((emb(NUMID[(fres - LO).clamp(0, HI - LO)]) * fok[:, None].to(emb.weight.dtype))[:, None])
        logits = lm(inputs_embeds=torch.cat(parts + [emb(ans[:, None])], 1)).logits.float()
    return logits, ans, log, gold


def evaluate(model, rows, bs=32):
    model.eval(); out = []
    with torch.no_grad():
        for i in range(0, len(rows), bs):
            ch = rows[i:i + bs]
            logits, ans, log, _ = run_batch(model, ch, False)
            pred = logits[:, POS].argmax(-1)
            c0, c1 = log["calls"][0], log["calls"][1]
            for j, r in enumerate(ch):
                def good(c, want_op, pairs):
                    return int(c[0][j]) == (1 if want_op == "ADD" else 2) and (int(c[1][j]), int(c[2][j])) in pairs
                two = r["steps"] == 2
                op1 = r["op1"] if two else r["op"]
                call1 = good(c0, op1, {(0, 1), (1, 0)} if op1 == "ADD" else {(0, 1)})
                call2 = (good(c1, r["op2"], {(3, 2), (2, 3)} if r["op2"] == "ADD" else {(3, 2)})) if two else int(c1[0][j]) == 0
                out.append({"id": r.get("id"), "cell": r.get("cell"), "steps": r["steps"], "op1": op1, "op2": r.get("op2"), "answer": r["answer"],
                            "pred": tok.decode([int(pred[j])]).strip(), "final_ok": int(pred[j]) == int(ans[j]), "call1_ok": bool(call1),
                            "call2_ok": bool(call2), "chain_ok": bool(call1 and call2)})
    model.train(); return out


def main():
    torch.manual_seed(args.seed); random.seed(args.seed)
    T, Ho = gen.answer_split(); Ts = set(T)
    form = json.loads((HERE / "EVAL-TWO-v1.json").read_text())
    v1 = json.loads((HERE / "EVAL-FORM-v1.json").read_text()); v2 = json.loads((HERE / "EVAL-FORM-v2.json").read_text())
    ex = gen.eval_pair_set(v1) | gen.eval_pair_set(v2) | {(r["x"], r["y"], r["z"]) for r in form}
    n_total = args.steps * args.batch
    data = gen_two.stream_two(ex, args.seed, n_total)
    assert all(r["answer"] in Ts for r in data) and sum(r["steps"] == 2 for r in data) > 0
    model = Reasoner2(LMW).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(i, args.steps) / args.steps)))
    name = f"two-seed{args.seed}" + ("-nocopy" if args.no_copy else "")
    Path(args.out).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    fit = [r for r in data[-400:] if r["steps"] == 2][:96]
    for step in range(args.steps):
        rows = data[step * args.batch:(step + 1) * args.batch]
        logits, ans, log, gold = run_batch(model, rows, True)
        ce = F.cross_entropy(logits[:, POS], ans) + 0.5 * F.cross_entropy(logits[:, POS + 1], torch.full_like(ans, EOS))
        ca = sum(F.cross_entropy(log["act"][k], gold["action"][:, k]) for k in range(LOOPS)) / LOOPS
        cp = 0
        for k in range(2):
            sel = gold["action"][:, k] != 0
            if bool(sel.any()):
                cp = cp + F.cross_entropy(log["left"][k][sel], gold["left"][:, k][sel]) + F.cross_entropy(log["right"][k][sel], gold["right"][:, k][sel])
        loss = ce + ca + cp + model.aux()
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step()
        if step % 100 == 0 or step == args.steps - 1:
            msg = f"step {step} loss {loss.item():.4f} ce {ce.item():.4f} act {ca.item():.4f} ptr {float(cp):.4f} t {time.time()-t0:.0f}s"
            if step % 500 == 0 or step == args.steps - 1:
                fr = evaluate(model, fit); msg += f" | trainfit2step final {sum(r['final_ok'] for r in fr)/len(fr):.3f} chain {sum(r['chain_ok'] for r in fr)/len(fr):.3f}"
            print(msg, flush=True)
    ev = evaluate(model, form)
    for r in ev: print("ROW " + name + " " + json.dumps(r), flush=True)
    (Path(args.out) / f"{name}-rows.json").write_text(json.dumps(ev))
    print("DONE " + name, flush=True)


main()
