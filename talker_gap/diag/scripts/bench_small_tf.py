# Benchmark: 4-layer d=256 4-head causal transformer, seq 64, batch 64, vocab 32768 (tok32k size).
# One full train step = forward + backward + AdamW step. 5 warmup steps, then 30 timed steps.
import sys, time, json, torch, torch.nn as nn, torch.nn.functional as F

dev = sys.argv[1]
VOCAB, D, H, L, T, B = 32768, 256, 4, 4, 64, 64
torch.set_num_threads(4)
torch.manual_seed(0)

class Block(nn.Module):
    def __init__(s):
        super().__init__()
        s.ln1 = nn.LayerNorm(D); s.qkv = nn.Linear(D, 3 * D); s.proj = nn.Linear(D, D)
        s.ln2 = nn.LayerNorm(D); s.fc = nn.Linear(D, 4 * D); s.fc2 = nn.Linear(4 * D, D)
    def forward(s, x):
        b, t, _ = x.shape
        q, k, v = s.qkv(s.ln1(x)).view(b, t, 3, H, D // H).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + s.proj(a.transpose(1, 2).reshape(b, t, D))
        return x + s.fc2(F.gelu(s.fc(s.ln2(x))))

class TinyLM(nn.Module):
    def __init__(s):
        super().__init__()
        s.emb = nn.Embedding(VOCAB, D); s.pos = nn.Embedding(T, D)
        s.blocks = nn.ModuleList([Block() for _ in range(L)]); s.ln_f = nn.LayerNorm(D)
        s.head = nn.Linear(D, VOCAB, bias=False); s.head.weight = s.emb.weight
    def forward(s, idx):
        x = s.emb(idx) + s.pos(torch.arange(idx.shape[1], device=idx.device))
        for blk in s.blocks: x = blk(x)
        return s.head(s.ln_f(x))

m = TinyLM().to(dev)
n_params = sum(p.numel() for p in m.parameters())
opt = torch.optim.AdamW(m.parameters(), lr=3e-4)
x = torch.randint(0, VOCAB, (B, T), device=dev)
y = torch.randint(0, VOCAB, (B, T), device=dev)

def sync():
    if dev == 'mps': torch.mps.synchronize()
    elif dev == 'cuda': torch.cuda.synchronize()

def step():
    opt.zero_grad(set_to_none=True)
    loss = F.cross_entropy(m(x).reshape(-1, VOCAB), y.reshape(-1))
    loss.backward(); opt.step()
    return loss

for _ in range(5): step()
sync()
times = []
for _ in range(30):
    t0 = time.perf_counter(); step(); sync(); times.append(time.perf_counter() - t0)
times.sort()
mean = sum(times) / len(times)
res = dict(device=dev, params=n_params, threads=torch.get_num_threads(),
           steps_per_s_mean=round(1 / mean, 2), ms_per_step_mean=round(mean * 1000, 1),
           ms_per_step_median=round(times[15] * 1000, 1), ms_per_step_min=round(times[0] * 1000, 1),
           ms_per_step_max=round(times[-1] * 1000, 1), tokens_per_s=round(B * T / mean))
if dev == 'mps':
    res['mps_peak_alloc_MB'] = round(torch.mps.driver_allocated_memory() / 2**20, 1)
print(json.dumps(res))
