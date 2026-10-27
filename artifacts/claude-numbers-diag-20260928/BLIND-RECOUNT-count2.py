import json,glob,os
runs=sorted(glob.glob('runs/*'))
tot=0
loopfix={}; anyr=0; loopright=0; loopv1=0
print("net | n4 right | n4 v1rule | sums4 | grids5 | n4 first step>=.99 (exact_by_kind) | first step overall exact>=.99 | n4 ever-reaches-1.0 first")
first_all=[]
for d in runs:
    name=os.path.basename(d).split('__')[0][7:15]+'/'+os.path.basename(d).split('__')[1]
    t=json.load(open(d+'/tests.json'))
    T=t['tests']; n4=T['numbers4']
    log=[json.loads(l) for l in open(d+'/train_log.jsonl')]
    f=next((r['step'] for r in log if r['exact_by_kind'].get('numbers4',0)>=0.99),None)
    f1=next((r['step'] for r in log if r['exact_by_kind'].get('numbers4',0)>=1.0),None)
    fe=next((r['step'] for r in log if r['exact']>=0.99),None)
    # also count records with numbers4 missing
    miss=sum(1 for r in log if 'numbers4' not in r['exact_by_kind'])
    tot+=n4['right']; first_all.append(f)
    print(name,'|',n4['n'],n4['right'],n4.get('right_v1_rule'),'|',T['sums4']['right'],'|',T['grids5']['right'],'|',f,'|',fe,'|',f1,'| miss',miss, '| keys',sorted(n4.keys()) if d==runs[0] else '')
    if t['arm']=='loop' :
        loopright+=n4['right']; anyr+=n4['right_at_any_round']; loopv1+=n4.get('right_v1_rule',0)
        for k,v in n4['fixed_rounds'].items(): loopfix[k]=loopfix.get(k,0)+v
print('total n4 right',tot)
print('first steps',first_all,min(first_all),max(first_all))
print('loop n4 fixed sums',loopfix,'anyround',anyr,'right(stop rule)',loopright,'v1',loopv1)
