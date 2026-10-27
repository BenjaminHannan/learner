"""Checks for scripts/fable_dispatcher_probes26.py.  Plain script; no pytest.

Run:
    OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python3.12 -B \
        tests/test_fable_dispatcher_probes26.py

Knobs (all optional):
    FABLE_P26_TMP=<dir>     where the end-to-end panel/probe smoke writes
    FABLE_P26_SKIP_SMOKE=1  skip the end-to-end smoke (panel + probe + report on a
                            freshly built, untrained model over two tiny cells)

Nothing here loads any experiment-19/19b checkpoint, nothing trains, nothing touches
the registered panels, and nothing writes into artifacts/.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import fable_dispatcher as V1                                              # noqa: E402
import fable_dispatcher_v3 as V3                                           # noqa: E402
import fable_dispatcher_v4 as V4                                           # noqa: E402
import fable_dispatcher_probes26 as P                                      # noqa: E402

torch = V4.torch
LINK = V3.LINK

PASSED = 0
FAILED = []


def check(name, function):
    global PASSED
    started = time.monotonic()
    try:
        detail = function()
    except Exception as exc:                                    # noqa: BLE001
        FAILED.append((name, repr(exc)))
        print(f'FAIL  {name}: {exc!r}', flush=True)
        return
    PASSED += 1
    print(f'ok    {name}  [{time.monotonic() - started:.1f}s]' + (f'  {detail}' if detail else ''),
          flush=True)


# --------------------------------------------------------------------------- fixtures


def _question(hops, asker=52, terminal=10):
    return V3.question_tokens(asker, hops, terminal)


def _chain(hops, people=(52, 53, 54, 55, 56, 57, 58, 59, 60), terminal=10, answer=30):
    steps = [[people[i], LINK, people[i + 1]] for i in range(hops - 1)]
    steps.append([people[hops - 1], terminal, answer])
    return steps


def _units(cell, n, namespace=P.NAMESPACE):
    units = []
    for index in range(n):
        unit = V4.throwaway_unit(cell, index, namespace)
        problems = V3.audit_unit(unit)
        assert not problems, f'{cell}:{index}: {problems}'
        units.append(unit)
    return units


def _fresh_model(arm='ctx', seed=7):
    torch.manual_seed(seed)
    flags = V4.flags_for_arm(arm)
    model = V4.build_model(width=32, flags=flags)
    model.eval()
    return model, flags


_CONTROL_CACHE = {}


def _control_model(key='v4-ctx-s0'):
    """One of the twelve KNOWN-ANSWER v4 control checkpoints, loaded through the script's
    own verified loader.

    An untrained model's first pointer is almost always illegal, so a live-episode check
    needs a controller that actually makes calls.  These twelve are the positive control
    the specification itself tells the builder to validate against; no experiment-19/19b
    checkpoint is ever loaded here.
    """
    if key not in _CONTROL_CACHE:
        entry = P.CHECKPOINTS[key]
        if not Path(entry['path']).is_file():
            raise FileNotFoundError(entry['path'])
        model, flags, _detail = P.load_model(entry)
        _CONTROL_CACHE[key] = (model, flags)
    return _CONTROL_CACHE[key]


# --------------------------------------------------------------------------- frozen constants


def test_spec_hash_and_registry():
    """The design file is the one this script was written against, and section 2's
    twenty-four checkpoints all exist with exactly the recorded hashes."""
    actual = V1.sha(P.SPEC_PATH)
    assert actual == P.SPEC_SHA256, f'specification hashes to {actual}'
    assert len(P.CHECKPOINTS) == 24, len(P.CHECKPOINTS)
    assert len(P.CONTROL_IDS) == 12 and len(P.REGISTERED_IDS) == 9
    for key, entry in P.CHECKPOINTS.items():
        path = Path(entry['path'])
        assert path.is_file(), f'{key}: missing {path}'
        assert len(entry['sha256']) == 64
    assert P.NAMESPACE == 'fable-probe26-v1'
    assert P.NAMESPACE not in (V4.THROWAWAY_NAMESPACE, V3.PANEL_NAMESPACE, V3.TRAIN_NAMESPACE,
                               V4.TRAIN_NAMESPACE)
    assert P.EVAL_CAP == V3.EVAL_CAP == 16
    assert (P.MARK_R1, P.MARK_R2, P.MARK_R3, P.MARK_R5) == (61, 48, 59, 16)
    assert P.CELLS26 == ('k3-prac', 'k3-held', 'k4-prac', 'k4-held', 'k5-prac', 'k5-held',
                         'k6-prac', 'k6-held', 'k8-prac', 'k8-held')
    return f'{len(P.CHECKPOINTS)} checkpoints on disk'


def test_code_hashes_match_the_design():
    """Section 2's code hashes: the imported modules have not drifted."""
    found = P.code_hashes()
    for name, digest in P.DESIGN_CODE_SHA256.items():
        assert found[name] == digest, f'{name} is {found[name]}, design recorded {digest}'
    assert V1.sha(P.OPERATOR_PATH) == P.OPERATOR_SHA256
    return 'five modules and the frozen operator unchanged'


