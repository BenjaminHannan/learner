"""Sleep-1 (see backbone/PREREG-sleep1.md). Arms: s0 (base), ic (facts in context), s1 (plain LoRA), s2 (dreams + KL guard).

  python backbone/sleep/sleep1.py --arm s2 --model Qwen/Qwen3.5-2B --out out/sleep/s2
  python backbone/sleep/sleep1.py --arm s2 --smoke --out /tmp/x      # CPU, tiny random qwen3_5
"""
import argparse
import json
import math
import random
import re
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import facts as facts_mod  # noqa: E402
from train import LORA_TARGETS, load_model  # noqa: E402

SYS = "Answer with just the name."
K = 4
ARC_SMOKE = [{"question": "Which is a mammal?", "choices": ["trout", "dog", "eagle", "frog"], "answer": 1},
             {"question": "Water freezes at what Celsius temperature?", "choices": ["0", "50", "100", "-40"], "answer": 0},
             {"question": "What do plants need for photosynthesis?", "choices": ["sunlight", "sand", "plastic", "salt"], "answer": 0}]

_TOPICS = ["volcanoes", "bread", "the moon", "bicycles", "photosynthesis", "the Roman Empire", "tea", "electric cars", "honeybees",
           "the ocean", "chess", "jazz", "rainbows", "libraries", "earthquakes", "soccer", "coffee", "glaciers", "the internet", "dinosaurs"]
_TASKS = ["Explain {t} in two sentences.", "Give me three fun facts about {t}.", "Write a haiku about {t}.",
          "What is a common misconception about {t}?", "Describe {t} to a ten-year-old.", "List two pros and two cons related to {t}.",
          "Write one question a student might ask about {t}, and answer it.", "Summarize why {t} matters in one sentence.",
          "What would a beginner need to know about {t}?", "Write a short, friendly tweet about {t}."]
_HAND = ["What is the capital of France?", "How many days are in a leap year?", "Translate 'good morning' into Spanish.",
         "What is 17 times 23?", "Write a Python function that reverses a string.", "Give me a recipe idea for dinner with rice and beans.",
         "What is the difference between weather and climate?", "Suggest a name for a pet goldfish.", "How do I politely decline an invitation?",
         "What is the boiling point of water in Fahrenheit?", "Write a two-line poem about autumn.", "Who wrote Romeo and Juliet?",
         "Explain what a prime number is.", "What are three tips for studying effectively?", "Convert 5 kilometres to miles.",
         "What does DNA stand for?", "Write a polite email asking for a deadline extension.", "What is the largest planet in our solar system?",
         "Why is the sky blue?", "Give me a synonym for 'happy'."]


def generic_prompts():
    rng = random.Random(1)
    combos = [t.format(t=x) for x in _TOPICS for t in _TASKS]
    rng.shuffle(combos)
    return (_HAND + combos)[:200]


# ------------------------------------------------------------------ text plumbing
class Lang:
    def __init__(self, tok, smoke, device):
        self.tok, self.smoke, self.device = tok, smoke, device
        self.eos = tok.eos_token_id

    def render(self, system, user):
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
        if hasattr(self.tok, "apply_chat_template") and not self.smoke:
            return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        return "".join(f"{m['role']}: {m['content']}\n" for m in msgs) + "assistant: "

    def ids(self, text):
        return self.tok(text, add_special_tokens=False)["input_ids"]

    def decode(self, ids):
        return self.tok.decode(ids, skip_special_tokens=True)

    @torch.no_grad()
    def generate(self, model, prompts, max_new=20, bs=8, sample=False, temp=0.8):
        outs = [None] * len(prompts)
        order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
        for s in range(0, len(order), bs):
            idx = order[s:s + bs]
            enc = [self.ids(prompts[i]) for i in idx]
            n = max(map(len, enc))
            pad = 0 if self.smoke else (self.tok.pad_token_id if self.tok.pad_token_id is not None else self.eos)
            ids = torch.full((len(enc), n), pad, dtype=torch.long)
            mask = torch.zeros((len(enc), n), dtype=torch.long)
            for r, e in enumerate(enc):
                ids[r, n - len(e):] = torch.tensor(e)
                mask[r, n - len(e):] = 1
            kw = dict(do_sample=True, temperature=temp, top_p=0.95, top_k=0) if sample else dict(do_sample=False)
            out = model.generate(input_ids=ids.to(self.device), attention_mask=mask.to(self.device), max_new_tokens=max_new,
                                 pad_token_id=pad, eos_token_id=self.eos, **kw)
            for r, i in enumerate(idx):
                outs[i] = self.decode(out[r, n:].tolist()).strip()
        return outs

    def pad_right(self, seqs):
        n = max(map(len, seqs))
        ids = torch.zeros((len(seqs), n), dtype=torch.long)
        mask = torch.zeros((len(seqs), n), dtype=torch.long)
        for r, e in enumerate(seqs):
            ids[r, :len(e)] = torch.tensor(e)
            mask[r, :len(e)] = 1
        return ids.to(self.device), mask.to(self.device)


