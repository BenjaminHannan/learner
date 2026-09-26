"""Unregistered CPU preview (not a test), 2026-09-26 02:00 UTC, while the registered 358a runs on BensPC: small loop
vs small plain on Latin grids only (practise 4x4 and 5x5), dev items from fresh seeds (never the sealed tests).
Asks: does the loop carry to 6x6/7x7 better than plain? Used only to pick the next change if 358a fails."""
import json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import torch
import claude_rsn358a_run as R, claude_rsn358a_envs as E
import claude_rsn358a2_run as V  # noqa: F401  (v2 stop rule for the loop's evaluate)
R.ARMS = {"plain": dict(d=128, layers=8, heads=4), "loop": dict(d=256, layers=2, heads=4)}
torch.set_num_threads(int(sys.argv[2]) if len(sys.argv) > 2 else 2)
steps, B = int(sys.argv[1]), 64
out = {}
for arm in ("plain", "loop"):
    torch.manual_seed(1); rng = random.Random(21); rr = random.Random(22)
    net = R.Net(arm); opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=0.1)
    t0 = time.time()
    for s in range(steps):
        n = rng.choice([4, 5])
        items = [E.latin_item(rng, *E.make_latin_base(rng, n)) for _ in range(B)]
        t, sl, y, env = R.tensors(items, "cpu")
        if arm == "plain":
            ce, _ = R.ce_and_exact(net.plain_forward(t, sl, env), sl, y); loss = ce
        else:
            tot = rr.randint(1, 16); k = rr.randint(1, min(tot, 6))
            outs = net.loop_train(t, sl, env, tot - k, k)
            loss = sum(R.ce_and_exact(lg, sl, y)[0] + 0.5 * torch.nn.functional.binary_cross_entropy_with_logits(q, R.ce_and_exact(lg, sl, y)[1]) for lg, q in outs) / k
        opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step()
        if s % 500 == 0: print(arm, s, round(loss.item(), 3), round((time.time() - t0) / 60, 1), flush=True)
    drng = random.Random(4777)
    res = {}
    for n in (5, 6, 7):
        res[f"grids{n}"] = R.evaluate(net, [E.latin_item(drng, *E.make_latin_base(drng, n)) for _ in range(200)], "cpu")
    out[arm] = res
    torch.save(net.state_dict(), Path(__file__).with_name(f"preview_grids_{arm}.pt"))
    print(arm, json.dumps(res), flush=True)
Path(__file__).with_name(f"preview_grids_{steps}.json").write_text(json.dumps(out, indent=1))
