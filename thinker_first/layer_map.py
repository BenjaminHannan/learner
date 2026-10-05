"""Test 1 of the thinker-first design: skip / repeat each layer of frozen LFM2.5-1.2B, score round-6 bare 8-shot.
No training. 33 variants x 576 questions (FRESH-EN-R3 + NEW-KINDS-R5 + NEW-KINDS2-R6, source text and paraphrase).
Same prompt and scorer as reasoner_ptr/real/english/run_english.py --arm lm_fewshot (greedy, max 12 new tokens),
except: bf16 by default, and the shared 8-shot prefix is cached per variant, questions of equal tail length are batched.
Skip/repeat rebuild the layer list (copies share weights, own layer_idx) so the KV/conv caches stay consistent."""
import argparse, copy, json, re, sys, time, unicodedata
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

HERE = Path(__file__).parent
p = argparse.ArgumentParser()
p.add_argument("--device", default="mps")
p.add_argument("--dtype", default="bfloat16")
p.add_argument("--variants", default="all")  # e.g. "full,skip0,rep3"
p.add_argument("--limit", type=int, default=0)  # dry runs: questions per variant
p.add_argument("--out", default=str(HERE / "results"))
p.add_argument("--max-new", type=int, default=12)
p.add_argument("--lm", default="LiquidAI/LFM2.5-1.2B-Instruct")
p.add_argument("--revision", default="0f604ada3f766f9f257460c4c9f0b5d6f69d431b")
args = p.parse_args()
dev = args.device
kw = {} if Path(args.lm).is_dir() else {"revision": args.revision}
tok = AutoTokenizer.from_pretrained(args.lm, **kw)
lm = AutoModelForCausalLM.from_pretrained(args.lm, dtype=getattr(torch, args.dtype), **kw).to(dev).eval().requires_grad_(False)
EOS = lm.generation_config.eos_token_id
EOS = set(EOS if isinstance(EOS, list) else [EOS])
ORIG_LAYERS = list(lm.model.layers)
ORIG_TYPES = list(lm.config.layer_types)
N = len(ORIG_LAYERS)


def norm(s):
    s = unicodedata.normalize("NFC", s).lower().replace("’", "'").replace("‘", "'").strip()
    s = re.sub(r"\s+", " ", s); return re.sub(r"[.!?,;:]+$", "", s).strip()


def rows_of(path, panels):
    out = []
    for e in json.load(open(path))["examples"]:
        for panel, key in panels:
            for qi, q in enumerate(e["questions"]):
                out.append({"id": f"{e['id']}-{key}-q{qi}", "family": e["family"], "panel": panel, "type": q["type"],
                            "passage": e[key], "question": q["question"], "answer": q["canonical_answer"],
                            "accepted": [norm(a) for a in [q["canonical_answer"]] + q["accepted_answers"]]})
    return out


D = HERE / "data"
train = rows_of(D / "english_training_candidates_v3.json", [("train_source", "source_text"), ("train_paraphrase", "paraphrase")])
fams = {}
for r in train:
    if r["panel"] == "train_source": fams.setdefault(r["family"], []).append(r)
SHOTS = [v[0] for v in fams.values()] + [r for r in train if r["type"] == "yes_no" and r["panel"] == "train_source"][:2]
SETS = {"fresh": ("FRESH-EN-R3.json", [("fresh_source", "source_text"), ("fresh_paraphrase", "paraphrase")]),
        "r5": ("NEW-KINDS-R5.json", [("new_source", "source_text"), ("new_paraphrase", "paraphrase")]),
        "r6": ("NEW-KINDS2-R6.json", [("new2_source", "source_text"), ("new2_paraphrase", "paraphrase")])}
ROWS = []
for k, (f, panels) in SETS.items():
    for r in rows_of(D / f, panels): r["set"] = k; ROWS.append(r)
