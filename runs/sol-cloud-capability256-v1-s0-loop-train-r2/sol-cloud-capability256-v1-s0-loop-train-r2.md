BASH-ONLY: yes
GPU: yes
DISK: 0
TIME CAP: 75 minutes
LABEL: sol-cloud-capability256-v1-s0-loop-train-r2
PUSH: artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v2/execution-sol-cloud-capability256-v1-s0-loop-train-r2

Unique successor after r1 failed before Mac or PC execution because its source file was absent from the watcher worktree. This approved sealed fit has not started. The bootstrap reads exact relay/helper bytes from `origin/main`, verifies both SHA pins, smoke-executes the helper's pure output-layout function to validate this PUSH path, then runs the exact pinned relay in memory. The relay performs actual watcher claim, native package/import/help smoke and fresh process/GPU/disk gates before the runner's own gates. No retries, parallel arms, or experiment changes.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 4500 /usr/bin/python3 -B - --spec artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v2/SPEC-s0-loop-r2.json --spec-sha256 5d6ddcbeb44f9f9aba27547613d85205d245f5e56c302432e1eba979106dfb20 <<'CAP256_R2_BOOTSTRAP'
import hashlib,pathlib,platform,subprocess,sys
W=pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27');job='sol-cloud-capability256-v1-s0-loop-train-r2';relay_path='artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v2/MAC-LAUNCH-v2.py';relay_sha='cc9a7e95cb1d33ec84b1f654ee38ca043deed1d8d471ec3ec99112b705a1e32b';helper_path='scripts/sol_cloud_queue_recovery_v1.py';helper_sha='4708726dc856823f1bea1248fe08607e519dacee521723816d54dd5e89f50876'
assert platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6) and pathlib.Path.cwd().resolve()==W.resolve()
Q=pathlib.Path('/Users/ben-hannan/premonition-watch/queue');queue=Q/(job+'.md')
assert queue.is_file() and (Q/(job+'.running')).is_file() and not (Q/(job+'.exit')).exists()
queue_bytes=queue.read_bytes();tracked=subprocess.run(['git','show','origin/main:handoff/queue/'+job+'.md'],capture_output=True,check=True,timeout=15).stdout
assert tracked==queue_bytes,'actual copied r2 queue differs from origin/main'
def gitblob(path,pin):
 r=subprocess.run(['git','show','origin/main:'+path],capture_output=True,check=True,timeout=15)
 assert hashlib.sha256(r.stdout).hexdigest()==pin,'immutable main source differs: '+path
 return r.stdout
relay=gitblob(relay_path,relay_sha);helper=gitblob(helper_path,helper_sha)
ns={'__name__':'_cap256_helper_smoke'};exec(compile(helper,helper_path,'exec'),ns)
layout=ns['output_layout']('artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v2',job)
assert layout['execution_path']=='artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v2/execution-sol-cloud-capability256-v1-s0-loop-train-r2' and layout['publication_path']=='artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v2/execution-sol-cloud-capability256-v1-s0-loop-train-r2'
exec(compile(relay,relay_path,'exec'),{'__name__':'__main__','__file__':str(W/relay_path)})
CAP256_R2_BOOTSTRAP
```
