"""Unit tests for `scripts/fable_newnames27.py` (experiment 27 / M1-F, frozen scale 1.2).

Plain script, no pytest, in this repository's house style: `check(name, function)`, a
`_Skip` for anything that needs a fixture that is not on this machine, and a PASSED /
FAILED / SKIPPED tally with a non-zero exit on any failure.

  python3.12 -B tests/test_fable_newnames27.py [--exp FIXTURE_EXP_DIR]

`--exp` (default `artifacts/fable-newnames27-20260921/fixtures/exp`) points at a small
DISPOSABLE fixture experiment folder -- a pool reference plus a 16-unit panel suite, built
with fixture namespaces, never the registered ones.  Tests that need it skip cleanly when
it is absent.  No registered seed (2103, 2104, 2105) is ever trained or scored here.

What is proved, in the order the design asks for it:

  the one change             `code_scale` is a constant BUFFER in arm F: not in
                             `parameters()` (so it cannot reach `clip_grad_norm_`), no
                             gradient, unchanged by real optimizer updates, and identical
                             to arm L's start value at construction.
  a violation is INVALID     nudging the buffer raises `FrozenScaleViolation`, the run
                             writes `failure.json` with `invalid: true`, and `gates` turns
                             the whole experiment INVALID.
  control equivalence        this file's control path against the registered functions AND
                             against `fable_newnames21`'s own control path, tensor for
                             tensor.
  arm L reproduces 21        arm L started at 0.13856 lands on experiment 21's treatment
                             fingerprint, tensor for tensor.
  the trace is inert         the 100-update trace on and off gives identical parameters.
  the pool is REUSED         the same tensors as experiment 21's frozen pool, hash-checked,
                             and no reserved code is reachable from the training sampler.
  panels                     experiment 27's own code namespace, byte-identical panel files
                             across the two scorings, paired sides sharing their codes.
  gate arithmetic            synthetic tables driving PASS, PARTIAL, FAIL, VOID, INCOMPLETE
                             and INVALID, the two-sided paired warning, and every one of
                             the six pre-named failure signatures with its sub-label.
  arm L is descriptive       no verdict moves when arm L fails.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import random
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'scripts'))

import fable_newnames27 as X                                              # noqa: E402

N = X.N
torch = X.torch
DEFAULT_EXP = HERE.parent/'artifacts/fable-newnames27-20260921/fixtures/exp'
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


def with_tmp(function):
    with tempfile.TemporaryDirectory() as tmp:
        return function(Path(tmp))


def need_fixture():
    if not (EXP/'panels/manifest.json').exists():
        raise _Skip(f'no fixture panels at {EXP}')
    if not (EXP/'pool/pool-ref.json').exists():
        raise _Skip(f'no fixture pool reference at {EXP}')


def fixture_pool():
    need_fixture()
    return X.load_pool(EXP)


def fixture_panels():
    need_fixture()
    return X.panel_paths(EXP)


def a_batch(seed=5):
    X.configure_recipe(seed)
    return X.A.training_batch(random.Random(1101), X.VISITS, frozenset())


# ---------------------------------------------------------------- registration

def test_registered_constants_match_design_27():
    assert X.SEEDS == (2103, 2104, 2105)
    assert X.ARMS == ('control', 'F', 'L') and X.CODE_ARMS == ('F', 'L')
    assert X.CODE_SCALE == 1.2 and X.L_CODE_SCALE_START == 1.2
    assert X.TRACE_EVERY == 100, 'design 4.6: every 100 updates, not 21\'s 500'
    assert X.UPDATES == 6000 and X.VISITS == 16
    assert X.PAIRED_SLACK == 13 and X.PANEL_N == 512
    assert [X.CUTOFFS[c] for c in ('c1', 'c2', 'p12-1', 'p12-2')] == [487]*4
    assert [X.CUTOFFS[c] for c in ('c3', 'c4', 'c5', 'c6', 'p12-3', 's3')] == [461]*6
    assert len(X.CELL_ORDER) == 10
    assert X.VARIANT == 'grow-blind'
    assert (X.SCALE_COLLAPSED_AT, X.SCALE_COLLAPSED_FROM) == (.05, 500)
    assert (X.BIAS_EXIT_AT, X.GAIN_EXIT_AT) == (-3.0, 3.5)
    assert X.LINK_CHANCE_AT == .125 and X.ATTRIBUTES_FINE_AT == .90
    # the namespaces must be fresh, never experiment 21's
    for mine, theirs in ((X.TRAIN_CODE_NAMESPACE, N.TRAIN_CODE_NAMESPACE),
                         (X.PANEL_CODE_NAMESPACE, N.PANEL_CODE_NAMESPACE),
                         (X.PANEL_NAMESPACE, N.PANEL_NAMESPACE)):
        assert mine != theirs, (mine, theirs)
    assert X.PANEL_SEED_BASE != N.PANEL_SEED_BASE
    assert set(X.SEEDS).isdisjoint(N.SEEDS), 'the spent seeds are never reused'


def test_value_row_window_matches_the_frozen_generator():
    X.data.bootstrap()
    from premonition.toy_ladder import LadderSpec
    spec = LadderSpec()
    assert X.VALUE_MIN == spec.value(0)
    assert X.VALUE_COUNT == spec.values == 16
    assert X.VALUE_MIN+X.VALUE_COUNT-1 == spec.value(spec.values-1)
    assert X.LINK == spec.link


def test_source_fingerprint_covers_both_scripts():
    files = X.source_files()
    names = {Path(p).name for p in files}
    for wanted in ('fable_newnames27.py', 'fable_newnames21.py',
                   'astra_canonical_operator.py', 'astra_canonical_operator_run.py',
                   'fable_operator_startup.py', 'fable_confirmation_panels.py',
                   'premonition_token_memory.py', 'toy_ladder.py'):
        assert wanted in names, wanted
    assert X.source_fingerprint(files) == X.source_fingerprint(files)
    assert X.source_fingerprint(files) != N.source_fingerprint()


# ---------------------------------------------------------------- THE ONE CHANGE

def test_code_scale_is_a_buffer_not_a_parameter():
    model = X.new_F_model(3)
    names = {n for n, _p in model.named_parameters()}
    buffers = {n for n, _b in model.named_buffers()}
    assert 'code_scale' not in names, 'a parameter would still enter clip_grad_norm_'
    assert 'code_scale' in buffers
    assert 'code_scale' in model.state_dict(), 'a reload must be exact'
    assert not model.code_scale.requires_grad
    assert abs(float(model.code_scale)-1.2) < 1e-6
    assert all(p is not model.code_scale for p in model.parameters())


def test_frozen_scale_is_invisible_to_the_gradient_clipper():
    """Design 4.1's reason for a buffer: it must not be in `parameters()` at all."""
    model = X.new_F_model(4)
    assert all(p is not model.code_scale for p in model.parameters())
    learned = X.new_L_model(4)
    assert any(p is learned.code_scale for p in learned.parameters())
    assert len(list(model.parameters())) == len(list(learned.parameters()))-1


