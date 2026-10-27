BASH-ONLY: yes
GPU: no
DISK: 1 MiB
TIME CAP: 5 minutes
LABEL: sol-cloud-question-token-count-1965-v1
PUSH: artifacts/sol-cloud-question-token-count-20260930/all1965-v1/execution-v1

HELD template; sole integrator owns live publication. One hash-verified accepted-only question corpus packet contains 1,965 ID/question/question-SHA rows. The PC tokenizer receives only each complete question string; IDs and hashes bind results but are never passed to tokenizer.encode. No labels, target sidecar, facts, trees, archive, weights, model construction, generation, GPU, network or optimizer action. Uses only the exact locally cached tokenizer/config metadata pins and appends the tokenizer's EOS once after encoding with add_special_tokens=False. No truncation; report actual full question+EOS IDs/counts against the 48-token cap. Preserve stdout/stderr and transport disposition.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 300 /usr/bin/python3 -B - <<'QUESTION_TOKEN_COUNT_MAC_BOOTSTRAP'
import hashlib,os,pathlib,subprocess
relative='artifacts/sol-cloud-question-token-count-20260930/all1965-v1/MAC-COUNT-v1.py'
result=subprocess.run(['git','show','origin/main:'+relative],capture_output=True,timeout=10,check=True)
assert hashlib.sha256(result.stdout).hexdigest()=='d99d1a60aa0e7f1a4c462cf440fb9c4ea84a8873ce2648535814da5dccedfec4','pinned relay bytes differ'
path=pathlib.Path(relative);path.parent.mkdir(parents=True,exist_ok=True)
if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()=='d99d1a60aa0e7f1a4c462cf440fb9c4ea84a8873ce2648535814da5dccedfec4','existing relay differs; preserve it'
else:
 with path.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3','-B',relative,'--packet-sha256','8639ec1bec42506b5fc8801b179703ce26a66862fddc57fe4fc97371354d4067'])
QUESTION_TOKEN_COUNT_MAC_BOOTSTRAP
```
