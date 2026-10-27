BASH-ONLY: yes
GPU: yes
DISK: 0
TIME CAP: 75 minutes
LABEL: sol-cloud-capability256-v1-s0-loop-train-r4
PUSH: artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v4/execution-sol-cloud-capability256-v1-s0-loop-train-r4

Unique s0-loop r3 successor after r2 stopped before runner invocation: the exact read-only preflight failed before Mac execution because the queue referenced a nonexistent v2 filename inside the v3 relay directory. This additive r4 package binds the exact v4 relay filename and matching queue identity; its ownership and GPU/process guards are unchanged; separate GPU/model-runtime and unknown-owner checks remain sealed. Scientific plan, runner, rows, marks, caps, and scoring are unchanged. 

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 4500 /usr/bin/python3 -B - --spec artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v4/SPEC-sol-cloud-capability256-v1-s0-loop-train-r4.json --spec-sha256 f011f7904f5a112c962c3046193ae0b9628d8de3d1fd04b7feb8796541492598 <<'CAP256_R4_BOOTSTRAP'
import hashlib,pathlib,platform,subprocess,sys
W=pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27');job='sol-cloud-capability256-v1-s0-loop-train-r4';relay_path='artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v4/MAC-LAUNCH-v4.py';relay_sha='1ce0477df0635c2814e626639d48462f3ba96786b0a0c8a5b3e44caee15c3b69';helper_path='scripts/sol_cloud_queue_recovery_v1.py';helper_sha='4708726dc856823f1bea1248fe08607e519dacee521723816d54dd5e89f50876'
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
layout=ns['output_layout']('artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v4',job)
assert layout['execution_path']=='artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v4/execution-sol-cloud-capability256-v1-s0-loop-train-r4' and layout['publication_path']=='artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v4/execution-sol-cloud-capability256-v1-s0-loop-train-r4'
exec(compile(relay,relay_path,'exec'),{'__name__':'__main__','__file__':str(W/relay_path)})
CAP256_R4_BOOTSTRAP
```
