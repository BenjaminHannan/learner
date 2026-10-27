#!/usr/bin/env python3
"""Lead 0: is the jumpy few-example curve just the learning rate?

Re-adapts ONE start (default: practised loop, seed 1) at k = 1,024 and 16,384 with a chosen
learning rate and nothing else changed (same pool, same batches, same 2,048 updates, same
Learner as the sealed eq harness). Scores the DEV panel only, 9x9. No sleep, no old panels,
no holdout. Imports the sealed harness; edits nothing.

  python -B scripts/claude_dir_lr_lead0.py run --arm loop --seed 1 --init pre --lr 3e-4
  python -B scripts/claude_dir_lr_lead0.py verdict          # reads all lead0 json, applies LEAD0-MARKS.md
  python -B scripts/claude_dir_lr_lead0.py selftest         # no torch needed
"""
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "claude-dir-lr-20260928" / "lead0"
STORED = ROOT / "artifacts" / "claude-fewex-20260927" / "eq-runs"
KS = (1024, 16384)
LRS = ("0.0003", "0.001", "0.003")
LR_SENSITIVE = 30      # counts of 300 (10 points); see LEAD0-MARKS.md
COLLAPSE_FIX = 60      # fresh-loop rescue bar, counts of 300


def run(a):
    sys.path.insert(0, str(ROOT / "scripts"))
    import copy, torch
    import claude_fewex_eq_bench as EQ
    import claude_fewex_bench as B
    import claude_fewex_data as D
    import claude_fewex_net
    B.N = claude_fewex_net
    torch.set_num_threads(a.threads)
    lr = float(a.lr)
    src_dir = B.ART / "runs" / f"qual-{a.arm}-s{a.seed}"
    src = EQ.identity_source(src_dir, a.arm, a.seed)
    depth = src["fixed_depth"]
    panels, banned = D.panels()
    pool, _, digest = EQ.make_pool(a.seed, banned)
    if a.init == "pre":
        base = B.load_model(src_dir / "source.pt", a.arm)
    else:
        torch.manual_seed(900000 + a.seed)
        base = B.N.Net(a.arm)
    tag = f"{a.arm}-s{a.seed}-{a.init}-lr{a.lr}"
    OUT.mkdir(parents=True, exist_ok=True)
    for k in KS:
        path = OUT / f"{tag}-k{k}.json"
        if path.exists():
            continue
        t0 = time.monotonic()
        learner = B.Learner(copy.deepcopy(base), lr)
        for batch in EQ.batches(pool, k, a.seed):
            learner.maze_batch(batch)
        assert learner.steps == EQ.N_UPDATES
        sc = B.score(learner.net, panels["dev"][9], depth)
        B.dump(path, {"arm": a.arm, "seed": a.seed, "init": a.init, "lr": lr, "k": k,
                      "updates": learner.steps, "support_sha256": digest, "panel": "dev-9x9",
                      "right": sc["right"], "n": sc["n"], "fixed_right": sc["fixed_right"],
                      "mean_rounds": sc["mean_rounds"], "cap_hits": sc["cap_hits"],
                      "seconds": round(time.monotonic() - t0)})
        print(json.dumps({"tag": tag, "k": k, "right": sc["right"], "n": sc["n"]}), flush=True)


def stored_right(arm, seed, init, k):
    d = json.loads((STORED / f"{arm}-s{seed}-{init}" / "adapt.json").read_text())
    return d["rungs"][str(k)]["9"]["right"]


def judge(counts, stored):
    """counts {lr: {k: right}}; stored {k: right at lr 1e-3}. Pure function; see LEAD0-MARKS.md."""
    out = {"rerun_matches_stored": all(counts.get("0.001", {}).get(k) == stored[k] for k in KS if k in counts.get("0.001", {})),
           "spread": {}, "lr_sensitive_rungs": [], "best_lr": {}}
    for k in KS:
        v = {lr: counts[lr][k] for lr in counts if k in counts[lr]}
        if len(v) < 3:
            out["spread"][k] = None
            continue
        out["spread"][k] = max(v.values()) - min(v.values())
        out["best_lr"][k] = max(v, key=v.get)
        if out["spread"][k] >= LR_SENSITIVE:
            out["lr_sensitive_rungs"].append(k)
    n = len(out["lr_sensitive_rungs"])
    complete = all(out["spread"][k] is not None for k in KS)
    out["word"] = ("INCOMPLETE" if not complete else
                   "LR_MATTERS" if n == 2 else "LR_MATTERS_AT_ONE_RUNG" if n == 1 else "NOT_THE_LR")
    return out


def verdict(a=None):
    rows = {}
    for p in sorted(OUT.glob("*.json")):
        d = json.loads(p.read_text())
        rows.setdefault((d["arm"], d["seed"], d["init"]), {}).setdefault(f'{d["lr"]:g}', {})[d["k"]] = d["right"]
    for (arm, seed, init), c in rows.items():
        st = {k: stored_right(arm, seed, init, k) for k in KS}
        print(arm, seed, init, "counts of 300:", json.dumps(c), "stored 1e-3:", st)
        print("  ", judge(c, st))
        if init == "fresh":
            k = 1024
            fixed = [lr for lr in c if c[lr].get(k, 0) >= COLLAPSE_FIX]
            print(f"   fresh collapse at k=1024 (stored {st[k]} of 300): rescued (>= {COLLAPSE_FIX}) by lr {fixed or 'none'}")


def selftest():
    a = {"0.0003": {1024: 215, 16384: 250}, "0.001": {1024: 233, 16384: 261}, "0.003": {1024: 240, 16384: 100}}
    r = judge(a, {1024: 233, 16384: 261})
    assert r["word"] == "LR_MATTERS_AT_ONE_RUNG" and r["lr_sensitive_rungs"] == [16384] and r["rerun_matches_stored"], r
    b = {"0.0003": {1024: 230, 16384: 255}, "0.001": {1024: 233, 16384: 261}, "0.003": {1024: 240, 16384: 270}}
    assert judge(b, {1024: 233, 16384: 262})["word"] == "NOT_THE_LR"
    assert not judge(b, {1024: 233, 16384: 262})["rerun_matches_stored"]
    assert judge({"0.001": {1024: 1}}, {1024: 1, 16384: 1})["word"] == "INCOMPLETE"
    print("lead0 selftest ok")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("run", "verdict", "selftest"))
    p.add_argument("--arm", default="loop", choices=("loop", "plain"))
    p.add_argument("--seed", type=int, default=1, choices=(0, 1))
    p.add_argument("--init", default="pre", choices=("pre", "fresh"))
    p.add_argument("--lr", default="0.001", choices=LRS)
    p.add_argument("--threads", type=int, default=1)
    a = p.parse_args()
    {"run": run, "verdict": verdict, "selftest": lambda _: selftest()}[a.cmd](a)
