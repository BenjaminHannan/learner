"""Unit tests for `scripts/fable_newnames21.py` (experiment 21 / M1, "new names").

Plain script, no pytest, in this repository's house style: `check(name, function)`, a
`_Skip` for anything that needs a fixture that is not on this machine, and a PASSED /
FAILED / SKIPPED tally with a non-zero exit on any failure.

  python3.12 -B tests/test_fable_newnames21.py [--exp FIXTURE_EXP_DIR]

`--exp` (default `artifacts/fable-newnames21-20260920/fixtures/exp`) points at a small
DISPOSABLE fixture experiment folder -- a pool plus a tiny panel suite, built with the
fixture namespaces, never the registered ones.  The tests that need panels skip cleanly
when it is absent; everything else runs from nothing.

What is actually proved here, in the order the brief asks for it:

  reserved codes are unreachable   an exhaustive check over a long training stream: every
                                   code the treatment trainer can ever draw is compared,
                                   by identity of the pool row, against the reserved half.
  panels are byte-identical        the two treatment scorings read the same files and never
                                   write: the sha256 of every panel is taken before and
                                   after both scorings, and the two scorings' packed input
                                   tensors are compared tensor for tensor.
  codes are frozen                 no `requires_grad`, no gradient, and bit-identical after
                                   real optimizer updates.
  the tied head uses the same codes  the entity columns of the output logits are shown to
                                   be exactly `answer . (code_scale * code)` for the very
                                   codes the story tokens were embedded with, per world.
  parameter counts                 treatment < control, and the arithmetic of the change.
  control equivalence              this file's control path against the registered training
                                   functions called directly, fingerprint by fingerprint.
  the C1 scale trace               the 500-update heartbeat carries `code_scale` and
                                   `entity_output_bias` on the treatment arm, the trace
                                   reaches `training.json` even with printing switched off,
                                   and the control's key is null.
  gate arithmetic                  synthetic tables driving PASS, PARTIAL, VOID, INCOMPLETE
                                   and both pre-named failure signatures.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import random
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'scripts'))

import fable_newnames21 as N                                              # noqa: E402

torch = N.torch
DEFAULT_EXP = HERE.parent/'artifacts/fable-newnames21-20260920/fixtures/exp'
EXP = DEFAULT_EXP

PASSED = FAILED = SKIPPED = 0


class _Skip(Exception):
    pass


def check(name, function):
    global PASSED, FAILED, SKIPPED
    try:
        function()
    except _Skip as exc:
        SKIPPED += 1
        print(f'SKIPPED {name}: {exc}', flush=True)
    except Exception:                                                     # noqa: BLE001
        FAILED += 1
        print(f'FAILED  {name}', flush=True)
        traceback.print_exc()
    else:
        PASSED += 1
        print(f'PASSED  {name}', flush=True)


def fixture_pool():
    if not (EXP/'pool/pool.json').exists():
        raise _Skip(f'no fixture pool at {EXP}')
    return N.load_pool(EXP)


def fixture_panels():
    if not (EXP/'panels/manifest.json').exists():
        raise _Skip(f'no fixture panels at {EXP}')
    return N.panel_paths(EXP)


def small_pool(size=N.POOL_SIZE):
    """The real builder; the split is what the reachability test needs, not the bytes."""
    return N.build_pool('test/pool', 'test/pool/split')


def a_batch(seed=5):
    N.configure_once()
    N.S.configure_variant(N.VARIANT, seed=seed, **N.S.registered_params(N.VARIANT))
    return N.A.training_batch(random.Random(1101), N.VISITS, frozenset())


# ---------------------------------------------------------------- the pool and the split

def test_pool_shape_and_split():
    pool = small_pool()
    codes = pool['codes']
    assert codes.shape == (N.POOL_SIZE, N.WIDTH), tuple(codes.shape)
    assert codes.dtype == torch.float32
    assert float((codes.norm(dim=1)-1).abs().max()) < 1e-5, 'codes are unit-norm'
    train, reserved = pool['train_index'], pool['reserved_index']
    assert len(train) == N.TRAIN_SIZE == 3072 and len(reserved) == N.RESERVED_SIZE == 1024
    assert set(train.tolist()).isdisjoint(set(reserved.tolist()))
    assert sorted(train.tolist()+reserved.tolist()) == list(range(N.POOL_SIZE)), \
        'the split is a permutation of the whole pool, not a prefix'
    # the split must not be the trivial "first 3,072": a prefix split would make the two
    # halves distinguishable by construction order.
    assert train.tolist() != list(range(N.TRAIN_SIZE))


def test_pool_is_deterministic():
    a, b = small_pool(), small_pool()
    assert N.tensor_sha(a['codes']) == N.tensor_sha(b['codes'])
    assert N.tensor_sha(a['train_index']) == N.tensor_sha(b['train_index'])
    assert N.tensor_sha(a['reserved_index']) == N.tensor_sha(b['reserved_index'])
    assert N.tensor_sha(a['codes']) != N.tensor_sha(
        N.build_pool('test/other', 'test/other/split')['codes'])


def test_code_scale_rule():
    """`code_scale` starts at the control entity rows' initialisation RMS norm."""
    assert abs(N.CODE_SCALE_INIT - .02*N.WIDTH**.5) < 1e-12
    control = N.new_control_model(3)
    norms = control.embedding.weight.detach()[N.ENTITY_MIN:].norm(dim=1)
    assert abs(float(norms.mean())/N.CODE_SCALE_INIT - 1) < .10, \
        (float(norms.mean()), N.CODE_SCALE_INIT)
    treatment = N.new_treatment_model(3)
    assert abs(float(treatment.code_scale.detach()) - N.CODE_SCALE_INIT) < 1e-9


