import torch, sys
sys.path.insert(0, ".")
from fable_talker101_model import Talker101
torch.manual_seed(0)
m = Talker101().cuda().bfloat16() if False else Talker101().cuda()
opt = torch.optim.AdamW(m.parameters(), lr=3e-4)
xb = torch.randint(0, 4096, (8, 512), device="cuda")
yb = torch.randint(0, 4096, (8, 512), device="cuda")
torch.cuda.reset_peak_memory_stats()
for _ in range(5):
    opt.zero_grad()
    with torch.autocast("cuda", dtype=torch.bfloat16):
        loss = m(xb, yb)["loss"]
    loss.backward()
    opt.step()
print("peak_mem_MiB:", round(torch.cuda.max_memory_allocated() / 2**20, 1))
print("model_params_M:", round(sum(p.numel() for p in m.parameters()) / 1e6, 2))
