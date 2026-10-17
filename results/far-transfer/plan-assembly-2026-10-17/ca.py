import json,sys,collections,re
sys.path.insert(0,'.'); sys.path.insert(0,'out')
from strata import ncells
from domain.far import join_gap as JG
CA=re.compile(r'^[AB]\d[+\-*][AB]\d(?:[*+\-]\d+)?$|^[AB]\d[+\-][AB]\d\*\d+$')
def pieces(p):
    f=p.split(';',1)[1].strip()[1:]
    sp=JG.split_formula(f)
    return sp
def shape(x): return re.sub(r'\b\d+\b','N',re.sub(r'[AB]\d','c',x))
ev=[json.loads(l) for l in open('inputs/far/eval-rows-l5.jsonl')]
tr=[json.loads(l) for l in open('inputs/far/train-rows-l5.jsonl') if 'layout' in json.loads(l)]
for name,rows in [('eval',ev),('train',tr)]:
    c=collections.Counter()
    for r in rows:
        sp=pieces(r['prompt'])
        if not sp: c[(r.get('split'),r['layout'],'UNSPLIT')]+=1; continue
        op,K,J,_=sp
        ks,js=shape(K),shape(J)
        has='c+c*N' in (ks,js)
        c[(r['split'] if name=='eval' else 'train',r['layout'],'CA-piece' if has else 'no-CA',('K' if ks=='c+c*N' else 'J' if js=='c+c*N' else '-'))]+=1
    for k in sorted(c,key=str): print(name,k,c[k])
# HO: is every CA-piece item in DZ?
ho=[r for r in ev if r['split']=='HO']
d=collections.Counter()
for r in ho:
    op,K,J,_=pieces(r['prompt']); has='c+c*N' in (shape(K),shape(J))
    d[(has,(r['n_steps'],ncells(r['prompt']))==(4,4))]+=1
print('HO (has CA piece, in DZ):',d)
# what kind shapes of 'cell arithmetic'
print(collections.Counter(shape(x) for r in tr for x in pieces(r['prompt'])[1:3] if 'SUM' not in x and 'MAX' not in x and 'MIN' not in x and 'PRODUCT' not in x and 'ABS' not in x))