def test_namespace_units_differ_from_every_other_panel():
    """A probe-26 unit is not a v3 registered unit, a v4 throwaway unit or an exp-19 one."""
    mine = V4.throwaway_unit('k3-held', 0, P.NAMESPACE)
    theirs = V4.throwaway_unit('k3-held', 0, V4.THROWAWAY_NAMESPACE)
    assert mine['a']['memory'] != theirs['a']['memory']
    again = V4.throwaway_unit('k3-held', 0, P.NAMESPACE)
    assert again['a'] == mine['a'], 'the namespace RNG is not deterministic'
    return 'distinct and reproducible'


# --------------------------------------------------------------------------- probe A classifier


def test_classifier_every_category():
    """One hand-built episode per category of section 4, probe A."""
    question = _question(3)
    chain = _chain(3)
    width = len(question)
    cases = []

    # 1 OPERATOR: pointers right, returned token wrong
    bad = [list(s) for s in chain]
    bad[1][2] = 99
    cases.append(('OPERATOR', bad[:2], 'answered'))

    # 2 OP_EARLY_ATTR: a relation where the chain links
    early = [list(chain[0]), [chain[1][0], 10, 41]]
    cases.append(('OP_EARLY_ATTR', early, 'answered'))

    # 3 OP_RUN_ON: LINK where the chain takes the terminal relation
    run_on = [list(chain[0]), list(chain[1]), [chain[2][0], LINK, 61]]
    cases.append(('OP_RUN_ON', run_on, 'answered'))

    # 4 SUBJECT: operation right, subject wrong
    subject = [list(chain[0]), [61, LINK, 62]]
    cases.append(('SUBJECT', subject, 'answered'))

    # 5 STOP_EARLY: a correct proper prefix, answered
    cases.append(('STOP_EARLY', [list(s) for s in chain[:2]], 'answered'))

    # 6 STOP_LATE: the whole chain then more calls
    late = [list(s) for s in chain] + [[chain[-1][0], LINK, 61]]
    cases.append(('STOP_LATE', late, 'answered'))
    cases.append(('STOP_LATE', late, 'over_cap'))

    out = {}
    for expected, transcript, status in cases:
        pointers = [[1, 2 + i, 0] for i in range(len(transcript))]
        got = P.classify_first_fault(transcript, chain, status, pointers, question)
        assert got['category'] == expected, f'{expected}: got {got}'
        out[expected] = got['index']

    # 7 INVALID after a correct prefix, sub-typed by the illegal pointer
    pointers = [[1, 2, 0], [width + 0, width - 1, -1]]          # operation points at ANSWER
    got = P.classify_first_fault([list(chain[0])], chain, 'invalid_action', pointers, question)
    assert got['category'] == 'INVALID', got
    assert 'INVALID_OPERATION' in got['detail'], got['detail']
    pointers = [[1, 2, 0], [0, 2, -1]]                          # subject points at QUESTION
    got = P.classify_first_fault([list(chain[0])], chain, 'invalid_action', pointers, question)
    assert 'INVALID_SUBJECT' in got['detail'], got['detail']
    pointers = [[1, 2, 0], [0, width - 1, -1]]
    got = P.classify_first_fault([list(chain[0])], chain, 'invalid_action', pointers, question)
    assert 'INVALID_BOTH' in got['detail'], got['detail']

    # 8 OTHER: an operation mismatch that is neither early-attribute nor run-on -- the
    # terminal step answered with the WRONG relation (8 where the chain takes 10)
    other = [list(chain[0]), list(chain[1]), [chain[2][0], 8, 41]]
    got = P.classify_first_fault(other, chain, 'answered', [[1, 2, 0]] * 3, question)
    assert got['category'] == 'OTHER', got

    # NONE
    got = P.classify_first_fault([list(s) for s in chain], chain, 'answered',
                                 [[1, 2, 0], [width, 3, 0], [width + 1, 4, 1]], question)
    assert got['category'] == 'NONE' and got['index'] is None
    return f'8 categories + NONE; first-fault indices {out}'


def test_classifier_precedence():
    """The order of section 4 decides when two categories could both apply."""
    question = _question(4)
    chain = _chain(4)
    # subject wrong AND the operation is an early attribute -> OP_EARLY_ATTR (2 before 4)
    transcript = [list(chain[0]), [61, 10, 41]]
    got = P.classify_first_fault(transcript, chain, 'answered', [[1, 2, 0], [1, 5, 1]], question)
    assert got['category'] == 'OP_EARLY_ATTR', got
    # a first fault inside the transcript beats an INVALID status later (1-4 before 7)
    transcript = [[61, LINK, 62]]
    got = P.classify_first_fault(transcript, chain, 'invalid_action', [[1, 2, 0], [9, 2, -1]],
                                 question)
    assert got['category'] == 'SUBJECT', got
    # a correct prefix that then stops short beats nothing else
    got = P.classify_first_fault([list(s) for s in chain[:1]], chain, 'answered', [[1, 2, 1]],
                                 question)
    assert got['category'] == 'STOP_EARLY', got
    # the full chain plus an illegal action is INVALID, not STOP_LATE (6 needs answered/over_cap)
    got = P.classify_first_fault([list(s) for s in chain], chain, 'invalid_action',
                                 [[1, 2, 0]] * 4 + [[0, 0, -1]], question)
    assert got['category'] == 'INVALID', got
    return 'four precedence cases'


