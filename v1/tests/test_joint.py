"""Bit-equality tests (CPU): V1 flags off == the original code; the bridge attached at zero == bridge off (both sides).
Original trees are extracted from git: D from 273446d36 (premonition/), B2 code from claude/project-thread-trabt2 (custom_io/).
Run: python -m unittest v1.tests.test_joint   (needs B2_CKPT, SKILLS_TRAIN and network-free git refs fetched)."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D_ORIG_COMMIT = "273446d36"
B2_ORIG_REF = "origin/claude/project-thread-trabt2"


def run(mode, root, bridge=False, extra_path=None):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(root)] + ([str(extra_path)] if extra_path else [])))
    args = [sys.executable, str(ROOT / "v1/tests/ref_dump.py"), mode] + (["bridge"] if bridge else [])
    out = subprocess.run(args, env=env, cwd=str(root), capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def extract(ref, paths, dest):
    tar = subprocess.run(["git", "archive", ref] + paths, cwd=str(ROOT), capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=tar, check=True)


class DSide(unittest.TestCase):
    def test_flags_off_equals_original_and_bridge_zero_equals_off(self):
        with tempfile.TemporaryDirectory() as t:
            extract(D_ORIG_COMMIT, ["premonition", "learnlab", "memorylab"], t)
            Path(t, "v1").symlink_to(ROOT / "v1")
            orig = run("d", t)
        cur = run("d", ROOT)
        bridged = run("d", ROOT, bridge=True)
        self.assertEqual(orig["loss"], cur["loss"], "V1 edits with every flag off changed D's loss")
        self.assertEqual(orig["grads"], cur["grads"], "V1 edits with every flag off changed D's gradients")
        self.assertEqual(cur["loss"], bridged["loss"], "zero bridge changed D's loss")
        self.assertEqual(cur["grads"], bridged["grads"], "zero bridge changed D's gradients")


@unittest.skipUnless(os.environ.get("B2_CKPT") and os.environ.get("SKILLS_TRAIN"), "needs B2_CKPT and SKILLS_TRAIN")
class CreativeSide(unittest.TestCase):
    def test_flags_off_equals_original_and_bridge_zero_equals_off(self):
        with tempfile.TemporaryDirectory() as t:
            extract(B2_ORIG_REF, ["custom_io"], t)
            Path(t, "v1").symlink_to(ROOT / "v1")
            orig = run("b2", t)
        cur = run("b2", ROOT)
        bridged = run("b2", ROOT, bridge=True)
        self.assertEqual(orig["loss"], cur["loss"])
        self.assertEqual(orig["grads"], cur["grads"])
        self.assertEqual(cur["loss"], bridged["loss"], "zero bridge changed the creative loss")
        self.assertEqual(cur["grads"], bridged["grads"], "zero bridge changed the creative gradients")


if __name__ == "__main__":
    unittest.main()
