"""Sleep-1L: MLX (Apple Silicon) port of sleep1.py for LiquidAI/LFM2.5-24B-A2B-MLX-4bit (plan: backbone/PREREG-sleep1L.md).

Arms: s0 (base), ic (facts in context), s1 (plain LoRA on the 120 teaching sentences), s2 (dream -> verify -> LoRA + KL guard on
generic replay prompts), s2t (= s2 plus dreamed, verified two-hop questions; the ONLY difference from s2).
Same data (facts.py seed 0), tests (forward 120 / reverse 120 / two-hop 60 / ARC-Easy first 500 test, letter logit) and
hyper-parameters (LoRA rank 16, alpha 32, lr 2e-4 cosine, 300 steps, bsz 16, kl_weight 1.0, replay_bsz 8) as sleep1.py.
Does not import torch (uses mlx, mlx-lm, datasets; tokenizers come in through mlx-lm).

INSTALL (Mac: the separate Python 3.12 venv already used for mlx_lm; run from the repo root, ~/learner or wherever it is cloned)
  pip install -U mlx-lm datasets
RUN (everything overnight; arms run in the prereg order S0, S2, S2T, then IC, S1; results are written after each arm)
  mkdir -p ~/learner-ops/sleep1L/out
  python backbone/sleep/sleep1_mlx.py --arms s0,s2,s2t,ic,s1 --out ~/learner-ops/sleep1L/out 2>&1 | tee -a ~/learner-ops/sleep1L/out/run.log
  # model defaults to LiquidAI/LFM2.5-24B-A2B-MLX-4bit. If it is cut off, just rerun the same command: arms with an existing
  # result_<arm>.json are skipped (add --force to redo). Quick check first (a few minutes, tiny model, no big download):
  python backbone/sleep/sleep1_mlx.py --smoke --model LiquidAI/LFM2.5-350M --arms s0,s2,s2t,ic,s1 --out /tmp/sleep1L_smoke
ESTIMATED RUNTIME on an M1 Pro 32 GB (a guess, not measured; nothing here was run on the 24B model): s0 ~10 min (300 short
generations + ARC), dream ~30-60 min (120-240 prompts of ~1.5k tokens, ~300-500 new tokens each), verification ~15-40 min (prefix
cached), 300 LoRA steps ~1-2.5 h each, final eval ~10 min. S0+S2+S2T ~4-7 h, IC ~15 min, S1 ~1-2 h. S2T reuses S2's standard dreams
(saved in dreams_std.json) and only adds the two-hop dream, so it costs training plus ~40 min. If memory pressure is severe
(swapping, "[mem]" lines near the RAM limit) lower --micro-bsz to 2 and --gen-bs to 2, or add --grad-ckpt.
DISK GUARD: before each arm the free space of the home volume is checked; below 3 GB it logs "[disk]" and exits (code 3).
SEND BACK: every line starting with "[result]" (one per arm, plus "[marks]" at the end), the lines starting with "[probe]" and
"[dream]", and the paths of result_s0.json, result_s2.json, result_s2t.json, result_ic.json, result_s1.json, dreams_*.json,
marks.json in the out directory. If something fails, send the last 40 lines of run.log.

THINKING IS OFF EVERYWHERE. The LFM2.5 chat template has NO enable_thinking switch: add_generation_prompt always appends
"<|im_start|>assistant\\n<think>" and the model then reasons until it writes "</think>". Chosen switch (Lang.render): render the
template normally, and if the prompt ends with "<think>", append "</think>" so the assistant turn starts as an already-closed empty
think block, "<|im_start|>assistant\\n<think></think>". The same prefix is used in training prompts, so the LoRA learns to answer
right after the empty block. (Templates without a trailing <think>, e.g. LFM2.5-350M, are left untouched; enable_thinking=False is
also passed in case a template reads it.) Backstop: strip_think() removes any <think>...</think> (and an unclosed <think>...)
from every generation before scoring or parsing. A "[probe]" line at startup prints 3 raw generations so you can check that the
model answers directly; if it still writes reasoning, use --think-prefill (default "</think>"; e.g. --think-prefill $'\\n</think>\\n\\n').

KL GUARD. Before any LoRA exists, the frozen base model's log-probs on the replay answer tokens are precomputed: per position the
top-32 log-probs + indices, renormalised over those 32. Training uses KL(base_top32 || current) = sum_k p_base_k (log p_base_k -
log p_cur[idx_k]) with log p_cur from the full softmax of the LoRA model, averaged over replay answer tokens.
MEMORY. Each step of 16 sequences is 4 micro-steps of 4 (--micro-bsz) with gradient accumulation, each micro-step carrying 2 of the 8
replay sequences; sequences are capped at 512 tokens; LoRA goes on attention (q/k/v/out_proj), the short-conv (in_proj/out_proj) and
the 2 dense-MLP layers (gate/up/down); the MoE experts and the router get no adapter (adapter size ~ what sleep1.py trained).
"""
import argparse
import copy
import json
import math
import random
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten, tree_map, tree_unflatten

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import facts as facts_mod  # noqa: E402

