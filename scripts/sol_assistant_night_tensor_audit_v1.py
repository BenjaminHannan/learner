#!/usr/bin/env python3
"""Read-only CPU audit of actual saved night tensors and populated optimizer.
No forward/backward/optimizer construction or steps. Does not accept ledger flags
as evidence of tensor equality, parameter change or finite Adam moments.
"""
import argparse,importlib,json,math,sys
from pathlib import Path
from sol_assistant_bundle import ROOT,owned,pin,verify_pin,sha,save_new,Unavailable

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def run(spec_path,out):
    import torch
    torch.set_num_threads(2)
    spec=read(spec_path);out=owned(out);out.mkdir(parents=True,exist_ok=False)
    report={'spec_sha256':sha(spec_path),'checks':[],'measurements':{},'inference_calls':0,'optimizer_steps':0,'activation':False,'actual_day_experience':False,'scope':'actual saved checkpoint bytes, one trained seed0; no learning/retention/semantic claim'}
    def check(name,passed,**detail):
        report['checks'].append({'name':name,'pass':bool(passed),**detail})
        if not passed:raise Unavailable(name)
    def equal_state(name,left,right):
        check(name+' keys',set(left)==set(right))
        bad=[k for k in left if left[k].dtype!=right[k].dtype or left[k].shape!=right[k].shape or not torch.equal(left[k],right[k])]
        check(name+' actual tensors',not bad,tensors=len(left),mismatches=bad)
    try:
        inputs=spec['inputs'];sources=spec['sources']
        for p in [*inputs.values(),*sources]:verify_pin(p)
        check('all input/source byte pins',True,count=len(inputs)+len(sources))
        manifest=read(inputs['manifest']['path']);decision=read(inputs['decision']['path'])
        check('manifest bound by final decision',decision['candidate_bundle_pin']==inputs['manifest']['sha256'])
        for role,key in [('parent','candidate'),('prefix','prefix'),('reader','reader')]:check('manifest '+role,manifest[role]['sha256']==inputs[key]['sha256'])
        for role in ('candidate','prefix','resume'):
            matches=[h for p,h in decision['candidate_files'].items() if Path(p).name==Path(inputs[role]['path']).name]
            check('final decision pins '+role,matches==[inputs[role]['sha256']])
        load=lambda role:torch.load(inputs[role]['path'],map_location='cpu',weights_only=True)
        candidate=load('candidate');baseline=load('baseline');resume=load('resume');prefix=load('prefix');oldprefix=load('baseline_prefix');reader=load('reader');oldreader=load('baseline_reader')
        equal_state('candidate export equals resume',candidate['state_dict'],resume['core'])
        check('baseline/candidate architecture',candidate['constructor']==baseline['constructor'])
        left,right=baseline['state_dict'],candidate['state_dict']
        check('baseline/candidate keys',set(left)==set(right))
        changed=[k for k in left if not torch.equal(left[k],right[k])]
        check('actual saved core tensors changed',bool(changed),changed_names=changed,changed_count=len(changed),total_tensors=len(left))
        for label,state in [('core',right),('reader',reader['state_dict']),('prefix',prefix['adapter_state'])]:
            bad=[k for k,v in state.items() if not bool(torch.isfinite(v).all())]
            check(label+' finite actual tensors',not bad,nonfinite_names=bad)
        frozen=[k for k in left if 'halt' in k or k in ('position_frequencies','boundary_roles')]
        check('halt/position buffers unchanged',all(torch.equal(left[k],right[k]) for k in frozen),names=frozen)
        equal_state('reader actual tensors unchanged',reader['state_dict'],oldreader['state_dict'])
        equal_state('prefix actual tensors unchanged',prefix['adapter_state'],oldprefix['adapter_state'])
        check('prefix rebound parent',prefix['parent_sha256']==inputs['candidate']['sha256'])
        check('prefix same reader',prefix['reader_sha256']==inputs['reader']['sha256'])
        check('core-only resume schema',set(resume)=={'core','optimizer','sample_rng','torch_rng','cuda_rng','ledger','binding'})
        # Instantiate exact native constructor only to recover parameter registration
        # order/shapes. It performs no model execution or optimization.
        sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
        ordered=importlib.import_module('sol_spatial_poc_ordered_v2')
        core,_=ordered.load_ordered_bundle(inputs['candidate']['path'],'cpu')
        named=[(n,p) for n,p in core.named_parameters() if 'halt' not in n]
        optimizer=resume['optimizer'];groups=optimizer['param_groups'];ids=[i for g in groups for i in g['params']]
        check('Adam groups map exact core parameter order',len(ids)==len(named) and len(set(ids))==len(ids),group_count=len(groups),group_params=len(ids),native_nonhalt_params=len(named))
        check('Adam hyperparameters match sealed plan',len(groups)==1 and groups[0]['lr']==spec['lr'] and groups[0]['weight_decay']==spec['weight_decay'] and tuple(groups[0]['betas'])==(0.9,0.999) and groups[0]['eps']==1e-8)
        states=optimizer['state'];check('populated Adam state IDs subset of groups',bool(states) and set(states).issubset(set(ids)))
        records=[]
        for ident,(name,param) in zip(ids,named):
            if ident not in states:continue
            state=states[ident];check('Adam fields '+name,set(state)=={'step','exp_avg','exp_avg_sq'})
            step=state['step'];value=float(step)
            check('Adam positive bounded step '+name,step.numel()==1 and math.isfinite(value) and value.is_integer() and 0<value<=25)
            for key in ('exp_avg','exp_avg_sq'):
                v=state[key]
                check('Adam finite matching '+key+' '+name,v.shape==param.shape and v.dtype==param.dtype and bool(torch.isfinite(v).all()))
            check('Adam second moment nonnegative '+name,bool((state['exp_avg_sq']>=0).all()))
            records.append({'id':ident,'parameter':name,'shape':list(param.shape),'step':value,'exp_avg_nonzero':int(torch.count_nonzero(state['exp_avg'])),'exp_avg_sq_nonzero':int(torch.count_nonzero(state['exp_avg_sq']))})
        check('actual nonzero Adam moments',any(x['exp_avg_sq_nonzero']>0 for x in records))
        report['measurements']['Adam_states']=records
        report['measurements']['Adam_missing_state_parameters']=[n for i,(n,p) in zip(ids,named) if i not in states]
        report['measurements']['populated_Adam_state_count']=len(records)
        ledger=read(inputs['ledger']['path'])
        check('resume and JSON ledger exact equality',resume['ledger']==ledger)
        report['measurements']['ledger_updates_not_independent_step_history']=ledger['updates']
        check('stored RNG tensors finite uint8',resume['torch_rng'].dtype==torch.uint8 and all(v.dtype==torch.uint8 for v in resume['cuda_rng']))
        for p in [*inputs.values(),*sources]:verify_pin(p)
        check('repeat input/source byte hashes unchanged',True,changed_files=0)
        report['measurements']['reader_limitation']='same frozen reader file is referenced; no separate post-training reader export exists. Does not prove live training-time memory immutability.'
        report['pass']=True
    except Exception as exc:
        report['pass']=False;report['error']={'type':type(exc).__name__,'message':str(exc)}
    report['checks_passed']=sum(r['pass'] for r in report['checks']);report['checks_total']=len(report['checks'])
    save_new(out/'raw-audit.json',report);print(json.dumps(report,indent=2));return 0 if report['pass'] else 1
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--out',required=True);a=p.parse_args();raise SystemExit(run(a.spec,a.out))