def test_parameter_counts():
    control = X.new_control_model(1)
    frozen, learned = X.new_F_model(1), X.new_L_model(1)
    assert X.trainable_parameters(control) == 79316
    assert X.trainable_parameters(learned) == 78534, 'experiment 21\'s treatment'
    assert X.trainable_parameters(frozen) == 78533, 'design 27: one fewer'
    assert X.trainable_parameters(frozen) == X.trainable_parameters(learned)-1
    assert frozen.parameters_count() == learned.parameters_count()-1


def test_F_and_L_start_from_the_same_weights():
    """Only `requires_grad` differs, so the construction stream is unchanged."""
    frozen, learned = X.new_F_model(23), X.new_L_model(23)
    assert X.C.fingerprint(frozen) == X.C.fingerprint(learned)
    state_f, state_l = frozen.state_dict(), learned.state_dict()
    assert sorted(state_f) == sorted(state_l)
    for key in state_f:
        assert torch.equal(state_f[key], state_l[key]), key


def test_F_and_L_give_the_same_logits_at_the_same_scale():
    frozen, learned = X.new_F_model(25), X.new_L_model(25)
    batch = a_batch(25)
    pool = fixture_pool()
    codes, _ = X.assign_codes(X.pool_subset(pool, 'train'), 'test:same', X.VISITS,
                              X.ENTITIES)
    for model in (frozen, learned):
        model.eval()
        model.bind_batch(batch, codes)
    with torch.no_grad():
        difference = (frozen(batch.canonical)-learned(batch.canonical)).abs().max()
    assert float(difference) == 0., float(difference)


def test_the_frozen_buffer_survives_real_updates():
    X.configure_recipe(17)
    frozen = X.new_F_model(17)
    optimizer = X.A.T.optimizer_for(frozen)
    pool = fixture_pool()
    subset = X.pool_subset(pool, 'train')
    rng = random.Random(1101)
    before = X.tensor_sha(frozen.code_scale)
    for step in range(6):
        batch = X.A.training_batch(rng, X.VISITS, frozenset())
        codes, _ = X.assign_codes(subset, f'test:frozen:{step}', X.VISITS, X.ENTITIES)
        frozen.bind_batch(batch, codes)
        X.A.training_step(frozen, optimizer, batch, step)
        assert frozen.code_scale.grad is None, 'the buffer received a gradient'
        frozen.check_frozen(f'after update {step}')
        frozen.clear_bindings()
    assert X.tensor_sha(frozen.code_scale) == before
    assert float(frozen.code_scale) == frozen.frozen_code_scale


def test_the_learned_scale_does_move_in_arm_L():
    X.configure_recipe(18)
    learned = X.new_L_model(18)
    optimizer = X.A.T.optimizer_for(learned)
    pool = fixture_pool()
    subset = X.pool_subset(pool, 'train')
    rng = random.Random(1101)
    before = float(learned.code_scale.detach())
    for step in range(6):
        batch = X.A.training_batch(rng, X.VISITS, frozenset())
        codes, _ = X.assign_codes(subset, f'test:learned:{step}', X.VISITS, X.ENTITIES)
        learned.bind_batch(batch, codes)
        X.A.training_step(learned, optimizer, batch, step)
        learned.clear_bindings()
    assert float(learned.code_scale.detach()) != before, \
        'arm L keeps the dial; that is the whole difference'


def test_check_frozen_catches_a_moved_buffer():
    model = X.new_F_model(19)
    with torch.no_grad():
        model.code_scale += 1e-7
    try:
        model.check_frozen('in the test')
    except X.FrozenScaleViolation as exc:
        assert 'moved' in str(exc), str(exc)
    else:
        raise AssertionError('any change at all must be refused')


