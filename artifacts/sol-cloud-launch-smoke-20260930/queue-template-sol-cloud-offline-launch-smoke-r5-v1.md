BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 0
TIME CAP: 3 minutes
LABEL: sol-cloud-offline-launch-smoke-r5-v1
PUSH: artifacts/sol-cloud-launch-smoke-20260930/r5-v1/collected-v1

Model-free offline capability/import smoke for the next r5 exposure package only. No current bridge gate.
Imports only three sealed Python modules from memory with non-main names and package-shaped virtual paths.
No LM/tokenizer instantiation, model/data loaders, optimizer, GPU, code extraction or PC file writes.
Actual Mac3.9.6 and PC3.10.9 receipt reports tar API/filter behavior and native allocation-unit metadata.
Source-only package contains no human records. Full diagnostics suppressed. Existing strict benspc SSH stdin route.
Publisher owns this template's sole live queue publication.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 150 /usr/bin/python3 -B - <<'SMOKE_BOOTSTRAP'
import hashlib, os, pathlib, subprocess
files = [('scripts/sol_cloud_offline_launch_smoke_v1.py', 'fa70d07c3a097f00195978848602619fb17c2e5a5eba583261e8c3acf3480f92'), ('artifacts/sol-cloud-launch-smoke-20260930/r5-v1/SOURCE-'artifacts/sol-cloud-launch-smoke-20260930/r5-v1/SOURCE-PACKAGE.json'.json', '81da5a87401bc7eeec398269feba6236179883127afaea772db5189d4a231f0f')]
for source, expected in files:
    path = pathlib.Path(source)
    result = subprocess.run(['git', 'show', 'origin/main:' + source], capture_output=True, timeout=15)
    if result.returncode or len(result.stdout)>262144 or hashlib.sha256(result.stdout).hexdigest()!=expected:
        raise SystemExit('pinned smoke source unavailable; diagnostics suppressed')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise SystemExit('existing smoke source differs; preserve without overwrite')
    else:
        with path.open('xb') as stream:
            stream.write(result.stdout)
os.execv('/usr/bin/python3', ['/usr/bin/python3', '-B', 'scripts/sol_cloud_offline_launch_smoke_v1.py', 'relay', '--package', 'artifacts/sol-cloud-launch-smoke-20260930/r5-v1/SOURCE-PACKAGE.json', '--package-sha256', '81da5a87401bc7eeec398269feba6236179883127afaea772db5189d4a231f0f', '--output', 'artifacts/sol-cloud-launch-smoke-20260930/r5-v1/collected-v1'])
SMOKE_BOOTSTRAP
```
