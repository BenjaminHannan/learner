import json,sys
S='data/simulations/%s/results.json'
want={'0':'stageA','1':'stageA','5':'stageA','11':'stageA','19':'stageA_rerun4b','20':'stageA','27':'stageA','31':'stageA','34':'stageA','38':'stageA_rerun2','39':'stageA'}
for t in sys.argv[1:]:
    d=json.load(open(S%want[t]))
    tk={x['id']:x for x in d['tasks']}[t]
    s=[x for x in d['simulations'] if x['task_id']==t and x['reward_info']][0]
    print('=====TASK',t,s['termination_reason'],len(s['messages']))
    print('USER SCENARIO:',json.dumps(tk['user_scenario']['instructions'])[:900])
    print('GOLD:',[(a['name'],json.dumps(a['arguments'])[:200]) for a in tk['evaluation_criteria']['actions'] if not a['name'].startswith(('get_','find_','list_','calculate','think'))])
    for m in s['messages']:
        for c in (m.get('tool_calls') or []):
            if not c['name'].startswith(('get_','find_','list_','calculate','think')): print('AGENT WRITE:',c['name'],json.dumps(c['arguments'])[:200])
        if m['role']=='tool' and m.get('error'): print('TOOLERR',m['content'][:150])
    for m in s['messages'][-6:]:
        print(m['role'].upper(),':',(m.get('content') or '')[:350].replace('\n',' '))