def test_reserved_codes_are_unreachable_from_the_training_sampler():
    """Exhaustive over a long stream: nothing the trainer can draw is a reserved row.

    Identity of the POOL ROW is what is checked, not float equality of the vector, so a
    coincidental near-duplicate could not hide a leak.
    """
    pool = small_pool()
    subset = N.pool_subset(pool, 'train')
    reserved_rows = set(pool['reserved_index'].tolist())
    train_rows = pool['train_index'].tolist()
    seen = set()
    generator = random.Random('test:stream')
    for step in range(3000):
        _codes, index = N.assign_codes(subset, f'test:{step}:{generator.randrange(1 << 30)}',
                                       N.VISITS, N.ENTITIES)
        assert index.shape == (N.VISITS, N.ENTITIES)
        for row in index.reshape(-1).tolist():
            seen.add(train_rows[row])
    assert seen.isdisjoint(reserved_rows), 'a reserved code reached the training sampler'
    assert len(seen) == N.TRAIN_SIZE, \
        f'the stream should exercise the whole training half; saw {len(seen)}'
    reserved_subset = N.pool_subset(pool, 'reserved')
    wanted = pool['codes'].index_select(0, pool['reserved_index'])
    assert torch.equal(reserved_subset, wanted)


def test_codes_are_distinct_within_a_world():
    pool = small_pool()
    subset = N.pool_subset(pool, 'reserved')
    for step in range(50):
        _codes, index = N.assign_codes(subset, f'test:distinct:{step}', 8, N.ENTITIES)
        for world in index.tolist():
            assert len(set(world)) == N.ENTITIES, 'two people shared a name in one world'


def test_code_assignment_is_a_pure_function_of_its_key():
    pool = small_pool()
    subset = N.pool_subset(pool, 'train')
    a, ai = N.assign_codes(subset, 'k', 4, 16)
    b, bi = N.assign_codes(subset, 'k', 4, 16)
    c, _ci = N.assign_codes(subset, 'k2', 4, 16)
    assert torch.equal(a, b) and torch.equal(ai, bi)
    assert not torch.equal(a, c)


# ---------------------------------------------------------------- the treatment model

def test_parameter_counts():
    control, treatment = N.new_control_model(1), N.new_treatment_model(1)
    assert control.parameters_count() == 79316
    assert N.trainable_parameters(control) == 79316
    trainable = N.trainable_parameters(treatment)
    expected = 79316 - N.VOCAB*N.WIDTH - N.VOCAB + N.ENTITY_MIN*N.WIDTH + N.ENTITY_MIN + 2
    assert trainable == expected == 78534, (trainable, expected)
    assert trainable < N.trainable_parameters(control), 'the treatment must not add capacity'
    names = {n for n, p in treatment.named_parameters() if p.requires_grad}
    assert 'code_scale' in names and 'entity_output_bias' in names
    assert 'embedding.weight' not in names, 'the tied-head stub must never be trained'