def test_classifier_is_pure():
    """The classifier does not mutate its arguments and takes no model input."""
    question = _question(3)
    chain = _chain(3)
    transcript = [list(s) for s in chain[:2]]
    before = json.dumps([transcript, chain])
    P.classify_first_fault(transcript, chain, 'answered', [[1, 2, 0], [3, 3, 1]], question)
    assert json.dumps([transcript, chain]) == before
    return None


# --------------------------------------------------------------------------- probe C policy


def test_probe_c_policy_matches_force_operation_subject_at_steps_0_and_1():
    """Task-list item 6: under S0 the offset policy reproduces `force_operation+subject`
    for the first two steps exactly, and forces nothing at step 2 or later."""
    hops = torch.tensor([8] * 5, dtype=torch.long)
    width = 11
    theirs = V3.intervention_policy('force_operation+subject', hops, width)
    layout = dict(width=width, links=tuple(range(2, 9)), rel=9)
    conditions = P.offset_conditions(layout)
    mine = P.offset_start_policy(*conditions['S0']['forced'], width)
    tokens = torch.zeros(5, width, dtype=torch.long)
    for step in (0, 1):
        results = torch.zeros(5, P.EVAL_CAP, dtype=torch.long)
        n_results = torch.full((5,), step, dtype=torch.long)
        a = theirs(step, tokens, results, n_results)
        b = mine(step, tokens, results, n_results)
        assert set(b) == {'subject', 'operation'}, b.keys()
        for name in ('subject', 'operation'):
            assert torch.equal(a[name][0], b[name][0]), (step, name, a[name][0], b[name][0])
            assert torch.equal(a[name][1], b[name][1]), (step, name)
    for step in (2, 3, 7):
        b = mine(step, tokens, torch.zeros(5, P.EVAL_CAP, dtype=torch.long),
                 torch.full((5,), step, dtype=torch.long))
        assert 'stop' not in b
        assert not bool(b['subject'][1].any()) and not bool(b['operation'][1].any())
    assert conditions['S3']['forced'] == (5, 6) and conditions['S3']['next'] == 7
    assert conditions['S5']['forced'] == (7, 8) and conditions['S5']['next'] == 9
    return 'S0 == force_operation+subject at steps 0-1; nothing forced from step 2'


def test_probe_c_forced_calls_are_legal_link_lookups():
    """Every forced position of every condition carries a LINK token in a k8 question."""
    question = _question(8)
    layout = P.question_layout(question)
    assert layout['links'] == tuple(range(2, 9)) and layout['rel'] == 9
    for name, condition in P.offset_conditions(layout).items():
        for position in condition['forced']:
            assert question[position] == LINK, (name, position, question[position])
    return 'S0/S3/S5 force LINK positions only'


# --------------------------------------------------------------------------- native logits


def test_recorded_logits_are_the_models_own():
    """Auditor's checklist: the logits in `record` are taken BEFORE the forced overwrite.

    Run one cell free, read the model's own greedy pointers, then force exactly those
    pointers.  The recorded logits must be identical to the free run's, step for step.
    """
    model, flags = _control_model('v4-ctx-s0')
    units = _units('k4-held', 8)
    operator = V4.OracleOperator()
    prepared = V3.prepare_side(operator, units, 'a', 32)
    _inputs, questions, table = prepared[0]
    tokens, present = V1.pad_questions(questions)
    free_record = []
    free = V4.rollout_v4(model, tokens, present, table, torch.arange(len(units)), P.EVAL_CAP,
                         mode='greedy', flags=flags, record=free_record, gates=[])
    choices = [[list(p) for p in row] for row in free.pointers]

    def policy(step, _tokens, _results, _n_results):
        subject, operation, mask = [], [], []
        for row in choices:
            if step < len(row) and row[step][2] >= 0:
                subject.append(row[step][0])
                operation.append(row[step][1])
                mask.append(True)
            else:
                subject.append(0)
                operation.append(0)
                mask.append(False)
        return dict(subject=(torch.tensor(subject), torch.tensor(mask)),
                    operation=(torch.tensor(operation), torch.tensor(mask)))

    forced_record = []
    forced = V4.rollout_v4(model, tokens, present, table, torch.arange(len(units)), P.EVAL_CAP,
                           mode='greedy', policy=policy, flags=flags, record=forced_record,
                           gates=[])
    assert forced.transcripts == free.transcripts
    assert len(forced_record) == len(free_record)
    for a, b in zip(free_record, forced_record):
        for key in ('subject', 'operation', 'stop', 'state'):
            assert torch.equal(a[key], b[key]), f'step {a["step"]} differs in {key}'
    return f'{len(free_record)} recorded steps identical'


