"""English rerun on the real pipeline (two-doors round 3). One run = one arm, one seed. Marks: PASS-MARKS-R3.md.

Same real modules and recipe as ../run_story.py (PR #33 commit 34608a1: contextual reader, 9.0M ordered core with
begin_latent + 4 advance_latent, StatePrefix exit, prefix before BOS). Task = the English pilot's training bank
(24 passages x {source_text, paraphrase} x 2 questions = 96 rows, 48 QA) and a fresh held-out set written for this
round (FRESH-EN-R3.json: 48 new passages, 96 questions, asked of source_text and of paraphrase). Multi-token answers:
teacher-forced CE on answer tokens + EOS; greedy generation at test, exact match after the bank's normalization.

Arms (one change vs pool):
  pool    today's real exit: 8 pooled prefix vectors.
  allptr  pool + 8 pointer vectors (Linear(256->8), softmax over prompt positions, value = LM input embedding there)
          + the LM input embeddings of every prompt token (the 'all words' arm; Ben 02:01 UTC 10-04: no objection).
Lesion at test (allptr): the 8 pooled core vectors zeroed. Reference (--arm lm_alone, eval only): the frozen
instruct LM with its chat template, passage + question, no trained parts.
"""
import argparse, json, math, os, random, re, sys, time, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE.parent, HERE.parent / "scripts", HERE.parent / "scripts" / "cap256_launch", HERE):
    sys.path.insert(0, str(p))

import torch
from torch import nn
from torch.nn import functional as F

p = argparse.ArgumentParser()
p.add_argument("--arm", choices=["pool", "allptr", "lm_alone", "lm_fewshot"], required=True)
p.add_argument("--seed", type=int, default=0)
p.add_argument("--steps", type=int, default=2000)
p.add_argument("--batch", type=int, default=16)
p.add_argument("--lr", type=float, default=1e-3)
p.add_argument("--lm", default="LiquidAI/LFM2.5-1.2B-Instruct")
p.add_argument("--revision", default="0f604ada3f766f9f257460c4c9f0b5d6f69d431b")
p.add_argument("--train", default=str(HERE / "english_training_candidates_v3.json"))
p.add_argument("--fresh", default=str(HERE / "FRESH-EN-R3.json"))
p.add_argument("--out", default=str(HERE / "results"))
p.add_argument("--device", default="cuda")
p.add_argument("--max-new", type=int, default=12)
p.add_argument("--limit", type=int, default=0)  # dry runs only
p.add_argument("--gen", type=int, default=0)  # round 4: add this many generated examples (gen_english.py) to the bank
p.add_argument("--heldout", default=str(HERE / "GEN-HELDOUT-R4.json"))
p.add_argument("--drop-fams", default="")  # round 5: comma list of families removed from bank rows and generated rows
p.add_argument("--extra-eval", default="")  # round 5: extra eval file (new question kinds), reported as res["extra"]
p.add_argument("--tag", default="")
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


def norm(s):
    s = unicodedata.normalize("NFC", s).lower().replace("’", "'").replace("‘", "'").strip()
    s = re.sub(r"\s+", " ", s); return re.sub(r"[.!?,;:]+$", "", s).strip()


def rows_of(path, panels, examples=None):
    out = []
    for e in (examples if examples is not None else json.load(open(path))["examples"]):
        for panel, key in panels:
            for qi, q in enumerate(e["questions"]):
                out.append({"id": f"{e['id']}-{key}-q{qi}", "family": e["family"], "panel": panel, "type": q["type"],
                            "text": e[key] + " " + q["question"], "passage": e[key], "question": q["question"],
                            "answer": q["canonical_answer"], "accepted": [norm(a) for a in [q["canonical_answer"]] + q["accepted_answers"]]})
    return out


_cache = {}


def ids_of(r):
    if r["text"] not in _cache:
        ids = tok.encode(r["text"], add_special_tokens=False) + [EOS]
        assert len(ids) <= 49, (r["id"], len(ids))
        _cache[r["text"]] = ids
    return _cache[r["text"]]


def ans_ids(r):
    return tok.encode(" " + r["answer"], add_special_tokens=False) + [EOS]


if not args.arm.startswith("lm_"):
    from calculator_runtime import CalculatorPath, STATUS_IDS
    from sol_translator_grounding import HumanInputProjection
    from sol_translator_english_v6 import StatePrefix
    from sol_spatial_poc_ordered_v2 import OrderedAttentionReasoner
    import claude_fewex_net as base
    from sol_stop_ordered_api2 import ordered_attention_math

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
            if args.arm == "allptr":
                self.ptr = nn.Linear(256, K)


def make_prefix(model, ids, lesion=None):
    """ids [B,n] (equal prompt length incl. EOS) -> prefix embeddings [B,P,LMW]."""
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
    parts = [prefix]
    if args.arm == "allptr":
        pw = model.ptr(h).float().softmax(1)
        parts += [torch.einsum("bnk,bnl->bkl", pw, tok_e), tok_e]
    return torch.cat(parts, 1).to(emb.weight.dtype)