def test_treatment_reproduces_the_control_when_the_codes_are_the_control_rows():
    """The only difference is per-entity output bias, which section 5 replaces by one."""
    control, treatment = N.new_control_model(7), N.new_treatment_model(7)
    batch = a_batch(7)
    with torch.no_grad():
        treatment.base_embedding.copy_(control.embedding.weight[:N.ENTITY_MIN])
        treatment.base_output_bias.copy_(control.output_bias[:N.ENTITY_MIN])
        treatment.code_scale.fill_(1.)
        entity = control.embedding.weight[N.ENTITY_MIN:].clone()
    codes = entity[None].expand(N.VISITS, -1, -1).contiguous()
    treatment.bind_batch(batch, codes)
    control.eval(); treatment.eval()
    with torch.no_grad():
        adjust = torch.cat((torch.zeros(N.ENTITY_MIN), control.output_bias[N.ENTITY_MIN:]))
        difference = (control(batch.canonical)-treatment(batch.canonical)-adjust).abs().max()
    assert float(difference) < 1e-5, float(difference)


def answer_state(treatment, codes, inputs):
    """The frozen forward's answer vector, reached through the identity tied head."""
    treatment._codes, treatment._lines = codes, inputs.memory.shape[1]
    treatment._owner = inputs.owner
    try:
        with torch.no_grad():
            return N.A.CanonicalOperator.forward(treatment, inputs)
    finally:
        treatment._codes = treatment._lines = treatment._owner = None


def test_tied_output_uses_the_same_per_world_codes():
    """Entity logits are exactly `answer . (code_scale * that world's code)` + one bias."""
    treatment = N.new_treatment_model(11)
    treatment.eval()
    batch = a_batch(11)
    inputs = batch.canonical
    pool = small_pool()
    codes, _index = N.assign_codes(N.pool_subset(pool, 'train'), 'test:tied',
                                   N.VISITS, N.ENTITIES)
    treatment.bind_batch(batch, codes)
    with torch.no_grad():
        logits = treatment(inputs)
    assert logits.shape[1] == N.ENTITY_MIN+N.ENTITIES == 68
    answer = answer_state(treatment, codes, inputs)
    with torch.no_grad():
        scale = treatment.code_scale.detach()
        entity = torch.einsum('qd,qvd->qv', answer, (scale*codes)[inputs.owner]) \
            + treatment.entity_output_bias.detach()
        base = answer @ treatment.base_embedding.detach().T \
            + treatment.base_output_bias.detach()
    assert torch.allclose(logits[:, N.ENTITY_MIN:], entity, atol=1e-6), \
        float((logits[:, N.ENTITY_MIN:]-entity).abs().max())
    assert torch.allclose(logits[:, :N.ENTITY_MIN], base, atol=1e-6)
    assert treatment.entity_output_bias.shape == torch.Size([]), 'one shared bias, not 16'
    other, _ = N.assign_codes(N.pool_subset(pool, 'reserved'), 'test:tied:other',
                              N.VISITS, N.ENTITIES)
    treatment.clear_bindings()
    treatment.bind_batch(batch, other)
    with torch.no_grad():
        changed = treatment(inputs)
    assert not torch.allclose(changed[:, N.ENTITY_MIN:], logits[:, N.ENTITY_MIN:]), \
        'different names must give different entity logits'


def test_story_tokens_and_question_tokens_share_one_code():
    """A person is ONE vector: the memory rows and the question use the same table row.

    Both sides carry the same positional term (a single token at position 0) and differ
    only by their type embedding, so subtracting `types[kind]` leaves exactly the code.
    """
    treatment = N.new_treatment_model(13)
    batch = a_batch(13)
    inputs = batch.canonical
    pool = small_pool()
    codes, _ = N.assign_codes(N.pool_subset(pool, 'train'), 'test:share', N.VISITS,
                              N.ENTITIES)
    treatment.bind_batch(batch, codes)
    worlds, lines = inputs.memory.shape[0], inputs.memory.shape[1]
    scale = float(treatment.code_scale.detach())
    treatment._codes, treatment._lines, treatment._owner = codes, lines, inputs.owner
    try:
        for person in (0, 5, N.ENTITIES-1):
            token = N.ENTITY_MIN+person
            with torch.no_grad():
                memory = treatment.embed(torch.full((worlds*lines, 1), token), 0) \
                    - treatment.types[0]
                question = treatment.embed(torch.full((len(inputs.owner), 1), token), 1) \
                    - treatment.types[1]
            for q, owner in enumerate(inputs.owner.tolist()):
                assert torch.allclose(question[q, 0], memory[owner*lines, 0], atol=1e-6), \
                    (person, q, owner)
            delta = memory[0, 0]-memory[lines, 0]
            assert torch.allclose(delta, scale*(codes[0, person]-codes[1, person]),
                                  atol=1e-6), person
    finally:
        treatment._codes = treatment._lines = treatment._owner = None