def test_a_moved_buffer_makes_the_run_invalid():
    """The trainer must write failure.json with `invalid: true`, not a quiet result."""
    need_fixture()
    pool = fixture_pool()
    real = X.new_F_model

    class Saboteur(X.FrozenScaleOperator):
        """Moves the buffer mid-run.  (Patching `A.training_step` would not do: the
        registered `configure_variant` rebinds that attribute inside `train_run`.)"""

        def bind_batch(self, batch, codes):
            super().bind_batch(batch, codes)
            with torch.no_grad():
                self.code_scale += .5

    def sabotage(seed, code_scale=X.CODE_SCALE):
        model = real(seed, code_scale)
        model.__class__ = Saboteur
        return model

    def body(tmp):
        X.new_F_model = sabotage
        try:
            X.train_run('F', 9, EXP, updates=2, out=tmp/'F-9', pool=pool, log_every=0)
        except X.FrozenScaleViolation:
            pass
        else:
            raise AssertionError('a moved buffer must abort the run')
        finally:
            X.new_F_model = real
        row = json.loads((tmp/'F-9/failure.json').read_text())
        assert row['invalid'] is True and 'INVALID' in row['reason'], row
        assert not (tmp/'F-9/completion.json').exists()
    with_tmp(body)


# ---------------------------------------------------------------- the reused pool

def test_the_pool_is_experiment_21s_tensors_not_a_new_draw():
    pool = fixture_pool()
    reference = pool['reference']
    parent = N.load_pool(Path(reference['source']))
    for key in ('codes', 'train_index', 'reserved_index'):
        assert torch.equal(pool[key], parent[key]), key
    assert X.tensor_sha(pool['codes']) == reference['codes_sha256']
    assert reference['train_size'] == 3072 and reference['reserved_size'] == 1024


def test_a_tampered_pool_reference_is_refused():
    need_fixture()

    def body(tmp):
        reference = json.loads((EXP/'pool/pool-ref.json').read_text())
        reference['codes_sha256'] = '0'*64
        (tmp/'pool').mkdir()
        (tmp/'pool/pool-ref.json').write_text(json.dumps(reference))
        try:
            X.load_pool(tmp)
        except RuntimeError as exc:
            assert 'changed' in str(exc), str(exc)
        else:
            raise AssertionError('a changed pool tensor must be refused')
    with_tmp(body)


def test_reserved_codes_are_unreachable_from_experiment_27s_training_stream():
    """Exhaustive over a long stream drawn with THIS experiment's namespace."""
    pool = fixture_pool()
    subset = X.pool_subset(pool, 'train')
    reserved = set(pool['reserved_index'].tolist())
    train_rows = pool['train_index'].tolist()
    key = f'{X.TRAIN_CODE_NAMESPACE}:{X.SEEDS[0]}'
    generator = random.Random(key)
    seen = set()
    for step in range(2000):
        _codes, index = X.assign_codes(subset, f'{key}:{step}:{generator.randrange(1 << 30)}',
                                       X.VISITS, X.ENTITIES)
        assert index.shape == (X.VISITS, X.ENTITIES)
        for row in index.reshape(-1).tolist():
            seen.add(train_rows[row])
    assert seen.isdisjoint(reserved), 'a reserved code reached the training sampler'
    assert len(seen) == 3072, len(seen)


# ---------------------------------------------------------------- panels and scoring

def test_panel_codes_use_experiment_27s_namespace():
    pool, rows = fixture_pool(), fixture_panels()
    subset = X.pool_subset(pool, 'reserved')
    model = X.new_F_model(29)
    cell = 'c1'
    panel = X.load_panel(rows[cell])
    X.bind_cell(model, panel, subset, 'reserved', cell)
    mine = {X.tensor_sha(model.codes_for(x.memory))
            for sides in X.P.chunks(panel) for x, _t in sides.values()}
    theirs = {X.tensor_sha(X.assign_codes(
        subset, f'{N.PANEL_CODE_NAMESPACE}:reserved:{cell}:{i}', w, X.ENTITIES)[0])
        for i, sides in enumerate(X.P.chunks(panel))
        for w in [next(iter(sides.values()))[0].memory.shape[0]]}
    assert mine and theirs and mine.isdisjoint(theirs), \
        'experiment 27 must not reuse experiment 21\'s panel names'


def test_the_two_scorings_read_byte_identical_panels():
    pool, rows = fixture_pool(), fixture_panels()
    before = {cell: X.C.sha(row['path']) for cell, row in rows.items()}
    model = X.new_F_model(31)
    packed = {}
    for which in X.POOLS:
        subset = X.pool_subset(pool, which)
        packed[which] = []
        for cell, row in rows.items():
            panel = X.load_panel(row)
            assert X.bind_cell(model, panel, subset, which, cell) > 0
            for sides in X.P.chunks(panel):
                for side, (x, targets) in sorted(sides.items()):
                    packed[which].append((cell, side, X.tensor_sha(x.memory),
                                          X.tensor_sha(x.questions),
                                          X.tensor_sha(x.owner), tuple(targets)))
    assert packed['train'] == packed['reserved']
    assert before == {cell: X.C.sha(row['path']) for cell, row in rows.items()}


def test_both_sides_of_a_pair_share_their_codes():
    pool, rows = fixture_pool(), fixture_panels()
    subset = X.pool_subset(pool, 'reserved')
    model = X.new_F_model(33)
    paired = 0
    for cell, row in rows.items():
        panel = X.load_panel(row)
        X.bind_cell(model, panel, subset, 'reserved', cell)
        for sides in X.P.chunks(panel):
            if len(sides) < 2:
                continue
            paired += 1
            shas = {X.tensor_sha(model.codes_for(x.memory))
                    for _side, (x, _t) in sides.items()}
            assert len(shas) == 1, f'{cell}: the two sides of a pair got different names'
    if not paired:
        raise _Skip('no pair cells in this fixture suite')


