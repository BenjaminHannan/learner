import sys, json, random
from pathlib import Path
S = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames21-20260920/audit-scratch')
sys.path.insert(0, str(S))
import postc1_newnames21 as M

EXPF = S.parent/'fixtures/exp'
pool = M.load_pool(EXPF)
train_idx = set(pool['train_index'].tolist()); res_idx = set(pool['reserved_index'].tolist())
print('pool: train', len(train_idx), 'reserved', len(res_idx), 'overlap', len(train_idx & res_idx))
codes = pool['codes']
# map each code row -> its pool index (codes are distinct directions)
key_of = {tuple(r.tolist()): i for i, r in enumerate(codes)}
assert len(key_of) == 4096

# --- 1. training code stream, first 50 updates, all three registered seeds
for seed in M.SEEDS:
    subset = M.pool_subset(pool, 'train')
    k = f'{M.TRAIN_CODE_NAMESPACE}:{seed}'
    gen = random.Random(k)
    seen_pool_idx, per_step = set(), []
    for step in range(50):
        c, idx = M.assign_codes(subset, f'{k}:{step}:{gen.randrange(1<<30)}', M.VISITS, M.ENTITIES)
        assert c.shape == (16, 16, 48), c.shape
        for v in range(16):
            rows = [tuple(c[v,p].tolist()) for p in range(16)]
            assert len(set(rows)) == 16, 'codes not distinct within a world'
            for r in rows: seen_pool_idx.add(key_of[r])
        # visits differ from one another
        assert len({tuple(sorted(idx[v].tolist())) for v in range(16)}) == 16
        per_step.append(tuple(sorted(idx[0].tolist())))
    assert len(set(per_step)) == 50, 're-drawn every update'
    print(f'seed {seed}: 50 updates x 16 visits x 16 codes; distinct pool codes touched',
          len(seen_pool_idx), '| in reserved half:', len(seen_pool_idx & res_idx),
          '| all in train half:', seen_pool_idx <= train_idx)

# --- 2. panel code assignment per pool
rows = M.panel_paths(EXPF)
print('cell order used by score_model:', list(rows))
for which in M.POOLS:
    sub = M.pool_subset(pool, which)
    touched = set()
    for cell in rows:
        panel = M.load_panel(rows[cell])
        for i, sides in enumerate(M.P.chunks(panel)):
            worlds = next(iter(sides.values()))[0].memory.shape[0]
            c, _ = M.assign_codes(sub, f'{M.PANEL_CODE_NAMESPACE}:{which}:{cell}:{i}', worlds, M.ENTITIES)
            assert c.shape[1] == 16, (cell, c.shape)
            for w in range(c.shape[0]):
                for p in range(16): touched.add(key_of[tuple(c[w,p].tolist())])
    want = train_idx if which == 'train' else res_idx
    print(f'panel pool {which}: codes touched {len(touched)}, all inside its half:', touched <= want,
          '| leaked into the other half:', len(touched - want))
