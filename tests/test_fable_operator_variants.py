"""Pre-launch mechanism tests for the three canonical-operator variants.

Plain script. Throwaway seeds (>= 993300) and a throwaway two-item panel only; no
registered panel, checkpoint or output folder is read or written, and no smoke model
is ever scored on the registered panels.

    PY -B tests/test_fable_operator_variants.py
"""
from __future__ import annotations

import json
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
HERE = Path(__file__).resolve().parents[1]
for entry in (str(BASE), str(BASE/'scripts'), str(HERE/'scripts')):
    while entry in sys.path:
        sys.path.remove(entry)
    sys.path.insert(0, entry)
sys.path.insert(0, str(HERE/'scripts'))     # the wrapper under test, wherever it lives

import fable_operator_variants as V

A, P, C, R, torch = V.A, V.P, V.C, V.R, V.torch
E, T, data, F = V.E, V.T, V.data, V.F
CHECKS = 0
SEED = 993300


def check(label, condition, detail=''):
    global CHECKS
    if not condition:
        raise AssertionError(f'FAILED: {label} {detail}')
    CHECKS += 1
    print(f'ok {CHECKS:>2}  {label}', flush=True)


# --------------------------------------------------------------------------- setup
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
A.data.bootstrap()
import premonition.toy_ladder as tl

check('frozen premonition package is the BASE archive copy',
      Path(tl.__file__).resolve().is_relative_to(BASE/'archive'), tl.__file__)
check('ROOT is the base checkout', V.ROOT == BASE, V.ROOT)
check('lr schedule matches v3r', [round(V.lr_at(s), 9) for s in (0, 99, 100, 3999, 4000, 5000, 5999)]
      == [1e-5, 1e-3, 1e-3, 1e-3, 1e-3, round(5.5e-4, 9), round(1e-3 + (1e-4-1e-3)*1999/2000, 9)])

ORIG = V.ORIGINAL_BATCH


# ------------------------------------------------- 1. the world stream is untouched
def stream_parity(variant, batches=20, visits=4):
    V.configure_variant(variant, seed=SEED)
    mine, theirs = random.Random(1101), random.Random(1101)
    for _ in range(batches):
        new = A.training_batch(mine, visits)
        old = ORIG(theirs, visits)
        if mine.getstate() != theirs.getstate():
            return 'world rng diverged'
        memory = new.one_hop.memory if isinstance(new, V.MargBatch) else new.canonical.memory
        if not torch.equal(memory, old.canonical.memory):
            return 'memories differ'
        keep = [i for i in range(6*visits) if i % 6 not in (0, 1)]
        one = [i for i in range(6*visits) if i % 6 in (0, 1)]
        link = [i for i in range(6*visits) if i % 6 in (2, 4)]
        if isinstance(new, V.MargBatch):
            if not torch.equal(new.one_hop.questions, old.canonical.questions[one]):
                return 'marg one-hop questions differ'
            if not torch.equal(new.link.questions, old.canonical.questions[link]):
                return 'marg LINK questions differ'
            if not torch.equal(new.monolithic.questions, old.monolithic.questions):
                return 'marg monolithic questions differ'
            if not torch.equal(new.monolithic_answers, old.monolithic_targets.answer):
                return 'marg monolithic answers differ'
        elif variant == 'balance':
            if not torch.equal(new.canonical.questions[keep], old.canonical.questions[keep]):
                return 'balance LINK/terminal records differ'
            if not torch.equal(new.canonical_targets.answer[keep], old.canonical_targets.answer[keep]):
                return 'balance LINK/terminal answers differ'
            if not torch.equal(new.canonical_targets.lines[keep], old.canonical_targets.lines[keep]):
                return 'balance LINK/terminal evidence differ'
            if not torch.equal(new.monolithic.questions, old.monolithic.questions):
                return 'balance monolithic differ'
        else:
            for a, b in ((new.canonical.questions, old.canonical.questions),
                         (new.canonical_targets.answer, old.canonical_targets.answer),
                         (new.canonical_targets.lines, old.canonical_targets.lines),
                         (new.monolithic.questions, old.monolithic.questions)):
                if not torch.equal(a, b):
                    return 'e0 batch differs from v3r'
    return ''