SYS = "Answer with just the name."
K = 4   # paraphrases / QA per fact (as sleep1.py)
K2 = 4  # two-hop questions per focus fact (s2t)
MAXLEN = 512
TOPK = 32
ARM_ORDER = ["s0", "s2", "s2t", "ic", "s1"]
LORA_KEY_RE = re.compile(r"(self_attn\.(q_proj|k_proj|v_proj|o_proj|out_proj)|conv\.(in_proj|out_proj)|"
                         r"feed_forward\.(gate_proj|up_proj|down_proj|w1|w2|w3))$")
ARC_SMOKE = [{"question": "Which is a mammal?", "choices": ["trout", "dog", "eagle", "frog"], "answer": 1},
             {"question": "Water freezes at what Celsius temperature?", "choices": ["0", "50", "100", "-40"], "answer": 0},
             {"question": "What do plants need for photosynthesis?", "choices": ["sunlight", "sand", "plastic", "salt"], "answer": 0}]

# generic replay prompts: copied from sleep1.py (no torch import)
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


def clear_cache():
    try:
        mx.clear_cache()
    except AttributeError:
        mx.metal.clear_cache()


def peak_gb():
    try:
        return mx.get_peak_memory() / 1e9
    except AttributeError:
        return mx.metal.get_peak_memory() / 1e9


def strip_think(t):
    if "</think>" in t:
        t = t.split("</think>")[-1]
    t = re.sub(r"<think>.*", "", t, flags=re.S)
    # LFM2.5 writes narrow no-break spaces and non-breaking hyphens (found by the tricks thread); normalise before any matching
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[\u2010-\u2015\u2212]", "-", t)
    return re.sub(r"\s+", " ", t).strip()


# ------------------------------------------------------------------ text plumbing
class Lang:
    def __init__(self, tok, prefill):
        self.tok, self.prefill = tok, prefill
        self.eos = tok.eos_token_id

    def render(self, system, user):
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
        if getattr(self.tok, "chat_template", None):
            t = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        else:
            t = "".join(f"{m['role']}: {m['content']}\n" for m in msgs) + "assistant: "
        if t.rstrip().endswith("<think>"):  # LFM2.5: the template opens a think block; close it so the model answers directly
            t = t.rstrip() + self.prefill
        return t

    def ids(self, text):
        return list(self.tok.encode(text, add_special_tokens=False))

    def generate(self, model, prompts, max_new=20, bs=8, sample=False, temp=0.8, label=""):
        """Batched generation (mlx_lm.batch_generate); falls back to one-at-a-time stream_generate if that API is missing/fails."""
        from mlx_lm.sample_utils import make_sampler
        sampler = make_sampler(temp=temp, top_p=0.95) if sample else make_sampler(temp=0.0)
        outs = []
        chunk = 32
        t0 = time.time()
        for s in range(0, len(prompts), chunk):
            part = prompts[s:s + chunk]
            enc = [self.ids(p) for p in part]
            try:
                from mlx_lm.generate import batch_generate
                r = batch_generate(model, self.tok, enc, max_tokens=max_new, sampler=sampler, completion_batch_size=bs,
                                   prefill_batch_size=min(bs, 4), prefill_step_size=512)
                texts = list(r.texts)
            except Exception as e:  # older/newer mlx-lm: sequential fallback
                print(f"[gen] batch_generate failed ({e!r}); falling back to stream_generate", flush=True)
                texts = [self._stream(model, e_, max_new, sampler) for e_ in enc]
            outs += [strip_think(t) for t in texts]
            clear_cache()
            if label and len(prompts) > chunk:
                print(f"[gen] {label} {len(outs)}/{len(prompts)} {time.time() - t0:.0f}s", flush=True)
        return outs

    def _stream(self, model, ids, max_new, sampler, cache=None):
        from mlx_lm.generate import stream_generate
        kw = {"prompt_cache": cache} if cache is not None else {}
        return "".join(r.text for r in stream_generate(model, self.tok, ids, max_tokens=max_new + 1, sampler=sampler, **kw))

    def generate_ctx(self, model, prefix, suffixes, max_new=20):
        """Greedy answers for prompts that share a long prefix (the fact list): prefill the prefix once, copy the cache per query."""
        from mlx_lm.models.cache import make_prompt_cache
        from mlx_lm.sample_utils import make_sampler
        sampler = make_sampler(temp=0.0)
        pre = self.ids(prefix)
        cache = make_prompt_cache(model)
        for s in range(0, len(pre), 512):
            model(mx.array(pre[s:s + 512])[None], cache=cache)
            mx.eval([c.state for c in cache])
        outs, t0 = [], time.time()
        for i, sfx in enumerate(suffixes):
            outs.append(strip_think(self._stream(model, self.ids(sfx), max_new, sampler, cache=copy.deepcopy(cache))))
            if i % 100 == 99:
                clear_cache()
                print(f"[gen] ctx {i + 1}/{len(suffixes)} {time.time() - t0:.0f}s", flush=True)
        return outs

    def pad_right(self, seqs):
        n = max(map(len, seqs))
        ids = [list(e) + [0] * (n - len(e)) for e in seqs]
        mask = [[1] * len(e) + [0] * (n - len(e)) for e in seqs]
        return mx.array(ids, dtype=mx.int32), mx.array(mask, dtype=mx.int32)


