"""GPU bench for the lead (one box, ~15-25 min on an RTX PRO 6000): sleep-night generation phases, original path vs fastgen variants -> ONE JSON.
  python speed/dreamgen/gpu_bench.py --model Qwen/Qwen3.6-35B-A3B --out speed/dreamgen/gpu_bench.json [--bs 32] [--n 96] [--tiny-cpu]
Phases mimic Brain: tag (greedy, max_new 160, ~220 tok prompts), dream (sampled T0.8 p0.95, max_new 400, ~450 tok), verify (greedy, max_new 20, ~420 tok,
~6 questions per shared diary context, 10% duplicate prompts), rem (sampled, 40), probe (generate_p, 20, ~60 tok). Prompts are synthetic fact diaries, so reply
lengths come from the real model (no forced full length). Variants: base | compact (seg 8) | compact+pad64 | compact+seg16. Per phase/variant: seconds, new tokens,
tok/s, model row-steps, and for greedy phases the share of replies equal to base (bf16 batch-size noise can flip a few near-ties; >= 0.97 expected).
Also 'shape_probe': prefill-only (max_new 1) repeated at one shape then at fresh shapes: a large first-call-per-shape gap = the per-shape warm-up (use pad_multiple).
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "backbone" / "sleep" / "brain", ROOT / "backbone" / "sleep", ROOT / "backbone", Path(__file__).resolve().parent):
    sys.path.insert(0, str(p))
import fastgen  # noqa: E402
import sleep1  # noqa: E402
import sleepb  # noqa: E402

NAMES = "Zelmir Quarry Hollis Brannock Tavish Oriel Fenwick Marlow Pellam Ostrand Kestrel Dunmore Ashby Corvin Lisle Yarrow Thorne Wick".split()
THINGS = "kitten saddle ocean garden button paper letter empire river morning feather winter dragon copper cellar blanket harvest orchard bridge".split()


def diary(rng, words):  # ~words words of chat-diary lines that link names
    out = []
    while sum(map(len, (o.split() for o in out))) < words:
        a, b = rng.sample(NAMES, 2)
        out.append(f"Day {rng.randint(1, 7)}: {a} told me that {b} keeps a {rng.choice(THINGS)} at {rng.choice(NAMES)}'s place, and I think {a} lives near the {rng.choice(THINGS)}.")
    return "\n".join(out)


def prompts_for(L, phase, n, rng):
    R = L.render
    if phase == "tag":
        return [R(sleep1.SYS, "List the facts that link two named things, one per line, as JSON.\n" + diary(rng, 150)) for _ in range(n)]
    if phase == "dream":
        return [R(sleep1.SYS, "Messages:\n" + diary(rng, 300) + "\n\nWrite 4 numbered paraphrases and 4 numbered Question/Answer pairs about " + f"{rng.choice(NAMES)} and {rng.choice(NAMES)}.") for _ in range(n)]
    if phase == "verify":
        out = []
        while len(out) < n:
            ctx = diary(rng, 280)
            out += [R(sleep1.SYS, f"Messages:\n{ctx}\n\nQuestion: Where does {rng.choice(NAMES)} keep the {rng.choice(THINGS)}?") for _ in range(6)]
        out = out[:n]
        return out[:n - n // 10] + out[:n // 10]  # 10% duplicates
    if phase == "rem":
        return [R(sleep1.SYS, f"{diary(rng, 150)}\nWrite one short dream linking {rng.choice(NAMES)} and {rng.choice(NAMES)}.") for _ in range(n)]
    return [R(sleep1.SYS, f"Where does {rng.choice(NAMES)} live?") for _ in range(n)]  # probe


PHASES = {"tag": dict(max_new=160, sample=False), "dream": dict(max_new=400, sample=True), "verify": dict(max_new=20, sample=False),
          "rem": dict(max_new=40, sample=True), "probe": dict(max_new=20, sample=False, p=True)}
VARIANTS = {"base": None, "compact": dict(compact=True, seg=8, dedupe=True, pad_multiple=1), "compact_pad64": dict(compact=True, seg=8, dedupe=True, pad_multiple=64),
            "compact_seg16": dict(compact=True, seg=16, dedupe=True, pad_multiple=1)}


class Count:  # wraps the model: counts row-steps and tokens
    def __init__(s, m): s.m, s.config, s.rows, s.calls = m, m.config, 0, 0

    def generate(s, **kw):
        out = s.m.generate(**kw)
        o = out.sequences if hasattr(out, "sequences") else out
        s.rows += kw["input_ids"].shape[0] * (o.shape[1] - kw["input_ids"].shape[1])
        s.calls += 1
        return out

    def __getattr__(s, k): return getattr(s.m, k)


def sync(dev):
    if dev.type == "cuda":
        torch.cuda.synchronize()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.6-35B-A3B")
    ap.add_argument("--out", default="speed/dreamgen/gpu_bench.json")
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--n", type=int, default=96, help="prompts per phase")
    ap.add_argument("--tiny-cpu", action="store_true", help="smoke the script itself on a tiny random model")
    ap.add_argument("--try-static", action="store_true", help="also time base-path generation with HF cache_implementation='static' (auto torch.compile); may fail on MoE: recorded, not fatal")
    ap.add_argument("--phases", default="tag,dream,verify,rem,probe")
    a = ap.parse_args()
    dev = torch.device("cpu" if a.tiny_cpu else "cuda")
    import train
    ns = argparse.Namespace(model=a.model, revision=None, smoke=a.tiny_cpu, seed=0)
    lm, tok = train.load_model(ns, dev, torch.float32 if a.tiny_cpu else torch.bfloat16)
    lm.eval()
    L = sleep1.Lang(tok, a.tiny_cpu, dev)
    res = {"model": a.model, "bs": a.bs, "n": a.n, "torch": torch.__version__, "gpu": torch.cuda.get_device_name(0) if dev.type == "cuda" else "cpu", "phases": {}}
    rng = random.Random(0)
    P = {ph: prompts_for(L, ph, a.n, rng) for ph in a.phases.split(",")}
    new_max = {"tag": 160, "dream": 400, "verify": 20, "rem": 40, "probe": 20}
    # shape probe (prefill only): same shape x3, then 3 fresh lengths
    sp = []
    base_ids = L.ids(P["verify"][0] if "verify" in P else P[next(iter(P))][0])
    for ln in [len(base_ids)] * 3 + [len(base_ids) - 7, len(base_ids) - 19, len(base_ids) - 31]:
        ids = torch.tensor([base_ids[-ln:]] * a.bs, device=dev)
        sync(dev); t = time.time()
        with torch.no_grad():
            lm.generate(input_ids=ids, attention_mask=torch.ones_like(ids), max_new_tokens=1, do_sample=False, pad_token_id=0)
        sync(dev); sp.append({"len": ln, "s": round(time.time() - t, 3)})
    res["shape_probe"] = sp
    for ph, ps in P.items():
        cfg = PHASES[ph]
        res["phases"][ph] = {}
        ref = None
        for vn, vc in VARIANTS.items():
            fastgen.uninstall()
            if vc:
                fastgen.install(sleepb, **vc)
            torch.manual_seed(0)
            cm = Count(lm)
            sync(dev); t = time.time()
            if cfg.get("p"):
                outs, pf = sleepb.generate_p(L, cm, ps, cfg["max_new"], a.bs)
            else:
                outs = sleep1.Lang.generate(L, cm, ps, max_new=cfg["max_new"], bs=a.bs, sample=cfg["sample"])
            sync(dev); dt = time.time() - t
            ntok = sum(len(L.ids(o)) for o in outs)
            row = {"seconds": round(dt, 2), "reply_tokens": ntok, "tok_per_s": round(ntok / dt, 1), "model_row_steps": cm.rows, "generate_calls": cm.calls}
            if vn == "base":
                ref = outs
            elif not cfg["sample"]:
                row["same_as_base"] = round(sum(x == y for x, y in zip(ref, outs)) / len(outs), 4)
            if vn != "base":
                row["speedup_vs_base"] = round(res["phases"][ph]["base"]["seconds"] / dt, 3)
            res["phases"][ph][vn] = row
            print(ph, vn, row, flush=True)
    fastgen.uninstall()
    if a.try_static:  # untested idea: static cache + compiled decode through plain HF generate (batch composition as base)
        res["static_compile"] = {}
        for ph in ("verify", "tag"):
            if ph not in P:
                continue
            try:
                lm.generation_config.cache_implementation = "static"
                for rep in (1, 2):  # run 1 includes compile, run 2 is steady state
                    sync(dev); t = time.time()
                    sleep1.Lang.generate(L, lm, P[ph], max_new=PHASES[ph]["max_new"], bs=a.bs)
                    sync(dev); res["static_compile"][f"{ph}_run{rep}_s"] = round(time.time() - t, 2)
            except Exception as e:  # noqa: BLE001
                res["static_compile"][ph] = "failed: " + repr(e)[:300]
            finally:
                lm.generation_config.cache_implementation = None
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({ph: {v: r["seconds"] for v, r in d.items()} for ph, d in res["phases"].items()}))


if __name__ == "__main__":
    main()
