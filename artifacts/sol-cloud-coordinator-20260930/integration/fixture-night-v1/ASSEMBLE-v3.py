#!/usr/bin/env python3
"""Construct a held, cross-platform fixture packet; no model imports or runs."""
import ast
import hashlib
import io
import json
from pathlib import Path, PureWindowsPath
import random
import tarfile

ROOT = Path(__file__).resolve().parents[4]
OWN = Path(__file__).resolve().parent
PC = PureWindowsPath(r'C:\Users\benja\sol-cloud-fixture-night-v3')
DEPLOY = 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(relative, value):
    path = OWN / relative
    with path.open('x', encoding='utf8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')
    return path

def windows(relative):
    return str(PC.joinpath(*Path(relative).parts))

def record(relative):
    return {'path': windows(relative), 'sha256': sha(ROOT / relative)}

def main():
    metadata = json.loads((OWN / 'ASSEMBLY-METADATA-v1.json').read_text())
    plan = metadata['plan_candidate']
    plan['comparator'] = 'same source checkpoint before/after; no comparative qualification'
    plan['noise_policy'] = 'identical guard-before repeat, measured CE drift; no gain claim'
    plan['pass_marks'] = {'mechanics': '25 global core optimizer calls plus actual per-tensor participation, populated Adam, reload, frozen components and exact pointer preservation; explicit rollback only', 'semantics': 'unqualified; always inactive'}
    sampling = random.Random(plan['sample_seed'])
    plan['sample_schedule'] = {'0': [[sampling.choice(plan['experience_ids']), sampling.choice(plan['replay_ids'])] for _ in range(25)]}
    plan_path = save('PLAN-v3.json', plan)
    closure = set(metadata['required_source_files']) | {'scripts/sol_spatial_poc_ordered_v2.py', 'scripts/sol_translator_ground_ordered_v10.py', 'scripts/sol_stop_ordered_api2.py'}
    todo = list(closure)
    while todo:
        relative = todo.pop()
        tree = ast.parse((ROOT / relative).read_text())
        names = []
        nodes = list(tree.body)
        visited = []
        while nodes:
            node = nodes.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name) and node.test.left.id == '__name__':
                continue
            visited.append(node)
            nodes.extend(ast.iter_child_nodes(node))
        for node in visited:
            if isinstance(node, ast.Import):
                names.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        for name in names:
            candidates = ['scripts/' + name.replace('.', '/') + '.py', name.replace('.', '/') + '.py']
            for candidate in candidates:
                if (ROOT / candidate).is_file() and candidate not in closure:
                    closure.add(candidate)
                    todo.append(candidate)
    # This helper is imported inside the frozen decoder loader.
    closure.add('scripts/sol_translator_cache_policy_v6.py')
    pins = {windows(relative): sha(ROOT / relative) for relative in sorted(closure)}
    train = {key: record(item['path']) for key, item in metadata['TRAIN_packet_pins'].items()}
    binding = {'version': 'sol.cloud.night.v1', 'seed': 0,
               'plan_sha256': sha(plan_path), 'driver_sha256': sha(ROOT / 'scripts/sol_cloud_night_v1.py'),
               'dependency_pins': pins, 'source': metadata['source_tuple'], 'train': train,
               'modules': {'ordered': 'sol_spatial_poc_ordered_v2', 'graph': 'sol_translator_ground_ordered_v10',
                           'native': 'sol_stop_ordered_api2', 'trainonly': 'sol_cloud_trainonly_v1',
                           'day_adapter': 'sol_cloud_day_adapter_v1'}}
    binding_path = save('BINDING-v3.json', binding)
    fixture = 'artifacts/sol-cloud-fixture-20260930/run-v3'
    night = 'artifacts/sol-cloud-night-20260930/run-v3'
    spec = {'schema': 'sol.cloud.fixture-spec.v1', 'actual_user_day': False, 'activation_allowed': False,
            'source': {**train, 'loader': record('scripts/sol_cloud_trainonly_v1.py')},
            'bundle': binding['source']['previous_bundle'], 'fixture_row_ids': plan['experience_ids'],
            'state_dir': windows(fixture + '/state'), 'batch_path': windows(fixture + '/eligible-batch.json'),
            'claim_id': 'sol-cloud-fixture-night-v3-source0', 'claim_receipt': windows(fixture + '/claim.json'),
            'completion_receipt': windows(fixture + '/completion.json'), 'failure_receipt': windows(fixture + '/failure.json'),
            'dispatch_log': windows(fixture + '/dispatch.log'), 'rollback_receipt': windows(night + '/rollback.json'),
            'idle_seconds': 2, 'wait_seconds': 10, 'pipeline_seconds': 900,
            'dependency_pins': [{'path': key, 'sha256': value} for key, value in pins.items()],
            'pipeline': {'entrypoint': record('scripts/sol_cloud_night_v1.py'),
                         'argv': ['{python}', windows('scripts/sol_cloud_night_v1.py'), '--binding', windows(DEPLOY + '/BINDING-v3.json'),
                                  '--binding-sha256', sha(binding_path), '--plan', windows(DEPLOY + '/PLAN-v3.json'),
                                  '--seed', '0', '--output', windows(night), '--day-rows', '{day_batch}', '--day-sha256', '{day_batch_sha256}']}}
    spec_path = save('FIXTURE-SPEC-v3.json', spec)
    files = {relative: sha(ROOT / relative) for relative in sorted(closure)}
    for relative in [item['path'] for item in metadata['TRAIN_packet_pins'].values()] + [DEPLOY + '/PLAN-v3.json', DEPLOY + '/BINDING-v3.json', DEPLOY + '/FIXTURE-SPEC-v3.json']:
        files[relative] = sha(ROOT / relative)
    payload = OWN / 'payload-v3.tar.gz'
    with payload.open('xb') as stream:
        import gzip
        with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for relative in sorted(files):
                    data = (ROOT / relative).read_bytes()
                    entry = tarfile.TarInfo(relative)
                    entry.size, entry.mtime, entry.mode = len(data), 0, 0o644
                    archive.addfile(entry, io.BytesIO(data))
    assert payload.stat().st_size < 1024 ** 2, 'new transport payload exceeds sealed 1MiB cap'
    package = {'schema': 'sol.cloud.fixture-package.v1', 'status': 'HELD; no live queue until verified PC ownership',
               'pc_root': str(PC), 'files': files, 'payload': {'sha256': sha(payload), 'bytes': payload.stat().st_size},
               'plan_sha256': sha(plan_path), 'binding_sha256': sha(binding_path), 'spec_sha256': sha(spec_path),
               'actual_user_day': False, 'activation_allowed': False, 'model_payloads_included': False,
               'mixed_corpus_or_docs_included': False, 'new_output_and_atomic_cap_bytes': 256 * 1024 ** 2,
               'disk_floor_bytes': 1024 ** 3, 'source_closure': sorted(closure)}
    package_path = save('PACKAGE-v3.json', package)
    checks = {'schema': 'sol.cloud.fixture-assembly-checks.v1', 'model_imports': 0,
              'closure_file_count': len(closure), 'payload_bytes': payload.stat().st_size,
              'hashes': {path.name: sha(path) for path in [plan_path, binding_path, spec_path, package_path, payload]},
              'windows_path_roundtrip': all(str(PureWindowsPath(key)) == key and key.startswith(str(PC) + '\\') for key in pins),
              'disjoint_identity_count': len(set(plan['experience_ids'] + plan['replay_ids'] + plan['guard_ids'])),
              'schedule_updates': len(plan['sample_schedule']['0']), 'source_seed': 0,
              'no_direct_execution': True, 'no_original_training_rerun': True}
    save('ASSEMBLY-CHECKS-v3.json', checks)
    print(json.dumps(checks))

if __name__ == '__main__':
    main()