def test_native_steps_aggregates_the_right_things():
    """`native_steps` reads the layout, the used LINKs and the STOP probability."""
    model, flags = _control_model('v4-reg-ctx-s0')
    units = _units('k8-held', 8)
    operator = V4.OracleOperator()
    prepared = V3.prepare_side(operator, units, 'a', 32)
    factory = (lambda hop, width: V3.intervention_policy('force_operation+subject', hop, width))
    steps, rows = P.native_steps(model, flags, units, 'k8-held', prepared, P.EVAL_CAP, factory,
                                 max_step=P.EVAL_CAP - 1)
    assert '0' in steps and steps['0']['n_active'] == len(units)
    for key, bucket in steps.items():
        total = sum(bucket['op_category'].values())
        assert total == bucket['n_active'], (key, bucket)
        assert 0 <= bucket['subject_gold'] <= bucket['n_active']
        assert bucket['p_stop_median'] is None or 0. <= bucket['p_stop_median'] <= 1.
        assert bucket['gate_median'] is not None, 'the register arm must log a write gate'
    assert len(rows) == len(units)
    assert all(set(row) >= {'transcript', 'truth_chain', 'status', 'strict_path'} for row in rows)
    return f'{len(steps)} steps logged'


def test_native_steps_agrees_with_score_side_v4():
    """The direct rollout used for the logits is the same episode `score_side_v4` scores."""
    model, flags = _control_model('v4-ctx-s0')
    units = _units('k5-prac', 8)
    operator = V4.OracleOperator()
    prepared = V3.prepare_side(operator, units, 'a', 32)
    factory = (lambda hop, width: V3.intervention_policy('force_operation+subject', hop, width))
    scored = V4.score_side_v4(model, operator, units, 'a', P.EVAL_CAP, flags, factory, block=32,
                              prepared=prepared)
    _steps, rows = P.native_steps(model, flags, units, 'k5-prac', prepared, P.EVAL_CAP, factory,
                                  max_step=P.EVAL_CAP - 1)
    for a, b in zip(scored, rows):
        assert a['transcript'] == b['transcript'] and a['status'] == b['status']
        assert a['strict_path'] == b['strict_path'] and a['calls'] == b['calls']
    return f'{len(rows)} episodes identical'


# --------------------------------------------------------------------------- geometry


def test_geometry_skips_arms_without_learned_positions():
    panel = {cell: _units(cell, 4) for cell in ('k3-prac', 'k3-held', 'k8-prac', 'k8-held')}
    plain, _ = _fresh_model('reg')
    assert P.geometry(plain, panel) is None
    model, _ = _fresh_model('ctx')
    out = P.geometry(model, panel)
    assert out['sep_trained'] > 0 and out['sep_long'] > 0
    assert abs(out['ratio'] - out['sep_long'] / out['sep_trained']) < 1e-9
    return f'ratio {out["ratio"]:.3f} on a fresh model'


# --------------------------------------------------------------------------- thresholds


def _synthetic_document(**overrides):
    """A minimal probe document with dialable counts, for the threshold arithmetic."""
    cells = {}
    for cell in P.CELLS26:
        hops = int(cell.split('-')[0][1:])
        cells[cell] = dict(
            hops=hops, n=64, width=hops + 3,
            probe_a=dict(trained_operator=dict(
                answers=0, strict=0,
                categories={k: 0 for k in P.CATEGORIES})),
            probe_b={kind: dict(strict=0, answers=0,
                                categories={k: 0 for k in P.CATEGORIES})
                     for kind in V3.INTERVENTIONS})
    document = dict(checkpoint='synthetic', family='19-awake', group='registered', arm='reg+ctx',
                    seed=1900, learned_positions=True, cells=cells, probe_d=dict(ratio=0.5))
    for path, value in overrides.items():
        target = document
        keys = path.split('.')
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
    return document


