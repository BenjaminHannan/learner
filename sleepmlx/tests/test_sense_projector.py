"""CPU-only tests for sense_projector (no numpy, no MLX, no model): manifest checks, features by reference, replay of kept nights
only, the seatbelt (bf16 and q8), exact byte rollback + quarantine, crash rollback, Ben-first stop."""
import json
import struct
import tempfile
import unittest
from pathlib import Path

from sleepmlx import sense_projector as SP


def write_day(d: Path, day: str, vecs):
    off, entries = 0, []
    with open(d / f"features-{day}.bin", "ab") as f:
        for v in vecs:
            b = struct.pack(f"<{len(v)}e", *v)
            f.write(b)
            entries.append({"day": day, "off": off, "len": len(v), "shape": [len(v)]})
            off += len(b)
    return entries


def manifest(d: Path, night: str, eye, ear=(), dtype="float16"):
    p = d / f"practice-{night}.json"
    p.write_text(json.dumps({"night": night, "dtype": dtype, "featureDir": str(d), "eye": list(eye), "ear": list(ear)}))
    return p


class Env:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.w = self.d / "vision_projector.safetensors"
        self.w.write_bytes(b"WEIGHTS-v0" * 100)
        e = write_day(self.d, "2026-11-04", [[0.5, -1.0, 2.0], [1.0, 1.0, 1.0], [0.25, 0.0, -0.5]])
        self.entries = [dict(x, label=lab) for x, lab in zip(e, ["a wolf in snow", "BUS 42", "a red car"])]


class ScoreBook:
    """Fake fixed tests: the score depends on the weights file's bytes."""
    def __init__(self, table):
        self.table, self.calls = table, []

    def __call__(self, path):
        b = Path(path).read_bytes()
        self.calls.append(b[:10])
        return dict(self.table[b[:10]])


