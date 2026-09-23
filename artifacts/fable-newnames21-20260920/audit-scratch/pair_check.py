import sys, json
from pathlib import Path
S = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames21-20260920/audit-scratch')
sys.path.insert(0, str(S))
import postc1_newnames21 as M

EXP = S/'tamper-exp'
seen = {}
real_score_cell = M.R.score_cell
box = {'pool': None}
def spy(model, panel, *a, **k):
    key = (box['pool'], panel['name'])
    sig = []
    for i, sides in enumerate(M.P.chunks(panel)):
        for side, (x, targets) in sorted(sides.items()):
            sig.append((i, side, tuple(targets), M.tensor_sha(x.memory), M.tensor_sha(x.questions),
                        tuple(x.owner.tolist())))
    seen[key] = tuple(sig)
    return real_score_cell(model, panel, *a, **k)
M.R.score_cell = spy
real_sm = M.score_model
def sm(model, exp, which_pool, **k):
    box['pool'] = which_pool
    return real_sm(model, exp, which_pool, **k)
M.score_model = sm

M.main(['score', '--exp', str(EXP), '--arm', 'treatment', '--seed', '9',
        '--out', str(S/'pair-treatment-9.json')])

cells = sorted({c for p, c in seen if ('train', c) in seen and ('reserved', c) in seen})
print('gated cells seen by both pools:', len(cells), '| all keys:', sorted(seen))
same = [c for c in cells if seen[('train', c)] == seen[('reserved', c)]]
print('\ncells scored:', cells)
print('cells where the reserved and train scorings saw IDENTICAL worlds/questions/targets/order:',
      len(same), 'of', len(cells))
diff = [c for c in cells if c not in same]
print('differing:', diff)