def test_thresholds_are_exactly_section_five():
    """R1, R2, R3, R4, R5, R6, R6', R7 on the boundary values."""
    doc = _synthetic_document()
    for cell in ('k4-prac', 'k4-held'):
        doc['cells'][cell]['probe_b']['force_operation+subject']['strict'] = 61
    flags = P.r_flags(doc)
    assert flags['R1(4)'] is True
    doc['cells']['k4-held']['probe_b']['force_operation+subject']['strict'] = 60
    assert P.r_flags(doc)['R1(4)'] is False

    doc = _synthetic_document()
    doc['cells']['k8-held']['probe_a']['trained_operator']['categories']['OP_EARLY_ATTR'] = 48
    assert P.r_flags(doc)['R2'] is True
    doc['cells']['k8-held']['probe_a']['trained_operator']['categories']['OP_EARLY_ATTR'] = 47
    assert P.r_flags(doc)['R2'] is False

    doc = _synthetic_document()
    for cell in ('k8-prac', 'k8-held'):
        doc['cells'][cell]['probe_b']['force_operation']['strict'] = 59
    assert P.r_flags(doc)['R3'] is True
    doc['cells']['k8-prac']['probe_b']['force_operation']['strict'] = 58
    assert P.r_flags(doc)['R3'] is False

    # R4(6): operation-only does NOT reach the cell mark while R1(6) holds
    doc = _synthetic_document()
    for cell in ('k6-prac', 'k6-held'):
        doc['cells'][cell]['probe_b']['force_operation+subject']['strict'] = 62
        doc['cells'][cell]['probe_b']['force_operation']['strict'] = 40
    flags = P.r_flags(doc)
    assert flags['R4(6)'] is True and flags['R1(6)'] is True
    for cell in ('k6-prac', 'k6-held'):
        doc['cells'][cell]['probe_b']['force_operation']['strict'] = 59
    assert P.r_flags(doc)['R4(6)'] is False

    doc = _synthetic_document()
    doc['cells']['k5-held']['probe_b']['force_operation+subject']['categories']['STOP_EARLY'] = 16
    assert P.r_flags(doc)['R5'] is True
    doc['cells']['k5-held']['probe_b']['force_operation+subject']['categories']['STOP_EARLY'] = 15
    assert P.r_flags(doc)['R5'] is False

    doc = _synthetic_document()
    doc['cells']['k8-held']['probe_c'] = dict(
        S0=dict(step2=dict(adjacent_unused_link_abs_median=0.005, offset_category={})),
        S3=dict(step2=dict(offset_category=dict(REL=48, NEXT=16))))
    doc['probe_d'] = dict(ratio=0.10)
    flags = P.r_flags(doc)
    assert flags['R6'] is True and flags["R6'"] is False and flags['R7'] is True
    doc['cells']['k8-held']['probe_c']['S3']['step2']['offset_category'] = dict(REL=16, NEXT=30,
                                                                                OTHER_LINK=18)
    doc['probe_d'] = dict(ratio=0.11)
    flags = P.r_flags(doc)
    assert flags['R6'] is False and flags["R6'"] is True and flags['R7'] is False
    return 'every threshold checked on both sides of its boundary'


def test_positive_control_and_decision_table():
    """D0 short-circuits; D1/D2a/D2b/D3/D4/D4'/D5 fire from the flags alone."""
    documents, flags = {}, {}

    def add(key, family, group, arm, learned, marks):
        documents[key] = dict(checkpoint=key, family=family, group=group, arm=arm,
                              learned_positions=learned, seed=0)
        flags[key] = dict(marks)

    for i, key in enumerate(P.CONTROL_IDS):
        entry = P.CHECKPOINTS[key]
        learned = entry['arm'] in P.LEARNED_POSITION_ARMS
        marks = {'R1(4)': True, 'R2': learned, 'R3': entry['family'] == 'v4-ctx',
                 '_subject_only_k8_held_strict': 64 if entry['family'] == 'v4-reg' else 0,
                 'R6': entry['family'] == 'v4-ctx', "R6'": False}
        add(key, entry['family'], 'control', entry['arm'], learned, marks)
    control = P.positive_control(documents, flags)
    assert control['passed'], control
    # audit B2: a passing control with NO registered checkpoint yields one explicit
    # "not evaluable" row and no D-row at all
    partial = P.decision_rows(documents, flags, control)
    assert len(partial) == 1 and partial[0].get('incomplete') and not partial[0]['fired']
    assert set(partial[0]['missing']) == set(P.REGISTERED_IDS)
    assert not any(r['row'].startswith('D') for r in partial)

    # a broken control short-circuits to D0
    flags[P.CONTROL_IDS[0]]['R1(4)'] = False
    broken = P.positive_control(documents, flags)
    assert not broken['passed']
    only = P.decision_rows(documents, flags, broken)
    assert len(only) == 1 and only[0]['row'] == 'D0' and only[0]['fired']

    # D1 with the registered families all holding R1(4), R1(5) and (for awake) R2
    flags[P.CONTROL_IDS[0]]['R1(4)'] = True
    for key in P.REGISTERED_IDS:
        entry = P.CHECKPOINTS[key]
        add(key, entry['family'], 'registered', entry['arm'], True,
            {'R1(4)': True, 'R1(5)': True, 'R2': True, 'R5': False, 'R4(6)': False})
    rows = {r['row']: r for r in P.decision_rows(documents, flags, control)}
    assert rows['D1']['fired'] and not rows['D2a']['fired'] and not rows['D5']['fired']
    assert rows['D4']['fired'] and not rows["D4'"]['fired']

    # D2a: premature STOP in two of the three awake seeds
    for key in [k for k in P.REGISTERED_IDS if k.startswith('19-awake')][:2]:
        flags[key]['R5'] = True
    rows = {r['row']: r for r in P.decision_rows(documents, flags, control)}
    assert rows['D2a']['fired']
    for key in [k for k in P.REGISTERED_IDS if k.startswith('19-awake')][:2]:
        flags[key]['R5'] = False

    # D2b: U8 only
    for key in [k for k in P.REGISTERED_IDS if k.startswith('19b-U8')][:2]:
        flags[key]['R5'] = True
    rows = {r['row']: r for r in P.decision_rows(documents, flags, control)}
    assert rows['D2b']['fired'] and not rows['D2a']['fired']
    for key in [k for k in P.REGISTERED_IDS if k.startswith('19b-U8')][:2]:
        flags[key]['R5'] = False

    # D3: R4(6) in two U5 seeds
    for key in [k for k in P.REGISTERED_IDS if k.startswith('19b-U5')][:2]:
        flags[key]['R4(6)'] = True
    rows = {r['row']: r for r in P.decision_rows(documents, flags, control)}
    assert rows['D3']['fired']
    return 'D0 short-circuit plus D1, D2a, D2b, D3, D4'


