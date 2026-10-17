import json,re,sys,collections
sys.path.insert(0,'.')
import torch
from custom_io.models import load_model
from domain.far import p2_diag as P
ca=re.compile(r'^\(?[AB]\d[+\-][AB]\d\*\d+\)?\*')
torch.set_num_threads(2)
for tag in sys.argv[1:]:
    m=load_model(f'ck/{tag}/checkpoint.pt').eval()
    it=[json.loads(l) for l in open(f'out/items-{tag}.jsonl')]
    rows=[dict(prompt=x['prompt'],tool_value=x['gold'],steps=x['tool_steps'],cell=x['cell']) for x in it if x['cell'] in('HO','HPO') and ca.search(x['prompt'].split('=',1)[1])]
    res=P.teacher_forced(m,rows)
    c=collections.Counter(); ex=[]
    for r,(g,mc) in zip(rows,res):
        n=len(r['steps']); gj=r['steps'][-1]; mj=mc[n-1]
        st=r['steps']; t_add=st[1]  # K's add = c1 + c2N
        if mj[0]==gj[0] and {mj[1],mj[2]}=={gj[1],gj[2]}: k='right'
        elif mj[0]=='add': k='add (precedence: c1 + ...)'
        elif mj[0]=='mul' and st[0][3] in (mj[1],mj[2]): k='mul using c2*N (not K) [precedence]'
        elif mj[0]=='mul': k='mul other operands'
        else: k='other op '+mj[0]
        c[k]+=1
        if len(ex)<4: ex.append((r['prompt'].split(';')[1],[tuple(s[:3]) for s in st],mj))
    print(tag,'TF join call, CA-in-K, HO+HPO n=',len(rows),dict(c))
    for e in ex: print('   ',e)
