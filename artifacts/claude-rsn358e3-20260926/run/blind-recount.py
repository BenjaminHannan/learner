import json
B='/home/user/learner/artifacts/claude-rsn358e3-20260926/runs/'
def L(a,s): return json.load(open(f'{B}{a}-s{s}/result.json'))
def r(d,ph,k): return d['phases'][ph][k]['right']
for a in ['moe-grow-replay','dense-replay']:
  for s in [1,2]:
    d=L(a,s)
    print(a,s,'arm/seed in file:',d['arm'],d['seed'],'size',d.get('size'),'weights',d.get('weights'),'min',d.get('minutes'))
    for ph in ['start','after_grids','after_sums','after_mazes']:
      print('  ',ph,{k:r(d,ph,k) for k in ['grids5','grids6','sums4','sums6','maze7']})
    print('   replayed',d['phases']['after_sums'].get('replayed_batches'),
          'F',r(d,'after_grids','grids5')-r(d,'after_sums','grids5'))
g=[L('moe-grow-replay',s) for s in (1,2)]
V=all(r(d,'after_grids','grids5')>=120 for d in g)
p1=[r(d,'after_sums','grids5')>=150 for d in g]; p2=[r(d,'after_sums','sums4')>=120 for d in g]
pw=all(r(d,'after_sums','grids5')<=100 for d in g)
print('V',V,'grids',p1,'sums',p2,'provedwrong',pw)
print('verdict', 'INCONCLUSIVE' if not V else 'PASS' if all(p1+p2) else 'FAIL proved wrong' if pw else 'FAIL not proved wrong')
