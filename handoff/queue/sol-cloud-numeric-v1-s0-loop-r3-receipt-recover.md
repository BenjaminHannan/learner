BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 2 minutes
LABEL: sol-cloud-numeric-v1-s0-loop-r3-receipt-recover
PUSH: artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v2/execution-r3-s0-loop

Read-only receipt salvage for the already closed r3 s0-loop job. Do not invoke any model, training driver, optimizer, SSH, deletion, or write to the source execution directory. Verify exact PC final manifest, transport exit, copied raw/checkpoint metadata, and list optimizer updates/timing from saved raw/CLOSED if present. PUSH is the already-existing exact source directory because the original launcher wrote under mac-launch-v2; preserve all source bytes.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
/usr/bin/python3 -B - <<'RECOVER_SAVED_R3_RECEIPT'
import hashlib,json,pathlib
base=pathlib.Path('artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v2/execution-r3-s0-loop')
assert base.is_dir() and not base.is_symlink(), 'exact saved s0-loop r3 receipt directory absent'
def read_json(path):
    assert path.is_file() and not path.is_symlink(), 'required saved receipt missing: '+str(path)
    return json.loads(path.read_bytes())
final=read_json(base/'PC-FINAL-MANIFEST.json')
assert final.get('schema')=='sol.cloud.numeric-fit.transport.v1'
assert final.get('job')=='sol-cloud-numeric-v1-s0-loop-r3-benspc' and final.get('seed')==0 and final.get('arm')=='loop'
ssh=read_json(base/'PC-SSH-EXIT.json')
assert ssh.get('returncode')==final.get('returncode') and ssh.get('timed_out') is False
small=read_json(base/'SMALL-RETURN.json')
assert small.get('schema')=='sol.cloud.numeric.small-return.v1' and small.get('job')==final['job']
updates=[];closed=[];verified=[]
for item in small['records']:
    rel=pathlib.PurePosixPath(item['relative'])
    assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in item['relative'] and ':' not in item['relative']
    path=base/'copied'/pathlib.Path(*rel.parts)
    assert path.is_file() and not path.is_symlink(), 'saved exact copied member absent: '+item['relative']
    data=path.read_bytes(); assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
    verified.append({'relative':item['relative'],'bytes':len(data),'sha256':item['sha256']})
    if rel.name=='TRAIN-RAW.jsonl':
        for line in data.splitlines():
            row=json.loads(line); updates.append(row.get('update'))
    if rel.name=='CLOSED.json': closed.append(json.loads(data))
result={'job':final['job'],'pc_returncode':final['returncode'],'timed_out':ssh['timed_out'],
        'manifest_records':final.get('records',[]),'verified_small_return_records':verified,
        'raw_update_rows':len(updates),'first_update':updates[0] if updates else None,
        'last_update':updates[-1] if updates else None,'closed_records':closed,
        'actual_user_day':False,'activated':False,'source_modified':False}
print(json.dumps(result,sort_keys=True),flush=True)
RECOVER_SAVED_R3_RECEIPT
```
