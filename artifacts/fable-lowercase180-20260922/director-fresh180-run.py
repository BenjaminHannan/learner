import sys, json, shutil, re
from pathlib import Path
sys.path.insert(0, 'scripts')
import fable_marks123_all as M
S = Path(sys.argv[1]); C = json.load(open(S/'cases.json'))
agents = {'180': ('scripts/fable_loop180_agent.py','artifacts/fable-lowercase180-20260922/loop180-config.json'),
          '138g': ('scripts/fable_loop138g_agent.py','artifacts/fable-agent138g-20260922/loop138g-config.json')}
L = {}
for k,(a,c) in agents.items():
    mod, dcls, _, _ = M.load_agent(a); L[k] = (dcls, M.load_base_cfg(c))
n = [0]
def run(k, turns):
    dcls, base = L[k]; n[0] += 1
    root = S/'w'/f'{k}-{n[0]:03d}'; shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
    d = M.make_daemon(dcls, base, root); reps = []; facts = []
    for j,t in enumerate(turns):
        f = root/'inbox'/f'm{j:02d}.txt'; f.write_text(t); d.process_file(f)
        reps.append((root/'outbox'/f'm{j:02d}.txt').read_text().strip())
        ev = root/'notebook'/'events.jsonl'
        ents = {}; fs = []
        if ev.exists():
            for l in ev.read_text().splitlines():
                e = json.loads(l)
                if e['kind']=='ENTITY': ents[e['entity_id']] = e['name']
                if e['kind']=='FACT': fs.append((ents.get(e['subject'],e['subject']), e['relation'], json.dumps(e['value'],sort_keys=True), e.get('source')))
        facts.append(fs)
    return reps, facts
res = {'asks':[], 'teaches':[], 'traps':[]}; ok = {'asks':0,'teaches':0,'traps':0}
for setup, low, cap in C['asks']:
    r1,f1 = run('180', setup+[low]); r2,f2 = run('180', setup+[cap])
    good = r1[-1]==r2[-1] and f1[-1]==f2[-1]; ok['asks'] += good
    res['asks'].append({'low':low,'rep':r1[-1],'twin':r2[-1],'ok':good})
for setup, low, cap, yes, q in C['teaches']:
    r1,f1 = run('180', setup+[low,yes,q]); r2,f2 = run('180', setup+[cap,q])
    before = f1[len(setup)-1] if setup else []
    confirm = ('?' in r1[len(setup)]) and f1[len(setup)]==before
    good = confirm and f1[len(setup)+1]==f2[len(setup)] and r1[-1]==r2[-1]; ok['teaches'] += good
    res['teaches'].append({'low':low,'confirm':r1[len(setup)],'after_yes':r1[len(setup)+1],'q':r1[-1],'twin_q':r2[-1],'ok':good})
for setup, t in C['traps']:
    r1,f1 = run('180', setup+[t]); r2,f2 = run('138g', setup+[t])
    good = r1[-1]==r2[-1] and f1[-1]==f2[-1]; ok['traps'] += good
    res['traps'].append({'turn':t,'r180':r1[-1],'r138g':r2[-1],'ok':good})
json.dump(res, open(S/'result.json','w'), indent=1)
print({k:f"{ok[k]}/{len(C[k])}" for k in ok})
for k in res:
    for r in res[k]:
        if not r['ok']: print('MISS', k, json.dumps(r)[:400])
