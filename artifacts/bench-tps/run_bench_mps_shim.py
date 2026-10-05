# local MPS shim (not pushed): exact adaptive_avg_pool1d for non-divisible sizes, computed on the device
import sys, runpy, math, torch
import torch.nn.functional as F
_orig = F.adaptive_avg_pool1d
def pool(x, out):
    L = x.shape[-1]
    if x.device.type != "mps" or L % out == 0:
        return _orig(x, out)
    cols = [x[..., (i * L) // out: -((-(i + 1) * L) // out)].mean(-1) for i in range(out)]
    return torch.stack(cols, -1)
F.adaptive_avg_pool1d = pool
torch.nn.functional.adaptive_avg_pool1d = pool
sys.argv = ["bench_tps.py"] + sys.argv[1:]
runpy.run_path("bench_tps.py", run_name="__main__")
