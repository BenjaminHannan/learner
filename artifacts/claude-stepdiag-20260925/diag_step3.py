"""$0 CPU preview (dev only, not registered): does a shared chain-step input let a small net answer
3-step questions after practising only 1-2 steps? Copy phase only, width D.
usage (from scripts/): diag_step3.py ARM INPUT D STEPS SEED OUTDIR
  ARM = plain | loop (loop = no step embedding, random 2-12 passes)
  INPUT = old | shared (shared = rsn-355's chain-step input)"""
import sys, math, random, json, time, torch, torch.nn.functional as F
sys.path.insert(0, '.')
arm, inp, D, STEPS, SEED, OUT = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
import claude_rsn294_core as C
import claude_rsn296_gen  # noqa
if inp == "shared":
    import claude_rsn355_run  # noqa  (patches C.Embed)
if arm == "loop":
    import claude_rsn353_run  # noqa  (patches LoopThinker.forward: no step embedding)
import claude_rsn294_run as Rn
torch.set_num_threads(1)
torch.manual_seed(SEED); rng = random.Random(SEED)
model = C.PlainThinker(D, 6, max(1, D // 64)) if arm == "plain" else C.LoopThinker(D, 2, max(1, D // 64))
opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 300) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(s, STEPS) / STEPS))))
it = iter(Rn.Stream(Rn.COPY_KINDS, 64, SEED))
t0 = time.time()
logf = open(f"{OUT}/{arm}-{inp}-s{SEED}.log", "w")
for s in range(STEPS):
    enc, ga, sup, _, _ = next(it)
    logits, sl = model(enc, rng.randint(2, 12)) if arm == "loop" else model(enc)
    la = F.cross_entropy(logits, ga, ignore_index=-100); m = sl > -1e8
    loss = la + 0.5 * F.binary_cross_entropy_with_logits(sl[m], sup[m])
    opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step()
    if s % 100 == 0 or s == STEPS - 1:
        logf.write(json.dumps({"step": s, "ce": round(la.item(), 4), "min": round((time.time() - t0) / 60, 2)}) + "\n"); logf.flush()
model.eval()
drng = random.Random(777); items = []
for k in ["value1", "value2", "value3"]:
    for _ in range(200):
        e = C.gen_episode(drng, k); e["cat"] = k; items.append(e)
res = {}
with torch.no_grad():
    for st in ([6, 12, 20] if arm == "loop" else [None]):
        sc = Rn.score(items, Rn.answer(model, arm, items, torch.device("cpu"), st or 12), "cat")["by_category"]
        res[f"passes_{st}"] = {k: (v.get("raw_right", 0), v.get("checked_right", 0), v["n"]) for k, v in sc.items()}
json.dump(res, open(f"{OUT}/{arm}-{inp}-s{SEED}.json", "w"), indent=1)
print(json.dumps(res))