def q_prompt(L, q, context=None):
    if context:
        return L.render(SYS, "Facts:\n" + "\n".join(f"- {t}" for t in context) + f"\n\nQuestion: {q}")
    return L.render(SYS, q)


# ------------------------------------------------------------------ scoring
def score_qa(L, model, items, context, bs):
    prompts = [q_prompt(L, it["q"], context) for it in items]
    ans = L.generate(model, prompts, max_new=20, bs=bs)
    ok = [it["target"].lower() in a.lower() for it, a in zip(items, ans)]
    return {"acc": sum(ok) / len(ok), "n": len(ok),
            "examples": [{"q": it["q"], "target": it["target"], "answer": a, "correct": c} for it, a, c in list(zip(items, ans, ok))[:20]]}


@torch.no_grad()
def score_arc(L, model, rows, bs=8):
    letters = "ABCDE"
    lid = [L.ids(c)[0] for c in letters]
    correct, ex = 0, []
    for s in range(0, len(rows), bs):
        chunk = rows[s:s + bs]
        seqs = []
        for r in chunk:
            u = r["question"] + "\n" + "\n".join(f"{letters[i]}. {c}" for i, c in enumerate(r["choices"])) + "\nAnswer with the letter only."
            seqs.append(L.ids(L.render(None, u)))
        ids, mask = L.pad_right(seqs)
        logits = model(input_ids=ids, attention_mask=mask).logits
        for r, row in enumerate(chunk):
            last = logits[r, len(seqs[r]) - 1].float()
            sc = last[lid[:len(row["choices"])]]
            pred = int(sc.argmax())
            correct += pred == row["answer"]
            if len(ex) < 20:
                ex.append({"q": row["question"], "pred": letters[pred], "gold": letters[row["answer"]]})
    return {"acc": correct / len(rows), "n": len(rows), "examples": ex}


def load_arc(smoke):
    if smoke:
        return ARC_SMOKE
    from datasets import load_dataset
    ds = load_dataset("allenai/ai2_arc", "ARC-Easy", split="test")
    rows = []
    for r in list(ds)[:500]:
        labels = r["choices"]["label"]
        rows.append({"question": r["question"], "choices": r["choices"]["text"], "answer": labels.index(r["answerKey"])})
    return rows


# ------------------------------------------------------------------ dreaming
def dream_prompt(L, world, fact):
    ctx = "\n".join(f"- {t}" for t in world["teaching"])
    u = (f"Here are facts you learned today:\n{ctx}\n\nFocus on this fact: \"{fact['text']}\"\n\n"
         f"Write {K} paraphrases of this fact (different wording, same meaning, naming both entities) and {K} question-answer pairs "
         f"about it. Cover both directions: some questions should ask about one entity, some about the other. Each answer must be a "
         f"single name from the fact. Reply with only JSON of the form "
         f"{{\"paraphrases\": [\"...\"], \"qa\": [{{\"q\": \"...\", \"a\": \"...\"}}]}}")
    return L.render("You are a careful assistant that studies facts.", u)


def parse_dream(txt):
    paras, qas = [], []
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            paras = [p for p in d.get("paraphrases", []) if isinstance(p, str)]
            qas = [(x.get("q"), x.get("a")) for x in d.get("qa", []) if isinstance(x, dict) and isinstance(x.get("q"), str) and isinstance(x.get("a"), str)]
            return paras, qas
        except Exception:
            pass
    for line in txt.splitlines():  # fallback: "Q: ... A: ..." lines and bare sentences
        line = line.strip().lstrip("-*0123456789. ").strip()
        mm = re.match(r"(?:Q:|Question:)\s*(.+?)\s*(?:\||A:|Answer:)\s*(.+)$", line)
        if mm:
            qas.append((mm.group(1), mm.group(2)))
    return paras, qas


