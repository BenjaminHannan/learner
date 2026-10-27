BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 0
TIME CAP: 3 minutes
LABEL: sol-cloud-cached-lm-header-v3
PUSH: artifacts/sol-cloud-chat-delivery-20260930/cached-lm-header-v3

Read ONLY exact approved V6 frozen LM config and the exact cached weight header (physical path, size, prior provenance SHA). No tensor bytes, model/inference, launcher repeat, optimizer or PC writes. Old helper failures retained.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 150 /usr/bin/python3 -B - <<'CHAT_VERIFY'
import json,pathlib,platform,subprocess,sys
assert platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6)
q=pathlib.Path('/Users/ben-hannan/premonition-watch/queue');assert (q/'sol-cloud-chat-nosleep-v1-benspc.exit').read_text().strip()=='rc=0' and not (q/'sol-cloud-chat-nosleep-v1-benspc.running').exists()
out=pathlib.Path('artifacts/sol-cloud-chat-delivery-20260930/cached-lm-header-v3');out.mkdir(parents=True,exist_ok=False)
source="import datetime,hashlib,json,math,pathlib,struct,sys\nresult={'schema':'sol.cloud.cached-lm-header-count.v3','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':0,'model_calls':0,'optimizer_updates':0,'PC_writes_by_collector':0,'expected_full_weight_sha256_from_approved_provenance':'1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a','full_weight_bytes_read_or_rehashed':False,'existing_cache_policy':'scripts/sol_translator_cache_policy_v6.py exact logical/physical target; no shared-cache whitelist'}\nlm=pathlib.Path('C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b')\nconfig=lm/'config.json';assert config.stat().st_size<1048576;raw=config.read_bytes();assert hashlib.sha256(raw).hexdigest()=='15d6157fb6df3f8272e2fe90e18f57727ccf02a125c94469198b0f3281510185';result['LM_config']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'config':json.loads(raw)}\nnames=['model.safetensors']\nexpected_blob=pathlib.Path('C:/Users/benja/.cache/huggingface/hub/blobs/02/0223e4373a31a728f6e306f68fc58ad4b41e86054badb87928b7a491437a8b99')\nassert expected_blob.resolve()==expected_blob\nheaders=[];total=0\nfor name in names:\n path=lm/name;assert path.resolve()==expected_blob and path.is_file() and path.stat().st_size==2340697936\n with path.open('rb') as f:\n  first=f.read(8);assert len(first)==8;extent=struct.unpack('<Q',first)[0];assert extent<=16777216;raw=f.read(extent);assert len(raw)==extent\n header=json.loads(raw);elements=0;shapes=[]\n for key,v in header.items():\n  if key=='__metadata__':continue\n  shape=v['shape'];assert all(type(x)is int and x>=0 for x in shape);count=math.prod(shape);elements+=count;shapes.append({'name':key,'shape':shape,'dtype':v['dtype'],'numel':count})\n total+=elements;headers.append({'filename':name,'snapshot_path':str(path),'resolved_path':str(path.resolve()),'file_bytes':path.stat().st_size,'header_bytes':extent,'header_sha256':hashlib.sha256(raw).hexdigest(),'stored_tensor_elements':elements,'tensor_shapes':shapes})\nresult['LM_safetensors_headers']=headers;result['stored_tensor_elements_total']=total;result['count_scope']='Stored tensor elements from headers; not independently classified model parameters versus buffers or aliases. No weight tensor bytes read.'\nprint(json.dumps(result,sort_keys=True),flush=True)\n"
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=10','benspc',r'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -B -'],input=source.encode(),capture_output=True,timeout=70)
(out/'PC-stdout.log').write_bytes(r.stdout);(out/'PC-stderr.log').write_bytes(r.stderr)
assert r.returncode==0 and len(r.stdout)<3145728,'native read-only verification failed; exact streams preserved'
result=json.loads(r.stdout);(out/'RESULT.json').write_bytes(r.stdout);print(json.dumps(result),flush=True)
raise SystemExit(result['returncode'])CHAT_VERIFY
```
