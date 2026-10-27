BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 0
TIME CAP: 3 minutes
LABEL: sol-cloud-chat-launcher-verify-v1
PUSH: artifacts/sol-cloud-chat-delivery-20260930/launcher-verify-v1

Exact installed CHAT.cmd --verify-only (0 model/optimizer), plus existing LM config and safetensors shape headers only. No tensor bytes, PC source writes, training or model rescore.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 150 /usr/bin/python3 -B - <<'CHAT_VERIFY'
import json,pathlib,platform,subprocess,sys
assert platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6)
q=pathlib.Path('/Users/ben-hannan/premonition-watch/queue');assert (q/'sol-cloud-chat-nosleep-v1-benspc.exit').read_text().strip()=='rc=0' and not (q/'sol-cloud-chat-nosleep-v1-benspc.running').exists()
out=pathlib.Path('artifacts/sol-cloud-chat-delivery-20260930/launcher-verify-v1');out.mkdir(parents=True,exist_ok=False)
source="import datetime,hashlib,json,math,pathlib,struct,subprocess,sys\nroot=pathlib.Path('C:/Users/benja/sol-cloud-chat-delivery-v1');cmd=root/'CHAT.cmd';cli=root/'scripts/sol_cloud_chat_nosleep_v1.py'\nsha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()\nassert sha(cmd)=='d71a9d313581f60522b55bfee0aed4871f992052cf83edf7bce3d8a9542b498b' and sha(cli)=='efd48a179488808fd1b7839c91a57f3bd03117d8f6ae175f5ec9f0c9accdba1a'\nr=subprocess.run(['cmd','/d','/c',str(cmd),'--verify-only'],capture_output=True,timeout=40)\nassert len(r.stdout)<65536 and len(r.stderr)<65536\nresult={'schema':'sol.cloud.chat.installed-launcher-verify.v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':r.returncode,'stdout':r.stdout.decode('utf8'),'stderr':r.stderr.decode('utf8'),'launcher_sha256':sha(cmd),'CLI_sha256':sha(cli),'model_calls':0,'optimizer_updates':0,'PC_writes_by_collector':0}\nlm=pathlib.Path('C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b')\nconfig=lm/'config.json';assert config.stat().st_size<1048576;raw=config.read_bytes();result['LM_config']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'config':json.loads(raw)}\nindex=lm/'model.safetensors.index.json'\nif index.is_file():\n assert index.stat().st_size<1048576;names=sorted(set(json.loads(index.read_bytes())['weight_map'].values()))\nelse:names=[p.name for p in sorted(lm.glob('*.safetensors'))]\nassert 0<len(names)<=16\nheaders=[];total=0\nfor name in names:\n path=lm/name;assert path.resolve().parent==lm.resolve() and path.is_file()\n with path.open('rb') as f:\n  first=f.read(8);assert len(first)==8;extent=struct.unpack('<Q',first)[0];assert extent<=16777216;raw=f.read(extent);assert len(raw)==extent\n header=json.loads(raw);elements=0;shapes=[]\n for key,v in header.items():\n  if key=='__metadata__':continue\n  shape=v['shape'];assert all(type(x)is int and x>=0 for x in shape);count=math.prod(shape);elements+=count;shapes.append({'name':key,'shape':shape,'dtype':v['dtype'],'numel':count})\n total+=elements;headers.append({'filename':name,'file_bytes':path.stat().st_size,'header_bytes':extent,'header_sha256':hashlib.sha256(raw).hexdigest(),'stored_tensor_elements':elements,'tensor_shapes':shapes})\nresult['LM_safetensors_headers']=headers;result['stored_tensor_elements_total']=total;result['count_scope']='Stored tensor elements from headers; not independently classified model parameters versus buffers or aliases. No weight tensor bytes read.'\nprint(json.dumps(result,sort_keys=True),flush=True)\n"
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=10','benspc',r'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -B -'],input=source.encode(),capture_output=True,timeout=70)
(out/'PC-stdout.log').write_bytes(r.stdout);(out/'PC-stderr.log').write_bytes(r.stderr)
assert r.returncode==0 and len(r.stdout)<3145728,'native read-only verification failed; exact streams preserved'
result=json.loads(r.stdout);(out/'RESULT.json').write_bytes(r.stdout);print(json.dumps(result),flush=True)
raise SystemExit(result['returncode'])
CHAT_VERIFY
```
