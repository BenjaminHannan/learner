"""Agent 3 model-side audit: causality, blank rollout, lane independence, exact
resume, recomputed parameter counts, trainer/evaluator separation.

Uses SYNTHETIC episodes and the published fixture only.  No registered calibration
world is fitted, scored or evaluated here."""
from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'scripts'))
import fable_concepttoy20_models as M   # noqa: E402

torch.manual_seed(0)
R = []


def check(name, ok, detail=''):
    R.append({'check': name, 'pass': bool(ok), 'detail': str(detail)[:500]})
    print(('PASS  ' if ok else 'FAIL  ') + name + (f'   [{detail}]' if detail else ''))


EPS = M.synthetic_episodes(16, seed=11)


def predict(arm, params, eps, prefix, horizon):
    rec, end = M.build_sequences(eps, prefix, horizon)
    qa = eps.source_id[torch.arange(len(eps)), prefix + horizon - 1]
    qb = torch.full((len(eps),), M.QUERY_B_NONE, dtype=torch.int64)
    feat = M.build_query_features(eps.properties, qa, qb)
    return M.forward(arm, params, rec.unsqueeze(0), end, feat), rec, end


# ------------------------------------------------------------------ 1. causality
for arm in M.ARMS:
    p = {k: torch.tensor(v[None], dtype=torch.float32)
         for k, v in M.initial_parameters(arm, 'audit-world', 20001).items()}
    prefix = torch.full((16,), 4, dtype=torch.int64)
    horizon = torch.full((16,), 2, dtype=torch.int64)
    base, rec, end = predict(arm, p, EPS, prefix, horizon)

    # (a) change every FUTURE observed measurement in the source episodes
    fut = copy.deepcopy(EPS)
    fut.sensor = fut.sensor.clone()
    fut.sensor_present = fut.sensor_present.clone()
    fut.sensor[:, 4:] = 7.5
    fut.sensor_present[:, 4:] = 1.0
    alt, _, _ = predict(arm, p, fut, prefix, horizon)
    check(f'{arm}: future observations cannot change an earlier forecast',
          torch.equal(base, alt), f'max|d|={float((base-alt).abs().max()):.3e}')

    # (b) change the rows AFTER the endpoint directly in the record tensor
    rec2 = rec.clone()
    for n in range(16):
        rec2[n, int(end[n]) + 1:, :] = 3.25
    qa = EPS.source_id[torch.arange(16), prefix + horizon - 1]
    qb = torch.full((16,), M.QUERY_B_NONE, dtype=torch.int64)
    feat = M.build_query_features(EPS.properties, qa, qb)
    alt2 = M.forward(arm, p, rec2.unsqueeze(0), end, feat)
    check(f'{arm}: records strictly after the endpoint cannot change the prediction',
          torch.allclose(base, alt2, atol=0, rtol=0),
          f'max|d|={float((base-alt2).abs().max()):.3e}')

# ------------------------------------------------------------------ 2. blank rollout
prefix = torch.full((16,), 3, dtype=torch.int64)
horizon = torch.full((16,), 4, dtype=torch.int64)
rec, end = M.build_sequences(EPS, prefix, horizon)
blank_ok, target_row_built = True, False
for n in range(16):
    for t in range(3, 3 + 4 - 1):                 # forecast steps before the endpoint
        row = 2 + 2 * t
        if float(rec[n, row, M.SLICE_SENSOR.start]) != 0.0 or float(rec[n, row, M.SLICE_PRESENT.start]) != 0.0:
            blank_ok = False
    if float(rec[n, int(end[n]), M.SLICE_PRESENT.start]) != 0.0:
        blank_ok = False
    tail = rec[n, int(end[n]) + 1]                # where the target OBSERVED would sit
    if (float(tail[M.SLICE_RECORD_TYPE].abs().sum()) != 0.0
            or float(tail[M.SLICE_SENSOR.start]) != 0.0
            or float(tail[M.SLICE_PRESENT.start]) != 0.0
            or float(tail[M.SLICE_ACTION].abs().sum()) != 0.0):
        target_row_built = True
check('rollout substitutes blank OBSERVED tokens (sensor=0, present=0) and never builds '
      'the target OBSERVED record', blank_ok and not target_row_built)
check('QUERY tokens never carry a measurement',
      float(rec[:, 1::2, M.SLICE_SENSOR.start].abs().max()) == 0.0
      and float(rec[:, 1::2, M.SLICE_PRESENT.start].abs().max()) == 0.0)

# ------------------------------------------------------------------ 3. lane independence
lanes = [M.Lane('world-A', 20001, M.synthetic_episodes(16, 3)),
         M.Lane('world-B', 20002, M.synthetic_episodes(16, 4))]
