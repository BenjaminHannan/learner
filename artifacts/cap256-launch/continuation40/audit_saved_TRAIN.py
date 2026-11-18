import pathlib,json,hashlib,collections,statistics,itertools,math
P=pathlib.Path('/tmp/cap256-train-audit'); manifest=json.loads((P/'HASHES.json').read_text())
for m in manifest:
 b=(P/m['path']).read_bytes();assert len(b)==m['bytes'];assert hashlib.sha256(b).hexdigest()==m['sha256']
report={'hashes_verified':12,'sources':manifest,'arms':{},'cross_arm_frames_aligned':True}
ref=None
for seed,arm in itertools.product([0,1],['loop','plain']):
 name=f'{arm}{seed}';base=P/f'seed{seed}'/arm
 frames=json.loads((base/'INPUT-FRAMES.json').read_text());F={x['id']:x for x in frames['rows']};assert len(F)==256 and not frames['truncation']
 for f in F.values():
  v={k:x for k,x in f.items() if k!='frame_sha256'};assert hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()==f['frame_sha256']
  assert f['label_mask']==[[x!=-100 for x in row] for row in f['labels']]
 if ref is None:ref=F
 assert F==ref
 D=collections.defaultdict(dict);T=collections.defaultdict(list)
 for fname in ['TRAIN-RAW.jsonl','DIAGNOSTIC-RAW.jsonl']:
  rows=[json.loads(x) for x in (base/fname).read_text().splitlines()];assert len(rows)==(5120 if fname.startswith('TRAIN') else 768)
  if fname.startswith('TRAIN'):assert [r['update'] for r in rows]==list(range(1,5121))
  for r in rows:
   f=F[r['id']];assert r['labels']==f['labels'] and r['label_mask']==f['label_mask'];assert r['input_frame_sha256']==f['frame_sha256'] and r['source_question_sha256']==f['question_sha256'];assert r['seed']==seed and r['arm']==arm and math.isfinite(r['numeric_CE'])
   if fname.startswith('TRAIN'):T[r['id']].append(r['visit_for_row']);assert r['objective']=='numeric-answer-CE-only' and r['auxiliary_weight']==0
   else:
    assert r['update'] in [768,2560,5120] and r['id'] not in D[r['update']]
    assert r['canonical_target_ids_with_EOS']==f['labels'][0] and r['expected_answer_ids_without_EOS']==f['labels'][0][:-1] and r['canonical_numeric_target']==f['canonical_numeric_target']
    eos=r['native_generation_options']['eos_token_id'];assert f['labels'][0][-1]==eos and f['labels'][0].count(eos)==1
    full=r['MODEL_raw_generate_ids'][0];assert r['MODEL_raw_generate_ids']==[full] and full==r['MODEL_generated_ids_with_observed_EOS'];assert all(type(x) is int and x>=0 for x in full)
    positions=[j for j,x in enumerate(full) if x==eos];assert positions==r['EOS_positions'] and bool(positions)==r['observed_EOS']
    stripped=full[:positions[0]] if positions else full;assert (r['MODEL_native_decoder_return']==[stripped])==r['native_stripped_output_equal']
    assert r['native_call_contract_valid'] and r['native_generate_call_count']==1 and not r['generation_error'] and len(full)<=32
    reason='observed_EOS' if positions else ('max_new_tokens_without_EOS' if len(full)==32 else 'terminated_without_observed_EOS')
    if positions:assert positions==[len(full)-1]
    assert reason==r['termination_reason']
    strict=r['termination_reason']=='observed_EOS' and r['native_stripped_output_equal'] is True and r['MODEL_generated_ids_with_observed_EOS']==f['labels'][0]
    assert strict==r['target_ids_plus_observed_EOS_exact'];r['_strict']=strict
    assert len(r['teacherforced_argmax'])==len(r['labels'])==len(r['label_mask']);assert all(len(p)==len(l)==len(m) for p,l,m in zip(r['teacherforced_argmax'],r['labels'],r['label_mask']))
    r['_tf']=all(p==l for preds,labels,masks in zip(r['teacherforced_argmax'],r['labels'],r['label_mask']) for p,l,m in zip(preds,labels,masks) if m)
    D[r['update']][r['id']]=r
 assert all(sorted(x)==list(range(1,21)) for x in T.values()) and len(T)==256
 assert all(set(x)==set(F) for x in D.values())
 visits=[768,2560,5120];C=collections.Counter(''.join(str(int(D[u][i]['_strict'])) for u in visits) for i in F)
 transitions=[]
 for u,v in zip(visits,visits[1:]):
  transitions.append({'losses':sum(D[u][i]['_strict'] and not D[v][i]['_strict'] for i in F),'acquisitions':sum(not D[u][i]['_strict'] and D[v][i]['_strict'] for i in F)})
 finalerr=[i for i in F if not D[5120][i]['_strict']];prev=sum(D[768][i]['_strict'] or D[2560][i]['_strict'] for i in finalerr)
 def ce_stats(ids):
  means=[statistics.mean(D[u][i]['numeric_CE'] for i in ids) for u in visits]
  return {'n':len(ids),'correct':[sum(D[u][i]['_strict'] for i in ids) for u in visits],'CE_means':means,'CE_delta_3_20':means[2]-means[0],'CE_increased_3_10':sum(D[2560][i]['numeric_CE']>D[768][i]['numeric_CE'] for i in ids),'CE_increased_10_20':sum(D[5120][i]['numeric_CE']>D[2560][i]['numeric_CE'] for i in ids)}
 lengths=collections.defaultdict(list);digits=collections.defaultdict(list)
 for i,f in F.items():
  lengths[sum(sum(row) for row in f['label_mask'])].append(i)
  target=f['canonical_numeric_target'];assert isinstance(target,str)
  digits[sum(c.isdigit() for c in target)].append(i)
 report['arms'][name]={'trajectories':{x:C[x] for x in ['000','001','010','011','100','101','110','111']},'transitions':transitions,'final_errors':len(finalerr),'final_errors_previously_correct':prev,'final_errors_never_observed_correct':len(finalerr)-prev,'ever_correct':256-C['000'],'dominant_observed_retention':prev>=len(finalerr)/2,'TF_gen_disagreement':[sum(D[u][i]['_strict']!=D[u][i]['_tf'] for i in F) for u in visits],'termination_counts':[dict(collections.Counter(D[u][i]['termination_reason'] for i in F)) for u in visits],'all_items_CE':ce_stats(list(F)),'supervised_token_length_including_EOS':{k:ce_stats(v) for k,v in sorted(lengths.items())},'numeric_digit_count':{k:ce_stats(v) for k,v in sorted(digits.items())},'alignment_pass':True}
(P/'AUDIT-RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='sources'},indent=2))
