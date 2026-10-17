import json,re,sys,collections
sys.path.insert(0,'.')
import torch
from custom_io.models import load_model
from domain.far import p2_diag as P
from domain.far import join_gap as JG
from domain.tools import sheet
caJ=re.compile(r'\*\(?[AB]\d[+\-][AB]\d\*\d+\)?$')
torch.set_num_threads(2)
for tag in sys.argv[1:]:
    m=load_model(f'ck/{tag}/checkpoint.pt').eval()
    it=[json.loads(l) for l in open(f'out/items-{tag}.jsonl')]
    rows=[dict(prompt=x['prompt'],tool_value=x['gold'],steps=x['tool_steps'],cell=x['cell']) for x in it if x['cell'] in('HO','HPO') and caJ.search(x['prompt'].split('=',1)[1])]
    res=P.teacher_forced(m,rows)
    ct=collections.Counter(); cl=collections.Counter()
    for r,(g,mc) in zip(rows,res):
        f=r['prompt'].split(';',1)[1].strip()[1:]; op,K,J,_=JG.split_formula(f)
        nK=len(sheet.evaluate(JG.piece_prompt(r['prompt'],K))['steps'])
        st=r['steps']; kval=st[nK-1][3]
        mm=re.search(r'([AB]\d)[+\-]([AB]\d)\*(\d+)',J)
        gr={}
        for part in r['prompt'].split(';')[0].split('|'):
            lab,vals=part.split(':'); 
            for i,v in enumerate(vals.split()): gr[f'{lab.strip()}{i+1}']=v
        c1=gr[mm.group(1)]
        t=mc[nK]; s=st[nK]
        if JG.same_call(tuple(t)+('',),tuple(s[:3])+('',)): k='right (mul c2 N)'
        elif t[0]=='mul' and kval in t[1:] : k='mul K-result * something [K*J precedence]'+(' (with c1)' if c1 in t[1:] else '')
        elif t[0]=='mul': k='mul other'
        else: k='op '+t[0]
        ct[k]+=1
        t=mc[nK+1]; s=st[nK+1]
        if JG.same_call(tuple(t)+('',),tuple(s[:3])+('',)): k='right (add c1 t)'
        elif t[0]=='mul': k='mul (precedence)'+(' with K-result' if kval in t[1:] else '')
        else: k='op '+t[0]
        cl[k]+=1
    print(tag,'CA-in-J HO+HPO n=',len(rows)); print('   J first call (TRANS):',dict(ct)); print('   CA add call (J_later):',dict(cl))