def test_panel_hashes_are_verified_before_use():
    rows = fixture_panels()
    cell, row = next(iter(rows.items()))
    try:
        X.load_panel(dict(row, sha256='0'*64))
    except RuntimeError as exc:
        assert 'changed on disk' in str(exc)
    else:
        raise AssertionError(f'{cell}: a tampered panel must be refused')


def test_outputs_refuse_to_overwrite():
    rows = fixture_panels()
    try:
        X.refuse_existing(Path(next(iter(rows.values()))['path']))
    except SystemExit as exc:
        assert 'refusing to overwrite' in str(exc)
    else:
        raise AssertionError('an existing path must be refused')


def test_train_run_refuses_an_existing_run_folder():
    need_fixture()

    def body(tmp):
        (tmp/'busy').mkdir()
        try:
            X.train_run('F', 9, EXP, updates=1, out=tmp/'busy', log_every=0)
        except SystemExit as exc:
            assert 'refusing to overwrite' in str(exc)
        else:
            raise AssertionError('an existing run folder must be refused')
    with_tmp(body)


def test_replay_seed_context_restores_experiment_21s_seeds():
    assert N.SEEDS == (2100, 2101, 2102)
    with X.replay_seeds():
        assert N.SEEDS == X.SEEDS
    assert N.SEEDS == (2100, 2101, 2102)
    try:
        with X.replay_seeds():
            raise ValueError('boom')
    except ValueError:
        pass
    assert N.SEEDS == (2100, 2101, 2102), 'restored even on an exception'


# ---------------------------------------------------------------- the registered guards

def test_the_registered_seeds_refuse_every_override():
    need_fixture()

    def body(tmp):
        for kwargs in (dict(code_scale=.5), dict(code_namespace='x'),
                       dict(trace_every=0), dict(fixture_step0=10)):
            try:
                X.train_run('F', X.SEEDS[0], EXP, updates=1, out=tmp/str(kwargs),
                            log_every=0, **kwargs)
            except AssertionError as exc:
                assert 'refuse' in str(exc) or 'fixture-step0' in str(exc), str(exc)
            else:
                raise AssertionError(f'a registered seed accepted {kwargs}')
    with_tmp(body)


def test_the_registered_seeds_refuse_a_short_run():
    """AUDIT-27 §2.1: a 3-update run on 2103 would write a completion.json saying
    "complete" and reach the gates looking like a 6,000-update run."""
    need_fixture()

    def body(tmp):
        for updates in (3, 5999, 6001):
            try:
                X.train_run('F', X.SEEDS[0], EXP, updates=updates, out=tmp/str(updates),
                            log_every=0)
            except AssertionError as exc:
                assert 'refuse' in str(exc) and 'updates' in str(exc), str(exc)
            else:
                raise AssertionError(f'a registered seed accepted {updates} updates')
            assert not (tmp/str(updates)).exists(), 'nothing may be created either'
        # the registered number itself is of course accepted (it is not an override)
        assert X.UPDATES == 6000
    with_tmp(body)


def test_load_checkpoint_refuses_a_checkpoint_saved_at_the_wrong_scale():
    """AUDIT-27 MINOR-8: arm F is rebuilt at the REGISTERED 1.2, not at the number the
    file claims, so a doctored `architecture` cannot make check_frozen self-consistent."""
    run = EXP/'runs/F-9/final.pt'
    if not run.exists():
        raise _Skip('no fixture F-9 checkpoint')

    def body(tmp):
        saved = X.P.load(run)
        saved['architecture'] = dict(saved['architecture'], code_scale=.5)
        doctored = tmp/'doctored.pt'
        torch.save(saved, doctored)
        try:
            X.load_checkpoint(doctored)
        except AssertionError as exc:
            assert 'not the registered' in str(exc), str(exc)
        else:
            raise AssertionError('a checkpoint recording a different scale must be refused')
    with_tmp(body)


def test_checkpoints_named_test_pt_are_prohibited():
    try:
        X.load_checkpoint(Path('/nowhere/test.pt'))
    except ValueError as exc:
        assert 'test.pt is prohibited' in str(exc)
    else:
        raise AssertionError('test.pt must never be loaded')


# ---------------------------------------------------------------- the trace (design 4.6)

def short_run(tmp, arm, updates, trace_every=X.TRACE_EVERY, seed=9, **kwargs):
    need_fixture()
    training = X.train_run(arm, seed, EXP, updates=updates, out=Path(tmp)/f'{arm}-{seed}',
                           pool=fixture_pool(), log_every=0, trace_every=trace_every,
                           **kwargs)
    return training


def test_the_trace_is_recorded_every_100_updates_for_the_code_arms():
    def body(tmp):
        training = short_run(tmp, 'F', 200)
        trace = training['trace']
        assert [row['updates'] for row in trace] == [100, 200], trace
        for row in trace:
            assert tuple(row) == X.TRACE_KEYS, tuple(row)
            for key in X.TRACE_KEYS:
                assert isinstance(row[key], (int, float)), (key, row[key])
            assert row['code_scale'] == training['code_scale_final'] == \
                trace[-1]['code_scale']
            assert abs(row['effective_name_scale']
                       - row['code_scale']*row['mean_answer_length']) < 1e-6
            assert 0. <= row['name_mass_link'] <= 1. and 0. <= row['name_mass_value'] <= 1.
        assert training['trace_summary']['rows'] == 2
    with_tmp(body)


