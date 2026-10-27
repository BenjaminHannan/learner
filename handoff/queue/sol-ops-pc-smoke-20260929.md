BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
TIME CAP: 2 minutes
Free RTX5070Ti infrastructure smoke only. No data, optimization, scoring, model downloads or installations. Seeds 0 and 1 check finite CUDA arithmetic, not model quality. Coordinator submits this fresh name only to handoff/queue/sol-ops-pc-smoke-20260929.md for the Mac watcher. Standalone pcwatch is absent. Mac watcher checks occupancy and creates its own exact job claim and GPU-BUSY marker. Do not remove any other claim or busy marker.
```bash
set -eu
date -u
perl -e 'alarm shift; exec @ARGV' 120 ssh -o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -c "import torch,json; torch.set_num_threads(2); assert torch.cuda.is_available(); results=[]; exec(\"for seed in (0,1):\\n torch.manual_seed(seed)\\n x=torch.randn(4,4,device=\\\"cuda\\\")\\n with torch.no_grad():\\n  ok=bool(torch.equal(x@torch.eye(4,device=\\\"cuda\\\"),x))\\n assert ok\\n results.append({\\\"seed\\\":seed,\\\"identity_ok\\\":ok})\"); torch.cuda.synchronize(); print(json.dumps({\"scope\":\"infrastructure only; no training or empirical model claim\",\"torch\":torch.__version__,\"cuda\":torch.version.cuda,\"gpu\":torch.cuda.get_device_name(0),\"results\":results}))"'
```
