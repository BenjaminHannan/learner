BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 0
TIME CAP: 3 minutes
LABEL: sol-cloud-native-venv-lineage-v1
PUSH: artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r1/native-venv-lineage-v1

Read-only native interpreter and child parent-PID proof. Two bounded stdlib children and torch module specification only; no Torch import/model/optimizer/PCwrites/config changes.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 150 /usr/bin/python3 -B - <<'NATIVE_LINEAGE'
import json,pathlib,platform,subprocess,sys
assert platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6)
q=pathlib.Path('/Users/ben-hannan/premonition-watch/queue')
assert (q/'sol-cloud-exposure16-r5-s0-r1-benspc.exit').read_text().strip()=='rc=1' and not (q/'sol-cloud-exposure16-r5-s0-r1-benspc.running').exists()
source='import datetime,importlib.util,json,os,site,subprocess,sys\nchild="import importlib.util,json,os,sys; print(json.dumps({\'pid\':os.getpid(),\'ppid\':os.getppid(),\'executable\':sys.executable,\'version\':list(sys.version_info[:3]),\'torch_spec\':importlib.util.find_spec(\'torch\').origin}))"\nresult={\'schema\':\'sol.cloud.native-venv-lineage.v1\',\'observed_utc\':datetime.datetime.now(datetime.timezone.utc).isoformat(),\'collector_pid\':os.getpid(),\'venv_executable\':sys.executable,\'base_executable\':sys._base_executable,\'venv_sites\':site.getsitepackages(),\'model_calls\':0,\'optimizer_updates\':0,\'PC_writes\':0,\'children\':[]}\nenv=dict(os.environ,PYTHONPATH=os.pathsep.join(site.getsitepackages()),PYTHONDONTWRITEBYTECODE=\'1\')\nfor label,exe,environment in [(\'venv\',sys.executable,dict(os.environ,PYTHONDONTWRITEBYTECODE=\'1\')),(\'direct-base-with-existing-venv-sites\',sys._base_executable,env)]:\n r=subprocess.run([exe,\'-X\',\'utf8\',\'-B\',\'-c\',child],env=environment,capture_output=True,text=True,timeout=20)\n assert r.returncode==0 and len(r.stdout)<8192,\'bounded native lineage diagnostic failed\'\n record=json.loads(r.stdout);record.update(label=label,parent_matches_collector=record[\'ppid\']==os.getpid());result[\'children\'].append(record)\nprint(json.dumps(result,sort_keys=True),flush=True)\n'
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=10','benspc',r'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -B -'],input=source.encode(),capture_output=True,timeout=60)
assert r.returncode==0 and len(r.stdout)<32768,'bounded native diagnostic failed; raw diagnostics suppressed'
result=json.loads(r.stdout)
out=pathlib.Path('artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r1/native-venv-lineage-v1');out.mkdir(parents=True,exist_ok=False);(out/'NATIVE-LINEAGE.json').write_bytes(r.stdout)
print(json.dumps(result),flush=True)
NATIVE_LINEAGE
```