def test_codes_are_frozen_through_real_updates():
    N.configure_once()
    N.S.configure_variant(N.VARIANT, seed=17, **N.S.registered_params(N.VARIANT))
    treatment = N.new_treatment_model(17)
    optimizer = N.A.T.optimizer_for(treatment)
    pool = small_pool()
    subset = N.pool_subset(pool, 'train')
    rng = random.Random(1101)
    before_scale = float(treatment.code_scale.detach())
    kept = []
    for step in range(6):
        batch = N.A.training_batch(rng, N.VISITS, frozenset())
        codes, _ = N.assign_codes(subset, f'test:frozen:{step}', N.VISITS, N.ENTITIES)
        assert not codes.requires_grad
        kept.append((codes, N.tensor_sha(codes)))
        treatment.bind_batch(batch, codes)
        N.A.training_step(treatment, optimizer, batch, step)
        assert codes.grad is None, 'a code received a gradient'
        treatment.clear_bindings()
    for codes, sha in kept:
        assert N.tensor_sha(codes) == sha, 'a code tensor changed during training'
    assert N.tensor_sha(pool['codes']) == N.tensor_sha(small_pool()['codes']), \
        'the pool itself changed'
    assert float(treatment.code_scale.detach()) != before_scale, \
        'the one learned scale should move -- it is the only thing about codes that learns'
    state = treatment.state_dict()
    assert torch.equal(state['embedding.weight'], torch.eye(N.WIDTH)), \
        'the tied-head stub must stay the identity'
    assert torch.equal(state['output_bias'], torch.zeros(N.WIDTH))


def test_forward_refuses_an_unbound_world():
    treatment = N.new_treatment_model(19)
    batch = a_batch(19)
    try:
        treatment(batch.canonical)
    except RuntimeError as exc:
        assert 'no world codes' in str(exc), str(exc)
    else:
        raise AssertionError('an unbound forward must refuse, never guess a name')


def test_control_arm_reproduces_the_registered_recipe():
    """Parameter fingerprint after EVERY update, plus the registered on-disk anchor."""
    if not (EXP/'panels/manifest.json').exists():
        raise _Skip(f'no fixture panels at {EXP} (the exclusion set comes from there)')
    result = N.control_equivalence(0, EXP, updates=12)
    assert result['fingerprints_equal'], result['first_differing_update']
    assert result['losses_equal'] and result['max_abs_loss_difference'] == 0.
    anchor = result['registered_reference']
    if anchor:
        assert anchor['initial_matches'], anchor
    else:
        print('    (no registered grow-blind run on disk for seed 0; loop equality only)')


# ------------------------------------------------- C1: the code_scale heartbeat trace

SCALE_STEP = .001                  # the stub's deterministic nudge, not a training rate
BIAS_STEP = -.0005


