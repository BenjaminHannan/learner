#!/usr/bin/env python3
"""Stdlib-only collector guards using symbolic paths and numeric byte fixtures."""
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import patch

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[1]
spec = importlib.util.spec_from_file_location('bridge_weights_collector', ROOT / 'scripts/sol_cloud_bridge_weights_collect_v1.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def records(size=None):
    return [dict(path=pin['path'], bytes=(size if size is not None else (pin['bytes'] or 1024)), mtime_ns=1, sha256=pin['sha256'])
            for pin in C.SPEC['expected_originals']]


class CollectorGuards(unittest.TestCase):
    def test_exact_pin_set_and_no_directory_or_reserved_substitution(self):
        C.validate_pins(C.SPEC['expected_originals'])
        for invalid in ('directory', 'reserved-symbolic-path', 'duplicate-file', 'missing-file'):
            pins = copy.deepcopy(C.SPEC['expected_originals'])
            if invalid == 'directory':
                pins[0]['path'] = pins[0]['path'].rsplit('/', 1)[0]
            elif invalid == 'reserved-symbolic-path':
                pins[0]['path'] = 'symbolic-only:/handoff/uncle-questions/example'
            elif invalid == 'duplicate-file':
                pins[1] = copy.deepcopy(pins[0])
            else:
                pins.pop()
            with self.subTest(change=invalid), self.assertRaises(ValueError):
                C.validate_pins(pins)

    def test_record_bytes_hashes_and_count_bound_to_pins(self):
        self.assertEqual(C.validate_records(records(), True), sum(r["bytes"] for r in records()))
        cases = []
        bad = records(); bad[0]['sha256'] = '0' * 64; cases.append(bad)
        bad = records(); bad[0]['path'] += '/other'; cases.append(bad)
        bad = records(); bad[0]['bytes'] = True; cases.append(bad)
        bad = records(); bad[0]['bytes'] = 0; cases.append(bad)
        bad = records(); bad[0]['bytes'] = C.PER_FILE_CAP + 1; cases.append(bad)
        cases.append(records(C.TOTAL_CAP // 4 + 1))
        cases.append(records()[:-1])
        for bad in cases:
            with self.assertRaises(ValueError):
                C.validate_records(bad, True)

    def test_stat_all_and_refuse_budget_before_hash_or_content_open(self):
        source = C.remote_probe_script()
        for size in (C.PER_FILE_CAP + 1, C.TOTAL_CAP // 4 + 1):
            stats = []
            class FakePath:
                def __init__(self, text): self.text = text
                def __str__(self): return self.text
                def resolve(self): return self
                def is_symlink(self): return False
                def is_file(self): return True
                def stat(self):
                    stats.append(self.text)
                    return SimpleNamespace(st_size=size, st_mtime_ns=1)
                def open(self, *args): raise AssertionError('No source content may open before budget acceptance')
            stream = io.StringIO()
            with patch.object(C.pathlib, 'Path', FakePath), patch.object(C.platform, 'system', return_value='Windows'), \
                 patch.object(C.sys, 'platform', 'win32'), patch.object(C.sys, 'version_info', (3, 10, 9)), \
                 patch.object(C.sys, 'executable', C.SPEC['pc_python']), \
                 patch.object(C.shutil, 'disk_usage', return_value=SimpleNamespace(free=2 * 1024**3)), \
                 patch.object(C.hashlib, 'sha256', side_effect=AssertionError('No hash before budget acceptance')) as digest, \
                 contextlib.redirect_stdout(stream):
                exec(compile(source, '<symbolic-budget-probe>', 'exec'), {})
                self.assertEqual(digest.call_count, 0)
            result = json.loads(stream.getvalue())
            self.assertEqual(result['status'], 'budget-refused')
            self.assertEqual(len(stats), 4)
            self.assertEqual(len(result['records']), 4)

    def test_remote_copy_stream_is_bounded_and_readonly(self):
        pin = C.SPEC['expected_originals'][0]
        source = C.remote_copy_script(pin, records()[0])
        tree = ast.parse(source, feature_version=(3, 9))
        self.assertIn('remaining=before.st_size', source)
        self.assertIn('f.read(min(1048576,remaining))', source)
        self.assertIn('remaining-=len(block)', source)
        opens = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr == 'open']
        self.assertEqual(len(opens), 1)
        self.assertEqual(opens[0].args[0].value, 'rb')
        self.assertNotIn('os.environ', source)
        self.assertNotIn('sys.argv', source)

    def test_publication_parts_reassemble_full_original_and_hashes(self):
        data = bytes(range(256)) * (C.PART_BYTES // 256) + bytes([3, 7, 11])
        with tempfile.TemporaryDirectory(dir=OWN) as folder:
            folder = Path(folder)
            source = folder / 'numeric.bin'; source.write_bytes(data)
            pub = folder / 'parts'; pub.mkdir()
            manifest = C.publication_parts(source, pub)
            self.assertEqual(manifest['bytes'], len(data))
            self.assertEqual(manifest['sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(len(manifest['ordered_parts']), 2)
            restored = b''
            for part in manifest['ordered_parts']:
                raw = (pub / part['name']).read_bytes()
                self.assertLessEqual(part['bytes'], C.PART_BYTES)
                self.assertEqual(part['sha256'], hashlib.sha256(raw).hexdigest())
                restored += raw
            self.assertEqual(restored, data)
            self.assertEqual(source.read_bytes(), data)

    def test_duplicate_part_destination_preserves_prior_bytes(self):
        with tempfile.TemporaryDirectory(dir=OWN) as folder:
            folder = Path(folder)
            source = folder / 'numeric.bin'; source.write_bytes(bytes([1, 2, 3]))
            pub = folder / 'parts'; pub.mkdir()
            existing = pub / 'numeric.bin.part000'; existing.write_bytes(bytes([9, 8]))
            with self.assertRaises(FileExistsError):
                C.publication_parts(source, pub)
            self.assertEqual(existing.read_bytes(), bytes([9, 8]))

    def test_timeout_refuses_expired_budget_without_launch(self):
        with self.assertRaises(TimeoutError):
            C.bounded_timeout(time.monotonic() - 1, 60)
        self.assertLessEqual(C.bounded_timeout(time.monotonic() + 1, 60), 1)

    def test_existing_output_refused_without_modifying_it_or_connecting(self):
        with tempfile.TemporaryDirectory(dir=OWN) as folder:
            folder = Path(folder).resolve()
            prior = folder / 'existing' / 'publication'; prior.mkdir(parents=True)
            evidence = prior / 'saved.json'; evidence.write_text('{"numeric":1}\n')
            stream = io.StringIO()
            with patch.dict(C.SPEC, {'watcher_publisher_root': str(folder), 'output_relative': 'existing'}), \
                 patch.object(C.platform, 'system', return_value='Darwin'), \
                 patch.object(C.sys, 'version_info', (3, 9, 6)), \
                 patch.object(C.pathlib.Path, 'cwd', return_value=folder), \
                 patch.object(C.shutil, 'disk_usage', return_value=SimpleNamespace(free=10 * 1024**3)), \
                 patch.object(C, 'probe_originals', side_effect=AssertionError('No connection for existing output')) as probe, \
                 contextlib.redirect_stdout(stream):
                self.assertEqual(C.main(), 1)
                self.assertEqual(probe.call_count, 0)
            self.assertEqual(sorted(p.name for p in prior.iterdir()), ['saved.json'])
            self.assertEqual(evidence.read_text(), '{"numeric":1}\n')
            self.assertEqual(json.loads(stream.getvalue())['error_type'], 'FileExistsError')

    def test_portable_mac39_sources_parse(self):
        ast.parse((ROOT / 'scripts/sol_cloud_bridge_weights_collect_v1.py').read_text(), feature_version=(3, 9))
        ast.parse(C.remote_probe_script(), feature_version=(3, 9))
        ast.parse(C.remote_copy_script(C.SPEC['expected_originals'][0], records()[0]), feature_version=(3, 9))


if __name__ == '__main__':
    unittest.main(verbosity=2)
