"""Regression checks for the capability256 launch guard and PC driver receipts.

Run: python3 -m unittest tests.test_cap256_launch
"""
import json
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'cap256_launch'))
import pc_driver  # noqa: E402
import pc_guard  # noqa: E402

ROOT = r'C:\Users\benja\sol-cloud-numeric-capability-v1'
VENV = r'C:\Users\benja\lis300\venv\Scripts\python.exe'
BASE = r'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
REMINDER = {'pid': 3716, 'ppid': 1480, 'name': 'pythonw.exe',
            'exe': r'C:\Users\benja\Downloads\reminder-server\venv\Scripts\pythonw.exe',
            'cmdline': r'"C:\Users\benja\Downloads\reminder-server\venv\Scripts\pythonw.exe" '
                       r'C:\Users\benja\Downloads\reminder-server\reminder_server.py'}
MANIM = {'pid': 25576, 'ppid': 25200, 'name': 'pythonw.exe',
         'exe': r'C:\Users\benja\manim-env\Scripts\pythonw.exe',
         'cmdline': r'"C:\Users\benja\manim-env\Scripts\pythonw.exe" "C:\Users\benja\OneDrive\Documents'
                    r'\Claude\Projects\Oliver Machine learning\render_server.py"'}
DWM = {'pid': 1804, 'ppid': 900, 'name': 'dwm.exe', 'exe': r'C:\Windows\System32\dwm.exe', 'cmdline': 'dwm.exe'}
SELF_LAUNCHER = {'pid': 500, 'ppid': 400, 'name': 'python.exe', 'exe': VENV,
                 'cmdline': VENV + r' -X utf8 -B C:\x\launch-cap256\pkg\abc\pc_driver.py run'}
SELF = {'pid': 501, 'ppid': 500, 'name': 'python.exe', 'exe': BASE,
        'cmdline': BASE + r' -X utf8 -B C:\x\launch-cap256\pkg\abc\pc_driver.py run'}
QUIET_GPU = [[0, 12, 2015, 16303]]


def decide(procs, apps=(), rows=QUIET_GPU):
    return pc_guard.classify([SELF_LAUNCHER, SELF, *procs], list(apps), rows, SELF['pid'], ROOT)


