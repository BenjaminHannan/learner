"""R0: is v1's bridge just a fixed bias?  See PREREG.md.  python -m bridgelab.r0.r0 --root ROOT --dev-visits 700 --val-visits 230"""
import argparse, json, random, sys, time
from pathlib import Path
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
torch.set_num_threads(2)


def cos(a, b):
    return float(torch.nn.functional.cosine_similarity(a.double(), b.double(), dim=0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--d-ckpt", default="/tmp/claude-0/w/D-final.pt")
    ap.add_argument("--c-ckpt", default="/tmp/claude-0/w/W2.pt")
    ap.add_argument("--dev-visits", type=int, default=700)
    ap.add_argument("--val-visits", type=int, default=230)
    ap.add_argument("--single-draws", type=int, default=5)
    ap.add_argument("--gauss-seeds", type=int, default=5)
    ap.add_argument("--out", default=str(Path(__file__).parent / "results.json"))
    ap.add_argument("--only-real", action="store_true")
    a = ap.parse_args()
    T0 = time.time()
    from learnlab.tokenizer import Tokenizer
    from memorylab.storage import Budget
    from learnlab import step1
    from premonition import data as pdata, preprocess
    from premonition.model import PremonitionMini
    from premonition.train import mini_config_from, validate
    from v1 import run as vrun
    from v1.joint import Bridge
    from v1.run import MAX_TOKENS, MAX_VISITS
    from creative import c2_stones, rules_real as R, sampler
    from creative.c2b import DATA

    root = Path(a.root)
    tok = Tokenizer.load(REPO / "data/tokenizer/premonition-tok-v2.json")
    budget = Budget(root.parent, hard=100_000_000_000, steady=80_000_000_000)
    det = pdata.name_detector(budget, root.name, workers=2)
    caches = {"dev": pdata.load_or_build(budget, root.name, "dev", tok, det, split="train", regime=preprocess.LABEL_FREE, log=print),
              "validation": pdata.load_or_build(budget, root.name, "validation", tok, det, regime=preprocess.LABEL_FREE, log=print)}
    stops = sorted(step1.stop_ids(tok)[0])

    def batches_for(cache, n_visits, seed):
        idx = list(range(len(cache)))
        random.Random(seed).shuffle(idx)
        chosen = sorted(idx[:n_visits])
        groups = pdata.length_batches(cache.lengths[chosen].tolist(), MAX_TOKENS, max_visits=MAX_VISITS)
        return [pdata.collate(cache, [chosen[i] for i in g]) for g in groups]

    sets = {"dev": batches_for(caches["dev"], a.dev_visits, 1234), "validation": batches_for(caches["validation"], a.val_visits, 1234)}

    saved = torch.load(a.d_ckpt, map_location="cpu", weights_only=False)
    d = PremonitionMini(mini_config_from(saved["config"]))
    d.load_state_dict(saved["model"])
    d.eval()
    c, _, _ = vrun.load_creative(a.c_ckpt, "cpu")
    bridge = Bridge(d.config.d_model, c.d).attach(d, c)
    bridge.load_state_dict(saved["bridge"])
    bridge.frozen_ctx = True
    for p in list(d.parameters()) + list(bridge.parameters()):
        p.requires_grad_(False)
    ctx = bridge.ctx_c.clone()
    unit, proj = bridge._unit, bridge.p_cd
    with torch.no_grad():
        real_vec = proj(unit(ctx)).clone()
    print("ctx_c rms", float(ctx.pow(2).mean().sqrt()), "norm", float(ctx.norm()), "out vec norm", float(real_vec.norm()), flush=True)

    def score(vec, names=("dev", "validation")):
        out = {}
        for nm in names:
            d.bridge_in = (lambda v=vec: v)
            with torch.no_grad():
                r = validate(d, sets[nm], tokenizer=tok, stop=stops, gold_cards=False)
            out[nm] = {"acc": r["accuracy"], "n": r["questions"]}
        return out

    # ---- creative summaries, fresh from W2
    def creative_mean(rows):
        cap = []
        c.bridge_out = lambda Rr: cap.append(Rr.detach().float().mean(1))        # [B,256] per prompt
        c.eval()
        with torch.no_grad():
            for s in range(0, len(rows), 64):
                c.run(sampler.make_batch(rows[s:s + 64], vocab, "cpu"))
        c.bridge_out = bridge.observe_c
        return torch.cat(cap)                                                    # [N,256]

    from creative import sleep
    _, vocab, _ = sleep.load_parent(a.c_ckpt, "cpu")
    dev_rows = c2_stones._with_nums(R.load_split(DATA, "dev"))[:256]
    warm_all = c2_stones._with_nums(R.load_split(DATA, "warm"))
    warm_rows = random.Random(0).sample(warm_all, 256)
    P_dev, P_warm = creative_mean(dev_rows), creative_mean(warm_rows)
    print("creative summaries done", round(time.time() - T0), flush=True)

    alts = {"4a_dev256_mean": P_dev.mean(0), "4b_warm256_mean": P_warm.mean(0)}
    rng = random.Random(7)
    pool = torch.cat([P_dev, P_warm])
    for i in range(a.single_draws):
        alts[f"4c_single_{i}"] = pool[rng.randrange(len(pool))].clone()
    rms = float(ctx.pow(2).mean().sqrt())
    for s in range(a.gauss_seeds):
        g = torch.Generator().manual_seed(100 + s)
        v = torch.randn(ctx.numel(), generator=g)
        alts[f"4d_gauss_{s}"] = v / v.pow(2).mean().sqrt() * rms

    res = {"config": vars(a), "ctx_rms": rms, "conditions": {}, "alt_geometry": {}}
    C = res["conditions"]
    C["1_real"] = score(real_vec)
    print("real", C["1_real"], round(time.time() - T0), flush=True)
    if a.only_real:
        print(json.dumps(res, indent=1)); return
    C["2_off"] = score(torch.zeros(d.config.d_model))
    print("off", C["2_off"], round(time.time() - T0), flush=True)
    with torch.no_grad():
        for tag, s in (("3_ctx_x0.5", 0.5), ("3_ctx_x2", 2.0)):
            v = proj(unit(ctx * s)).clone()
            C[tag] = score(v)
            C[tag]["vec_identical_to_real"] = bool(torch.equal(v, real_vec))
            C[tag]["max_abs_diff_vec"] = float((v - real_vec).abs().max())
        for tag, s in (("3_out_x0.5", 0.5), ("3_out_x1.5", 1.5)):
            C[tag] = score(real_vec * s)
        # 5: frozen constant
        b = torch.nn.Parameter(real_vec.clone(), requires_grad=False)
        C["5_frozen_const"] = score(b.data.clone())
        C["5_frozen_const"]["vec_bit_identical"] = bool(torch.equal(b.data, real_vec))
        # also check the unmodified bridge path (enabled, to_d) gives the identical vector and identical raw answers on one batch
        d.bridge_in = lambda: bridge.to_d()
        b0 = sets["dev"][0].to("cpu")
        ans_real = d.answer(b0, stop=stops)
        d.bridge_in = lambda v=b.data.clone(): v
        ans_const = d.answer(b0, stop=stops)
        C["5_frozen_const"]["answers_tensors_identical_first_dev_batch"] = bool(
            torch.equal(ans_real.tokens, ans_const.tokens) and torch.equal(ans_real.halt_prob, ans_const.halt_prob) and torch.equal(ans_real.loops, ans_const.loops))
        for name, v in alts.items():
            out_v = proj(unit(v)).clone()
            res["alt_geometry"][name] = {"cos_ctx": cos(ctx, v), "cos_out": cos(real_vec, out_v), "rms": float(v.pow(2).mean().sqrt()),
                                         "out_norm": float(out_v.norm())}
    for name, v in alts.items():
        with torch.no_grad():
            out_v = proj(unit(v)).clone()
        C[name] = score(out_v)
        print(name, C[name], res["alt_geometry"][name], round(time.time() - T0), flush=True)
        Path(a.out).write_text(json.dumps(res, indent=1))
    res["wall_seconds"] = time.time() - T0
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
