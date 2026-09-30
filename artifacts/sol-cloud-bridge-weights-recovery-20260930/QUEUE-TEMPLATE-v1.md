BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 1
LOWDISK-OK: yes
TIME CAP: 12 minutes
LABEL: sol-cloud-bridge-weights-collect-v1

HELD TEMPLATE. Integrator routes only after fit process conflict is safe.
Exactly four existing files: candidate-parent.pt, candidate-English.pt,
night-resume.pt, and the original source parent. Three sizes/hashes come from the
recovered SOURCE inventory and candidate manifest; original-parent path/hash
comes from BINDING-v3.json and its size is measured during preflight, never guessed.
Use existing strict SSH and native Mac 3.9.6/PC 3.10.9. No PC write/archive/delete,
model import, inference, optimizer, data collection, credential or security change.
Stat all four first. Refuse before content reads above 128 MiB/file or 256 MiB total.
PC free space must retain at least 1 GiB; PC gets no additional file footprint.
Bounded binary stream copies exactly the admitted size, verifies before/local/after
SHA and source metadata, retains PC originals, and writes Mac-only 4 MiB parts.
Mac aggregate copy/parts peak <=512 MiB plus small metadata, retaining 1 GiB free.
Exact origin/main collector/spec bytes are verified without checkout/helper writes.
No command arguments/environment/stderr dump. Fresh output only; failures preserved.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 660 /usr/bin/python3 -B - <<'SOL_BRIDGE_WEIGHT_RECOVERY'
import hashlib,json,pathlib,platform,subprocess,sys
try:
    if platform.system()!='Darwin' or sys.version_info[:3]!=(3,9,6):
        raise RuntimeError('Verified native Mac runtime required')
    root=pathlib.Path.cwd().resolve()
    if root!=pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27').resolve():
        raise RuntimeError('Verified publisher cwd required')
    pins={'scripts/sol_cloud_bridge_weights_collect_v1.py':'00cf3505e94754644364295ae82c890d277a8888fd66501d9ac84142dccf594b','artifacts/sol-cloud-bridge-weights-recovery-20260930/COLLECTION-SPEC-v1.json':'192c5ca3de40e39b9809878d5f71d63d055ea6d4b7b4151cc7b6780560523149'}
    payload={}
    for relative,expected in pins.items():
        data=subprocess.check_output(['git','show','origin/main:'+relative],stderr=subprocess.PIPE,timeout=15)
        if hashlib.sha256(data).hexdigest()!=expected:
            raise RuntimeError('Published collector/spec hash mismatch')
        payload[relative]=data
    source=payload['scripts/sol_cloud_bridge_weights_collect_v1.py']
except Exception as error:
    print(json.dumps(dict(stage='pinned bootstrap',error_type=type(error).__name__,model_calls=0,optimizer_updates=0,pc_writes=0,full_arguments_or_environment_logged=False)),flush=True)
    sys.exit(1)
namespace=dict(__name__='__main__',__file__=str(root/'scripts/sol_cloud_bridge_weights_collect_v1.py'))
exec(compile(source,'scripts/sol_cloud_bridge_weights_collect_v1.py','exec'),namespace)
SOL_BRIDGE_WEIGHT_RECOVERY
```

PUSH: artifacts/sol-cloud-bridge-weights-recovery-20260930/collected-v1/publication
