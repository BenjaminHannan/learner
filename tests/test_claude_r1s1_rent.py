"""Offline tests for scripts/claude_r1s1_rent.py (R1 stage 1ab rental controller). No network: urlopen is made to fail
and the controller's HTTP functions are mocked. Run: python3 -B -m unittest tests.test_claude_r1s1_rent"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "claude_r1s1_rent.py"
spec = importlib.util.spec_from_file_location("r1s1_rent", SCRIPT)
rent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rent)

SEAL_REL = rent.SEAL_DEFAULT
LABEL = "claude-steals8-r1s1-1ab"


def sh(b: bytes) -> str:
    return rent.sha(b)


def runner_package_hash(root: Path) -> str:
    """A copy of the runner's own package_hash() (scripts/premonition_steals_r1_stage1.py), over `root`."""
    digest = hashlib.sha256()
    for path in sorted([*(root / "premonition").glob("*.py"), *(root / "learnlab").rglob("*.py"),
                        *(root / "memorylab").rglob("*.py")]):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


class Ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Fixture(unittest.TestCase):
    """A throwaway git repo with the files the controller packs; REPO is pointed at it. Any real HTTP fails."""

    def setUp(self) -> None:
        net = mock.patch("urllib.request.urlopen", side_effect=AssertionError("network used in a test"))
        net.start()
        self.addCleanup(net.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.files = {
            "premonition/a.py": "A = 1\n", "learnlab/b.py": "B = 2\n", "learnlab/sub/d.py": "D = 4\n",
            "memorylab/c.py": "C = 3\n", rent.RUNNER: "print('runner')\n", rent.CARD: "# card\n",
            "data/tokenizer/premonition-tok-v2.json": "{}\n", "data/english/raw/r.jsonl": "{}\n",
            "data/village/patterns/p.json": "[]\n", "tests/ignored.py": "x\n"}
        for name, text in self.files.items():
            self.write(name, text)
        self.write(SEAL_REL, self.seal_text())
        self.git("init", "-q")
        self.commit("first")
        patch = mock.patch.object(rent, "REPO", self.repo)
        patch.start()
        self.addCleanup(patch.stop)
        self.out = Path(self.tmp.name) / "pack"

    def write(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def seal_text(self) -> str:
        """The seal's three entries: the card, the runner, and the package line."""
        return (f"{sh((self.repo / rent.CARD).read_bytes())}  {rent.CARD}\n"
                f"{sh((self.repo / rent.RUNNER).read_bytes())}  {rent.RUNNER}\n"
                f"{runner_package_hash(self.repo)}  {rent.PACKAGE}\n")

    def reseal(self) -> None:
        self.write(SEAL_REL, self.seal_text())

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       check=True, capture_output=True)

    def commit(self, msg: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def pack(self, **kw) -> dict:
        ns = Ns(seal=kw.get("seal", SEAL_REL), torch=kw.get("torch", rent.TORCH_PIN), dph=kw.get("dph", 0.45),
                out=str(self.out))
        with mock.patch("builtins.print") as pr:
            rent.pack(ns)
        return json.loads(pr.call_args[0][0])

    def args(self) -> list:
        return json.loads((self.out / "args.json").read_text())

    def members(self) -> set:
        with tarfile.open(self.out / "pack.tar.xz", "r:xz") as t:
            return set(t.getnames())


class PackTest(Fixture):
    def test_contents_and_job(self) -> None:
        info = self.pack()
        names = self.members()
        for f in ("premonition/a.py", "learnlab/b.py", "learnlab/sub/d.py", "memorylab/c.py", rent.RUNNER, rent.CARD,
                  SEAL_REL, "data/tokenizer/premonition-tok-v2.json", "data/english/raw/r.jsonl",
                  "data/village/patterns/p.json", "SEAL-pack.sha256.txt"):
            self.assertIn(f, names)
        self.assertNotIn("tests/ignored.py", names)
        args = self.args()
        self.assertEqual(args[:2], ["bash", "-c"])
        self.assertEqual(rent.job_stage(args), "1ab")
        self.assertEqual(sh(base64.b64decode("".join(args[4:]))), info["pack_sha256"])
        self.assertIn(f"PACK_SHA={info['pack_sha256']}", args[2])
        self.assertIn(f"SEAL_REL={SEAL_REL}", args[2])
        self.assertEqual(rent.HARD_STOP, {"1ab": 2.80})

    def test_the_two_stage_options_are_gone(self) -> None:
        for flag in (["--stage", "1a"], ["--flop-budget", "1e16"], ["--price", "x"], ["--allow-dirty"]):
            with mock.patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit) as cm:
                rent.main(["pack", "--dph", "0.45", "--out", str(self.out), *flag])
            self.assertEqual(cm.exception.code, 2, flag)
        self.assertFalse(self.out.exists())

    def test_needs_card_and_seal_at_head(self) -> None:
        self.git("rm", "-q", SEAL_REL)
        self.commit("no seal")
        with self.assertRaises(SystemExit) as cm:
            self.pack()
        self.assertIn("does not exist", str(cm.exception))
        self.reseal()                                                  # back, but not committed
        with self.assertRaises(SystemExit) as cm:
            self.pack()
        self.assertIn("HEAD", str(cm.exception))
        self.commit("seal again")
        self.git("rm", "-q", rent.CARD)
        self.commit("no card")
        with self.assertRaises(SystemExit):
            self.pack()
        self.assertFalse(self.out.exists())

    def test_card_and_runner_must_match_the_seal(self) -> None:
        self.write(rent.CARD, "# card changed after the seal\n")
        self.commit("card edited")
        with self.assertRaises(SystemExit) as cm:
            self.pack()
        self.assertIn("does not match", str(cm.exception))
        self.assertIn(rent.CARD, str(cm.exception))
        self.reseal()                                       # reseal the card, then break the runner instead
        self.commit("resealed")
        self.pack()
        self.write(rent.RUNNER, "print('edited runner')\n")
        self.commit("runner edited")
        with self.assertRaises(SystemExit) as cm:
            self.pack()
        self.assertIn(rent.RUNNER, str(cm.exception))

    def test_package_hash_must_match_the_seal(self) -> None:
        self.write("premonition/a.py", "A = 99\n")                 # code changed and committed, seal not redone
        self.commit("code edited")
        with self.assertRaises(SystemExit) as cm:
            self.pack()
        self.assertIn(rent.PACKAGE, str(cm.exception))
        self.reseal()
        self.commit("resealed")
        self.pack()                                                # the same code, sealed: packs
        self.write("learnlab/sub/d.py", "D = 5\n")                 # a nested learnlab file counts too
        self.commit("nested edited")
        with self.assertRaises(SystemExit) as cm:
            self.pack()
        self.assertIn(rent.PACKAGE, str(cm.exception))

    def test_seal_without_the_package_line_refused(self) -> None:
        self.write(SEAL_REL, "".join(self.seal_text().splitlines(True)[:2]))
        self.commit("two-entry seal")
        with self.assertRaises(SystemExit) as cm:
            self.pack()
        self.assertIn(rent.PACKAGE, str(cm.exception))

    def test_untracked_py_on_disk_refused(self) -> None:
        self.write("premonition/extra.py", "X = 1\n")             # untracked: the box would hash it, the pack lacks it
        with self.assertRaises(SystemExit) as cm:
            self.pack()
        self.assertIn("not the packed ones", str(cm.exception))
        self.assertIn("premonition/extra.py", str(cm.exception))
        (self.repo / "premonition/extra.py").unlink()
        self.write("learnlab/deep/x/y.py", "Y = 1\n")             # rglob reaches it
        with self.assertRaises(SystemExit):
            self.pack()
        (self.repo / "learnlab/deep/x/y.py").unlink()
        self.write(".gitignore", "memorylab/ign.py\n")             # ignored by git, but still on disk
        self.commit("ignore")
        self.write("memorylab/ign.py", "Z = 1\n")
        with self.assertRaises(SystemExit):
            self.pack()
        self.assertFalse(self.out.exists())

    def test_nested_premonition_py_is_not_hashed_by_the_runner(self) -> None:
        # premonition is globbed flat by the runner: an untracked nested file is not in its hash, so it does not refuse
        self.write("premonition/sub/z.py", "Z = 1\n")
        self.pack()

    def test_dirty_tree_refused(self) -> None:
        self.write("premonition/a.py", "A = 99\n")
        with self.assertRaises(SystemExit) as cm:
            self.pack()
        self.assertIn("HEAD", str(cm.exception))

    def test_untracked_runner_refused(self) -> None:
        self.git("rm", "-q", "--cached", rent.RUNNER)
        self.git("commit", "-q", "-m", "untrack runner")
        with self.assertRaises(SystemExit):
            self.pack()

    def test_deadline_counts_from_the_billing_start(self) -> None:           # N3
        info = self.pack(dph=0.45)
        want = int(0.9 * 2.80 / 0.45 * 3600) - 900                  # from BOX_START, the create request
        self.assertEqual(want, 19260)
        self.assertEqual((info["run_deadline_s"], rent.deadline_seconds(0.45)), (want, want))
        job = self.args()[2]
        self.assertIn("DEADLINE_S=19260", job)
        self.assertIn("RUN_END=$((BOX_START + DEADLINE_S))", job)
        self.assertIn("SPENT=$(( $(date +%s) - BOX_START ))", job)
        self.assertEqual(job.count("BOX_START=__BOX_START__"), 1)        # set by create, not by pack
        self.assertIn("DPH=0.45", job)
        self.assertEqual((rent.SAFETY, rent.EXPORT_SECONDS, rent.PREJOB_S), (0.9, 900, 900))

    def test_pack_refuses_when_the_deadline_is_under_the_floor(self) -> None:   # N3
        self.assertEqual(rent.FLOOR_S, 900 + 1800 + 2400 + 3600)
        self.pack(dph=0.90)                                       # 9180 s: fits
        shutil.rmtree(self.out)
        self.assertEqual(rent.deadline_seconds(1.0), 8172)
        with self.assertRaises(SystemExit) as cm:
            self.pack(dph=1.0)                                    # 8172 s < 8700
        self.assertIn("feasibility floor", str(cm.exception))
        self.assertFalse(self.out.exists())
        for dph in (0, -1):
            with self.assertRaises(SystemExit):
                self.pack(dph=dph)


class JobTextTest(Fixture):
    def job(self, **kw) -> str:
        self.pack(**kw)
        return self.args()[2]

    def test_bash_syntax(self) -> None:
        r = subprocess.run(["bash", "-n"], input=self.job(), text=True, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_step_order(self) -> None:
        job = self.job()
        marks = ['$PY -B $RUNNER build --root "$ROOT" --workers "$(nproc)"',
                 '$PY -B $RUNNER run --root "$ROOT" --data-rel "$DATA_REL" --out "$ROOT/out/1a" --timing',
                 '$PY -B $RUNNER price --from "$ROOT/out/1a" --dph "$DPH" --spent-seconds "$SPENT" '
                 '--seconds-left "$SECONDS_LEFT"',
                 '--out "$ROOT/out/1b/PRICE.json"',
                 'echo "=== PRICE ',
                 'cp "$ROOT/$SEAL_REL" "$ROOT/out/1b/SEAL.sha256.txt"',
                 '$PY -B $RUNNER run --root "$ROOT" --data-rel "$DATA_REL" --out "$ROOT/out/1b" '
                 '--price "$ROOT/out/1b/PRICE.json" --timing-from "$ROOT/out/1a"',
                 '$PY -B $RUNNER verify --out "$ROOT/out/1a"', '$PY -B $RUNNER verify --out "$ROOT/out/1b"',
                 "finish DONE"]
        at = [job.index(m) for m in marks[:-1]] + [job.rindex(marks[-1])]       # the DRYRUN stop also says finish DONE
        self.assertEqual(at, sorted(at), marks)
        self.assertIn("RUNNER=${RUNNER:-scripts/premonition_steals_r1_stage1.py}", job)
        self.assertIn("PY=${PY:-python3}", job)
        self.assertIn('SPENT=$(( $(date +%s) - BOX_START ))', job)
        self.assertIn('timeout --foreground -k 60 "${LEFT}s" $PY -B $RUNNER run', job)
        self.assertIn("[ \"$LEFT\" -gt \"$TIMING_MAX_S\" ] && LEFT=$TIMING_MAX_S", job)     # 1a: min(left, 2400)
        self.assertIn("TIMING_MAX_S=2400", job)
        self.assertNotIn("--flop-budget", job)
        self.assertNotIn("--unsealed", job)

    def test_gate_and_failure_lines(self) -> None:
        job = self.job()
        self.assertIn('if [ "$RC" = 3 ] || [ "$RC" = 4 ]', job)
        self.assertIn('say "R1S1 GATE-STOP $RC"', job)
        self.assertIn("finish GATE", job)
        self.assertIn('fail() { say "R1S1-FAIL $*"; finish FAIL; }', job)
        self.assertIn('say "R1S1 $1"', job)                       # the closing mark, after the export
        self.assertLess(job.index('say "MANIFEST"'), job.index('say "R1S1 $1"'))
        self.assertIn("  sleep 600 ", job)                        # not 3600
        self.assertNotIn("sleep 3600", job)
        self.assertIn("torch.cuda.get_device_name", job)
        self.assertIn("torch==$TORCH_PIN", job)
        self.assertIn("pip uninstall -y torchvision torchaudio", job)
        self.assertIn("export/MANIFEST.sha256", job)

    def test_export_holds_both_stages_and_all_checkpoints(self) -> None:
        job = self.job()
        self.assertIn('tar -czf export/out.tar.gz --exclude=ckpt -C "$ROOT/out" $stages', job)
        self.assertIn('tar -czf export/ckpt.tar.gz -C "$ROOT/out" $ckpts', job)
        self.assertIn("ls -d */ckpt", job)


class CostTest(unittest.TestCase):
    def test_arithmetic(self) -> None:
        x = {"dph_total": 0.45, "start_date": 1000.0}
        c = rent.running_cost(x, 1000.0 + 2 * 3600)
        self.assertAlmostEqual(c["usd"], 0.90)
        self.assertAlmostEqual(c["hours"], 2.0)
        self.assertIsNone(rent.running_cost({"start_date": 1.0}, 5.0)["usd"])
        self.assertAlmostEqual(rent.running_cost({"dph_total": 1.0, "duration": 1800}, 0)["usd"], 0.5)
        self.assertAlmostEqual(rent.running_cost({"dph_total": 1.0, "start_date": 100}, 100, 0.25)["usd"], 0.25)

    def test_hard_stop(self) -> None:
        self.assertEqual(rent.HARD_STOP, {"1ab": 2.80})
        self.assertEqual(rent.STAGES, ("1ab",))
        self.assertFalse(rent.over_stop(2.7999, "1ab"))
        self.assertTrue(rent.over_stop(2.80, "1ab"))
        self.assertFalse(rent.over_stop(None, "1ab"))
        # at $0.45/h the stop is reached after 6.22 h
        self.assertTrue(rent.over_stop(rent.running_cost({"dph_total": 0.45, "start_date": 0}, 6.23 * 3600)["usd"], "1ab"))
        self.assertFalse(rent.over_stop(rent.running_cost({"dph_total": 0.45, "start_date": 0}, 6.21 * 3600)["usd"], "1ab"))

    def test_stage_from_label(self) -> None:
        self.assertEqual(rent.stage_of(LABEL), "1ab")
        self.assertEqual(rent.stage_of("whatever", "1ab"), "1ab")
        for bad in ("claude-other-job", "claude-steals8-r1s1-1a", "claude-steals8-r1s1-1b"):
            with self.assertRaises(SystemExit):
                rent.stage_of(bad)

    def test_progress_key_ignores_the_clock_only(self) -> None:
        a = "x\n=== TICK 10:00:00 | line | kb=5"
        self.assertEqual(rent.progress_key(a), rent.progress_key("x\n=== TICK 10:02:00 | line | kb=5"))
        self.assertNotEqual(rent.progress_key(a), rent.progress_key("x\n=== TICK 10:02:00 | line | kb=6"))


class WaitlogTest(unittest.TestCase):
    STOPPED = [("PUT", "/instances/7/", {"state": "stopped"})]

    def run_wait(self, instance, text="", **kw):
        """waitlog against a box that reports `instance` until a stop request arrives, then reports it stopped."""
        calls = []

        def fake_call(method, path, body=None, timeout=60):
            calls.append((method, path, body))
            return {"success": True}

        def fake_inst(_i):
            stopped = any(b == {"state": "stopped"} for _, _, b in calls)
            return dict(instance, actual_status="stopped") if stopped else instance
        ns = Ns(id="7", stage=None, max_min=kw.get("max_min"), poll=0)
        with mock.patch.object(rent, "call", fake_call), mock.patch.object(rent, "inst", fake_inst), \
                mock.patch.object(rent, "log_text", return_value=text), mock.patch.object(rent.time, "sleep"), \
                mock.patch("builtins.print") as pr, self.assertRaises(SystemExit) as cm:
            rent.waitlog(ns)
        return cm.exception.code, calls, json.loads(pr.call_args[0][0]) if pr.call_args else None

    def inst(self, hours, dph=1.0, status="running", label=LABEL):
        return {"label": label, "actual_status": status, "dph_total": dph, "start_date": time.time() - hours * 3600}

    def test_hard_stop_stops_not_destroys(self) -> None:
        code, calls, out = self.run_wait(self.inst(2.9))           # $2.90 on a $2.80 stop
        self.assertEqual((code, out["event"]), (3, "HARD-STOP"))
        self.assertEqual(calls, self.STOPPED)
        self.assertFalse(any(m == "DELETE" for m, _, _ in calls))
        self.assertEqual(out["hard_stop_usd"], 2.80)

    def test_not_over_the_stop_just_below(self) -> None:
        code, _, out = self.run_wait(self.inst(2.7), "=== R1S1 DONE x")
        self.assertEqual((code, out["event"]), (0, "DONE"))

    def test_not_running_within_the_prejob_allowance_stops(self) -> None:
        inst = {"label": LABEL, "actual_status": "loading", "dph_total": 1.0, "start_date": 0}   # billed from 0
        self.assertEqual(rent.START_MIN, rent.PREJOB_S // 60)                      # the allowance is enforced
        with mock.patch.object(rent.time, "time", side_effect=[0, 14 * 60, 16 * 60]):
            code, calls, out = self.run_wait(inst)
        self.assertEqual((code, out["event"], calls), (4, "NOT-RUNNING", self.STOPPED))
        self.assertTrue(out["stopped"]["confirmed"])

    def test_closing_marks_stop_the_instance(self) -> None:
        code, calls, out = self.run_wait(self.inst(0.01), "a\n=== R1S1 DONE 2026-10-20T10:00:00Z\n")
        self.assertEqual((code, out["event"], calls), (0, "DONE", self.STOPPED))
        code, calls, out = self.run_wait(self.inst(0.01), "=== R1S1-FAIL build 2026\n=== R1S1 FAIL 2026\n")
        self.assertEqual((code, out["event"], calls), (2, "JOB-FAIL", self.STOPPED))

    def test_early_fail_line_without_the_closing_mark_does_not_stop(self) -> None:      # N1
        text = "=== R1S1-FAIL x 2026-10-20T10:00:00Z\n=== MANIFEST\n"
        self.assertEqual(rent.closing_marks(text.splitlines()), {"DONE": [], "FAIL": [], "GATE": []})
        inst = {"label": LABEL, "actual_status": "running", "dph_total": 1.0, "start_date": 0}
        with mock.patch.object(rent.time, "time", side_effect=[0, 60, 720]):
            code, calls, out = self.run_wait(inst, text)       # the early line is ignored; only the watchdog ends it
        self.assertEqual((code, out["event"], calls), (5, "WATCHDOG", self.STOPPED))     # and it stops the box
        code, calls, out = self.run_wait(self.inst(0.01), text + "=== R1S1 FAIL rc=na 2026-10-20T10:01:00Z\n")
        self.assertEqual((code, out["event"], calls), (2, "JOB-FAIL", self.STOPPED))

    def test_early_gate_stop_line_does_not_stop_but_the_closing_gate_does(self) -> None:    # N1 + GATE
        early = "=== R1S1 GATE-STOP 3 2026-10-20T10:00:00Z\n"
        self.assertEqual(rent.closing_marks(early.splitlines()), {"DONE": [], "FAIL": [], "GATE": []})
        code, calls, out = self.run_wait(self.inst(0.01), early + "=== R1S1 GATE 2026-10-20T10:01:00Z\n")
        self.assertEqual((code, out["event"], calls), (8, "GATE", self.STOPPED))

    def test_marks_must_stand_alone_on_a_line(self) -> None:
        self.assertEqual(len(rent.closing_marks(["=== R1S1 DONE 2026"])["DONE"]), 1)
        self.assertEqual(len(rent.closing_marks(["2026-10-20T10:00 === R1S1 DONE 2026"])["DONE"]), 1)
        for text in ("=== R1S1 DONEX", "=== R1S1-FAIL x", "=== R1S1 GATE-STOP 4", "=== R1S1 START stage 1ab",
                     "echo '=== R1S1DONE'"):
            self.assertEqual(rent.closing_marks([text]), {"DONE": [], "FAIL": [], "GATE": []}, text)

    def test_default_limit_comes_from_the_box(self) -> None:                      # N4
        self.assertAlmostEqual(rent.time_limit_min(1.0), 2.80 * 60 + 30)           # 198 min
        self.assertAlmostEqual(rent.time_limit_min(0.4), 450.0)

    def test_timeout_stops_the_instance(self) -> None:                             # N4
        now = 199 * 60                                                             # the derived limit is 198 min
        inst = {"label": LABEL, "actual_status": "running", "dph_total": 1.0, "start_date": now - 600}
        with mock.patch.object(rent.time, "time", side_effect=[0, now]):
            code, calls, out = self.run_wait(inst)
        self.assertEqual((code, out["event"], calls), (6, "TIMEOUT", self.STOPPED))
        self.assertEqual(out["limit_min"], 198.0)
        inst["start_date"] = 197 * 60 - 600                                        # a minute inside the limit: no stop yet
        with mock.patch.object(rent.time, "time", side_effect=[0, 197 * 60, 199 * 60]):
            code, calls, out = self.run_wait(inst)
        self.assertEqual((out["event"], calls, out["waited_min"]), ("TIMEOUT", self.STOPPED, 199.0))

    def test_a_box_stopped_before_the_watch_is_never_not_running(self) -> None:          # fix (3)
        for status in ("exited", "stopped", "offline"):
            box = {"label": LABEL, "actual_status": status, "intended_status": "stopped", "dph_total": 0.45,
                   "start_date": time.time() - 5 * 3600}                                   # long past 15 min
            code, _, out = self.run_wait(box)
            self.assertEqual((code, out["event"]), (6, "INSTANCE-ENDED"), status)
            self.assertIn("never destroy", out["note"].replace("destroy only after", "never destroy before"))
            self.assertNotIn("try another host", json.dumps(out))

    def test_a_missing_clock_is_an_unknown_cost_not_zero(self) -> None:
        self.assertIsNone(rent.running_cost({"dph_total": 0.45}, time.time())["usd"])
        self.assertIsNone(rent.running_cost({"dph_total": 0.45, "duration": 0}, time.time())["usd"])
        self.assertAlmostEqual(rent.running_cost({"dph_total": 0.45, "duration": 3600}, 0)["usd"], 0.45)

    def test_three_failed_polls_in_a_row_stop(self) -> None:
        code, calls, out = self.run_wait({"label": LABEL, "actual_status": "running"})      # no price: unreadable cost
        self.assertEqual((code, out["event"]), (7, "BLIND"))
        self.assertEqual(calls, self.STOPPED)
        calls = []
        replies = iter([None, None, {"label": LABEL, "actual_status": "running", "dph_total": 1.0,
                                     "start_date": time.time()}, None, None, None])
        with mock.patch.object(rent, "inst", lambda _i: next(replies, {"actual_status": "stopped",
                                                                      "intended_status": "stopped"})), \
                mock.patch.object(rent, "call", lambda m, p, b=None, timeout=60: calls.append((m, p, b)) or
                                  {"success": True}), \
                mock.patch.object(rent, "log_text", return_value=""), mock.patch.object(rent.time, "sleep"), \
                mock.patch("builtins.print") as pr, mock.patch("sys.stderr", io.StringIO()), \
                self.assertRaises(SystemExit) as cm:
            rent.waitlog(Ns(id="7", stage=None, max_min=None, poll=0))
        self.assertEqual((cm.exception.code, json.loads(pr.call_args[0][0])["event"]), (7, "BLIND"))   # 2 fails reset
        self.assertEqual(calls, self.STOPPED)

    def test_the_cost_is_checked_before_the_log_is_fetched(self) -> None:
        fetched = []
        with mock.patch.object(rent, "log_text", side_effect=lambda *a, **k: fetched.append(1) or ""):
            code, _, out = self.run_wait(self.inst(2.9))
        self.assertEqual((code, out["event"], fetched), (3, "HARD-STOP", []))

    def test_stop_confirmed_needs_vast_to_intend_the_stop(self) -> None:
        replies = iter([{"actual_status": "offline", "intended_status": "running"},     # offline, not stopped by us
                        {"actual_status": "exited", "intended_status": "running"},
                        {"actual_status": "stopped", "intended_status": "stopped"}])
        with mock.patch.object(rent, "inst", lambda _i: next(replies)), \
                mock.patch.object(rent, "call", return_value={"success": False}), \
                mock.patch.object(rent.time, "sleep"), mock.patch("sys.stderr", io.StringIO()):
            out = rent.stop_confirmed(7)
        self.assertEqual((out["confirmed"], out["status"], out["intended"]), (True, "stopped", "stopped"))
        with mock.patch.object(rent, "inst", return_value={}), mock.patch.object(rent, "call", return_value={}), \
                mock.patch.object(rent.time, "sleep"):
            self.assertEqual(rent.stop_confirmed(7)["status"], "gone")                  # no longer listed (or 404)
        with mock.patch.object(rent, "call", return_value={"success": False, "http": 404}):
            self.assertEqual(rent.inst(7), {})


class Net(Fixture):
    """create / pull / destroy with the HTTP layer mocked."""

    def setUp(self) -> None:
        super().setUp()
        self.pack(dph=0.45)
        self.calls = []
        self.instances = []                                       # what GET /instances/ lists
        self.offer_dph = 0.40                                     # what the offer costs (the pack allows 0.45)
        self.listing_fails = False
        self.stop_after = 0                                       # GETs of a stopped-by-us instance that still say running
        self.stop_requested = False
        self.sleep = mock.patch.object(rent.time, "sleep")
        self.sleep_mock = self.sleep.start()
        self.addCleanup(self.sleep.stop)
        call = mock.patch.object(rent, "call", self.fake_call)
        call.start()
        self.addCleanup(call.stop)

    def fake_call(self, method, path, body=None, timeout=60):
        self.calls.append((method, path))
        if method == "GET" and path == "/instances/":
            return {"success": False, "http": 503} if self.listing_fails else {"instances": list(self.instances)}
        if method == "POST" and path == "/bundles/":       # Vast answers a full filter query, never an id-only one
            if "id" in (body or {}) or "gpu_name" not in (body or {}):
                return {"offers": []}
            return {"offers": [{"id": 999, "dph_total": 0.1}, {"id": 123, "dph_total": self.offer_dph}]}
        if method == "GET" and path.startswith("/instances/"):
            i = int(path.strip("/").split("/")[-1])
            found = [dict(x) for x in self.instances if x["id"] == i]
            if found and self.stop_requested:
                if self.stop_after > 0:
                    self.stop_after -= 1
                else:
                    found[0]["actual_status"] = "exited"
            return {"instances": found}
        if method == "PUT" and path.startswith("/instances/") and body == {"state": "stopped"}:
            self.stop_requested = True
        if method == "DELETE":
            i = int(path.strip("/").split("/")[-1])
            self.instances = [x for x in self.instances if x["id"] != i]
        return {"success": True, "new_contract": 99}

    def create(self, **kw):
        ns = Ns(offer="123", args=str(self.out / "args.json"), label=kw.get("label"), disk=60,
                dryrun=kw.get("dryrun", False), yes=kw.get("yes", False))
        with mock.patch("builtins.print") as pr:
            rent.create(ns)
        return pr.call_args[0][0]

    def test_create_without_yes_sends_nothing(self) -> None:
        text = self.create()
        self.assertEqual(self.calls, [])
        shown = json.loads(text)
        self.assertFalse(shown["sent"])
        self.assertEqual(shown["would_send"]["body"]["image"], rent.IMAGE)
        self.assertEqual(shown["would_send"]["body"]["label"], LABEL)
        self.assertEqual(shown["hard_stop_usd"], 2.80)
        self.assertNotIn(self.args()[4][:50], text)                # the base64 pack is not dumped
        self.create(dryrun=True)
        self.assertEqual(self.calls, [])

    def test_create_with_yes_sends_once(self) -> None:
        self.create(yes=True)
        puts = [c for c in self.calls if c[0] == "PUT"]
        self.assertEqual(puts, [("PUT", "/asks/123/")])

    def test_create_refuses_a_dearer_offer(self) -> None:
        self.offer_dph = 0.50
        with self.assertRaises(SystemExit) as cm:
            self.create(yes=True)
        self.assertIn("nothing sent", str(cm.exception))
        self.assertFalse(any(m == "PUT" for m, _ in self.calls))

    def test_create_refuses_when_the_listing_fails(self) -> None:
        self.listing_fails = True
        with self.assertRaises(SystemExit):
            self.create(yes=True)
        self.assertFalse(any(m == "PUT" for m, _ in self.calls))

    def test_create_with_yes_stops_on_duplicate_label(self) -> None:
        self.instances = [{"id": 5, "label": LABEL}]
        with self.assertRaises(SystemExit):
            self.create(yes=True)
        self.assertFalse(any(m == "PUT" for m, _ in self.calls))

    def test_create_refuses_wrong_label(self) -> None:
        for label in ("claude-steals8-r1s1-1b", "claude-steals8-r1s1-1a"):
            with self.assertRaises(SystemExit):
                self.create(label=label, yes=True)
        self.assertEqual(self.calls, [])

    def test_image_and_machine_filters(self) -> None:
        self.assertEqual(rent.IMAGE, "pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel")
        seen = {}
        with mock.patch.object(rent, "call", lambda m, p, b=None, timeout=60: seen.update(q=b) or {"offers": []}):
            rent.search(Ns(n=3, max_dph=0.8))
        q = seen["q"]
        self.assertEqual(q["type"], "on-demand")
        self.assertEqual(q["gpu_name"], {"eq": "RTX 5090"})
        self.assertEqual(q["reliability"], {"gte": 0.98})
        self.assertEqual(q["cpu_cores_effective"], {"gte": 8})
        self.assertEqual(q["disk_space"], {"gte": 60})
        self.assertEqual(q["verified"], {"eq": True})

    # -- pull and destroy
    @staticmethod
    def tgz(files: dict) -> bytes:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as t:
            for n, b in files.items():
                i = tarfile.TarInfo(n)
                i.size = len(b)
                t.addfile(i, io.BytesIO(b))
        return buf.getvalue()

    def fake_box(self, tamper=False, status="DONE rc=0", inner=True, ckpt=False, stages=("1a", "1b")):
        """What /job/export and /job/b64 hold after a run: out.tar.gz holding the stage dirs 1a and 1b, each with a
        runner manifest (and, with `ckpt`, ckpt.tar.gz holding <stage>/ckpt/, which the manifest lists)."""
        files, weights = {}, {}
        for d in stages:
            files.update({f"{d}/RESULT.json": b'{"x": 1}', f"{d}/log.txt": b"hello\n"})
            if ckpt:
                weights[f"{d}/ckpt/A0-s0/state.pt"] = b"weights-" + d.encode()
        for d in stages:
            listed = {n: b for n, b in {**files, **weights}.items() if n.startswith(d + "/")}
            files[f"{d}/MANIFEST.sha256"] = "".join(f"{sh(b)}  {n[3:]}\n" for n, b in listed.items()).encode()
            if not inner:
                del files[f"{d}/MANIFEST.sha256"]
        tar = self.tgz(files)
        b64 = base64.encodebytes(tar)
        half = len(b64) // 2
        parts = {"big/out.tar.gz.b64.p000": b64, "small/out.tar.gz.b64.p000": b64[:half],
                 "small/out.tar.gz.b64.p001": b64[half:]}
        if tamper:
            parts["big/out.tar.gz.b64.p000"] = base64.encodebytes(tar[:-5] + b"xxxxx")
            parts["small/out.tar.gz.b64.p000"] = base64.encodebytes(tar[:-5] + b"xxxxx")
            parts.pop("small/out.tar.gz.b64.p001")
        manifest = f"{sh(tar)}  out.tar.gz\n"
        if ckpt:
            ctar = self.tgz(weights)
            parts["big/ckpt.tar.gz.b64.p000"] = base64.encodebytes(ctar)
            manifest += f"{sh(ctar)}  ckpt.tar.gz\n"
        sizes = "".join(f"{len(b)} {p}\n" for p, b in parts.items()) + "999 total\n"
        box = {"/job/export/MANIFEST.sha256": manifest.encode(),
               "/job/export/PARTS.txt": sizes.encode(), "/job/export/STATUS.txt": (status + "\n").encode()}
        box.update({f"/job/b64/{p}": b for p, b in parts.items()})
        return box

    def pull(self, box):
        run = Path(self.tmp.name) / "run"
        ns = Ns(id="7", out=str(run))
        self.read_paths = []

        def cat(i, path, tries=3):
            self.read_paths.append(path)
            return box.get(path)
        with mock.patch.object(rent, "exec_cat", cat), mock.patch("builtins.print"):
            try:
                rent.pull(ns)
                ok = True
            except SystemExit:
                ok = False
        return run, ok

    def destroy(self, **kw):
        ns = Ns(id="7", pulled=kw.get("pulled"), abandon=kw.get("abandon", False))
        with mock.patch("builtins.print") as pr:
            rent.destroy(ns)
        return pr

    def test_pull_ok_writes_marker_and_extracts_both_stages(self) -> None:
        self.instances = [{"id": 7, "label": LABEL, "actual_status": "stopped"}]   # waitlog already stopped it
        run, ok = self.pull(self.fake_box())
        self.assertTrue(ok)
        self.assertEqual(json.loads((run / rent.PULL_OK).read_text())["id"], 7)
        self.assertEqual((run / "1a" / "log.txt").read_bytes(), b"hello\n")
        self.assertEqual((run / "1b" / "log.txt").read_bytes(), b"hello\n")
        self.assertEqual(self.calls, [("GET", "/instances/7/")])   # a status read; the box is read through exec_cat
        self.assertEqual(self.read_paths[0], "/job/export/STATUS.txt")        # STATUS is read first

    def test_pull_refuses_an_unfinished_job(self) -> None:
        self.instances = [{"id": 7, "label": LABEL, "actual_status": "running"}]
        run, ok = self.pull(self.fake_box(status=""))
        self.assertFalse(ok)
        self.assertEqual(self.read_paths, ["/job/export/STATUS.txt"])
        self.assertFalse(any(m == "PUT" for m, _ in self.calls))              # the box was not even stopped
        self.assertFalse((run / rent.PULL_OK).exists())
        run, ok = self.pull({})                                               # nothing readable at all
        self.assertFalse(ok)
        self.assertFalse(any(m == "PUT" for m, _ in self.calls))

    def test_pull_stops_a_running_instance_and_waits_for_the_stop(self) -> None:
        self.instances = [{"id": 7, "label": LABEL, "actual_status": "running"}]
        self.stop_after = 3                                                   # three more polls still say running
        box = self.fake_box()
        seen = []

        def cat(i, path, tries=3):
            seen.append((path, self.stop_requested, self.stop_after))
            return box.get(path)
        run = Path(self.tmp.name) / "run"
        with mock.patch.object(rent, "exec_cat", cat), mock.patch("builtins.print"):
            rent.pull(Ns(id="7", out=str(run)))
        self.assertTrue((run / rent.PULL_OK).exists())
        seq = [c for c in self.calls if c[1] == "/instances/7/"]
        self.assertEqual(seq[:2], [("GET", "/instances/7/"), ("PUT", "/instances/7/")])
        self.assertEqual(seq.count(("GET", "/instances/7/")), 1 + 4)         # the first look, then 3 running + 1 exited
        self.assertGreaterEqual(self.sleep_mock.call_count, 3)               # it slept between polls
        parts_read = [s for s in seen if s[0] != "/job/export/STATUS.txt"]
        self.assertTrue(all(stopped and left == 0 for _, stopped, left in parts_read))   # parts read after the stop
        self.assertEqual(seen[0][0], "/job/export/STATUS.txt")

    def test_status_is_written_after_the_parts(self) -> None:
        job = self.args()[2]
        self.assertLess(job.index("> export/PARTS.txt"), job.index("> export/STATUS.txt"))

    def test_a_dry_run_box_passes_its_pull(self) -> None:
        self.instances = [{"id": 7, "label": LABEL, "actual_status": "stopped"}]
        run, ok = self.pull(self.fake_box(status="DONE rc=na dryrun=1", stages=()))
        self.assertTrue(ok)
        run, ok = self.pull(self.fake_box(status="DONE rc=0", stages=()))      # a real DONE without out/ dirs fails
        self.assertFalse(ok)

    def test_pull_keeps_asking_until_the_stop_is_confirmed(self) -> None:
        self.instances = [{"id": 7, "label": LABEL, "actual_status": "running"}]
        self.stop_after = 20                                                  # 20 polls still say running
        run, ok = self.pull(self.fake_box())
        self.assertTrue(ok)
        puts = [c for c in self.calls if c == ("PUT", "/instances/7/")]
        self.assertGreaterEqual(len(puts), 4)                                 # the stop request is repeated
        self.assertEqual(self.read_paths[0], "/job/export/STATUS.txt")
        self.assertTrue((run / rent.PULL_OK).exists())

    def test_pull_needs_the_checkpoints_when_exported(self) -> None:
        box = self.fake_box(ckpt=True)
        run, ok = self.pull(box)
        self.assertTrue(ok)
        self.assertEqual((run / "1a" / "ckpt" / "A0-s0" / "state.pt").read_bytes(), b"weights-1a")
        self.assertEqual((run / "1b" / "ckpt" / "A0-s0" / "state.pt").read_bytes(), b"weights-1b")
        self.assertIn("ckpt.tar.gz", json.loads((run / rent.PULL_OK).read_text())["files"])
        broken = self.fake_box(ckpt=True)
        for p in [p for p in broken if "ckpt.tar.gz.b64" in p]:
            broken[p] = b"garbage"
        run, ok = self.pull(broken)
        self.assertFalse(ok)
        self.assertFalse((run / rent.PULL_OK).exists())

    def test_pull_with_a_bad_hash_leaves_no_marker(self) -> None:
        run, ok = self.pull(self.fake_box(tamper=True))
        self.assertFalse(ok)
        self.assertFalse((run / rent.PULL_OK).exists())

    def test_pull_with_missing_inner_manifest_on_a_done_job_fails(self) -> None:
        run, ok = self.pull(self.fake_box(inner=False))
        self.assertFalse(ok)
        self.assertFalse((run / rent.PULL_OK).exists())
        run, ok = self.pull(self.fake_box(inner=False, status="FAIL rc=1"))   # a failed job may lack the manifest
        self.assertTrue(ok)
        run, ok = self.pull(self.fake_box(stages=("1a",)))                    # DONE needs both stages' manifests
        self.assertFalse(ok)
        run, ok = self.pull(self.fake_box(stages=("1a",), status="GATE rc=3"))    # a GATE stop has only 1a
        self.assertTrue(ok)

    def test_pull_with_a_changed_inner_file_fails(self) -> None:
        box = self.fake_box()
        run, _ = self.pull(box)
        for stage in ("1a", "1b"):
            (run / stage / "log.txt").write_bytes(b"changed")
        found, bad = rent.inner_check(run)
        self.assertTrue(found)
        self.assertEqual(bad, ["1a/log.txt", "1b/log.txt"])                   # every manifest is checked

    def test_destroy_refuses_until_a_pull_passed(self) -> None:
        self.instances = [{"id": 7, "label": LABEL}]
        with self.assertRaises(SystemExit):
            self.destroy()                                        # no --pulled
        run, _ = self.pull(self.fake_box(tamper=True))            # a failed pull
        before = list(self.calls)
        with self.assertRaises(SystemExit):
            self.destroy(pulled=str(run))
        self.assertEqual(self.calls, before)                      # refused before any request
        run, _ = self.pull(self.fake_box())
        (run / rent.PULL_OK).write_text(json.dumps({"id": 8, "ok": True}))   # a pull of another instance
        with self.assertRaises(SystemExit):
            self.destroy(pulled=str(run))
        self.assertFalse(any(m == "DELETE" for m, _ in self.calls))
        run, _ = self.pull(self.fake_box())                       # passed pull
        self.destroy(pulled=str(run))
        self.assertIn(("DELETE", "/instances/7/"), self.calls)
        self.assertEqual(self.instances, [])

    def test_destroy_refuses_a_foreign_label(self) -> None:
        self.instances = [{"id": 7, "label": "ben-own-job"}]
        run, _ = self.pull(self.fake_box())
        with self.assertRaises(SystemExit):
            self.destroy(pulled=str(run))
        self.assertFalse(any(m == "DELETE" for m, _ in self.calls))
        with self.assertRaises(SystemExit):
            self.destroy(abandon=True)
        self.assertFalse(any(m == "DELETE" for m, _ in self.calls))

    def test_destroy_abandon_for_a_never_started_instance(self) -> None:
        self.instances = [{"id": 7, "label": LABEL}]
        self.destroy(abandon=True)
        self.assertIn(("DELETE", "/instances/7/"), self.calls)


FAKE_RUNNER = r'''#!/usr/bin/env python3
"""A stand-in for scripts/premonition_steals_r1_stage1.py: build / run / price / verify write plausible files."""
import hashlib, json, os, sys
from pathlib import Path

argv = sys.argv[1:]
cmd = argv[0]


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def log(line):
    with open(os.environ["FAKE_LOG"], "a") as f:
        f.write(line + "\n")


def manifest(out):
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}"
             for p in sorted(out.rglob("*")) if p.is_file() and p.name != "MANIFEST.sha256"]
    (out / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")


if cmd == "build":
    log("build")
    rc = int(os.environ.get("FAKE_BUILD_RC", "0"))
    if rc:
        print("build broke", file=sys.stderr)
        sys.exit(rc)
    print("building the village ...")
    print(json.dumps({"data_rel": "data/v", "tag": "t", "seconds": 1}))
elif cmd == "run":
    out = Path(opt("--out"))
    timing = "--timing" in argv
    log("run 1a --timing" if timing else f"run 1b --price {Path(opt('--price')).name}")
    out.mkdir(parents=True, exist_ok=True)
    if not timing:
        if not Path(opt("--price")).is_file() or not (out / "SEAL.sha256.txt").is_file():
            print("1b needs the price file and the seal in its directory", file=sys.stderr)
            sys.exit(9)
    if not timing and os.environ.get("FAKE_RUN_1B_SLEEP"):         # a 1b run that hangs past the wall
        import time
        time.sleep(float(os.environ["FAKE_RUN_1B_SLEEP"]))
        Path(os.environ["FAKE_LOG"] + ".slept-through").write_text("1b outlived the wall\n")
    rc = int(os.environ.get("FAKE_RUN_1A_RC" if timing else "FAKE_RUN_1B_RC", "0"))
    if rc:
        sys.exit(rc)
    for arm in ("A0", "A1"):
        (out / f"{arm}-s0.json").write_text(json.dumps({"arm": arm}))
    (out / "log.txt").write_text("log\n")
    (out / "ckpt" / "A0-s0").mkdir(parents=True)
    (out / "ckpt" / "A0-s0" / "state.pt").write_bytes(b"weights")
    (out / "RESULT.json").write_text("{}")
    (out / "RUN-NOTE.md").write_text("Verdict: **PASS**\n")
    manifest(out)
    print(out / "MANIFEST.sha256")
elif cmd == "price":
    log(f"price spent={opt('--spent-seconds')} dph={opt('--dph')}")
    rc = int(os.environ.get("FAKE_PRICE_RC", "0"))
    if rc:
        print("price says no", file=sys.stderr)
        sys.exit(rc)
    result = {"flop_budget": 1e16, "dph": float(opt("--dph"))}
    Path(opt("--out")).write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
elif cmd == "verify":
    out = Path(opt("--out"))
    log(f"verify {out.name}")
    bad = []
    for line in (out / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if not (out / name).is_file() or hashlib.sha256((out / name).read_bytes()).hexdigest() != digest:
            bad.append(name)
    print("manifest OK" if not bad else f"MISSING OR CHANGED: {bad}")
    sys.exit(1 if bad else 0)
else:
    sys.exit(64)
'''


class JobE2ETest(Fixture):
    """The generated job script, run locally in a temp JOBDIR with stubs on PATH, PY = this python and RUNNER = a fake
    runner. No sleep of 300 s or more is real; the TICK loop is killed by finish()."""

    def setUp(self) -> None:
        super().setUp()
        base = Path(self.tmp.name)
        self.jobdir, self.stubs, self.log = base / "job", base / "stubs", base / "fake.log"
        self.stubs.mkdir()
        real_sleep = shutil.which("sleep")
        self.stub("nvidia-smi", 'case "$*" in *memory.used*) echo 0;; *) echo "FakeGPU, 32607 MiB, 570.00";; esac')
        self.stub("pip", 'echo "pip $*" >> "$FAKE_LOG"; exit 0')
        self.stub("sleep", f'if [ "${{1%.*}}" -ge 300 ] 2>/dev/null; then echo "sleep $1" >> "$FAKE_LOG"; exit 0; fi\n'
                           f'exec {real_sleep} "$@"')
        torch = base / "fake_torch" / "torch"
        torch.mkdir(parents=True)
        (torch / "__init__.py").write_text(
            "import types\n__version__ = '2.11.0'\nversion = types.SimpleNamespace(cuda='12.8')\n"
            "cuda = types.SimpleNamespace(is_available=lambda: True, get_device_name=lambda i: 'FakeGPU')\n")
        self.runner = base / "fake_runner.py"
        self.runner.write_text(FAKE_RUNNER)
        self.pack(dph=0.45, torch="none")

    def stub(self, name: str, body: str) -> None:
        path = self.stubs / name
        path.write_text("#!/bin/bash\n" + body + "\n")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def run_job(self, box_start=None, keep_ledger=False, **env_extra):
        """Run the job as `create` would send it: BOX_START set to `box_start` (default: now). The box ledger sits one
        level above JOBDIR; it is removed first unless `keep_ledger` (a restart of the same box)."""
        if not keep_ledger:
            (self.jobdir.parent / "r1s1-box-ledger.json").unlink(missing_ok=True)
        env = {k: v for k, v in os.environ.items() if k not in ("DRYRUN", "RUNNER", "PY", "JOBDIR")}
        env.update(PATH=f"{self.stubs}:{os.environ['PATH']}", JOBDIR=str(self.jobdir), PY=sys.executable,
                   RUNNER=str(self.runner), TICK_S="1", FAKE_LOG=str(self.log), PYTHONDONTWRITEBYTECODE="1",
                   PYTHONPATH=str(Path(self.tmp.name) / "fake_torch"))
        env.update({k: str(v) for k, v in env_extra.items()})
        args = self.args()
        args[2] = rent.with_box_start(args[2], int(time.time()) if box_start is None else box_start)
        outfile = Path(self.tmp.name) / "job.out"
        with outfile.open("wb") as fh:                    # a file, not a pipe: an orphaned stub sleep cannot hold it
            r = subprocess.run(["bash", "-c", args[2], args[3], *args[4:]], env=env, stdout=fh,
                               stderr=subprocess.STDOUT, timeout=180, stdin=subprocess.DEVNULL)
        return r.returncode, outfile.read_text(errors="replace")

    def calls(self) -> list:
        return [ln for ln in self.log.read_text().splitlines() if not ln.startswith(("sleep", "pip"))]

    def export(self) -> Path:
        return self.jobdir / "export"

    def test_done_path(self) -> None:
        rc, text = self.run_job()
        self.assertEqual(rc, 0, text[-3000:])
        exp = self.export()
        self.assertEqual((exp / "STATUS.txt").read_text().split()[0], "DONE")
        self.assertTrue((exp / "out.tar.gz").is_file())
        check = subprocess.run(["sha256sum", "-c", "MANIFEST.sha256"], cwd=exp, capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn("out.tar.gz", (exp / "MANIFEST.sha256").read_text())
        with tarfile.open(exp / "out.tar.gz") as t:
            names = set(t.getnames())
        for f in ("1a/MANIFEST.sha256", "1b/MANIFEST.sha256", "1b/PRICE.json", "1b/SEAL.sha256.txt", "1b/RESULT.json",
                  "checks/gpu.txt"):
            self.assertIn(f, names)
        self.assertFalse([n for n in names if "ckpt" in n])
        with tarfile.open(exp / "ckpt.tar.gz") as t:
            self.assertEqual({n for n in t.getnames() if n.endswith(".pt")},
                             {"1a/ckpt/A0-s0/state.pt", "1b/ckpt/A0-s0/state.pt"})
        # build -> 1a -> price -> 1b -> verify, in that order, and nothing else
        self.assertEqual([c.split(" spent=")[0] for c in self.calls()],
                         ["build", "run 1a --timing", "price", "run 1b --price PRICE.json", "verify 1a", "verify 1b"])
        self.assertIn("sleep 600", self.log.read_text())             # the closing sleep, not 3600
        # the log: PRICE with its sha256, then the file; the closing mark last; SPENT counts the pre-job allowance
        price = (self.jobdir / "tree/out/1b/PRICE.json").read_bytes()
        self.assertIn(f"=== PRICE {sh(price)}", text)
        self.assertLess(text.index(f"=== PRICE {sh(price)}"), text.index('"flop_budget"'))
        spent = int(next(c for c in self.calls() if c.startswith("price")).split("spent=")[1].split()[0])
        self.assertTrue(0 <= spent < 120, spent)                       # billed since BOX_START (create = now here)
        marks = rent.closing_marks(text.splitlines())
        self.assertEqual([len(marks[k]) for k in ("DONE", "FAIL", "GATE")], [1, 0, 0])
        self.assertLess(text.index("=== MANIFEST"), text.index("=== R1S1 DONE"))
        self.assertIn("RUN 1a timing, at most 2400 s", text)
        self.assertIn("Verdict: **PASS**", text)

    def test_price_exit_3_and_4_end_in_a_gate_without_1b(self) -> None:
        for code in (3, 4):
            with self.subTest(code=code):
                shutil.rmtree(self.jobdir, ignore_errors=True)
                self.log.unlink(missing_ok=True)
                rc, text = self.run_job(FAKE_PRICE_RC=code)
                self.assertEqual(rc, 0, text[-3000:])
                self.assertEqual((self.export() / "STATUS.txt").read_text().strip(), f"GATE rc={code}")
                self.assertTrue((self.export() / "out.tar.gz").is_file())
                self.assertEqual([c.split(" spent=")[0] for c in self.calls()], ["build", "run 1a --timing", "price"])
                self.assertNotIn("run 1b", self.log.read_text())
                self.assertIn(f"=== R1S1 GATE-STOP {code}", text)
                marks = rent.closing_marks(text.splitlines())
                self.assertEqual([len(marks[k]) for k in ("DONE", "FAIL", "GATE")], [0, 0, 1])   # N1: GATE-STOP is early
                self.assertLess(text.index("GATE-STOP"), text.index("=== MANIFEST"))
                with tarfile.open(self.export() / "out.tar.gz") as t:
                    self.assertIn("1a/MANIFEST.sha256", t.getnames())

    def test_other_price_errors_and_early_failures_fail(self) -> None:
        for env, status, early in ((dict(FAKE_PRICE_RC=1), "FAIL", "price rc=1"), (dict(FAKE_BUILD_RC=1), "FAIL", "build"),
                                   (dict(FAKE_RUN_1A_RC=5), "FAIL", "1a run rc=5"),
                                   (dict(FAKE_RUN_1B_RC=7), "FAIL", "1b run rc=7")):
            with self.subTest(env=env):
                shutil.rmtree(self.jobdir, ignore_errors=True)
                self.log.unlink(missing_ok=True)
                rc, text = self.run_job(**env)
                self.assertEqual(rc, 0, text[-3000:])
                self.assertEqual((self.export() / "STATUS.txt").read_text().split()[0], status)
                self.assertIn(f"=== R1S1-FAIL {early}", text)
                marks = rent.closing_marks(text.splitlines())
                self.assertEqual([len(marks[k]) for k in ("DONE", "FAIL", "GATE")], [0, 1, 0])   # one closing mark
                self.assertLess(text.index("=== R1S1-FAIL"), text.index("=== MANIFEST"))

    def test_a_tampered_pack_fails_at_setup(self) -> None:
        args = self.args()
        args[4] = ("A" if args[4][0] != "A" else "B") + args[4][1:]
        (self.out / "args.json").write_text(json.dumps(args))
        rc, text = self.run_job()
        self.assertIn("=== R1S1-FAIL pack sha256", text)
        self.assertEqual(self.calls() if self.log.exists() else [], [])

    def test_the_box_ends_by_its_wall_with_no_watcher(self) -> None:
        """Coordinator's on-box self-stop test: waitlog and the session are gone, 1b hangs. The wall kills the job,
        the wrapper asks Vast to stop the instance with the container's own key, and exits (ending the container)."""
        self.stub("curl", 'echo "curl $*" >> "$FAKE_LOG"; echo \'{"success": true}\'')
        started = time.time()
        rc, text = self.run_job(WALL_S_TEST=6, FAKE_RUN_1B_SLEEP=60, CONTAINER_ID=7, CONTAINER_API_KEY="k")
        elapsed = time.time() - started
        self.assertEqual(rc, 0, text[-3000:])
        self.assertLess(elapsed, 45, text[-2000:])                       # the wall (6 s), not the 60 s hang
        self.assertIn("=== R1S1 WALL 6 s", text)
        self.assertIn("=== R1S1 SELF-STOP wall deadline rc=124", text)
        self.assertIn("=== R1S1 SELF-STOP accepted (try 1)", text)
        curl = [ln for ln in self.log.read_text().splitlines() if ln.startswith("curl ")]
        self.assertEqual(len(curl), 1)
        self.assertIn("-X PUT", curl[0])
        self.assertIn('{"state": "stopped"}', curl[0])
        self.assertIn("https://console.vast.ai/api/v0/instances/7/", curl[0])
        self.assertIn("Authorization: Bearer k", curl[0])
        time.sleep(2)
        self.assertFalse(Path(str(self.log) + ".slept-through").exists())   # the hung runner was killed, not orphaned
        self.assertFalse(rent.closing_marks(text.splitlines())["DONE"])

    def test_the_wall_cannot_be_lengthened_and_a_normal_end_also_self_stops(self) -> None:
        self.stub("curl", 'echo "curl $*" >> "$FAKE_LOG"; echo \'{"success": true}\'')
        rc, text = self.run_job(WALL_S_TEST=10 ** 9, CONTAINER_ID=7, CONTAINER_API_KEY="k")
        self.assertEqual(rc, 0, text[-3000:])
        wall = rent.wall_seconds(0.45)
        shown = int(re.search(r"=== R1S1 WALL (\d+) s", text).group(1))
        self.assertTrue(wall - 5 <= shown <= wall, shown)                # the test override can only shorten it
        self.assertNotIn("SELF-STOP wall deadline", text)
        self.assertIn("=== R1S1 SELF-STOP accepted (try 1)", text)       # a finished job asks for the stop as well
        self.assertLess(text.index("=== R1S1 DONE"), text.index("=== R1S1 SELF-STOP accepted"))
        shutil.rmtree(self.jobdir)
        rc, text = self.run_job()                                       # outside Vast: no key, exiting ends the box
        self.assertIn("=== R1S1 SELF-STOP no container key", text)

    def test_a_restart_never_reruns_the_job(self) -> None:
        self.stub("curl", 'echo "curl $*" >> "$FAKE_LOG"; echo \'{"success": true}\'')
        rc, text = self.run_job(CONTAINER_ID=7, CONTAINER_API_KEY="k")
        self.assertIn("=== R1S1 DONE", text)
        ledger = json.loads((self.jobdir.parent / "r1s1-box-ledger.json").read_text())
        self.assertEqual(set(ledger), {"box_start", "dph", "cap", "job_start", "wall_end"})
        before = self.log.read_text()
        rc, text = self.run_job(keep_ledger=True, CONTAINER_ID=7, CONTAINER_API_KEY="k")   # the container restarts
        self.assertIn("=== R1S1 RESTART-REFUSED", text)
        self.assertIn("=== R1S1 SELF-STOP accepted", text)
        new = self.log.read_text()[len(before):]
        self.assertNotIn("build", new)                                   # nothing reran
        self.assertEqual([ln for ln in new.splitlines() if ln.startswith("curl ")][0].count("-X PUT"), 1)

    def test_the_wall_counts_from_box_start(self) -> None:
        wall = rent.wall_seconds(0.45)
        rc, text = self.run_job(box_start=int(time.time()) - wall + 30)    # 30 s of money left: refused
        self.assertIn("=== R1S1 REFUSED: no money left", text)
        self.assertNotIn("build", self.log.read_text() if self.log.exists() else "")
        rc, text = self.run_job(box_start=int(time.time()) + 3600)          # a BOX_START in the future
        self.assertIn("=== R1S1 REFUSED: BOX_START", text)

    def test_a_refused_self_stop_is_retried_and_reported(self) -> None:
        self.stub("curl", 'echo "curl $*" >> "$FAKE_LOG"; echo \'{"success": false, "error": "auth"}\'')
        rc, text = self.run_job(CONTAINER_ID=7, CONTAINER_API_KEY="k")
        self.assertEqual(text.count("=== R1S1 SELF-STOP refused or failed"), 5)
        self.assertNotIn("SELF-STOP accepted", text)

    def test_wall_arithmetic(self) -> None:
        self.assertEqual(rent.wall_seconds(0.45), int(0.95 * 2.80 / 0.45 * 3600))             # from BOX_START
        for dph in (0.3, 0.45, 0.8):
            self.assertGreaterEqual(rent.wall_seconds(dph), rent.deadline_seconds(dph) + rent.EXPORT_SECONDS)
            self.assertLessEqual(rent.wall_seconds(dph) / 3600 * dph, 0.95 * 2.80 + 1e-9)

    def test_dryrun_stops_after_setup(self) -> None:
        rc, text = self.run_job(DRYRUN=1)
        self.assertIn("DRYRUN stop", text)
        self.assertEqual((self.export() / "STATUS.txt").read_text().split()[0], "DONE")
        self.assertEqual(self.calls() if self.log.exists() else [], [])


class RunnerAgreementTest(unittest.TestCase):
    def test_package_name_matches_the_runner(self) -> None:
        runner = SCRIPT.parent / "premonition_steals_r1_stage1.py"
        text = runner.read_text()
        self.assertIn(f'PACKAGE = "{rent.PACKAGE}"', text)
        self.assertIn('(ROOT / "premonition").glob("*.py")', text)
        self.assertIn('(ROOT / "learnlab").rglob("*.py")', text)
        self.assertIn('(ROOT / "memorylab").rglob("*.py")', text)


class NetworkFailureTest(unittest.TestCase):
    """The coordinator's B-b test: socket and proxy failures on every kind of request, including the stop itself;
    waitlog still ends with the box stopped, confirmed by Vast."""

    def test_the_box_is_stopped_through_network_failures(self) -> None:
        import socket
        import urllib.error
        state = {"stopped": False, "stop_puts": 0, "n": 0}
        failures = [socket.timeout("timed out"), urllib.error.URLError("proxy: 502 Bad Gateway"),
                    ConnectionResetError(104, "Connection reset by peer"), OSError("Tunnel connection failed: 407")]

        class Reply(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def urlopen(req, timeout=60):
            state["n"] += 1
            url = req if isinstance(req, str) else req.full_url
            method = "GET" if isinstance(req, str) else req.get_method()
            if state["n"] % 3 == 0:                                         # every third request fails somehow
                raise failures[state["n"] % len(failures)]
            if url.endswith("/instances/request_logs/7/"):
                return Reply(json.dumps({"result_url": "https://logs.example/7"}).encode())
            if url == "https://logs.example/7":
                return Reply(b"=== R1S1 START\n=== MANIFEST\n=== R1S1 DONE 2026-10-20T12:00:00Z\n")
            if method == "PUT" and url.endswith("/instances/7/"):
                state["stop_puts"] += 1
                if state["stop_puts"] <= 2:                                   # the first two stops are lost
                    raise urllib.error.URLError("proxy: connection refused")
                state["stopped"] = True
                return Reply(b'{"success": true}')
            if method == "GET" and url.endswith("/instances/7/"):
                status = "stopped" if state["stopped"] else "running"
                return Reply(json.dumps({"instances": [{"id": 7, "label": LABEL, "actual_status": status,
                                                        "dph_total": 0.45, "start_date": time.time() - 3600}]}).encode())
            raise AssertionError(f"unexpected request {method} {url}")

        ns = Ns(id="7", stage=None, max_min=None, poll=0)
        with mock.patch("urllib.request.urlopen", urlopen), mock.patch.object(rent.time, "sleep"), \
                mock.patch("builtins.print") as pr, mock.patch("sys.stderr", io.StringIO()), \
                self.assertRaises(SystemExit) as cm:
            rent.waitlog(ns)
        out = json.loads(pr.call_args[0][0])
        self.assertEqual((cm.exception.code, out["event"]), (0, "DONE"))
        self.assertTrue(state["stopped"])
        self.assertGreaterEqual(state["stop_puts"], 3)                        # retried past the lost requests
        self.assertTrue(out["stopped"]["confirmed"])

    def test_call_never_raises_on_network_errors(self) -> None:
        import socket
        import urllib.error
        for error in (socket.timeout("t"), urllib.error.URLError("proxy"), ConnectionResetError(), OSError("x"),
                      ValueError("bad json")):
            with mock.patch("urllib.request.urlopen", side_effect=error):
                r = rent.call("GET", "/instances/7/")
            self.assertEqual((r["success"], r["error"]), (False, type(error).__name__))
        with mock.patch("urllib.request.urlopen", side_effect=socket.timeout("t")):
            self.assertIsNone(rent.inst(7))                                   # unknown, not "gone"


if __name__ == "__main__":
    unittest.main()
