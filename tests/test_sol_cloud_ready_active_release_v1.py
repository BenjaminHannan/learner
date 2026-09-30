"""Pinned r2 package regression; hashes/syntax only, no runner execution."""
import ast
import json
from pathlib import Path
import tempfile
import unittest

from scripts.sol_cloud_queue_recovery_v1 import packaged_runtime_pins
from scripts.sol_cloud_ready_jobs_v1 import (
    clean_tree_smoke, git_provider, runtime_manifest, sha_bytes, stage_package,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1'
COMMIT = '467ff3381a39523f28e79401b08aa321a19d842c'
SPEC = BASE / 'mac-launch-v2/SPEC-s0-loop-r2.json'


class ActiveReleaseFixtures(unittest.TestCase):
    def test_actual_r2_clean_package_physical_dependency_closure(self):
        self.assertEqual(sha_bytes(SPEC.read_bytes()),
                         '5d6ddcbeb44f9f9aba27547613d85205d245f5e56c302432e1eba979106dfb20')
        spec = json.loads(SPEC.read_text())
        # Only published TRAIN runtime closure. Never hash/read blind panels.
        self.assertFalse(any('panel' in p['path'].lower() or 'uncle-questions' in p['path'].lower()
                             for p in spec['files']))
        plan, seal, release = [json.loads((ROOT/spec[k]['path']).read_text())
                               for k in ('plan', 'seal', 'release')]
        required = packaged_runtime_pins(spec, plan, seal, release)
        manifest = runtime_manifest(spec['job'], COMMIT, spec['files'],
                                   'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v2',
                                   required=required)
        with tempfile.TemporaryDirectory() as temporary:
            staged = stage_package(manifest, temporary, git_provider(ROOT))
            smoke = clean_tree_smoke(manifest, staged)
        self.assertEqual(smoke['physical_files_read'], len(spec['files']))
        self.assertEqual(smoke['optimizer_updates'], 0)
        self.assertEqual(smoke['source_syntax']['executed_bootstraps'], 0)

    def test_generated_PC_bootstrap_pure_imports_and_native_syntax(self):
        path = BASE / 'mac-launch-v2/MAC-LAUNCH-v2.py'
        relative = path.relative_to(ROOT).as_posix()
        source = git_provider(ROOT)(COMMIT, relative)
        self.assertEqual(sha_bytes(source), 'cc9a7e95cb1d33ec84b1f654ee38ca043deed1d8d471ec3ec99112b705a1e32b')
        tree = ast.parse(source)
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'pc_source')
        allowed_nodes = (ast.FunctionDef, ast.arguments, ast.arg, ast.Expr,
                         ast.Constant, ast.Return, ast.Call, ast.Attribute, ast.Name, ast.Load)
        for node in ast.walk(function):
            self.assertIsInstance(node, allowed_nodes)
            if isinstance(node, ast.Call):
                self.assertTrue(isinstance(node.func, ast.Name) and node.func.id == 'repr'
                                or isinstance(node.func, ast.Attribute) and node.func.attr == 'replace')
        # Extract pure string generator and its literal constant only. No relay
        # main, native host gates, package writes, model or subprocess execution.
        pcroot = next(n.value.value for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'PCROOT' for t in n.targets))
        namespace = {'PCROOT': pcroot}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        generated = namespace['pc_source'](json.loads(SPEC.read_text()), [], {})
        parsed = ast.parse(generated, feature_version=(3, 10))
        imports = [n for n in parsed.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        allowed_imports = {'base64','ctypes','datetime','gzip','hashlib','importlib.util',
                           'json','os','pathlib','platform','shutil','subprocess','sys','time'}
        for node in imports:
            self.assertIsInstance(node, ast.Import)
            self.assertTrue(all(alias.name in allowed_imports for alias in node.names))
        pure = {}
        exec(compile(ast.Module(body=imports, type_ignores=[]), 'pure-PC-imports', 'exec'), pure)
        self.assertTrue(all(name in pure for name in ('gzip','hashlib','json','os','pathlib','subprocess','time')))
        for script in ('sol_cloud_ready_jobs_v1.py', 'sol_cloud_queue_recovery_v1.py'):
            ast.parse((ROOT/'scripts'/script).read_text(), feature_version=(3, 9))


if __name__ == '__main__':
    unittest.main()