@contextlib.contextmanager
def stub_training_calls():
    """Replace the three expensive per-update calls so 1,000 loop turns are free.

    C1 is logging, so what has to be exercised is the LOOP's bookkeeping at every 500th
    update, not the optimiser.  The stub keeps one real batch object (the treatment still
    binds codes to it, exactly as in training) and moves `code_scale` and
    `entity_output_bias` by a known amount per update, so the recorded trace can be
    checked against the parameter values those updates must have produced.

    The stubs are installed from inside `configure_recipe`, because
    `fable_operator_startup.configure_variant` rebinds `A.training_batch` and
    `A.training_step` itself -- anything installed earlier would be overwritten by the
    trainer's own call.
    """
    real_configure = N.configure_recipe
    saved = []

    def configure_recipe(seed):
        params = real_configure(seed)             # the recipe rebinds A.training_* here
        if not saved:
            saved.append((N.A.training_batch, N.A.training_flops, N.A.training_step))
        batch = N.A.training_batch(random.Random(1101), N.VISITS, frozenset())

        def training_batch(_rng, _visits, _forbidden):
            return batch

        def training_flops(_batch, _model):
            return 0

        def training_step(model, _optimizer, _batch, _step):
            if not hasattr(model, 'code_scale'):
                return                                    # the control has neither knob
            with torch.no_grad():
                model.code_scale += SCALE_STEP
                model.entity_output_bias += BIAS_STEP

        N.A.training_batch, N.A.training_flops, N.A.training_step = (
            training_batch, training_flops, training_step)
        return params

    N.configure_recipe = configure_recipe
    try:
        yield
    finally:
        N.configure_recipe = real_configure
        if saved:
            N.A.training_batch, N.A.training_flops, N.A.training_step = saved[0]


def stubbed_run(tmp, arm, updates, log_every, seed=9):
    """One `train_run` over the stub; returns (training.json, captured stdout)."""
    if not (EXP/'panels/manifest.json').exists():
        raise _Skip(f'no fixture panels at {EXP} (the exclusion set comes from there)')
    pool = fixture_pool()
    out = io.StringIO()
    with stub_training_calls(), contextlib.redirect_stdout(out):
        N.train_run(arm, seed, EXP, updates=updates, out=Path(tmp)/f'{arm}-{seed}',
                    pool=pool, log_every=log_every)
    return json.loads((Path(tmp)/f'{arm}-{seed}/training.json').read_text()), out.getvalue()


def test_scale_trace_is_recorded_at_every_500th_update_with_printing_off():
    def body(tmp):
        training, printed = stubbed_run(tmp, 'treatment', 1000, log_every=0)
        trace = training['scale_trace']
        assert [row['updates'] for row in trace] == [500, 1000], trace
        for row in trace:
            assert set(row) == {'updates', 'code_scale', 'entity_output_bias'}, row
            assert isinstance(row['code_scale'], float), row
            assert isinstance(row['entity_output_bias'], float), row
            assert abs(row['code_scale']
                       - (N.CODE_SCALE_INIT + SCALE_STEP*row['updates'])) < 1e-5, row
            assert abs(row['entity_output_bias']
                       - BIAS_STEP*row['updates']) < 1e-5, row
        assert 'training_seconds' not in printed, \
            'the heartbeat must stay silent when printing is off'
    with_tmp(body)


def test_scale_trace_is_none_for_the_control_arm():
    def body(tmp):
        training, printed = stubbed_run(tmp, 'control', 500, log_every=1)
        assert 'scale_trace' in training, 'the key is written for both arms'
        assert training['scale_trace'] is None, training['scale_trace']
        assert 'training_seconds' in printed, 'the control heartbeat still prints'
        beat = json.loads([line for line in printed.splitlines()
                           if 'training_seconds' in line][0])
        assert set(beat) == {'arm', 'seed', 'updates', 'training_seconds'}, beat
    with_tmp(body)


def test_treatment_heartbeat_prints_the_scale_and_the_bias():
    def body(tmp):
        training, printed = stubbed_run(tmp, 'treatment', 500, log_every=1)
        beat = json.loads([line for line in printed.splitlines()
                           if 'training_seconds' in line][0])
        assert set(beat) == {'arm', 'seed', 'updates', 'training_seconds',
                             'code_scale', 'entity_output_bias'}, beat
        assert beat['updates'] == 500
        assert training['scale_trace'] == [dict(updates=500,
                                                code_scale=beat['code_scale'],
                                                entity_output_bias=beat['entity_output_bias'])]
    with_tmp(body)


def test_scale_trace_is_empty_before_the_first_heartbeat():
    """A run shorter than 500 updates records no row -- and never crashes for it."""
    def body(tmp):
        training, _printed = stubbed_run(tmp, 'treatment', 3, log_every=1)
        assert training['scale_trace'] == [], training['scale_trace']
    with_tmp(body)


# ---------------------------------------------------------------- panels and scoring

