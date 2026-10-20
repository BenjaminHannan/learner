"""Offline tests for scripts/claude_r1s1_rent.py (R1 stage 1 rental controller). No network: urlopen is made to fail
and the controller's HTTP functions are mocked. Run: python3 -B -m unittest tests.test_claude_r1s1_rent"""
from __future__ import annotations

import base64
import importlib.util
import io
import json
import subprocess
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
PRICE_REL = rent.PRICE_DEFAULT


def sh(b: bytes) -> str:
    return rent.sha(b)


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
            "premonition/a.py": "A = 1\n", "learnlab/b.py": "B = 2\n", "memorylab/c.py": "C = 3\n",
            rent.RUNNER: "print('runner')\n", rent.CARD: "# card\n",
            "data/tokenizer/premonition-tok-v2.json": "{}\n", "data/english/raw/r.jsonl": "{}\n",
            "data/village/patterns/p.json": "[]\n", "tests/ignored.py": "x\n"}
        for name, text in self.files.items():
            self.write(name, text)
        self.write(SEAL_REL, self.seal_text())
        self.write(PRICE_REL, '{"flop_budget": 1.2e16}\n')
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
        return "".join(f"{sh((self.repo / f).read_bytes())}  {f}\n" for f in (rent.CARD, rent.RUNNER))

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       check=True, capture_output=True)

    def commit(self, msg: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def pack(self, stage: str, **kw) -> dict:
        ns = Ns(stage=stage, flop_budget=kw.get("flop_budget"), seal=kw.get("seal", SEAL_REL),
                price=kw.get("price", PRICE_REL), torch=rent.TORCH_PIN,
                allow_dirty=kw.get("allow_dirty", False), out=str(self.out))
        with mock.patch("builtins.print") as pr:
            rent.pack(ns)
        return json.loads(pr.call_args[0][0])

    def args(self) -> list:
        return json.loads((self.out / "args.json").read_text())

    def members(self) -> set:
        with tarfile.open(self.out / "pack.tar.xz", "r:xz") as t:
            return set(t.getnames())


class PackTest(Fixture):
    def test_1a_contents_and_job(self) -> None:
        info = self.pack("1a", flop_budget=3.15e16)
        names = self.members()
        for f in ("premonition/a.py", "learnlab/b.py", "memorylab/c.py", rent.RUNNER, rent.CARD,
                  "data/tokenizer/premonition-tok-v2.json", "data/english/raw/r.jsonl",
                  "data/village/patterns/p.json", "SEAL-pack.sha256.txt"):
            self.assertIn(f, names)
        self.assertNotIn("tests/ignored.py", names)
        self.assertNotIn(SEAL_REL, names)                    # 1a carries no seal and no price
        self.assertNotIn(PRICE_REL, names)
        args = self.args()
        self.assertEqual(args[:2], ["bash", "-c"])
        self.assertEqual(rent.job_stage(args), "1a")
        joined = base64.b64decode("".join(args[4:]))
        self.assertEqual(sh(joined), info["pack_sha256"])
        self.assertIn(f"PACK_SHA={info['pack_sha256']}", args[2])
        job = args[2]
        self.assertIn("--flop-budget 3.15e+16 --unsealed --seeds 0", job)
        self.assertNotIn("cp \"$ROOT/", job)                 # no seal copy

    def test_1a_needs_flop_budget(self) -> None:
        with self.assertRaises(SystemExit):
            self.pack("1a")
        self.assertFalse(self.out.exists())

    def test_1b_refuses_flop_budget_and_dirty(self) -> None:
        with self.assertRaises(SystemExit):
            self.pack("1b", flop_budget=1e16)
        with self.assertRaises(SystemExit):
            self.pack("1b", allow_dirty=True)

    def test_1b_needs_card_and_seal(self) -> None:
        self.git("rm", "-q", SEAL_REL)
        self.commit("no seal")
        with self.assertRaises(SystemExit) as cm:
            self.pack("1b")
        self.assertIn("does not exist", str(cm.exception))
        self.write(SEAL_REL, self.seal_text())
        self.git("rm", "-q", rent.CARD)
        self.commit("no card")
        with self.assertRaises(SystemExit):
            self.pack("1b")

    def test_1b_needs_a_committed_price(self) -> None:
        self.git("rm", "-q", PRICE_REL)
        self.commit("no price")
        with self.assertRaises(SystemExit):
            self.pack("1b")
        self.write(PRICE_REL, "{}\n")                       # no F in it
        self.commit("empty price")
        with self.assertRaises(SystemExit):
            self.pack("1b")
        self.write(PRICE_REL, '{"flop_budget": 1e16}\n')    # not committed
        with self.assertRaises(SystemExit):
            self.pack("1b")

    def test_1b_refuses_a_mismatched_seal(self) -> None:
        self.write(rent.CARD, "# card changed after the seal\n")
        self.commit("card edited")
        with self.assertRaises(SystemExit) as cm:
            self.pack("1b")
        self.assertIn("does not match", str(cm.exception))
        self.write(SEAL_REL, self.seal_text())               # reseal the card, then break the runner instead
        self.write(rent.RUNNER, "print('edited runner')\n")
        self.commit("runner edited")
        with self.assertRaises(SystemExit):
            self.pack("1b")
        self.assertFalse(self.out.exists())

    def test_1b_refuses_an_uncommitted_card(self) -> None:
        self.write(rent.CARD, "# edited, not committed\n")
        self.write(SEAL_REL, self.seal_text())               # seal matches the working file but HEAD differs
        with self.assertRaises(SystemExit):
            self.pack("1b")

    def test_1b_ok(self) -> None:
        self.pack("1b")
        self.assertIn(SEAL_REL, self.members())
        self.assertIn(PRICE_REL, self.members())
        job = self.args()[2]
        self.assertEqual(rent.job_stage(self.args()), "1b")
        self.assertIn(f'--seeds 0 1 2 --price "$ROOT/{PRICE_REL}"', job)
        self.assertNotIn("--flop-budget", job)
        self.assertNotIn("--unsealed", job)
        self.assertIn(f'cp "$ROOT/{SEAL_REL}" "$OUT/SEAL.sha256.txt"', job)

    def test_dirty_tree_refused_unless_1a_allows_it(self) -> None:
        self.write("premonition/a.py", "A = 99\n")
        with self.assertRaises(SystemExit):
            self.pack("1a", flop_budget=1e16)
        info = self.pack("1a", flop_budget=1e16, allow_dirty=True)
        self.assertEqual(info["dirty"], ["premonition/a.py"])

    def test_untracked_runner_refused(self) -> None:
        self.git("rm", "-q", "--cached", rent.RUNNER)
        self.git("commit", "-q", "-m", "untrack runner")
        with self.assertRaises(SystemExit):
            self.pack("1a", flop_budget=1e16)


class JobTextTest(Fixture):
    def job(self, stage: str, **kw) -> str:
        self.pack(stage, **kw)
        return self.args()[2]

    def test_bash_syntax(self) -> None:
        for stage, kw in (("1a", {"flop_budget": 1e16}), ("1b", {})):
            job = self.job(stage, **kw)
            r = subprocess.run(["bash", "-n"], input=job, text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_build_then_run_then_done(self) -> None:
        job = self.job("1a", flop_budget=1e16)
        build = job.index('$RUNNER build --root "$ROOT" --workers "$(nproc)"')
        run = job.index('$RUNNER run --root "$ROOT" --data-rel "$DATA_REL" --out "$OUT"')
        verify = job.index("$RUNNER verify --out")
        done = job.rindex("finish DONE")
        self.assertTrue(build < run < verify < done)
        self.assertIn("OUT=$ROOT/out/$STAGE", job)                   # the out dir is inside the root
        self.assertIn("=== R1S1 $1", job.replace('say "R1S1 $1"', "=== R1S1 $1"))
        self.assertIn('say "R1S1 $1"', job)                          # the DONE / FAIL marker waitlog looks for
        self.assertIn("torch.cuda.get_device_name", job)
        self.assertIn("torch==$TORCH_PIN", job)
        self.assertIn("pip uninstall -y torchvision torchaudio", job)
        self.assertIn("export/MANIFEST.sha256", job)
        self.assertIn("out.tar.gz", job)
        self.assertIn("sleep 14400", job)

    def test_seal_copied_before_run_in_1b(self) -> None:
        job = self.job("1b")
        self.assertLess(job.index("SEAL.sha256.txt"), job.index('$RUNNER run --root'))

    def test_marker_strings_match_waitlog(self) -> None:
        job = self.job("1a", flop_budget=1e16)
        self.assertIn("R1S1", job)
        self.assertEqual(rent.DONE_MARK, "=== R1S1 DONE")
        self.assertIn('fail() { say "R1S1-FAIL $*"', job)


class CostTest(unittest.TestCase):
    def test_arithmetic(self) -> None:
        x = {"dph_total": 0.45, "start_date": 1000.0}
        c = rent.running_cost(x, 1000.0 + 2 * 3600)
        self.assertAlmostEqual(c["usd"], 0.90)
        self.assertAlmostEqual(c["hours"], 2.0)
        self.assertIsNone(rent.running_cost({"start_date": 1.0}, 5.0)["usd"])
        self.assertAlmostEqual(rent.running_cost({"dph_total": 1.0, "duration": 1800}, 0)["usd"], 0.5)
        self.assertAlmostEqual(rent.running_cost({"dph_total": 1.0, "start_date": 100}, 100, 0.25)["usd"], 0.25)

    def test_hard_stops(self) -> None:
        self.assertEqual(rent.HARD_STOP, {"1a": 0.30, "1b": 2.50})
        self.assertFalse(rent.over_stop(0.2999, "1a"))
        self.assertTrue(rent.over_stop(0.30, "1a"))
        self.assertTrue(rent.over_stop(2.5, "1b"))
        self.assertFalse(rent.over_stop(2.49, "1b"))
        self.assertFalse(rent.over_stop(None, "1a"))
        # at $0.45/h, 1a stops after 0.667 h and 1b after 5.56 h
        self.assertTrue(rent.over_stop(rent.running_cost({"dph_total": 0.45, "start_date": 0}, 0.67 * 3600)["usd"], "1a"))
        self.assertFalse(rent.over_stop(rent.running_cost({"dph_total": 0.45, "start_date": 0}, 0.66 * 3600)["usd"], "1a"))

    def test_stage_from_label(self) -> None:
        self.assertEqual(rent.stage_of("claude-steals8-r1s1-1b"), "1b")
        self.assertEqual(rent.stage_of("whatever", "1a"), "1a")
        with self.assertRaises(SystemExit):
            rent.stage_of("claude-other-job")

    def test_progress_key_ignores_the_clock_only(self) -> None:
        a = "x\n=== TICK 10:00:00 | line | kb=5"
        self.assertEqual(rent.progress_key(a), rent.progress_key("x\n=== TICK 10:02:00 | line | kb=5"))
        self.assertNotEqual(rent.progress_key(a), rent.progress_key("x\n=== TICK 10:02:00 | line | kb=6"))


class WaitlogTest(unittest.TestCase):
    def run_wait(self, instance, text="", stage="1a", **kw):
        calls = []

        def fake_call(method, path, body=None, timeout=60):
            calls.append((method, path, body))
            return {"success": True}
        ns = Ns(id="7", stage=stage, max_min=kw.get("max_min", 360), poll=0)
        with mock.patch.object(rent, "call", fake_call), mock.patch.object(rent, "inst", return_value=instance), \
                mock.patch.object(rent, "log_text", return_value=text), mock.patch.object(rent.time, "sleep"), \
                mock.patch("builtins.print") as pr, self.assertRaises(SystemExit) as cm:
            rent.waitlog(ns)
        return cm.exception.code, calls, json.loads(pr.call_args[0][0])

    def inst(self, hours, dph=1.0, status="running", label="claude-steals8-r1s1-1a"):
        return {"label": label, "actual_status": status, "dph_total": dph, "start_date": time.time() - hours * 3600}

    def test_hard_stop_stops_not_destroys(self) -> None:
        code, calls, out = self.run_wait(self.inst(0.31))          # $0.31 on a $0.30 stop
        self.assertEqual(code, 3)
        self.assertEqual(out["event"], "HARD-STOP")
        self.assertEqual(calls, [("PUT", "/instances/7/", {"state": "stopped"})])
        self.assertFalse(any(m == "DELETE" for m, _, _ in calls))

    def test_1b_limit_is_its_own(self) -> None:
        inst = self.inst(1.0, label="claude-steals8-r1s1-1b")      # $1.00: over 1a's stop, under 1b's
        code, calls, out = self.run_wait(inst, stage="1b", text="=== R1S1 DONE x")
        self.assertEqual((code, calls), (0, []))
        code, calls, out = self.run_wait(self.inst(2.6, label="claude-steals8-r1s1-1b"), stage="1b")
        self.assertEqual((code, out["event"]), (3, "HARD-STOP"))

    def test_not_running_after_six_minutes(self) -> None:
        inst = self.inst(0.01, status="loading")
        with mock.patch.object(rent.time, "time", side_effect=[0, 7 * 60]):
            code, calls, out = self.run_wait(inst)
        self.assertEqual((code, out["event"], calls), (4, "NOT-RUNNING", []))

    def test_done_and_fail(self) -> None:
        code, calls, out = self.run_wait(self.inst(0.01), "a\n=== R1S1 DONE 2026-10-20T10:00:00Z\n")
        self.assertEqual((code, out["event"], calls), (0, "DONE", []))
        code, _, out = self.run_wait(self.inst(0.01), "=== R1S1-FAIL build 2026\n=== R1S1 FAIL 2026\n")
        self.assertEqual((code, out["event"]), (2, "JOB-FAIL"))

    def test_unreadable_price_stops(self) -> None:
        code, calls, out = self.run_wait({"label": "claude-steals8-r1s1-1a", "actual_status": "running"})
        self.assertEqual((code, out["event"]), (7, "COST-UNKNOWN"))
        self.assertEqual(calls, [("PUT", "/instances/7/", {"state": "stopped"})])


class Net(Fixture):
    """create / pull / destroy with the HTTP layer mocked."""

    def setUp(self) -> None:
        super().setUp()
        self.pack("1a", flop_budget=1e16)
        self.calls = []
        self.instances = []                                       # what GET /instances/ lists
        self.sleep = mock.patch.object(rent.time, "sleep")
        self.sleep.start()
        self.addCleanup(self.sleep.stop)
        call = mock.patch.object(rent, "call", self.fake_call)
        call.start()
        self.addCleanup(call.stop)

    def fake_call(self, method, path, body=None, timeout=60):
        self.calls.append((method, path))
        if method == "GET" and path == "/instances/":
            return {"instances": list(self.instances)}
        if method == "GET" and path.startswith("/instances/"):
            i = int(path.strip("/").split("/")[-1])
            return {"instances": [x for x in self.instances if x["id"] == i]}
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
        self.assertEqual(shown["would_send"]["body"]["label"], "claude-steals8-r1s1-1a")
        self.assertNotIn(self.args()[4][:50], text)                # the base64 pack is not dumped
        self.create(dryrun=True)
        self.assertEqual(self.calls, [])

    def test_create_with_yes_sends_once(self) -> None:
        self.create(yes=True)
        puts = [c for c in self.calls if c[0] == "PUT"]
        self.assertEqual(puts, [("PUT", "/asks/123/")])

    def test_create_with_yes_stops_on_duplicate_label(self) -> None:
        self.instances = [{"id": 5, "label": "claude-steals8-r1s1-1a"}]
        with self.assertRaises(SystemExit):
            self.create(yes=True)
        self.assertFalse(any(m == "PUT" for m, _ in self.calls))

    def test_create_refuses_wrong_label(self) -> None:
        with self.assertRaises(SystemExit):
            self.create(label="claude-steals8-r1s1-1b", yes=True)
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
    def fake_box(self, tamper=False, status="DONE rc=0", inner=True):
        """What /job/export and /job/b64 hold after a run: out.tar.gz holding stage dir '1a' with a runner manifest."""
        files = {"1a/RESULT.json": b'{"x": 1}', "1a/log.txt": b"hello\n"}
        files["1a/MANIFEST.sha256"] = "".join(f"{sh(b)}  {n[3:]}\n" for n, b in files.items()).encode()
        if not inner:
            del files["1a/MANIFEST.sha256"]
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as t:
            for n, b in files.items():
                i = tarfile.TarInfo(n)
                i.size = len(b)
                t.addfile(i, io.BytesIO(b))
        tar = buf.getvalue()
        b64 = base64.encodebytes(tar)
        half = len(b64) // 2
        parts = {"big/out.tar.gz.b64.p000": b64, "small/out.tar.gz.b64.p000": b64[:half],
                 "small/out.tar.gz.b64.p001": b64[half:]}
        if tamper:
            parts["big/out.tar.gz.b64.p000"] = base64.encodebytes(tar[:-5] + b"xxxxx")
            parts["small/out.tar.gz.b64.p000"] = base64.encodebytes(tar[:-5] + b"xxxxx")
            parts.pop("small/out.tar.gz.b64.p001")
        sizes = "".join(f"{len(b)} {p}\n" for p, b in parts.items()) + "999 total\n"
        box = {"/job/export/MANIFEST.sha256": f"{sh(tar)}  out.tar.gz\n".encode(),
               "/job/export/PARTS.txt": sizes.encode(), "/job/export/STATUS.txt": (status + "\n").encode()}
        box.update({f"/job/b64/{p}": b for p, b in parts.items()})
        return box

    def pull(self, box, with_ckpt=False):
        run = Path(self.tmp.name) / "run"
        ns = Ns(id="7", out=str(run), with_ckpt=with_ckpt)
        with mock.patch.object(rent, "exec_cat", lambda i, path, tries=3: box.get(path)), \
                mock.patch("builtins.print"):
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

    def test_pull_ok_writes_marker_and_extracts(self) -> None:
        run, ok = self.pull(self.fake_box())
        self.assertTrue(ok)
        self.assertEqual(json.loads((run / rent.PULL_OK).read_text())["id"], 7)
        self.assertEqual((run / "1a" / "log.txt").read_bytes(), b"hello\n")
        self.assertEqual(self.calls, [])                          # pull itself talks to the box only through exec_cat

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

    def test_pull_with_a_changed_inner_file_fails(self) -> None:
        box = self.fake_box()
        run, _ = self.pull(box)
        (run / "1a" / "log.txt").write_bytes(b"changed")
        found, bad = rent.inner_check(run, False)
        self.assertTrue(found)
        self.assertEqual(bad, ["1a/log.txt"])

    def test_destroy_refuses_until_a_pull_passed(self) -> None:
        self.instances = [{"id": 7, "label": "claude-steals8-r1s1-1a"}]
        with self.assertRaises(SystemExit):
            self.destroy()                                        # no --pulled
        run, _ = self.pull(self.fake_box(tamper=True))            # a failed pull
        with self.assertRaises(SystemExit):
            self.destroy(pulled=str(run))
        self.assertEqual(self.calls, [])                          # refused before any request
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
        self.instances = [{"id": 7, "label": "claude-steals8-r1s1-1b"}]
        self.destroy(abandon=True)
        self.assertIn(("DELETE", "/instances/7/"), self.calls)


if __name__ == "__main__":
    unittest.main()
