"""Unregistered: can small nets (mixed heads) learn mazes 5/7 in a short budget? Scores fresh 7x7 and 9x9 mazes."""
import sys, random, json, time, math
sys.path.insert(0, "/home/user/learner/scripts"); sys.path.insert(0, ".")
import torch, torch.nn.functional as F
import attn_trial as A
import claude_rsn358m_maze as M
E, R = A.E, A.R
E.ENVS.append("mazes") if "mazes" not in E.ENVS else None
_c = E.check
E.check = lambda it, p: M.check_maze(it, p) if it.env == "mazes" else _c(it, p)
arm, steps = sys.argv[1], int(sys.argv[2])
torch.manual_seed(1); torch.set_num_threads(1)
rng, rr = random.Random(11), random.Random(12)
net = A.make_net(arm, "mixed")
opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=0.1, betas=(0.9, 0.95))
sch = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(i, steps) / steps)))
trng = random.Random(77100)
tests = {f"maze{s}": [M.make_maze(trng, s) for _ in range(200)] for s in (7, 9, 11)}
t0 = time.time()
for step in range(1, steps + 1):
    net.train(); s_ = rng.choice([5, 7]); items = [M.make_maze(rng, s_) for _ in range(64)]
    t, s, y, env = R.tensors(items, "cpu")
    if arm == "plain":
        loss, _ = R.ce_and_exact(net.plain_forward(t, s, env), s, y)
    else:
        tot = rr.randint(1, 16); k = rr.randint(1, min(tot, 6)); ls = []
        for lg, q in net.loop_train(t, s, env, tot - k, k):
            c_, ex = R.ce_and_exact(lg, s, y); ls.append(c_ + 0.5 * F.binary_cross_entropy_with_logits(q.float(), ex))
        loss = torch.stack(ls).mean()
    opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step(); sch.step()
    if step % 500 == 0 or step == steps:
        res = {k: A.score(net, v) for k, v in tests.items()}
        print(json.dumps({"arm": arm, "step": step, "loss": round(loss.item(), 4), "min": round((time.time() - t0) / 60, 1), "res": res}), flush=True)
