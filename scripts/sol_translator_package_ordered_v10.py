#!/usr/bin/env python3
"""Seal runnable ordered joint HUMAN training+TRAIN diagnostic, no execution."""
import ast,hashlib,json,subprocess,tarfile,time,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'artifacts/sol-translator-20260929';REL=O.relative_to(ROOT)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build():
 if (O/'ORDERED-GROUND-V10-SEAL.json').exists():raise RuntimeError('new version required; preserve oldseal')
 coverage=O/'CONDITIONING-V9-PC.json'
 if sha(coverage)!='cd7b68ae1a656ea23b14cefe90da954378d89a5c120c0fbb440a38b91b1336bd':raise ValueError('actual coverage receipt changed')
 c=json.loads(coverage.read_text());assert len(c['rows_raw'])==512 and max(r['context_tokens'] for r in c['rows_raw'])==479
 warm={'stage':'actual immutable CLOSED500 V6parents/readers + CLOSED500 V7prefixes, not semantic qualification','per_seed':{}}
 for seed in (0,1):
  closed=O/f'frozen-parent-s{seed}';prefix=O/f'prefix-v7-s{seed}-d0-loop/English.pt';tr=O/f'prefix-v7-s{seed}-d0-loop/TRANSPORT-RESULT.json';ledger=json.loads(prefix.with_name('TRAIN-ledger.json').read_text());delivery=json.loads(tr.read_text());assert ledger['updates']==500 and ledger['closed'] and delivery['returncode']==0 and delivery['hashes']['English.pt']==sha(prefix)
  oldpc=f'C:/Users/benja/sol-translator-human-v6/artifacts/sol-translator-20260929/ground-v6-s{seed}'
  warm['per_seed'][str(seed)]={'source_path':oldpc+f'/parent-s{seed}.pt','source_sha256':sha(closed/f'parent-s{seed}.pt'),'reader_path':oldpc+f'/input-s{seed}.pt','reader_sha256':sha(closed/f'input-s{seed}.pt'),'prefix_path':f'C:/Users/benja/sol-translator-followup-v7/artifacts/sol-translator-20260929/prefix-v7-s{seed}-d0-loop/English.pt','prefix_sha256':sha(prefix),'prefix_closed_ledger_sha256':sha(prefix.with_name('TRAIN-ledger.json')),'prefix_closed_transport_sha256':sha(tr),'prior_grounding_updates':500,'prior_frozen_prefix_updates':500}
 (O/'ORDERED-GROUND-V10-WARMSTART.json').write_text(json.dumps(warm,indent=2)+'\n')
 spec={'stage':'ordered joint HUMAN final4 training; engineering, no semantic promotion','family':'loop','source_seeds':[0,1],'updates':500,'batch':2,'lr':.001,'weight_decay':.01,'clip_grad_norm':1,'rounds':4,'max_question':48,'max_context':512,'max_target':64,'wall_cap_seconds':2400,'cuda_cap_bytes':16*1024**3,'max_disk_bytes':512*1024**2,'disk_floor_bytes':2*1024**3,'queue_seconds':3950,'preflight_seconds':350,'TRAIN_child_seconds':2800,'TERM_grace_seconds':90,'TRAIN_diagnostic_seconds':450,'coverage_sha256':sha(coverage),'human_pairs_sha256':sha(O/'corpus/pairs.json'),'human_registry_sha256':sha(O/'corpus/registry.json'),'raw_human_training_sha256':sha(O/'corpus/train-v1.1.json'),'observed_TRAIN_context_max':479,'label_independent_full_context':'every TRAIN context<=479 tokens supplied with fixed512cap; no annotatedcrop/rowdrops','initialization':'actualclosedV6core+reader and actualclosedV7prefix warmstart; fresh joint AdamW','objective':'single final4 HUMAN shifted teacherforcing CE +mean8 physicalblock auxiliary; source learnedhalt unused','backend':'ownerordered_attention_math on nativecore ONLY, LMbackend untouched','raw':'IDs labels predictions masks source/tuple/codehashes actualgradnorms/work/ledgerwatermarks','overnight':'subsequentactualhumanexperience/replay coreoptimization is required engineering component; thisawakeTRAIN is not sleep','comparative_improvement':'deferred, no claim','fixed_stop':'fourroundengineeringfallback; learnedstopunqualified','DEV_examples':0,'stop88_consumed':False,'noise':'INSUFFICIENT for semanticpromotion; TRAINdiagnostic only; newfreshpaneloncewhenworthy','controls':'samejointprefix unmodified acrossloop/noState/alllexical+samepositionembedding/untrained/shuffled16predeclaredTRAIN inputs; separatelytrainedplainlater, notcapacitymatch','changes':'positions+fullcoverage+final4objective+warmedprefix jointlychanged; notsinglefactorcausalresearchproof'}
 rows=[r for r in json.loads((O/'corpus/pairs.json').read_text()) if r['split']=='train'];spec['TRAIN_schedule_sha256']={}
 for seed in (0,1):
  rng=random.Random(2026092970+seed);schedule=[[r['id'] for r in rng.sample(rows,2)] for _ in range(500)]
  exact=json.dumps(schedule,separators=(',',':'));spec['TRAIN_schedule_sha256'][str(seed)]=hashlib.sha256(exact.encode()).hexdigest()
  (O/f'ORDERED-GROUND-V10-TRAIN-SCHEDULE-s{seed}.json').write_text(exact)
 (O/'ORDERED-GROUND-V10-SPEC.json').write_text(json.dumps(spec,indent=2)+'\n')
 plan=json.loads((O/'DIAGNOSTIC-V7-PLAN.json').read_text());plan.update(stage='ordered closed joint TRAIN-only diagnostic, identical16predeclaredinputs',diagnostic_wall_seconds=400,notebook_cap=512,order_contract='sol-ordered-notebook-v2',prior_same_sample_plan_sha256=sha(O/'DIAGNOSTIC-V7-PLAN.json'),arms=['loop','no_state','embedding','untrained','shuffled_state'])
 (O/'ORDERED-GROUND-V10-DIAGNOSTIC-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
 base=json.loads((O/'FOLLOWUP-V7-SEAL.json').read_text())['files'];pins={k:v for k,v in base.items() if '/queue-' not in k}
 for k,v in pins.items():assert sha(ROOT/k)==v,'prior source modified '+k
 for p in (ROOT/'scripts').glob('sol_translator_*v10.py'):pins[str(p.relative_to(ROOT))]=sha(p)
 for n in ('sol_spatial_poc_ordered_v2.py','sol_spatial_poc_ordered_train_api_v2.py','sol_stop_ordered_api2.py'):
  p=ROOT/'scripts'/n;pins[str(p.relative_to(ROOT))]=sha(p)
 for n in ('CONDITIONING-V9-PC.json','ORDERED-GROUND-V10-WARMSTART.json','ORDERED-GROUND-V10-SPEC.json','ORDERED-GROUND-V10-DIAGNOSTIC-PLAN.json','ORDERED-GROUND-V10-CONTRACTS-r3.json','ORDERED-GROUND-V10-TRAIN-SCHEDULE-s0.json','ORDERED-GROUND-V10-TRAIN-SCHEDULE-s1.json'):
  p=O/n;pins[str(p.relative_to(ROOT))]=sha(p)
 for seed in (0,1):
  label=f'sol-translator-ordered-v10-s{seed}-pc';out=f'ground-ordered-v10-s{seed}-loop';diag=f'ordered-diagnostic-v10-s{seed}'
  q=f'''BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 66 minutes
LABEL: {label}

READY NEWordered HUMAN jointTRAIN500, full512context, final4CE/mean8aux. Actualwarmclosed500core/read+500frozenprefix exactbytes pinned; no semantic/sourceproof transfer. FP32 cachedLM reused/frozen, thinreader/core/prefix optimization.350s numericfull49query/512book/64target2rowgraph preflight noopt + actualnativeMATHparity MUSTPASS beforeTRAIN. 2GiBfloor512MiBnewoutputcap bothseeds; noLMcopies/downloads. Canonicalfinalquery only toEnglish, notebookinternal. NoDEV100/stop88/sleep work. Subsequentactualhumanexperience/replay nightlytraining required; engineeringgainproof deferred.3950wrapper bounded, same16predeclaredTRAINinputs×5 unchanged-adapter controls diagnostic. No hiddenbudgetcuts: partialweightsraw retained, no diagnostic on partialTRAIN.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 3950 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-translator-20260929
SOL_PC=C:/Users/benja/sol-translator-ordered-v10
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -' <<'PY'
from pathlib import Path
import shutil
r=Path('C:/Users/benja/sol-translator-ordered-v10');assert shutil.disk_usage('C:/').free>=2*1024**3,'DISK FLOOR';r.mkdir(exist_ok=True)
assert not (r/'artifacts/sol-translator-20260929/{out}/LAUNCH.json').exists(),'DUPLICATE: newexplicitresumejob required'
PY
scp "$SOL_ART/translator-ordered-v10-payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/ORDERED-GROUND-V10-PACKAGE.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -' <<'PY' 2>&1 | tee "$SOL_ART/{out}-PC.log"
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,os,sys,tarfile
r=Path('C:/Users/benja/sol-translator-ordered-v10');m=json.loads((r/'package.json').read_text())
assert hashlib.sha256((r/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256'],'PACKAGE HASH'
with tarfile.open(r/'payload.tar.gz') as t:
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts,'UNSAFE PACKAGE'
 t.extractall(r)
os.chdir(r);sys.path[:0]=[str(r),str(r/'scripts')]
from sol_translator_ordered_deploy_v10 import run
sys.exit(run(SimpleNamespace(root=str(r),seed={seed},job='{label}')))
PY
SOL_RC=${{PIPESTATUS[0]}}
set -e
scp benspc:"$SOL_PC/ordered-raw-s{seed}.tar.gz" "$SOL_ART/ordered-v10-s{seed}-raw.tar.gz" || true
if [ -f "$SOL_ART/ordered-v10-s{seed}-raw.tar.gz" ]; then tar -xzf "$SOL_ART/ordered-v10-s{seed}-raw.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model; fi
mkdir -p "$SOL_ART/ordered-v10-weights-s{seed}"
for SOL_NAME in parent-s{seed}.pt input-s{seed}.pt bootstrap-English-s{seed}.pt; do
 scp benspc:"$SOL_PC/$SOL_ART/{out}/$SOL_NAME" "$SOL_ART/ordered-v10-weights-s{seed}/$SOL_NAME" || true
done
printf '%s\\n' "$SOL_RC" > "$SOL_ART/{out}-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-translator-20260929/{out} artifacts/sol-translator-20260929/{diag} artifacts/sol-translator-20260929/{out}-PC.log artifacts/sol-translator-20260929/{out}-PC.exit
'''
  qp=O/f'queue-{label}.md';qp.write_text(q);check=subprocess.run(['bash','-n'],input=q.split('```bash\n')[1].split('```')[0],text=True,capture_output=True);assert check.returncode==0,check.stderr;pins[str(qp.relative_to(ROOT))]=sha(qp)
 for n in pins:
  if n.endswith('.py'):ast.parse((ROOT/n).read_text())
 seal={'sealed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'stage':'PRE-RUN neworderedjoint humanTRAIN2seeds, no semanticqualification','files':pins,'prerequisites':'cachedFP32LM + exactpreviousCLOSED core/reader/prefix + queuedactual512graph/PCnativeparity pass','fresh_panels_consumed':False,'optimizer_scope':'core/reader/prefix ONLY, frozenLM','source_proof_transfer':False}
 sp=O/'ORDERED-GROUND-V10-SEAL.json';sp.write_text(json.dumps(seal,indent=2)+'\n');payload=O/'translator-ordered-v10-payload.tar.gz'
 with tarfile.open(payload,'w:gz') as t:
  for n in sorted(pins):t.add(ROOT/n,arcname=n,recursive=False)
  t.add(sp,arcname=str(sp.relative_to(ROOT)),recursive=False)
 result={'sha256':sha(payload),'seal_sha256':sha(sp),'bytes':payload.stat().st_size,'pins':len(pins),'members':len(pins)+1,'no_LM_or_parent_binary_duplication':True};(O/'ORDERED-GROUND-V10-PACKAGE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':build()
