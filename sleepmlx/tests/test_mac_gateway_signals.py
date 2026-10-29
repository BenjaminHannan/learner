import importlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
from sleepmlx import mac_gateway as wrapper

FIXTURE = '''\
import os, time
from pathlib import Path
BIG_MAX = 0
MODEL_IDS = []
def prepare(*args): pass
def build_diary(*args): pass
class Gateway:
    def route(self, *args): pass
    def note_prefix(self, *args): pass
class Handler:
    def record(self, *args): pass
def main():
    try:
        Path(os.environ["READY"]).write_text("ready")
        while True: time.sleep(0.05)
    except KeyboardInterrupt:
        Path(os.environ["START_FLUSH"]).write_text("started")
        time.sleep(0.4)
        Path(os.environ["FLUSH"]).write_text("flushed")
'''

class Signals(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX signals required")
    def test_subprocess_inherited_ignored_sigint_and_sigterm(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp)
                (p/'gateway.py').write_text(FIXTURE)
                env = dict(os.environ, READY=str(p/'ready'), START_FLUSH=str(p/'start_flush'), FLUSH=str(p/'flush'), PYTHONPATH=str(ROOT))
                child = subprocess.Popen([sys.executable, '-m', 'sleepmlx.mac_gateway', '--gateway-file', str(p/'gateway.py')], env=env, cwd=ROOT, preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    end = time.monotonic()+5
                    while not (p/'ready').exists() and child.poll() is None and time.monotonic()<end: time.sleep(.01)
                    self.assertTrue((p/'ready').exists(), 'fixture did not start')
                    child.send_signal(sig)
                    end = time.monotonic()+5
                    while not (p/'start_flush').exists() and child.poll() is None and time.monotonic()<end: time.sleep(.01)
                    self.assertTrue((p/'start_flush').exists(), 'flush did not start')
                    child.send_signal(signal.SIGTERM if sig == signal.SIGINT else signal.SIGINT)
                    out, err = child.communicate(timeout=5)
                    self.assertEqual(child.returncode, 0, (out, err))
                    self.assertEqual((p/'flush').read_text(), 'flushed')
                finally:
                    if child.poll() is None: child.kill(); child.wait()
                    if child.stdout: child.stdout.close()
                    if child.stderr: child.stderr.close()

    def test_prior_handlers_restored_on_return_and_exception(self):
        class Gateway:
            def main(self):
                self.handlers = (signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM))
                if self.fail: raise RuntimeError('fixture failure')
        prior = (signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM))
        oldargv = sys.argv
        try:
            for fail in (False, True):
                fake = Gateway(); fake.fail = fail
                with patch.object(wrapper, 'load', return_value=fake):
                    if fail:
                        with self.assertRaises(RuntimeError): wrapper.main(['--gateway-file', '/fake'])
                    else: wrapper.main(['--gateway-file', '/fake'])
                self.assertTrue(all(callable(h) for h in fake.handlers))
                self.assertEqual((signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM)), prior)
        finally: sys.argv = oldargv

    def test_import_and_install_do_not_change_handlers(self):
        prior = (signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM))
        importlib.reload(wrapper)
        self.assertEqual((signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM)), prior)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'gateway.py'; p.write_text(FIXTURE)
            wrapper.load(p)
        self.assertEqual((signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM)), prior)

if __name__ == '__main__': unittest.main()
