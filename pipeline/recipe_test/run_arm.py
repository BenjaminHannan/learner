"""One run of the real-pipeline recipe test (see PASS-MARKS.md, fixed before training).

Real modules, fresh weights: HumanInputProjection reader on frozen-LM lexical embeddings, real ordered fresh 9.0M core
(shallow arm), real CalculatorPath heads + mechanical calculator (calculator_tools), 4 predicted calls with the real
label policy (train_calculator_poc_v3.supervision), real StatePrefix exit pooled to 8 prefix vectors, human_loss.
Only the batching is new: the real CalculatorPath.forward is batch 1, so `calc_forward` repeats its mechanics for a
batch of equal-length questions (the real core refuses ragged batches).

--copy : add the frozen LM's embedding of the latest OK calculator result as a 9th prefix vector (zeros if none).
--wording old|mix : old = 4 templates; mix = half old, half 180 composed frames (gen2).
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

import gen, gen2
from calculator_runtime import CalculatorPath, ACTIONS, STATUS_IDS
from calculator_tools import build_registry, execute_integer_call
from sol_translator_grounding import HumanInputProjection
from sol_translator_english_v6 import StatePrefix
from sol_spatial_poc_ordered_v2 import OrderedAttentionReasoner
import claude_fewex_net as base
from sol_stop_ordered_api2 import ordered_attention_math

p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, required=True)
p.add_argument("--copy", action="store_true")
p.add_argument("--ctx", action="store_true", help="reader reads the frozen LM's contextual last-layer states instead of lexical embeddings")
p.add_argument("--task", choices=["one", "two"], default="one")
p.add_argument("--ordered", action="store_true", help="each loop reads the question with its own learned attention query instead of the mean")
p.add_argument("--wording", choices=["old", "mix"], default="old")
p.add_argument("--frames", choices=["base", "comp", "tabv", "rlv"], default="base", help="two-step training frames: the fixed set, or the fixed set plus composed frames (round 4)")
p.add_argument("--blind", action="store_true", help="also evaluate on the independently written layouts (round 5)")
p.add_argument("--blind2", action="store_true", help="also evaluate on the round-6 independently written layouts")
p.add_argument("--long", action="store_true", help="round 7: lift the core query cap to 160 tokens, train on 30%% lengthened items, also score a long (55-150 token) fresh set")
p.add_argument("--dist", action="store_true", help="round 8: half of the lengthened training items also carry irrelevant numbers (needs --long)")
p.add_argument("--distr", action="store_true", help="round 8: also score the long set with irrelevant numbers inside")
p.add_argument("--steps", type=int, default=3000)
p.add_argument("--batch", type=int, default=16)
p.add_argument("--lr", type=float, default=1e-3)
p.add_argument("--lm", default="LiquidAI/LFM2.5-1.2B-Instruct")
p.add_argument("--revision", default="0f604ada3f766f9f257460c4c9f0b5d6f69d431b")
p.add_argument("--out", default=str(HERE / "results"))
p.add_argument("--device", default="cuda")
p.add_argument("--name", default=None)
args = p.parse_args()
dev = args.device

from transformers import AutoTokenizer, AutoModelForCausalLM
if os.path.isdir(args.lm):
    tok = AutoTokenizer.from_pretrained(args.lm)
    lm = AutoModelForCausalLM.from_pretrained(args.lm, torch_dtype=torch.float32)
else:
    tok = AutoTokenizer.from_pretrained(args.lm, revision=args.revision)
    lm = AutoModelForCausalLM.from_pretrained(args.lm, revision=args.revision, torch_dtype=torch.float32)
lm = lm.to(dev).eval().requires_grad_(False)
if dev == "cuda":
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
LMW = lm.config.hidden_size
BOS, EOS = tok.bos_token_id, tok.eos_token_id
emb = lm.get_input_embeddings()
NUMTOK = {v: tok.encode(str(v), add_special_tokens=False) for v in range(0, 400)}
assert all(len(NUMTOK[v]) == 1 for v in range(gen.LO, gen.HI + 1))
POS = 9 if args.copy else 8  # index of the BOS position after the prefix


def build_core(seed):
    # exactly fresh_core_calculator_constructor 'shallow' (9,007,790 params) but for any seed
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
        self.tool = CalculatorPath(256)
        self.loop_q = nn.Parameter(torch.randn(4, 256) * 0.02)  # only used with --ordered


_cache = {}


def encode_row(r):
    """token ids (with EOS), mechanical registry, checked operand refs. Cached by text."""
    key = r["text"]
    if key in _cache:
        return _cache[key]
    ids = tok.encode(r["text"], add_special_tokens=False) + [EOS]
    reg = build_registry(r["text"], tok)
    want = [r["x"], r["y"]] + ([r["z"]] if r.get("steps", 1) == 2 else [])
    vals = [e["value"] for e in reg]
    if vals == want:
        lit = list(range(len(want)))
    else:  # round 8: irrelevant numbers inside the text; the task operands must each appear exactly once among the literals
        assert len(reg) <= 8 and len(set(want)) == len(want) and all(vals.count(w) == 1 for w in want), (r["text"], reg)
        lit = [vals.index(w) for w in want]
    out = (ids, reg, lit)
    _cache[key] = out
    return out


def task_call_matches(trace, desired_action, desired_refs):
    # real train_calculator_poc_v3.task_call_matches
    if trace.get("status") != "OK" or trace.get("action") != desired_action:
        return False
    actual = tuple(trace.get("resolved_references", ()))
    return len(actual) == 2 and (set(actual) == set(desired_refs) if desired_action == "ADD" else actual == tuple(desired_refs))


def calc_forward(model, ids, regs):
    """Batched repeat of CalculatorPath.forward. ids [B,n] (EOS last, equal length), regs: list of literal registries.
    Returns h [B,n,256], per-loop logits, per-sample traces, latest OK result value (or None) per sample."""
    B, n = ids.shape
    core, reader, tool = model.core, model.reader, model.tool
    with torch.no_grad():
        if args.ctx:
            bosc = torch.full((B, 1), BOS, device=dev, dtype=ids.dtype)
            e0 = lm(input_ids=torch.cat([bosc, ids], 1), output_hidden_states=True).hidden_states[-1][:, 1:].float()
        else:
            e0 = emb(ids)
    mask = torch.ones(B, n, dtype=torch.bool, device=dev)
    query = reader(e0, mask)  # [B,1,n,256]
    role = tool.role
    memo = query.new_zeros((B, 8, 256))
    pending = tool.status.weight[STATUS_IDS["PENDING"]]
    for pair in range(4):
        memo[:, 2 * pair] = role
        memo[:, 2 * pair + 1] = pending + role
    with ordered_attention_math():
        state = core.begin_latent(query, memo, query_mask=mask, notebook_mask=torch.ones((B, 8), dtype=torch.bool, device=dev))
    codes = state["e"][:, n:] - memo
    cands = [[dict(r) for r in reg] for reg in regs]
    loops, traces = [], [[] for _ in range(B)]
    latest = [None] * B
    for L in range(4):
        feats = state["h"] + state["e"]
        if args.ordered:  # loop-indexed ordered read: loop L attends over the question with its own learned query
            w = ((feats[:, :n] @ model.loop_q[L]) / 16.0).softmax(-1)
            qmean = (feats[:, :n] * w[..., None]).sum(1)
        else:
            qmean = feats[:, :n].mean(1)
        action_logits = tool.action(qmean)
        C = max(len(c) for c in cands)
        refm = feats.new_zeros((B, C, 256)); valid = torch.zeros(B, C, dtype=torch.bool, device=dev)
        for b in range(B):
            for j, c in enumerate(cands[b]):
                idx = c["token_indices"] if c["source"] == "literal" else [c["slot_index"]]
                refm[b, j] = feats[b, idx].mean(0)
                valid[b, j] = True
        left = (torch.einsum("bd,df,bcf->bc", qmean, tool.left, refm) / math.sqrt(256)).masked_fill(~valid, -1e4)
        right = (torch.einsum("bd,df,bcf->bc", qmean, tool.right, refm) / math.sqrt(256)).masked_fill(~valid, -1e4)
        act = action_logits.argmax(-1).tolist(); li = left.argmax(-1).tolist(); ri = right.argmax(-1).tolist()
        content = query.new_zeros((B, 256)); status_ids = []
        ok_rows, ok_tok = [], []
        for b in range(B):
            a = ACTIONS[act[b]]; refs = []
            if a != "NONE" and cands[b]:
                refs = [cands[b][li[b]]["id"], cands[b][ri[b]]["id"]]
            tr = execute_integer_call(a, refs, cands[b], call_index=L + 1)
            tr["resolved_references"] = tr.get("resolved_references", [])
            tr["candidate_ids"] = [c["id"] for c in cands[b]]
            tr["left_index"], tr["right_index"] = (li[b], ri[b]) if a != "NONE" and cands[b] else (None, None)
            st = tr["status"]
            if st == "OK":
                v = tr["result"]["value"]
                t = NUMTOK.get(v) if (type(v) is int and 0 <= v < 400) else tok.encode(str(v), add_special_tokens=False)
                if t is None or len(t) != 1 or t[0] in (BOS, EOS, 0):
                    tr["status"] = st = "ERROR"; tr["error_code"] = "UNSUPPORTED_NUMERIC_TOKEN"; tr["result"] = None
                else:
                    ok_rows.append(b); ok_tok.append(t[0]); latest[b] = t[0]
            status_ids.append(STATUS_IDS[st])
            traces[b].append(tr)
        if ok_rows:
            tid = torch.tensor(ok_tok, device=dev)[:, None]
            with torch.no_grad():
                e_num = emb(tid)
            enc = reader(e_num, torch.ones(len(ok_rows), 1, dtype=torch.bool, device=dev))[:, 0, 0]
            content = content.index_put((torch.tensor(ok_rows, device=dev),), enc)
        vs, ss = n + 2 * L, n + 2 * L + 1
        next_e = state["e"].clone(); next_h = state["h"].clone()
        next_e[:, vs] = codes[:, 2 * L] + content + role
        next_e[:, ss] = codes[:, 2 * L + 1] + tool.status.weight[torch.tensor(status_ids, device=dev)] + role
        next_h[:, vs:ss + 1] = 0
        loops.append({"action_logits": action_logits, "left": left, "right": right})
        for b in range(B):
            if traces[b][-1]["status"] == "OK":
                cands[b].append({**traces[b][-1]["result"], "slot_index": vs, "token_indices": [vs]})
        with ordered_attention_math():
            state = core.advance_latent({**state, "h": next_h, "e": next_e})
    h = state["h"][:, :n]
    return h, loops, traces, latest


def forward(model, rows):
    enc = [encode_row(r) for r in rows]
    ids = torch.tensor([e[0] for e in enc], device=dev)
    assert ids.shape[1] == len(enc[0][0]) and all(len(e[0]) == ids.shape[1] for e in enc)
    h, loops, traces, latest = calc_forward(model, ids, [e[1] for e in enc])
    B, n = ids.shape
    prefix = model.adapter.project_training(h, torch.ones_like(h, dtype=torch.bool), torch.ones(B, n, dtype=torch.bool, device=dev), (1, n))
    parts = [prefix.to(emb.weight.dtype)]
    if args.copy:
        cv = torch.zeros(B, LMW, device=dev)
        for b in range(B):
            if latest[b] is not None:
                cv[b] = emb.weight[latest[b]].detach()
        parts.append(cv[:, None])
    prefix_all = torch.cat(parts, 1)
    ans = torch.tensor([NUMTOK[r["answer"]][0] for r in rows], device=dev)
    bos = torch.full((B, 1), BOS, device=dev)
    inp = torch.cat([prefix_all, emb(bos), emb(ans[:, None])], 1)
    logits = lm(inputs_embeds=inp).logits.float()[:, POS:]  # [B,2,V]: predicts ans, then EOS
    return logits, ans, loops, traces


def supervision(r, loops_traces):
    """real label policy, extended to chains: the task calls in order, each repeated until a correct predicted call, then NONE.
    One-step rows reduce exactly to the round-1/2 policy. Pointers = candidate indices of the desired refs."""
    two = r.get("steps", 1) == 2
    op1 = r["op1"] if two else r["op"]
    lit = encode_row(r)[2]
    desired = [(op1, (f"literal:{lit[0]}", f"literal:{lit[1]}"))] + ([(r["op2"], (None, f"literal:{lit[2]}"))] if two else [])
    labels, stage, rid = [], 0, None
    for tr in loops_traces:
        if stage == len(desired):
            labels.append((0, None)); continue
        want, refs = desired[stage]
        if stage == 1:
            refs = (rid, f"literal:{lit[2]}")
        cid = tr["candidate_ids"]
        labels.append((ACTIONS.index(want), [cid.index(refs[0]), cid.index(refs[1])]))
        if task_call_matches(tr, want, refs):
            if stage == 0:
                rid = tr["result"]["id"]
            stage += 1
    return labels, stage


def losses(rows, logits, ans, loops, traces):
    B = len(rows)
    tgt = torch.stack([ans, torch.full_like(ans, EOS)], 1)
    final = F.cross_entropy(logits.transpose(1, 2), tgt)  # mean over [ans, EOS], as human_loss
    act_terms, ptr_terms = [], []
    sup = [supervision(r, traces[b]) for b, r in enumerate(rows)]
    for L in range(4):
        al = loops[L]["action_logits"]
        at = torch.tensor([sup[b][0][L][0] for b in range(B)], device=dev)
        act_terms.append(F.cross_entropy(al, at, reduction="none"))
        elig = torch.tensor([sup[b][0][L][1] is not None for b in range(B)], device=dev)
        if bool(elig.any()):
            lt = torch.tensor([sup[b][0][L][1][0] if sup[b][0][L][1] else 0 for b in range(B)], device=dev)
            rt = torch.tensor([sup[b][0][L][1][1] if sup[b][0][L][1] else 0 for b in range(B)], device=dev)
            pl = (F.cross_entropy(loops[L]["left"], lt, reduction="none") + F.cross_entropy(loops[L]["right"], rt, reduction="none")) / 2
            ptr_terms.append((pl * elig).sum() / elig.sum())
    action_ce = torch.stack(act_terms).mean()
    pointer_ce = torch.stack(ptr_terms).mean() if ptr_terms else action_ce * 0
    return final, action_ce, pointer_ce


def bucket_batches(rows, bs, rng, drop_last=True):
    by = {}
    for r in rows:
        by.setdefault(len(encode_row(r)[0]), []).append(r)
    batches = []
    for k, rs in by.items():
        rng.shuffle(rs)
        for i in range(0, len(rs), bs):
            chunk = rs[i:i + bs]
            if len(chunk) == bs or not drop_last:
                batches.append(chunk)
    rng.shuffle(batches)
    return batches


@torch.no_grad()
def evaluate(model, rows):
    model.eval(); out = []
    for chunk in bucket_batches(rows, 32, random.Random(0), drop_last=False):
        logits, ans, loops, traces = forward(model, chunk)
        pred = logits[:, 0].argmax(-1); pred2 = logits[:, 1].argmax(-1)
        for b, r in enumerate(chunk):
            _, stage = supervision(r, traces[b])
            need = 2 if r.get("steps", 1) == 2 else 1
            last_ok = [tr for tr in traces[b] if tr["status"] == "OK"]
            first_hit = any(task_call_matches(tr, (r["op1"] if need == 2 else r["op"]), (f"literal:{encode_row(r)[2][0]}", f"literal:{encode_row(r)[2][1]}")) for tr in traces[b])
            out.append({"id": r.get("id"), "cell": r.get("cell"), "structure": r.get("structure"), "steps": need,
                        "op": r.get("op"), "op1": r.get("op1"), "op2": r.get("op2"), "answer": r["answer"],
                        "pred": tok.decode([int(pred[b])]).strip(),
                        "final_ok": bool(pred[b] == ans[b] and pred2[b] == EOS),
                        "first_token_ok": bool(pred[b] == ans[b]),
                        "call_ok": stage >= need, "call1_ok": stage >= 1, "chain_ok": stage >= need,
                        "first_call_ok": traces[b][0]["status"] == "OK" and first_hit,
                        "last_result_ok": bool(last_ok and last_ok[-1]["result"]["value"] == r["answer"]),
                        "calls_made": sum(tr["action"] != "NONE" for tr in traces[b])})
    model.train(); return out


def rate(sel, key):
    sel = list(sel)
    return round(sum(bool(r[key]) for r in sel) / max(1, len(sel)), 4), len(sel)


def summarize(res, T):
    s = {}
    for cell in sorted({r["cell"] for r in res if r["cell"]}):
        sub = [r for r in res if r["cell"] == cell]
        s[cell] = {k: rate(sub, k) for k in ("final_ok", "call_ok", "first_call_ok", "last_result_ok")}
    for name in ("unseen", "seen"):
        sub = [r for r in res if r["cell"] and r["cell"].startswith(name)]
        wrong = [r for r in sub if not r["final_ok"]]
        inT = sum(1 for r in wrong if r["pred"].isdigit() and int(r["pred"]) in T)
        s[name] = {k: rate(sub, k) for k in ("final_ok", "call_ok", "last_result_ok")}
        s[name].update(wrong_answers=len(wrong), wrong_equal_a_training_answer=inT)
    for w in ("train_wording", "new_wording"):
        sub = [r for r in res if r["cell"] and r["cell"].endswith(w)]
        s[w] = {k: rate(sub, k) for k in ("final_ok", "call_ok", "last_result_ok")}
    s["all"] = {k: rate([r for r in res if r["cell"]], k) for k in ("final_ok", "call_ok", "last_result_ok")}
    return s


def summarize_two(res, T):
    s = {}
    def agg(sel):
        sel = list(sel)
        d = {k: rate(sel, k) for k in ("chain_ok", "call1_ok", "final_ok", "last_result_ok")}
        d["call2_given_call1"] = rate([r for r in sel if r["call1_ok"]], "chain_ok")
        return d
    s["all"] = agg(res)
    for st in sorted({r["structure"] for r in res}):
        s[st] = agg(r for r in res if r["structure"] == st)
    for cell in ("unseen", "seen"):
        s[cell] = agg(r for r in res if r["cell"].startswith(cell))
        wrong = [r for r in res if r["cell"].startswith(cell) and not r["final_ok"]]
        s[cell].update(wrong_answers=len(wrong), wrong_equal_a_training_answer=sum(1 for r in wrong if r["pred"].isdigit() and int(r["pred"]) in T))
    for op in ("ADD", "SUB"):
        s["second_" + op] = agg(r for r in res if r["op2"] == op)
        s["first_" + op] = agg(r for r in res if r["op1"] == op)
    return s


def main():
    random.seed(args.seed)
    Tans, _ = gen.answer_split(); Tset = set(Tans)
    n_total = int(args.steps * args.batch * 1.25) + 64
    if args.task == "two":
        import gen_two_r3 as g3
        ntok = lambda t: len(tok.encode(t, add_special_tokens=False)) + 1
        fits = lambda t: ntok(t) <= 49  # real core query cap (short eval sets stay under it)
        if args.long:
            import sol_spatial_poc_ordered_v2 as _ov2
            _ov2.QUERY_CAP = 160  # the cap is an interface guard in ordered_begin, read at call time; fresh weights, nothing sealed is changed on disk
            fits_train = lambda t: ntok(t) <= 160
        else:
            fits_train = fits
        form = g3.build_eval(fits=fits)
        form_b = g3.build_blind(fits=fits, used={(r["x"], r["y"], r["z"]) for r in form}) if args.blind else []
        form_b2 = g3.build_blind(fits=fits, seed=20261601, fname="eval_layouts_r6_blind.json", used={(r["x"], r["y"], r["z"]) for r in form + form_b}) if args.blind2 else []
        import gen_two_long
        form_l = gen_two_long.build_long(ntok, used={(r["x"], r["y"], r["z"]) for r in form + form_b + form_b2}) if args.long else []
        form_d = gen_two_long.build_distr(ntok, used={(r["x"], r["y"], r["z"]) for r in form + form_b + form_b2 + form_l}) if args.distr else []
        ex_t = {(r["x"], r["y"], r["z"]) for r in form + form_b + form_b2 + form_l + form_d}
        ex_p = gen.eval_pair_set(gen.eval_form())
        data = g3.stream(ex_t, ex_p, args.seed, n_total, fits=fits_train, frames=args.frames, long_frac=0.3 if args.long else 0.0, ntok=ntok, dist_frac=0.5 if args.dist else 0.0)
        assert all(r["answer"] in Tset for r in data) and not ({(r["x"], r["y"], r["z"]) for r in data if r["steps"] == 2} & ex_t)
        ex = ex_p
    else:
        form = gen.eval_form()
        ex = gen.eval_pair_set(form)
        data = gen2.stream_w(ex, args.seed, n_total) if args.wording == "mix" else gen.stream_b(ex, args.seed, n_total)
        assert all(r["answer"] in Tset for r in data) and not ({(r["x"], r["y"]) for r in data} & ex)
    assert len({r["text"] for r in data}) == len(data)
    t0 = time.time()
    batches = bucket_batches(data, args.batch, random.Random(100 + args.seed))
    assert len(batches) >= args.steps, (len(batches), args.steps)
    batches = batches[:args.steps]
    fit_rows = [r for b in batches[-24:] for r in b if (args.task == "one" or r["steps"] == 2)][:192]  # last training-stream questions (train wording share only reported)
    print(f"encoded {n_total} rows in {time.time()-t0:.0f}s; {len(batches)} batches", flush=True)
    model = Model(args.seed).to(dev)
    params = [q for q in model.parameters() if q.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(i, args.steps) / args.steps)))
    name = args.name or f"{'two-' if args.task == 'two' else ''}{'copy' if args.copy else 'pool'}{'-ctx' if args.ctx else ''}{'-ord' if args.ordered else ''}{('-' + args.frames if args.frames != 'base' else '') + ('-long' if args.long else '') + ('-dist' if args.dist else '')}-{args.wording}-seed{args.seed}"
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    logf = open(outdir / f"{name}.log", "w")
    t0 = time.time()
    for step, rows in enumerate(batches):
        logits, ans, loops, traces = forward(model, rows)
        final, action_ce, pointer_ce = losses(rows, logits, ans, loops, traces)
        loss = final + action_ce + pointer_ce
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0); opt.step(); sched.step()
        if step % 100 == 0 or step == args.steps - 1:
            msg = f"step {step} loss {loss.item():.4f} final {final.item():.4f} act {action_ce.item():.4f} ptr {pointer_ce.item():.4f} t {time.time()-t0:.0f}s"
            print(msg, flush=True); logf.write(msg + "\n"); logf.flush()
    fit = evaluate(model, fit_rows)
    ev = evaluate(model, form)
    res = {"name": name, "seed": args.seed, "copy": args.copy, "ctx": args.ctx, "round": gen.ROUND, "wording": args.wording, "steps": args.steps, "batch": args.batch,
           "seconds": round(time.time() - t0), "task": args.task, "ordered": args.ordered, "frames": args.frames,
           "eval": (summarize_two if args.task == "two" else summarize)(ev, Tset),
           "train_fit_192": {k: rate(fit, k)[0] for k in ("final_ok", "call_ok", "chain_ok", "last_result_ok")}}
    if args.blind:
        evb = evaluate(model, form_b)
        res["eval_blind"] = summarize_two(evb, Tset)
        (outdir / f"{name}-blindrows.json").write_text(json.dumps(evb))
    if args.long:
        evl = evaluate(model, form_l)
        res["eval_long"] = summarize_two(evl, Tset)
        for lo, hi in ((55, 80), (81, 110), (111, 150)):
            sel = [r_ for r_, f_ in zip(sorted(evl, key=lambda q: q["id"]), sorted(form_l, key=lambda q: q["id"])) if lo <= f_["ntok"] <= hi]
            res["eval_long"][f"tok_{lo}_{hi}"] = {"chain_ok": list(rate(sel, "chain_ok")), "call1_ok": list(rate(sel, "call1_ok"))}
        res["eval_long"]["ntok_min_max"] = [min(f_["ntok"] for f_ in form_l), max(f_["ntok"] for f_ in form_l)]
        (outdir / f"{name}-longrows.json").write_text(json.dumps(evl))
    if args.distr:
        evd = evaluate(model, form_d)
        res["eval_distr"] = summarize_two(evd, Tset)
        for lo, hi in ((55, 80), (81, 110), (111, 150)):
            sel = [r_ for r_, f_ in zip(sorted(evd, key=lambda q: q["id"]), sorted(form_d, key=lambda q: q["id"])) if lo <= f_["ntok"] <= hi]
            res["eval_distr"][f"tok_{lo}_{hi}"] = {"chain_ok": list(rate(sel, "chain_ok")), "call1_ok": list(rate(sel, "call1_ok"))}
        (outdir / f"{name}-distrrows.json").write_text(json.dumps(evd))
    if args.blind2:
        evb2 = evaluate(model, form_b2)
        res["eval_blind2"] = summarize_two(evb2, Tset)
        (outdir / f"{name}-blind2rows.json").write_text(json.dumps(evb2))
    (outdir / f"{name}.json").write_text(json.dumps(res, indent=1))
    (outdir / f"{name}-rows.json").write_text(json.dumps(ev))
    (outdir / f"{name}-fitrows.json").write_text(json.dumps(fit))
    print("RESULT-JSON " + json.dumps(res), flush=True)


main()
