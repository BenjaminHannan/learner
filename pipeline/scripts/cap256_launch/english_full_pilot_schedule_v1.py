"""G6: matched full-pilot schedule, 2304 updates per arm-seed (1536 QA + 768 auxiliary).

Stdlib only. Software RNG only (never the model RNG): one sha256-seeded
random.Random stream per (seed, pass) for the passage shuffle and one for the
within-passage question order, as in english_small_paired_schedule_v1.py.

Per pass: shuffle the 24 passages; for each passage run its two QA frames in a
seed-fixed shuffled order, then the auxiliary frame. 32 passes x 72 = 2304.
Each record carries both arms' frame indices, so the order is identical across
arms within a seed by construction; only the auxiliary frame index differs
(4p+2 control reconstruction, 4p+3 treatment paraphrase).

CLI writes ENGLISH-PILOT-v1/FULL-PILOT-SCHEDULE-v1.json (exclusive create) and
prints its sha256.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import sys

SCHEMA = 'premonition.English-pilot-full-schedule.v1'
SEEDS = (0, 1)
ARMS = ('control', 'treatment')
PASSAGES = 24
PASSES = 32
PER_PASS = 72
UPDATES = PASSES * PER_PASS  # 2304
QA_UPDATES, AUX_UPDATES = 1536, 768
BANK_SHA256 = 'f2f5cce3dd2775af16ab13db8fa36b08a70b305bd1229df9e9471c4fdf7fb9ac'
DEFAULT_OUT = ('artifacts/cap256-launch/contextual-input-compare-v1/ENGLISH-PILOT-v1/'
               'FULL-PILOT-SCHEDULE-v1.json')


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def stream(label, seed, pass_index):
    key = 'English-full-pilot-%s-v1-seed%d-pass%d' % (label, seed, pass_index)
    return random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest(), 'big'))


def pilot_schedule(seed):
    if type(seed) is not int or seed not in SEEDS:
        raise ValueError('only the two fixed parent seeds admitted')
    records = []
    for pass_index in range(PASSES):
        passage_rng = stream('passage-order', seed, pass_index)
        question_rng = stream('question-order', seed, pass_index)
        order = list(range(PASSAGES))
        passage_rng.shuffle(order)
        for passage in order:
            questions = [0, 1]
            question_rng.shuffle(questions)
            steps = [('QA', q) for q in questions] + [('auxiliary', None)]
            for role, q in steps:
                update = len(records) + 1
                records.append({
                    'update': update, 'pass': pass_index, 'slot_in_pass': (update - 1) % PER_PASS,
                    'passage_index': passage, 'task_role': role, 'question_index': q,
                    'control_frame_index': 4 * passage + (q if role == 'QA' else 2),
                    'treatment_frame_index': 4 * passage + (q if role == 'QA' else 3)})
    validate_seed_schedule(records)
    return records


def arm_frames(records, arm):
    if arm not in ARMS:
        raise ValueError('control/treatment arm required')
    return [r[arm + '_frame_index'] for r in records]


def validate_seed_schedule(records):
    if type(records) is not list or len(records) != UPDATES:
        raise ValueError('exact 2304-update schedule required')
    roles = Counter(r['task_role'] for r in records)
    if roles != Counter({'QA': QA_UPDATES, 'auxiliary': AUX_UPDATES}):
        raise ValueError('exact 1536 QA + 768 auxiliary updates required')
    for i, r in enumerate(records):
        if r['update'] != i + 1 or r['pass'] != i // PER_PASS or r['slot_in_pass'] != i % PER_PASS:
            raise ValueError('update/pass numbering differs')
        p = r['passage_index']
        if r['task_role'] == 'QA':
            if r['question_index'] not in (0, 1) or r['control_frame_index'] != r['treatment_frame_index'] \
                    or r['control_frame_index'] != 4 * p + r['question_index']:
                raise ValueError('QA frames must be shared by both arms')
        elif (r['question_index'] is not None or r['control_frame_index'] != 4 * p + 2
                or r['treatment_frame_index'] != 4 * p + 3):
            raise ValueError('auxiliary frames must differ only by arm target')
    for arm in ARMS:
        counts = Counter(arm_frames(records, arm))
        expected_aux = 2 if arm == 'control' else 3
        expected = {4 * p + s: PASSES for p in range(PASSAGES) for s in (0, 1, expected_aux)}
        if counts != Counter(expected):
            raise ValueError('every arm frame must appear exactly 32 times')
    for pass_index in range(PASSES):
        block = records[pass_index * PER_PASS:(pass_index + 1) * PER_PASS]
        if Counter(r['passage_index'] for r in block) != Counter({p: 3 for p in range(PASSAGES)}):
            raise ValueError('each pass visits every passage exactly three times')
        for j in range(0, PER_PASS, 3):
            trio = block[j:j + 3]
            if (len({r['passage_index'] for r in trio}) != 1
                    or [r['task_role'] for r in trio] != ['QA', 'QA', 'auxiliary']
                    or sorted(r['question_index'] for r in trio[:2]) != [0, 1]):
                raise ValueError('per passage: two QA in shuffled order, then the auxiliary frame')
    return True


def schedule_document():
    schedules = {str(seed): pilot_schedule(seed) for seed in SEEDS}
    return {'schema': SCHEMA, 'bank_sha256': BANK_SHA256, 'seeds': list(SEEDS), 'arms': list(ARMS),
            'passes': PASSES, 'updates_per_pass': PER_PASS, 'updates_per_arm_seed': UPDATES,
            'QA_updates_per_arm_seed': QA_UPDATES, 'auxiliary_updates_per_arm_seed': AUX_UPDATES,
            'rng': 'sha256("English-full-pilot-{passage-order|question-order}-v1-seed{s}-pass{p}") '
                   '-> random.Random; model RNG never consumed',
            'frame_indexing': {'QA': '4*p+q', 'control_auxiliary': '4*p+2 reconstruction',
                               'treatment_auxiliary': '4*p+3 paraphrase'},
            'order_identical_across_arms_within_seed': True,
            'schedules': schedules,
            'schedule_sha256': {str(seed): canonical(schedules[str(seed)]) for seed in SEEDS}}


def validate_schedule_document(document):
    if type(document) is not dict or document.get('schema') != SCHEMA:
        raise ValueError('full pilot schedule schema required')
    expected = schedule_document()
    if document != expected:
        raise ValueError('schedule file differs from the deterministic generator output')
    return {int(seed): records for seed, records in document['schedules'].items()}


def write_schedule(path):
    path = Path(path)
    data = (json.dumps(schedule_document(), sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    with path.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument('--out', default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    path = Path(args.root).resolve() / args.out
    sha = write_schedule(path)
    print(json.dumps({'schedule': str(path), 'sha256': sha,
                      'schedule_sha256': schedule_document()['schedule_sha256']}, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
