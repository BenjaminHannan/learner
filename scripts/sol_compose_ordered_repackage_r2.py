#!/usr/bin/env python3
"""Add one already-sealed import dependency; preserve original V10 experiment."""
from pathlib import Path
import ast,hashlib,io,json,os,subprocess,tarfile,tempfile,datetime
R=Path(__file__).resolve().parents[1];A=R/'artifacts/sol-compose-20260929';T=R/'artifacts/sol-translator-20260929'
D=lambda b:hashlib.sha256(b).hexdigest()
base=T/'translator-ordered-v10-payload.tar.gz'
assert D(base.read_bytes())=='b1585fd697b8a38882956a3f1fcb31c09ec99c84b80479401dadd263c50d8ace'
files={}
with tarfile.open(base) as t:
 for x in t.getmembers():
  assert x.isfile() and not Path(x.name).is_absolute() and '..' not in Path(x.name).parts
  assert x.name not in files;files[x.name]=t.extractfile(x).read()
plain='scripts/sol_spatial_poc_plain.py';assert plain not in files
files[plain]=(R/plain).read_bytes();assert D(files[plain])=='878de58d016d30912323664a240952b7221870f2070e21feeecee82079c12fef'
sealname='artifacts/sol-compose-20260929/sol_compose_ORDERED-V10R2-SEAL.json'
seal={'version':'V10 additive transport r2','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_payload_sha256':D(base.read_bytes()),'original_V10_seal_unchanged':'5946f8e94da4edb3182f04684a5420ab823e46328f3718393a11627d2082ca65','reason':'actual original seed0 import failure before CUDA/preflight/TRAIN: missing sol_spatial_poc_plain','added_dependency':plain,'changes':'only missing already-sealed import file plus newroot/jobs/results isolation; experiment source/data/budgets/marks unchanged','files':{n:D(b) for n,b in sorted(files.items())}}
sealbytes=(json.dumps(seal,indent=2)+'\n').encode();(R/sealname).write_bytes(sealbytes);files[sealname]=sealbytes
payload=A/'sol_compose_ordered-v10r2-payload.tar.gz'
with tarfile.open(payload,'w:gz') as t:
 for name,data in sorted(files.items()):
  ti=tarfile.TarInfo(name);ti.size=len(data);ti.mode=0o644;ti.mtime=0;t.addfile(ti,io.BytesIO(data))
package={'sha256':D(payload.read_bytes()),'bytes':payload.stat().st_size,'seal_sha256':D(sealbytes),'pins':len(seal['files']),'members':len(files),'base_experiment':'immutable ordered V10','no_existing_results_overwritten':True}
(A/'sol_compose_ORDERED-V10R2-PACKAGE.json').write_text(json.dumps(package,indent=2)+'\n')
# Import from the extracted archive in isolation, without model loading or fitting.
with tempfile.TemporaryDirectory(prefix='sol-compose-v10r2-import-') as temp:
 temp=Path(temp)
 for name,data in files.items():
  p=temp/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 cmd=['/Users/ben-hannan/.local/bin/uv','run','--offline','--no-project','--python','3.12','--with','torch','--with','numpy','python','-B','-c',"import sys;sys.path.insert(0,'scripts');import sol_translator_ground_ordered_v10,sol_translator_runtime_ordered_v10,sol_translator_diagnostic_ordered_v10,sol_translator_ordered_deploy_v10;print('4 archive-only imports PASS; no model, optimizer or inference')"]
 result=subprocess.run(cmd,cwd=temp,text=True,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),timeout=90)
 evidence={'command':cmd,'rc':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'model_loads':0,'optimizer_steps':0,'source_archive_sha256':package['sha256']}
 (A/'sol_compose_ORDERED-V10R2-IMPORT.json').write_text(json.dumps(evidence,indent=2)+'\n');print(result.stdout,result.stderr);assert result.returncode==0,'archive-only imports failed'
for seed in (0,1):
 text=(T/f'queue-sol-translator-ordered-v10-s{seed}-pc.md').read_text()
 text=text.replace('sol-translator-ordered-v10-s'+str(seed)+'-pc','sol-compose-ordered-v10r2-s'+str(seed)+'-pc')
 text=text.replace('C:/Users/benja/sol-translator-ordered-v10','C:/Users/benja/sol-translator-ordered-v10r2')
 text=text.replace('SOL_ART=artifacts/sol-translator-20260929','SOL_ART=artifacts/sol-translator-20260929\nSOL_OWN=artifacts/sol-compose-20260929\nSOL_COLLECT="$SOL_OWN/ordered-v10r2/seed'+str(seed)+'"\nmkdir -p "$SOL_COLLECT"')
 text=text.replace('"$SOL_ART/translator-ordered-v10-payload.tar.gz"','"$SOL_OWN/sol_compose_ordered-v10r2-payload.tar.gz"').replace('"$SOL_ART/ORDERED-GROUND-V10-PACKAGE.json"','"$SOL_OWN/sol_compose_ORDERED-V10R2-PACKAGE.json"')
 text=text.replace(f'"$SOL_ART/ground-ordered-v10-s{seed}-loop-PC.log"',f'"$SOL_OWN/ordered-v10r2-s{seed}-PC.log"').replace(f'"$SOL_ART/ground-ordered-v10-s{seed}-loop-PC.exit"',f'"$SOL_OWN/ordered-v10r2-s{seed}-PC.exit"')
 text=text.replace("os.chdir(r);sys.path[:0]", "seal=json.loads((r/'"+sealname+"').read_text())\nfor name,want in seal['files'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==want,'ADDITIVE PIN '+name\nos.chdir(r);sys.path[:0]")
 text=text.replace(f'"$SOL_ART/ordered-v10-s{seed}-raw.tar.gz"',f'"$SOL_OWN/ordered-v10r2-s{seed}-raw.tar.gz"').replace('-C /Users/ben-hannan/Desktop/projects/beautiful-model; fi','-C "$SOL_COLLECT"; fi')
 text=text.replace(f'"$SOL_ART/ordered-v10-weights-s{seed}"',f'"$SOL_OWN/ordered-v10r2-weights-s{seed}"').replace(f'"$SOL_ART/ordered-v10-weights-s{seed}/$SOL_NAME"',f'"$SOL_OWN/ordered-v10r2-weights-s{seed}/$SOL_NAME"')
 text=text.split('\nPUSH:')[0]+f'\nPUSH: artifacts/sol-compose-20260929/ordered-v10r2/seed{seed} artifacts/sol-compose-20260929/ordered-v10r2-s{seed}-PC.log artifacts/sol-compose-20260929/ordered-v10r2-s{seed}-PC.exit\n'
 text=text.replace('READY NEWordered','ADDITIVE r2 missing sealed plain import dependency; newroot/job/results, original failed V10 preserved. READY NEWordered')
 subprocess.run(['bash','-n'],input=text.split('```bash\n')[1].split('```')[0],text=True,check=True)
 for path in [A/f'queue-sol-compose-ordered-v10r2-s{seed}-pc.md',R/f'handoff/queue/sol-compose-ordered-v10r2-s{seed}-pc.md']:
  assert not path.exists();path.write_text(text)
print(json.dumps(package))
