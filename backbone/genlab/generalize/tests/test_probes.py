"""Probe generator: existing output unchanged, per-axis split maps respected, the sealed split never touched."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from generalize import probes
from learnlab.splits import SplitLeak
from learnlab.village import names
from learnlab.village.render import PatternSource, village_registry
from learnlab.village.scheduler import style_assignment, world_families
from learnlab.village.shards import write_shards

# sha256 of 20-visit (10 per shard, seed 0) train and validation builds, recorded BEFORE scheduler.py / stream.py were touched
GOLDEN = {
    "train/shard-00000.jsonl": "413112fb2b55ddc0ca82d8201826df645b95a97f9582c3265b6ea5db7d8d6f73",
    "train/shard-00000.txt": "53947e572a014f104e41566fa99f641314f9619ac1da44110cb0a4c2c4c31b1c",
    "train/shard-00001.jsonl": "5247d73a3e2e434d9a61a4ea3aee8b5a2532e56e1c5b2949e7ae345ade66516d",
    "train/shard-00001.txt": "e2fdef744221e4a1895ea90efe04c38c15fadf5879baf03e29f2586fa86f5b06",
    "validation/shard-00000.jsonl": "b1f84a6b5fdc92c0b3bc813b285bbb0e2b255d6d0bff16249752026b5b254261",
    "validation/shard-00000.txt": "b32cf09150f814495380af514cb1be0842868b9d754374492e5beb9f8306e030",
    "validation/shard-00001.jsonl": "0209f83e603fc7956fe24f465c63da392b4f27fe280e05056018f67abfd69173",
    "validation/shard-00001.txt": "71c6e06463e1474c445c0c5f5b3d889af9dfcf5457fc902b01868740e07c9eb0",
}
N = 40


def rows(directory):
    out = []
    for shard in sorted(Path(directory).glob("shard-*.jsonl")):
        out += [json.loads(line) for line in shard.read_text().splitlines() if line.strip()]
    return out


class Existing(unittest.TestCase):
    def test_write_shards_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            for split in ("train", "validation"):
                write_shards(split, 20, tmp, 1, seed=0, visits_per_shard=10, verbose=False)
            got = {k: hashlib.sha256((Path(tmp) / k).read_bytes()).hexdigest() for k in GOLDEN}
        self.assertEqual(got, GOLDEN)


class Profiles(unittest.TestCase):
    def test_axis_maps(self):
        p = probes.Profile.of(["name"])
        self.assertEqual(p.axis_map(), {"name": "validation", "template": "train", "teacher_style": "train", "rule_family": "train"})
        self.assertEqual((p.label, p.knobs, p.families), ("train", "train", "train"))
        d = probes.Profile.of(["difficulty"])
        self.assertEqual((d.knobs, d.families, set(d.axis_map().values())), ("validation", "train", {"train"}))
        r = probes.Profile.of(["rule"])
        self.assertEqual((r.knobs, r.families, r.axis_map()["rule_family"]), ("train", "validation", "validation"))
        a = probes.Profile.of(probes.CONCERNS)
        self.assertEqual((a.label, a.knobs, a.families, set(a.axis_map().values())), ("validation",) * 3 + ({"validation"},))

    def test_test_split_refused(self):
        with self.assertRaises(SplitLeak):
            probes.Profile(frozenset(), base="test")
        with self.assertRaises(SplitLeak):
            probes.Profile(frozenset({"name"}), other="test")
        with self.assertRaises(ValueError):
            probes.Profile.of(["bogus"])

    def test_view_never_hands_out_test_items(self):
        import random
        source = PatternSource.load()
        registry = village_registry(source, world_families())
        view = probes.MixedView(registry, probes.Profile.of(probes.CONCERNS))
        test_names = [n for n in names.people_names() if registry.split_of("name", n) == "test"]
        self.assertTrue(test_names)
        self.assertNotIn(test_names[0], view.available("name", names.people_names()))
        with self.assertRaises(SplitLeak):
            view.use("name", test_names[0])
        for _ in range(20):
            for n in view.draw("name", names.people_names(), random.Random(_), 5):
                self.assertEqual(registry.split_of("name", n), "validation")
        train_view = probes.MixedView(registry, probes.Profile.of([]))
        with self.assertRaises(SplitLeak):
            train_view.use("name", next(n for n in names.people_names() if registry.split_of("name", n) == "validation"))

    def test_training_data_only_difficulty(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in (("name",), ("template",), ("style",), ("rule",), ("difficulty", "name")):
                with self.assertRaises(ValueError):
                    probes.write_training_data(bad, 4, tmp)
            with self.assertRaises(ValueError):
                probes.write_training_data(("difficulty",), 4, tmp, index_offset=0)


class Generated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dirs = {}
        for name, concerns in probes.PROBES.items():
            probes.write_probe(name, concerns, N, cls.tmp.name, 1, visits_per_shard=20, verbose=False)
            cls.dirs[name] = Path(cls.tmp.name) / name
        cls.sum = {n: probes.summarize(d) for n, d in cls.dirs.items()}
        cls.registry = village_registry(PatternSource.load(), world_families())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_shard_layout_and_metadata(self):
        for name, d in self.dirs.items():
            self.assertTrue(list(d.glob("shard-*.txt")) and (d / "manifest.json").is_file())
            q = [r for r in rows(d) if r["kind"] == "question"]
            self.assertTrue(q)
            for key in ("depth", "families", "base_qtype", "template", "style", "answer", "probe"):
                self.assertIn(key, q[0])
            self.assertEqual(q[0]["probe"], name)

    def test_audit_passes_and_no_test_items(self):
        for name, d in self.dirs.items():
            self.assertEqual(probes.audit_probe_dir(d)["visits"], N)
            for r in rows(d):
                if r["kind"] == "visit":
                    for axis, items in r["provenance"].items():
                        for item in items:
                            self.assertNotEqual(self.registry.split_of(axis, item), "test", (name, axis, item))
                    self.assertIn(r["split"], ("train", "validation"))

    def test_per_axis_provenance(self):
        styles = style_assignment()
        source = PatternSource.load()
        for name, concerns in probes.PROBES.items():
            profile = probes.Profile.of(concerns)
            for r in rows(self.dirs[name]):
                if r["kind"] != "visit":
                    continue
                prov = r["provenance"]
                for n in prov["name"]:
                    self.assertEqual(self.registry.split_of("name", n), profile.axis_split("name"), name)
                for s in prov["teacher_style"]:
                    self.assertEqual(styles[s], profile.axis_split("teacher_style"), name)
                for t in prov["template"]:
                    want = profile.axis_split("teacher_style") if source.bank[t].startswith("t.") else profile.axis_split("template")
                    self.assertEqual(source.split[t], want, (name, t))
                for f in prov["rule_family"]:
                    self.assertEqual(self.registry.split_of("rule_family", f), profile.axis_split("rule_family"), (name, f))

    def test_distributions(self):
        s = self.sum
        for n in ("P0", "Pname", "Pword", "Pstyle", "Prule"):
            self.assertEqual(s[n]["depth_gt3"], 0, n)
        for n in ("P0", "Pname", "Pword", "Pdepth", "Pstyle"):
            self.assertEqual(s[n]["r8"], 0, n)
        for n in ("P0", "Pname", "Pword", "Pdepth", "Prule"):
            self.assertEqual(s[n]["validation_style_questions"], 0, n)
        self.assertGreater(s["Pdepth"]["depth_gt3"], 0)
        self.assertGreater(s["Prule"]["r8"], 0)
        self.assertGreater(s["Pstyle"]["validation_style_questions"], 0)
        self.assertEqual(s["Pstyle"]["train_style_questions"], 0)
        self.assertEqual(s["Pall"]["train_style_questions"], 0)
        self.assertGreater(s["Pall"]["depth_gt3"], 0)
        self.assertGreater(s["Pall"]["r8"], 0)

    def test_pword_uses_validation_narration_only(self):
        source = PatternSource.load()
        for name, want in (("P0", "train"), ("Pword", "validation")):
            used = {t for r in rows(self.dirs[name]) if r["kind"] == "question" for t in r["templates"]
                    if not source.bank[t].startswith("t.")}
            self.assertTrue(used)
            self.assertEqual({source.split[t] for t in used}, {want}, name)

    def test_pname_changes_only_names(self):
        a = (self.dirs["P0"] / "shard-00000.txt").read_text()
        b = (self.dirs["Pname"] / "shard-00000.txt").read_text()
        self.assertNotEqual(a, b)

    def test_probe_visits_fresh(self):
        # ids are label-seed (seed 101 * 1e9 + index): none coincide with train/dev/validation (seed 0)
        ids = {r["id"] for r in rows(self.dirs["P0"]) if r["kind"] == "visit"}
        self.assertTrue(all(i.startswith("train-101") for i in ids))

    def test_pall_reproduces_validation(self):
        res = probes.check_pall_reproduces_validation(12)
        self.assertTrue(res["text_identical"] and res["rows_identical"], res)

    def test_training_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            probes.write_training_data(("difficulty",), 12, tmp, 1, visits_per_shard=6, verbose=False)
            d = Path(tmp) / "train+difficulty"
            self.assertEqual(probes.audit_probe_dir(d)["visits"], 12)
            ids = [r["id"] for r in rows(d) if r["kind"] == "visit"]
            normal = {f"train-{i}" for i in range(100_000)}
            self.assertFalse(set(ids) & normal)
            self.assertEqual(json.loads((d / "manifest.json").read_text())["split"], "train")


if __name__ == "__main__":
    unittest.main()
