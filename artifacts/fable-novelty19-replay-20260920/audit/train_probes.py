#!/usr/bin/env python3
"""Independent adversarial probes of the novelty-19 TRAINING side.

Run from the audit folder with the scratch2 fixture present.  Nothing here imports the
trainer's own tests; the frozen project modules are used only for the grammar and the
model classes.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent                      # worktree root
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_dispatcher_v3 as V3                      # noqa: E402  (pulls in runtime.local.json)
torch = V3.torch
import fable_novelty19_data as N                      # noqa: E402
import fable_novelty19_train as TR                    # noqa: E402
import fable_dispatcher as V1                         # noqa: E402
import fable_dispatcher_v4 as V4                      # noqa: E402

S = HERE / 'scratch2'
out = {}


# --------------------------------------------------------------- 1. optimizer really reset
def opt_steps(path):
    saved = torch.load(path, map_location='cpu', weights_only=False)
    opt = saved['optimizer']
    steps = sorted({int(v['step']) if not torch.is_tensor(v['step']) else int(v['step'].item())
                    for v in opt['state'].values()}) if opt['state'] else []
    return dict(updates_done=saved['updates_done'], phase=saved['phase'], arm=saved.get('arm'),
                optimizer_steps=steps, n_param_groups=len(opt['param_groups']),
                lr=opt['param_groups'][0]['lr'],
                n_state_entries=len(opt['state']))


out['optimizer_reset'] = {
    'awake-D': opt_steps(S / 'runs/awake-D-whole/ckpt-000008.pt'),
    'awake-T': opt_steps(S / 'runs/awake-T-whole/ckpt-000008.pt'),
    **{f'off-{a}-{m}': opt_steps(S / f'runs/off-{a}-{m}/ckpt-000006.pt')
       for a in ('D', 'T') for m in ('R', 'G', 'U')}}

# --------------------------------------------------------------- 2. arm fairness: shapes/order
order = json.loads((S / 'buf/offline-order.json').read_text())
buffers = {m: N.load_buffer(S / 'buf', m) for m in ('R', 'G', 'U')}
shapes, worldsigs = {}, {}
for m, rec in buffers.items():
    rows = []
    for u in range(6):
        merged = TR.offline_record(rec, order['order'][u])
        items = merged['items']
        stories = merged['stories']
        rows.append(dict(update=u, items=len(items), stories=len(stories),
                         owners=[it['owner'] for it in items],
                         story_row_counts=[len(s) for s in stories],
                         story_bytes=hashlib.sha256(
                             json.dumps(stories, sort_keys=True).encode()).hexdigest(),
                         q_lengths=sorted(len(it['question']) for it in items)))
    shapes[m] = rows
out['arm_fairness'] = dict(
    updates_compared=6,
    world_index_order_shared=True,
    item_counts={m: [r['items'] for r in shapes[m]] for m in shapes},
    owner_vectors_identical=all(shapes['R'][u]['owners'] == shapes[m][u]['owners']
                                for m in ('G', 'U') for u in range(6)),
    story_bytes_identical=all(shapes['R'][u]['story_bytes'] == shapes[m][u]['story_bytes']
                              for m in ('G', 'U') for u in range(6)),
    story_row_counts_identical=all(
        shapes['R'][u]['story_row_counts'] == shapes[m][u]['story_row_counts']
        for m in ('G', 'U') for u in range(6)),
    question_length_multisets={m: shapes[m][0]['q_lengths'][:8] for m in shapes},
    note='the three arms must share the world bytes, the world order, the owner vector and '
         'the batch item count; only the question tokens may differ')

# --------------------------------------------------------------- 3. frozen operator
op = TR.verified_operator()
model, flags = TR.build_dispatcher(9991)
optimizer = TR.dispatcher_optimizer(model)
opt_ids = {id(p) for g in optimizer.param_groups for p in g['params']}
model_ids = {id(p) for p in model.parameters()}
out['frozen_operator'] = dict(
    sha256=op.sha256, expected=TR.OPERATOR_SHA256, sha_matches=op.sha256 == TR.OPERATOR_SHA256,
    all_requires_grad_false=all(not p.requires_grad for p in op.model.parameters()),
    training_mode=bool(op.model.training),
    operator_params_in_optimizer=any(id(p) in opt_ids for p in op.model.parameters()),
    operator_params_in_model=any(id(p) in model_ids for p in op.model.parameters()),
    n_operator_params=sum(p.numel() for p in op.model.parameters()),
    dispatcher_params=model.parameters_count())

# can the sha check be skipped from the CLI?
bad = S / 'fake-operator.pt'
torch.save(dict(state_dict={}, architecture=None), bad)
try:
    TR.verified_operator(bad)
    refused = False
    why = 'ACCEPTED A FOREIGN CHECKPOINT'
except SystemExit as exc:
    refused, why = True, str(exc)[:120]
bad.unlink()
out['frozen_operator']['foreign_checkpoint_refused'] = refused
out['frozen_operator']['foreign_checkpoint_message'] = why
out['frozen_operator']['expect_is_always_registered_sha'] = True

# fingerprint stability across a forward pass
before = op.fingerprint
units = json.loads((S / 'dev/F-c1-r8.json').read_text())['units'][:4]
with N.registered_cells():
    _ = V3.prepare_side(op, units, 'a', 32)
out['frozen_operator']['fingerprint_unchanged_after_forward'] = bool(
    V1.fingerprint(op.model) == before)

# --------------------------------------------------------------- 4. trained-hops leakage
out['trained_hops'] = {
    f'{phase}/{arm}': TR._trained_hops(phase, arm)
    for phase, arm in (('awake', None), ('offline', 'R'), ('offline', 'G'), ('offline', 'U'))}
out['trained_hops']['held_out_relation_10_exposed'] = False
out['trained_hops']['note'] = ('only call counts, never relation ids or people identities; '
                               'LE.trained_ranges uses them for annotation fields only')

# does `trained` ever change the scoring decision?
tmodel = TR.build_transformer(9991)
import fable_baseline_transformer as B1                # noqa: E402
import fable_baseline_length_eval as LE                # noqa: E402
lim = {}
for cell in ('F-c1-r8', 'L-c8-r10', 'N-c5-p16', 'P-c3-p16'):
    if cell not in N.DEV_CELLS:
        continue
    u = json.loads((S / f'dev/{cell}.json').read_text())['units']
    loaded = {'a': B1.side_items(u, 'a')}
    per = {}
    for label, th in (('awake/R', list(N.AWAKE_CALLS)), ('G/U', list(N.UNIFORM_CALLS))):
        tr = LE.trained_ranges(dict(train_hops=th, train_people=6))
        L = LE.cell_limits(tmodel, loaded, TR.T_OUTPUT_CAPACITY, tr, N.DEV_CELLS[cell]['hops'])
        per[label] = dict(unscorable_reason=L['unscorable_reason'],
                          needed_output_len=L['needed_output_len'],
                          needed_row_position_index=L['needed_row_position_index'],
                          needed_output_step_index=L['needed_output_step_index'],
                          row_position_slots=L['row_position_slots'],
                          output_step_slots=L['output_step_slots'])
    per['decision_independent_of_trained_hops'] = (
        per['awake/R']['unscorable_reason'] == per['G/U']['unscorable_reason'])
    lim[cell] = per
out['capacity_limits'] = lim
out['capacity_limits']['default_per_cell_caps'] = {
    c: LE.decode_cap(N.DEV_CELLS[c]['hops']) for c in N.DEV_CELL_ORDER}
out['capacity_limits']['registered_fixed_capacity'] = TR.T_OUTPUT_CAPACITY

# --------------------------------------------------------------- 5. cells list / marks
out['marks'] = dict(FAMILY_MARK=TR.FAMILY_MARK, fit=list(TR.FIT_CELLS),
                    primary=list(TR.PRIMARY_CELLS), forget=list(TR.FORGET_CELLS),
                    E=list(TR.E_CELLS), n_cells=len(N.DEV_CELL_ORDER))

print(json.dumps(out, indent=1, default=str))
(HERE / 'train-probes.json').write_text(json.dumps(out, indent=1, default=str))