def test_the_two_treatment_scorings_read_byte_identical_panels():
    pool, rows = fixture_pool(), fixture_panels()
    before = {cell: N.C.sha(row['path']) for cell, row in rows.items()}
    treatment = N.new_treatment_model(23)
    packed = {}
    for which in N.POOLS:
        subset = N.pool_subset(pool, which)
        packed[which] = []
        for cell, row in rows.items():
            panel = N.load_panel(row)
            treatment.clear_bindings()
            bound = treatment.bind_panel(panel, lambda i, w, c=cell: N.assign_codes(
                subset, f'{N.PANEL_CODE_NAMESPACE}:{which}:{c}:{i}', w, N.ENTITIES)[0])
            assert bound > 0
            for sides in N.P.chunks(panel):
                for side, (x, targets) in sorted(sides.items()):
                    packed[which].append((cell, side, N.tensor_sha(x.memory),
                                          N.tensor_sha(x.questions),
                                          N.tensor_sha(x.owner), tuple(targets)))
    assert packed['train'] == packed['reserved'], \
        'the two scorings must see identical packed inputs'
    after = {cell: N.C.sha(row['path']) for cell, row in rows.items()}
    assert before == after, 'scoring must never write to a panel file'


def test_both_sides_of_a_pair_share_their_codes():
    pool, rows = fixture_pool(), fixture_panels()
    subset = N.pool_subset(pool, 'reserved')
    treatment = N.new_treatment_model(29)
    paired = 0
    for cell, row in rows.items():
        panel = N.load_panel(row)
        treatment.clear_bindings()
        treatment.bind_panel(panel, lambda i, w, c=cell: N.assign_codes(
            subset, f'{N.PANEL_CODE_NAMESPACE}:reserved:{c}:{i}', w, N.ENTITIES)[0])
        for sides in N.P.chunks(panel):
            if len(sides) < 2:
                continue
            paired += 1
            shas = {N.tensor_sha(treatment.codes_for(x.memory))
                    for _side, (x, _t) in sides.items()}
            assert len(shas) == 1, f'{cell}: the two sides of a pair got different names'
    if not paired:
        raise _Skip('no pair cells in this fixture suite')


def test_panel_hashes_are_verified_before_use():
    rows = fixture_panels()
    cell, row = next(iter(rows.items()))
    broken = dict(row, sha256='0'*64)
    try:
        N.load_panel(broken)
    except RuntimeError as exc:
        assert 'changed on disk' in str(exc)
    else:
        raise AssertionError(f'{cell}: a tampered panel must be refused')


def test_outputs_refuse_to_overwrite():
    rows = fixture_panels()
    try:
        N.refuse_existing(Path(next(iter(rows.values()))['path']))
    except SystemExit as exc:
        assert 'refusing to overwrite' in str(exc)
    else:
        raise AssertionError('an existing path must be refused')


def test_source_fingerprint_covers_this_script_and_the_frozen_modules():
    files = N.source_files()
    names = {Path(p).name for p in files}
    for wanted in ('fable_newnames21.py', 'astra_canonical_operator.py',
                   'astra_canonical_operator_run.py', 'astra_canonical_operator_panels.py',
                   'fable_operator_startup.py', 'fable_confirmation_panels.py',
                   'premonition_token_memory.py', 'toy_ladder.py'):
        assert wanted in names, wanted
    assert N.source_fingerprint(files) == N.source_fingerprint(files)
    mutated = dict(files)
    mutated[next(iter(mutated))] = '0'*64
    assert N.source_fingerprint(mutated) != N.source_fingerprint(files)


def test_widened_entities_restores_the_frozen_range():
    assert (N.A.ENTITY_MIN, N.A.ENTITY_MAX) == (52, 68)
    with N.widened_entities(52+64):
        assert N.A.ENTITY_MAX == 116
    assert (N.A.ENTITY_MIN, N.A.ENTITY_MAX) == (52, 68)
    try:
        with N.widened_entities(52+64):
            raise ValueError('boom')
    except ValueError:
        pass
    assert (N.A.ENTITY_MIN, N.A.ENTITY_MAX) == (52, 68), 'restored even on an exception'


