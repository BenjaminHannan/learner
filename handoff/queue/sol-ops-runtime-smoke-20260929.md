BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 1
TIME CAP: 2 minutes
Ops-only import/arithmetic smoke, no optimizer, training, model, data or holdout. $0 rental. Coordinator submits under fresh handoff/queue/sol-ops-runtime-smoke-20260929.md and pushes; local files alone are invisible to the watcher. Mac bash runner's actual outer alarm is 75 minutes; this block enforces its own 120-second bound.
```bash
set -eu
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
date -u
perl -e 'alarm shift; exec @ARGV' 120 uv run --offline --no-project --python 3.12 --with torch --with numpy python - <<'PY'
import json
import torch
torch.set_num_threads(2)
records = []
for seed in (0, 1):
    torch.manual_seed(seed)
    x = torch.randn(4, 4)
    with torch.no_grad():
        assert torch.equal(x @ torch.eye(4), x)
    records.append({'seed': seed, 'cpu_identity_ok': True})
print(json.dumps({'scope': 'infrastructure smoke only; no empirical model claim',
                  'torch': torch.__version__, 'mps_available': torch.backends.mps.is_available(),
                  'cuda_available': torch.cuda.is_available(), 'seeds': records}))
PY
```
