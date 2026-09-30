BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 5 minutes
LABEL: sol-cloud-question-token-count-396-v1
PUSH: artifacts/sol-cloud-question-token-count-20260930/execution-v1

HELD template; sole integrator owns live publication. Explicitly accepted synthetic TRAIN questions only (100+296), independently admitted canonical numeric targets. No held four answers or mixed source is shipped.
Actual cached LFM2.5 snapshot0f604ada3f766f9f257460c4c9f0b5d6f69d431b; four original tokenizer/config byte pins before/after. AutoTokenizer local_files_only, trust_remote_code=false, offline environment. Complete question is the sole query input; IDs/provenance never enter it. Numeric target is counted separately including EOS. No truncation, model weights, generation, GPU or optimizer.
CPU packet134484B; fresh owned PC input directory; no archive/delete/weight transfer. Mac stdout/stderr/SSH exit preserved even failure. Actual native counts remain unmeasured until watcher execution. Generated diagnostics never training material.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 300 /usr/bin/python3 -B - <<'QUESTION_TOKEN_COUNT_MAC_BOOTSTRAP'
import hashlib,os,pathlib,subprocess
relative='artifacts/sol-cloud-question-token-count-20260930/MAC-COUNT-v1.py'
result=subprocess.run(['git','show','origin/main:'+relative],capture_output=True,timeout=10,check=True)
assert hashlib.sha256(result.stdout).hexdigest()=='418aa53a65912f6ed6957c37783d4220de8c06f008eea7422e9d1f174b874d85','pinned relay bytes differ'
path=pathlib.Path(relative);path.parent.mkdir(parents=True,exist_ok=True)
if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()=='418aa53a65912f6ed6957c37783d4220de8c06f008eea7422e9d1f174b874d85','existing relay differs; preserve it'
else:
 with path.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3','-B',relative,'--packet-sha256','1e6299fe31455c1edd53c62784dd0934b8faf180c52be0ef16491a1cc2e10f76'])
QUESTION_TOKEN_COUNT_MAC_BOOTSTRAP
```