def dream(L, model, world, tests, bs, smoke, log):  # tests: all test question strings (leak filter)
    facts = world["facts"]
    raw = L.generate(model, [dream_prompt(L, world, f) for f in facts], max_new=500 if not smoke else 40, bs=bs, sample=True, temp=0.8)
    leak = {facts_mod.norm(t) for t in tests}
    stats = {"facts": len(facts), "parse_fail": 0, "paraphrases_gen": 0, "paraphrases_kept": 0, "qa_gen": 0, "qa_kept": 0,
             "dropped_test_leak": 0, "dropped_missing_entities": 0, "dropped_bad_answer": 0, "dropped_unverified": 0, "dropped_dup": 0}
    cand_p, cand_q = [], []
    for f, txt in zip(facts, raw):
        paras, qas = parse_dream(txt)
        if smoke and not paras and not qas:  # random tiny model emits noise; fabricate so the pipeline is exercised
            paras = [f["text"] + " (smoke)"]
            qas = [(f"What is linked to {f['a']}?", f["b"])]
        if not paras and not qas:
            stats["parse_fail"] += 1
        for p in paras[:K]:
            stats["paraphrases_gen"] += 1
            if any(l in facts_mod.norm(p) for l in leak):
                stats["dropped_test_leak"] += 1
            elif not all(e.lower() in p.lower() for e in f["entities"]):
                stats["dropped_missing_entities"] += 1
            else:
                cand_p.append((f["id"], p.strip()))
        for q, a in qas[:K]:
            stats["qa_gen"] += 1
            nq = facts_mod.norm(q)
            ents = [e for e in f["entities"] if e.lower() in a.lower()]
            if any(l in nq or nq in l for l in leak):
                stats["dropped_test_leak"] += 1
            elif len(ents) != 1 or ents[0].lower() in q.lower():
                stats["dropped_bad_answer"] += 1
            else:
                cand_q.append((f["id"], q.strip(), ents[0]))
    # verification: answer each own question greedily with all facts in context
    ver = L.generate(model, [q_prompt(L, q, world["teaching"]) for _, q, _ in cand_q], max_new=20, bs=bs)
    kept_q, seen = [], set()
    for (fid, q, ent), v in zip(cand_q, ver):
        if ent.lower() not in v.lower() and not smoke:  # smoke: random model never verifies; keep all to exercise the path
            stats["dropped_unverified"] += 1
        elif (q.lower(), ent) in seen:
            stats["dropped_dup"] += 1
        else:
            seen.add((q.lower(), ent))
            kept_q.append({"fact": fid, "q": q, "a": ent})
    kept_p, seenp = [], set()
    for fid, p in cand_p:
        if p.lower() in seenp:
            stats["dropped_dup"] += 1
        else:
            seenp.add(p.lower())
            kept_p.append({"fact": fid, "text": p})
    stats["paraphrases_kept"], stats["qa_kept"] = len(kept_p), len(kept_q)
    log(f"[dream] {stats}")
    return kept_p, kept_q, stats, raw[:5]


# ------------------------------------------------------------------ training
def build_examples(L, world, paras, qas):
    ex = []  # (ids, loss_mask_start): loss on tokens from `start`
    for t in world["teaching"] + [p["text"] for p in paras]:
        ids = L.ids(t) + [L.eos]
        ex.append((ids, 0))
    for x in qas:
        p = L.ids(L.render(SYS, x["q"]))
        a = L.ids(x["a"]) + [L.eos]
        ex.append((p + a, len(p)))
    return ex


