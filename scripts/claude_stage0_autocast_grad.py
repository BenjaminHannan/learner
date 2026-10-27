#!/usr/bin/env python3
"""Stage 0 for the autocast-cache suspect (sleep research thread, 2026-09-26). One 358i loop step with 3 no-grad rounds then 2
graded rounds under bf16 autocast, with and without the autocast weight cache; prints how many block weight matrices get
no gradient. Run: python -B scripts/claude_stage0_autocast_grad.py  (CUDA if present, else CPU). No training, no tests."""
import sys, random, torch
sys.path.insert(0, "scripts")
import claude_rsn358i_run as I
R, E = I.R, I.E
dev = "cuda" if torch.cuda.is_available() else "cpu"
print("torch", torch.__version__, dev)
torch.manual_seed(0)
rng = random.Random(0)
items = [E.latin_item(rng, *E.make_latin_base(rng, 5)) for _ in range(8)]
t, s, y, env = R.tensors(items, dev)
for arm in ("loop", "plain"):
  for n_free, n_grad in ((3, 2), (0, 2)):
    for cache in (True, False):
        net = R.Net(arm).to(dev)
        with torch.autocast(dev, dtype=torch.bfloat16, cache_enabled=cache):
            if arm == "plain":
                if n_free: continue
                loss = R.ce_and_exact(net.plain_forward(t, s, env), s, y)[0]
            else:
                outs = net.loop_train(t, s, env, n_free, n_grad)
                loss = sum(R.ce_and_exact(lg, s, y)[0] + q.float().mean() for lg, q in outs)
        loss.backward()
        mats = [(n, p) for n, p in net.named_parameters() if n.startswith("blocks.") and p.dim() == 2]
        none = sum(p.grad is None or p.grad.abs().sum().item() == 0 for _, p in mats)
        print(f"{arm:5s} free={n_free} grad={n_grad} cache={cache!s:5s}: block weight matrices with no gradient {none}/{len(mats)}")
