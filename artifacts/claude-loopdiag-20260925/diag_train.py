"""CPU diagnosis of the 294/296 LoopThinker copy failure. Small width, same recipe otherwise.
usage: diag_train.py VARIANT D STEPS BATCH SEED"""
import sys, math, random, json, time, torch, torch.nn as nn, torch.nn.functional as F
sys.path.insert(0, '.')
import claude_rsn294_core as C
import claude_rsn296_gen  # noqa
import claude_rsn294_run as Rn
torch.set_num_threads(2)
var, D, STEPS, B, SEED = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
torch.manual_seed(SEED); rng = random.Random(SEED)

class Loop(C.LoopThinker):
    def __init__(self, d, v):
        super().__init__(d, 2, max(1, d // 64)); self.v = v
        if v == "normstate": self.sn = nn.LayerNorm(d)
        if v == "smallstep": nn.init.normal_(self.step.weight, std=0.02)
        if v == "residinject": nn.init.zeros_(self.inject.weight); nn.init.zeros_(self.inject.bias)
    def forward(self, e, steps=6, all_passes=False):
        x0, m = self.emb(e); x = x0; outs = []
        for t in range(steps):
            xs = self.sn(x) if self.v == "normstate" else x
            if self.v == "residinject":
                x = x + self.inject(torch.cat([xs, x0], -1))
            else:
                x = self.inject(torch.cat([xs, x0], -1))
            if self.v not in ("nostep",): x = x + self.step.weight[t]
            for L in self.block: x = L(x, src_key_padding_mask=~m)
            if all_passes and t >= 1: outs.append(self.heads(x, e))
        return outs if all_passes else self.heads(x, e)

if var == "plain":
    model = C.PlainThinker(D, 6, max(1, D // 64)); arm = "plain"
else:
    model = Loop(D, var); arm = "loop"
lr = 1e-4 if var == "lr1e-4" else 3e-4
opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
total = 12000
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 300) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(s, total) / total))))
it = iter(Rn.Stream(Rn.COPY_KINDS, B, SEED))
def passes():
    if var == "fixed4": return 4
    return rng.randint(2, 12)
t0 = time.time(); log = []
for s in range(STEPS):
    enc, ga, sup, _, _ = next(it)
    if arm == "plain":
        logits, sl = model(enc)
        la = F.cross_entropy(logits, ga, ignore_index=-100); m = sl > -1e8
        loss = la + 0.5 * F.binary_cross_entropy_with_logits(sl[m], sup[m])
    elif var == "perpass":
        outs = model(enc, passes(), all_passes=True); ls = []
        for logits, sl in outs:
            la_ = F.cross_entropy(logits, ga, ignore_index=-100); m = sl > -1e8
            ls.append(la_ + 0.5 * F.binary_cross_entropy_with_logits(sl[m], sup[m]))
        loss = sum(ls) / len(ls); la = F.cross_entropy(outs[-1][0], ga, ignore_index=-100)
    else:
        logits, sl = model(enc, passes())
        la = F.cross_entropy(logits, ga, ignore_index=-100); m = sl > -1e8
        loss = la + 0.5 * F.binary_cross_entropy_with_logits(sl[m], sup[m])
    opt.zero_grad(); loss.backward()
    gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0).item(); opt.step(); sched.step()
    if s % 25 == 0 or s == STEPS - 1:
        log.append({"step": s, "loss": round(loss.item(), 4), "ce": round(la.item(), 4), "gn": round(gn, 3), "min": round((time.time() - t0) / 60, 2)})
        print(json.dumps(log[-1]), flush=True)
json.dump(log, open(f"{sys.argv[6] if len(sys.argv)>6 else '.'}/diag-{var}-d{D}-s{SEED}.json", "w"))
