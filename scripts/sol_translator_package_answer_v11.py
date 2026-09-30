#!/usr/bin/env python3
"""Seal runnable ordered joint HUMAN training+TRAIN diagnostic, no execution."""
import ast,hashlib,json,subprocess,tarfile,time,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'artifacts/sol-translator-20260929';REL=O.relative_to(ROOT)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build():
 if (O/'ANSWER-V11-SEAL.json').exists():raise RuntimeError('new version required; preserve oldseal')
 coverage=O/'CONDITIONING-V9-PC.json'
 if sha(coverage)!='cd7b68ae1a656ea23b14cefe90da954378d89a5c120c0fbb440a38b91b1336bd':raise ValueError('actual coverage receipt changed')
 c=json.loads(coverage.read_text());assert len(c['rows_raw'])==512 and max(r['context_tokens'] for r in c['rows_raw'])==479
 warm={'stage':'actual immutable CLOSED500 V6parents/readers + CLOSED500 V7prefixes, not semantic qualification','per_seed':{}}
 for seed in (0,1):
  closed=O/f'frozen-parent-s{seed}';prefix=O/f'prefix-v7-s{seed}-d0-loop/English.pt';tr=O/f'prefix-v7-s{seed}-d0-loop/TRANSPORT-RESULT.json';ledger=json.loads(prefix.with_name('TRAIN-ledger.json').read_text());delivery=json.loads(tr.read_text());assert ledger['updates']==500 and ledger['closed'] and delivery['returncode']==0 and delivery['hashes']['English.pt']==sha(prefix)
  oldpc=f'C:/Users/benja/sol-translator-human-v6/artifacts/sol-translator-20260929/ground-v6-s{seed}'
  warm['per_seed'][str(seed)]={'source_path':oldpc+f'/parent-s{seed}.pt','source_sha256':sha(closed/f'parent-s{seed}.pt'),'reader_path':oldpc+f'/input-s{seed}.pt','reader_sha256':sha(closed/f'input-s{seed}.pt'),'prefix_path':f'C:/Users/benja/sol-translator-followup-v7/artifacts/sol-translator-20260929/prefix-v7-s{seed}-d0-loop/English.pt','prefix_sha256':sha(prefix),'prefix_closed_ledger_sha256':sha(prefix.with_name('TRAIN-ledger.json')),'prefix_closed_transport_sha256':sha(tr),'prior_grounding_updates':500,'prior_frozen_prefix_updates':500}
 (O/'ANSWER-V11-WARMSTART.json').write_text(json.dumps(warm,indent=2)+'\n')
 spec={'stage':'HUMAN answer annotation joint final4 pilot; shortspan not grammatical chat','family':'loop','source_seeds':[0,1],'updates':200,'batch':2,'lr':.001,'weight_decay':.01,'clip_grad_norm':1,'rounds':4,'max_question':48,'max_context':512,'max_target':64,'wall_cap_seconds':600,'cuda_cap_bytes':16*1024**3,'max_disk_bytes':512*1024**2,'disk_floor_bytes':1536*1024**2+16*1024**2,'retained_free_bytes':1024**3,'queue_seconds':1800,'preflight_seconds':350,'TRAIN_child_seconds':800,'TERM_grace_seconds':90,'TRAIN_diagnostic_seconds':450,'coverage_sha256':sha(coverage),'human_pairs_sha256':sha(O/'corpus/pairs.json'),'human_registry_sha256':sha(O/'corpus/registry.json'),'raw_human_training_sha256':sha(O/'corpus/train-v1.1.json'),'observed_TRAIN_context_max':479,'label_independent_full_context':'every TRAIN context<=479 tokens supplied with fixed512cap; no annotatedcrop/rowdrops','initialization':'actualclosedV6core+reader and actualclosedV7prefix warmstart; fresh joint AdamW','objective':'verbatim official HUMAN answer_text+EOS shifted teacherforcing final4CE+mean8aux; shortspan engineeringpartial, not grammatical conversation','target_change':'support sentence -> human answer annotation; balanced shared-context distinct-answer pairs; no span head, oracle input, external solver or generated targets','controls_limit':'unchanged-head interventions, not separately trained matched-budget controls; no scientific promotion','backend':'ownerordered_attention_math on nativecore ONLY, LMbackend untouched','raw':'IDs labels predictions masks source/tuple/codehashes actualgradnorms/work/ledgerwatermarks','overnight':'subsequentactualhumanexperience/replay coreoptimization is required engineering component; thisawakeTRAIN is not sleep','comparative_improvement':'deferred, no claim','fixed_stop':'fourroundengineeringfallback; learnedstopunqualified','DEV_examples':0,'stop88_consumed':False,'noise':'INSUFFICIENT for semanticpromotion; TRAINdiagnostic only; newfreshpaneloncewhenworthy','controls':'samejointprefix unmodified acrossloop/noState/alllexical+samepositionembedding/untrained/shuffled16predeclaredTRAIN inputs; separatelytrainedplainlater, notcapacitymatch','changes':'answer annotation objective plus paired sampling; same symmetric V6/V7 warmstarts as originalV10, not ordered seed0 warmstart; not isolated objective causalproof'}
 rows=[r for r in json.loads((O/'corpus/pairs.json').read_text()) if r['split']=='train'];spec['TRAIN_schedule_sha256']={}
 raw=json.loads((O/'corpus/train-v1.1.json').read_text());official={q['id']:(q,p['context']) for article in raw['data'] for p in article['paragraphs'] for q in p['qas']}
 annotations=[];groups={}
 for row in rows:
  q,context=official[row['id']];accepted=sorted(set(x['text'] for x in q['answers']))
  assert row['answer_text'] in accepted and row['question']==q['question'] and row['context']==context
  assert all(context[a['answer_start']:a['answer_start']+len(a['text'])]==a['text'] for a in q['answers'])
  ctx=hashlib.sha256(context.encode()).hexdigest();annotations.append({'id':row['id'],'answer_text':row['answer_text'],'accepted_human_answers':accepted,'official_answer_offsets':q['answers'],'context_sha256':ctx,'question_sha256':hashlib.sha256(q['question'].encode()).hexdigest()})
  groups.setdefault(ctx,[]).append(row['id'])
 amap={r['id']:r for r in annotations};eligible=[]
 for ctx,ids in groups.items():
  pairs=[[a,b] for i,a in enumerate(ids) for b in ids[i+1:] if not {x.casefold().strip() for x in amap[a]['accepted_human_answers']} & {x.casefold().strip() for x in amap[b]['accepted_human_answers']}]
  if pairs:eligible.append((ctx,pairs))
 diagnostic_pairs=[pairs[0] for ctx,pairs in eligible[:8]];diagnostic_ids=[i for pair in diagnostic_pairs for i in pair]
 ann={'stage':'PRE-RUN official HUMAN TRAIN answer-annotation binding; no model text','official_train_sha256':sha(O/'corpus/train-v1.1.json'),'pairs_sha256':sha(O/'corpus/pairs.json'),'license':'CC-BY-SA-4.0','source_url':'https://rajpurkar.github.io/SQuAD-explorer/dataset/train-v1.1.json','rows':annotations}
 (O/'ANSWER-V11-ANNOTATIONS.json').write_text(json.dumps(ann,indent=2,ensure_ascii=False)+'\n');spec['annotation_manifest_sha256']=sha(O/'ANSWER-V11-ANNOTATIONS.json');spec['paired_context_groups']=len(eligible);spec['sampling']='First8 fixed diagnostic pairs, then uniform eligible context and uniform disjoint accepted-answer pair; seed-specific swap/order; repeats allowed; unmatched TRAINrows not selected by this paired pilot, no inference annotation routing'
 byid={r['id']:r for r in rows};shared=sum(byid[a]['target_text']==byid[b]['target_text'] for _,pairs in eligible for a,b in pairs);total=sum(len(pairs) for _,pairs in eligible)
 (O/'ANSWER-V11-TARGET-AUDIT.json').write_text(json.dumps({'TRAIN_rows':len(rows),'same_context_distinct_answer_pairs':total,'pairs_with_identical_old_evidence_target':shared,'eligible_context_groups':len(eligible),'inference_calls':0,'optimizer_steps':0,'interpretation':'Shared evidence targets supply identical continuation labels for distinct questions. This is a plausible training shortcut, not proof of sole cause of collapse.','raw_human_sha256':ann['official_train_sha256']},indent=2)+'\n')
 for seed in (0,1):
  rng=random.Random(2026092970+seed);schedule=[list(pair) for pair in diagnostic_pairs]
  for _ in range(200-len(schedule)):
   ctx,pairs=rng.choice(eligible);pair=list(rng.choice(pairs));rng.shuffle(pair);schedule.append(pair)
  exact=json.dumps(schedule,separators=(',',':'));spec['TRAIN_schedule_sha256'][str(seed)]=hashlib.sha256(exact.encode()).hexdigest()
  (O/f'ANSWER-V11-TRAIN-SCHEDULE-s{seed}.json').write_text(exact)
 (O/'ANSWER-V11-SPEC.json').write_text(json.dumps(spec,indent=2)+'\n')
 plan={'stage':'predeclared reused TRAIN development contrasts, no fresh proof','training_updates':200,'TRAIN_diagnostic_examples':len(diagnostic_ids),'TRAIN_diagnostic_ids':diagnostic_ids,'same_context_pairs':diagnostic_pairs,'arms':['loop','no_state','embedding','no_notebook','untrained','shuffled_state'],'diagnostic_wall_seconds':400,'notebook_cap':512,'annotation_manifest_sha256':spec['annotation_manifest_sha256'],'pass_line':'No scientific promotion; descriptive exact raw only. A useful engineering direction requires question-specific relevant answer changes on paired questions and deterioration under notebook/state interventions; manual examples cannot establish generalization.','noise':'INSUFFICIENT; three identical first-input repeats estimate determinism only','fresh_DEV':0,'grammar_limit':'Verbatim short annotations are not full grammatical sentences; this pilot addresses grounding, not complete chat.'}
 (O/'ANSWER-V11-DIAGNOSTIC-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
 base=json.loads((O/'ORDERED-GROUND-V10-SEAL.json').read_text())['files'];pins={k:v for k,v in base.items() if '/queue-' not in k}
 for k,v in pins.items():assert sha(ROOT/k)==v,'prior source modified '+k
 for p in (ROOT/'scripts').glob('sol_translator_*v11.py'):pins[str(p.relative_to(ROOT))]=sha(p)
 for n in ('sol_spatial_poc_ordered_v2.py','sol_spatial_poc_ordered_train_api_v2.py','sol_stop_ordered_api2.py','sol_spatial_poc_plain.py'):
  p=ROOT/'scripts'/n;pins[str(p.relative_to(ROOT))]=sha(p)
 for n in ('CONDITIONING-V9-PC.json','ANSWER-V11-WARMSTART.json','ANSWER-V11-SPEC.json','ANSWER-V11-DIAGNOSTIC-PLAN.json','ANSWER-V11-ANNOTATIONS.json','ANSWER-V11-TARGET-AUDIT.json','ANSWER-V11-TRAIN-SCHEDULE-s0.json','ANSWER-V11-TRAIN-SCHEDULE-s1.json'):
  p=O/n;pins[str(p.relative_to(ROOT))]=sha(p)
 for seed in (0,1):
  label=f'sol-translator-answer-v11-s{seed}-pc';out=f'ground-answer-v11-s{seed}-loop';diag=f'answer-diagnostic-v11-s{seed}'
  q=f'''BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 30 minutes
LABEL: {label}

READY NEWordered HUMAN jointTRAIN200, full512context, final4CE/mean8aux. Actualwarmclosed500core/read+500frozenprefix exactbytes pinned; no semantic/sourceproof transfer. FP32 cachedLM reused/frozen, thinreader/core/prefix optimization.350s numericfull49query/512book/64target2rowgraph preflight noopt + actualnativeMATHparity MUSTPASS beforeTRAIN. 1GiBretainedreserve+512MiBaggregate+16MiBpackagefloor;512MiBnewoutputcap bothseeds; noLMcopies/downloads. Canonicalfinalquery only toEnglish, notebookinternal. NoDEV100/stop88/sleep work. Subsequentactualhumanexperience/replay nightlytraining required; engineeringgainproof deferred.1800wrapper bounded, 16predeclaredsharedcontextTRAINinputs×6 unchanged-adapter controls diagnostic. No hiddenbudgetcuts: partialweightsraw retained, no diagnostic on partialTRAIN.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 1800 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-translator-20260929
SOL_PC=C:/Users/benja/sol-translator-answer-v11
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -' <<'PY'
from pathlib import Path
import shutil
r=Path('C:/Users/benja/sol-translator-answer-v11');assert shutil.disk_usage('C:/').free>=(1536+16)*1024**2,'DISK FLOOR';r.mkdir(exist_ok=True)
assert not (r/'artifacts/sol-translator-20260929/{out}/LAUNCH.json').exists(),'DUPLICATE: newexplicitresumejob required'
PY
scp "$SOL_ART/translator-answer-v11-payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/ANSWER-V11-PACKAGE.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -' <<'PY' 2>&1 | tee "$SOL_ART/{out}-PC.log"
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,os,sys,tarfile
r=Path('C:/Users/benja/sol-translator-answer-v11');m=json.loads((r/'package.json').read_text())
assert hashlib.sha256((r/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256'],'PACKAGE HASH'
with tarfile.open(r/'payload.tar.gz') as t:
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts,'UNSAFE PACKAGE'
 t.extractall(r)
os.chdir(r);sys.path[:0]=[str(r),str(r/'scripts')]
from sol_translator_answer_deploy_v11 import run
sys.exit(run(SimpleNamespace(root=str(r),seed={seed},job='{label}')))
PY
SOL_RC=${{PIPESTATUS[0]}}
set -e
scp benspc:"$SOL_PC/answer-raw-s{seed}.tar.gz" "$SOL_ART/answer-v11-s{seed}-raw.tar.gz" || true
if [ -f "$SOL_ART/answer-v11-s{seed}-raw.tar.gz" ]; then tar -xzf "$SOL_ART/answer-v11-s{seed}-raw.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model; fi
mkdir -p "$SOL_ART/answer-v11-weights-s{seed}"
for SOL_NAME in parent-s{seed}.pt input-s{seed}.pt bootstrap-English-s{seed}.pt; do
 scp benspc:"$SOL_PC/$SOL_ART/{out}/$SOL_NAME" "$SOL_ART/answer-v11-weights-s{seed}/$SOL_NAME" || true
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
 sp=O/'ANSWER-V11-SEAL.json';sp.write_text(json.dumps(seal,indent=2)+'\n');payload=O/'translator-answer-v11-payload.tar.gz'
 with tarfile.open(payload,'w:gz') as t:
  for n in sorted(pins):t.add(ROOT/n,arcname=n,recursive=False)
  t.add(sp,arcname=str(sp.relative_to(ROOT)),recursive=False)
 result={'sha256':sha(payload),'seal_sha256':sha(sp),'bytes':payload.stat().st_size,'pins':len(pins),'members':len(pins)+1,'no_LM_or_parent_binary_duplication':True};(O/'ANSWER-V11-PACKAGE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':build()