def test_family_rule_is_two_of_three_and_never_averages():
    documents = {f'19-awake-s{s}': dict(family='19-awake') for s in (1900, 1901, 1902)}
    flags = {k: {'R5': False} for k in documents}
    assert not P.family_holds(documents, flags, '19-awake', 'R5')['verdict']
    flags['19-awake-s1900']['R5'] = True
    assert not P.family_holds(documents, flags, '19-awake', 'R5')['verdict']
    flags['19-awake-s1901']['R5'] = True
    out = P.family_holds(documents, flags, '19-awake', 'R5')
    assert out['verdict'] and out['holds'] == 2 and out['seeds'] == 3
    return None


# --------------------------------------------------------------------------- end to end


def test_end_to_end_smoke():
    """panel -> probe -> report on a freshly built (untrained) model over two cells.

    The loader is monkey-patched so the run cannot reach an experiment-19/19b checkpoint;
    the model it hands back is one of the twelve v4 control checkpoints, which exercises
    every code path including probes C and D and the refuse-to-overwrite / resume
    behaviour.  Everything is written to a temporary directory, never to artifacts/.
    """
    if os.environ.get('FABLE_P26_SKIP_SMOKE'):
        return 'skipped'
    out = Path(TMP) / 'smoke'
    shutil.rmtree(out, ignore_errors=True)
    cells = ('k3-prac', 'k3-held', 'k8-prac', 'k8-held')
    manifest = P.build_panel(out, force_cells=cells, n=4, dev=True)
    assert (out / 'panel.json').exists() and manifest['panel_units'] == 16
    assert manifest['dev_panel'] is True and manifest['probe_source_sha256'] == P.source_sha256()
    assert manifest['forecasts']['predictions_sha256'] and manifest['forecasts']['ledger_sha256']
    try:
        P.build_panel(out, force_cells=cells, n=4, dev=True)
        raise AssertionError('a second panel build must be refused')
    except SystemExit:
        pass
    try:                                                     # audit M1
        P.load_panel(out)
        raise AssertionError('a --dev panel must not be readable as a registered run')
    except SystemExit:
        pass
    loaded_manifest, panel = P.load_panel(out, dev=True)
    assert set(panel) == set(cells)

    original = P.load_model
    model, flags = _control_model('v4-ctx-s0')

    def fake_load(entry):
        return model, flags, dict(path=str(entry['path']), sha256=entry['sha256'],
                                  loader='test-double', arm=entry['arm'], seed=entry['seed'],
                                  parameters=model.parameters_count(), flags=flags.as_dict(),
                                  weight_fingerprint=V1.fingerprint(model))
    P.load_model = fake_load
    try:
        entry = P.CHECKPOINTS['v4-ctx-s0']
        path = out / 'probes' / f'probe-{entry["id"]}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        document = P.probe_checkpoint(entry, loaded_manifest, panel, path)
        assert path.exists()
        for cell in cells:
            row = document['cells'][cell]
            assert set(row['probe_b']) == set(V3.INTERVENTIONS)
            assert sum(row['probe_a']['trained_operator']['categories'].values()) == 4
            if cell.startswith('k8'):
                assert set(row['probe_c']) == {'S0', 'S3', 'S5'}
                assert row['probe_c']['S3']['forced_positions'] == [5, 6]
        assert document['probe_d']['ratio'] is not None
        # resume: a second probe call is a no-op and never rewrites the file
        before = V1.sha(path)
        assert P.probe(argparse_namespace(out=str(out), ckpt='v4-ctx-s0', family=None,
                                          dev=True)) is None
        assert V1.sha(path) == before
        # refuse to overwrite directly
        try:
            P.probe_checkpoint(entry, loaded_manifest, panel, path)
            raise AssertionError('an existing probe output must not be overwritten')
        except FileExistsError:
            pass
        text = P.report(argparse_namespace(out=str(out), suffix='smoke', dev=True))
        assert not text['control']['passed'], 'one checkpoint cannot pass the positive control'
        assert text['decisions'][0]['row'] == 'D0'
        assert (out / 'report-smoke.txt').exists()
        body = (out / 'report-smoke.txt').read_text()
        assert 'registered set     0 of 9' in body
        assert 'positive control   1 of 12' in body
        assert 'R4(d) is read as' in body
        assert 'oracle/trained first-fault agreement' in body
        assert 'bit-identical to 19b-U5' in body
    finally:
        P.load_model = original
    return 'panel, probe, resume, report'


class argparse_namespace:                                    # noqa: N801  (a tiny stand-in)
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _refuses(call, why):
    try:
        call()
    except SystemExit:
        return
    raise AssertionError(why)


