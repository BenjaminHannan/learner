import sys
from pathlib import Path
S = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames21-20260920/audit-scratch')
sys.path.insert(0, str(S))
import postc1_newnames21 as M
EXP = S/'tamper-exp'
seq = {'train': [], 'reserved': []}
box = {'pool': None}
real_score_cell = M.R.score_cell
def spy(model, panel, *a, **k):
    sig = []
    for i, sides in enumerate(M.P.chunks(panel)):
        for side, (x, targets) in sorted(sides.items()):
            sig.append((i, side, tuple(targets), M.tensor_sha(x.memory),
                        M.tensor_sha(x.questions), tuple(x.owner.tolist())))
    seq[box['pool']].append((panel['name'], panel['n'], tuple(sig)))
    return real_score_cell(model, panel, *a, **k)
M.R.score_cell = spy
real_sm = M.score_model
def sm(model, exp, which_pool, **k):
    box['pool'] = which_pool
    return real_sm(model, exp, which_pool, **k)
M.score_model = sm
M.main(['score', '--exp', str(EXP), '--arm', 'treatment', '--seed', '9',
        '--skip-wide', '--out', str(S/'pair2-treatment-9.json')])
a, b = seq['train'], seq['reserved']
print('\ncalls: train', len(a), 'reserved', len(b))
print('same length:', len(a) == len(b))
print('IDENTICAL sequence of (panel, n, worlds, questions, targets, order):', a == b)
print('first mismatch:', next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None))
