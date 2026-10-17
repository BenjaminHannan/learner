import json,re,sys,collections
sys.path.insert(0,'.')
import torch
from custom_io.models import load_model
from domain.mode import greedy
from domain.far import join_gap as JG
from domain.tools import sheet
torch.set_num_threads(2)
probe=[json.loads(l) for l in open('inputs/far/sheet-probe.jsonl')]
CA=re.compile(r'=([AB]\d)([+\-])([AB]\d)\*(\d+)$')
base=[r['prompt'] for r in probe if CA.search(r['prompt'])]
print('single CA formulas in probe:',len(base))
br=[CA.sub(lambda m:f'=({m.group(1)}{m.group(2)}{m.group(3)})*{m.group(4)}',p) for p in base]
tr=[json.loads(l) for l in open('inputs/far/train-rows-l5.jsonl')]
print('train rows with "(c+c)*" or "(c-c)*":',sum(1 for r in tr if re.search(r'\([AB]\d[+\-][AB]\d\)\*',r['prompt'])))
for tag in sys.argv[1:]:
    m=load_model(f'ck/{tag}/checkpoint.pt').eval()
    for name,ps in (('c1+c2*N',base),('(c1+c2)*N',br)):
        out=greedy(m,ps); c=collections.Counter(); hits=0
        for p,(calls,pred) in zip(ps,out):
            ev=sheet.evaluate(p); st=ev['steps']; hits+=pred.strip()==str(ev['value'])
            if not calls: c['no call']+=1; continue
            f=calls[0]
            if JG.same_call(tuple(f[:3])+('',),tuple(st[0][:3])+('',)): c['first call right']+=1
            elif f[0]=='mul' and '*' in p and p.split('*')[-1] in f[1:3]: c['mul ?*N first (ignores bracket)' if '(' in p else 'mul wrong cell']+=1
            else: c['other']+=1
        print(f'  {tag} {name:10s} hits {hits}/{len(ps)}  first call: {dict(c)}')
