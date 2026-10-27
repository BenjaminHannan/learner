"""Unregistered CPU preview (not a test; 2026-09-26 ~11:20 UTC): does the looped-flow code learn at all? Small flow net
(width 256, 2 layers) on sums only (1-4 digits), 4,000 steps, batch 64, lr 1e-3; fresh dev sums (seed 777, the same
dev draw as the 358a sums preview, never the sealed tests) at 4/6/8 digits, 200 each, after 16/32/64 Euler steps.
Compare artifacts/claude-rsn358a-20260925/preview/ (loop 200/175/88, plain 195/155/42 at the same settings)."""
import json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import torch
import torch.nn.functional as F
import claude_rsn358f_flow as Fl, claude_rsn358a_run as R, claude_rsn358a_envs as E
Fl.WIDTH, Fl.HEADS = 256, 4
R.ARMS["flow"] = dict(d=256, layers=2, heads=4)
torch.set_num_threads(4)
steps, B = int(sys.argv[1]), 64
torch.manual_seed(1); rng = random.Random(11)
net = Fl.FlowNet(); opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=0.1)
gen = torch.Generator(); gen.manual_seed(5)
t0 = time.time()
for s in range(steps):
    n = rng.choice([1, 2, 3, 4]); items = [E.make_sum(rng, n) for _ in range(B)]
    t, sl, y, env = R.tensors(items, "cpu")
    outs = net.flow_train(t, sl, env, y, gen)
    loss = sum(R.ce_and_exact(lg, sl, y)[0] + 0.5 * F.binary_cross_entropy_with_logits(q, R.ce_and_exact(lg, sl, y)[1]) for lg, q in outs) / len(outs)
    opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step()
    if s % 500 == 0: print(s, round(loss.item(), 3), round((time.time() - t0) / 60, 1), flush=True)
drng = random.Random(777)
res = {f"sums{n}": Fl.evaluate(net, [E.make_sum(drng, n) for _ in range(200)], "cpu") for n in (4, 6, 8)}
print(json.dumps(res), flush=True)
Path(__file__).with_name(f"preview_flow_sums_{steps}.json").write_text(json.dumps(res, indent=1))