def test_wide64_worlds_have_the_declared_shape():
    world = N.wide_world(0, 64)
    assert world['people'] == 64
    assert world['facts'] == 256, world['facts']
    entities = {token for row in world['rows'] for token in row
                if token >= N.ENTITY_MIN}
    assert max(entities) == N.ENTITY_MIN+63, max(entities)
    assert len(world['questions']) == len(world['answers']) == len(world['kinds'])
    assert set(k.split('-')[0] for k in world['kinds']) <= {'attribute', 'link', 'two'}


# ---------------------------------------------------------------- gate arithmetic

def synthetic_scoring(values, link=.99, attribute=.99):
    cells = {}
    for cell in N.CELL_ORDER:
        n = N.PANEL_N
        cells[cell] = dict(
            R=values[cell], M=values[cell], n=n, cutoff=N.CUTOFFS[cell],
            diagnostics_by_operation=dict(
                by_first_operation={}, one_call_by_operation={
                    '8': dict(n=n, R=int(attribute*n)), '9': dict(n=n, R=int(attribute*n)),
                    '10': dict(n=n, R=int(attribute*n))},
                first_link_stage=dict(n=n, correct=int(link*n), accuracy=link)))
    return dict(cells=cells)


def flat(value):
    return {cell: value for cell in N.CELL_ORDER}


def write_synthetic(folder, arm, seed, reserved, train=None):
    scorings = ({'control': reserved} if arm == 'control'
                else {'reserved': reserved, 'train': train})
    (folder/'scores').mkdir(parents=True, exist_ok=True)
    (folder/'scores'/f'{arm}-{seed}.json').write_text(json.dumps(
        dict(arm=arm, seed=seed, scorings=scorings, cutoffs=N.CUTOFFS,
             cell_order=list(N.CELL_ORDER))))


def synthetic_experiment(tmp, control_pass, treatment_pass, drop=(), **kw):
    folder = Path(tmp)
    for i, seed in enumerate(N.SEEDS):
        if 'control' in drop:
            continue
        good = i < control_pass
        write_synthetic(folder, 'control', seed,
                        synthetic_scoring(flat(500 if good else 100)))
    for i, seed in enumerate(N.SEEDS):
        if 'treatment' in drop:
            continue
        good = i < treatment_pass
        reserved = synthetic_scoring(flat(500 if good else 100), **kw)
        train = synthetic_scoring(flat(500))
        write_synthetic(folder, 'treatment', seed, reserved, train)
    return folder


def with_tmp(function):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        return function(Path(tmp))


def test_gate_pass():
    def body(tmp):
        table = N.gate_table(synthetic_experiment(tmp, 3, 3))
        assert table['verdict'] == 'PASS', table
        assert table['treatment_seeds_passed'] == 3
    with_tmp(body)


def test_gate_partial():
    def body(tmp):
        table = N.gate_table(synthetic_experiment(tmp, 3, 2))
        assert table['verdict'] == 'PARTIAL', table['verdict']
        assert 'no claim' in table['reason']
    with_tmp(body)


def test_gate_fail():
    def body(tmp):
        table = N.gate_table(synthetic_experiment(tmp, 3, 1))
        assert table['verdict'] == 'FAIL', table['verdict']
    with_tmp(body)


def test_gate_void_when_the_control_does_not_reproduce():
    def body(tmp):
        table = N.gate_table(synthetic_experiment(tmp, 1, 3))
        assert table['verdict'] == 'VOID', table['verdict']
        assert table['reason'] == 'recipe did not reproduce'
    with_tmp(body)


def test_gate_incomplete():
    def body(tmp):
        table = N.gate_table(synthetic_experiment(tmp, 3, 3, drop=('treatment',)))
        assert table['verdict'] == 'INCOMPLETE', table['verdict']
        assert len(table['missing']) == 3
    with_tmp(body)


def test_paired_slack_is_the_binding_mark():
    """Cutoffs met but the reserved side slipping more than 13/512 must not pass."""
    def body(tmp):
        folder = Path(tmp)
        for seed in N.SEEDS:
            write_synthetic(folder, 'control', seed, synthetic_scoring(flat(500)))
            reserved = synthetic_scoring(dict(flat(500), c3=490))
            train = synthetic_scoring(dict(flat(500), c3=490+N.PAIRED_SLACK+1))
            write_synthetic(folder, 'treatment', seed, reserved, train)
        table = N.gate_table(folder)
        row = table['treatment'][str(N.SEEDS[0])]['cells']['c3']
        assert row['meets_cutoff'] and not row['meets_paired'], row
        assert table['verdict'] == 'FAIL', table['verdict']
        # exactly -13 is inside the mark
        folder2 = folder/'edge'
        for seed in N.SEEDS:
            write_synthetic(folder2, 'control', seed, synthetic_scoring(flat(500)))
            write_synthetic(folder2, 'treatment', seed,
                            synthetic_scoring(dict(flat(500), c3=490)),
                            synthetic_scoring(dict(flat(500), c3=490+N.PAIRED_SLACK)))
        assert N.gate_table(folder2)['verdict'] == 'PASS'
    with_tmp(body)


