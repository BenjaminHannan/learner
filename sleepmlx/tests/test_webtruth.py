"""Option B: unverified web facts never reach a training set. Synthetic temp files only; no model is loaded.

The planted-page test builds a userData folder with the real Desk code (desk/test/fixtures/plant-pages.js, needs node):
one FALSE fact from a single site, one TRUE fact from two independent sites, and Glim repeating both in chat.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from sleepmlx import diary as diary_mod
from sleepmlx import webtruth as wt
from sleepmlx.corpus import Diary
from sleepmlx.recipe import Item
from .helpers import Env

DESK = Path(__file__).resolve().parents[2] / "desk"
CASES = json.loads((DESK / "test" / "fixtures" / "webtruth-cases.json").read_text())
FALSE_CARD = "Luma Ferry => home dock => Mossbank"
TRUE_CARD = "Tidewick Light => keeper => Odile Marsh"
NODE = shutil.which("node")


def plant(userdata: Path):
    subprocess.run([NODE, str(DESK / "test" / "fixtures" / "plant-pages.js"), str(userdata)], check=True, cwd=str(DESK))


class SharedCaseTests(unittest.TestCase):
    def test_domains_and_normalisation_match_the_desk(self):
        for url, want in CASES["domains"]:
            self.assertEqual(wt.registrable_domain(url), want, url)
        for text, want in CASES["norm"]:
            self.assertEqual(wt.norm_claim(text), want, text)


@unittest.skipUnless(NODE, "node is needed to build the planted userData with the real Desk code")
class PlantedPageTests(unittest.TestCase):
    def setUp(self):
        self.env = Env(days=())
        self.addCleanup(self.env.close)
        self.ud = self.env.paths.userdata_dir
        plant(self.ud)

    def texts(self, notes):
        return {n["text"] for n in notes}

    def test_note_filter_keeps_only_the_verified_fact(self):
        self.assertEqual(self.texts(wt.trainable_notes(self.ud)), {TRUE_CARD})
        self.assertEqual(self.texts(wt.blocked_notes(self.ud)), {FALSE_CARD})

    def test_sleeper_cards_only_the_true_fact(self):
        sl = self.env.sleeper(self.env.backend())
        sl.load_items()
        sl.diary = Diary({"diary": []}, "Ben")
        sl.N = {"id": "n", "day": 1, "date": "2026-10-20", "phase": "dream", "done_steps": 0, "stats": {}, "rem_done": [], "scale": 1}
        st = Counter()
        sl.card_notes(1, st)
        live = [it for it in sl.items.values() if not it.dead]
        self.assertEqual({(it.subj, it.obj) for it in live}, {("Tidewick Light", "Odile Marsh")})
        self.assertNotIn("Mossbank", json.dumps(sl._items_data()))

    def test_old_checkpoint_rem_and_holdout_rows_are_purged(self):
        sl = self.env.sleeper(self.env.backend())
        sl.load_items()
        sl.N = {"id": "n", "day": 1, "date": "2026-10-20", "phase": "train", "done_steps": 0, "stats": {}, "rem_done": [], "scale": 1}
        bad_id = next(n["id"] for n in wt.blocked_notes(self.ud))
        key = "oldcard|" + bad_id
        # a checkpoint written before this rule: the false card was dreamed, held out and chained into REM
        sl.items[key] = Item(key, "Luma Ferry", "Mossbank", "home dock", 1, first=1, days=1, nment=1, imp=True, line="Luma Ferry home dock Mossbank.",
                             source="saved card note", card_note_id=bad_id, sig="s", para=["Luma Ferry docks at Mossbank."],
                             qa=[["Where does Luma Ferry dock?", "Mossbank"]], held=[{"q": "Dock?", "a": "Mossbank", "night": 1, "dir": "forward"}], trained=True)
        sl.rem_pool = [{"q": "Dock of the ferry?", "a": "Mossbank", "keys": [key], "kind": "chain", "night": 1, "cycle": 0}]
        st = Counter()
        sl.purge_unverified_web(st)
        it = sl.items[key]
        self.assertTrue(it.dead)
        self.assertEqual((it.para, it.qa, it.held, sl.rem_pool), ([], [], [], []))
        self.assertEqual(st["web_unverified_retired"], 1)
        # the retired shell keeps its identity (as for any retired card) but nothing that trains: no live item, card, held row or REM row
        live = {k: v for k, v in sl._items_data()["items"].items() if not v["dead"]}
        self.assertNotIn("Mossbank", json.dumps([live, sl.rem_pool]))

    def test_chat_repeat_of_the_false_fact_never_reaches_diary_training_rows(self):
        raw = self.ud / "raw"
        with_guard = diary_mod.build_week(raw, "Ben", guard=wt.DiaryGuard(self.ud))
        without = diary_mod.build_week(raw, "Ben")
        self.assertIn("Mossbank", json.dumps(without["diary"]))                 # the leak exists without the guard
        rows = with_guard["diary"]
        self.assertNotIn("Mossbank", " ".join(r["text"] for r in rows if r["role"] == "assistant"))
        self.assertTrue(any("Odile Marsh keeps Tidewick Light." == r["text"] for r in rows if r["role"] == "assistant"))   # the verified answer stays
        self.assertTrue(any(r["role"] == "user" and "jazz" in r["text"] for r in rows))
        self.assertEqual(Diary(with_guard, "Ben").turns[0]["role"], "user")

    def test_desk_flag_file_drops_an_answer_python_could_not_match(self):
        answer = "It anchors off the old mill at night."
        (self.ud / "unverified-assertions.jsonl").write_text(json.dumps({"answer_sha256": hashlib.sha256(answer.encode()).hexdigest()}) + "\n")
        guard = wt.DiaryGuard(self.ud)
        self.assertTrue(guard.drops("Where does it dock?", answer))
        self.assertFalse(guard.drops("Hi", "Hello there."))

    def test_planted_pass_mark(self):
        """Pass = 0 false facts in any training set, and the true fact is there."""
        sl = self.env.sleeper(self.env.backend())
        sl.load_items()
        sl.diary = Diary({"diary": []}, "Ben")
        sl.N = {"id": "n", "day": 1, "date": "2026-10-20", "phase": "dream", "done_steps": 0, "stats": {}, "rem_done": [], "scale": 1}
        sl.card_notes(1, Counter())
        sl.purge_unverified_web(Counter())
        week = diary_mod.build_week(self.ud / "raw", "Ben", guard=wt.DiaryGuard(self.ud))
        training = json.dumps([sl._items_data(), week["diary"], [n["text"] for n in wt.trainable_notes(self.ud)]])
        self.assertEqual(training.count("Mossbank"), 0)
        self.assertGreater(training.count("Odile Marsh"), 0)


class FailClosedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ud = Path(self.tmp.name)

    def test_legacy_untagged_cards_and_skill_notes_are_blocked_but_personal_notes_pass(self):
        (self.ud / "memory.md").write_text(
            "- Old Lighthouse => keeper => Pim | topic: card | id: mlegacy1 | updated: 2026-01-01\n"
            "- Study tip: spaced repetition | topic: skill: memory | id: m2 | updated: 2026-01-01\n"
            "- Ben likes jazz | topic: preference | id: m3 | updated: 2026-01-01\n"
            "- Handwritten card => is => fine | topic: card | updated: 2026-01-01\n")
        self.assertEqual({n["text"] for n in wt.trainable_notes(self.ud)}, {"Ben likes jazz", "Handwritten card => is => fine"})

    def test_local_origin_claim_is_trainable(self):
        (self.ud / "memory.md").write_text("- Rowan => plays => oboe | topic: card | id: m9 | updated: 2026-01-01\n")
        self.assertEqual(wt.trainable_notes(self.ud), [])
        (self.ud / "memory-local-origin.jsonl").write_text(json.dumps({"note_id": "m9", "claim_norm": wt.norm_claim("Rowan => plays => oboe")}) + "\n")
        self.assertEqual(len(wt.trainable_notes(self.ud)), 1)

    def test_damaged_ledger_blocks_glim_saved_notes(self):
        (self.ud / "memory.md").write_text("- Ben likes jazz | topic: preference | id: m3 | updated: 2026-01-01\n")
        self.assertEqual(len(wt.trainable_notes(self.ud)), 1)
        (self.ud / "memory-provenance.jsonl").write_text("{broken\n")
        self.assertEqual(wt.trainable_notes(self.ud), [])

    def test_hedge_does_not_excuse_a_turn_from_training(self):
        notes = [{"id": "m1", "topic": "card", "text": FALSE_CARD}]
        hedged = "One site claims it docks at Mossbank, but I haven't confirmed it."
        self.assertEqual(len(wt.asserted_claims(hedged, "Where does the Luma Ferry dock?", notes, strict=True)), 1)
        self.assertEqual(len(wt.asserted_claims(hedged, "Where does the Luma Ferry dock?", notes, strict=False)), 0)


if __name__ == "__main__":
    unittest.main()
