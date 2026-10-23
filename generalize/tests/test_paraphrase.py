"""generalize.paraphrase: the augmented bank keeps old assignments, adds train-only ids and loads (no API calls)."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from generalize import paraphrase as PP
from learnlab import patterns as P
from learnlab.village.render import PatternSource

BASE = json.loads(PP.SRC.read_text())


def fake_entries():
    rows = []
    for bank, text in (("q.where_object", "Please tell me where {object} is lying."), ("ev.go", "{person} strolled off to {place}.")):
        rows.append({"id": P.pattern_id(bank, text), "bank": bank, "text": text, "writer": "test"})
    rows.append({"id": P.pattern_id("t.state", "Listen well to this. {fact}"), "bank": "t.state", "style": "bossy",
                 "text": "Listen well to this. {fact}", "writer": "test"})
    return rows


class AssembleTest(unittest.TestCase):
    def test_assemble_is_train_only_and_consistent(self):
        new = fake_entries()
        aug = PP.assemble(BASE, new)
        PP.verify_untouched(BASE, aug)
        assignment = aug["manifest"]["families"]["template"]["assignment"]
        self.assertTrue(all(assignment[e["id"]] == "train" for e in new))
        self.assertEqual(len(assignment), len(BASE["manifest"]["families"]["template"]["assignment"]) + 3)
        self.assertNotEqual(aug["manifest_digest"], BASE["manifest_digest"])
        self.assertEqual(aug["counts"]["q.where_object"]["train"], BASE["counts"]["q.where_object"]["train"] + 1)
        self.assertEqual(aug["counts"]["q.where_object"]["validation"], BASE["counts"]["q.where_object"]["validation"])

    def test_loads_and_validation_pools_unchanged(self):
        aug = PP.assemble(BASE, fake_entries())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aug.json"
            PP.write_bank(aug, path)
            new, old = PatternSource.load(path), PatternSource.load(PP.SRC)
        self.assertNotEqual(new.version, old.version)
        for key, ids in old.pools.items():
            if key[1] in ("validation", "test") or key[1] not in PP.TRAIN_STYLES and key[0].startswith("t."):
                self.assertEqual(new.pools[key], ids)
        self.assertEqual(len(new.pools[("q.where_object", "train")]), len(old.pools[("q.where_object", "train")]) + 1)
        self.assertEqual(len(new.pools[("t.state", "bossy")]), len(old.pools[("t.state", "bossy")]) + 1)

    def test_digest_of_untouched_manifest_matches(self):
        from learnlab.splits import SplitManifest
        self.assertEqual(SplitManifest.from_json(json.dumps(BASE["manifest"])).digest(), BASE["manifest_digest"])

    def test_duplicate_id_refused(self):
        row = fake_entries()[0]
        with self.assertRaises(ValueError):
            PP.assemble(PP.assemble(BASE, [row]), [row])


class PlanTest(unittest.TestCase):
    def test_fallback_banks_are_skipped(self):
        skip = PP.fallback_banks(PP.SRC)
        self.assertIn("q.where_before", skip)
        need = PP.plan(BASE, 24, skip)
        self.assertFalse(set(skip) & {k[0] if isinstance(k, tuple) else k for k in need})
        self.assertEqual(need["q.where_object"], 23)
        self.assertEqual(need[("t.ask", "bossy")], len(PP.current_train(BASE)[("t.ask", "bossy")]))

    def test_only_train_styles_planned(self):
        need = PP.plan(BASE, 24, set())
        self.assertEqual({k[1] for k in need if isinstance(k, tuple)}, set(PP.TRAIN_STYLES))


class AuditTest(unittest.TestCase):
    def test_simulated_audit_is_clean_for_a_train_only_addition(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aug.json"
            PP.write_bank(PP.assemble(BASE, fake_entries()), path)
            self.assertEqual(PP.leaking_ids(path) - {e["id"] for e in fake_entries()}, set())


class ShippedBankTest(unittest.TestCase):
    @unittest.skipUnless(PP.OUT.exists(), "bank-v1-aug.json not built")
    def test_shipped_aug_bank(self):
        aug = json.loads(PP.OUT.read_text())
        PP.verify_untouched(BASE, aug)
        PatternSource.load(PP.OUT)
        for bank, by_split in aug["banks"].items():
            if bank in PP.fallback_banks(PP.SRC):
                self.assertEqual(by_split, BASE["banks"][bank])


if __name__ == "__main__":
    unittest.main()
