BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
TIME CAP: 2 minutes

Infrastructure check only, $0. Original job failed before arithmetic because
Windows command quoting retained literal backslash-n characters. This new name
passes Python source on stdin. No training, dataset, model or holdout is used.
The watcher owns the GPU claim. Leave every other job and claim untouched.

```bash
set -eu
date -u
perl -e 'alarm shift; exec @ARGV' 120 ssh -T -o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -' <<'PY'
import json
import torch
torch.set_num_threads(2)
assert torch.cuda.is_available()
results = []
for seed in (0, 1):
    torch.manual_seed(seed)
    with torch.no_grad():
        x = torch.randn(4, 4, device='cuda')
        y = x @ torch.eye(4, device='cuda')
        assert bool(torch.isfinite(y).all())
        assert torch.equal(x, y)
    results.append({'seed': seed, 'finite_identity_ok': True})
torch.cuda.synchronize()
print(json.dumps({'scope': 'infrastructure only; no trained-model evidence',
    'torch': torch.__version__, 'cuda': torch.version.cuda,
    'gpu': torch.cuda.get_device_name(0), 'results': results}))
PY
```
