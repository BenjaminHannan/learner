"""Record-only joins and transaction failures; no model or user files involved."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from sleepmlx.lessons import read_notes
from sleepmlx.provenance import audit_notes, fact_hash, read_ledger


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fact = "Luma Ferry uses Mossbank as its home dock."
        self.note(self.fact)

    def tearDown(self):
        self.tmp.cleanup()

    def note(self, text, *, topic="card", note_id="m1"):
        (self.root / "memory.md").write_text(f"# Notes\n- {text} | topic: {topic} | id: {note_id} | updated: 2026-10-29\n")

    def prepare(self, *, tx="tx1", text=None, topic="card", status="attributed", expires=None):
        quote = "The fictional Luma Ferry uses Mossbank as its home dock."
        return {"version": 1, "type": "research-note-prepare", "tx_id": tx, "note_id": "m1",
                "fact_sha256": fact_hash(text or self.fact), "topic": topic,
                "origin": "learn-research", "context": {"run_id": "run1", "thread_id": "thread1", "helper_id": "helper1"},
                "attribution": {"status": status, "verified": False, "reason": None if status == "attributed" else "no_source_read",
                                "source": {"read_id": "read_0123456789abcdef", "tool_call_id": "call1", "url": "https://example.test/reference",
                                           "page": 1, "read_at": "2026-10-29T00:00:00Z", "quote": quote,
                                           "quote_sha256": fact_hash(quote), "visible_body_sha256": fact_hash(quote)} if status == "attributed" else None},
                "expires": expires, "prepared_at": "2026-10-29T00:00:00Z"}

    @staticmethod
    def commit(tx="tx1"):
        return {"version": 1, "type": "research-note-commit", "tx_id": tx, "committed_at": "2026-10-29T00:00:01Z"}

    def ledger(self, *rows):
        (self.root / "memory-provenance.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))

    def state(self):
        return audit_notes(self.root, today="2026-10-29")["notes"][0]

    def test_committed_attribute_is_never_verification_or_training_admission(self):
        self.ledger(self.prepare(expires="2026-10-28"), self.commit())
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        report = audit_notes(self.root, today="2026-10-29")
        self.assertEqual(report["counts"], {"attributed": 1})
        self.assertEqual(report["known_research_count"], 1)
        self.assertEqual(report["would_require_support_review"], 1)
        self.assertFalse(report["eligibility_enforced"])
        self.assertEqual(report["support_status"], "not_evaluated")
        self.assertFalse(report["notes"][0]["verified"])
        self.assertTrue(report["notes"][0]["expired"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        self.assertEqual(len(read_notes(self.root)), 1) # no expiry/quarantine activation

    def test_pending_new_version_and_failed_repeat_preserve_prior_committed_version(self):
        self.ledger(self.prepare())
        self.assertEqual(self.state()["provenance_status"], "pending")
        self.ledger(self.prepare(), self.commit(), self.prepare(tx="failed-repeat", status="unattributed"))
        self.assertEqual(self.state()["provenance_status"], "attributed")
        changed = "Luma Ferry uses Pinebank as its home dock."
        self.note(changed)
        self.ledger(self.prepare(), self.commit(), self.prepare(tx="new-body", text=changed))
        self.assertEqual(self.state()["provenance_status"], "pending")

    def test_exact_text_id_and_topic_binding_prevents_inherited_support_after_edit(self):
        self.ledger(self.prepare(), self.commit())
        for text, topic, note_id, state in [(self.fact.replace("uses ", "uses  "), "card", "m1", "stale"),
                                           (self.fact, "skill: ferries", "m1", "stale"),
                                           (self.fact, "card", "independent", "legacy")]:
            self.note(text, topic=topic, note_id=note_id)
            self.assertEqual(self.state()["provenance_status"], state)
        self.assertIsNone(self.state()["origin"])

    def test_known_research_origin_is_independent_of_card_topic(self):
        for topic in ("card", "skill: ferries", "ferries", ""):
            self.note(self.fact, topic=topic)
            self.ledger(self.prepare(topic=topic or None, status="unattributed"), self.commit())
            note = self.state()
            self.assertEqual(note["provenance_status"], "unattributed")
            self.assertTrue(note["known_research"])

    def test_legacy_unknown_origin_and_default_reader_behavior_are_preserved(self):
        self.assertEqual(self.state()["provenance_status"], "legacy")
        self.assertIsNone(self.state()["origin"])
        self.note("Luma  Ferry | a hand-written suffix")
        normal = read_notes(self.root)[0]
        exact = read_notes(self.root, exact_text=True)[0]
        self.assertEqual(normal["text"], "Luma Ferry")
        self.assertNotIn("text_exact", normal)
        self.assertEqual(exact["text"], normal["text"])
        self.assertEqual(exact["text_exact"], "Luma  Ferry / a hand-written suffix")

    def test_malformed_truncated_or_falsely_verified_ledger_is_unavailable(self):
        ledger_path = self.root / "memory-provenance.jsonl"
        malformed = [b'{"version":1}\n', json.dumps(self.prepare()).encode(), b'\xff\n', b'{broken\n']
        for body in malformed:
            ledger_path.write_bytes(body)
            self.assertEqual(self.state()["provenance_status"], "unavailable")
            self.assertIsNone(self.state()["origin"])
        for mutate in (lambda r: r["attribution"].update(verified=True),
                       lambda r: r["attribution"]["source"].update(quote="Unmatched quote"),
                       lambda r: r["attribution"]["source"].update(url=[]),
                       lambda r: r.update(origin="user"),
                       lambda r: r.update(expires="2027-02-29")):
            row = copy.deepcopy(self.prepare()); mutate(row)
            self.ledger(row, self.commit())
            self.assertEqual(read_ledger(self.root)["status"], "unavailable")

    @unittest.skipUnless(shutil.which("node"), "Node is required for the cross-language ledger fixture")
    def test_actual_node_memory_ledger_matches_python_after_pipe_and_unicode_storage(self):
        repo = Path(__file__).resolve().parents[2]
        script = """
const {createMemory}=require('./desk/src/memory');
const {EvidenceRegistry,attachSourceRead}=require('./desk/src/evidence');
const {looksSecret}=require('./desk/src/memory');
const memory=createMemory(process.argv[1]);
const body='The fictional Luma Ferry uses Mossbank as its home dock.';
const observed=attachSourceRead({text:body},{url:'https://example.test/reference',body,bodyStart:0,page:1,readAt:Date.now()});
const registry=new EvidenceRegistry({enabled:true,isSecret:looksSecret});
const read=registry.recordRead('browser_read',observed,'call1',1000);
const research=registry.metadata({source_read_id:read.readId,source_quote:body});
const result=memory.save('Luma Ferry uses Mossbank | by the café inlet.','skill: ferries',{research});
if(!result.ok||result.provenance.status!=='attributed')throw Error(JSON.stringify(result));
"""
        subprocess.run([shutil.which("node"), "-e", script, str(self.root)], cwd=repo, check=True, capture_output=True, text=True)
        report = audit_notes(self.root)
        self.assertEqual(report["ledger_status"], "ok")
        actual = next(n for n in report["notes"] if n["topic"] == "skill: ferries")
        self.assertEqual(actual["provenance_status"], "attributed")
        self.assertEqual(actual["fact_sha256"], fact_hash("Luma Ferry uses Mossbank / by the café inlet."))


if __name__ == "__main__":
    unittest.main()
