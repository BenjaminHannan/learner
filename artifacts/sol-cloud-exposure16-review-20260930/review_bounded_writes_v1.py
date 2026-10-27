#!/usr/bin/env python3
"""Independent nontraining numeric-byte tests of the frozen r5 write guards."""
from __future__ import annotations
import ast
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
SCRIPT = ROOT / 'scripts/sol_cloud_exposure16_v5.py'


def main():
    spec = importlib.util.spec_from_file_location('independent_bounded_sink', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tests = []
    def passed(name, **evidence):
        tests.append(dict(name=name, passed=True, **evidence))
    def rejected(action):
        try:
            action()
        except (RuntimeError, ValueError):
            return
        raise AssertionError('expected rejection before bytes were written')
    def sink(cap=8, callback=lambda extent: None):
        backing = io.BytesIO()
        return backing, module.BoundedFileSink(backing, cap, callback)
    backing, bounded = sink()
    assert bounded.write(bytes([1, 2, 3, 4])) == 4
    assert bounded.write(bytes([5, 6, 7, 8])) == 4
    assert backing.getvalue() == bytes(range(1, 9)) and bounded.extent == 8
    passed('exact_per_file_boundary')
    rejected(lambda: bounded.write(bytes([9])))
    assert backing.getvalue() == bytes(range(1, 9)) and bounded.extent == 8
    passed('overflow_append_rejected_without_growth')
    backing, bounded = sink()
    rejected(lambda: bounded.write(bytes(range(9))))
    assert backing.getvalue() == b'' and bounded.extent == 0
    passed('initial_oversized_write_rejected_before_any_growth')
    charged = []
    backing, bounded = sink(callback=charged.append)
    bounded.write(bytes(range(8)))
    bounded.seek(1)
    bounded.write(bytes([42, 43]))
    assert bounded.extent == 8 and len(backing.getvalue()) == 8 and charged == [8, 8]
    passed('random_seek_overwrite_keeps_high_water_extent')
    old = bounded.tell()
    rejected(lambda: bounded.seek(9))
    assert bounded.tell() == old and len(backing.getvalue()) == 8
    passed('seek_beyond_cap_restores_position')
    backing, bounded = sink()
    bounded.seek(7)
    rejected(lambda: bounded.write(bytes([1, 2])))
    assert backing.getvalue() == b''
    bounded.write(bytes([1]))
    assert len(backing.getvalue()) == 8 and bounded.extent == 8
    passed('sparse_write_bounded_by_extent')
    def five_only(extent):
        if extent > 5:
            raise RuntimeError('NONTRAINING numeric cap fixture')
    backing, bounded = sink(callback=five_only)
    bounded.write(bytes(range(4)))
    rejected(lambda: bounded.write(bytes(range(2))))
    assert len(backing.getvalue()) == 4 and bounded.extent == 4
    passed('aggregate_callback_rejects_before_backing_write')
    # Execute the exact nested before_extent guard in an isolated numeric scope.
    tree = ast.parse(SCRIPT.read_text())
    functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    state = {'actual': 0, 'total': 100, 'free': 1000}
    tmp = SimpleNamespace(stat=lambda: SimpleNamespace(st_size=state['actual']))
    env = {'tmp': tmp, 'total_bytes': lambda: state['total'], 'out': 'NONTRAINING-NUMERIC-FIXTURE',
           'budget': {'operating_run_output_cap_bytes': 110, 'retained_free_bytes': 100},
           'shutil': SimpleNamespace(disk_usage=lambda _: SimpleNamespace(free=state['free']))}
    code = ast.fix_missing_locations(ast.Module(body=[functions['before_extent']], type_ignores=[]))
    exec(compile(code, str(SCRIPT), 'exec'), env)
    callback = env['before_extent']
    state['free'] = 100 + 65536 + 10
    backing, bounded = sink(cap=20, callback=callback)
    bounded.write(bytes([1, 2]))
    bounded.write(bytes([3, 4]))
    assert len(backing.getvalue()) == 4 and bounded.extent == 4
    passed('buffered_pending_growth_charged_once', reported_stat_bytes=0, charged_extent_bytes=4)
    rejected(lambda: bounded.write(bytes(range(7))))
    assert len(backing.getvalue()) == 4
    passed('aggregate_one_byte_overflow_rejected_before_write')
    # Simulate an earlier buffer flush: total and stat include four bytes.
    state.update(actual=4, total=104)
    bounded.write(bytes(range(6)))
    assert len(backing.getvalue()) == 10
    passed('persisted_growth_not_double_counted_at_exact_aggregate_boundary')
    bounded.seek(0)
    bounded.write(bytes([42]))
    assert len(backing.getvalue()) == 10
    passed('overwrite_at_aggregate_cap_allowed_without_extra_growth')
    state.update(actual=0, total=100, free=100 + 65536 + 4 - 1)
    backing, bounded = sink(cap=20, callback=callback)
    rejected(lambda: bounded.write(bytes(range(4))))
    assert len(backing.getvalue()) == 0
    passed('reserve_allocation_margin_one_byte_short_rejects_before_write')
    state['free'] += 1
    bounded.write(bytes(range(4)))
    assert len(backing.getvalue()) == 4
    passed('reserve_plus_pending_plus64KiB_exact_boundary_allowed')
    state['free'] -= 1
    rejected(bounded.flush)
    assert len(backing.getvalue()) == 4
    passed('flush_rechecks_buffered_pending_and_allocation_reserve')
    # A stdlib binary ZIP serializer exercises header seeks/overwrites, central
    # directory writes and flushing, without Torch, model data or text inputs.
    backing, bounded = sink(cap=2048)
    numeric = bytes(range(64))
    with zipfile.ZipFile(bounded, 'w', compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('numeric.bin', numeric)
    with zipfile.ZipFile(io.BytesIO(backing.getvalue()), 'r') as archive:
        assert archive.read('numeric.bin') == numeric
    passed('binary_zip_serializer_roundtrip_with_seeks', actual_serialized_bytes=len(backing.getvalue()))
    backing, bounded = sink(cap=32)
    rejected(lambda: zipfile.ZipFile(bounded, 'w').writestr('numeric.bin', numeric))
    assert len(backing.getvalue()) <= 32
    passed('binary_serializer_overshoot_rejected_before_cap', actual_serialized_bytes=len(backing.getvalue()))
    # Execute the exact JSON writer with a rejecting guard. No fixture file may
    # exist if the allocation reserve rejects the write.
    json_env = {'json': json, 'raw_bytes': lambda: 0, 'budget': {'raw_JSON_cap_bytes_per_seed': 10000},
                'os': SimpleNamespace(fsync=lambda _: None)}
    guards = []
    def reject_json(estimate):
        guards.append(estimate)
        raise RuntimeError('NONTRAINING allocation reserve fixture')
    json_env['disk_guard'] = reject_json
    exec(compile(ast.fix_missing_locations(ast.Module(body=[functions['json_write']], type_ignores=[])), str(SCRIPT), 'exec'), json_env)
    fixture_path = OWN / 'NONTRAINING-JSON-MUST-NOT-EXIST.json'
    assert not fixture_path.exists()
    record = {'numeric_fixture': 42}
    rejected(lambda: json_env['json_write'](fixture_path, record))
    expected = len((json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')) + 65536
    assert guards == [expected] and not fixture_path.exists()
    passed('JSON_allocation_guard_before_open_exact_bytes_plus64KiB', checked_bytes=expected)
    # The model graph, diagnostic and entire update loop must be AST-identical
    # across the cap repair; line movement is intentionally ignored.
    old_tree = ast.parse((ROOT / 'scripts/sol_cloud_exposure16_v3.py').read_text())
    old_functions = {n.name: n for n in ast.walk(old_tree) if isinstance(n, ast.FunctionDef)}
    hashes = {}
    for key in ('graph', 'packet', 'diagnostic'):
        old_dump = ast.dump(old_functions[key], include_attributes=False)
        new_dump = ast.dump(functions[key], include_attributes=False)
        assert old_dump == new_dump
        hashes[key] = hashlib.sha256(new_dump.encode()).hexdigest()
    def update_loop(tree):
        return next(n for n in ast.walk(tree) if isinstance(n, ast.For)
                    and isinstance(n.iter, ast.Call) and isinstance(n.iter.func, ast.Name)
                    and n.iter.func.id == 'enumerate' and len(n.iter.args) == 2
                    and isinstance(n.iter.args[0], ast.Name) and n.iter.args[0].id == 'schedule')
    loop_dump = ast.dump(update_loop(tree), include_attributes=False)
    assert ast.dump(update_loop(old_tree), include_attributes=False) == loop_dump
    hashes['entire_800_update_loop'] = hashlib.sha256(loop_dump.encode()).hexdigest()
    passed('model_graph_generation_diagnostics_and_fit_AST_unchanged_from_r3', AST_sha256=hashes)
    # Filesystem allocation query and check must precede the first evidence write.
    source = SCRIPT.read_text()
    assert source.index('if not 0 < allocation_unit <= 65536:') < source.index("    json_write(out / 'LAUNCH.json'")
    assert 'GetDiskFreeSpaceW' in source and 'os.statvfs(out)' in source
    passed('native_allocation_unit_guard_precedes_first_evidence_write')
    report = {'schema': 'sol.cloud.exposure16.independent.bounded-writer-tests.v1',
        'seal_sha256': hashlib.sha256((ROOT / 'artifacts/sol-cloud-exposure16-20260930/r5/SEAL.json').read_bytes()).hexdigest(),
        'driver_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(), 'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'tests': tests, 'test_count': len(tests), 'passed_count': sum(t['passed'] for t in tests), 'all_passed': all(t['passed'] for t in tests),
        'methods': 'Numeric BytesIO fixtures and exact AST-extracted guards; stdlib ZIP serializer only',
        'actual_target_PyTorch_serializer_verified': False, 'actual_Windows_allocation_unit_verified': False,
        'models_loaded': 0, 'optimizer_updates': 0, 'GPU_calls': 0, 'actual_processes_launched': 0,
        'human_or_reserved_source_opened': False, 'all_generated_artifacts_are_nontraining': True}
    with (OWN / 'BOUNDED-WRITE-TESTS-r5-v1.json').open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'numeric_guard_tests': len(tests), 'passed': report['passed_count'], 'models_loaded': 0, 'optimizer_updates': 0}))


if __name__ == '__main__':
    main()
