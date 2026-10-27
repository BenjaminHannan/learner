"""$0 CPU preview (dev only, not registered) of road-map step R4, "one step per thinking round, then
hold", on the loop reasoner (no step embedding, rsn-355's shared chain-step input). Copy phase only.
  MODE = last    loss on the last pass only (as 294/296/353)
  MODE = ladder  loss at EVERY pass: at pass t the answer so far is the value of the chain row for step
                 min(t, k) (for step < k that value is the next person in the chain), and from pass k on
                 it is the final answer and must stay there. Other kinds: the final answer at every pass.
                 Support bits at the last pass only. The solver's row is never fed back in as input.
usage (from scripts/): diag_ladder.py MODE D STEPS SEED OUTDIR"""
import sys, math, random, json, time, torch, torch.nn.functional as F
sys.path.insert(0, '.')
mode, D, STEPS, SEED, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
import claude_rsn294_core as C
import claude_rsn296_gen  # noqa
import claude_rsn355_run  # noqa  (shared chain-step input)
import claude_rsn294_run as Rn
torch.set_num_threads(1)
torch.manual_seed(SEED); rng = random.Random(SEED)
_K = C._key


def forward_all(self, e, steps):
    x0, m = self.emb(e); x = x0; outs = []
    for t in range(steps):
        x = self.inject(torch.cat([x, x0], -1))          # no step embedding (rsn-353)
        for L in self.block:
            x = L(x, src_key_padding_mask=~m)
        outs.append(self.heads(x, e))
    return outs


def forward_last(self, e, steps=6):
    return forward_all(self, e, steps)[-1]


C.LoopThinker.forward = forward_last
model = C.LoopThinker(D, 2, max(1, D // 64))
opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 300) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(s, STEPS) / STEPS))))
it = iter(Rn.Stream(Rn.COPY_KINDS, 64, SEED))


def chain_actions(info, ga):
    """per-step target actions for a value question with a present answer, else None."""
    fr = info["frame"]
    if fr["kind"] != "value" or ga == C.A_UNK or ga == -100:
        return None
    rows, cur, acts = info["rows"], fr["who"][0], []
    for r in fr["relations"]:
        h = [i for i, x in enumerate(rows) if _K(x["subject"]) == _K(cur) and _K(x["relation"]) == _K(r)]
        if not h:
            return None
        i = max(h, key=lambda j: int(rows[j]["when"]))
        acts.append(C.A_ROWV0 + i); cur = rows[i]["value"]
    return acts


t0 = time.time(); logf = open(f"{OUT}/ladder-{mode}-s{SEED}.log", "w")
for s in range(STEPS):
    enc, ga, sup, _, infos = next(it)
    P = rng.randint(2, 12)
    outs = forward_all(model, enc, P)
    m = outs[-1][1] > -1e8
    lsup = F.binary_cross_entropy_with_logits(outs[-1][1][m], sup[m])
    if mode == "last":
        la = F.cross_entropy(outs[-1][0], ga, ignore_index=-100)
        loss = la + 0.5 * lsup
    else:
        tgt = ga.unsqueeze(0).repeat(P, 1)                 # [P, B]
        for b, inf in enumerate(infos):
            ca = chain_actions(inf, int(ga[b]))
            if ca:
                for t in range(P):
                    tgt[t, b] = ca[min(t, len(ca) - 1)]
        lps = [F.cross_entropy(outs[t][0], tgt[t], ignore_index=-100) for t in range(P)]
        la = F.cross_entropy(outs[-1][0], ga, ignore_index=-100)
        loss = sum(lps) / P + 0.5 * lsup
    opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step()
    if s % 100 == 0 or s == STEPS - 1:
        logf.write(json.dumps({"step": s, "ce_last": round(la.item(), 4), "min": round((time.time() - t0) / 60, 2)}) + "\n"); logf.flush()
model.eval()
drng = random.Random(777); items = []
for k in ["value1", "value2", "value3"]:
    for _ in range(200):
        e = C.gen_episode(drng, k); e["cat"] = k; items.append(e)
res = {}
with torch.no_grad():
    for st in [2, 3, 4, 6, 12, 20, 40]:
        sc = Rn.score(items, Rn.answer(model, "loop", items, torch.device("cpu"), st), "cat")["by_category"]
        res[f"passes_{st}"] = {k: (v.get("raw_right", 0), v.get("checked_right", 0), v["n"]) for k, v in sc.items()}
json.dump(res, open(f"{OUT}/ladder-{mode}-s{SEED}.json", "w"), indent=1)
print(json.dumps(res))
