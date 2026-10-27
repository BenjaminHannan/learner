#!/usr/bin/env python3
"""Bounded real-process fixture lifecycle checks; no model or optimizer calls.

Uses one verbatim approved HUMAN TRAIN record in temporary SQLite databases.
The bundle reference is explicitly metadata only, never a model/candidate or
an optimizer receipt. Production source and prior test evidence stay unchanged.
"""
import argparse
import datetime
import hashlib
import importlib
import json
import multiprocessing
from pathlib import Path
import queue
import sqlite3
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
OWN = ROOT / 'artifacts/sol-cloud-fixture-concurrency-20260930'
ROW_ID = '5733be284776f41900661182'
PINS = {
    'scripts/sol_cloud_fixture_v1.py': '0480ffced7883e8be721842e53ba9439102a019149027f81ca2455f8492dff24',
    'scripts/sol_cloud_day_adapter_v1.py': '5cef30bf8cc46667a41635ee6f4167b2cb4ab1f4915023d7ed7d2ba8db4f774f',
    'scripts/sol_cloud_trainonly_v1.py': 'a730907978cca5856c8b6ca318d2dac25e85d2df15390a5f085549884698cadf',
    'artifacts/sol-cloud-trainonly-20260930/TRAIN-PACKET.json': '46ae697a2dc183048832fed4ef42144888afa08fe5e82db5ccb338c5703fea7e',
    'artifacts/sol-cloud-trainonly-20260930/TRAIN-MANIFEST.json': '690bd7f6b12fadc5c350ed65d710c82e4e4bd1d8e1dda968e5f8f50b8fc75b7b',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def modules():
    for path, expected in PINS.items():
        if path.endswith('.py') and digest(ROOT / path) != expected:
            raise RuntimeError('production source pin changed: ' + path)
    sys.path.insert(0, str(ROOT / 'scripts'))
    return (importlib.import_module('sol_cloud_fixture_v1'),
            importlib.import_module('sol_cloud_day_adapter_v1'))


def require(value, message):
    if not value:
        raise AssertionError(message)


def source_spec():
    return {name: {'path': str(ROOT / path), 'sha256': PINS[path]}
            for name, path in (
                ('packet', 'artifacts/sol-cloud-trainonly-20260930/TRAIN-PACKET.json'),
                ('manifest', 'artifacts/sol-cloud-trainonly-20260930/TRAIN-MANIFEST.json'),
                ('loader', 'scripts/sol_cloud_trainonly_v1.py'))}


def capture_case(root, label):
    fixture, adapter = modules()
    directory = root / label
    directory.mkdir()
    reference = directory / 'metadata-reference-only.json'
    reference.write_text(json.dumps({'scope': 'SQLite fixture lifecycle test only',
                                     'model_included': False, 'actual_user_day': False}))
    state = directory / 'state'
    store = fixture.FixtureStore(state, allowed_root=root)
    spec = {'source': source_spec(), 'bundle': fixture.pin(reference),
            'state_dir': str(state), 'fixture_row_ids': [ROW_ID],
            'idle_seconds': 1, 'batch_path': str(directory / 'batch.json'),
            'claim_id': label + '-claim'}
    capture = store.capture(spec['source'], spec['bundle'], spec['fixture_row_ids'])
    require(capture['actual_user_day'] is False, 'capture falsely claims live user day')
    # Exercise the real clock/idle protocol; no patched time or synthetic day.
    time.sleep(1.02)
    return store, spec, capture


def child(mode, config, barrier, results):
    fixture, adapter = modules()
    connections = []

    def audit(event, args):
        if event == 'sqlite3.connect':
            database = str(args[0])
            connections.append({'read_only': database.endswith('?mode=ro')})

    sys.addaudithook(audit)
    try:
        if mode in ('claim', 'begin'):
            store = fixture.FixtureStore(config['state_dir'], allowed_root=config['root'])
        barrier.wait(timeout=15)
        if mode == 'claim':
            result = store.snapshot(config['spec'], allowed_root=config['root'])
        elif mode == 'begin':
            store.begin_dispatch(config['claim'], 1)
            result = {'started': True, 'actual_user_day': False}
        elif mode in ('admit', 'inspect'):
            function = adapter.load_rows if mode == 'admit' else adapter.inspect_rows
            rows = function(config['claim']['batch']['path'],
                            config['claim']['batch']['sha256'],
                            config['bundle']['sha256'], allowed_root=config['root'])
            result = {'row_ids': [row['source_row_id'] for row in rows],
                      'row_digests': [adapter.identity(row) for row in rows],
                      'actual_user_day': [row['actual_user_day'] for row in rows],
                      'origins': [row['origin'] for row in rows]}
        else:
            raise ValueError('unknown bounded test action')
        results.put({'pid': __import__('os').getpid(), 'mode': mode,
                     'ok': True, 'result': result, 'sqlite_connections': connections})
    except Exception as error:
        results.put({'pid': __import__('os').getpid(), 'mode': mode, 'ok': False,
                     'error_type': type(error).__name__, 'error': str(error),
                     'sqlite_connections': connections})


def parallel(actions):
    context = multiprocessing.get_context('spawn')
    barrier = context.Barrier(len(actions) + 1)
    results = context.Queue()
    processes = [context.Process(target=child, args=(mode, config, barrier, results))
                 for mode, config in actions]
    started = time.monotonic()
    try:
        for process in processes:
            process.start()
        barrier.wait(timeout=15)
        records = [results.get(timeout=20) for _ in processes]
        for process in processes:
            process.join(timeout=5)
        require(all(not process.is_alive() and process.exitcode == 0 for process in processes),
                'test child did not finish cleanly')
        return {'elapsed_seconds': time.monotonic() - started,
                'actions': sorted(records, key=lambda item: item['pid'])}
    finally:
        # Only our temporary test children can be stopped; no PC/live jobs exist.
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        results.close()
        results.join_thread()


def config(root, spec, claim=None):
    return {'root': str(root), 'state_dir': spec['state_dir'],
            'spec': spec, 'bundle': spec['bundle'], 'claim': claim}


def claim_race(root, raw):
    fixture, adapter = modules()
    for round_id in range(2):
        store, spec, capture = capture_case(root, 'claim-race-' + str(round_id))
        actions = []
        for number in range(4):
            competing = dict(spec, claim_id=spec['claim_id'] + '-' + str(number),
                             batch_path=str(Path(spec['batch_path']).with_name('batch-' + str(number) + '.json')))
            actions.append(('claim', config(root, competing)))
        result = parallel(actions)
        raw.append({'phase': 'four-process independent claim race', 'round': round_id,
                    'capture': capture, **result})
        winners = [item for item in result['actions'] if item['ok']]
        losers = [item for item in result['actions'] if not item['ok']]
        require(len(winners) == 1 and len(losers) == 3, 'claim race did not produce exactly one owner')
        require(all(item['error_type'] == 'FixtureError' for item in losers), 'claim loser was a lock/protocol error')
        require(winners[0]['result']['actual_user_day'] is False, 'claim mislabeled actual user day')
        with store.connect() as db:
            count, status = db.execute('SELECT count(*),min(status) FROM claims').fetchone()
        require(count == 1 and status == 'claimed', 'durable claims disagree with exactly one owner')
        require(len(list(Path(spec['batch_path']).parent.glob('batch-*.json'))) == 1,
                'losing claim left an orphan eligible batch')


def begin_race(root, raw):
    store, spec, capture = capture_case(root, 'begin-race')
    claim = store.snapshot(spec, allowed_root=root)
    result = parallel([('begin', config(root, spec, claim)) for _ in range(4)])
    raw.append({'phase': 'four-process begin-dispatch race', 'capture': capture,
                'claim': claim, **result})
    require(sum(item['ok'] for item in result['actions']) == 1, 'duplicate running dispatch owner')
    require(all(item['ok'] or item['error_type'] == 'FixtureError' for item in result['actions']),
            'begin-dispatch loser was a lock/protocol error')
    admitted = parallel([('admit', config(root, spec, claim))])
    raw.append({'phase': 'sole running owner source admission; no dispatch/model', **admitted})
    assert_admitted(admitted)


def assert_admitted(result):
    for item in result['actions']:
        require(item['ok'], 'read-only HUMAN TRAIN admission failed: ' + item.get('error_type', ''))
        require(item['result']['row_ids'] == [ROW_ID], 'admitted identity changed')
        require(item['result']['actual_user_day'] == [False], 'transition laundered fixture origin')
        require(item['result']['origins'] == ['verified-human-TRAIN-fixture'], 'fixture provenance lost')
        require(item['sqlite_connections'] == [{'read_only': True}],
                'admission attempted a write-capable SQLite constructor')


def committed_activity(root, raw):
    fixture, adapter = modules()
    for running in (False, True):
        store, spec, capture = capture_case(root, 'activity-' + str(running).lower())
        claim = store.snapshot(spec, allowed_root=root)
        if running:
            store.begin_dispatch(claim, 1)
        store.activity()  # committed before fresh admission children are released
        result = parallel([('admit', config(root, spec, claim)),
                           ('inspect', config(root, spec, claim)),
                           ('begin', config(root, spec, claim))])
        raw.append({'phase': 'committed cross-process activity invalidation',
                    'initial_status': 'running' if running else 'claimed',
                    'capture': capture, 'claim': claim, **result})
        by_mode = {item['mode']: item for item in result['actions']}
        require(not by_mode['admit']['ok'] and by_mode['admit']['error_type'] == 'FixtureError',
                'activity resumed but new execution admission succeeded')
        require(not by_mode['begin']['ok'] and by_mode['begin']['error_type'] == 'FixtureError',
                'activity resumed but new dispatch start succeeded')
        assert_admitted({'actions': [by_mode['inspect']]})


def writer_lock_readers(root, raw):
    store, spec, capture = capture_case(root, 'writer-lock')
    claim = store.snapshot(spec, allowed_root=root)
    store.begin_dispatch(claim, 1)
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE state SET activity=activity WHERE id=1')
        require(db.in_transaction, 'actual writer transaction missing')
        result = parallel([('admit', config(root, spec, claim)),
                           ('inspect', config(root, spec, claim))])
        raw.append({'phase': 'independent read-only admission/recount while dirty writer remains held',
                    'writer_in_transaction_before_and_after': db.in_transaction,
                    'capture': capture, 'claim': claim, **result})
        require(db.in_transaction, 'writer transaction ended before readers completed')
        assert_admitted(result)
        db.rollback()


def consumed_terminal_claims(root, raw):
    for status in ('complete', 'failed'):
        store, spec, capture = capture_case(root, 'consumed-' + status)
        claim = store.snapshot(spec, allowed_root=root)
        store.begin_dispatch(claim, 1)
        store.finish_dispatch(claim['claim_id'], status)
        result = parallel([('admit', config(root, spec, claim)),
                           ('inspect', config(root, spec, claim)),
                           ('begin', config(root, spec, claim))])
        raw.append({'phase': 'consumed terminal claim; no candidate or optimizer receipt',
                    'terminal_status': status, 'capture': capture, 'claim': claim, **result})
        by_mode = {item['mode']: item for item in result['actions']}
        require(not by_mode['admit']['ok'] and by_mode['admit']['error_type'] == 'FixtureError',
                'terminal claim re-admitted for execution')
        require(not by_mode['begin']['ok'] and by_mode['begin']['error_type'] == 'FixtureError',
                'terminal claim re-started')
        assert_admitted({'actions': [by_mode['inspect']]})
        saved = json.loads(Path(claim['batch']['path']).read_text())
        require(saved['actual_user_day'] is False and saved['model_authored_text_included'] is False,
                'saved immutable fixture origin changed after terminal status')


CASES = [('two rounds of simultaneous independent claims', claim_race),
         ('simultaneous dispatch lifecycle starts', begin_race),
         ('committed activity across process boundaries', committed_activity),
         ('read-only readers under actual dirty writer transaction', writer_lock_readers),
         ('complete/failed lifecycle claims cannot be re-admitted', consumed_terminal_claims)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    require(output.is_relative_to(OWN.resolve()) and output != OWN.resolve(), 'owned output subdirectory required')
    output.mkdir(parents=True, exist_ok=False)
    for path, expected in PINS.items():
        require(digest(ROOT / path) == expected, 'externally pinned bytes changed: ' + path)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    plan = {'schema': 'sol.cloud.fixture-concurrency-plan.v1', 'created_utc': started,
            'source_pins': PINS, 'test_source_sha256': digest(__file__), 'human_train_record_id': ROW_ID,
            'cases': [name for name, function in CASES], 'claim_competitors': 4, 'claim_rounds': 2,
            'idle_seconds': 1, 'child_barrier_timeout_seconds': 15, 'child_result_timeout_seconds': 20,
            'actual_user_day': False, 'model_calls': 0, 'optimizer_updates': 0,
            'live_queue': False, 'scope': 'engineering concurrency/lifecycle; no executed sleep or semantics'}
    (output / 'PRE-RUN.json').write_text(json.dumps(plan, indent=2) + '\n')
    raw = []
    results = []
    with tempfile.TemporaryDirectory(prefix='sol-cloud-fixture-concurrency-') as temporary:
        root = Path(temporary)
        for name, function in CASES:
            case_started = time.monotonic()
            try:
                function(root, raw)
                item = {'case': name, 'pass': True, 'wall_seconds': time.monotonic() - case_started}
            except Exception as error:
                item = {'case': name, 'pass': False, 'wall_seconds': time.monotonic() - case_started,
                        'error_type': type(error).__name__, 'error': str(error),
                        'traceback': traceback.format_exc()}
            results.append(item)
            with (output / 'EVENTS.jsonl').open('a') as stream:
                stream.write(json.dumps(item, sort_keys=True) + '\n')
            # Keep actual failed and completed actions even if a later case fails.
            (output / 'RAW.json').write_text(json.dumps(raw, indent=2) + '\n')
            print(json.dumps(item, sort_keys=True), flush=True)
    report = {'schema': 'sol.cloud.fixture-concurrency-report.v1', 'started_utc': started,
              'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'passed': sum(item['pass'] for item in results), 'total': len(results), 'cases': results,
              'actual_user_day': False, 'model_calls': 0, 'optimizer_updates': 0, 'network_calls': 0,
              'training_cycle_executed': False, 'production_source_mutations': 0,
              'test_children_only': True, 'temporary_databases_removed': True,
              'source_pins': PINS, 'test_source_sha256': digest(__file__),
              'raw_sha256': digest(output / 'RAW.json'), 'plan_sha256': digest(output / 'PRE-RUN.json'),
              'reference_only': 'Temporary JSON is no model, checkpoint, candidate or optimizer evidence.',
              'limits': ['These are SQLite engineering lifecycle tests, not executed sleep or semantic evidence.',
                         'Complete/failed are state-machine test transitions; no real candidate rollback occurred.',
                         'Activity invalidation is checked after activity commit, not during an optimizer step.',
                         'SQLite BEGIN IMMEDIATE permits readers; an exclusive writer lock is outside this test.']}
    (output / 'REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'total': report['total'], 'report': str(output / 'REPORT.json')}), flush=True)
    return 0 if report['passed'] == report['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