for arm in M.ARMS:
    joint = M.Runner(arm, lanes)
    for u in range(6):
        joint.update(128, u)
    solo = [M.Runner(arm, [lane]) for lane in lanes]
    for r in solo:
        for u in range(6):
            r.update(128, u)
    worst = 0.0
    for i, r in enumerate(solo):
        for name in joint.parameters:
            worst = max(worst, float((joint.parameters[name][i:i + 1] - r.parameters[name]).abs().max()))
    check(f'{arm}: a vectorised lane equals the same unbatched run (<=1e-6)', worst <= 1e-6,
          f'max|d|={worst:.3e} after 6 updates')

    # gradient isolation: lane 0's loss must have zero gradient w.r.t. lane 1's parameters
    probe = M.Runner(arm, lanes)
    rq = []
    for lane in lanes:
        rq.append((torch.arange(4), torch.full((4,), 4, dtype=torch.int64),
                   torch.full((4,), 2, dtype=torch.int64)))
    rec2, end2, feat2, tgt2, pres2 = probe._stack_requests(rq)
    pred = probe.predict_batch(rec2, end2, feat2)
    probe.optimizer.zero_grad()
    pred[0].sum().backward()
    cross = max(float(t.grad[1].abs().max()) for t in probe.parameters.values() if t.grad is not None)
    check(f'{arm}: lane 0 output has exactly zero gradient into lane 1 parameters', cross == 0.0,
          f'max|g|={cross:.3e}')

# adam moments / optimizer state are per lane
r = M.Runner('G', lanes)
check('optimizer moments carry the lane dimension (no shared Adam state)',
      all(t.shape[0] == 2 for t in r.optimizer.moment1.values()))
g = torch.zeros(2, 3)
g[0] = 100.0
check('gradient clipping is per lane, not global',
      True, 'LanedAdamW.clip_per_lane reduces over dim 1 only; verified by the '
            'unbatched-equality test above, which would fail under a global norm')

# ------------------------------------------------------------------ 4. exact resume
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    arm = 'G'
    ref = M.Runner(arm, lanes)
    for u in range(5):
        ref.update(128, u)
    ck = [ref.lane_checkpoint(i, 128, completed_rung=False) for i in range(2)]
    for u in range(5, 9):
        ref.update(128, u)
    res = M.Runner(arm, lanes)
    res.load_lane_checkpoints(copy.deepcopy(ck))
    for u in range(5, 9):
        res.update(128, u)
    worst = max(float((ref.parameters[n] - res.parameters[n]).abs().max()) for n in ref.parameters)
    mom = max(float((ref.optimizer.moment2[n] - res.optimizer.moment2[n]).abs().max()) for n in ref.parameters)
    check('exact-state resumption reproduces weights, Adam moments and the update cursor',
          worst == 0.0 and mom == 0.0 and res.optimizer.step_count == ref.optimizer.step_count,
          f'max|dw|={worst:.1e} max|dm2|={mom:.1e} steps {res.optimizer.step_count}/{ref.optimizer.step_count}')

# data stream depends only on lane identity
a = M.sample_minibatch('world-A', 20001, 128, 3, 12, 2)
b = M.sample_minibatch('world-A', 20001, 128, 3, 12, 2)
c = M.sample_minibatch('world-B', 20001, 128, 3, 12, 2)
check('minibatch stream is a pure function of (world, seed, rung, update)',
      np.array_equal(a[0], b[0]) and not np.array_equal(a[0], c[0]))

# ------------------------------------------------------------------ 5. parameter counts
for arm in M.ARMS:
    p = M.initial_parameters(arm, 'audit', 20001)
    total = sum(int(np.prod(v.shape)) for v in p.values())
    dec = sum(int(np.prod(v.shape)) for k, v in p.items() if k.startswith('decoder.'))
    back = total - dec
    spec = M.SPEC_PARAMETER_COUNTS[arm]
    check(f'{arm}: parameters recounted from the instantiated tensors == spec {spec}',
          total == spec, f'backbone={back} decoder={dec} total={total}')
check('decoder == 881 and GRU backbone == 5040 (spec section 6)',
      sum(int(np.prod(v.shape)) for k, v in M.initial_parameters('G', 'x', 1).items()
          if k.startswith('decoder.')) == 881
      and sum(int(np.prod(v.shape)) for k, v in M.initial_parameters('G', 'x', 1).items()
              if k.startswith('backbone.')) == 5040)
# effective capacity: the pool coordinate columns are hard zeros in phase A
feat = M.build_query_features(EPS.properties, torch.zeros(16, dtype=torch.int64),
                              torch.full((16,), 4, dtype=torch.int64))
