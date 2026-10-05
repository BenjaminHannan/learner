"""Speed test: real recipe (round-8 flags) vs bare LFM2.5-1.2B. Fresh weights (speed does not depend on them).
Run from <repo>/pipeline/recipe_test:   python bench_tps.py <LFM2.5-1.2B snapshot dir> [large_batch]   (large_batch default: 256 on CUDA, 32 on Apple MPS / CPU)
Device is chosen automatically: CUDA, else Apple MPS, else CPU (override with env BENCH_DEVICE=cuda|mps|cpu).
Needs torch, transformers, huggingface-hub<1.0. Do not run while another job holds the GPU (GPU-BUSY marker).
Prints SYS/BARE lines and writes bench_tps_result.json. A batch that runs out of memory is skipped, not fatal."""
import os, sys, time, json, copy, random, statistics
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")  # Apple: let unsupported ops fall back to CPU
os.environ.setdefault("RT_ROUND", "2")  # gen_two_r3 asserts this
import torch as _t
DEV = os.environ.get("BENCH_DEVICE") or ("cuda" if _t.cuda.is_available() else "mps" if _t.backends.mps.is_available() else "cpu")
LARGE = int(sys.argv[2]) if len(sys.argv) > 2 else (256 if DEV == "cuda" else 32)
BARE_LARGE = min(64, LARGE)
print("device:", DEV, flush=True)
sys.argv = ["run_arm.py", "--device", DEV, "--seed", "0", "--copy", "--ctx", "--task", "two", "--long", "--frames", "tabv", "--lm", sys.argv[1]]
src = open("run_arm.py").read().rstrip()
assert src.endswith("main()")
g = {"__name__": "run_arm", "__file__": __import__("os").path.abspath("run_arm.py")}
exec(compile(src[:-len("main()")], "run_arm.py", "exec"), g)
torch, tok, lm, dev, emb = g["torch"], g["tok"], g["lm"], g["dev"], g["emb"]
import sol_spatial_poc_ordered_v2 as _ov2; _ov2.QUERY_CAP = 160
import gen_two_r3 as g3, gen_two_long
ntok = lambda t: len(tok.encode(t, add_special_tokens=False)) + 1
short = g3.build_eval(fits=lambda t: ntok(t) <= 49)
long_ = gen_two_long.build_long(ntok, used=set())
model = g["Model"](0).to(dev).eval()
BOS, POS = g["BOS"], g["POS"]
def sync():
    if DEV == "cuda": torch.cuda.synchronize()
    elif DEV == "mps": torch.mps.synchronize()
def oom(e): return isinstance(e, RuntimeError) and "out of memory" in str(e).lower()
def clear():
    if DEV == "cuda": torch.cuda.empty_cache()
    elif DEV == "mps": torch.mps.empty_cache()

@torch.no_grad()
def infer(rows):
    enc = [g["encode_row"](r) for r in rows]
    ids = torch.tensor([e[0] for e in enc], device=dev)
    h, loops, traces, latest = g["calc_forward"](model, ids, [e[1] for e in enc])
    B, n = ids.shape
    prefix = model.adapter.project_training(h, torch.ones_like(h, dtype=torch.bool), torch.ones(B, n, dtype=torch.bool, device=dev), (1, n))
    cv = torch.zeros(B, g["LMW"], device=dev)
    for b in range(B):
        if latest[b] is not None:
            cv[b] = emb.weight[latest[b]]
    inp = torch.cat([prefix.to(emb.weight.dtype), cv[:, None], emb(torch.full((B, 1), BOS, device=dev))], 1)
    return lm(inputs_embeds=inp).logits[:, POS].argmax(-1)

def bucket(rows):
    by = {}
    for r in rows:
        by.setdefault(len(g["encode_row"](r)[0]), []).append(r)
    return by

def timeit(fn, warm=3, iters=10):
    for _ in range(warm): fn()
    sync(); ts = []
    for _ in range(iters):
        t = time.perf_counter(); fn(); sync(); ts.append(time.perf_counter() - t)
    return statistics.median(ts)

out = {"gpu": torch.cuda.get_device_name(0) if DEV == "cuda" else __import__("platform").platform() + " " + DEV, "torch": torch.__version__, "system": [], "bare": []}
for label, pool in (("short", short), ("long", long_)):
    by = bucket(pool)
    k = max(by, key=lambda x: len(by[x]))  # most common length
    base = by[k]
    for B in (1, 16, 64, LARGE):
        rows = (base * (B // len(base) + 1))[:B]
        try:
            s = timeit(lambda: infer(rows))
        except RuntimeError as e:
            if not oom(e): raise
            print("SYS OOM", label, B, flush=True); clear(); continue
        r = {"set": label, "prompt_tokens_each": k, "batch": B, "sec_per_batch": s, "questions_per_s": B / s, "prompt_tok_per_s": B * k / s, "answer_tok_per_s": B / s}
        print("SYS", json.dumps(r), flush=True); out["system"].append(r)
    # bare LM prefill-only share (the contextual read inside the system)
    ids = torch.tensor([g["encode_row"](base[0])[0]], device=dev)
    s = timeit(lambda: lm(input_ids=ids))
    print("LMPASS1", label, k, s, flush=True)

ids1 = g["encode_row"](long_[0])[0]
for dtype_name, dt in (("fp32+tf32", None), ("bf16", torch.bfloat16)):
    m = lm if dt is None else copy.deepcopy(lm).to(dt)
    for label, prompt in (("short", short), ("long", long_)):
        k0 = max(bucket(prompt).items(), key=lambda kv: len(kv[1]))
        k, base = k0[0], k0[1]
        for B in (1, BARE_LARGE):
            rows = (base * (B // len(base) + 1))[:B]
            ids = torch.tensor([g["encode_row"](r)[0] for r in rows], device=dev)
            try:
              with torch.no_grad():
                pre = timeit(lambda: m(input_ids=ids), iters=5)
                N = 64
                gen = lambda: m.generate(input_ids=ids, attention_mask=torch.ones_like(ids), do_sample=False, max_new_tokens=N, min_new_tokens=N, pad_token_id=g["EOS"])
                tot = timeit(gen, warm=1, iters=3)
            except RuntimeError as e:
                if not oom(e): raise
                print("BARE OOM", dtype_name, label, B, flush=True); clear(); continue
            r = {"dtype": dtype_name, "set": label, "prompt_tokens_each": k, "batch": B, "prefill_tok_per_s": B * k / pre,
                 "decode_tok_per_s": B * N / max(tot - pre, 1e-6), "gen_total_s": tot, "decode_new_tokens": N}
            print("BARE", json.dumps(r), flush=True); out["bare"].append(r)
    if dt is not None: del m
print("BENCH-JSON " + json.dumps(out))
open("bench_tps_result.json", "w").write(json.dumps(out, indent=1))
