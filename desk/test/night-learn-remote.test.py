import datetime
import importlib.util
import json
import tempfile
import unittest
import subprocess
import sys
from unittest import mock
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'src' / 'night-learn-remote'
spec = importlib.util.spec_from_file_location('hands_remote_runner', root / 'remote_runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class GateTests(unittest.TestCase):
    def test_synthetic_gate_allows_any_hour(self):
        runner.gate_for(True)()

    def test_real_gate_allows_only_night_with_idle_mac(self):
        night = datetime.datetime(2026, 11, 7, 3, 0)
        morning = datetime.datetime(2026, 11, 7, 9, 0)
        self.assertEqual(runner.real_gate(now=night, idle=1300), 1300)
        with self.assertRaises(RuntimeError):
            runner.real_gate(now=morning, idle=1300)
        with self.assertRaises(RuntimeError):
            runner.real_gate(now=night, idle=1199)

    def test_real_gate_honours_stop_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            stop = Path(tmp) / 'STOP-TRAINING'
            stop.write_text('stop')
            with self.assertRaises(RuntimeError):
                runner.real_gate(now=datetime.datetime(2026, 11, 7, 3, 0), idle=1300,
                                 stop_file=stop)

    def test_gate_for_returns_the_production_rule(self):
        self.assertIs(runner.gate_for(False), runner.real_gate)
        runner.gate_for(True)()


class SafetyTests(unittest.TestCase):
    def test_gate_rejects_nonfinite_idle_and_window_edges(self):
        for hour, idle in [(0, 1300), (7, 1300), (3, float('nan')), (3, float('inf'))]:
            with self.subTest(hour=hour, idle=idle), self.assertRaises(RuntimeError):
                runner.real_gate(now=datetime.datetime(2026, 11, 7, hour), idle=idle)
        self.assertEqual(runner.real_gate(now=datetime.datetime(2026, 11, 7, 1), idle=1200), 1200)

    def test_synthetic_still_obeys_stop_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            stop = Path(tmp) / 'STOP'
            stop.touch()
            with mock.patch.object(runner, 'STOP_FILE', stop), self.assertRaises(RuntimeError):
                runner.gate_for(True)()

    def test_powershell_is_utf16le_and_python_uses_stdin(self):
        with mock.patch.object(runner, 'command_run') as command:
            runner.ssh_python('benspc-lan', 'print(42)')
        arguments = command.call_args
        self.assertEqual(arguments.kwargs['source'], 'print(42)')
        import base64
        encoded = arguments.args[0][-1].split()[-1]
        decoded = base64.b64decode(encoded).decode('utf-16-le')
        self.assertIn(runner.PC_PYTHON, decoded)
        self.assertIn(' -; exit $LASTEXITCODE', decoded)

    def test_pending_reboot_flag_is_warning_not_cuda_admission(self):
        status = {'sharedLeaseRootExists': True, 'freeBytes': 10 * 1024 ** 3,
                  'rebootRequired': True}
        with mock.patch.object(runner, 'ssh_python', return_value=mock.Mock(stdout=json.dumps(status))):
            self.assertEqual(runner.pc_preflight('host'), status)

    def test_transport_failure_becomes_recoverable_unavailability(self):
        with mock.patch.object(runner.subprocess, 'run', side_effect=subprocess.TimeoutExpired('ssh', 1)):
            with self.assertRaises(runner.RemoteUnavailable):
                runner.command_run(['ssh'], timeout=1)

    def test_return_hash_mismatch_is_rejected(self):
        def download(host, remote, local):
            Path(local).write_bytes(b'tampered')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(runner, 'scp_download', download):
            with self.assertRaises(runner.RemoteUnavailable):
                runner.download_outputs('host', 'remote', Path(tmp) / 'out',
                                        {'modelSha256': {'old': '0' * 64}})

    def test_benchmark_zero_does_no_cpu_work(self):
        self.assertIsNone(runner.cpu_benchmark(None, None, None, 0))

    def test_real_gate_is_checked_even_when_worker_is_silent(self):
        process = mock.Mock(stdout=[], returncode=0)
        process.poll.return_value = None
        messages = mock.Mock()
        messages.get.side_effect = runner.queue.Empty
        gate = mock.Mock(side_effect=[None, RuntimeError('Mac became active')])
        with mock.patch.object(runner.subprocess, 'Popen', return_value=process), \
             mock.patch.object(runner.queue, 'Queue', return_value=messages), \
             mock.patch.object(runner, 'ssh_python'), \
             mock.patch.object(runner, 'cancel_supervisor') as cancel, \
             mock.patch.object(runner, 'audit'):
            with self.assertRaisesRegex(RuntimeError, 'Mac became active'):
                runner.stream_remote('host', 'private-job', timeout=10, gpu_wait=0,
                                     gate=gate, logger=lambda _: None)
        self.assertEqual(gate.call_count, 2)
        cancel.assert_called_once_with('host', 'private-job')
        process.kill.assert_called_once()


class SupervisorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        module_spec = importlib.util.spec_from_file_location('night_supervisor', root / 'supervise_remote.py')
        cls.supervisor = importlib.util.module_from_spec(module_spec)
        with mock.patch.dict(sys.modules, {'gpu_gate': mock.Mock()}):
            module_spec.loader.exec_module(cls.supervisor)

    def test_expired_missing_corrupt_or_cancelled_permit_is_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.assertFalse(self.supervisor.authorized(directory, now=100))
            for value in ['broken', '{"expiresAt":99}', '{"expiresAt":1000}']:
                (directory / 'permit.json').write_text(value)
                self.assertFalse(self.supervisor.authorized(directory, now=100))
            (directory / 'permit.json').write_text('{"expiresAt":160}')
            self.assertTrue(self.supervisor.authorized(directory, now=100))
            (directory / 'cancel').touch()
            self.assertFalse(self.supervisor.authorized(directory, now=100))

    def test_cleanup_cannot_target_shared_lease_or_foreign_directory(self):
        for directory in [self.supervisor.LEASE_ROOT, self.supervisor.PC_ROOT, Path('/tmp/foreign')]:
            with self.subTest(directory=directory), self.assertRaises(RuntimeError):
                self.supervisor.remove_job(directory)

    def test_busy_lease_never_starts_worker_and_cleans_own_job(self):
        lease = mock.Mock()
        lease.__enter__ = mock.Mock(side_effect=FileExistsError('other owner'))
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'hands-unit-busy'
            directory.mkdir()
            (directory / 'permit.json').write_text('{"expiresAt":160}')
            (directory / 'upload-ready').touch()
            with mock.patch.object(self.supervisor, 'PC_ROOT', Path(tmp)), \
                 mock.patch.object(self.supervisor, 'authorized', return_value=True), \
                 mock.patch.object(self.supervisor.gpu_gate, 'Lease', return_value=lease), \
                 mock.patch.object(self.supervisor.subprocess, 'Popen') as start, \
                 mock.patch.object(self.supervisor, 'wait_for_client'), \
                 mock.patch.object(self.supervisor, 'emit'):
                self.assertEqual(self.supervisor.supervise(directory, gpu_wait=0, timeout=1), 3)
            start.assert_not_called()
            self.assertFalse(directory.exists())


class FallbackTests(unittest.TestCase):
    def dataset(self, tmp, synthetic=True):
        path = Path(tmp) / 'dataset.json'
        path.write_text(json.dumps({'synthetic': synthetic, 'examples': []}))
        return path

    def test_remote_unavailable_falls_back_and_logs_reason(self):
        calls = []

        def remote(dataset, output, **kwargs):
            calls.append(('remote', kwargs['synthetic']))
            raise runner.RemoteUnavailable('pc down for test')

        def local(dataset, output):
            calls.append(('local',))
            return {'status': 'quarantine; not promoted'}

        with tempfile.TemporaryDirectory() as tmp:
            dataset = self.dataset(tmp)
            original = runner.FALLBACK_LOG
            log_path = Path(tmp) / 'fallback.log'
            runner.FALLBACK_LOG = log_path
            try:
                result = runner.run(dataset, Path(tmp) / 'out', remote_fn=remote,
                                    local_fn=local, logger=lambda _: None)
            finally:
                runner.FALLBACK_LOG = original
            self.assertEqual(result['trainingBackend'], 'mac-cpu-fallback')
            self.assertEqual(result['fallbackReason'], 'pc down for test')
            self.assertEqual(calls, [('remote', True), ('local',)])
            entry = json.loads(log_path.read_text().splitlines()[0])
            self.assertIn('pc down for test', entry['reason'])
            self.assertEqual(entry['dataset'], str(dataset))

    def test_remote_success_does_not_fall_back(self):
        calls = []

        def remote(dataset, output, **kwargs):
            calls.append('remote')
            return {'status': 'quarantine; not promoted'}

        def local(dataset, output):
            calls.append('local')
            return {'status': 'unexpected'}

        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(self.dataset(tmp), Path(tmp) / 'out', remote_fn=remote,
                                local_fn=local, logger=lambda _: None)
            self.assertEqual(result['trainingBackend'], 'benspc-gpu')
            self.assertFalse(result['remote']['fallback'])
            self.assertEqual(calls, ['remote'])

    def test_bad_dataset_never_falls_back(self):
        calls = []

        def remote(*args, **kwargs):
            calls.append('remote')
            raise AssertionError('must not reach remote')

        def local(*args, **kwargs):
            calls.append('local')
            raise AssertionError('must not reach local')

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(runner.InputError):
                runner.run(Path(tmp) / 'missing.json', Path(tmp) / 'out',
                           remote_fn=remote, local_fn=local, logger=lambda _: None)
            self.assertEqual(calls, [])

    def test_cuda_failure_never_falls_back(self):
        calls = []

        def remote(*args, **kwargs):
            calls.append('remote')
            raise runner.CudaFailure('sm_120 kernel failed')

        def local(*args, **kwargs):
            calls.append('local')

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(runner.CudaFailure):
                runner.run(self.dataset(tmp), Path(tmp) / 'out', remote_fn=remote,
                           local_fn=local, logger=lambda _: None)
            self.assertEqual(calls, ['remote'])

    def test_no_fallback_flag_reraises(self):
        calls = []

        def remote(*args, **kwargs):
            calls.append('remote')
            raise runner.RemoteUnavailable('busy')

        def local(*args, **kwargs):
            calls.append('local')

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(runner.RemoteUnavailable):
                runner.run(self.dataset(tmp), Path(tmp) / 'out', remote_fn=remote,
                           local_fn=local, no_fallback=True, logger=lambda _: None)
            self.assertEqual(calls, ['remote'])

    def test_busy_and_rebooting_reasons_reach_local_fallback(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(runner, 'FALLBACK_LOG', Path(tmp) / 'log'):
            for reason in ['GPU busy; lease owned', 'PC unreachable during reboot']:
                def remote(*args, **kwargs):
                    raise runner.RemoteUnavailable(reason)
                result = runner.run(self.dataset(tmp), Path(tmp) / 'out', remote_fn=remote,
                                    local_fn=lambda *args: {}, logger=lambda _: None)
                self.assertEqual(result['fallbackReason'], reason)

    def test_real_recordings_cannot_be_relabelled_synthetic_by_cli(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(runner.InputError):
            runner.run(self.dataset(tmp, synthetic=False), tmp, synthetic=True)

    def test_real_gate_applies_before_remote_or_local(self):
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(runner, 'real_gate', side_effect=RuntimeError('daytime')), \
             mock.patch.object(runner, 'run_remote') as remote, \
             mock.patch.object(runner, 'run_local') as local:
            with self.assertRaises(RuntimeError):
                runner.run(self.dataset(tmp, synthetic=False), tmp)
            remote.assert_not_called()
            local.assert_not_called()

    def test_cleanup_failure_is_not_silently_fallback_eligible(self):
        def remote(*args, **kwargs):
            raise RuntimeError('PC cleanup unconfirmed')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(runner, 'run_local') as local:
            with self.assertRaises(RuntimeError):
                runner.run(self.dataset(tmp), tmp, remote_fn=remote)
            local.assert_not_called()

    def test_bad_frame_is_an_input_error_before_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / 'dataset.json'
            dataset.write_text(json.dumps({'synthetic': True, 'examples': [
                {'id': 'a', 'frame': str(Path(tmp) / 'missing.png')}]}))
            with self.assertRaises(runner.InputError):
                runner.pack_job(dataset, tmp, 'hands-test', steps=1, batch_size=1, lr=0.001)


if __name__ == '__main__':
    unittest.main()