CTX_MARK = "\n\nQuestion: "


def q_prompt(L, q, context=None):
    if context:
        return L.render(SYS, "Facts:\n" + "\n".join(f"- {t}" for t in context) + f"{CTX_MARK}{q}")
    return L.render(SYS, q)


def answer_qs(L, model, qs, context, bs, max_new=20, label=""):
    """Greedy answers to questions, with the facts in context (prefix-cached) or without."""
    if not qs:
        return []
    if not context:
        return L.generate(model, [q_prompt(L, q) for q in qs], max_new=max_new, bs=bs, label=label)
    fulls = [q_prompt(L, q, context) for q in qs]
    cut = fulls[0].index(CTX_MARK) + 2
    prefix = fulls[0][:cut]
    if all(f.startswith(prefix) for f in fulls):
        try:
            return L.generate_ctx(model, prefix, [f[cut:] for f in fulls], max_new=max_new)
        except Exception as e:
            print(f"[gen] prefix-cache path failed ({e!r}); using plain batches", flush=True)
    return L.generate(model, fulls, max_new=max_new, bs=max(1, bs // 2), label=label)


# ------------------------------------------------------------------ scoring
def score_qa(L, model, items, context, bs):
    ans = answer_qs(L, model, [it["q"] for it in items], context, bs, label="eval")
    ok = [it["target"].lower() in a.lower() for it, a in zip(items, ans)]
    return {"acc": sum(ok) / len(ok), "n": len(ok),
            "examples": [{"q": it["q"], "target": it["target"], "answer": a, "correct": c} for it, a, c in list(zip(items, ans, ok))[:20]]}


def score_arc(L, model, rows, bs=4):
    letters = "ABCDE"
    lid = [L.ids(c)[0] for c in letters]
    correct, ex = 0, []
    for s in range(0, len(rows), bs):
        chunk = rows[s:s + bs]
        seqs = []
        for r in chunk:
            u = r["question"] + "\n" + "\n".join(f"{letters[i]}. {c}" for i, c in enumerate(r["choices"])) + "\nAnswer with the letter only."
            seqs.append(L.ids(L.render(None, u))[-MAXLEN:])
        ids, _ = L.pad_right(seqs)
        logits = model(ids)
        for r, row in enumerate(chunk):
            sc = logits[r, len(seqs[r]) - 1].astype(mx.float32)[mx.array(lid[:len(row["choices"])])]
            pred = int(mx.argmax(sc).item())
            correct += pred == row["answer"]
            if len(ex) < 20:
                ex.append({"q": row["question"], "pred": letters[pred], "gold": letters[row["answer"]]})
        if s % 100 == 0:
            clear_cache()
    return {"acc": correct / len(rows), "n": len(rows), "examples": ex}


def load_arc(smoke):
    if smoke:
        return ARC_SMOKE
    try:
        from datasets import load_dataset
        ds = list(load_dataset("allenai/ai2_arc", "ARC-Easy", split="test"))[:500]
    except Exception as e:  # datasets missing / script-dataset trouble: fetch the parquet directly
        print(f"[arc] datasets failed ({e!r}); downloading parquet", flush=True)
        from huggingface_hub import hf_hub_download
        import pyarrow.parquet as pq
        p = hf_hub_download("allenai/ai2_arc", "ARC-Easy/test-00000-of-00001.parquet", repo_type="dataset")
        ds = pq.read_table(p).to_pylist()[:500]
    rows = []
    for r in ds:
        labels = list(r["choices"]["label"])
        rows.append({"question": r["question"], "choices": list(r["choices"]["text"]), "answer": labels.index(r["answerKey"])})
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


def twohop_prompt(L, world, fact):
    ctx = "\n".join(f"- {t}" for t in world["teaching"])
    u = (f"Here are facts you learned today:\n{ctx}\n\nFocus on this fact: \"{fact['text']}\"\n\n"
         f"Write {K2} two-hop questions that chain this fact with one other fact from the notes: the answer to the first step is "
         f"needed to look up the second step. Name only the starting entity in the question; never name the middle entity. Each "
         f"answer must be a single name from the notes. Reply with only JSON of the form "
         f"{{\"twohop\": [{{\"q\": \"...\", \"a\": \"...\"}}]}}")
    return L.render("You are a careful assistant that studies facts.", u)


def parse_dream(txt, qa_key="qa"):
    paras, qas = [], []
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            paras = [p for p in d.get("paraphrases", []) if isinstance(p, str)]
            qas = [(x.get("q"), x.get("a")) for x in d.get(qa_key, d.get("qa", [])) if isinstance(x, dict) and isinstance(x.get("q"), str) and isinstance(x.get("a"), str)]
            return paras, qas
        except Exception:
            pass
    for line in txt.splitlines():  # fallback: "Q: ... A: ..." lines
        line = line.strip().lstrip("-*0123456789. ").strip()
        mm = re.match(r"(?:Q:|Question:)\s*(.+?)\s*(?:\||A:|Answer:)\s*(.+)$", line)
        if mm:
            qas.append((mm.group(1), mm.group(2)))
    return paras, qas


def chains_of(world):
    """True two-hop chains computed from the fact list (not from the test items): dicts x (asked entity), mid, target, facts."""
    by = {(f["rel"], f["a"]): f for f in world["facts"]}
    out = []
    for f in world["facts"]:
        if f["rel"] == "mentor_of":      # mentor f.a of student f.b; mentor lives in C  -> ask about student
            g, x, mid = by[("lives_in", f["a"])], f["b"], f["a"]
        elif f["rel"] == "sibling":      # f.a and f.b siblings; f.b works at C           -> ask about f.a
            g, x, mid = by[("works_at", f["b"])], f["a"], f["b"]
        elif f["rel"] == "owns":         # owner f.a owns boat f.b; owner born in T       -> ask about the boat
            g, x, mid = by[("born_in", f["a"])], f["b"], f["a"]
        else:
            continue
        out.append({"x": x, "mid": mid, "target": g["b"], "facts": [f["id"], g["id"]]})
    return out


def dream(L, model, world, tests, bs, smoke, log):  # standard dream, identical to sleep1.py (tests = all test questions, leak filter)
    facts = world["facts"]
    raw = L.generate(model, [dream_prompt(L, world, f) for f in facts], max_new=500 if not smoke else 40, bs=bs, sample=True, temp=0.8, label="dream")
    leak = {facts_mod.norm(t) for t in tests}
    stats = {"facts": len(facts), "parse_fail": 0, "paraphrases_gen": 0, "paraphrases_kept": 0, "qa_gen": 0, "qa_kept": 0,
             "dropped_test_leak": 0, "dropped_missing_entities": 0, "dropped_bad_answer": 0, "dropped_unverified": 0, "dropped_dup": 0}
    cand_p, cand_q = [], []
    for f, txt in zip(facts, raw):
        paras, qas = parse_dream(txt)
        if smoke and not paras and not qas:  # tiny model emits noise; fabricate so the pipeline is exercised
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
    ver = answer_qs(L, model, [q for _, q, _ in cand_q], world["teaching"], bs, label="verify")
    kept_q, seen = [], set()
    for (fid, q, ent), v in zip(cand_q, ver):
        if ent.lower() not in v.lower() and not smoke:  # smoke: tiny model never verifies; keep all to exercise the path
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


def dream_twohop(L, model, world, chains, tests, bs, smoke, log):
    """s2t extra: dream two-hop questions per focus fact; keep those matching exactly one TRUE chain, not leaking a test question,
    and reproduced by the model with all facts in context."""
    facts = world["facts"]
    raw = L.generate(model, [twohop_prompt(L, world, f) for f in facts], max_new=350 if not smoke else 40, bs=bs, sample=True, temp=0.8, label="dream2")
    leak = {facts_mod.norm(t) for t in tests}
    st = {"focus_facts": len(facts), "twohop_parse_fail": 0, "twohop_gen": 0, "twohop_kept": 0, "twohop_dropped_test_leak": 0,
          "twohop_dropped_no_true_chain": 0, "twohop_dropped_unverified": 0, "twohop_dropped_dup": 0, "twohop_chains_covered": 0,
          "twohop_chains_total": len(chains)}
    cand = []
    for f, txt in zip(facts, raw):
        _, qas = parse_dream(txt, "twohop")
        if smoke:  # tiny model emits noise; add one fabricated true-chain question so the path is exercised
            c = next((c for c in chains if f["id"] in c["facts"]), chains[0])
            qas = list(qas) + [(f"What is two steps from {c['x']}?", c["target"])]
        if not qas:
            st["twohop_parse_fail"] += 1
        for q, a in qas[:K2]:
            st["twohop_gen"] += 1
            nq = facts_mod.norm(q)
            if any(l in nq or nq in l for l in leak):
                st["twohop_dropped_test_leak"] += 1
                continue
            m = [c for c in chains if c["x"].lower() in q.lower() and c["target"].lower() in a.lower()
                 and c["mid"].lower() not in q.lower() and c["target"].lower() not in q.lower() and c["mid"].lower() not in a.lower()]
            if len(m) != 1:
                st["twohop_dropped_no_true_chain"] += 1
            else:
                cand.append((m[0], q.strip()))
    ver = answer_qs(L, model, [q for _, q in cand], world["teaching"], bs, label="verify2")
    kept, seen = [], set()
    for (c, q), v in zip(cand, ver):
        if c["target"].lower() not in v.lower() and not smoke:
            st["twohop_dropped_unverified"] += 1
        elif (q.lower(), c["target"]) in seen:
            st["twohop_dropped_dup"] += 1
        else:
            seen.add((q.lower(), c["target"]))
            kept.append({"facts": c["facts"], "q": q, "a": c["target"]})
    st["twohop_kept"] = len(kept)
    st["twohop_chains_covered"] = len({tuple(k["facts"]) for k in kept})
    log(f"[dream2] {st}")
    return kept, st, raw[:5]


# ------------------------------------------------------------------ LoRA
def lora_keys(model):
    keys = set()
    for l in model.layers:
        for k, m in l.named_modules():
            if LORA_KEY_RE.search(k) and isinstance(m, (nn.Linear, nn.QuantizedLinear)):
                keys.add(k)
    return keys


def add_lora(model, args):
    from mlx_lm.tuner.utils import linear_to_lora_layers
    model.freeze()
    cfg = {"rank": args.rank, "scale": args.alpha / args.rank, "dropout": 0.0, "keys": lora_keys(model)}
    linear_to_lora_layers(model, len(model.layers), cfg)
    n = sum(v.size for _, v in tree_flatten(model.trainable_parameters()))
    return n


def strip_lora(model):
    from mlx_lm.tuner.lora import LoRALinear
    for l in model.layers:
        sw = [(k, m.linear) for k, m in l.named_modules() if isinstance(m, LoRALinear)]
        if sw:
            l.update_modules(tree_unflatten(sw))
    model.freeze()


# ------------------------------------------------------------------ KL guard precompute (frozen base, before LoRA)
def base_topk(L, model, replay, log):
    out = []
    for i, (ids, st) in enumerate(replay):
        lg = model(mx.array(ids, dtype=mx.int32)[None])[0, st - 1:len(ids) - 1].astype(mx.float32)  # positions predicting the answer tokens
        lp = lg - mx.logsumexp(lg, axis=-1, keepdims=True)
        idx = mx.argsort(-lp, axis=-1)[:, :TOPK]
        v = mx.take_along_axis(lp, idx, axis=-1)
        v = v - mx.logsumexp(v, axis=-1, keepdims=True)  # renormalise over the kept top-k
        mx.eval(idx, v)
        out.append((idx.astype(mx.int32), v))
        if i % 50 == 49:
            clear_cache()
    log(f"[kl] base top-{TOPK} log-probs for {len(replay)} replay examples")
    return out


# ------------------------------------------------------------------ training
def build_examples(L, world, paras, qas):
    ex = []  # (ids, loss_start): loss on tokens from `loss_start`
    for t in world["teaching"] + [p["text"] for p in paras]:
        ex.append(((L.ids(t) + [L.eos])[:MAXLEN], 0))
    for x in qas:
        p = L.ids(L.render(SYS, x["q"]))
        a = L.ids(x["a"]) + [L.eos]
        ex.append(((p + a)[:MAXLEN], len(p)))
    return ex


def train(L, model, examples, args, replay, topk, log):
    opt = optim.AdamW(learning_rate=args.lr, weight_decay=0.0)
    rng = random.Random(args.seed)
    use_kl = replay is not None and args.kl_weight > 0
    nacc = max(1, args.bsz // args.micro_bsz)
    rmicro = max(1, math.ceil(args.replay_bsz / nacc))

    def loss_fn(m, ids, lmask, rids, rmask, ridx, rlp, n_ce, n_kl):
        logits = m(ids)[:, :-1].astype(mx.float32)
        tgt = ids[:, 1:]
        tok_lp = mx.take_along_axis(logits, tgt[..., None], axis=-1).squeeze(-1) - mx.logsumexp(logits, axis=-1)
        ce = -(tok_lp * lmask[:, 1:]).sum() / n_ce
        kl = mx.array(0.0)
        if rids is not None:
            cl = m(rids)[:, :-1].astype(mx.float32)
            cur = mx.take_along_axis(cl, ridx, axis=-1) - mx.logsumexp(cl, axis=-1, keepdims=True)
            per = (mx.exp(rlp) * (rlp - cur)).sum(-1)
            kl = (per * rmask).sum() / n_kl
        return ce + args.kl_weight * kl, (ce, kl)

    vg = nn.value_and_grad(model, loss_fn)
    pool, curve = [], []
    model.train()
    t0 = time.time()
    for step in range(args.steps):
        lr = args.lr * 0.5 * (1 + math.cos(math.pi * step / args.steps))
        opt.learning_rate = lr
        batch = []
        while len(batch) < args.bsz:
            if not pool:
                pool = list(range(len(examples)))
                rng.shuffle(pool)
            batch.append(examples[pool.pop()])
        rb = rng.sample(range(len(replay)), min(args.replay_bsz, len(replay))) if use_kl else []
        n_ce = float(sum(len(e) - max(st, 1) for e, st in batch))
        n_kl = float(sum(len(replay[j][0]) - replay[j][1] for j in rb)) if use_kl else 1.0
        grads, ce_t, kl_t = None, 0.0, 0.0
        for a in range(nacc):
            mb = batch[a * args.micro_bsz:(a + 1) * args.micro_bsz]
            if not mb:
                continue
            ids, mask = L.pad_right([b[0] for b in mb])
            lm = mx.array([[1.0 if (st <= j < len(e) and j >= 1) else 0.0 for j in range(ids.shape[1])] for e, st in mb])
            rids = rmask = ridx = rlp = None
            rs = rb[a * rmicro:(a + 1) * rmicro] if use_kl else []
            if rs:
                rids, _ = L.pad_right([replay[j][0] for j in rs])
                T = rids.shape[1] - 1
                ri, rl, rm = [], [], []
                for j in rs:
                    e, st = replay[j][0], replay[j][1]
                    ix, lp = topk[j]
                    n = ix.shape[0]  # rows are positions st-1 .. len-2
                    padn = T - (st - 1) - n
                    ri.append(mx.concatenate([mx.zeros((st - 1, TOPK), dtype=mx.int32), ix, mx.zeros((padn, TOPK), dtype=mx.int32)]))
                    rl.append(mx.concatenate([mx.zeros((st - 1, TOPK)), lp, mx.zeros((padn, TOPK))]))
                    rm.append([1.0 if st - 1 <= p < st - 1 + n else 0.0 for p in range(T)])
                ridx, rlp, rmask = mx.stack(ri), mx.stack(rl), mx.array(rm)
            (loss, (ce, kl)), g = vg(model, ids, lm, rids, rmask, ridx, rlp, n_ce, n_kl)
            grads = g if grads is None else tree_map(lambda x, y: x + y, grads, g)
            mx.eval(grads, ce, kl)
            ce_t += float(ce.item())
            kl_t += float(kl.item())
        grads, _ = optim.clip_grad_norm(grads, 1.0)
        opt.update(model, grads)
        mx.eval(model.parameters(), opt.state)
        if step % 10 == 0 or step == args.steps - 1:
            curve.append({"step": step, "ce": ce_t, "kl": kl_t, "lr": lr})
            if step % 25 == 0 or step == args.steps - 1:
                log(f"[train] step {step} ce {ce_t:.4f} kl {kl_t:.4f} lr {lr:.2e} t {time.time() - t0:.0f}s [mem] peak {peak_gb():.1f} GB")
        if step % 20 == 0:
            clear_cache()
    model.eval()
    return curve


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="s0,s2,s2t,ic,s1", help="comma list from s0,s2,s2t,ic,s1 (run in prereg order)")
    ap.add_argument("--model", default="LiquidAI/LFM2.5-24B-A2B-MLX-4bit")
    ap.add_argument("--out", default=str(Path.home() / "learner-ops/sleep1L/out"))
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--force", action="store_true", help="redo arms that already have a result file")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--micro-bsz", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--kl-weight", type=float, default=1.0)
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--gen-bs", type=int, default=4)
    ap.add_argument("--think-prefill", default="</think>")
    ap.add_argument("--grad-ckpt", action="store_true", help="gradient checkpointing per layer (less memory, ~30%% slower)")
    ap.add_argument("--min-free-gb", type=float, default=3.0)
    args = ap.parse_args()
    if args.smoke:
        args.steps = min(args.steps, 6)
        args.bsz, args.micro_bsz, args.replay_bsz, args.gen_bs = 4, 2, 2, 2
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    bad = [a for a in arms if a not in ARM_ORDER]
    if bad:
        sys.exit(f"unknown arms {bad}; choose from {ARM_ORDER}")
    arms = [a for a in ARM_ORDER if a in arms]
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    logf = open(out / "log.txt", "a")

    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")
        logf.flush()

    from mlx_lm import load
    try:
        mx.set_cache_limit(1 << 30)  # keep the MLX buffer cache small: RAM is tight
    except Exception:
        pass
    mx.random.seed(args.seed)
    log(f"[start] arms {arms} model {args.model} smoke {args.smoke} out {out}")
    t_load = time.time()
    model, tok = load(args.model)
    model.eval()
    model.freeze()
    if args.grad_ckpt:
        from mlx_lm.tuner.trainer import grad_checkpoint
        grad_checkpoint(model.layers[0])
    L = Lang(tok, args.think_prefill)
    log(f"[load] {time.time() - t_load:.0f}s peak {peak_gb():.1f} GB")
    world = facts_mod.build()
    tests = {"forward": world["forward"], "reverse": world["reverse"], "twohop": world["twohop"]}
    all_test_q = [t["q"] for k in ("forward", "reverse", "twohop") for t in world[k]]  # full test set, for the leak filter
    chains = chains_of(world)
    if args.smoke:
        tests = {k: v[:8] for k, v in tests.items()}
        world = dict(world, facts=world["facts"][:8], teaching=world["teaching"][:8])
    # probe: confirm thinking is off
    pr = L.generate(model, [L.render(SYS, q) for q in ("What is the capital of France?", "Who wrote Romeo and Juliet?")], max_new=24, bs=2)
    log(f"[probe] prompt tail {L.render(SYS, 'Q')[-60:]!r}")
    for p in pr:
        log(f"[probe] stripped answer {p!r}")
    arc_rows = None
    cache = {}  # shared between arms: standard dream, replay set and base top-k
    for arm in arms:
        rf = out / f"result_{arm}.json"
        if rf.exists() and not args.force:
            log(f"[skip] {arm}: {rf} exists")
            continue
        free = shutil.disk_usage(Path.home()).free / 1e9
        if free < args.min_free_gb:
            log(f"[disk] only {free:.1f} GB free (< {args.min_free_gb}); stopping before arm {arm}")
            sys.exit(3)
        t0 = time.time()
        mx.random.seed(args.seed)
        result = {"arm": arm, "model": args.model, "smoke": args.smoke, "steps": args.steps, "bsz": args.bsz, "lr": args.lr,
                  "rank": args.rank, "alpha": args.alpha, "kl_weight": args.kl_weight, "think_prefill": args.think_prefill}
        log(f"[arm] {arm} start")
        if arm in ("s1", "s2", "s2t"):
            paras, qas, replay, topk = [], [], None, None
            if arm in ("s2", "s2t"):
                if "std" not in cache:
                    sf = out / "dreams_std.json"
                    if sf.exists() and not args.force and json.loads(sf.read_text()).get("model") == args.model:
                        d = json.loads(sf.read_text())
                        cache["std"] = (d["paraphrases"], d["qa"], d["stats"], d.get("raw", []))
                        log(f"[dream] reusing {sf}")
                    else:
                        p_, q_, s_, r_ = dream(L, model, world, all_test_q, args.gen_bs, args.smoke, log)
                        cache["std"] = (p_, q_, s_, r_)
                        sf.write_text(json.dumps({"model": args.model, "paraphrases": p_, "qa": q_, "stats": s_, "raw": r_}, indent=1))
                paras, qas, stats, raw = cache["std"]
                stats = dict(stats)
                result["dream_stats"], result["dream_raw_samples"] = stats, raw
                if arm == "s2t":
                    th, st2, raw2 = dream_twohop(L, model, world, chains, all_test_q, args.gen_bs, args.smoke, log)
                    stats.update(st2)
                    result["dream_raw_samples_twohop"] = raw2
                    result["dream_kept_examples"] = {"paraphrases": paras[:20], "qa": qas[:20], "twohop": th[:20]}
                    qas = qas + [{"fact": x["facts"], "q": x["q"], "a": x["a"]} for x in th]
                    (out / "dreams_s2t.json").write_text(json.dumps({"paraphrases": paras, "qa": qas, "twohop": th, "stats": stats}, indent=1))
                else:
                    result["dream_kept_examples"] = {"paraphrases": paras[:20], "qa": qas[:20]}
                    (out / "dreams_s2.json").write_text(json.dumps({"paraphrases": paras, "qa": qas, "stats": stats}, indent=1))
                if "replay" not in cache:
                    gp = generic_prompts()[:(6 if args.smoke else 200)]
                    prompts = [L.render(None, g) for g in gp]
                    resp = L.generate(model, prompts, max_new=8 if args.smoke else 48, bs=args.gen_bs, label="replay")
                    rep = []
                    for p, r in zip(prompts, resp):
                        pi = L.ids(p)
                        ri = L.ids(r) + [L.eos]
                        rep.append(((pi + ri)[:MAXLEN], len(pi)))
                    cache["replay"] = rep
                    cache["topk"] = base_topk(L, model, rep, log)  # frozen base, before LoRA exists
                replay, topk = cache["replay"], cache["topk"]
                result["replay_n"] = len(replay)
            n = add_lora(model, args)
            log(f"[lora] trainable {n:,}")
            examples = build_examples(L, world, paras, qas)
            result["n_train_examples"] = len(examples)
            tt = time.time()
            result["loss_curve"] = train(L, model, examples, args, replay, topk, log)
            result["train_seconds"] = time.time() - tt
        model.eval()
        ctx = world["teaching"] if arm == "ic" else None
        for name, items in tests.items():
            result[name] = score_qa(L, model, items, ctx, args.gen_bs * 2)
            log(f"[eval] {name} acc {result[name]['acc']:.3f} (n={result[name]['n']})")
        if arm in ("s1", "s2", "s2t"):  # addendum 2: does the slept model still use notes in context? (Sleep-B saw it get worse)
            for name, items in tests.items():
                r = score_qa(L, model, items, world["teaching"], args.gen_bs * 2)
                result[f"{name}_with_notes"] = r
                log(f"[eval] {name}_with_notes acc {r['acc']:.3f} (n={r['n']})")
        try:
            if arc_rows is None:
                arc_rows = load_arc(args.smoke)
            result["arc_easy"] = score_arc(L, model, arc_rows)
            log(f"[eval] arc_easy acc {result['arc_easy']['acc']:.3f} (n={result['arc_easy']['n']})")
        except Exception as e:
            result["arc_easy"] = {"error": repr(e)}
            log(f"[eval] ARC FAILED: {e!r}")
        result["wall_seconds"] = time.time() - t0
        result["peak_gb"] = peak_gb()
        rf.write_text(json.dumps(result, indent=1))
        a = result["arc_easy"].get("acc")
        log(f"[result] arm={arm} forward={result['forward']['acc']:.3f} reverse={result['reverse']['acc']:.3f} "
            f"twohop={result['twohop']['acc']:.3f} arc={a if a is None else round(a, 3)} wall={result['wall_seconds']:.0f}s -> {rf}")
        if arm in ("s1", "s2", "s2t"):
            strip_lora(model)  # back to the frozen base for the next arm
            clear_cache()
    marks(out, log)


def marks(out, log):
    R = {}
    for a in ARM_ORDER:
        f = out / f"result_{a}.json"
        if f.exists():
            R[a] = json.loads(f.read_text())
    g = lambda a, k: R[a][k]["acc"] * 100 if a in R and "acc" in R[a].get(k, {}) else None
    m = {}
    if "s2" in R:
        m["M1"] = (g("s2", "forward") >= 70) and (g("s1", "forward") is None or g("s2", "forward") >= g("s1", "forward") + 15) if "s1" in R else "need s1"
        m["M2"] = g("s2", "reverse") >= 40
        if "s0" in R:
            m["M4"] = g("s2", "arc_easy") is not None and g("s0", "arc_easy") is not None and g("s2", "arc_easy") >= g("s0", "arc_easy") - 2
    if "s2" in R and "s2t" in R:
        m["M5"] = (g("s2t", "twohop") >= g("s2", "twohop") + 15) and (g("s2t", "forward") >= g("s2", "forward") - 5)
    if m:
        (out / "marks.json").write_text(json.dumps(m, indent=1))
        log(f"[marks] {m}")


if __name__ == "__main__":
    main()
