import json
S='data/simulations/%s/results.json'
runs={}
for n in ['stageA','stageA_rerun4','stageA_rerun4b','stageA_rerun2']:
    d=json.load(open(S%n))
    for s in d['simulations']:
        if s['reward_info'] is None: continue
        runs.setdefault(s['task_id'],(n,s))
        if n=='stageA': runs[s['task_id']]=(n,s)
print(len(runs),sorted(map(int,runs)))
pi=po=0
ok=0;dbok=0;fails=[]
for t,(n,s) in sorted(runs.items(),key=lambda x:int(x[0])):
    r=s['reward_info'];ok+=r['reward']==1;dbok+=bool(r['db_check']['db_match'])
    for m in s['messages']:
        u=m.get('usage')
        if u: pi+=u['prompt_tokens'];po+=u['completion_tokens']
    if r['reward']<1: fails.append((t,n,s['termination_reason'],r['db_check']['db_match'],r['reward']))
print('reward pass',ok,'db match',dbok,'of',len(runs)); print('tokens',pi,po,'usd(msgs only)',pi*1e-7+po*5e-7)
print(fails)