def test_the_control_arm_records_no_trace():
    def body(tmp):
        training = short_run(tmp, 'control', 100)
        assert training['trace'] is None and training['trace_summary'] is None
        assert training['trace_every'] is None
        assert training['code_scale_final'] is None
        assert training['code_scale_is_buffer'] is False
    with_tmp(body)


def test_the_trace_is_inert():
    """Design 4.6's proof, on the fixture seed: same parameters with logging on and off."""
    need_fixture()

    def body(tmp):
        result = X.inertness(EXP, updates=100, seed=9, arms=('F',), scratch=tmp)
        row = result['arms']['F']
        assert row['final_equal'] and row['tensors_equal'] and row['initial_equal'], row
        assert row['flops_equal']
        assert (row['trace_rows_on'], row['trace_rows_off']) == (1, 0), row
        assert result['all_inert']
    with_tmp(body)


def test_trace_summary_arithmetic():
    trace = [dict(updates=u, code_scale=s, entity_output_bias=-.1,
                  mean_answer_length=9., effective_name_scale=9.*s,
                  answer_norm_gain_rms=1., value_row_mean_length=.4, answer_loss=1.,
                  link_accuracy=.5, attribute_accuracy=.9, name_mass_link=.9,
                  name_mass_value=.01)
             for u, s in ((100, .01), (400, .02), (500, .9), (600, 1.1))]
    summary = X.trace_summary(trace, 'L')
    assert summary['min_abs_code_scale_from_500'] == .9, summary
    assert summary['scale_collapsed'] is False, 'the dip before 500 does not count'
    collapsed = X.trace_summary(trace[:2]+[dict(trace[2], code_scale=.01)], 'L')
    assert collapsed['scale_collapsed'] is True
    assert X.trace_summary(trace[:2]+[dict(trace[2], code_scale=.01)],
                           'F')['scale_collapsed'] is False, \
        'scale_collapsed is an arm-L label; for F a moved buffer is INVALID'
    assert X.trace_summary([], 'L') is None


# ---------------------------------------------------------------- equivalence proofs

def test_control_equivalence_against_21_and_against_the_registered_functions():
    need_fixture()

    def body(tmp):
        result = X.control_equivalence(0, EXP, updates=8, scratch=tmp)
        assert result['fingerprints_equal'], result['first_differing_update']
        assert result['losses_equal'] and result['max_abs_loss_difference'] == 0.
        against = result['against_experiment_21']
        assert against['initial_equal'] and against['final_equal'], against
        assert against['tensors_equal'] and against['tensors_compared'] > 40, against
        assert against['mismatched_tensors'] == []
        anchor = result['registered_reference']
        if anchor:
            assert anchor['initial_matches'], anchor
        else:
            print('    (no registered grow-blind run on disk for seed 0)')
    with_tmp(body)


def test_arm_L_at_013856_reproduces_experiment_21s_treatment():
    need_fixture()

    def body(tmp):
        result = X.treatment_equivalence(9, EXP, updates=8, scratch=tmp)
        assert result['initial_equal'] and result['final_equal'], result
        assert result['tensors_equal'] and result['mismatched_tensors'] == []
        assert result['exp27_trainable'] == result['exp21_trainable'] == 78534
        assert result['code_scale_start'] == N.CODE_SCALE_INIT
    with_tmp(body)


# ---------------------------------------------------------------- descriptive read-outs

def test_line_attention_maps_tokens_back_to_story_lines():
    pool, rows = fixture_pool(), fixture_panels()
    model = X.new_F_model(37)
    model.eval()
    panel = X.load_panel(rows['c2'])
    X.bind_cell(model, panel, X.pool_subset(pool, 'reserved'), 'reserved', 'c2')
    sides = next(iter(X.P.chunks(panel)))
    x, _targets = sides['a']
    paths = X.A.truth_paths(x)
    ids = [i for i, path in enumerate(paths) if path and path[0]['operation'] == X.LINK]
    if not ids:
        raise _Skip('no first-stage LINK records in this fixture cell')
    stage = X.A.canonical_input(x, [paths[i][0]['entity'] for i in ids],
                                [X.LINK]*len(ids), ids)
    with torch.no_grad():
        _logits, attention = model(stage, trace=True)
    mass = X.line_attention(stage, attention)
    assert mass.shape == (len(ids), x.memory.shape[1]), tuple(mass.shape)
    total = mass.sum(-1)
    assert float(total.max()) <= 1.0001 and float(total.min()) > .5, \
        'the NULL key holds the rest; the story lines must hold nearly all of it'
    assert int(mass.argmax(-1).max()) < x.memory.shape[1]


def test_openset_readout_counts_and_monotonicity():
    pool, rows = fixture_pool(), fixture_panels()
    run = EXP/'runs/F-9/final.pt'
    if not run.exists():
        raise _Skip('no fixture F-9 checkpoint')
    model, _sha, _saved = X.load_checkpoint(run)
    few = X.openset_readout(model, EXP, pool, 'reserved', 'reserved', rows)
    many = X.openset_readout(model, EXP, pool, 'reserved', 'all', rows)
    assert few['candidate_count'] == 1024 and many['candidate_count'] == 4096
    assert few['n'] == many['n'] > 0
    assert many['correct'] <= few['correct'], \
        'more distractors can only cost accuracy, never gain it'
    assert few['cells']['c1']['n'] == 0, 'c1 has no first-stage LINK'
    assert few['cells']['c2']['n'] > 0