class SenseProjectorTests(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.tmp.cleanup)

    def test_features_round_trip_and_manifest_rules(self):
        m = SP.read_manifest(manifest(self.env.d, "n1", self.env.entries))
        v = SP.load_features(str(self.env.d), m["eye"][0])
        self.assertEqual(v, [0.5, -1.0, 2.0])
        with self.assertRaises(ValueError):
            SP.read_manifest(manifest(self.env.d, "n2", self.env.entries, dtype="float32"))
        with self.assertRaises(ValueError):
            SP.read_manifest(manifest(self.env.d, "n3", [dict(self.env.entries[0], label="maybe a dog")]))

    def test_seatbelt(self):
        b = {"V1": 67.6, "A1": 30.2, "VID1": 56.7}
        self.assertTrue(SP.seatbelt(b, {"V1": 66.0, "A1": 31, "VID1": 55.0})[0])
        keep, drops, why = SP.seatbelt(b, {"V1": 65.5, "A1": 40, "VID1": 60})
        self.assertFalse(keep)
        self.assertIn("V1 dropped 2.1", why)
        self.assertFalse(SP.seatbelt(b, {"V1": 70, "A1": 40})[0])  # VID1 missing
        self.assertFalse(SP.seatbelt(b, None)[0])

    def test_good_night_is_kept_and_replay_uses_kept_nights_only(self):
        d, seen = self.env.d, {}
        p1 = manifest(d, "2026-11-04", self.env.entries[:1])
        book = ScoreBook({b"WEIGHTS-v0": {"V1": 60, "A1": 30}, b"WEIGHTS-v1": {"V1": 61, "A1": 34}, b"WEIGHTS-v2": {"V1": 62, "A1": 35},
                          b"POISONED!!": {"V1": 50, "A1": 34}})

        def train_to(tag):
            def t(path, tonight, replay):
                seen[tag] = (len(tonight), len(replay))
                Path(path).write_bytes(tag * 100)
            return t
        e1 = SP.run_night(self.env.w, p1, train_fn=train_to(b"WEIGHTS-v1"), eval_fn=book)
        self.assertTrue(e1["kept"])
        self.assertEqual(seen[b"WEIGHTS-v1"], (1, 0))
        # a poisoned night is rolled back and quarantined
        p2 = manifest(d, "2026-11-05", self.env.entries[1:2])
        e2 = SP.run_night(self.env.w, p2, train_fn=train_to(b"POISONED!!"), eval_fn=book)
        self.assertFalse(e2["kept"])
        self.assertTrue(e2["quarantined"])
        self.assertEqual(self.env.w.read_bytes(), b"WEIGHTS-v1" * 100)
        self.assertEqual(e2["sha_after"], e2["sha_before"])
        self.assertFalse(p2.exists())
        self.assertTrue((d / "practice-2026-11-05.quarantined.json").exists())
        # the next night replays only the kept night (1 example), never the quarantined one
        p3 = manifest(d, "2026-11-06", self.env.entries[2:])
        e3 = SP.run_night(self.env.w, p3, train_fn=train_to(b"WEIGHTS-v2"), eval_fn=book)
        self.assertTrue(e3["kept"])
        self.assertEqual(seen[b"WEIGHTS-v2"], (1, 1))
        lines = [json.loads(l) for l in (d / "nights.jsonl").read_text().splitlines()]
        self.assertEqual([l["kept"] for l in lines], [True, False, True])
        self.assertTrue((d / "vision_projector.safetensors.prev").exists())

    def test_q8_check_can_undo_a_night_that_passes_on_bf16(self):
        p = manifest(self.env.d, "n", self.env.entries)
        bf16 = ScoreBook({b"WEIGHTS-v0": {"V1": 60}, b"WEIGHTS-v1": {"V1": 61}})
        q8 = ScoreBook({b"WEIGHTS-v0": {"V1": 59}, b"WEIGHTS-v1": {"V1": 55}})
        e = SP.run_night(self.env.w, p, train_fn=lambda path, a, b: Path(path).write_bytes(b"WEIGHTS-v1" * 100), eval_fn=bf16, q8_eval_fn=q8)
        self.assertFalse(e["kept"])
        self.assertTrue(e["reason"].startswith("q8:"))
        self.assertEqual(self.env.w.read_bytes(), b"WEIGHTS-v0" * 100)

    def test_crash_during_training_restores_exact_weights(self):
        p = manifest(self.env.d, "n", self.env.entries)
        book = ScoreBook({b"WEIGHTS-v0": {"V1": 60}})

        def boom(path, a, b):
            Path(path).write_bytes(b"half-written")
            raise MemoryError("oom")
        e = SP.run_night(self.env.w, p, train_fn=boom, eval_fn=book)
        self.assertFalse(e["kept"])
        self.assertIn("training failed", e["reason"])
        self.assertEqual(self.env.w.read_bytes(), b"WEIGHTS-v0" * 100)

    def test_ben_first_stop_and_empty_night_do_not_touch_weights(self):
        p = manifest(self.env.d, "n", self.env.entries)
        called = []
        e = SP.run_night(self.env.w, p, train_fn=lambda *a: called.append(1), eval_fn=lambda _: {"V1": 1}, should_stop=lambda: True)
        self.assertFalse(e["trained"])
        self.assertEqual(called, [])
        e = SP.run_night(self.env.w, manifest(self.env.d, "m", []), train_fn=lambda *a: called.append(1), eval_fn=lambda _: {"V1": 1})
        self.assertEqual(e["reason"], "nothing to practise")
        self.assertEqual(self.env.w.read_bytes(), b"WEIGHTS-v0" * 100)

    def test_mixed_batches_half_tonight_half_replay(self):
        b = next(SP.mixed_batches([("t",)], [("r",)], 8, 1))
        self.assertEqual(sum(1 for x in b if x == ("t",)), 4)
        self.assertEqual(len(next(SP.mixed_batches([("t",)], [], 8, 1))), 8)


if __name__ == "__main__":
    unittest.main()