def train(L, pm, examples, args, replay, log):
    params = [p for p in pm.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
    rng = random.Random(args.seed)
    pool, curve = [], []
    pm.train()
    for step in range(args.steps):
        lr = args.lr * 0.5 * (1 + math.cos(math.pi * step / args.steps))
        for g in opt.param_groups:
            g["lr"] = lr
        batch = []
        while len(batch) < args.bsz:
            if not pool:
                pool = list(range(len(examples)))
                rng.shuffle(pool)
            batch.append(examples[pool.pop()])
        ids, mask = L.pad_right([b[0] for b in batch])
        lmask = torch.zeros_like(mask)
        for r, (e, st) in enumerate(batch):
            lmask[r, st:len(e)] = 1
        logits = pm(input_ids=ids, attention_mask=mask).logits
        tgt_mask = lmask[:, 1:].bool()
        # first-token loss only when st>0 is handled by shift; for plain text the first token has no context (skipped)
        ce = F.cross_entropy(logits[:, :-1][tgt_mask].float(), ids[:, 1:][tgt_mask])
        loss, kl_v = ce, 0.0
        if replay is not None and args.kl_weight > 0:
            rb = rng.sample(replay, min(args.replay_bsz, len(replay)))
            rids, rmask = L.pad_right([r[0] for r in rb])
            rl = torch.zeros_like(rmask)
            for r, (e, st) in enumerate(rb):
                rl[r, st:len(e)] = 1
            rt = rl[:, 1:].bool()
            cur = pm(input_ids=rids, attention_mask=rmask).logits[:, :-1][rt].float()
            with torch.no_grad(), pm.disable_adapter():
                ref = pm(input_ids=rids, attention_mask=rmask).logits[:, :-1][rt].float()
            kl = F.kl_div(F.log_softmax(cur, -1), F.log_softmax(ref, -1), log_target=True, reduction="batchmean")
            loss = ce + args.kl_weight * kl
            kl_v = float(kl.detach())
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        if step % 10 == 0 or step == args.steps - 1:
            curve.append({"step": step, "ce": float(ce.detach()), "kl": kl_v, "lr": lr})
            if step % 50 == 0 or step == args.steps - 1:
                log(f"[train] step {step} ce {float(ce.detach()):.4f} kl {kl_v:.4f} lr {lr:.2e}")
    pm.eval()
    return curve


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["s0", "ic", "s1", "s2"])
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--out", required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--kl-weight", type=float, default=1.0)
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--gen-bs", type=int, default=8)
    args = ap.parse_args()
    if args.smoke:
        args.steps = min(args.steps, 6)
        args.bsz, args.replay_bsz, args.gen_bs = 4, 2, 4
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    logf = open(out / f"log_{args.arm}.txt", "a")

    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")
        logf.flush()

    t0 = time.time()
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    lm, tok = load_model(args, device, dtype)
    L = Lang(tok, args.smoke, device)
    world = facts_mod.build()
    tests = {"forward": world["forward"], "reverse": world["reverse"], "twohop": world["twohop"]}
    all_test_q = [t["q"] for k in ("forward", "reverse", "twohop") for t in world[k]]  # full test set, for the leak filter
    if args.smoke:  # CPU: keep it quick
        tests = {k: v[:8] for k, v in tests.items()}
        world = dict(world, facts=world["facts"][:8], teaching=world["teaching"][:8])
    result = {"arm": args.arm, "model": args.model, "smoke": args.smoke, "steps": args.steps, "bsz": args.bsz, "lr": args.lr,
              "rank": args.rank, "alpha": args.alpha, "kl_weight": args.kl_weight}
    model = lm
    if args.arm in ("s1", "s2"):
        paras, qas, replay = [], [], None
        if args.arm == "s2":
            paras, qas, stats, raw = dream(L, lm, world, all_test_q, args.gen_bs, args.smoke, log)
            result["dream_stats"], result["dream_raw_samples"] = stats, raw
            result["dream_kept_examples"] = {"paraphrases": paras[:20], "qa": qas[:20]}
            (out / "dreams.json").write_text(json.dumps({"paraphrases": paras, "qa": qas, "stats": stats}, indent=1))
            gp = generic_prompts()[:(6 if args.smoke else 200)]
            prompts = [L.render(None, g) for g in gp]
            resp = L.generate(lm, prompts, max_new=8 if args.smoke else 48, bs=args.gen_bs)
            replay = []
            for p, r in zip(prompts, resp):
                pi = L.ids(p)
                ri = L.ids(r) + [L.eos]
                replay.append((pi + ri, len(pi)))
            result["replay_n"] = len(replay)
        from peft import LoraConfig, get_peft_model
        pm = get_peft_model(lm, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        log(f"[lora] trainable {sum(p.numel() for p in pm.parameters() if p.requires_grad):,}")
        examples = build_examples(L, world, paras, qas)
        result["n_train_examples"] = len(examples)
        tt = time.time()
        result["loss_curve"] = train(L, pm, examples, args, replay, log)
        result["train_seconds"] = time.time() - tt
        model = pm
    model.eval()
    ctx = world["teaching"] if args.arm == "ic" else None
    for name, items in tests.items():
        result[name] = score_qa(L, model, items, ctx, 4 if ctx else args.gen_bs * 2)
        log(f"[eval] {name} acc {result[name]['acc']:.3f} (n={result[name]['n']})")
    try:
        result["arc_easy"] = score_arc(L, model, load_arc(args.smoke))
        log(f"[eval] arc_easy acc {result['arc_easy']['acc']:.3f} (n={result['arc_easy']['n']})")
    except Exception as e:  # datasets missing / offline
        result["arc_easy"] = {"error": repr(e)}
        log(f"[eval] ARC FAILED: {e!r}")
    result["wall_seconds"] = time.time() - t0
    (out / f"result_{args.arm}.json").write_text(json.dumps(result, indent=1))
    log(f"[done] {args.arm} wall {result['wall_seconds']:.0f}s -> {out}/result_{args.arm}.json")


if __name__ == "__main__":
    main()
