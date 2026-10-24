"""LoRA RL on sandbox tasks with Claude as grader. --algo grpo | jolt_plus. See SPEC.md."""
import argparse, json, os, random, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, PeftModel, get_peft_model
from grader import Grader
from rollout import rollout, prompt_ids, hint_block, seq_terms

TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def load_tasks(path, n=None):
    rows = [json.loads(l) for l in open(path)]
    return rows[:n] if n else rows


def load_model(a, dev):
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.bfloat16 if dev == "cuda" else torch.float32).to(dev)
    if a.adapter:
        model = PeftModel.from_pretrained(model, a.adapter, is_trainable=not a.eval_only)
    elif not a.eval_only:
        model = get_peft_model(model, LoraConfig(r=a.lora_r, lora_alpha=2 * a.lora_r, target_modules=TARGETS, lora_dropout=0.0, task_type="CAUSAL_LM"))
    if not a.eval_only:
        base = model.get_base_model()
        base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        base.enable_input_require_grads()
        model.train()
    return tok, model


def reward(eps, graded):
    fr = [e.check_frac() for e in eps]
    return [0.6 * f + 0.4 * s / 10 for f, (s, _) in zip(fr, graded)], fr


def advantages(r, G):
    out = []
    for i in range(0, len(r), G):
        g = r[i:i + G]
        m = sum(g) / len(g)
        out += [x - m for x in g]
    return out


def ntok(eps):
    return max(1, sum(sum(e.mask[e.prompt_len:]) for e in eps))


