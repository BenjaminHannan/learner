"""CPU-only tests for sense_encoder_lora (no numpy, no MLX, no model): manifest rules, mid-layer states by reference, the
short window purge, stale pooled features dropped, separate switchable adapter, seatbelt bf16 + q8, exact rollback of BOTH files
(including 'there was no adapter' -> deleted), quarantine, crash rollback, Ben-first stop, version bump on keep."""
import json
import struct
import tempfile
import unittest
from pathlib import Path

from sleepmlx import sense_encoder_lora as EL


def write_states(d: Path, day: str, mats):
    off, entries = 0, []
    with open(d / f"states-{day}.bin", "ab") as f:
        for rows in mats:
            flat = [x for r in rows for x in r]
            b = struct.pack(f"<{len(flat)}e", *flat)
            f.write(b)
            entries.append({"day": day, "off": off, "shape": [len(rows), len(rows[0])], "layer": 8})
            off += len(b)
    return entries


def manifest(d: Path, night: str, ear=(), eye=(), dtype="float16"):
    p = d / f"encpractice-{night}.json"
    p.write_text(json.dumps({"night": night, "dtype": dtype, "statesDir": str(d), "ear_states": list(ear), "eye_states": list(eye)}))
    return p


class Env:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.proj = self.d / "audio_projector.safetensors"
        self.proj.write_bytes(b"PROJ-v0..." * 50)
        self.store = EL.AdapterStore(self.d / "encoder-lora")
        e = write_states(self.d, "2026-11-04", [[[0.5, -1.0], [2.0, 0.25]], [[1.0, 1.0], [1.0, 1.0]]])
        self.entries = [dict(x, label=lab) for x, lab in zip(e, ["a dog barks", "rain on a roof"])]


class Scores:
    """Fake fixed tests: score depends on the first bytes of the projector and adapter files (adapter None -> 'off')."""
    def __init__(self, table):
        self.table, self.calls = table, []

    def __call__(self, proj, adapter):
        key = (Path(proj).read_bytes()[:7], Path(adapter).read_bytes()[:7] if adapter else b"off")
        self.calls.append(key)
        return dict(self.table.get(key, self.table.get("default", {})))


def trainer(new_proj=b"PROJ-v1", new_adapter=b"LORA-v1", crash=False):
    def t(proj, adapter, tonight, replay):
        t.seen = (len(tonight), len(replay))
        if crash:
            Path(adapter).write_bytes(b"HALF")
            raise RuntimeError("boom")
        Path(proj).write_bytes(new_proj + b"x" * 20)
        Path(adapter).write_bytes(new_adapter + b"y" * 20)
    return t


GOOD = {(b"PROJ-v0", b"off"): {"V1": 60, "A1": 31, "VID1": 50}, (b"PROJ-v1", b"LORA-v1"): {"V1": 60.5, "A1": 40, "VID1": 50},
        (b"PROJ-v1", b"off"): {"V1": 60, "A1": 30, "VID1": 50}}


