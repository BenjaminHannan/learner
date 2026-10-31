import json
import math
import os
import sys
import threading
import time
import unittest
from unittest.mock import patch

from sleepmode import scheduler as sched
from sleepmode.checkin import Item
from sleepmode.scheduler import Scheduler
from sleepmode.state import State
from sleepmode.tests.helpers import TmpCase, make_cfg
from sleepmode.workers import ChunkResult, CommandWorker, FakeWorker

FAST = lambda h: 50 + 30 * (1 - math.exp(-h / 0.5))


class Scanner:
    name = "fake"

    def __init__(self):
        self.calls = 0

    def scan(self, cfg):
        self.calls += 1
        return []


class Practice:
    def __init__(self, result="ok"):
        self.calls = []
        self.result = result

    def __call__(self, budget_s):
        self.calls.append(budget_s)
        if self.result is None:
            return None
        return {"kind": "spreadsheet", "n": 5, "pass1": 0.5, "files": ["/x/sft%d.jsonl" % len(self.calls)]}


class SchedTest(TmpCase):
    def setUp(self):
        super().setUp()
        self.state = State(self.cfg)
        self.scanner = Scanner()
        self.worker = FakeWorker(FAST, hour_s=self.cfg.hour_s, delay_s=0.01)
        self.practice = Practice()
        self.sc = self._make()

    def _make(self, **kw):
        return Scheduler(self.cfg, kw.get("worker", self.worker), kw.get("practice", self.practice),
                         scanners=[self.scanner])

    def go(self):
        t = threading.Thread(target=self.sc.run, daemon=True)
        t.start()
        return t

    def wait_for(self, cond, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            if cond():
                return True
            time.sleep(0.01)
        return False

    def test_chunk_that_crosses_deadline_is_not_started(self):
        self.sc.clock = lambda: 1000
        self.sc.wake_at_ms = 1900 * 1000
        self.sc.sleep_chunk(900)
        self.assertEqual(self.sc.chunks, 0)
        self.assertEqual(self.sc.stop_reason, "insufficient time before wake deadline")

    def test_running_chunk_observes_deadline(self):
        now = [1000]
        self.sc.clock = lambda: now[0]
        self.sc.wake_at_ms = 2400 * 1000
        class Worker:
            def run_chunk(worker, budget, files, stop):
                self.assertFalse(stop())
                now[0] = 2400
                self.assertTrue(stop())
                return ChunkResult(None, 1000, 0, True, {})
        self.sc.worker = Worker()
        self.sc.sleep_chunk(900)
        self.assertEqual(self.sc.stop_reason, "wake deadline")
        self.assertEqual(self.sc.quizzes, [])

    def test_general_drop_switches_to_practice_and_scanner_memory(self):
        from sleepmode.workers import ChunkResult
        gens = iter([50, 50, 48, 48, 48, 48])
        n = [0]

        class W:
            def run_chunk(w, budget_s, files, stop):
                n[0] += 1
                return ChunkResult(10.0 * n[0], budget_s, 1, False, {"general": next(gens)})
        self.sc.worker = W()
        for _ in range(4):
            self.sc.sleep_chunk(self.cfg.hour_s)
        self.assertEqual(self.sc.mode, "practice")
        self.assertIn("general skills dropping", self.sc.switches[0])

        class Denied:
            name = "mail"
            def scan(s, cfg):
                raise PermissionError("-1743")
        self.sc.scanners = [Denied()]
        self.sc.do_checkin()
        self.assertEqual(self.sc.blocked_scanners, {"mail"})

    def wake_and_join(self, t):
        self.state.request_wake()
        t0 = time.time()
        t.join(5)
        self.assertFalse(t.is_alive())
        return time.time() - t0

    def test_switches_to_practice_and_alternates(self):
        t = self.go()
        self.assertTrue(self.wait_for(lambda: len(self.practice.calls) >= 2))
        self.assertTrue(self.cfg.sleeping_path.exists())
        st = self.state.read_status()
        self.assertEqual(st["mode"], "practice")
        self.assertEqual(st["pid"], os.getpid())
        self.wake_and_join(t)
        sw = self.state.events("switch")
        self.assertEqual(len(sw), 1)
        kinds = [e["kind"] for e in self.state.events() if e["kind"] in ("chunk_done", "practice_round", "switch")]
        i = kinds.index("switch")
        tail = kinds[i + 1:]
        self.assertEqual(tail[0], "practice_round")
        self.assertEqual(tail[1], "chunk_done")      # consolidate after practice
        self.assertEqual(tail[2], "practice_round")
        # consolidate chunks received the practice files
        self.assertTrue(any(c["practice_files"] for c in self.worker.calls))

    def test_wake_file_stops_quickly_and_writes_summary(self):
        t = self.go()
        self.assertTrue(self.wait_for(lambda: len(self.state.events("chunk_done")) >= 1))
        dt = self.wake_and_join(t)
        self.assertLess(dt, 1.0)
        self.assertFalse(self.cfg.sleeping_path.exists())
        self.assertFalse(self.cfg.wake_path.exists())
        txt = self.cfg.summary_path.read_text()
        self.assertIn("WAKE file", txt)
        self.assertIn("Quiz score", txt)
        st = self.state.read_status()
        self.assertEqual(st["state"], "awake")
        self.assertGreaterEqual(st["chunks"], 1)
        self.assertEqual(self.state.events("wake")[-1]["reason"], "WAKE file")

    def test_wake_interrupts_running_chunk(self):
        class Slow(FakeWorker):
            def run_chunk(self, budget_s, files, should_stop):
                for _ in range(1000):
                    if should_stop():
                        from sleepmode.workers import ChunkResult
                        return ChunkResult(None, 0, 0, True)
                    time.sleep(0.01)
        self.sc = self._make(worker=Slow())
        t = self.go()
        self.assertTrue(self.wait_for(lambda: self.state.read_status().get("state") == "sleeping"))
        self.assertLess(self.wake_and_join(t), 1.0)

    def test_timed_wake_interrupts_chunk_and_records_deadline(self):
        now = [100.0]

        class Worker:
            def run_chunk(self, budget_s, files, should_stop):
                self.assert_before = should_stop()
                now[0] = 600.0
                self.assert_after = should_stop()
                return ChunkResult(None, 0, 0, True)

        worker = Worker()
        with patch.dict(os.environ, {"SLEEPMODE_WAKE_AT_MS": "600000"}):
            sc = Scheduler(self.cfg, worker, scanners=[], clock=lambda: now[0])
        sc.run()
        self.assertFalse(worker.assert_before)
        self.assertTrue(worker.assert_after)
        self.assertEqual(sc.stop_reason, "wake deadline")
        self.assertEqual(self.state.read_status()["wake_at_ms"], 600000)
        self.assertEqual(self.state.read_status()["state"], "awake")
        self.assertFalse(self.cfg.sleeping_path.exists())

    def test_invalid_or_absent_wake_deadline_is_open(self):
        for value in ("", "bad", "NaN", "Infinity", "1e308", "-1", "0", "0.5"):
            with self.subTest(value=value), patch.dict(os.environ, {"SLEEPMODE_WAKE_AT_MS": value}):
                sc = self._make()
                self.assertIsNone(sc.wake_at_ms)
                self.assertFalse(sc.should_stop())

    def test_past_wake_deadline_stops_before_work(self):
        with patch.dict(os.environ, {"SLEEPMODE_WAKE_AT_MS": "1000"}):
            sc = Scheduler(self.cfg, self.worker, scanners=[], clock=lambda: 2.0)
        sc.run()
        self.assertEqual(sc.stop_reason, "wake deadline")
        self.assertEqual(self.worker.calls, [])

    def test_assistant_running_wakes(self):
        t = self.go()
        self.assertTrue(self.wait_for(lambda: self.cfg.sleeping_path.exists()))
        open(self.cfg.assistant_running, "w").close()
        t.join(3)
        self.assertFalse(t.is_alive())
        self.assertIn("assistant started", self.cfg.summary_path.read_text())
        self.assertFalse(self.cfg.sleeping_path.exists())

    def test_checkin_every_hour_in_practice_and_when_paused(self):
        t = self.go()
        self.assertTrue(self.wait_for(lambda: self.state.read_status().get("mode") == "practice"))
        n0 = self.scanner.calls
        self.assertTrue(self.wait_for(lambda: self.scanner.calls >= n0 + 2))      # during practice
        open(self.cfg.pause_others, "w").close()
        self.assertTrue(self.wait_for(lambda: self.state.read_status().get("state") == "paused"))
        n1 = self.scanner.calls
        self.assertTrue(self.wait_for(lambda: self.scanner.calls >= n1 + 2))      # while paused
        self.assertTrue(self.state.events("paused"))
        self.wake_and_join(t)
        self.assertEqual(len(self.state.events("checkin")), self.scanner.calls)

    def test_pause_stops_work(self):
        open(self.cfg.pause_others, "w").close()
        t = self.go()
        self.assertTrue(self.wait_for(lambda: len(self.state.events("paused")) >= 2))
        self.wake_and_join(t)
        self.assertEqual(self.worker.calls, [])

    def test_memory_pressure_pauses(self):
        old = sched.memory_pressure
        sched.memory_pressure = lambda: 2
        self.addCleanup(setattr, sched, "memory_pressure", old)
        t = self.go()
        self.assertTrue(self.wait_for(lambda: self.state.events("paused")))
        self.wake_and_join(t)
        self.assertEqual(self.state.events("paused")[0]["reason"], "memory pressure")
        self.assertEqual(self.worker.calls, [])

    def test_nothing_practicable_goes_idle_without_crash(self):
        self.practice = Practice(None)
        self.sc = self._make(practice=self.practice)
        self.cfg.idle_hours = 100
        t = self.go()
        self.assertTrue(self.wait_for(lambda: self.state.events("idle")))
        self.assertTrue(self.wait_for(lambda: self.state.read_status().get("state") == "idle"))
        n = len(self.worker.calls)
        time.sleep(0.5)
        self.assertEqual(len(self.worker.calls), n)         # idle: no more training
        self.assertTrue(t.is_alive())
        self.assertEqual(self.state.read_status()["mode"], "sleep")
        self.wake_and_join(t)
        self.assertEqual(len(self.practice.calls), 1)
        self.assertEqual(self.state.events("error"), [])

    def test_practice_exception_does_not_crash(self):
        def boom(b):
            raise ValueError("bad")
        self.sc = self._make(practice=boom)
        t = self.go()
        self.assertTrue(self.wait_for(lambda: self.state.events("idle")))
        self.wake_and_join(t)
        self.assertIn("practice", self.cfg.summary_path.read_text())

    def _assert_worker_failure_goes_idle(self, code, expected_error):
        self.cfg.max_errors = 2
        self.cfg.idle_hours = 100
        self.sc = self._make(worker=CommandWorker(
            [sys.executable, "-c", code], os.path.join(self.root, "worker-failure"), poll_s=0.01))
        t = self.go()
        try:
            self.assertTrue(self.wait_for(lambda: self.state.events("idle")))
            errors = self.state.events("error")
            self.assertGreaterEqual(len(errors), 2)
            self.assertTrue(all(expected_error in e["error"] for e in errors))
            self.assertIn("2 errors in a row", self.state.events("idle")[0]["reason"])
            self.assertEqual(self.sc.quizzes, [])
            self.assertEqual(self.sc.mode, "sleep")
        finally:
            self.wake_and_join(t)
        self.assertIn(expected_error, self.cfg.summary_path.read_text())

    def test_nonzero_worker_exit_uses_error_backoff(self):
        self._assert_worker_failure_goes_idle("import sys; sys.exit(3)", "exit 3")

    def test_missing_worker_output_uses_error_backoff(self):
        self._assert_worker_failure_goes_idle("pass", "no output json")

    def test_interruption_and_budget_expiry_are_not_worker_failures(self):
        results = [
            ChunkResult(None, 0.01, interrupted=True, info={"error": "exit -15"}),
            ChunkResult(None, 0.01, info={"budget_exceeded": True, "error": "no output json"}),
        ]
        for result in results:
            with self.subTest(info=result.info):
                class Worker:
                    def run_chunk(self, budget, files, stop):
                        return result
                self.sc = self._make(worker=Worker())
                self.sc.sleep_chunk(self.cfg.hour_s)
                self.assertEqual(self.sc.chunks, 1)
                self.assertEqual(self.sc.errors, [])

    def test_refuses_second_instance(self):
        self.cfg.sleeping_path.write_text("%d\n" % os.getppid())
        with self.assertRaises(RuntimeError):
            self._make().start()

    def test_stale_sleeping_file_replaced(self):
        self.cfg.sleeping_path.write_text("999999999\n")
        t = self.go()
        self.assertTrue(self.wait_for(lambda: self.state.sleeping_pid() == os.getpid()))
        self.wake_and_join(t)

    def test_default_practice_fn_without_model_returns_none(self):
        fn = sched.default_practice_fn(self.cfg, self.state)
        self.assertIsNone(fn(1.0))


if __name__ == "__main__":
    unittest.main()
