import sys, random, torch
sys.path.insert(0, '.')
import claude_rsn294_core as C
import claude_rsn296_gen  # noqa
import claude_rsn294_run as Rn
torch.manual_seed(0)
it = iter(Rn.Stream(Rn.COPY_KINDS, 32, 1))
batch = next(it)
enc, ga, sup, _, _ = batch
m = C.LoopThinker()
# per-pass state norm at init
x0, mask = m.emb(enc); x = x0
print("x0 rms", x0.pow(2).mean().sqrt().item())
for t in range(12):
    xi = m.inject(torch.cat([x, x0], -1)) + m.step.weight[t]
    x = xi
    for L in m.block: x = L(x, src_key_padding_mask=~mask)
    print(f"pass {t+1}: after-inject rms {xi.pow(2).mean().sqrt().item():.3f}  after-block rms {x.pow(2).mean().sqrt().item():.3f}")
# gradient reaching embeddings vs passes, and how much each pass's state matters
import torch.nn.functional as F
for steps in (2, 6, 12):
    m.zero_grad()
    logits, sl = m(enc, steps)
    loss = F.cross_entropy(logits, ga, ignore_index=-100)
    loss.backward()
    ge = m.emb.sym.weight.grad.norm().item()
    gb = m.block[0].linear1.weight.grad.norm().item()
    print(f"steps {steps}: loss {loss.item():.3f} grad|emb.sym| {ge:.2e} grad|block0.lin1| {gb:.2e}")
