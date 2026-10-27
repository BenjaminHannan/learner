"""Independent tensor-only recount. No author/model imports or model execution."""
import json,hashlib
from pathlib import Path
import torch
R=Path(__file__).resolve().parents[1]
B=R/'artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1'
C=B/'collected-awake-s0/artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1'
O=R/'artifacts/sol-spatial-20260929/STOP-R2-S0-RAW-RECOUNT.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
pkg=json.loads((B/'PACKAGE.json').read_text());tu=json.loads((B/'TUPLE-s0.json').read_text());receipt=json.loads((C/'actual-awake-s0/receipt.json').read_text())
checks={};records=[]
for path,h in pkg['source_pins'].items():checks['source_bytes:'+path]=sha(R/path)==h
for seed in (0,1):
 p=C/f'actual-awake-s0/raw-probe-{seed}.pt';raw=torch.load(p,map_location='cpu',weights_only=True)
 rec=next(x for x in receipt['records'] if x['probe_seed']==seed)
 c={};q=raw['query_mask'];m=raw['notebook_mask'];qn=int(q.sum());mn=int(m.sum());ident=raw['identity']
 c['lexical_shape_dtype']=all(raw[k].dtype==torch.float32 and tuple(raw[k].shape)==shape for k,shape in [('numeric_lexical_query',(1,49,2048)),('numeric_lexical_book',(1,512,2048))])
 c['projected_shape_dtype']=all(raw[k].dtype==torch.float32 and tuple(raw[k].shape)==shape for k,shape in [('projected_query',(1,49,256)),('projected_book',(1,512,256))])
 c['prefix_masks']=q.dtype==m.dtype==torch.bool and tuple(q.shape)==(1,49) and tuple(m.shape)==(1,512) and torch.equal(q,torch.arange(49)[None]<qn) and torch.equal(m,torch.arange(512)[None]<mn)
 c['raw_sha']=sha(p)==rec['raw_sha256'] if 'raw_sha256' in rec else sha(p)==rec['raw_probe_sha256']
 numeric=digest(raw['numeric_lexical_query'].numpy().tobytes()+raw['numeric_lexical_book'].numpy().tobytes())
 c['numeric_binding']=numeric==ident['numeric_input_sha256']==rec['input_identity_sha256']
 bound=digest(json.dumps(ident,sort_keys=True,separators=(',',':')).encode())
 c['identity_binding']=bound==raw['bound_identity_sha256']==rec['bound_identity_sha256']
 c['tuple_declarations']=ident['component_sha256']=={k:v['sha256'] for k,v in tu.items()}
 c['spec_bytes']=ident['spec_sha256']==sha(C/'binding-s0.json')
 deps=ident['dependency_pins'];c['dependency_digests']=len(deps)==len(pkg['source_pins']) and all(any(k.replace('\\','/').endswith('/'+path) and v==h for k,v in deps.items()) for path,h in pkg['source_pins'].items())
 c['native_runtime_begin']=raw['native_begin'].keys()==raw['runtime_begin'].keys() and all(torch.equal(v,raw['runtime_begin'][k]) for k,v in raw['native_begin'].items())
 begin=raw['native_begin'];c['begin_geometry']=tuple(begin['h'].shape)==tuple(begin['e'].shape)==(1,qn+mn,256) and tuple(begin['input_valid'].shape)==(1,qn+mn) and bool(begin['input_valid'].all())
 c['position_prefix_preserved']=all(torch.equal(begin[k+'_absolute_positions'],raw[k+'_positions'][:,:n]) for k,n in [('query',qn),('notebook',mn)])
 deltas={k:float((raw[k]-raw['native_final']).abs().max()) for k in ('runtime_final','repeat_final','trimmed_final','permuted_final')}
 for k in ('runtime_final','repeat_final','trimmed_final'):c[k+'_exact']=torch.equal(raw[k],raw['native_final'])
 c['query_only_final_shapes']=all(tuple(raw[k].shape)==(1,qn,256) and raw[k].dtype==torch.float32 for k in ('native_final','runtime_final','repeat_final','trimmed_final','permuted_final'))
 c['final_masks']=raw['final_answer_mask'].dtype==raw['final_latent_mask'].dtype==torch.bool and tuple(raw['final_answer_mask'].shape)==(1,qn) and tuple(raw['final_latent_mask'].shape)==(1,qn,256) and bool(raw['final_answer_mask'].all()) and bool(raw['final_latent_mask'].all())
 c['prefix_geometry_finite']=tuple(raw['prefix_output'].shape)==(1,8,2048) and bool(torch.isfinite(raw['prefix_output']).all())
 c['persisted_round4']=raw['rounds'].tolist()==[4]
 c['no_labels']=raw['labels'] is None
 c['row_id']=raw['row_id']==ident['row_id']==rec['row_id']==f'numeric-probe-{seed}'
 tensors=[v for v in raw.values() if isinstance(v,torch.Tensor)]+list(begin.values())+list(raw['runtime_begin'].values())
 c['all_saved_tensors_finite']=all(bool(torch.isfinite(v).all()) for v in tensors)
 records.append({'numeric_probe_seed':seed,'trained_seed':0,'raw_sha256':sha(p),'valid_query':qn,'valid_book':mn,'checks':c,'passed':sum(c.values()),'total':len(c),'max_abs_vs_native_final':deltas})
report={'scope':'Independent tensor-only recount of two numeric probes on ONE trained seed. Original queue exact-zero equality marks. Author booleans ignored; no model calls, no scoring or optimization.','source_byte_checks':checks,'records':records,'author_42_checks_reproduced':False,'unsupported':['Checkpoint bytes are not loaded: tuple declarations match pre-run tuple but do not independently prove checkpoint execution.','No individual transition trace: physical four steps/MAC counts not independently reconstructable from final round field.','No duplicate begin/input before-after snapshots: input and checkpoint immutability cannot be reconstructed.','Prefix tensor geometry/finiteness checked; actual prefix dependency on final state cannot be established without execution.','No logits or labels: source predictions correctness not reconstructable.','Exception-policy tests, packet Python class and detachment history not recorded in raw.','No learned stop, English semantics, new trained seed or post-sleep checkpoint qualification transfers.'], 'input_hashes':{str(p.relative_to(R)):sha(p) for p in [B/'PACKAGE.json',B/'TUPLE-s0.json',B/'queue-sol-stop-ordered-r2-s0-receipt-cpu-v1.md',C/'binding-s0.json',C/'actual-awake-s0/receipt.json']},'script_sha256':sha(Path(__file__))}
with O.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'report':str(O),'sha256':sha(O),'source_pins_passed':sum(checks.values()),'records':[{k:v for k,v in r.items() if k!='checks'} for r in records],'failed':[k for k,v in checks.items() if not v]+[f"seed{r['numeric_probe_seed']}:{k}" for r in records for k,v in r['checks'].items() if not v]}))