def evaluate(a, tok, model, grader, dev):
    tasks = load_tasks(a.heldout, a.n_eval)
    eps = []
    for i in range(0, len(tasks), a.gen_batch * 2):
        eps += rollout(model, tok, [(t, None) for t in tasks[i:i + a.gen_batch * 2]], greedy=True, gen_batch=a.gen_batch)
    graded = grader.grade_many([(e.task, e.transcript) for e in eps]) if a.eval_grade else [(None, "")] * len(eps)
    rows = []
    for e, (s, cr) in zip(eps, graded):
        ch = e.checks()
        rows.append(dict(id=e.task["id"], scenario=e.task["scenario"], checks=ch, success=all(ch), sonnet=s, turns=e.turns, final=e.final[:300]))
    tag = os.path.basename(a.adapter.rstrip("/")) if a.adapter else "base"
    with open(os.path.join(a.outdir, f"eval_{tag}.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    summ = dict(adapter=a.adapter, n=len(rows), success_rate=sum(r["success"] for r in rows) / len(rows),
                mean_check_frac=sum(sum(r["checks"]) / len(r["checks"]) for r in rows) / len(rows),
                sonnet_mean=(sum(r["sonnet"] for r in rows) / len(rows)) if a.eval_grade else None, usd=grader.ledger.usd)
    json.dump(summ, open(os.path.join(a.outdir, f"eval_{tag}.json"), "w"), indent=1)
    print(summ)
    return summ


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", choices=["grpo", "jolt_plus"], default="grpo")
    ap.add_argument("--model", default="Qwen/Qwen3-1.7B")
    ap.add_argument("--train", default=os.path.join(os.path.dirname(__file__), "data/tasks_train.jsonl"))
    ap.add_argument("--heldout", default=os.path.join(os.path.dirname(__file__), "data/tasks_heldout.jsonl"))
    ap.add_argument("--outdir", default="runs/run")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--tasks-per-step", type=int, default=8)
    ap.add_argument("--group", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--lora-r", type=int, default=32)
    ap.add_argument("--beta-t", type=float, default=0.05)
    ap.add_argument("--beta-s", type=float, default=1.0)
    ap.add_argument("--max-usd", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--gen-batch", type=int, default=16)
    ap.add_argument("--max-new", type=int, default=384)
    ap.add_argument("--max-total", type=int, default=2048)
    ap.add_argument("--eval-only", action="store_true")
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--eval-grade", action="store_true")
    ap.add_argument("--n-eval", type=int, default=None)
    ap.add_argument("--fake-grader", action="store_true")
    ap.add_argument("--save-every", type=int, default=10)
    a = ap.parse_args(argv)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(a.outdir, exist_ok=True)
    random.seed(a.seed); torch.manual_seed(a.seed)
    grader = Grader(a.outdir, a.max_usd, fake=a.fake_grader, seed=a.seed)
    tok, model = load_model(a, dev)
    if a.eval_only:
        return evaluate(a, tok, model, grader, dev)
    tasks = load_tasks(a.train)
    order_rng = random.Random(a.seed)  # same task order for both algos
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
    G, jolt, t0, gen_tokens = a.group, a.algo == "jolt_plus", time.time(), 0
    logf = open(os.path.join(a.outdir, "log.jsonl"), "a")
    for step in range(1, a.steps + 1):
        batch = order_rng.sample(tasks, a.tasks_per_step)
        calls0, ts = grader.n_calls, time.time()
        eps_s = rollout(model, tok, [(t, None) for t in batch for _ in range(G)], max_new=a.max_new, max_total=a.max_total, gen_batch=a.gen_batch)
        gr_s = grader.grade_many([(e.task, e.transcript) for e in eps_s])
        r_s, fr_s = reward(eps_s, gr_s)
        A_s = advantages(r_s, G)
        st = dict(step=step, reward=sum(r_s) / len(r_s), check_frac=sum(fr_s) / len(fr_s), success=sum(f == 1 for f in fr_s) / len(fr_s),
                  sonnet=sum(s for s, _ in gr_s) / len(gr_s), A_abs=sum(map(abs, A_s)) / len(A_s), A_max=max(A_s), A_min=min(A_s))
        eps_t = []
        if jolt:
            cs = []
            for i in range(len(batch)):  # critique of the worst student attempt in each group
                grp = range(i * G, (i + 1) * G)
                w = min(grp, key=lambda j: r_s[j])
                cs.append(hint_block(batch[i], gr_s[w][1]))
            eps_t = rollout(model, tok, [(t, cs[i]) for i, t in enumerate(batch) for _ in range(G)], max_new=a.max_new, max_total=a.max_total, gen_batch=a.gen_batch)
            gr_t = grader.grade_many([(e.task, e.transcript) for e in eps_t])
            r_t, fr_t = reward(eps_t, gr_t)
            A_t = advantages(r_t, G)
            st.update(teacher_reward=sum(r_t) / len(r_t), teacher_success=sum(f == 1 for f in fr_t) / len(fr_t), teacher_sonnet=sum(s for s, _ in gr_t) / len(gr_t))
        st["gen_s"] = time.time() - ts
        gen_tokens += sum(sum(e.mask[e.prompt_len:]) for e in eps_s + eps_t)
        # ---- one gradient update ----
        model.train(); opt.zero_grad(set_to_none=True)
        Ns, Nt = ntok(eps_s), ntok(eps_t)
        pg_s = kl_s = pg_t = kl_t = 0.0
        for e, A in zip(eps_s, A_s):
            ids, pos = e.view(e.ids[:e.prompt_len])
            if not pos:
                continue
            other = e.view(prompt_ids(tok, e.task, cs[batch.index(e.task)])) if jolt else None
            lp, kl = seq_terms(model, ids, pos, other)
            loss = -A * lp.sum() / Ns + (a.beta_s * kl.sum() / Ns if jolt else 0)
            loss.backward()
            pg_s += float((-A * lp.sum() / Ns).detach()); kl_s += float((kl.sum() / Ns).detach()) if jolt else 0
        for e, A in zip(eps_t, A_t if jolt else []):
            ids, pos = e.view(e.ids[:e.prompt_len])
            if not pos:
                continue
            lp, kl = seq_terms(model, ids, pos, e.view(prompt_ids(tok, e.task, None)))
            (-A * lp.sum() / Nt + a.beta_t * kl.sum() / Nt).backward()
            pg_t += float((-A * lp.sum() / Nt).detach()); kl_t += float((kl.sum() / Nt).detach())
        gn = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        st.update(loss_pg_student=pg_s, loss_kl_student=kl_s, loss_pg_teacher=pg_t, loss_kl_teacher=kl_t, grad_norm=float(gn),
                  grader_calls=grader.n_calls - calls0, grader_calls_total=grader.n_calls, usd=grader.ledger.usd, tokens_generated=gen_tokens,
                  spot_agree=grader.spot_agreement(), wall_s=time.time() - t0)
        logf.write(json.dumps(st) + "\n"); logf.flush()
        print({k: round(v, 4) if isinstance(v, float) else v for k, v in st.items()}, flush=True)
        if step % a.save_every == 0 or step == a.steps:
            model.save_pretrained(os.path.join(a.outdir, f"adapter_step{step}"))
    model.save_pretrained(os.path.join(a.outdir, "adapter_final"))


if __name__ == "__main__":
    main()
