"""Unregistered CPU preview (not a test): small loop vs small plain on sums only, dev items from fresh seeds
(never the sealed tests). Asks only: does the loop's accuracy on longer sums rise with more rounds at all?"""
import json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import torch
import claude_rsn358a_run as R, claude_rsn358a_envs as E
R.ARMS = {"plain": dict(d=128, layers=8, heads=4), "loop": dict(d=256, layers=2, heads=4)}
torch.set_num_threads(2)
steps, B = int(sys.argv[1]), 64
out = {}
for arm in ("plain", "loop"):
    torch.manual_seed(1); rng = random.Random(11); rr = random.Random(12)
    net = R.Net(arm); opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=0.1)
    t0 = time.time()
    for s in range(steps):
        items = [E.make_sum(rng, rng.choice([1, 2, 3, 4])) for _ in range(1)]
        n = items[0].size; items += [E.make_sum(rng, n) for _ in range(B - 1)]
        t, sl, y, env = R.tensors(items, "cpu")
        if arm == "plain":
            ce, _ = R.ce_and_exact(net.plain_forward(t, sl, env), sl, y); loss = ce
        else:
            tot = rr.randint(1, 16); k = rr.randint(1, min(tot, 6))
            outs = net.loop_train(t, sl, env, tot - k, k)
            loss = sum(R.ce_and_exact(lg, sl, y)[0] + 0.5 * torch.nn.functional.binary_cross_entropy_with_logits(q, R.ce_and_exact(lg, sl, y)[1]) for lg, q in outs) / k
        opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step()
        if s % 500 == 0: print(arm, s, round(loss.item(), 3), round((time.time() - t0) / 60, 1), flush=True)
    drng = random.Random(777)
    res = {}
    for n in (4, 6, 8):
        res[f"sums{n}"] = R.evaluate(net, [E.make_sum(drng, n) for _ in range(200)], "cpu")
    out[arm] = res
    print(arm, json.dumps(res), flush=True)
Path(__file__).with_name(f"preview_sums_{steps}.json").write_text(json.dumps(out, indent=1))
