"""Small stdlib compatibility/path/hash fixtures; zero network or model calls."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE / 'collect_closed_r2_v1.py'
specification = importlib.util.spec_from_file_location('closed_r2_collect', SOURCE)
C = importlib.util.module_from_spec(specification)
specification.loader.exec_module(C)
MANIFEST_BASE = ROOT / 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r2'
MANIFEST_PINS = {0:'0d7146b8c2caed72c2f9866895d451b2108c4e18a688f314ae51f330b63daa11',
                 1:'90c2038d47d6fb3ec628d4f4808ebe39606db5a791c193314104a825958d62c4'}


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='cpu-fixture-', dir=HERE)
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def manifest(self, seed=0):
        path = MANIFEST_BASE / ('actual-s%d/cloud-pinned/PC-FINAL-MANIFEST.json' % seed)
        self.assertEqual(C.sha(path), MANIFEST_PINS[seed])
        return json.loads(path.read_text())

    def test_exact_three_saved_records_and_combined_budget(self):
        total = 0
        for seed in (0, 1):
            manifest = self.manifest(seed)
            records = C.selected_records(manifest, seed, manifest['job'])
            self.assertEqual({Path(r['relative']).name for r in records}, C.NAMES)
            self.assertEqual(len(records), 3)
            self.assertLessEqual(sum(r['bytes'] for r in records), C.SEED_CAP)
            total += sum(r['bytes'] for r in records)
        self.assertLessEqual(total, C.TOTAL_CAP)
        self.assertEqual(C.PART, 4 * 1024 ** 2)

    def test_missing_duplicate_and_unclosed_manifest_refuse(self):
        manifest = self.manifest()
        for alteration in ('missing', 'duplicate', 'rc', 'seed'):
            bad = copy.deepcopy(manifest)
            if alteration == 'missing':
                bad['records'] = [r for r in bad['records'] if Path(r['relative']).name != 'connected-resume.pt']
            elif alteration == 'duplicate':
                bad['records'].append(copy.deepcopy(bad['records'][0]))
            elif alteration == 'rc':
                bad['returncode'] = 1
            else:
                bad['seed'] = 1
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                C.selected_records(bad, 0, manifest['job'])

    def test_literal_paths_and_no_extra_allowlist(self):
        for path in ('/absolute', '../escape', 'a/../b', 'a//b', 'a/./b', 'C:/file', 'a\\b', '', 'x\x00y'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                C.relative_path(path)
        manifest = self.manifest()
        altered = copy.deepcopy(manifest)
        for record in altered['records']:
            if Path(record['relative']).name == 'connected-resume.pt':
                record['relative'] = record['relative'].replace('connected-resume.pt', 'unexpected-resume.pt')
        with self.assertRaises(ValueError):
            C.selected_records(altered, 0, manifest['job'])

    def test_budget_refuses_before_any_remote_action(self):
        manifest = self.manifest()
        for record in manifest['records']:
            if Path(record['relative']).name == 'connected-resume.pt':
                record['bytes'] = C.SEED_CAP
        with mock.patch.object(C, 'probe') as probe, self.assertRaises(ValueError):
            C.selected_records(manifest, 0, manifest['job'])
        probe.assert_not_called()

    def test_metadata_allowlist_rejects_before_hash(self):
        with mock.patch.object(C, 'sha') as sha:
            for relative in (C.OWN+'/not-selected.json', C.EXPOSURE+'/mac-launch-v1/r9/PC-FINAL-MANIFEST.json',
                             'handoff/uncle-questions/not-opened.json'):
                with self.assertRaises(ValueError):
                    C.pinned_json({'path':relative, 'sha256':'0'*64})
            sha.assert_not_called()

    def test_metadata_symlink_rejected_before_hash(self):
        relative = C.OWN+'/SPEC-s0-r2-v1.json'
        with mock.patch.object(C, 'W', self.directory), mock.patch.object(Path, 'is_symlink', return_value=True), mock.patch.object(C, 'sha') as sha:
            with self.assertRaises(ValueError):
                C.pinned_json({'path':relative,'sha256':'0'*64})
            sha.assert_not_called()

    def test_native_syntax_and_import_only_compatibility(self):
        ast.parse(SOURCE.read_text(), feature_version=(3, 9))
        generated = C.remote_header([{'relative':'allowed.bin','bytes':1,'sha256':'0'*64}])
        ast.parse(generated, feature_version=(3, 10))
        with mock.patch.object(sys, 'version_info', (3, 9, 6)), mock.patch.object(C.subprocess, 'Popen') as spawn:
            namespace = {'__name__':'_import_only_fixture', '__file__':str(SOURCE)}
            exec(compile(SOURCE.read_text(), str(SOURCE), 'exec'), namespace)
            spawn.assert_not_called()
            self.assertEqual(namespace['NAMES'], C.NAMES)

    def test_remote_stdlib_hash_inspection_no_writes(self):
        data = bytes(range(256)) * 4
        path = self.directory/'allowed.bin';path.write_bytes(data)
        record = {'relative':'allowed.bin','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        with mock.patch.object(C, 'PC', str(self.directory)), mock.patch.object(sys, 'version_info', (3,10,9)):
            namespace = {}
            source = C.remote_header([record]);exec(source,namespace)
            self.assertEqual({k:namespace['inspect'](record)[k] for k in record},record)
        self.assertEqual(path.read_bytes(),data)
        self.assertNotIn('.open(\'w', source)
        self.assertNotIn('torch',source)

    def test_local_binary_parts_full_hash_and_extra_extent_refusal(self):
        data = bytes(range(256)) * (C.PART//256) + bytes(range(201))
        path = self.directory/'fixture.bin';path.write_bytes(data)
        record = {'relative':'connected-resume.pt','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        out = self.directory/'parts';out.mkdir()
        source = 'import sys\nwith open(%r,"rb") as f:sys.stdout.buffer.write(f.read())\n' % str(path)
        result = C.stream_parts([sys.executable,'-B','-'],source,record,out)
        self.assertEqual([p['bytes'] for p in result['ordered_parts']],[C.PART,201])
        self.assertEqual(b''.join((out/p['name']).read_bytes() for p in result['ordered_parts']),data)
        bad = dict(record,bytes=len(data)-1)
        out2 = self.directory/'overrun';out2.mkdir()
        with self.assertRaises(ValueError):
            C.stream_parts([sys.executable,'-B','-'],source,bad,out2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