def test_probe_source_sha256_is_pinned():
    """Audit B1: nothing may mix outputs written by two versions of this script.

    The manifest and every probe output record the source hash; `load_panel`, `probe`
    and `report` all refuse a mismatch outright -- they never skip the odd file out.
    """
    out = Path(TMP) / 'sha-pin'
    shutil.rmtree(out, ignore_errors=True)
    manifest = P.build_panel(out, force_cells=('k3-prac',), n=2, dev=True)
    assert manifest['probe_source_sha256'] == P.source_sha256()
    P.load_panel(out, dev=True)                                   # the honest case

    manifest_path = out / 'manifest.json'
    good = json.loads(manifest_path.read_text())
    manifest_path.write_text(json.dumps(dict(good, probe_source_sha256='0' * 64)))
    _refuses(lambda: P.load_panel(out, dev=True),
             'a manifest written by another version of the script must be refused')
    _refuses(lambda: P.report(argparse_namespace(out=str(out), suffix='x', dev=True)),
             'report must refuse a manifest from another version')
    manifest_path.write_text(json.dumps(good))

    probes = out / 'probes'
    probes.mkdir(parents=True, exist_ok=True)
    stranger = probes / 'probe-v4-ctx-s0.json'
    stranger.write_text(json.dumps(dict(checkpoint='v4-ctx-s0',
                                        panel_sha256=good['panel_sha256'],
                                        probe_source_sha256='1' * 64)))
    _refuses(lambda: P.report(argparse_namespace(out=str(out), suffix='mixed', dev=True)),
             'report must refuse a probe output from another version')
    _refuses(lambda: P.probe(argparse_namespace(out=str(out), ckpt='v4-ctx-s1', family=None,
                                                dev=True)),
             'probe must refuse to ADD to a folder holding another version\'s work')
    assert not (out / 'report-mixed.txt').exists() and not (out / 'report-x.txt').exists()
    assert not (probes / 'probe-v4-ctx-s1.json').exists(), 'nothing may be written after a refusal'

    stranger.write_text(json.dumps(dict(checkpoint='v4-ctx-s0',
                                        panel_sha256=good['panel_sha256'],
                                        probe_source_sha256=P.source_sha256())))
    assert set(P.read_documents(probes, good)) == {'v4-ctx-s0'}
    return 'manifest, probe and report all refuse a foreign source hash'


def test_report_gating_final_and_control_only():
    """Audit B2: `--suffix final` refuses an incomplete run; `--suffix control` prints
    no row of the section-6 table."""
    out = Path(TMP) / 'gating'
    shutil.rmtree(out, ignore_errors=True)
    cells = ('k3-prac', 'k3-held', 'k8-prac', 'k8-held')     # probe D pools k3 and k8
    P.build_panel(out, force_cells=cells, n=2, dev=True)
    manifest, panel = P.load_panel(out, dev=True)
    original = P.load_model
    model, flags = _control_model('v4-ctx-s0')

    def fake_load(entry):
        return model, flags, dict(path=str(entry['path']), sha256=entry['sha256'],
                                  loader='test-double', arm=entry['arm'], seed=entry['seed'],
                                  parameters=model.parameters_count(), flags=flags.as_dict(),
                                  weight_fingerprint=V1.fingerprint(model))
    P.load_model = fake_load
    try:
        entry = P.CHECKPOINTS['v4-ctx-s0']
        path = out / 'probes' / f'probe-{entry["id"]}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        P.probe_checkpoint(entry, manifest, panel, path)
        # final: one of twenty-one checkpoints is not a registered run
        _refuses(lambda: P.report(argparse_namespace(out=str(out), suffix='final', dev=True)),
                 'a FINAL report must be refused while the registered set is incomplete')
        assert not (out / 'report-final.txt').exists()
        # control-only: the control section, and no D-row anywhere
        result = P.report(argparse_namespace(out=str(out), suffix='control', dev=True))
        assert result['control_only'] and result['decisions'] == []
        text = (out / 'report-control.txt').read_text()
        assert 'CONTROL ONLY' in text and 'not evaluated' in text
        assert '1. POSITIVE CONTROL' in text
        for row in ('D0', 'D1', 'D2a', 'D2b', 'D3', 'D4', 'D5'):
            assert f'\n{row} ' not in text and f'\n{row:<4} ' not in text, row
        saved = json.loads((out / 'report-control.json').read_text())
        assert saved['kind'] == 'control' and saved['decision_table_evaluated'] is False
        assert saved['registered_missing'] == list(P.REGISTERED_IDS)
        assert saved['forecasts']['predictions_sha256']
    finally:
        P.load_model = original
    return 'final refused, control-only prints no decision row'


