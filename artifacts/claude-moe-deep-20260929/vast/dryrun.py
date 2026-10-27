"""Toy-budget dry run of the whole MoE pipeline (ADDENDUM-2), on the rental before real training. Plumbing dry-run of claude_moe_deep_run.py with toy budgets. Not a result; no holdout item is read."""
import sys, json, types, hashlib, torch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import claude_moe_deep_run2 as R2  # noqa: F401  (applies the ADDENDUM-2 fixes)
import claude_moe_deep_run as R, claude_fewex_data as D, claude_fewex_eq_bench as EQ, claude_fewex_bench as B, claude_moe_deep_net as M, claude_fewex_net as N
OUT = Path(sys.argv[1]); DEV = sys.argv[2] if len(sys.argv) > 2 else "cuda"
R.ROOT = OUT; R.ART, R.RUNS, R.EQR = OUT, OUT / "runs", OUT / "eq-runs"
R.SOURCE_STEPS, R.SOURCE_CK = 4, 2
EQ.N_BATCHES = 2; EQ.N_UPDATES = 2 * B.UPDATES
EQ.RUNGS = (1, 64, 16384)
B.SLEEP_STEPS = M.SLEEP_STEPS = 2
B.MAX_ROUNDS = 48
real_panels = D.panels
def small_panels():
    p, banned = real_panels()
    dev = {s: v[:3] for s, v in p["dev"].items()}
    return {"dev": dev, "holdout": dev}, banned   # holdout replaced by dev items: no holdout item is read
D.panels = small_panels
real_old = D.old_panels
D.old_panels = lambda seed=D.SOURCE_SEED: {k: v[:4] for k, v in real_old(seed).items()}
B.DEPTHS = (8, 16)
# lenient source identity (toy sources cannot pass V1)
EQ.identity_source = lambda d, arm, seed: json.loads((d / "source.json").read_text())
real_train = R.train_source
def fake_train(cfg, seed, dev, lr, threads):
    res = real_train(cfg, seed, dev, lr, threads)
    return dict(res, v1_pass=True)
R.train_source = fake_train
# a fake loop source for the loop-control path
ls = OUT / "loopsrc" / "qual-loop-s0"; ls.mkdir(parents=True, exist_ok=True)
torch.manual_seed(0); ln = N.Net("loop"); torch.save(ln.state_dict(), ls / "source.pt")
(ls / "source.json").write_text(json.dumps({"arm": "loop", "seed": 0, "fixed_depth": 16,
    "old": {"sums4": {"right": 200}, "grids5": {"right": 200}}, "gradient_check": {"nonzero_all": True}}))
R.LOOP_SOURCE_SHA[0] = hashlib.sha256((ls / "source.pt").read_bytes()).hexdigest()
a = types.SimpleNamespace(phase=1, device=DEV, threads=2, loop_source_root=OUT / "loopsrc")
R.PHASES[1] = [("source", "L8-E64", 0), ("dev", "L8-E64", 0, "pre"), ("dev", "loopctl", 0, "pre"), ("dev", "loopctl", 1, "pre")]
R.PHASES[3] = [("source", "plain-big", 0), ("dev", "plain-big", 0, "pre"), ("dev", "L8-E64", 0, "fresh")]
R.cmd_phase(a)
a.phase = 3; R.cmd_phase(a)
R.cmd_holdout("L8-E64", 0, "pre", DEV, 2)
R.cmd_holdout("loopctl", 0, "pre", DEV, 2)
for p in sorted(OUT.rglob("*.json")):
    print(p.relative_to(OUT))
h = json.loads((OUT / "eq-runs/L8-E64-pre-s0/holdout.json").read_text())
print("holdout keys", sorted(h["scores"]), "cfg", h["cfg"])
r = json.loads((OUT / "eq-runs/L8-E64-pre-s0/routes.json").read_text())
print("routes stages", sorted(r), "dead k64", r["k64"]["dead_total"], "of", r["k64"]["experts_total"])
print("PLUMBING OK")
