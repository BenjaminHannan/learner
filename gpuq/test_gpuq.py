"""Tests for gpuq; no GPU needed (GPUQ_FAKE_GPUS). Run: python -m unittest gpuq/test_gpuq.py -v"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PY = Path(__file__).resolve().parent / "gpuq.py"
spec = importlib.util.spec_from_file_location("gpuq_mod", PY)
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


class Base(unittest.TestCase):
    gpus = [0, 1]

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gpuq-test-")
        os.environ.update(GPUQ_HOME=self.tmp, GPUQ_FAKE_GPUS="2")
        os.environ.pop("GPUQ_FAKE_MEM", None)
        self.h = G.Home()
        self.h.ensure()
        self.d = G.Daemon(self.h, self.gpus, grace=1.0, filler_cooldown=0)

    def tearDown(self):
        self.d.stop_all()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def job(self, name, body="true", dest="pending", **hdr):
        hdr = dict(name=name, **hdr)
        text = "#!/usr/bin/env bash\n" + "".join("# gpuq: %s=%s\n" % kv for kv in hdr.items()) + body + "\n"
        p = getattr(self.h, dest) / (name + ".sh")
        p.write_text(text)
        if dest == "filler":
            p.chmod(0o755)
        return p

    def pump(self, cond, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            self.d.tick()
            if cond():
                return
            time.sleep(0.1)
        self.fail("condition not met; status=%s" % json.dumps(G.snapshot(self.h), default=str)[:1500])

    def in_dir(self, d, name):
        return (getattr(self.h, d) / (name + ".sh")).exists()

    def meta(self, name):
        return json.loads((self.h.out / name / "_gpuq.json").read_text())

    def running_names(self, filler=False):
        return [r["name"] for r in self.d.st["running"].values() if bool(r.get("filler")) == filler]


class Scheduling(Base):
    gpus = [0]

    def test_priority_then_age(self):
        rec = 'echo "$GPUQ_NAME" >> "$GPUQ_HOME/order.txt"; sleep 0.2'
        now = time.time()
        for name, prio, age in [("low", 10, 0), ("tie-new", 50, 0), ("high", 90, 0), ("tie-old", 50, 100)]:
            p = self.job(name, rec, priority=prio)
            os.utime(p, (now - age, now - age))
        self.pump(lambda: self.in_dir("done", "low"))
        self.assertEqual((self.h.root / "order.txt").read_text().split(), ["high", "tie-old", "tie-new", "low"])

    def test_cancel_running(self):
        self.job("long", "sleep 60")
        self.pump(lambda: "long" in self.running_names())
        G.cmd_cancel(type("A", (), {"name": "long"}))
        self.pump(lambda: self.in_dir("failed", "long"))
        self.assertEqual(self.meta("long")["rc"], "cancelled")

    def test_bad_job_goes_to_failed(self):
        self.job("bad", gpus=7)
        (self.h.pending / "garbage.sh").write_bytes(b"\xff\xfe\x00 not a job")
        self.job("good")
        self.pump(lambda: self.in_dir("done", "good"))
        self.assertTrue(self.in_dir("failed", "bad"))
        self.assertIn("gpus", self.d.st["jobs"]["bad"]["reason"])


class TwoGpu(Base):
    def test_two_gpu_waits_for_both_and_blocks_lower_priority(self):
        self.job("filler-ignores-term", "trap '' TERM; while :; do sleep 0.2; done", dest="filler")
        self.job("a", "sleep 1.5", priority=50)
        self.pump(lambda: "a" in self.running_names())
        self.job("b", 'echo "$CUDA_VISIBLE_DEVICES" > gpus.txt; sleep 0.3', gpus=2, priority=90)
        self.job("c", "sleep 0.2", priority=10)
        self.pump(lambda: self.in_dir("done", "c"), timeout=40)
        a, b, c = self.meta("a"), self.meta("b"), self.meta("c")
        self.assertGreaterEqual(b["start"], a["end"])        # waited for both GPUs
        self.assertGreaterEqual(c["start"], b["end"])        # lower priority did not jump in
        self.assertEqual(sorted(b["gpu"]), [0, 1])
        self.assertEqual((self.h.out / "b" / "gpus.txt").read_text().strip(), "0,1")

    def test_external_busy_gpu_is_skipped(self):
        os.environ["GPUQ_FAKE_MEM"] = "1:9000"
        self.job("x", "sleep 0.5")
        self.job("y", "sleep 0.5")
        self.d.tick()
        self.assertEqual([r["gpus"] for r in self.d.st["running"].values() if not r.get("filler")], [[0]])
        self.pump(lambda: self.in_dir("done", "y"))
        self.assertEqual(self.meta("x")["gpu"], [0])
        self.assertEqual(self.meta("y")["gpu"], [0])


class Fillers(Base):
    gpus = [0]

    def test_keepalive_alert_and_filler_preemption(self):
        # empty filler dir: keepalive + loud alert
        self.pump(lambda: "filler-keepalive" in self.running_names(filler=True))
        self.assertTrue(self.h.alert.exists())
        self.job("real", "echo hi")
        self.pump(lambda: self.in_dir("done", "real"))
        self.assertEqual(self.meta("real")["rc"], 0)

    def test_filler_runs_numbered_and_is_preempted(self):
        self.job("seed", 'echo "$GPUQ_FILLER_RUN" > ran.txt; trap "" TERM; while :; do sleep 0.2; done',
                 dest="filler", priority=5)
        self.pump(lambda: "filler-seed" in self.running_names(filler=True))
        ran = self.h.out / "filler-seed" / "run1" / "ran.txt"
        self.pump(ran.exists)
        self.assertEqual(ran.read_text().strip(), "1")
        t0 = time.time()
        self.job("real", "echo real")                  # filler ignores SIGTERM -> SIGKILL after grace
        self.pump(lambda: self.in_dir("done", "real"))
        self.assertLess(time.time() - t0, 10)
        self.assertFalse(self.h.alert.exists())
        # filler comes back as run 2 once the real job is done
        self.pump(lambda: (self.h.out / "filler-seed" / "run2").exists())
        self.assertEqual(self.d.st["filler_runs"]["seed"], 2)


class Failures(Base):
    gpus = [0]

    def test_timeout_kills_process_group(self):
        self.job("slow", "sleep 300 & sleep 300", hours=0.0004)      # 1.44 s * 1.1
        self.pump(lambda: self.in_dir("failed", "slow"))
        self.assertEqual(self.meta("slow")["rc"], "timeout")
        self.assertEqual(self.d.st["jobs"]["slow"]["rc"], "timeout")

    def test_retry_then_success(self):
        self.job("flaky", 'echo "attempt $GPUQ_ATTEMPT"; [ "$GPUQ_ATTEMPT" = 2 ] || exit 3', retries=1)
        self.pump(lambda: self.in_dir("done", "flaky"))
        text = (self.h.logs / "flaky.log").read_text()
        self.assertEqual(text.count("=== gpuq attempt"), 2)
        self.assertEqual(self.meta("flaky")["attempt"], 2)

    def test_failure_without_retries(self):
        self.job("dead", "exit 5")
        self.pump(lambda: self.in_dir("failed", "dead"))
        self.assertEqual(self.d.st["jobs"]["dead"]["rc"], 5)
        G.cmd_requeue(type("A", (), {"name": "dead"}))
        self.assertTrue(self.in_dir("pending", "dead"))

    def test_crash_recovery(self):
        p = subprocess.Popen(["true"])
        p.wait()
        dead = p.pid
        for name, hdr in (("redo", dict(retries=1)), ("giveup", {}), ("orphan", dict(retries=1))):
            self.job(name, "echo ok", dest="running", **hdr)
        st = G.load_state(self.h)
        for name in ("redo", "giveup"):
            st["running"][name] = dict(name=name, gpus=[0], attempt=1, pid=dead, start=time.time(), hours=1,
                                       rcfile=str(self.h.out / name / "_rc"), out=str(self.h.out / name),
                                       filler=False)
        G.save_state(self.h, st)
        d2 = G.Daemon(self.h, [0], grace=1.0)
        self.d = d2
        d2.recover()
        d2.tick()                                    # reaps the dead entries
        self.assertTrue(self.in_dir("failed", "giveup"))
        self.pump(lambda: self.in_dir("done", "redo") and self.in_dir("done", "orphan"))
        self.assertEqual(self.meta("redo")["attempt"], 2)


class Rendering(Base):
    gpus = [0]

    def test_render_md_and_cli(self):
        self.job("ok1", "echo fine")
        self.job("bad1", "exit 1")
        self.pump(lambda: self.in_dir("done", "ok1") and self.in_dir("failed", "bad1"))
        self.job("waiting", priority=5)
        out = self.h.root / "QUEUE.md"
        G.render_md(self.h, out)
        text = out.read_text()
        for needle in ("## Running", "## Pending", "## Recently done (last 30)", "## Failed", "ok1", "bad1", "waiting"):
            self.assertIn(needle, text)
        self.assertEqual(G.snapshot(self.h)["pending"][0]["name"], "waiting")

    def test_cli_end_to_end(self):
        job = Path(self.tmp) / "cli.sh"
        job.write_text("#!/usr/bin/env bash\n# gpuq: name=cli-job\n# gpuq: priority=1   (low)\necho cli-ok\n")
        run = lambda *a, **kw: subprocess.run([sys.executable, str(PY)] + list(a), capture_output=True, text=True,
                                              timeout=30, **kw)
        self.assertEqual(run("submit", str(job), "--priority", "77").returncode, 0)
        self.assertNotEqual(run("submit", str(job)).returncode, 0)       # duplicate refused
        self.assertIn("priority=77", (self.h.pending / "cli-job.sh").read_text())
        r = run("daemon", "--tick", "0.3", "--max-seconds", "3", "--grace", "1", "--kill-on-exit")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.in_dir("done", "cli-job"))
        s = json.loads(run("status", "--json").stdout)
        self.assertEqual(s["done"][0]["name"], "cli-job")
        self.assertEqual(len(s["gpus"]), 2)
        self.assertEqual(run("render-md", str(self.h.root / "Q.md")).returncode, 0)


if __name__ == "__main__":
    unittest.main()
