"""Recovery dry tests. No production process, service, model, or marker touched."""
import importlib.util
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).with_name("paused-learning-run.py")
spec = importlib.util.spec_from_file_location("paused_learning_run", MODULE)
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


class DryRecovery(unittest.TestCase):
    def test_marker_is_exclusive_and_only_exact_owned_content_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "pause"
            run.claim_marker(p, "foreign")
            with self.assertRaises(FileExistsError): run.claim_marker(p, "ours")
            with self.assertRaises(RuntimeError): run.release_marker(p, "ours")
            self.assertEqual(p.read_text(), "foreign")
            self.assertTrue(run.release_marker(p, "foreign"))
            self.assertFalse(p.exists())

    def test_durable_obligation_cannot_replace_an_existing_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "record.json"
            run.durable(p, {"first": True}, exclusive=True)
            with self.assertRaises(FileExistsError): run.durable(p, {"second": True}, exclusive=True)
            self.assertEqual(json.loads(p.read_text()), {"first": True})

    def test_pid_identity_mismatch_never_terminates_a_different_process(self):
        child = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"], start_new_session=True)
        try:
            item = run.identity(child.pid); item["created"] += 1
            run.stop_owned(item)
            self.assertIsNone(child.poll())
        finally:
            child.terminate(); child.wait(timeout=5)

    def test_owned_termination_preserves_signal_exit_status(self):
        child = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"], start_new_session=True)
        status = run.stop_owned(run.identity(child.pid))
        self.assertEqual(status, -signal.SIGTERM)
        child.returncode = int(status)
        self.assertEqual(child.wait(), -signal.SIGTERM)

    def test_unknown_active_diagnostic_blocks_restoration_and_preserves_pause(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); marker = root / "pause"
            run.claim_marker(marker, "ours")
            control = root / "control.json"; run.durable(control, {"restore_requested": True})
            obligation = root / "obligation.json"
            run.durable(obligation, {"wrapper": run.identity(os.getpid()), "control": str(control),
                                    "restoration_deadline": 9999999999, "pause_marker": str(marker),
                                    "marker_content": "ours", "output": "our-output"})
            with patch.object(run, "diagnostic_jobs", side_effect=lambda output=None: [] if output else [{"pid": 123}]), \
                 patch.object(run.subprocess, "Popen", side_effect=AssertionError("must not launch under active diagnostic")):
                with self.assertRaisesRegex(RuntimeError, "another HF diagnostic"):
                    run.restore(obligation)
            self.assertEqual(marker.read_text(), "ours")
            result = json.loads((root / "obligation-restoration.json").read_text())
            self.assertEqual(result["status"], "restore-failed-explicit-obligation")

    def test_detached_restorer_handles_wrapper_death_and_stops_only_owned_test_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"], start_new_session=True)
            unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"], start_new_session=True)
            try:
                own = run.identity(owned.pid)
                marker = root / "pause"; run.claim_marker(marker, "our unique reservation")
                control = root / "control.json"; run.durable(control, {"restore_requested": False, "diagnostic": own})
                wrapper = run.identity(os.getpid()); wrapper["created"] += 1 # simulate exited original wrapper
                obligation = root / "obligation.json"
                run.durable(obligation, {"wrapper": wrapper, "control": str(control), "output": "unique-test-output",
                                        "restoration_deadline": 9999999999, "pause_marker": str(marker),
                                        "marker_content": "our unique reservation"}, exclusive=True)
                script = '''
import importlib.util,json,sys
spec=importlib.util.spec_from_file_location('recovery',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
item=json.loads(sys.argv[3]);other=int(sys.argv[4])
m.diagnostic_jobs=lambda output=None: [item] if m.matching(item) is not None else []
m.health=lambda: True
def verified(obligation):
 assert m.matching(item) is None,'restoring while diagnostic is live'
 assert m.psutil.pid_exists(other),'unrelated process was terminated'
 return {'pid':123,'dry_test':True}
m.verify_restored=verified
m.restore(sys.argv[2])
'''
                restorer = subprocess.Popen([sys.executable, "-c", script, str(MODULE), str(obligation), json.dumps(own), str(unrelated.pid)],
                                            start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                out, err = restorer.communicate(timeout=20)
                self.assertEqual(restorer.returncode, 0, out + err)
                owned.wait(timeout=5)
                self.assertIsNone(unrelated.poll())
                self.assertFalse(marker.exists())
                result = json.loads((root / "obligation-restoration.json").read_text())
                self.assertEqual(result["status"], "restored")
                self.assertTrue((root / "obligation-restorer-ready.json").exists())
            finally:
                for child in (owned, unrelated):
                    if child.poll() is None: child.terminate()
                    child.wait(timeout=5)


if __name__ == "__main__": unittest.main()