class GuardTests(unittest.TestCase):
    def test_reminder_server_and_manim_are_left_alone(self):
        d = decide([REMINDER, MANIM, DWM], apps=[{'pid': 1804, 'used_memory': '[N/A]'}])
        self.assertTrue(d['ok'], d)
        self.assertEqual({p['pid'] for p in d['allowed_python']}, {3716, 25576})

    def test_unrelated_python_on_gpu_is_allowed_but_recorded(self):
        d = decide([MANIM], apps=[{'pid': 25576, 'used_memory': '[N/A]'}])
        self.assertTrue(d['ok'], d)
        self.assertEqual(d['gpu_clients'][0]['pid'], 25576)

    def test_bracketed_na_desktop_clients_do_not_block(self):
        # The r4 failure: driver 591.86 prints "[N/A]", which the old gate rejected.
        apps = [{'pid': 1804, 'used_memory': '[N/A]'}, {'pid': 777, 'used_memory': '[N/A]'}]
        d = decide([DWM], apps=apps)
        self.assertTrue(d['ok'], d)
        self.assertEqual(len(d['gpu_clients']), 2)

    def test_existing_capability_runner_blocks(self):
        runner = {'pid': 9000, 'ppid': 8999, 'name': 'python.exe', 'exe': BASE,
                  'cmdline': BASE + ' -X utf8 -B ' + ROOT + r'\scripts\sol_cloud_capability256_v1.py --phase train'}
        d = decide([runner])
        self.assertFalse(d['ok'])
        self.assertIn('duplicate', d['block'][0]['reason'])

    def test_premonition_gpu_job_blocks_even_with_stdin_script(self):
        launcher = {'pid': 18832, 'ppid': 27828, 'name': 'python.exe', 'exe': VENV, 'cmdline': VENV + ' -X utf8 -B -'}
        child = {'pid': 9700, 'ppid': 18832, 'name': 'python.exe', 'exe': BASE, 'cmdline': BASE + ' -X utf8 -B -'}
        d = decide([launcher, child], apps=[{'pid': 9700, 'used_memory': '[N/A]'}])
        self.assertFalse(d['ok'])
        self.assertTrue(any(b.get('pid') == 9700 and 'Premonition' in b['reason'] for b in d['block']))

    def test_premonition_cpu_python_waits_instead_of_blocking(self):
        probe = {'pid': 18832, 'ppid': 27828, 'name': 'python.exe', 'exe': VENV, 'cmdline': VENV + ' -X utf8 -B -'}
        d = decide([probe])
        self.assertFalse(d['ok'])
        self.assertEqual(d['block'], [])
        self.assertEqual(d['wait'][0]['pid'], 18832)

    def test_model_server_on_gpu_blocks(self):
        llama = {'pid': 4242, 'ppid': 1, 'name': 'llama-server.exe', 'exe': r'C:\llama\llama-server.exe',
                 'cmdline': r'C:\llama\llama-server.exe -m qwen.gguf'}
        d = decide([llama], apps=[{'pid': 4242, 'used_memory': '[N/A]'}])
        self.assertFalse(d['ok'])

    def test_high_gpu_memory_blocks(self):
        d = decide([], rows=[[0, 90, 14000, 16303]])
        self.assertFalse(d['ok'])
        self.assertIn('GPU memory', d['block'][0]['reason'])

    def test_waiting_launcher_driver_does_not_block_lock_holder(self):
        other = {'pid': 600, 'ppid': 1, 'name': 'python.exe', 'exe': BASE,
                 'cmdline': BASE + r' C:\x\launch-cap256\pkg\def\pc_driver.py run'}
        d = decide([other])
        self.assertTrue(d['ok'], d)


FAKE_RUNNER = textwrap.dedent('''
    import json, os, pathlib, sys, time
    run = pathlib.Path(sys.argv[1]); run.mkdir(parents=True)
    print('runner says hello'); print('some warning', file=sys.stderr); sys.stdout.flush()
    n = int(sys.argv[2])
    with (run / 'TRAIN-RAW.jsonl').open('a') as f:
        for i in range(1, n + 1):
            f.write(json.dumps({'update': i, 'numeric_CE': 1.5, 'job': os.environ['JOB']}) + '\\n'); f.flush()
    if n == 5120:
        (run / 'final-resume.pt').write_bytes(b'ckpt')
        (run / 'CLOSED.json').write_text(json.dumps({'closed': True, 'optimizer_updates': n}) + '\\n')
        sys.exit(0)
    (run / 'FAILED.json').write_text(json.dumps({'error': 'boom', 'optimizer_updates': n}) + '\\n')
    raise SystemExit('Traceback: boom at update %d' % n)
''')


class FakeDriver(pc_driver.Driver):
    updates = {}

    def probe_processes(self):
        return [REMINDER, MANIM]

    def probe_gpu(self):
        return QUIET_GPU, [{'pid': 1804, 'used_memory': '[N/A]'}]

    def gpu_snapshot(self):
        return 'fake'

    def verify_package(self):
        return {}, {'total_bytes': 1}

    def verify_closure(self, plan):
        return []

    def runner_argv(self, seed, arm, inventory_path, inventory_sha):
        run_dir = self.root / pc_driver.OWN_REL / 'ns' / ('seed%d' % seed) / arm
        return [sys.executable, str(self.root / 'fake_runner.py'), str(run_dir), str(self.updates[(seed, arm)])]


