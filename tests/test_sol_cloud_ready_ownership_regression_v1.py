"""Reported PC-process/path regression, isolated from native launch or SSH.

The successor predicate below is a contract fixture for the execution owner,
not a replacement bootstrap. Commands are synthetic; app identities and PIDs
come from Derek's read-only diagnosis. Actual resource gates remain unchanged.
"""
import ast
import copy
from pathlib import Path, PureWindowsPath
import tempfile
import unittest

from scripts.sol_cloud_ready_jobs_v1 import git_provider, sha_bytes


ROOT = Path(__file__).resolve().parents[1]
RELAY = 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v2/MAC-LAUNCH-v2.py'
PIN = '467ff3381a39523f28e79401b08aa321a19d842c'


def process_loop():
    source = git_provider(ROOT)(PIN, RELAY)
    assert sha_bytes(source) == 'cc9a7e95cb1d33ec84b1f654ee38ca043deed1d8d471ec3ec99112b705a1e32b'
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'pc_source')
    # Only the byte-pinned pure string generator runs; generated host code never
    # runs. Extract its metadata-classification loop without subprocess calls.
    namespace = {'PCROOT': 'C:/Users/benja/sol-cloud-numeric-capability-v1'}
    exec(compile(ast.Module(body=[function], type_ignores=[]), 'pinned-generator', 'exec'), namespace)
    generated = ast.parse(namespace['pc_source']({}, [], {}))
    loop = next(n for n in ast.walk(generated) if isinstance(n, ast.For)
                and isinstance(n.iter, ast.Name) and n.iter.id == 'py')
    return loop


def classify(loop, processes):
    scope = {'py': processes, 'root': PureWindowsPath('C:/Users/benja/sol-cloud-numeric-capability-v1'),
             'lineage': {500, 400}, 'py_summary': [], 'project_conflicts': [],
             'pathlib': __import__('pathlib'), 'sys': __import__('sys')}
    exec(compile(ast.Module(body=[loop], type_ignores=[]), 'isolated-process-metadata', 'exec'), scope)
    return scope['project_conflicts'], scope['py_summary']


def desired_scope_fixture(loop):
    """A foreign positive project match conflicts; an unrelated Python does not.

    This modifies a copied AST solely inside the test, never the relay on disk.
    The execution owner applies its independently reviewed implementation.
    """
    loop = copy.deepcopy(loop)
    condition = next(n for n in loop.body if isinstance(n, ast.If)
                     and isinstance(n.test, ast.BoolOp))
    assert isinstance(condition.test.op, ast.Or)
    condition.test.op = ast.And()
    return ast.fix_missing_locations(loop)


class OwnershipRegression(unittest.TestCase):
    def setUp(self):
        self.loop = process_loop()
        self.background = [
            {'ProcessId':3716, 'ParentProcessId':100, 'Name':'pythonw.exe',
             'ExecutablePath':r'C:\fixture\reminder-server\pythonw.exe',
             'CommandLine':r'C:\fixture\reminder-server\pythonw.exe server.py'},
            {'ProcessId':25576, 'ParentProcessId':101, 'Name':'pythonw.exe',
             'ExecutablePath':r'C:\fixture\manim-env\pythonw.exe',
             'CommandLine':r'C:\fixture\manim-env\pythonw.exe helper.py'}]

    def test_exact_r2_reproduces_unrelated_background_rejection(self):
        conflicts, summary = classify(self.loop, self.background)
        self.assertEqual({p['pid'] for p in conflicts}, {3716, 25576})
        self.assertTrue(all(p['owned_command_match'] is False for p in summary))

    def test_successor_contract_retains_legitimate_background_processes(self):
        conflicts, summary = classify(desired_scope_fixture(self.loop), self.background)
        self.assertEqual(conflicts, [])
        self.assertEqual({p['pid'] for p in summary}, {3716, 25576})

    def test_successor_contract_blocks_foreign_owned_project_runner(self):
        owned = {'ProcessId':900, 'ParentProcessId':100, 'Name':'python.exe',
                 'ExecutablePath':r'C:\fixture\python.exe',
                 'CommandLine':r'python C:\Users\benja\sol-cloud-numeric-capability-v1\scripts\sol_cloud_capability256_v1.py --phase train'}
        conflicts, summary = classify(desired_scope_fixture(self.loop), self.background+[owned])
        self.assertEqual([p['pid'] for p in conflicts], [900])
        self.assertTrue(summary[-1]['owned_command_match'])
        owned['ProcessId'] = 500  # current bootstrap lineage is not a competing job
        self.assertEqual(classify(desired_scope_fixture(self.loop), [owned])[0], [])

    def test_mac_probe_execution_path_groups_string_before_path_join(self):
        with tempfile.TemporaryDirectory() as temporary:
            W = Path(temporary)
            job = 'sol-cloud-read-only-fixture'
            with self.assertRaises(TypeError):
                _ = W / 'artifacts/relay/execution-' + job
            correct = W / ('artifacts/relay/execution-' + job)
            self.assertEqual(correct.relative_to(W).as_posix(),
                             'artifacts/relay/execution-sol-cloud-read-only-fixture')


if __name__ == '__main__':
    unittest.main()