def test_attention_readout_shape():
    pool, rows = fixture_pool(), fixture_panels()
    run = EXP/'runs/F-9/final.pt'
    if not run.exists():
        raise _Skip('no fixture F-9 checkpoint')
    model, _sha, _saved = X.load_checkpoint(run)
    out = X.attention_readout(model, EXP, pool, 'reserved', rows)
    assert out['n'] > 0 and 0 <= out['wrong'] <= out['n']
    assert 0 <= out['right_line_attended'] <= out['wrong']
    assert out['fraction'] is None or 0. <= out['fraction'] <= 1.
    assert 'DESCRIPTIVE' in out['note']


# ---------------------------------------------------------------- gate arithmetic

def synthetic_scoring(values, link=.99, attribute=.99):
    cells = {}
    for cell in X.CELL_ORDER:
        n = X.PANEL_N
        cells[cell] = dict(
            R=values[cell], M=values[cell], n=n, cutoff=X.CUTOFFS[cell],
            diagnostics_by_operation=dict(
                by_first_operation={}, one_call_by_operation={
                    '8': dict(n=n, R=int(attribute*n)), '9': dict(n=n, R=int(attribute*n)),
                    '10': dict(n=n, R=int(attribute*n))},
                first_link_stage=dict(n=n, correct=int(link*n), accuracy=link)))
    return dict(cells=cells)


def flat(value):
    return {cell: value for cell in X.CELL_ORDER}


def synthetic_summary(**kw):
    row = dict(rows=60, first_update=100, final_update=6000,
               min_abs_code_scale_from_500=1.1, final_code_scale=1.2,
               final_entity_output_bias=-.2, final_mean_answer_length=10.,
               final_effective_name_scale=12., final_link_accuracy=.9,
               final_attribute_accuracy=.95, scale_collapsed=False,
               scale_collapsed_rule='')
    row.update(kw)
    return row


def write_synthetic(folder, arm, seed, reserved, train=None, summary=None, buffer_ok=None):
    scorings = ({'control': reserved} if arm == 'control'
                else {'reserved': reserved, 'train': train})
    (folder/'scores').mkdir(parents=True, exist_ok=True)
    (folder/'scores'/f'{arm}-{seed}.json').write_text(json.dumps(
        dict(arm=arm, seed=seed, scorings=scorings, cutoffs=X.CUTOFFS,
             cell_order=list(X.CELL_ORDER), trace_summary=summary,
             buffer_ok=buffer_ok if arm != 'control' else None,
             code_scale_final=1.2 if arm != 'control' else None)))


def synthetic_experiment(tmp, control_pass=3, f_pass=3, l_pass=3, drop=(), **kw):
    folder = Path(tmp)
    counts = dict(control=control_pass, F=f_pass, L=l_pass)
    for arm in X.ARMS:
        if arm in drop:
            continue
        for i, seed in enumerate(X.SEEDS):
            good = i < counts[arm]
            reserved = synthetic_scoring(flat(500 if good else 100), **kw)
            if arm == 'control':
                write_synthetic(folder, arm, seed, reserved)
            else:
                write_synthetic(folder, arm, seed, reserved, synthetic_scoring(flat(500)),
                                summary=synthetic_summary(),
                                buffer_ok=True if arm == 'F' else None)
    return folder


def test_gate_pass():
    def body(tmp):
        table = X.gate_table(synthetic_experiment(tmp))
        assert table['verdict'] == 'PASS', table['reason']
        assert table['F_seeds_passed'] == 3
    with_tmp(body)


def test_gate_partial_and_fail():
    def body(tmp):
        assert X.gate_table(synthetic_experiment(tmp/'a', f_pass=2))['verdict'] == 'PARTIAL'
        assert X.gate_table(synthetic_experiment(tmp/'b', f_pass=1))['verdict'] == 'FAIL'
        assert X.gate_table(synthetic_experiment(tmp/'c', f_pass=0))['verdict'] == 'FAIL'
    with_tmp(body)


def test_gate_void_when_the_control_does_not_reproduce():
    def body(tmp):
        table = X.gate_table(synthetic_experiment(tmp, control_pass=1))
        assert table['verdict'] == 'VOID' and table['reason'] == 'recipe did not reproduce'
    with_tmp(body)


def test_gate_incomplete_ignores_a_missing_L_wave():
    def body(tmp):
        table = X.gate_table(synthetic_experiment(tmp/'a', drop=('L',)))
        assert table['verdict'] == 'PASS', table['reason']
        assert table['missing'] == [], 'wave 2 is descriptive; it cannot block the verdict'
        table = X.gate_table(synthetic_experiment(tmp/'b', drop=('F',)))
        assert table['verdict'] == 'INCOMPLETE' and len(table['missing']) == 3
    with_tmp(body)