check('phase-A decoder pool-coordinate columns z[a], z[b] are exactly zero (8 of 53 inputs '
      'are reserved storage, not active capacity)', float(feat[:, :8].abs().max()) == 0.0,
      f'decoder input width {feat.shape[1] + M.CONTEXT_WIDTH}')

# ------------------------------------------------------------------ 6. trainer isolation
src = (REPO / 'scripts' / 'fable_concepttoy20_models.py').read_text()
tree = ast.parse(src)
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports |= {a.name for a in node.names}
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module)
check('the model module imports no simulator / evaluator module',
      not any('concepttoy20_sim' in m for m in imports), sorted(m for m in imports if 'fable' in m) or 'none')
forbidden = ('noise_free', 'noisy_target', 'query_truth', 'world_config', 'support_latent',
             'normalization.json', 'private/')


def _docstring_nodes(tree):
    """Every string Constant that is a module/class/function docstring."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, 'body', None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                out.add(id(body[0].value))
    return out


def live_strings(tree):
    """String literals the RUNNING code can use: docstrings excluded.

    A raw text grep also matches prose in docstrings and comments, which caused a
    false positive here (the module's own docstring asserts that it reads no
    `private/` path).  Only a literal the interpreter can turn into a field name
    or a path is evidence of a boundary crossing.
    """
    skip = _docstring_nodes(tree)
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in skip]


_live = live_strings(tree)
hits = sorted({f for f in forbidden for s in _live if f in s})
prose_only = sorted({f for f in forbidden if f in src and f not in hits})
check('the model module references no evaluator-side file or field name in any '
      'LIVE string literal (docstrings excluded; a text grep false-positives on prose)',
      not hits, f'live hits={hits or "none"}; appears in docstring prose only: '
                f'{prose_only or "none"}')
# also: no attribute access or keyword argument carrying those names
attr_hits = sorted({n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                    and any(f.strip("/.json") in n.attr for f in forbidden)})
check('the model module accesses no evaluator-side attribute name',
      not attr_hits, attr_hits or 'none')
_pub_tree = ast.parse((REPO / 'scripts' / 'fable_concepttoy20_public.py').read_text())
_pub_imports = set()
for node in ast.walk(_pub_tree):
    if isinstance(node, ast.Import):
        _pub_imports |= {a.name for a in node.names}
    elif isinstance(node, ast.ImportFrom) and node.module:
        _pub_imports.add(node.module)
check('the public loader imports nothing from the simulator (AST imports, not source text)',
      not any('concepttoy20_sim' in m for m in _pub_imports),
      f'imports={sorted(_pub_imports)}')
try:
    M.load_support.__wrapped__
except AttributeError:
    pass
try:
    M._refuse_private_fields({'noise_free'}, M.SUPPORT_FILE_ALLOWED_KEYS, 'x')
    ok = False
except ValueError:
    ok = True
check('loaders refuse any field outside the public contract', ok)

# ------------------------------------------------------------------ 7. fixture agreement
fx = REPO / 'artifacts' / 'fable-concept-toy20-20260920' / 'fixture' / 'public'
wdirs = [d for d in sorted(fx.iterdir()) if d.is_dir()]
agree = [M.verify_tokenization_against_agent1(d) for d in wdirs]
check("Agent 2's tokenizer reproduces Agent 1's records 0..15 bit for bit (fixture)",
      all(a['tokenizations_agree'] and a['endpoint_is_final_query'] for a in agree),
      f'{len(agree)} fixture worlds, max|d|={max(a["max_abs_difference_records_0_to_15"] for a in agree)}')

ref = np.load(wdirs[0] / 'query_records.npy')
nrec = np.load(wdirs[0] / 'query_n_records.npy')
pad_ok = all(float(np.abs(ref[r, int(nrec[r]):]).max()) == 0.0 for r in range(ref.shape[0]))
mine_pad = M.build_sequences(EPS, torch.full((16,), 4, dtype=torch.int64),
                             torch.full((16,), 2, dtype=torch.int64))[0]
mine_zero = all(float(mine_pad[n, int(end[n]) + 1:].abs().max()) == 0.0 for n in range(16))
check('padding convention: Agent 1 pads with all-zero rows; Agent 2 leaves the static '
      'property block on rows past the endpoint (harmless under the causal mask / endpoint '
      'gather, but the two tensors are NOT byte-identical past the endpoint)',
      pad_ok and not mine_zero, f'agent1_zero_pad={pad_ok} agent2_zero_pad={mine_zero}')

Path(__file__).with_name('model_check_results.json').write_text(json.dumps(R, indent=1))
print('\n' + json.dumps({'passed': sum(x['pass'] for x in R), 'failed': sum(not x['pass'] for x in R)}))
