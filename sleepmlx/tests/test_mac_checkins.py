import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

from sleepmlx import mac_checkins

CHECKIN = '''import json, os, subprocess
class Config: pass

def lora_matches(lora, base): return True

def start_triage_server(cfg: Config):
    cmd = []
''' + mac_checkins.OLD_START + '    return cmd\n'
CONFIG = 'from dataclasses import dataclass\n@dataclass\nclass Config:\n' + mac_checkins.OLD_DAY + '\n'
SCHEDULER = 'def summary(sc):\n    lines = []\n    if True:\n' + mac_checkins.OLD_SUMMARY + '    return lines\n'

class MacCheckinsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.home = self.root / 'home'; self.home.mkdir()
        self.base = self.root / 'hf'; self.gguf = self.root / 'base.gguf'; self.gguf.write_bytes(b'base')
        self.cfg = types.SimpleNamespace(worker_cmd=[sys.executable, '-m', 'sleepmlx.worker', '--profile', 'lfm3_mps'],
            worker_env={'SLEEPMLX_MODEL_DIR': str(self.base), 'PYTHONPATH': str(Path(__file__).resolve().parents[2])},
            triage_server_cmd=['server', '-m', str(self.gguf)], triage_lora=str(self.home / 'adapter.gguf'), lora_base='LiquidAI/LFM3-1.7B')
        ns = {}; exec(mac_checkins.SELECTOR, {'os': os, 'json': json, 'subprocess': subprocess}, ns); self.select = ns['verified_triage_lora']

    def export(self, name='adapter.gguf', **changes):
        path = self.home / name; content = b'synthetic adapter'; path.write_bytes(content)
        record = {'profile': 'lfm3_mps', 'base_hf_id': 'LiquidAI/LFM3-1.7B', 'base_dir': str(self.base), 'base_gguf': str(self.gguf), 'night_id': 'synthetic', 'served': {'ok': True}, 'artifact': {'version': 1, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}}
        record.update(changes); Path(str(path) + '.json').write_text(json.dumps(record)); return path

    def make_sources(self, dest):
        dest.mkdir()
        for name, data in zip(mac_checkins.FILES, (CHECKIN, CONFIG, SCHEDULER)): (dest / name).write_text(data)

    def test_actual_selector_pending_uses_verified_previous_failed_unbound_use_base(self):
        current = self.export(served_pending={}); prev = self.export('adapter.prev.gguf')
        self.assertEqual(self.select(self.cfg), str(prev))
        Path(str(prev) + '.json').unlink()
        for record in ({'served': {'ok': False}}, {'artifact': None}, {'base_gguf': str(self.root / 'other.gguf')}):
            self.export(**record); self.assertEqual(self.select(self.cfg), '')
        self.export(); self.assertEqual(self.select(self.cfg), str(current))
        current.write_bytes(b'changed'); self.assertEqual(self.select(self.cfg), '')

    def test_cli_environment_and_canonical_output_restrictions(self):
        path = self.export(); calls = []
        def run(command, **kw):
            calls.append((command, kw)); kw['stdout'].write(json.dumps({'adapter': str(path)}).encode()); return types.SimpleNamespace(returncode=0)
        with mock.patch.object(subprocess, 'run', side_effect=run):
            self.assertEqual(self.select(self.cfg), str(path))
        command, kw = calls[0]
        self.assertEqual(command[:4], [sys.executable, '-m', 'sleepmlx.day_adapter', '--json'])
        self.assertEqual(command[command.index('--home') + 1], str(self.home))
        self.assertEqual(command[command.index('--profile') + 1], 'lfm3_mps')
        self.assertEqual(command[command.index('--base-gguf') + 1], str(self.gguf))
        self.assertEqual(command[command.index('--base-dir') + 1], str(self.base))
        self.assertEqual(kw['timeout'], 10); self.assertTrue(kw['env']['PYTHONPATH'].startswith(self.cfg.worker_env['PYTHONPATH']))
        outside = self.root / 'outside.gguf'; outside.write_bytes(b'x')
        for data in (b'{', json.dumps({'adapter': str(outside)}).encode(), b'x' * 65537):
            def fake(command, **kw): kw['stdout'].write(data); return types.SimpleNamespace(returncode=0)
            with mock.patch.object(subprocess, 'run', side_effect=fake): self.assertEqual(self.select(self.cfg), '')
        with mock.patch.object(subprocess, 'run', side_effect=subprocess.TimeoutExpired('selector', 10)): self.assertEqual(self.select(self.cfg), '')
        def failed(command, **kw): return types.SimpleNamespace(returncode=1)
        with mock.patch.object(subprocess, 'run', side_effect=failed): self.assertEqual(self.select(self.cfg), '')
        path.unlink(); path.symlink_to(outside)
        def symlink_result(command, **kw): kw['stdout'].write(json.dumps({'adapter': str(path)}).encode()); return types.SimpleNamespace(returncode=0)
        with mock.patch.object(subprocess, 'run', side_effect=symlink_result): self.assertEqual(self.select(self.cfg), '')

    def test_unknown_worker_or_ambiguous_base_never_invokes_selector(self):
        for worker in ([sys.executable, '-m', 'sleepmlx.worker', '--profile', 'other'], [sys.executable, '-m', 'other.worker', '--profile', 'lfm3_mps'], [sys.executable, '-m', 'sleepmlx.worker', '--profile', 'lfm3_mps', '--profile']):
            self.cfg.worker_cmd = worker
            with mock.patch.object(subprocess, 'run') as run: self.assertEqual(self.select(self.cfg), ''); run.assert_not_called()
        self.cfg.worker_cmd = [sys.executable, '-m', 'sleepmlx.worker', '--profile=lfm3_mps']
        self.cfg.triage_server_cmd += ['--model', 'other.gguf']
        with mock.patch.object(subprocess, 'run') as run: self.assertEqual(self.select(self.cfg), ''); run.assert_not_called()

    def test_prepare_is_read_only_install_checks_hashes_and_can_rollback(self):
        source = self.root / 'source'; self.make_sources(source); prepared = self.root / 'prepared'; backup = self.root / 'backup'
        mac_checkins.prepare(source, prepared)
        self.assertEqual((source / 'checkin.py').read_text(), CHECKIN)
        ns = {}; exec((prepared / 'checkin.py').read_text(), ns)
        self.assertEqual(ns['start_triage_server'](self.cfg), [])
        new = (prepared / 'scheduler.py').read_text(); self.assertIn('pending or failed exports are excluded', new); self.assertNotIn('not changed', new)
        self.assertIn('LFM3 (the assistant gateway)', (prepared / 'config.py').read_text())
        (source / 'config.py').write_text(CONFIG + '# changed\n')
        with self.assertRaises(ValueError): mac_checkins.install(source, prepared, backup)
        self.assertFalse(backup.exists()); self.assertEqual((source / 'checkin.py').read_text(), CHECKIN)
        (source / 'config.py').write_text(CONFIG)
        original_replace = os.replace; count = 0
        def fail_once(a, b):
            nonlocal count
            count += 1
            if count == 2: raise OSError('synthetic install failure')
            return original_replace(a, b)
        with mock.patch.object(os, 'replace', side_effect=fail_once):
            with self.assertRaises(OSError): mac_checkins.install(source, prepared, backup)
        for name, content in zip(mac_checkins.FILES, (CHECKIN, CONFIG, SCHEDULER)):
            self.assertEqual((source / name).read_text(), content); self.assertEqual((backup / name).read_text(), content)

if __name__ == '__main__': unittest.main()