def test_gate_invalid_when_the_buffer_moved():
    def body(tmp):
        folder = synthetic_experiment(tmp/'a')
        # a passing seed whose buffer nonetheless moved: still INVALID, never PASS
        write_synthetic(folder, 'F', X.SEEDS[0], synthetic_scoring(flat(500)),
                        synthetic_scoring(flat(500)), summary=synthetic_summary(),
                        buffer_ok=False)
        table = X.gate_table(folder)
        assert table['verdict'] == 'INVALID', table
        assert table['buffer_violations'] == [f'F-{X.SEEDS[0]}']
        # and a failure.json marked invalid does the same
        folder2 = synthetic_experiment(tmp/'b')
        run = folder2/'runs'/f'F-{X.SEEDS[1]}'
        run.mkdir(parents=True)
        (run/'failure.json').write_text(json.dumps(
            dict(arm='F', seed=X.SEEDS[1], invalid=True, reason='the frozen code_scale '
                 'changed; the run is INVALID')))
        assert X.gate_table(folder2)['verdict'] == 'INVALID'
    with_tmp(body)


def write_training(folder, arm, seed, updates=None, fingerprint='f'*64, overrides=None):
    run = Path(folder)/'runs'/f'{arm}-{seed}'
    run.mkdir(parents=True, exist_ok=True)
    (run/'training.json').write_text(json.dumps(
        dict(arm=arm, seed=seed, updates=X.UPDATES if updates is None else updates,
             source_fingerprint=fingerprint, overrides=overrides or {})))


def full_run_set(folder, **kw):
    for arm in X.ARMS:
        for seed in X.SEEDS:
            write_training(folder, arm, seed, **kw)


def test_run_integrity_accepts_a_full_set():
    def body(tmp):
        folder = synthetic_experiment(tmp)
        full_run_set(folder)
        table = X.gate_table(folder)
        assert table['integrity']['problems'] == [], table['integrity']
        assert len(table['integrity']['runs']) == 9
        assert table['integrity']['source_fingerprints'] == ['f'*64]
        assert table['verdict'] == 'PASS', table['reason']
    with_tmp(body)


def test_run_integrity_makes_a_short_run_invalid():
    """AUDIT-27 §2.3: a doctored completion with the wrong update count."""
    def body(tmp):
        folder = synthetic_experiment(tmp)
        full_run_set(folder)
        write_training(folder, 'F', X.SEEDS[1], updates=3)
        table = X.gate_table(folder)
        assert table['verdict'] == 'INVALID', table
        assert table['integrity']['problems'] == [f'F-{X.SEEDS[1]}: 3 updates, not 6000']
        assert 'not a full registered run' in table['reason']
    with_tmp(body)


def test_run_integrity_makes_mixed_source_versions_invalid():
    def body(tmp):
        folder = synthetic_experiment(tmp)
        full_run_set(folder)
        write_training(folder, 'control', X.SEEDS[2], fingerprint='a'*64)
        table = X.gate_table(folder)
        assert table['verdict'] == 'INVALID', table
        assert len(table['integrity']['source_fingerprints']) == 2
        assert any('different source versions' in p
                   for p in table['integrity']['problems']), table['integrity']
    with_tmp(body)


def test_run_integrity_makes_a_recorded_override_invalid():
    def body(tmp):
        folder = synthetic_experiment(tmp)
        full_run_set(folder)
        write_training(folder, 'F', X.SEEDS[0], overrides=dict(code_namespace='sneaky'))
        table = X.gate_table(folder)
        assert table['verdict'] == 'INVALID', table
        assert any('overrides' in p for p in table['integrity']['problems'])
    with_tmp(body)


def test_run_integrity_is_silent_when_no_run_folder_exists():
    """The gate arithmetic tests score synthetic tables with no runs/ folder at all."""
    def body(tmp):
        table = X.gate_table(synthetic_experiment(tmp))
        assert table['integrity']['problems'] == []
        assert table['integrity']['runs'] == {}
        assert table['verdict'] == 'PASS'
    with_tmp(body)


def test_arm_L_never_moves_the_verdict():
    def body(tmp):
        table = X.gate_table(synthetic_experiment(tmp, l_pass=0))
        assert table['verdict'] == 'PASS', table['reason']
        assert table['L_seeds_passed'] == 0
        assert 'DESCRIPTIVE' in table['rules']['arm_L']
    with_tmp(body)


def test_paired_slack_is_the_binding_mark_and_the_warning_is_two_sided():
    def body(tmp):
        folder = Path(tmp)
        for seed in X.SEEDS:
            write_synthetic(folder, 'control', seed, synthetic_scoring(flat(500)))
            write_synthetic(folder, 'F', seed, synthetic_scoring(dict(flat(500), c3=490)),
                            synthetic_scoring(dict(flat(500), c3=490+X.PAIRED_SLACK+1)),
                            summary=synthetic_summary(), buffer_ok=True)
        table = X.gate_table(folder)
        row = table['F'][str(X.SEEDS[0])]['cells']['c3']
        assert row['meets_cutoff'] and not row['meets_paired'], row
        assert table['verdict'] == 'FAIL'
        assert table['paired_warnings'][f'F-{X.SEEDS[0]}'] == ['c3']
        # better on reserved by more than the slack: passes the mark, warns anyway
        folder2 = folder/'edge'
        for seed in X.SEEDS:
            write_synthetic(folder2, 'control', seed, synthetic_scoring(flat(500)))
            write_synthetic(folder2, 'F', seed,
                            synthetic_scoring(dict(flat(500), c3=500)),
                            synthetic_scoring(dict(flat(500), c3=480)),
                            summary=synthetic_summary(), buffer_ok=True)
        table2 = X.gate_table(folder2)
        assert table2['verdict'] == 'PASS'
        assert table2['paired_warnings'][f'F-{X.SEEDS[0]}'] == ['c3'], \
            'a two-sided warning, which is not a mark (21b Q10)'
    with_tmp(body)