class DriverTests(unittest.TestCase):
    def setUp(self):
        pc_driver.FIRST_POLL_SECONDS = pc_driver.TRAIN_POLL_SECONDS = 0.05
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'fake_runner.py').write_text(FAKE_RUNNER)
        self.request = {'root': str(self.root), 'batch_id': 'b1', 'commit': 'c' * 40,
                        'queued_utc': pc_driver.iso(), 'arms': [[0, 'loop'], [0, 'plain'], [1, 'loop']],
                        'spec': {'run_namespace': 'ns', 'files': []}}

    def tearDown(self):
        self.tmp.cleanup()

    def jobs(self):
        return self.root / 'launch-cap256' / 'jobs'

    def test_success_then_failure_keeps_full_receipts_and_stops_batch(self):
        FakeDriver.updates = {(0, 'loop'): 5120, (0, 'plain'): 7, (1, 'loop'): 5120}
        batch = FakeDriver(self.request).run()
        self.assertEqual([j['status'] for j in batch['jobs']], ['completed', 'failed'])
        self.assertEqual(batch['skipped_arms'], [[1, 'loop']])
        ok = self.jobs() / 'cap256-s0-loop-b1'
        first = json.loads((ok / 'FIRST-UPDATE.json').read_text())
        self.assertEqual(first['first_record_update'], 1)
        self.assertEqual(first['first_record_job'], 'cap256-s0-loop-b1')
        self.assertGreaterEqual(first['queue_to_first_update_seconds'], 0)
        done = json.loads((ok / 'EXIT.json').read_text())
        self.assertEqual(done['returncode'], 0)
        self.assertEqual(done['optimizer_updates_counted_from_TRAIN_RAW'], 5120)
        self.assertTrue(done['checkpoint']['path'].endswith('final-resume.pt'))
        self.assertIn('runner says hello', done['stdout']['tail'])
        bad = self.jobs() / 'cap256-s0-plain-b1'
        failed = json.loads((bad / 'EXIT.json').read_text())
        self.assertNotEqual(failed['returncode'], 0)
        self.assertIn('boom at update 7', failed['stderr']['tail'])
        self.assertEqual(failed['FAILED.json']['error'], 'boom')
        self.assertEqual(failed['optimizer_updates_counted_from_TRAIN_RAW'], 7)
        state = json.loads((bad / 'STATE.json').read_text())
        self.assertEqual(state['status'], 'failed')
        self.assertIsNotNone(state['idle_seconds_since_previous_arm'])
        self.assertFalse((self.root / 'launch-cap256' / 'LOCK.json').exists())

    def test_existing_arm_output_is_never_overwritten(self):
        FakeDriver.updates = {(0, 'loop'): 5120}
        existing = self.root / pc_driver.OWN_REL / 'ns' / 'seed0' / 'loop'
        existing.mkdir(parents=True)
        (existing / 'keep.txt').write_text('evidence')
        self.request['arms'] = [[0, 'loop']]
        batch = FakeDriver(self.request).run()
        self.assertEqual(batch['jobs'][0]['status'], 'failed')
        self.assertEqual((existing / 'keep.txt').read_text(), 'evidence')
        state = json.loads((self.jobs() / 'cap256-s0-loop-b1' / 'STATE.json').read_text())
        self.assertIn('refusing to overwrite', state['error'])
        self.assertFalse(state['runner_invoked'])

    def test_guard_block_records_the_offending_process(self):
        class Busy(FakeDriver):
            def probe_processes(self):
                return [REMINDER, {'pid': 9000, 'ppid': 1, 'name': 'python.exe', 'exe': BASE,
                                   'cmdline': 'python sol_cloud_capability256_v1.py --phase train'}]
        self.request['arms'] = [[0, 'loop']]
        batch = Busy(self.request).run()
        self.assertEqual(batch['jobs'][0]['status'], 'failed')
        guard = json.loads((self.jobs() / 'cap256-s0-loop-b1' / 'GUARD.json').read_text())
        self.assertEqual(guard['attempts'][-1]['block'][0]['pid'], 9000)


if __name__ == '__main__':
    unittest.main()