def group_by_len(rows):
    by = {}
    for r in rows:
        by.setdefault(len(ids_of(r)), []).append(r)
    return list(by.values())


def loss_on(model, rows):
    ids = torch.tensor([ids_of(r) for r in rows], device=dev)
    pre = make_prefix(model, ids)
    B, P = pre.shape[0], pre.shape[1]
    A = [ans_ids(r) for r in rows]; m = max(map(len, A))
    tgt = torch.full((B, m), -100, device=dev, dtype=torch.long)
    inp_ids = torch.full((B, m), EOS, device=dev, dtype=torch.long)
    for b, a in enumerate(A):
        tgt[b, :len(a)] = torch.tensor(a); inp_ids[b, :len(a) - 1] = torch.tensor(a[:-1])
    inp = torch.cat([pre, emb(torch.full((B, 1), BOS, device=dev)), emb(inp_ids[:, :m - 1])], 1)
    logits = lm(inputs_embeds=inp).logits.float()[:, P:]  # predicts answer tokens then EOS
    return F.cross_entropy(logits.transpose(1, 2), tgt, ignore_index=-100, reduction="sum") / (tgt != -100).sum()


@torch.no_grad()
def generate(pre):
    B = pre.shape[0]
    cur = torch.cat([pre, emb(torch.full((B, 1), BOS, device=dev))], 1)
    out = [[] for _ in range(B)]; done = [False] * B
    for _ in range(args.max_new):
        nxt = lm(inputs_embeds=cur).logits[:, -1].argmax(-1)
        for b in range(B):
            if not done[b]:
                if int(nxt[b]) == EOS: done[b] = True
                else: out[b].append(int(nxt[b]))
        if all(done): break
        cur = torch.cat([cur, emb(nxt[:, None])], 1)
    return [tok.decode(o).strip() for o in out]


def score(r, pred):
    n = norm(pred)
    return {"id": r["id"], "family": r["family"], "panel": r["panel"], "type": r["type"], "answer": r["answer"],
            "pred": pred, "ok": n in r["accepted"], "contains": any(a and a in n for a in r["accepted"])}


@torch.no_grad()
def evaluate(model, rows, lesion=None):
    model.eval(); out = []
    for g in group_by_len(rows):
        for i in range(0, len(g), 32):
            c = g[i:i + 32]
            preds = generate(make_prefix(model, torch.tensor([ids_of(r) for r in c], device=dev), lesion))
            out += [score(r, pr) for r, pr in zip(c, preds)]
    model.train(); return out


SHOTS = []


@torch.no_grad()
def eval_lm_alone(rows):
    out = []
    for r in rows:
        msgs = []
        for sh in SHOTS:
            msgs += [{"role": "user", "content": f"{sh['passage']}\n{sh['question']}\nAnswer with a short phrase only."},
                     {"role": "assistant", "content": sh["answer"]}]
        msgs += [{"role": "user", "content": f"{r['passage']}\n{r['question']}\nAnswer with a short phrase only."}]
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)["input_ids"].to(dev)
        g = lm.generate(ids, max_new_tokens=args.max_new, do_sample=False)
        out.append(score(r, tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True).strip()))
    return out


def summarize(res, train_answers, bank_words):
    def rate(sel, k="ok"):
        sel = list(sel); return [round(sum(r[k] for r in sel) / max(1, len(sel)), 4), len(sel)]
    s = {"all": rate(res), "all_contains": rate(res, "contains")}
    for pn in sorted({r["panel"] for r in res}):
        s[pn] = rate(r for r in res if r["panel"] == pn)
    for fam in sorted({r["family"] for r in res}):
        s["fam:" + fam] = rate(r for r in res if r["family"] == fam)
    s["yes_no"] = rate(r for r in res if r["type"] == "yes_no")
    s["short_answer"] = rate(r for r in res if r["type"] == "short_answer")
    new = [r for r in res if r["type"] == "short_answer" and not (set(norm(r["answer"]).split()) & bank_words)]
    s["new_word_answers"] = rate(new)
    wrong = [r for r in res if not r["ok"]]
    s["wrong_is_train_answer"] = [sum(norm(r["pred"]) in train_answers for r in wrong), len(wrong)]
    return s


