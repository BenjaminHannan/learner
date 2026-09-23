import sys
from pathlib import Path
S = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames21-20260920/audit-scratch')
sys.path.insert(0, str(S))
import postc1_newnames21 as M
print('S.LOG_EVERY =', M.S.LOG_EVERY)
EXPF = S.parent/'fixtures/exp'
import shutil, tempfile
seen = {}
box = {'arm': None}
real = None
def spy(rng, visits, forbidden):
    b = real(rng, visits, forbidden)
    seen[box['arm']].append((M.tensor_sha(b.canonical.memory), M.tensor_sha(b.canonical.questions),
                             M.tensor_sha(b.canonical.owner), M.tensor_sha(b.monolithic.memory),
                             M.tensor_sha(b.monolithic.questions)))
    return b
for arm in ('control', 'treatment'):
    seen[arm] = []; box['arm'] = arm
    tmp = Path(tempfile.mkdtemp())
    # configure_variant rebinds A.training_batch, so install the spy from inside configure_recipe
    base_cfg = M.configure_recipe
    def cfg(seed, _b=base_cfg):
        global real
        p = _b(seed)
        real = M.A.training_batch
        M.A.training_batch = spy
        return p
    M.configure_recipe = cfg
    try:
        M.train_run(arm, 2100, EXPF, updates=25, out=tmp/'r', log_every=0)
    finally:
        M.A.training_batch = real
        M.configure_recipe = base_cfg
        shutil.rmtree(tmp, ignore_errors=True)
a, b = seen['control'], seen['treatment']
print('batches: control', len(a), 'treatment', len(b))
print('IDENTICAL world stream, batch for batch:', a == b)
print('first differing batch:', next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y), None))
