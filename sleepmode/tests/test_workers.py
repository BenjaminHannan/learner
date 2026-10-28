import os
import sys
import time
import unittest

from sleepmode.workers import CommandWorker, FakeWorker
from sleepmode.tests.helpers import TmpCase

WRITER = r"""
import json, os
files = os.environ["SLEEPMODE_PRACTICE"].split(os.pathsep) if os.environ["SLEEPMODE_PRACTICE"] else []
json.dump({"quiz": 61.5, "steps": 7, "budget": os.environ["SLEEPMODE_BUDGET_S"], "nfiles": len(files),
           "workdir": os.environ["SLEEPMODE_WORKDIR"]}, open(os.environ["SLEEPMODE_OUT"], "w"))
"""
SLOW = "import time; time.sleep(60)"
# ignores SIGTERM, so only SIGKILL stops it
STUBBORN = "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"


class FakeWorkerTest(unittest.TestCase):
    def test_curve_and_stop(self):
        w = FakeWorker(hour_s=10.0)
        r1 = w.run_chunk(10.0, [], lambda: False)
        r2 = w.run_chunk(10.0, ["a"], lambda: False)
        self.assertGreater(r2.quiz, r1.quiz)
        self.assertEqual(w.calls[1]["practice_files"], ["a"])
        r3 = w.run_chunk(10.0, [], lambda: True)
        self.assertTrue(r3.interrupted)
        self.assertIsNone(r3.quiz)


class CommandWorkerTest(TmpCase):
    def worker(self, code, **kw):
        kw.setdefault("poll_s", 0.02)
        return CommandWorker([sys.executable, "-c", code], os.path.join(self.root, "wd"), **kw)

    def test_reads_output_and_env(self):
        r = self.worker(WRITER).run_chunk(30, ["x.jsonl", "y.jsonl"], lambda: False)
        self.assertEqual(r.quiz, 61.5)
        self.assertEqual(r.steps, 7)
        self.assertFalse(r.interrupted)
        self.assertEqual(r.info["nfiles"], 2)
        self.assertEqual(r.info["budget"], "30")
        self.assertEqual(r.info["returncode"], 0)

    def test_stop_sends_sigterm(self):
        t0 = time.time()
        r = self.worker(SLOW, grace_s=5).run_chunk(30, [], lambda: time.time() - t0 > 0.3)
        self.assertTrue(r.interrupted)
        self.assertIsNone(r.quiz)
        self.assertLess(time.time() - t0, 4)
        self.assertFalse(r.info["killed"])

    def test_sigkill_after_grace(self):
        t0 = time.time()
        r = self.worker(STUBBORN, grace_s=0.3).run_chunk(30, [], lambda: time.time() - t0 > 0.5)
        self.assertTrue(r.interrupted)
        self.assertTrue(r.info["killed"])

    def test_budget_kill(self):
        t0 = time.time()
        r = self.worker(SLOW, grace_s=2, slack_s=0.2).run_chunk(0.2, [], lambda: False)
        self.assertTrue(r.info["budget_exceeded"])
        self.assertLess(time.time() - t0, 5)

    def test_failing_command_reports_error(self):
        r = self.worker("import sys; sys.exit(3)").run_chunk(5, [], lambda: False)
        self.assertIn("error", r.info)
        self.assertIsNone(r.quiz)


if __name__ == "__main__":
    unittest.main()