# ---------------------------------------------------------------- failure signatures

def test_signature_never_started():
    verdict = X.seed_verdict('F', synthetic_scoring(flat(30)),
                             reference=synthetic_scoring(flat(30)))
    sig = X.failure_signatures('F', synthetic_scoring(flat(30)),
                               reference=synthetic_scoring(flat(30)), verdict=verdict)
    assert sig['never_started'] is True
    assert X.failure_signatures('F', synthetic_scoring(flat(500)))['never_started'] is False


def test_signature_copy_side_failure():
    scoring = synthetic_scoring(flat(300), link=.06, attribute=.99)
    sig = X.failure_signatures('F', scoring)
    assert sig['copy_side_failure'] is True, sig
    healthy = X.failure_signatures('F', synthetic_scoring(flat(500), link=.97))
    assert healthy['copy_side_failure'] is False
    both = X.failure_signatures('F', synthetic_scoring(flat(30), link=.06, attribute=.05))
    assert both['copy_side_failure'] is False, 'both broken is never_started, not copy-side'


def test_signature_name_blind_and_its_sub_labels():
    reserved = synthetic_scoring(flat(100), link=.06)
    train = synthetic_scoring(flat(100), link=.06)
    verdict = X.seed_verdict('F', reserved, reference=train)
    assert all(v == 0 for v in [verdict['cells'][c]['paired_delta'] for c in X.CELL_ORDER])
    for summary, label in ((synthetic_summary(final_entity_output_bias=-4.), 'bias_exit'),
                           (synthetic_summary(final_mean_answer_length=3.), 'gain_exit'),
                           (synthetic_summary(), 'unexplained')):
        sig = X.failure_signatures('F', reserved, reference=train, verdict=verdict,
                                   summary=summary)
        assert sig['name_blind'] is True, sig
        assert sig['name_blind_sub_label'] == label, (label, sig['name_blind_sub_label'])
    # a non-zero paired difference is not name_blind, whatever the LINK accuracy
    other = synthetic_scoring(dict(flat(100), c3=101), link=.06)
    verdict2 = X.seed_verdict('F', other, reference=train)
    assert X.failure_signatures('F', other, reference=train, verdict=verdict2,
                                summary=synthetic_summary())['name_blind'] is False


def test_signature_reserved_gap():
    reserved = synthetic_scoring(dict(flat(500), c3=400))
    train = synthetic_scoring(flat(500))
    verdict = X.seed_verdict('F', reserved, reference=train)
    sig = X.failure_signatures('F', reserved, reference=train, verdict=verdict,
                               summary=synthetic_summary())
    assert sig['reserved_gap'] is True, sig
    ok = X.failure_signatures('F', synthetic_scoring(flat(500)), reference=train,
                              verdict=X.seed_verdict('F', synthetic_scoring(flat(500)),
                                                     reference=train))
    assert ok['reserved_gap'] is False


def test_signature_scale_collapsed_is_arm_L_only():
    reserved, train = synthetic_scoring(flat(100)), synthetic_scoring(flat(100))
    verdict = X.seed_verdict('L', reserved, reference=train)
    summary = synthetic_summary(min_abs_code_scale_from_500=.01, scale_collapsed=True)
    assert X.failure_signatures('L', reserved, reference=train, verdict=verdict,
                                summary=summary)['scale_collapsed'] is True
    assert X.failure_signatures('F', reserved, reference=train, verdict=verdict,
                                summary=summary)['scale_collapsed'] is False


def test_signature_unnamed():
    reserved = synthetic_scoring(dict(flat(500), c3=400), link=.9)
    train = synthetic_scoring(dict(flat(500), c3=400), link=.9)
    verdict = X.seed_verdict('F', reserved, reference=train)
    sig = X.failure_signatures('F', reserved, reference=train, verdict=verdict,
                               summary=synthetic_summary())
    assert sig['unnamed'] is True, sig
    assert not any(sig[k] for k in ('never_started', 'name_blind', 'copy_side_failure',
                                    'reserved_gap', 'scale_collapsed'))
    passing = synthetic_scoring(flat(500))
    good = X.failure_signatures('F', passing, reference=passing,
                                verdict=X.seed_verdict('F', passing, reference=passing),
                                summary=synthetic_summary())
    assert good['unnamed'] is False, 'a passing seed is never "unnamed"'


def test_gates_and_report_run_end_to_end_on_a_synthetic_table():
    def body(tmp):
        folder = synthetic_experiment(tmp, f_pass=1, link=.05)
        table = X.gate_table(folder)
        assert table['verdict'] == 'FAIL'
        assert set(table['signature_summary']) == {
            'never_started', 'name_blind', 'copy_side_failure', 'reserved_gap',
            'scale_collapsed', 'unnamed'}
        args = argparse.Namespace(exp=str(folder), out=str(folder/'report.txt'), wave=1)
        with contextlib.redirect_stdout(open('/dev/null', 'w')):
            text = X.cmd_report(args)
        for wanted in ('verdict', 'paired reserved minus training-pool',
                       'pre-named failure signatures', 'frozen code_scale'):
            assert wanted in text, wanted
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
    X.configure_once()
    torch.manual_seed(0)
    for name, function in TESTS:
        if args.only and args.only not in name:
            continue
        check(name, function)
    print(f'\nPASSED {PASSED}  FAILED {FAILED}  SKIPPED {SKIPPED}', flush=True)
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