def main():
    train = rows_of(args.train, [("train_source", "source_text"), ("train_paraphrase", "paraphrase")])
    drop = [f for f in args.drop_fams.split(",") if f]
    train = [r for r in train if r["family"] not in drop]
    gen_train, held = [], []
    if args.gen:
        import gen_english as GE
        gen_train = rows_of(None, [("gen_source", "source_text"), ("gen_paraphrase", "paraphrase")], GE.make(args.gen, 1000 + args.seed, "train", drop=drop))
        held = [r for r in rows_of(args.heldout, [("held_source", "source_text"), ("held_paraphrase", "paraphrase")]) if r["family"] not in drop]
    extra = rows_of(args.extra_eval, [("new_source", "source_text"), ("new_paraphrase", "paraphrase")]) if args.extra_eval else []
    fresh = rows_of(args.fresh, [("fresh_source", "source_text"), ("fresh_paraphrase", "paraphrase")])
    bank = json.load(open(args.train))["examples"]
    train_answers = {a for r in train for a in r["accepted"]}
    stop = {"the", "a", "an", "to", "of", "in", "on", "by", "with", "did", "and", "yes", "no"}
    bank_words = {w for e in bank for t in (e["source_text"], e["paraphrase"]) for w in norm(t).replace(",", " ").replace(";", " ").replace(".", " ").replace("'s", " ").split()} - stop
    assert not ({r["text"] for r in fresh} & {r["text"] for r in train + gen_train})
    assert not ({r["text"] for r in held} & {r["text"] for r in gen_train})
    if args.limit:
        fresh = fresh[::max(1, len(fresh) // args.limit)][:args.limit]
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    name = f"{args.arm}{'-gen' if args.gen else ''}{args.tag}-seed{args.seed}"
    if args.arm.startswith("lm_"):
        if args.arm == "lm_fewshot":  # one bank example per family, first question, source text (8 shots incl. 2 yes/no)
            fams = {}
            for r in train:
                if r["panel"] == "train_source": fams.setdefault(r["family"], []).append(r)
            SHOTS.extend([v[0] for v in fams.values()] + [r for r in train if r["type"] == "yes_no" and r["panel"] == "train_source"][:2])
        ev = eval_lm_alone(fresh); fit = eval_lm_alone(train[:args.limit] if args.limit else train)
        if extra:
            evx = eval_lm_alone(extra[:args.limit] if args.limit else extra)
            (outdir / f"{name}-extra-rows.json").write_text(json.dumps(evx))
        res = {"arm": args.arm, "extra": summarize(evx, train_answers, bank_words) if extra else None, "train_fit": summarize(fit, train_answers, bank_words)["all"], "eval": summarize(ev, train_answers, bank_words)}
        (outdir / f"{name}-rows.json").write_text(json.dumps(ev))
        (outdir / f"{name}.json").write_text(json.dumps(res, indent=1))
        print("RESULT-JSON " + name + " fresh " + str(res["eval"]["all"]) + " contains " + str(res["eval"]["all_contains"]), flush=True)
        return
    random.seed(args.seed)
    model = Model(args.seed).to(dev)
    params = [q for q in model.parameters() if q.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(i, args.steps) / args.steps)))
    rng = random.Random(100 + args.seed); order = []
    t0 = time.time()
    for step in range(args.steps):
        while len(order) < args.batch:
            ep = train + gen_train; rng.shuffle(ep); order += ep
        rows, order = order[:args.batch], order[args.batch:]
        opt.zero_grad(set_to_none=True); tot = 0.0
        for g in group_by_len(rows):  # equal prompt lengths per forward; accumulate to one step of `batch` rows
            l = loss_on(model, g) * len(g) / len(rows); l.backward(); tot += l.item()
        torch.nn.utils.clip_grad_norm_(params, 1.0); opt.step(); sched.step()
        if step % 100 == 0 or step == args.steps - 1:
            print(f"{name} step {step} loss {tot:.4f} t {time.time()-t0:.0f}s", flush=True)
    fit = evaluate(model, train[:args.limit] if args.limit else train)
    ev = evaluate(model, fresh)
    res = {"arm": args.arm, "seed": args.seed, "steps": args.steps, "batch": args.batch, "seconds": round(time.time() - t0),
           "params": sum(q.numel() for q in params), "train_fit": summarize(fit, train_answers, bank_words)["all"],
           "eval": summarize(ev, train_answers, bank_words)}
    (outdir / f"{name}-rows.json").write_text(json.dumps(ev))
    (outdir / f"{name}-train-rows.json").write_text(json.dumps(fit))
    if held:
        evh = evaluate(model, held); res["gen_heldout"] = summarize(evh, train_answers, bank_words)
        (outdir / f"{name}-heldout-rows.json").write_text(json.dumps(evh))
    res["gen"] = args.gen; res["drop_fams"] = drop; res["tag"] = args.tag
    if extra:
        evx = evaluate(model, extra[:args.limit] if args.limit else extra); res["extra"] = summarize(evx, train_answers, bank_words)
        (outdir / f"{name}-extra-rows.json").write_text(json.dumps(evx))
    if args.arm == "allptr":
        evl = evaluate(model, fresh, "zero_pool"); res["lesion_zero_pool"] = summarize(evl, train_answers, bank_words)
        (outdir / f"{name}-lesion-zero_pool-rows.json").write_text(json.dumps(evl))
    (outdir / f"{name}.json").write_text(json.dumps(res, indent=1))
    print("RESULT-JSON " + name + " fit " + str(res["train_fit"]) + " fresh " + str(res["eval"]["all"]) + " newword " + str(res["eval"]["new_word_answers"]), flush=True)


main()