def test_signature_never_started():
    scoring = synthetic_scoring(flat(30))       # 30/512 is below 2x chance (64/512)
    signature = N.failure_signatures(scoring)
    assert signature['never_started'] is True
    assert N.failure_signatures(synthetic_scoring(flat(500)))['never_started'] is False


def test_signature_attributes_fine_link_at_chance():
    """The scale bug: every attribute relation healthy, every first LINK at chance."""
    scoring = synthetic_scoring(flat(300), link=.06, attribute=.99)
    signature = N.failure_signatures(scoring)
    assert signature['attributes_fine_link_at_chance'] is True, signature
    assert signature['one_call_attribute_accuracy'], 'the raw split must be emitted'
    assert signature['first_stage_link_accuracy'], 'the raw split must be emitted'
    healthy = N.failure_signatures(synthetic_scoring(flat(500), link=.97, attribute=.99))
    assert healthy['attributes_fine_link_at_chance'] is False
    broken_both = N.failure_signatures(synthetic_scoring(flat(30), link=.06, attribute=.05))
    assert broken_both['attributes_fine_link_at_chance'] is False, \
        'both broken is a never-started, not a scale bug'


def test_gates_and_signatures_are_emitted_together():
    def body(tmp):
        table = N.gate_table(synthetic_experiment(tmp, 3, 3, link=.05, attribute=.99))
        assert table['signature_summary']['attributes_fine_link_at_chance']
        assert set(table['signatures']) >= {f'treatment-{s}' for s in N.SEEDS}
    with_tmp(body)


def test_registered_constants_match_section_5():
    assert N.SEEDS == (2100, 2101, 2102)
    assert N.UPDATES == 6000 and N.VISITS == 16
    assert N.POOL_SIZE == 4096 and N.RESERVED_SIZE == 1024 and N.TRAIN_SIZE == 3072
    assert N.PAIRED_SLACK == 13
    assert [N.CUTOFFS[c] for c in ('c1', 'c2', 'p12-1', 'p12-2')] == [487]*4
    assert [N.CUTOFFS[c] for c in ('c3', 'c4', 'c5', 'c6', 'p12-3', 's3')] == [461]*6
    assert len(N.CELL_ORDER) == 10
    assert N.WIDE_PEOPLE == 64 and N.WIDE_PEOPLE*4 == 256
    assert N.VARIANT == 'grow-blind'
    assert N.S.registered_params(N.VARIANT)['blind_lines'] == 16


def test_fixture_step0_is_refused_for_the_registered_seeds():
    def body(tmp):
        try:
            N.train_run('control', N.SEEDS[0], EXP, updates=1, out=Path(tmp)/'r',
                        fixture_step0=10)
        except AssertionError as exc:
            assert 'fixture-step0' in str(exc), str(exc)
        except FileNotFoundError:
            raise _Skip('no fixture panels for the exclusion set')
        else:
            raise AssertionError('a registered seed must refuse a shifted curriculum clock')
    with_tmp(body)


TESTS = [(name, obj) for name, obj in sorted(globals().items())
         if name.startswith('test_') and callable(obj)]


def main():
    global EXP
    parser = argparse.ArgumentParser()
    parser.add_argument('--exp', default=str(DEFAULT_EXP))
    parser.add_argument('--only', default=None)
    args = parser.parse_args()
    EXP = Path(args.exp)
    N.configure_once()
    torch.manual_seed(0)
    for name, function in TESTS:
        if args.only and args.only not in name:
            continue
        check(name, function)
    print(f'\nPASSED {PASSED}  FAILED {FAILED}  SKIPPED {SKIPPED}', flush=True)
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