class EncoderLoraTests(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.tmp.cleanup)

    def test_manifest_rules_and_state_round_trip(self):
        m = EL.read_manifest(manifest(self.env.d, "n1", self.env.entries))
        v, shp = EL.load_state(str(self.env.d), m["ear_states"][0])
        self.assertEqual((v, shp), ([0.5, -1.0, 2.0, 0.25], [2, 2]))
        with self.assertRaises(ValueError):
            EL.read_manifest(manifest(self.env.d, "n2", self.env.entries, dtype="float32"))
        with self.assertRaises(ValueError):
            EL.read_manifest(manifest(self.env.d, "n3", [dict(self.env.entries[0], label="maybe a wolf")]))
        with self.assertRaises(ValueError):
            EL.read_manifest(manifest(self.env.d, "n4", [dict(self.env.entries[0], shape=[2])]))
        with self.assertRaises(ValueError):
            EL.read_manifest(manifest(self.env.d, "n5", [{k: v for k, v in self.env.entries[0].items() if k != "layer"}]))

    def test_kept_night_creates_adapter_bumps_version_logs_adapter_off(self):
        sc = Scores(GOOD)
        e = EL.run_night(self.env.proj, manifest(self.env.d, "n1", self.env.entries), self.env.store, sense="ear",
                         train_fn=trainer(), eval_fn=sc)
        self.assertTrue(e["kept"] and e["trained"]); self.assertFalse(e["had_adapter"])
        self.assertEqual(self.env.store.version("ear"), 1)
        self.assertEqual(self.env.store.version("eye"), 0)
        self.assertEqual(e["adapter_off"]["A1"], 30)
        self.assertEqual(self.env.store.active_path("ear"), str(self.env.store.path("ear")))
        self.env.store.set_enabled("ear", False)
        self.assertIsNone(self.env.store.active_path("ear"))
        led = [json.loads(l) for l in (self.env.d / "encoder-nights.jsonl").read_text().splitlines()]
        self.assertEqual(led[-1]["enc_version_after"], 1)

    def test_switch_off_restores_projector_from_before_the_adapter(self):
        before = self.env.proj.read_bytes()
        EL.run_night(self.env.proj, manifest(self.env.d, "n1", self.env.entries), self.env.store, sense="ear",
                     train_fn=trainer(), eval_fn=Scores(GOOD))
        self.assertNotEqual(self.env.proj.read_bytes(), before)
        r = self.env.store.switch_off("ear", self.env.proj)
        self.assertTrue(r["projector_restored"]); self.assertEqual(self.env.proj.read_bytes(), before)
        self.assertIsNone(self.env.store.active_path("ear")); self.assertTrue(self.env.store.path("ear").exists())
        self.assertTrue((self.env.d / "audio_projector.safetensors.with-adapter").exists())

    def test_drop_rolls_back_and_deletes_new_adapter_and_quarantines(self):
        bad = dict(GOOD); bad[(b"PROJ-v1", b"LORA-v1")] = {"V1": 57.5, "A1": 45, "VID1": 50}  # V1 -2.5
        before = self.env.proj.read_bytes()
        mp = manifest(self.env.d, "n1", self.env.entries)
        e = EL.run_night(self.env.proj, mp, self.env.store, sense="ear", train_fn=trainer(), eval_fn=Scores(bad))
        self.assertFalse(e["kept"]); self.assertIn("V1 dropped", e["reason"])
        self.assertEqual(self.env.proj.read_bytes(), before)
        self.assertFalse(self.env.store.path("ear").exists())
        self.assertEqual(self.env.store.version("ear"), 0)
        self.assertFalse(mp.exists()); self.assertTrue((self.env.d / "encpractice-n1.quarantined.json").exists())

    def test_existing_adapter_restored_byte_exact(self):
        a = self.env.store.path("ear"); a.write_bytes(b"LORA-v0" + b"z" * 30); old = a.read_bytes()
        tab = {"default": {"V1": 60, "A1": 31, "VID1": 50}, (b"PROJ-v1", b"LORA-v1"): {"V1": 60, "A1": 31, "VID1": 47}}
        e = EL.run_night(self.env.proj, manifest(self.env.d, "n1", self.env.entries), self.env.store, sense="ear",
                         train_fn=trainer(), eval_fn=Scores(tab))
        self.assertFalse(e["kept"]); self.assertEqual(a.read_bytes(), old)

    def test_q8_drop_and_missing_score_and_crash_roll_back(self):
        q8 = {"default": {"V1": 55, "A1": 30, "VID1": 40}, (b"PROJ-v1", b"LORA-v1"): {"V1": 55, "A1": 27, "VID1": 40}}
        e = EL.run_night(self.env.proj, manifest(self.env.d, "n1", self.env.entries), self.env.store, sense="ear",
                         train_fn=trainer(), eval_fn=Scores(GOOD), q8_eval_fn=Scores(q8))
        self.assertFalse(e["kept"]); self.assertTrue(e["reason"].startswith("q8"))
        miss = dict(GOOD); miss[(b"PROJ-v1", b"LORA-v1")] = {"V1": 61, "A1": 40}
        e = EL.run_night(self.env.proj, manifest(self.env.d, "n2", self.env.entries), self.env.store, sense="ear",
                         train_fn=trainer(), eval_fn=Scores(miss))
        self.assertFalse(e["kept"]); self.assertIn("VID1 missing", e["reason"])
        before = self.env.proj.read_bytes()
        e = EL.run_night(self.env.proj, manifest(self.env.d, "n3", self.env.entries), self.env.store, sense="ear",
                         train_fn=trainer(crash=True), eval_fn=Scores(GOOD))
        self.assertFalse(e["kept"]); self.assertIn("training failed", e["reason"])
        self.assertEqual(self.env.proj.read_bytes(), before); self.assertFalse(self.env.store.path("ear").exists())

    def test_ben_first_switched_off_and_empty(self):
        mp = manifest(self.env.d, "n1", self.env.entries)
        t = trainer()
        e = EL.run_night(self.env.proj, mp, self.env.store, sense="ear", train_fn=t, eval_fn=Scores(GOOD), should_stop=lambda: True)
        self.assertFalse(e["trained"]); self.assertFalse(hasattr(t, "seen"))
        self.env.store.set_enabled("ear", False)
        e = EL.run_night(self.env.proj, mp, self.env.store, sense="ear", train_fn=t, eval_fn=Scores(GOOD))
        self.assertEqual(e["reason"], "adapter switched off"); self.assertFalse(hasattr(t, "seen"))
        self.env.store.set_enabled("ear", True)
        e = EL.run_night(self.env.proj, mp, self.env.store, sense="eye", train_fn=t, eval_fn=Scores(GOOD))
        self.assertEqual(e["reason"], "nothing to practise")

    def test_replay_only_kept_nights_inside_window(self):
        st = self.env.store
        EL.run_night(self.env.proj, manifest(self.env.d, "n1", self.env.entries), st, sense="ear", train_fn=trainer(), eval_fn=Scores(GOOD))
        e2 = write_states(self.env.d, "2026-11-05", [[[0.0, 1.0]]])
        tab = {"default": {"V1": 60, "A1": 40, "VID1": 50}}
        t = trainer(b"PROJ-v1", b"LORA-v1")
        EL.run_night(self.env.proj, manifest(self.env.d, "n2", [dict(e2[0], label="a cat")]), st, sense="ear", train_fn=t, eval_fn=Scores(tab))
        self.assertEqual(t.seen, (1, 2))
        gone = EL.purge_states(self.env.d, "2026-11-06", keep_days=2)
        self.assertEqual(gone, ["states-2026-11-04.bin"])
        t3 = trainer(b"PROJ-v1", b"LORA-v1")
        e3 = write_states(self.env.d, "2026-11-06", [[[1.0, 0.0]]])
        EL.run_night(self.env.proj, manifest(self.env.d, "n3", [dict(e3[0], label="a bus")]), st, sense="ear", train_fn=t3, eval_fn=Scores(tab))
        self.assertEqual(t3.seen, (1, 1))  # n1's states purged -> only n2 replays

    def test_purge_by_bytes_and_stale_filter(self):
        for day in ("2026-11-01", "2026-11-02", "2026-11-03"):
            (self.env.d / f"states-{day}.bin").write_bytes(b"\0" * 1000)
        gone = EL.purge_states(self.env.d, "2026-11-03", keep_days=10, max_bytes=2100)
        self.assertEqual(gone, ["states-2026-11-01.bin"])
        self.assertLessEqual(sum(p.stat().st_size for p in self.env.d.glob("states-*.bin")), 2100)
        keep, dropped = EL.stale_filter([{"encVersion": 2}, {"encVersion": 1}, {}], 2)
        self.assertEqual((len(keep), dropped), (1, 2))
        keep, dropped = EL.stale_filter([{}, {"encVersion": 0}], 0)
        self.assertEqual((len(keep), dropped), (2, 0))


class ProjectorStaleFeatureTests(unittest.TestCase):
    """The hunk added to sense_projector: pooled features from an older encoder adapter never train the projector."""
    def test_stale_pooled_features_left_out(self):
        from sleepmlx import sense_projector as SP
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            with open(d / "features-2026-11-04.bin", "wb") as f:
                f.write(struct.pack("<4e", 1.0, 2.0, 3.0, 4.0))
            ents = [{"day": "2026-11-04", "off": 0, "len": 2, "label": "old", "encVersion": 1},
                    {"day": "2026-11-04", "off": 4, "len": 2, "label": "new", "encVersion": 2}]
            m = {"ear": ents}
            tonight, _ = SP.practice_set(m, "ear", d, enc_version=2)
            self.assertEqual([x[2] for x in tonight], ["new"])
            tonight, _ = SP.practice_set(m, "ear", d)
            self.assertEqual(len(tonight), 2)
            tonight, old = SP.practice_set({"ear": []}, "ear", d, replay=[{"ear": ents}], enc_version=0)
            self.assertEqual((tonight, old), ([], []))


if __name__ == "__main__":
    unittest.main()