def test_panel_size_and_cells_are_pinned():
    """Audit M1: every section-5 threshold is an absolute count out of 64, so a panel of
    any other size -- or of any other cells -- is refused unless it is marked --dev."""
    out = Path(TMP) / 'size'
    shutil.rmtree(out, ignore_errors=True)
    _refuses(lambda: P.build_panel(out / 'small', n=8),
             'a panel of 8 units per cell must be refused without --dev')
    _refuses(lambda: P.build_panel(out / 'cells', force_cells=('k3-prac', 'k8-held')),
             'a panel with a different cell list must be refused without --dev')
    assert not (out / 'small' / 'panel.json').exists()

    good = P.build_panel(out / 'dev', force_cells=('k3-prac',), n=2, dev=True)
    assert good['dev_panel'] is True and good['n_per_cell'] == 2
    _refuses(lambda: P.load_panel(out / 'dev'), 'a dev panel is not a registered run')
    P.load_panel(out / 'dev', dev=True)

    # a hand-edited manifest that hides the dev mark is still caught by n_per_cell / cells
    path = out / 'dev' / 'manifest.json'
    data = json.loads(path.read_text())
    path.write_text(json.dumps(dict(data, dev_panel=False)))
    _refuses(lambda: P.load_panel(out / 'dev'), 'n_per_cell 2 is not section 3\'s 64')
    path.write_text(json.dumps(dict(data, dev_panel=False, n_per_cell=P.PANEL_N)))
    _refuses(lambda: P.load_panel(out / 'dev'), 'one cell is not section 3\'s ten')
    assert P.PANEL_N == 64
    return 'n != 64 and cells != CELLS26 both refused'


def test_forecast_hashes():
    """Audit M2: the manifest pins the text of the frozen forecasts P102-P117."""
    found = P.forecast_hashes()
    assert Path(P.PREDICTIONS_PATH).is_file() and Path(P.LEDGER_PATH).is_file()
    assert found['predictions_sha256'] == V1.sha(P.PREDICTIONS_PATH)
    assert found['ledger_sha256'] == V1.sha(P.LEDGER_PATH)
    assert found['predictions_matches_its_record'] is True, \
        'FABLE-PREDICTIONS.md no longer hashes to its own recorded .sha256.txt'
    assert found['predictions_recorded_sha256'] == found['predictions_sha256']
    return f'forecasts {found["predictions_sha256"][:8]}, ledger {found["ledger_sha256"][:8]}'


# --------------------------------------------------------------------------- guards


def test_nothing_writes_into_artifacts_or_loads_test_pt():
    """Static guards: no `test.pt`, no writes outside --out, no training entry point."""
    source = (HERE.parent / 'scripts' / 'fable_dispatcher_probes26.py').read_text()
    assert 'test.pt' not in source
    for forbidden in ('optimizer.step', 'loss.backward', 'torch.save', '.train()'):
        assert forbidden not in source, forbidden
    assert 'write_new' in source, 'outputs must go through the refuse-to-overwrite writer'
    assert source.count("open('x')") + source.count(".open('x')") >= 1
    return None


CHECKS = [
    ('specification hash and the 24-checkpoint registry', test_spec_hash_and_registry),
    ('section-2 code hashes unchanged', test_code_hashes_match_the_design),
    ('the probe namespace is new and deterministic',
     test_namespace_units_differ_from_every_other_panel),
    ('probe A classifier: every category', test_classifier_every_category),
    ('probe A classifier: order of precedence', test_classifier_precedence),
    ('probe A classifier is pure', test_classifier_is_pure),
    ('probe C policy == force_operation+subject at steps 0-1',
     test_probe_c_policy_matches_force_operation_subject_at_steps_0_and_1),
    ('probe C forces legal LINK look-ups only', test_probe_c_forced_calls_are_legal_link_lookups),
    ('recorded logits are the model\'s own', test_recorded_logits_are_the_models_own),
    ('native step aggregates', test_native_steps_aggregates_the_right_things),
    ('native rollout == score_side_v4 episode', test_native_steps_agrees_with_score_side_v4),
    ('geometry skips arms without learned positions',
     test_geometry_skips_arms_without_learned_positions),
    ('thresholds are exactly section 5', test_thresholds_are_exactly_section_five),
    ('positive control and decision table', test_positive_control_and_decision_table),
    ('family rule is 2 of 3', test_family_rule_is_two_of_three_and_never_averages),
    ('end-to-end panel/probe/resume/report smoke', test_end_to_end_smoke),
    ('the probe source sha256 is pinned (B1)', test_probe_source_sha256_is_pinned),
    ('report gating: final and control-only (B2)', test_report_gating_final_and_control_only),
    ('panel size and cell list are pinned (M1)', test_panel_size_and_cells_are_pinned),
    ('the frozen forecasts are hashed into the manifest (M2)', test_forecast_hashes),
    ('static guards', test_nothing_writes_into_artifacts_or_loads_test_pt),
]

TMP = None


def main():
    global TMP
    V1.configure()
    random.seed(0)
    torch.manual_seed(0)
    TMP = os.environ.get('FABLE_P26_TMP') or tempfile.mkdtemp(prefix='fable-probes26-tests-')
    Path(TMP).mkdir(parents=True, exist_ok=True)
    try:
        for name, function in CHECKS:
            check(name, function)
    finally:
        if not os.environ.get('FABLE_P26_TMP'):
            shutil.rmtree(TMP, ignore_errors=True)
    if FAILED:
        print(json.dumps(dict(failed=[name for name, _ in FAILED])), flush=True)
        raise SystemExit(f'{len(FAILED)} CHECKS FAILED')
    print(f'ALL {PASSED} CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