if args.limit: ROWS = ROWS[::max(1, len(ROWS) // args.limit)][:args.limit]


def prompt_ids(r):
    msgs = []
    for sh in SHOTS:
        msgs += [{"role": "user", "content": f"{sh['passage']}\n{sh['question']}\nAnswer with a short phrase only."},
                 {"role": "assistant", "content": sh["answer"]}]
    msgs += [{"role": "user", "content": f"{r['passage']}\n{r['question']}\nAnswer with a short phrase only."}]
    return tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)["input_ids"][0].tolist()


for r in ROWS: r["ids"] = prompt_ids(r)
L = min(len(r["ids"]) for r in ROWS)
for i in range(L):
    if any(r["ids"][i] != ROWS[0]["ids"][i] for r in ROWS): L = i; break
PREFIX = ROWS[0]["ids"][:L]
GROUPS = {}
for r in ROWS: GROUPS.setdefault(len(r["ids"]) - L, []).append(r)
print(f"questions {len(ROWS)} shots {len(SHOTS)} prefix {L} tokens, {len(GROUPS)} tail-length groups, dtype {args.dtype} dev {dev}", flush=True)


def clone_layer(layer, new_idx):
    c = copy.copy(layer); c._modules = dict(layer._modules)
    opn = "self_attn" if layer.is_attention_layer else "conv"
    op = copy.copy(getattr(layer, opn)); op._modules = dict(getattr(layer, opn)._modules); op.layer_idx = new_idx
    c._modules[opn] = op
    return c


def set_variant(order):
    """order = list of original layer indices, run in this order (a repeated index = the layer applied twice)."""
    lm.model.layers = torch.nn.ModuleList([clone_layer(ORIG_LAYERS[o], i) for i, o in enumerate(order)])
    lm.config.layer_types = [ORIG_TYPES[o] for o in order]
    lm.config.num_hidden_layers = len(order)
    lm.model.config = lm.config


def variants():
    v = {"full": list(range(N))}
    for i in range(N): v[f"skip{i}"] = [j for j in range(N) if j != i]
    for i in range(N): v[f"rep{i}"] = [j for j in range(N) for _ in range(2 if j == i else 1)]
    return v


def expand(cache, B):
    cb = copy.deepcopy(cache)
    for ly in cb.layers:
        for k, v in list(vars(ly).items()):
            if torch.is_tensor(v) and v.ndim >= 2 and v.numel(): setattr(ly, k, v.repeat_interleave(B, 0))
            elif isinstance(v, (list, dict)):
                for kk in (range(len(v)) if isinstance(v, list) else list(v)):
                    if torch.is_tensor(v[kk]) and v[kk].ndim >= 2 and v[kk].numel(): v[kk] = v[kk].repeat_interleave(B, 0)
    return cb


@torch.no_grad()
def run_variant():
    from transformers import DynamicCache
    pre = torch.tensor([PREFIX], device=dev)
    cache = DynamicCache(config=lm.config)
    lm(input_ids=pre, past_key_values=cache, use_cache=True)
    out = {}
    for tl, g in sorted(GROUPS.items()):
        for s in range(0, len(g), 24):
            c = g[s:s + 24]; B = len(c)
            cb = expand(cache, B)
            ids = torch.tensor([r["ids"][L:] for r in c], device=dev)
            gen = [[] for _ in range(B)]; done = [False] * B
            pos = L
            for _ in range(args.max_new):
                T = ids.shape[1]
                pid = torch.arange(pos, pos + T, device=dev)[None].expand(B, -1)
                lg = lm(input_ids=ids, past_key_values=cb, use_cache=True, position_ids=pid).logits[:, -1]
                pos += T
                nxt = lg.argmax(-1)
                for b in range(B):
                    if not done[b]:
                        if int(nxt[b]) in EOS: done[b] = True
                        else: gen[b].append(int(nxt[b]))
                if all(done): break
                ids = nxt[:, None]
            for r, gg in zip(c, gen): out[r["id"]] = tok.decode(gg, skip_special_tokens=True).strip()
    return out


def summarize(preds):
    res = {}
    for key, sel in [("pooled", lambda r: True)] + [(k, (lambda k: lambda r: r["set"] == k)(k)) for k in SETS] + [("unseen", lambda r: r["set"] != "fresh")]:
        rs = [r for r in ROWS if sel(r)]
        res[key] = round(100 * sum(norm(preds[r["id"]]) in r["accepted"] for r in rs) / max(1, len(rs)), 1)
    return res


def main():
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    allv = variants()
    names = list(allv) if args.variants == "all" else args.variants.split(",")
    for n in names:
        f = outdir / f"{n}.json"
        if f.exists(): print("have", n, flush=True); continue
        t = time.time(); set_variant(allv[n])
        preds = run_variant(); res = summarize(preds)
        f.write_text(json.dumps({"variant": n, "order": allv[n], "scores": res, "n": len(ROWS), "seconds": round(time.time() - t),
                                 "dtype": args.dtype, "preds": preds}))
        print(f"RESULT {n} {res} {time.time()-t:.0f}s", flush=True)


if __name__ == "__main__": main()
