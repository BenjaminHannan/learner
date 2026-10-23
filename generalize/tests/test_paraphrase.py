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


AUG = PP.PATTERNS / "bank-v1-aug.json"
AUG2 = PP.PATTERNS / "bank-v1-aug2.json"
FILLED = ("ev.breaks", "ev.is_closed", "ev.kind_group", "q.next_to", "q.plan_get", "q.rule_category", "q.rule_container",
          "q.rule_material", "q.where_at_time", "q.where_before", "q.who_has", "q.yn_has", "rule.R1_material", "rule.R2",
          "t.quiz_later", "t.right")


@unittest.skipUnless(AUG2.exists(), "bank-v1-aug2.json not built")
class Aug2Test(unittest.TestCase):
    def test_loads_without_fallback_and_registry_accepts(self):
        from learnlab.village.render import village_registry
        source = PatternSource.load(AUG2)
        self.assertNotIn("+fill", source.version)
        self.assertFalse([p for p in source.text if p.startswith("fb-") and source.bank[p] not in FILLED])
        village_registry(source)

    def test_held_out_pools_identical_to_bank_v1(self):
        old, new = PatternSource.load(PP.SRC), PatternSource.load(AUG2)
        for key, ids in old.pools.items():
            if key[1] in ("validation", "test") or (key[0].startswith("t.") and key[1] not in PP.TRAIN_STYLES):
                self.assertEqual(new.pools[key], ids, key)
                self.assertEqual([old.text[i] for i in ids], [new.text[i] for i in ids])
        for bank in FILLED:  # held-out fallback ids keep their texts
            self.assertTrue(all(new.text[i] == old.text[i] for i in new.text if i.startswith("fb-") and i in old.text))

    def test_counts_and_more_templates_than_aug(self):
        old, new = PatternSource.load(AUG), PatternSource.load(AUG2)
        for bank in FILLED + ("q.why_at", "q.yn_at", "q.yn_in"):
            if bank.startswith("t."):
                for style in PP.TRAIN_STYLES:
                    self.assertGreaterEqual(len(new.pools[(bank, style)]), 2 * len(old.pools[(bank, style)]))
            else:
                self.assertGreaterEqual(len(new.pools[(bank, "train")]), 22 if bank in FILLED + ("q.why_at", "q.yn_at") else 24)
                self.assertGreater(len(new.pools[(bank, "train")]), len(old.pools[(bank, "train")]))

    def test_train_renders_use_more_distinct_templates(self):
        import tempfile
        from collections import Counter
        from learnlab.village import shards
        used = {}
        for name, path in (("aug", AUG), ("aug2", AUG2)):
            with tempfile.TemporaryDirectory() as tmp:
                shards.write_shards("train", 40, tmp, 1, patterns=str(path), verbose=False)
                ids = Counter()
                for f in Path(tmp, "train").glob("*.jsonl"):
                    for line in f.read_text().splitlines():
                        ids.update(json.dumps(json.loads(line).get("provenance", {})).split('"'))
            source = PatternSource.load(path)
            used[name] = {b: {i for i in ids if i in source.bank and source.bank[i] == b} for b in FILLED}
        better = [b for b in FILLED if len(used["aug2"][b]) > len(used["aug"][b])]
        self.assertGreaterEqual(len(better), 12, {b: (len(used["aug"][b]), len(used["aug2"][b])) for b in FILLED})
        for b in FILLED:
            self.assertGreaterEqual(len(used["aug2"][b]), len(used["aug"][b]))

    def test_validation_shards_and_probe_byte_identical(self):
        import tempfile
        from generalize import probes
        from learnlab.village import shards

        def read(directory):
            return {p.name: p.read_bytes() for p in sorted(Path(directory).rglob("*")) if p.suffix in (".txt", ".jsonl")}

        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            shards.write_shards("validation", 40, a, 1, patterns=str(PP.SRC), verbose=False)
            shards.write_shards("validation", 40, b, 1, patterns=str(AUG2), verbose=False)
            ra, rb = read(a), read(b)
            self.assertTrue(ra)
            self.assertEqual(ra, rb)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            probes.write_probe("Pword", ("template",), 40, a, 1, verbose=False)
            probes.write_probe("Pword", ("template",), 40, b, 1, verbose=False, patterns=str(AUG2))
            # A probe is a TRAIN visit with only the non-teacher templates switched to validation, so its teacher
            # (train-style) wordings legitimately change with any train augmentation (bank-v1-aug does too). What must
            # not change is every non-teacher template choice, visit by visit.
            old, new = PatternSource.load(), PatternSource.load(AUG2)

            def choices(directory, source):
                rows = [json.loads(line) for f in sorted(Path(directory).rglob("*.jsonl")) for line in f.read_text().splitlines()]
                return [[t for t in r["provenance"]["template"] if not source.bank[t].startswith("t.")]
                        for r in rows if r.get("kind") == "visit"]

            ca, cb = choices(a, old), choices(b, new)
            self.assertEqual(len(ca), 40)
            self.assertEqual(ca, cb)
            self.assertTrue(all(old.split[t] in ("validation", "test") for v in ca for t in v if old.bank[t] in FILLED))


if __name__ == "__main__":
    unittest.main()
