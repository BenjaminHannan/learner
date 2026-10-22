from lib import *
D=S+'far-data/'
tr=load(D+'learn/train-rows-l5.jsonl'); ev=load(D+'learn/eval-rows-l5.jsonl'); pr=load(D+'diag/sheet-probe.jsonl')
SC={'cell arithmetic','division','ABS','SUM','MAX','MIN','PRODUCT'}
cells={}
cells['TRAIN F4-two (joined)']=[r for r in tr if r['split']=='F4-two']
cells['TRAIN F0-near (single)']=[r for r in tr if r['split']=='F0-near']
for c in ['HO','HPO','HP','S','S5']: cells['EVAL '+c]=[r for r in ev if r['split']==c]
cells['PROBE F4-two (eval)']=[r for r in pr if r['split']=='F4-two' and r['kind'] in SC]
cells['PROBE F0-near (eval)']=[r for r in pr if r['split']=='F0-near' and r['kind'] in SC]
def info(r):
    e=sheet_tool.evaluate(r['prompt']); st=e['steps']
    f=formula(r['prompt']); sp=split_formula(f)
    layout=None
    if sp:
        op,K,J,strict=sp
        layout=('(K)*(J)' if f.startswith('(') and op=='*' and f[0]=='(' else ('K*J' if op=='*' else 'K+J'))
    return len(st), (st[0][0] if st else None), sp is not None, f
import functools
res={}
for name,rows in cells.items():
    inf=[info(r) for r in rows]
    res[name]=(rows,inf)
print('CHAIN-LENGTH HISTOGRAM (number of calculator calls in the tool working), counts and % per cell')
allk=sorted({i[0] for _,inf in res.values() for i in inf})
print('%-26s %6s '%('cell','n')+' '.join('%5d'%k for k in allk)+'   mean')
for name,(rows,inf) in res.items():
    c=collections.Counter(i[0] for i in inf); n=len(inf)
    print('%-26s %6d '%(name,n)+' '.join('%5.1f'%(100*c[k]/n) for k in allk)+'   %.2f'%(sum(i[0] for i in inf)/n))
print('\n(counts)')
for name,(rows,inf) in res.items():
    c=collections.Counter(i[0] for i in inf)
    print('%-26s '%name+' '.join('%d:%d'%(k,c[k]) for k in allk if c[k]))
print('\nLAYOUT (template) MIX, from the row\'s layout field where present, else parsed')
for name,(rows,inf) in res.items():
    c=collections.Counter(r.get('layout') or ('single' if not i[2] else 'parsed:join') for r,i in zip(rows,inf))
    print('%-26s '%name+', '.join('%s %d (%.1f%%)'%(k,v,100*v/len(rows)) for k,v in c.most_common()))
print('\nFIRST-OPERATION MIX by step count (op of the first calculator call; % within step count)')
for name,(rows,inf) in res.items():
    print('--',name)
    for k in allk:
        sel=[i for i in inf if i[0]==k]
        if not sel: continue
        c=collections.Counter(i[1] for i in sel)
        print('   %d calls (n=%d): '%(k,len(sel))+', '.join('%s %.0f%%'%(o,100*v/len(sel)) for o,v in c.most_common()))
print('\nLAYOUT x STEP COUNT (counts), joined cells')
for name in ['TRAIN F4-two (joined)','EVAL HO','EVAL S5','EVAL S','EVAL HP','EVAL HPO','PROBE F4-two (eval)']:
    rows,inf=res[name]
    c=collections.Counter((r.get('layout','-'),i[0]) for r,i in zip(rows,inf))
    print('--',name,{k:v for k,v in sorted(c.items(),key=lambda x:str(x))})
