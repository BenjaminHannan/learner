"""Saved-card source identity, correction retirement and checkpoint regressions.

Every file and backend is synthetic and temporary; no model is loaded.
"""
from collections import Counter
import copy
import unittest

from sleepmlx.checkpoint import Checkpoints
from sleepmlx.backend import Stop
from sleepmlx.corpus import Diary
from sleepmlx.recipe import GenCache, Item, key_of
from .helpers import Env


class CardLineageTests(unittest.TestCase):
    def setUp(self):
        self.env = Env(days=())
        self.addCleanup(self.env.close)
        self.sl = self.env.sleeper(self.env.backend())
        self.sl.load_items()
        self.sl.diary = Diary({"diary": []}, "Ben")
        self.sl.N = {"id": "synthetic-lineage-night", "day": 1, "date": "2026-10-20",
                     "phase": "dream", "done_steps": 0, "stats": {}, "rem_done": [], "scale": 1}
        self.env.paths.userdata_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.env.paths.userdata_dir / "memory.md"

    def notes(self, rows):
        self.path.write_text("".join("- %s | topic: card | id: %s | updated: 2026-10-20\n" % (text, note_id)
                                     for note_id, text in rows))

    def reconcile(self, day=1):
        stats = Counter()
        self.sl.card_notes(day, stats)
        return stats

    def active(self, note_id=None):
        return [item for item in self.sl.items.values() if not item.dead and getattr(item, "card_note_id", "")
                and (note_id is None or item.card_note_id == note_id)]

    def artifacts(self, item):
        item.para = [item.fact]
        item.qa = [["Where does Mira work?", "Larkhouse"]]
        item.held = [{"q": "Name Mira's workplace.", "a": "Larkhouse", "night": 1, "dir": "forward"}]
        item.trained = True
        item.seen_ment = 1
        item.dirty = False

    def test_editing_relation_changes_the_live_assertion_not_just_the_file(self):
        self.notes([("m1", "Mira => works at => Larkhouse")])
        self.reconcile()
        self.notes([("m1", "Mira => left => Larkhouse")])
        self.reconcile(2)
        live = [it for it in self.sl.items.values() if not it.dead and it.line]
        self.assertEqual([(it.rel, it.line) for it in live], [("left", "Mira left Larkhouse.")])

    def test_relation_edit_retires_all_old_training_artifacts(self):
        self.notes([("m1", "Mira => works at => Larkhouse")])
        self.reconcile()
        self.assertEqual(len(self.active("m1")), 1)
        old = self.active("m1")[0]
        self.artifacts(old)
        self.sl.rem_pool = [{"q": "old chain", "a": "Larkhouse", "keys": [old.key, "other"]},
                            {"q": "unrelated", "a": "Rivermoor", "keys": ["other"]}]
        self.notes([("m1", "Mira => left => Larkhouse")])
        self.reconcile(2)
        current = self.active("m1")[0]
        self.assertEqual((current.rel, current.line), ("left", "Mira left Larkhouse."))
        self.assertNotEqual(current.key, old.key)
        self.assertNotEqual(current.sig, old.sig)
        self.assertTrue(old.dead)
        self.assertEqual((old.para, old.qa, old.held), ([], [], []))
        self.assertFalse(old.trained)
        self.assertEqual(self.sl.rem_pool, [{"q": "unrelated", "a": "Rivermoor", "keys": ["other"]}])
        self.assertEqual((current.para, current.qa, current.held), ([], [], []))

    def test_card_cannot_overwrite_or_merge_an_independent_diary_fact(self):
        key = key_of("Mira", "Larkhouse")
        diary_item = Item(key, "Mira", "Larkhouse", "lives in", 1, days=1, nment=1,
                          para=["Mira lives in Larkhouse."], qa=[["Where does Mira live?", "Larkhouse"]])
        self.sl.items[key] = diary_item
        original = copy.deepcopy(diary_item.__dict__)
        self.notes([("m1", "Mira => works at => Larkhouse")])
        self.reconcile()
        self.assertEqual(len(self.active("m1")), 1)
        self.assertNotEqual(self.active("m1")[0].key, key)
        self.sl.cleanup()
        self.assertIs(self.sl.items[key], diary_item)
        self.assertEqual(diary_item.__dict__, original)

    def test_same_entity_pair_different_relations_and_sources_survive_cleanup(self):
        self.notes([("m1", "Mira => works at => Larkhouse"), ("m2", "Mira => owns => Larkhouse")])
        self.reconcile()
        self.sl.cleanup()
        self.assertEqual({(it.card_note_id, it.rel) for it in self.active()}, {("m1", "works at"), ("m2", "owns")})
        second = self.active("m2")[0]
        self.artifacts(second)
        second_snapshot = copy.deepcopy(second.__dict__)
        self.notes([("m1", "Mira => works at => Rivermoor"), ("m2", "Mira => owns => Larkhouse")])
        self.reconcile(2)
        self.assertEqual([(it.rel, it.obj) for it in self.active("m1")], [("works at", "Rivermoor")])
        self.assertEqual(self.active("m2")[0].__dict__, second_snapshot)

    def test_editing_one_line_or_reordering_does_not_regenerate_unchanged_claim(self):
        self.notes([("m1", "Mira => works at => Larkhouse; Talia => owns => Sunbird")])
        self.reconcile()
        self.assertEqual(len(self.active("m1")), 2)
        unchanged = next(it for it in self.active("m1") if it.subj == "Talia")
        self.artifacts(unchanged)
        snapshot = copy.deepcopy(unchanged.__dict__)
        self.notes([("m1", "Talia => owns => Sunbird; Mira => left => Larkhouse")])
        self.reconcile(2)
        self.assertEqual(unchanged.__dict__, snapshot)
        self.assertEqual(len(self.active("m1")), 2)
        self.assertEqual(next(it for it in self.active("m1") if it.subj == "Mira").rel, "left")

    def test_removal_and_reappearance_never_resurrect_old_artifacts(self):
        self.notes([("m1", "Mira => works at => Larkhouse")])
        self.reconcile()
        self.assertEqual(len(self.active()), 1)
        old = self.active()[0]
        self.artifacts(old)
        self.notes([])
        self.reconcile(2)
        self.assertTrue(old.dead)
        self.notes([("m1", "Mira => works at => Larkhouse")])
        self.reconcile(3)
        revived = self.active()[0]
        self.assertEqual((revived.para, revived.qa, revived.held), ([], [], []))
        self.assertFalse(revived.trained)

    def test_legacy_card_migration_does_not_guess_a_note_identity_or_keep_old_qa(self):
        key = key_of("Mira", "Larkhouse")
        legacy = Item(key, "Mira", "Larkhouse", "works at", 1, days=1, nment=1,
                      line="Mira works at Larkhouse.", source="saved card note")
        self.artifacts(legacy)
        self.sl.items[key] = legacy
        self.sl.rem_pool = [{"q": "obsolete", "a": "Larkhouse", "keys": [key]}]
        self.notes([("m1", "Mira => left => Larkhouse"), ("m2", "Mira => owns => Larkhouse")])
        self.reconcile(2)
        self.assertEqual({it.rel for it in self.active()}, {"left", "owns"})
        self.assertTrue(legacy.dead)
        self.assertNotIn(key, self.sl.items)
        self.assertEqual((legacy.para, legacy.qa, legacy.held, self.sl.rem_pool), ([], [], [], []))
        self.assertTrue(any(it is legacy for it in self.sl.items.values()))

    def test_bound_card_context_uses_its_own_line_when_diary_has_another_relation(self):
        self.sl.diary = Diary({"diary": [{"role": "user", "text": "Mira lives in Larkhouse", "day": 1}]}, "Ben")
        self.notes([("m1", "Mira => left => Larkhouse")])
        self.reconcile()
        self.assertEqual(len(self.active()), 1)
        context = self.sl.ctx_of(self.active()[0], 1)
        self.assertIn("Mira left Larkhouse.", context)
        self.assertNotIn("lives in", context)
        self.sl.set_scale(1)
        self.sl.dream_templated(1, self.active(), Counter())
        self.assertIn("Mira left Larkhouse.", self.active()[0].para)
        self.assertFalse(any("lives in" in p for p in self.active()[0].para))

    def test_reconciled_checkpoint_reload_is_idempotent_and_retains_no_obsolete_replay(self):
        self.notes([("m1", "Mira => works at => Larkhouse")])
        self.reconcile()
        self.assertEqual(len(self.active()), 1)
        old = self.active()[0]
        self.artifacts(old)
        self.sl.rem_pool = [{"q": "obsolete", "a": "Larkhouse", "keys": [old.key]}]
        self.notes([("m1", "Mira => left => Larkhouse")])
        self.reconcile(2)
        self.sl.save_night()
        night, items = Checkpoints(self.env.paths).load()
        resumed = self.env.sleeper(self.env.backend())
        resumed.N = night
        resumed.load_items(items)
        resumed.diary = Diary({"diary": []}, "Ben")
        before = copy.deepcopy(resumed._items_data())
        resumed.card_notes(2, Counter())
        self.assertEqual(resumed._items_data(), before)
        self.assertEqual(resumed.rem_pool, [])
        live = [it for it in resumed.items.values() if not it.dead and getattr(it, "card_note_id", "")]
        self.assertEqual([(it.rel, it.para, it.qa, it.held) for it in live], [("left", [], [], [])])

    def test_dream_resume_splits_changed_claim_without_reshuffling_unchanged_holdout(self):
        self.env.cfg.card_shape = "templated12"
        self.env.cfg.dreamcheck = False
        self.notes([("m1", "Mira => works at => Larkhouse"), ("m2", "Talia => owns => Sunbird")])
        self.reconcile()
        for item in self.active():
            self.artifacts(item)
        unchanged = self.active("m2")[0]
        held_before = copy.deepcopy(unchanged.held)
        self.sl.N.update(holdout_done=True, card_holdout_pending=[], pre={"obsolete": True})
        self.notes([("m1", "Mira => left => Larkhouse"), ("m2", "Talia => owns => Sunbird")])
        self.sl.cache = GenCache(None)
        self.sl.state = self.sl.load_state()
        self.sl._train = lambda *args: (_ for _ in ()).throw(Stop("captured_before_training"))
        with self.assertRaises(Stop):
            self.sl._night({"diary": [], "dates": {}}, 1, False, {})
        changed = self.active("m1")[0]
        self.assertEqual(changed.rel, "left")
        self.assertTrue(changed.held)
        self.assertEqual(unchanged.held, held_before)
        self.assertNotIn("pre", self.sl.N)
        self.assertEqual(self.sl.N["card_holdout_pending"], [])

    def test_train_resume_retains_its_published_snapshot_until_the_next_tag_boundary(self):
        self.notes([("m1", "Mira => works at => Larkhouse")])
        self.reconcile()
        self.artifacts(self.active()[0])
        self.sl.N.update(phase="train", holdout_done=True, card_holdout_pending=[])
        self.sl.save_night()
        self.notes([("m1", "Mira => left => Larkhouse")])
        night, items = Checkpoints(self.env.paths).load()
        resumed = self.env.sleeper(self.env.backend())
        resumed.N = night
        resumed.load_items(items)
        resumed.diary = Diary({"diary": []}, "Ben")
        resumed.state = resumed.load_state()
        resumed._train = lambda *args: (_ for _ in ()).throw(Stop("captured_before_training"))
        with self.assertRaises(Stop):
            resumed._night({"diary": [], "dates": {}}, 1, False, {})
        live = [item for item in resumed.items.values() if not item.dead and item.card_note_id]
        self.assertEqual([item.rel for item in live], ["works at"])
        self.assertTrue(live[0].qa)


if __name__ == "__main__":
    unittest.main()