for variant in V.VARIANTS:
    check(f'{variant}: 20 batches leave the v3r world stream and unchanged records identical',
          stream_parity(variant) == '', stream_parity(variant))


# ------------------------------------------------- 2/3/4. balance record composition
V.configure_variant('balance', seed=SEED)
rng = random.Random(1101)
VISITS, PER = 2000, 16
totals = dict.fromkeys(('8', '9', '10', '11'), 0)
one_hop_draws = dict.fromkeys(('8', '9', '10'), 0)
terminal_relations = dict.fromkeys(('8', '9', '10'), 0)
answerable = mismatched = 0
for _ in range(VISITS//PER):
    b = A.training_batch(rng, PER)
    for key, value in b.accounting['relations'].items():
        totals[key] += value
    ops = b.canonical.questions[:, 2].tolist()
    for i, op in enumerate(ops):
        if i % 6 in (0, 1):
            one_hop_draws[str(op)] += 1
        elif i % 6 in (3, 5):
            terminal_relations[str(op)] += 1
    paths = A.truth_paths(b.canonical)
    answerable += len(paths)
    mismatched += sum(p[-1]['target'] != int(t) for p, t in zip(paths, b.canonical_targets.answer))

draws = sum(one_hop_draws.values())
frequency = {k: v/draws for k, v in one_hop_draws.items()}
check('balance: one-hop relation frequencies ~ (1/6, 1/6, 2/3) over 2,000 visits',
      all(abs(frequency[k]-p) < .015 for k, p in (('8', 1/6), ('9', 1/6), ('10', 2/3))),
      json.dumps({k: round(v, 4) for k, v in frequency.items()}))
check('balance: 2 one-hop canonical records per visit',
      draws == 2*VISITS, draws)
expected = 4/3*VISITS
check('balance: per-relation canonical attribute counts are equal (4/3 per visit each)',
      all(abs(totals[k]-expected)/expected < .05 for k in ('8', '9', '10')),
      json.dumps({k: totals[k] for k in ('8', '9', '10', '11')}) + f' expected {expected:.0f}')
check('balance: LINK canonical records unchanged at 2 per visit', totals['11'] == 2*VISITS, totals['11'])
check('balance: every canonical record is answerable from eligible visible facts (truth_paths)',
      mismatched == 0 and answerable == 6*VISITS, f'{mismatched} mismatched of {answerable}')
check('balance: relation 10 is never the terminal of a two-hop-derived record',
      terminal_relations['10'] == 0 and sum(terminal_relations.values()) == 2*VISITS,
      json.dumps(terminal_relations))

# The replaced one-hop record keeps the eligibility (`where`) of the question it replaces.
V.configure_variant('balance', seed=SEED)
mine, theirs = random.Random(1101), random.Random(1101)
nb, ob = A.training_batch(mine, 8), ORIG(theirs, 8)
check('balance: one-hop records keep the original causal eligibility mask',
      torch.equal(nb.canonical.eligible, ob.canonical.eligible))
check('balance: supporting line of every one-hop record is eligible',
      bool(nb.canonical.eligible.gather(1, nb.canonical_targets.lines).all())
      and bool(E.evidence_mask(nb.canonical, nb.canonical_targets).any(-1).all()))
check('balance: record counts and kinds unchanged versus v3r',
      nb.accounting['kinds'] == ob.accounting['kinds'] == dict(one_hop=16, link=16, terminal=16, monolithic=16)
      and nb.accounting['records'] == ob.accounting['records'] == 64)


def _raises(fn, needle='overlap'):
    try:
        fn()
    except RuntimeError as exc:
        return needle in str(exc)
    return False


V.configure_variant('balance', seed=SEED)
probe = A.training_batch(random.Random(992811), 2)
sig = A.visible_signature(probe.canonical.memory[0].tolist(), probe.canonical.questions[0].tolist())
V.configure_variant('balance', seed=SEED)
check('balance: the semantic-overlap forbidden check still fires',
      _raises(lambda: A.training_batch(random.Random(992811), 2, {sig})))
V.configure_variant('marg', seed=SEED)
mprobe = A.training_batch(random.Random(992811), 2)
msig = A.visible_signature(mprobe.one_hop.memory[0].tolist(), mprobe.terminal.questions[0].tolist())
V.configure_variant('marg', seed=SEED)
check('marg: the forbidden check covers the sixteen-way terminal expansion',
      _raises(lambda: A.training_batch(random.Random(992811), 2, {msig})))


# ------------------------------------------------- 5. e0 loss is exactly the answer CE
V.configure_variant('e0', seed=SEED)
model = A.new_model(SEED)
batch = A.training_batch(random.Random(1101), 4)
same = True
for x, y in ((batch.canonical, batch.canonical_targets), (batch.monolithic, batch.monolithic_targets)):
    total, answer, evidence, _ = E.loss_for(model, x, y)
    mine = V._answer_ce(model, x, y)
    same &= (bool(torch.equal(mine, answer)) and float(evidence.detach()) > 0
             and not torch.equal(total, answer))
check('e0: loss equals E.loss_for\'s answer cross-entropy exactly, with the evidence term dropped', same)

grads = {}
for name, step in (('e0', V._step_e0), ('v3r', V._step_balance)):
    m = A.new_model(SEED)
    opt = A.T.optimizer_for(m)
    step(m, opt, batch, 0)
    grads[name] = C.fingerprint(m)
check('e0: dropping the evidence term actually changes the update', grads['e0'] != grads['v3r'])


# ------------------------------------------------- 6/7/8. marg
V.configure_variant('marg', seed=SEED)
model = A.new_model(SEED + 1).eval()
memory = [[[3, 52, 11, 53, 7], [3, 53, 8, 12, 7], [3, 52, 8, 13, 7], [3, 54, 8, 14, 7], []]]
Y = 12
tiny = V.MargBatch(
    one_hop=data.pack(memory, [[4, 52, 8, 5]], [0], [4]),
    one_hop_answers=torch.tensor([13]),
    link=data.pack(memory, [[4, 52, 11, 5]], [0], [4]),
    terminal=data.pack(memory, [[4, e, 8, 5] for e in range(52, 68)], [0]*16, [4]*16),
    two_hop_answers=torch.tensor([Y]),
    monolithic=data.pack(memory, [[4, 52, 11, 8, 5]], [0], [4]),
    monolithic_answers=torch.tensor([Y]),
    accounting=dict(kinds=dict(one_hop=1, marginalised_two_hop=1, monolithic=1), relations={}))

with torch.no_grad():
    brute = 0.
    p1_full = model(data.pack(memory, [[4, 52, 11, 5]], [0], [4])).softmax(-1)[0]
    for e in range(52, 68):
        pe = float(p1_full[e])
        conditional = model(data.pack(memory, [[4, e, 8, 5]], [0], [4])).softmax(-1)[0, Y]
        brute += pe * float(conditional)
    batched = float(V.marginal_probability(model, tiny)[0])
check('marg: batched marginal equals a brute-force per-entity computation',
      abs(batched - brute) < 1e-9, f'{batched!r} vs {brute!r}')
check('marg: p1 is NOT renormalised (entity mass < 1 leaves the marginal short)',
      float(p1_full[52:68].sum()) < 1. and batched <= float(p1_full[52:68].sum()) + 1e-9,
      f'entity mass {float(p1_full[52:68].sum()):.6f}')

trained = A.new_model(SEED + 1)
probability, parts = V.marginal_probability(trained, tiny, trace=True)
loss = -probability.clamp_min(1e-12).log().mean()
dlink, dterm = torch.autograd.grad(loss, [parts['link_logits'], parts['terminal_logits']],
                                   retain_graph=True)
check('marg: gradient reaches the LINK-call path', float(dlink.norm()) > 0, float(dlink.norm()))
check('marg: gradient reaches the terminal-call path', float(dterm.norm()) > 0, float(dterm.norm()))
check('marg: every terminal entity receives gradient',
      bool((dterm.reshape(16, -1).norm(dim=1) > 0).all()))
parameter_grads = torch.autograd.grad(loss, [p for p in trained.parameters() if p.requires_grad],
                                      allow_unused=True)
check('marg: the marginalised record produces a nonzero parameter gradient',
      sum(float(g.norm()) for g in parameter_grads if g is not None) > 0)

_visit = tl.visit


def poisoned_visit(spec, rng, **kwargs):
    rows, world, record = _visit(spec, rng, **kwargs)
    for row in rows:
        if row.question:
            row.gold = (10**6, 10**6)
            row.supplied = (10**6,)*6
    return rows, world, record


V.configure_variant('marg', seed=SEED)
clean = A.training_batch(random.Random(1101), 4)
tl.visit = poisoned_visit
try:
    V.configure_variant('marg', seed=SEED)
    dirty = A.training_batch(random.Random(1101), 4)
finally:
    tl.visit = _visit
identical = all(torch.equal(getattr(clean, f), getattr(dirty, f)) for f in
                ('one_hop_answers', 'two_hop_answers', 'monolithic_answers')) and \
            all(torch.equal(getattr(clean, f).questions, getattr(dirty, f).questions)
                and torch.equal(getattr(clean, f).memory, getattr(dirty, f).memory)
                and torch.equal(getattr(clean, f).eligible, getattr(dirty, f).eligible)
                for f in ('one_hop', 'link', 'terminal', 'monolithic'))
m1, m2 = A.new_model(SEED), A.new_model(SEED)
l1 = sum(w*l for w, l in zip(V.marg_weights(clean), V.marg_losses(m1, clean)))
l2 = sum(w*l for w, l in zip(V.marg_weights(dirty), V.marg_losses(m2, dirty)))
check('marg: poisoning row.gold/row.supplied changes neither the batch nor the loss',
      identical and torch.equal(l1, l2), f'{float(l1.detach())!r} vs {float(l2.detach())!r}')

tl.visit = poisoned_visit
try:
    V.configure_variant('balance', seed=SEED)
    reached = False
    try:
        A.training_batch(random.Random(1101), 4)
    except (IndexError, AssertionError):
        reached = True
finally:
    tl.visit = _visit
check('marg: the poison probe is meaningful (balance/v3r DO read row.gold and fail on it)', reached)

V.configure_variant('marg', seed=SEED)
batch = A.training_batch(random.Random(1101), 16)
check('marg: six records per visit (2 one-hop + 2 marginalised + 2 monolithic)',
      batch.accounting['records'] == 96 and batch.accounting['kinds'] ==
      dict(one_hop=32, marginalised_two_hop=32, monolithic=32), json.dumps(batch.accounting['kinds']))
check('marg: the three groups are weighted as equal records',
      V.marg_weights(batch) == (1/3, 1/3, 1/3), V.marg_weights(batch))
check('marg: 1 + 16 canonical forwards per marginalised record',
      batch.accounting['forwards'] == dict(one_hop=32, link=32, terminal=512, monolithic=32),
      json.dumps(batch.accounting['forwards']))
counted = V.training_flops_marg(batch, model)
expected_flops = sum(T.training_flops(x, model) for x in
                     (batch.one_hop, batch.link, batch.terminal, batch.monolithic))
# The counter is affine in the question count; check that every one of the 512 terminal
# forwards is charged, not just the 32 records they expand from.
f32, f64, f512 = (T.training_flops(A.select(batch.terminal, list(range(n))), model)
                  for n in (32, 64, 512))
V.configure_variant('e0', seed=SEED)
v3r_flops = V.ORIGINAL_FLOPS(ORIG(random.Random(1101), 16), model)
V.configure_variant('marg', seed=SEED)
check('marg: FLOPs are counted per forward, including the sixteen-way expansion',
      counted == expected_flops and f512 - f64 == 14*(f64 - f32) and counted > 2*v3r_flops,
      f'counted {counted:,} vs v3r {v3r_flops:,}')
check('marg: no gold entity or evidence line is recorded in the accounting',
      batch.accounting['gold_entities_used'] == 0 and batch.accounting['evidence_lines_used'] == 0)

V.configure_variant('marg', seed=SEED, marg_visits=8)
reduced = A.training_batch(random.Random(1101), 16)
V.configure_variant('marg', seed=SEED)
check('marg: the --marg-visits flag defaults OFF and only trims the marginalised fan-out',
      reduced.accounting['kinds'] == dict(one_hop=32, marginalised_two_hop=16, monolithic=32)
      and abs(sum(V.marg_weights(reduced)) - 1) < 1e-12
      and batch.accounting['marg_visits'] == 16, json.dumps(reduced.accounting['kinds']))


# ------------------------------------------------- 9. parameter count and schema
reference = T.TokenMemoryReasoner()
schema = [(k, tuple(v.shape)) for k, v in reference.state_dict().items()]
ok = True
for variant in V.VARIANTS:
    V.configure_variant(variant, seed=SEED)
    m = A.new_model(SEED)
    ok &= m.parameters_count() == 79316
    ok &= [(k, tuple(v.shape)) for k, v in m.state_dict().items()] == schema
    reference.load_state_dict(m.state_dict(), strict=True)
check('all variants: 79,316 parameters and the unchanged state-dict schema', ok)


# ------------------------------------------------- 10. end-to-end worker smoke
SMOKE_UPDATES = 20
work = Path(tempfile.mkdtemp(prefix='fable-operator-variants-smoke-'))
try:
    panel = P.generate('c1_own_one_hop', n=2, namespace='fable-operator-variants-smoke-993300')
    panel_path = work/'throwaway-panel.pt'
    torch.save(panel, panel_path)
    forbidden = work/'throwaway-forbidden.json'
    C.write_new(forbidden, sorted(P.signatures(panel)[0]))
    saved_out = R.OUT
    for variant in V.VARIANTS:
        folder = work/variant
        folder.mkdir()
        C.write_new(folder/'astra_canonical_operator_launch.json', dict(
            variant=variant, marg_visits=0, files={},
            schedule=dict(updates=SMOKE_UPDATES, training_seconds=600, work_seconds=900,
                          terminate_seconds=930, visits_per_update=16),
            exclusion_path=str(forbidden),
            panels={'throwaway': dict(path=str(panel_path), sha256=C.sha(panel_path))}))
        V.configure_variant(variant, seed=SEED)
        R.OUT = folder
        R.worker(SEED, time.monotonic())
        done = json.loads((folder/f'astra_canonical_operator_seed-{SEED}/completion.json').read_text())
        training = json.loads((folder/f'astra_canonical_operator_seed-{SEED}/training.json').read_text())
        check(f'{variant}: worker smoke runs end to end on a throwaway panel '
              f'({SMOKE_UPDATES} updates, seed {SEED})',
              done['complete'] and done['updates'] == SMOKE_UPDATES
              and done['final_checkpoint_only'] and training['flops'] > 0
              and set(done['results']) == {'throwaway'}
              and done['results']['throwaway']['n'] == 2,
              json.dumps(done['results']))
    R.OUT = saved_out
finally:
    shutil.rmtree(work, ignore_errors=True)

print(f'\nALL {CHECKS} CHECKS PASSED', flush=True)
