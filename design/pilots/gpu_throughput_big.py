import json, time, math
import torch, torch.nn as nn, torch.nn.functional as F
torch.backends.cuda.matmul.allow_tf32 = True
dev = torch.device("cuda")
class Block(nn.Module):
    def __init__(s, d, h):
        super().__init__(); s.h = h
        s.n1 = nn.LayerNorm(d); s.qkv = nn.Linear(d, 3*d); s.o = nn.Linear(d, d)
        s.n2 = nn.LayerNorm(d); s.f1 = nn.Linear(d, 4*d); s.f2 = nn.Linear(4*d, d)
    def forward(s, x):
        B, T, D = x.shape
        q, k, v = s.qkv(s.n1(x)).view(B, T, 3, s.h, D//s.h).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(B, T, D)
        x = x + s.o(a)
        return x + s.f2(F.gelu(s.f1(s.n2(x))))
class LM(nn.Module):
    def __init__(s, V, d, L, h, T):
        super().__init__()
        s.emb = nn.Embedding(V, d); s.pos = nn.Parameter(torch.zeros(T, d))
        s.blocks = nn.ModuleList([Block(d, h) for _ in range(L)]); s.nf = nn.LayerNorm(d); s.head = nn.Linear(d, V, bias=False)
    def forward(s, x):
        h = s.emb(x) + s.pos[:x.shape[1]]
        for b in s.blocks: h = b(h)
        return s.head(s.nf(h))
V, T = 2048, 512
out = []
for name, d, L, h in (("base-85M", 768, 12, 12), ("big-300M", 1024, 24, 16), ("huge-700M", 1536, 24, 16)):
    for B in (8, 16, 32):
        torch.manual_seed(0); torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
        m = LM(V, d, L, h, T).to(dev); opt = torch.optim.AdamW(m.parameters(), lr=3e-4, fused=True)
        params = sum(p.numel() for p in m.parameters())
        x = torch.randint(0, V, (B, T + 1), device=dev)
        def step():
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = F.cross_entropy(m(x[:, :-1]).float().view(-1, V), x[:, 1:].reshape(-1))
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
        try:
            for _ in range(3): step()
            torch.cuda.synchronize(); t = time.perf_counter(); n = 0
            while time.perf_counter() - t < 6.0: step(); n += 1
            torch.cuda.synchronize(); dt = time.perf_counter() - t
            r = dict(model=name, params=params, batch=B, tokens_per_s=round(n*B*T/dt), steps_per_s=round(n/dt, 2), peak_alloc_mib=round(torch.cuda.max_memory_allocated()/2**20))
        except torch.cuda.OutOfMemoryError:
            r = dict(model=name, batch=B, oom=True)
        print("TPUT=" + json.dumps(r), flush=True); out.append(r)
        del m, opt
