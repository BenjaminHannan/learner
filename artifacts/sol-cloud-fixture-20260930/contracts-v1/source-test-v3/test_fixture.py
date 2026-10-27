"""Stdlib fixture mechanics tests; numeric test doubles, never training material.

No real model or optimizer is imported or called. Test-only loader bytes return
numeric records; they are not asserted to be human source evidence.
"""
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import sol_cloud_day_adapter_v1 as adapter
import sol_cloud_fixture_v1 as fixture


class FixtureContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sol-cloud-fixture-contract-")
        self.root = Path(self.temporary.name)
        self.rows = [{"id": "numeric-unit-0", "question": "7", "context": "[3,4]",
                      "target_text": "7", "answer_text": "7", "accepted_human_answers": ["7"],
                      "split": "train", "source_sha256": "1" * 64}]
        packet = self.root / "numeric-test-packet.json"
        packet.write_text(json.dumps({"rows": self.rows}), encoding="utf-8")
        manifest = self.root / "numeric-test-manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        loader = self.root / "numeric_test_loader.py"
        loader.write_text("import json\nfrom pathlib import Path\ndef load_packet(path, expected_sha256, manifest_path=None, manifest_sha256=None):\n    return json.loads(Path(path).read_text(encoding='utf-8'))['rows']\n", encoding="utf-8")
        bundle = self.root / "numeric-test-bundle.json"
        bundle.write_text("{}", encoding="utf-8")
        self.source = {"packet": fixture.pin(packet), "manifest": fixture.pin(manifest), "loader": fixture.pin(loader)}
        self.bundle = fixture.pin(bundle)
        self.state = self.root / "state"
        self.store = fixture.FixtureStore(self.state, allowed_root=self.root)
        self.spec = {"source": self.source, "bundle": self.bundle, "state_dir": str(self.state), "fixture_row_ids": [self.rows[0]["id"]],
                     "idle_seconds": 5, "batch_path": str(self.root / "batch.json"), "claim_id": "numeric-unit-claim"}

    def tearDown(self):
        self.temporary.cleanup()

    def capture(self):
        with patch.object(fixture.time, "time", return_value=100):
            return self.store.capture(self.source, self.bundle, self.spec["fixture_row_ids"])

    def snapshot(self):
        with patch.object(fixture.time, "time", return_value=106):
            return self.store.snapshot(self.spec, allowed_root=self.root)

    def load(self, claim):
        return adapter.inspect_rows(claim["batch"]["path"], claim["batch"]["sha256"],
                                 self.bundle["sha256"], allowed_root=self.root)

    def test_capture_idle_batch_and_original_identity(self):
        capture = self.capture()
        self.assertFalse(capture["actual_user_day"])
        with patch.object(fixture.time, "time", return_value=104):
            self.assertFalse(self.store.snapshot(self.spec, allowed_root=self.root)["ready"])
        claim = self.snapshot()
        rows = self.load(claim)
        self.assertEqual(len(rows), 1)
        for key, value in self.rows[0].items():
            self.assertEqual(rows[0][key], value)
        self.assertFalse(rows[0]["actual_user_day"])
        self.assertEqual(rows[0]["source_row_id"], self.rows[0]["id"])

    def test_source_drift_and_bundle_mismatch_refuse(self):
        self.capture()
        claim = self.snapshot()
        with self.assertRaises(adapter.FixtureError):
            adapter.load_rows(claim["batch"]["path"], claim["batch"]["sha256"], "0" * 64, allowed_root=self.root)
        Path(self.source["packet"]["path"]).write_text("{}", encoding="utf-8")
        with self.assertRaises(adapter.FixtureError):
            self.load(claim)

    def test_journal_tamper_refuses_even_when_packet_matches(self):
        self.capture()
        claim = self.snapshot()
        with self.store.connect() as db:
            db.execute("UPDATE captures SET row_json='{}'")
        with self.assertRaises(adapter.FixtureError):
            self.load(claim)

    def test_duplicate_capture_snapshot_and_dispatch_refuse(self):
        self.capture()
        with self.assertRaises(adapter.FixtureError):
            self.capture()
        claim = self.snapshot()
        with self.assertRaises(adapter.FixtureError):
            self.snapshot()
        with patch.object(fixture.time, "time", return_value=106):
            self.store.begin_dispatch(claim, 5)
            with self.assertRaises(adapter.FixtureError):
                self.store.begin_dispatch(claim, 5)
        self.store.finish_dispatch(claim["claim_id"], "failed")
        with patch.object(fixture.time, "time", return_value=106):
            with self.assertRaises(adapter.FixtureError):
                self.store.begin_dispatch(claim, 5)

    def test_activity_invalidates_saved_claim_and_worker_admission(self):
        self.capture()
        claim = self.snapshot()
        with patch.object(fixture.time, "time", return_value=106):
            self.store.begin_dispatch(claim, 5)
        with patch.object(fixture.time, "time", return_value=107):
            self.store.activity()
            self.assertFalse(self.store.unchanged(claim["capture_revision"]))
            with self.assertRaises(adapter.FixtureError):
                self.store.begin_dispatch(claim, 5)
        with self.assertRaises(adapter.FixtureError):
            adapter.load_rows(claim["batch"]["path"], claim["batch"]["sha256"],
                              self.bundle["sha256"], allowed_root=self.root)
        self.assertEqual(self.load(claim)[0]["id"], self.rows[0]["id"])

    def test_readonly_admission_under_writer_lock(self):
        self.capture()
        claim = self.snapshot()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.assertEqual(self.load(claim)[0]["id"], self.rows[0]["id"])

    def test_batch_claim_missing_refuses(self):
        self.capture()
        claim = self.snapshot()
        with self.store.connect() as db:
            db.execute("DELETE FROM claims")
        with self.assertRaises(adapter.FixtureError):
            self.load(claim)

    def test_watcher_gate_requires_exact_tree(self):
        for environment in ({}, {"JOB": "contract", "TREE": str(self.root)}):
            with patch.dict(os.environ, environment, clear=True):
                with self.assertRaises(adapter.FixtureError):
                    fixture.watcher_required()

    def test_no_truthy_shortcut_for_rollback(self):
        candidate = self.root / "candidate.json"
        candidate.write_text("{}", encoding="utf-8")
        validation = self.root / "validation.json"
        validation.write_text("{}", encoding="utf-8")
        receipt = self.root / "rollback.json"
        raw = {"schema": "sol.cloud.candidate-disposition.v1", "actual_user_day": False,
               "activated": False, "disposition": "rollback", "operation": "reject-candidate-retain-prior",
               "previous_bundle_sha256": self.bundle["sha256"],
               "pointer_before": {"revision": 0}, "pointer_after": {"revision": 0},
               "prior_pointer_unchanged": True, "previous_bundle_unchanged": True,
               "mechanics_complete": True, "candidate_manifest": fixture.pin(candidate),
               "validation": fixture.pin(validation)}
        receipt.write_text(json.dumps(raw), encoding="utf-8")
        fixture.validate_disposition(receipt, self.bundle)
        raw["pointer_after"] = {"revision": 1}
        receipt.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(adapter.FixtureError):
            fixture.validate_disposition(receipt, self.bundle)
        raw["pointer_after"] = raw["pointer_before"]
        raw["actual_user_day"] = 0
        receipt.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(adapter.FixtureError):
            fixture.validate_disposition(receipt, self.bundle)

    def test_dispatch_activity_interrupt_preserves_failure_and_consumes_claim(self):
        self.capture()
        claim = self.snapshot()
        spec = dict(self.spec, pipeline_seconds=5, dependency_pins=[],
                    pipeline={"entrypoint": fixture.pin(ROOT / "scripts/sol_cloud_fixture_v1.py"),
                              "argv": ["{python}", "unexecuted-numeric-test.py", "--day-rows", "{day_batch}",
                                       "--day-sha256", "{day_batch_sha256}"]},
                    dispatch_log=str(self.root / "dispatch.log"), failure_receipt=str(self.root / "failure.json"),
                    completion_receipt=str(self.root / "complete.json"), rollback_receipt=str(self.root / "rollback.json"))
        store = self.store

        class NoModelProcess:
            returncode = None
            def poll(self):
                if self.returncode is None:
                    store.activity()
                return self.returncode
            def terminate(self):
                self.returncode = -15
            def wait(self, timeout=None):
                return self.returncode
            def kill(self):
                self.returncode = -9

        original_owned = adapter.owned
        original_load = adapter.load_rows
        original_inspect = adapter.inspect_rows
        with patch.object(fixture, "owned", side_effect=lambda p: original_owned(p, allowed_root=self.root)), \
             patch.object(fixture, "FixtureStore", return_value=self.store), \
             patch.object(fixture, "watcher_required"), \
             patch.object(fixture, "inspect_rows", side_effect=lambda p, h, b: original_inspect(p, h, b, allowed_root=self.root)), \
             patch.object(fixture, "load_rows", side_effect=lambda p, h, b: original_load(p, h, b, allowed_root=self.root)), \
             patch.object(fixture.subprocess, "Popen", return_value=NoModelProcess()) as popen:
            with self.assertRaisesRegex(adapter.FixtureError, "interruption"):
                fixture.dispatch(spec, claim)
            self.assertEqual(popen.call_count, 1)
        failure = json.loads(Path(spec["failure_receipt"]).read_text(encoding="utf-8"))
        self.assertFalse(failure["actual_user_day"])
        self.assertFalse(failure["activated"])
        self.assertFalse(Path(spec["completion_receipt"]).exists())
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT status FROM claims").fetchone()[0], "failed")

    def test_pinned_spec_rejects_shell_and_unbound_day_input(self):
        spec = dict(self.spec, schema=fixture.SPEC_SCHEMA, actual_user_day=False, activation_allowed=False,
                    wait_seconds=10, pipeline_seconds=5, dependency_pins=[],
                    pipeline={"entrypoint": fixture.pin(ROOT / "scripts/sol_cloud_fixture_v1.py"),
                              "argv": ["{python}", str(ROOT / "scripts/sol_cloud_fixture_v1.py"),
                                       "--day-rows", "{day_batch}", "--day-sha256", "{day_batch_sha256}"]})
        for key in ("claim_receipt", "completion_receipt", "failure_receipt", "dispatch_log", "rollback_receipt"):
            spec[key] = str(self.root / (key + ".json"))
        spec["rollback_receipt"] = str(ROOT / "artifacts/sol-cloud-night-20260930/numeric-test-not-executed/rollback.json")
        path = self.root / "spec.json"
        original_owned = adapter.owned
        with patch.object(fixture, "owned", side_effect=lambda p: original_owned(p, allowed_root=self.root)):
            path.write_text(json.dumps(spec), encoding="utf-8")
            fixture.checked_spec(path, adapter.sha(path))
            spec["pipeline"]["argv"][0] = "bash"
            path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(adapter.FixtureError):
                fixture.checked_spec(path, adapter.sha(path))
            spec["pipeline"]["argv"][0] = "{python}"
            spec["pipeline"]["argv"][-1] = "0" * 64
            path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(adapter.FixtureError):
                fixture.checked_spec(path, adapter.sha(path))

    def test_sibling_night_receipt_read_path_is_narrow(self):
        path = ROOT / "artifacts/sol-cloud-night-20260930/unique-unexecuted-test/rollback.json"
        self.assertEqual(fixture.rollback_path(path), path.resolve())
        with self.assertRaises(adapter.FixtureError):
            fixture.rollback_path(ROOT / "artifacts/unrelated/rollback.json")
        with self.assertRaises(adapter.FixtureError):
            fixture.rollback_path(path.with_name("candidate-manifest.json"))

    def test_forbidden_paths_refuse_before_hash_or_file_open(self):
        names = ("DEV100.json", "stop88.json", "pairs.json", "train-v1.1.json",
                 "human-documents/record.json", "uncle-questions/record.json", "readpanel320/record.json")
        with patch.object(adapter, "sha", side_effect=AssertionError("forbidden hash accessed")) as digest, \
             patch.object(Path, "is_file", side_effect=AssertionError("forbidden filesystem accessed")) as exists:
            for name in names:
                with self.subTest(name=name):
                    with self.assertRaisesRegex(adapter.FixtureError, "forbidden"):
                        adapter.verify_pin({"path": str(self.root / name), "sha256": "0" * 64})
            self.assertEqual(digest.call_count, 0)
            self.assertEqual(exists.call_count, 0)

    def test_optimizer_admission_requires_running_not_consumed_claim(self):
        self.capture()
        claim = self.snapshot()
        def optimizer_rows():
            return adapter.load_rows(claim["batch"]["path"], claim["batch"]["sha256"],
                                     self.bundle["sha256"], allowed_root=self.root)
        with self.assertRaisesRegex(adapter.FixtureError, "running"):
            optimizer_rows()
        with patch.object(fixture.time, "time", return_value=106):
            self.store.begin_dispatch(claim, 5)
        self.assertEqual(optimizer_rows()[0]["id"], self.rows[0]["id"])
        self.store.finish_dispatch(claim["claim_id"], "complete")
        with self.assertRaisesRegex(adapter.FixtureError, "running"):
            optimizer_rows()
        self.assertEqual(self.load(claim)[0]["id"], self.rows[0]["id"])
        with self.store.connect() as db:
            db.execute("UPDATE claims SET status='failed'")
        with self.assertRaisesRegex(adapter.FixtureError, "running"):
            optimizer_rows()


if __name__ == "__main__":
    unittest.main()
