import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from memorylab.storage import BoundedFile, Budget, BudgetError


class BudgetTests(unittest.TestCase):
    def make_budget(self, root):
        return Budget(
            root,
            hard=16_000_000,
            steady=12_000_000,
            free_floor=0,
        )

    def write_ledger(self, budget, active):
        budget.ledger_path.write_text(json.dumps({
            "active": active,
            "reservation_peak_bytes": 0,
            "sampled_peak_bytes": 0,
        }))

    def owned_entry(self, *, host="host-a", pid=123, name="stale", cap=4096,
                    process_start_identity="procfs-start-ticks:10"):
        return {
            "name": name,
            "cap": cap,
            "owner_version": 1,
            "host": host,
            "pid": pid,
            "process_start_identity": process_start_identity,
            "created_ns": 1,
        }

    def test_scan_and_reservation_lifecycle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            payload = root / "payload.bin"
            payload.write_bytes(b"scan-me")

            budget = self.make_budget(root)
            report = budget.scan()
            self.assertGreaterEqual(report["logical_bytes"], payload.stat().st_size)
            self.assertGreaterEqual(report["accounted_bytes"], report["logical_bytes"])
            self.assertEqual(report["unregistered_symlinks"], [])

            with budget.reserve("unit-test", 4096) as ticket:
                active = budget.audit()["active_reservations"]
                self.assertIn(ticket, active)
                self.assertEqual(active[ticket]["name"], "unit-test")
                self.assertEqual(active[ticket]["cap"], 4096)
                self.assertEqual(active[ticket]["owner_version"], 1)
                self.assertTrue(active[ticket]["host"])
                self.assertGreater(active[ticket]["pid"], 0)
                self.assertIn("process_start_identity", active[ticket])

            self.assertEqual(budget.audit()["active_reservations"], {})

    def test_dead_same_host_reservation_is_reaped_and_audited(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            budget = self.make_budget(root)
            self.write_ledger(budget, {"dead-ticket": self.owned_entry()})

            with mock.patch("memorylab.storage._host_identity", return_value="host-a"), \
                    mock.patch("memorylab.storage._pid_liveness", return_value="dead"):
                report = budget.audit()

            self.assertEqual(report["active_reservations"], {})
            self.assertEqual(len(report["reaped_reservations"]), 1)
            self.assertEqual(report["reaped_reservations"][0]["ticket"], "dead-ticket")
            self.assertEqual(report["reaped_reservations"][0]["cap"], 4096)

    def test_live_same_host_reservation_is_preserved_even_on_pid_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            budget = self.make_budget(root)
            self.write_ledger(budget, {"live-ticket": self.owned_entry()})

            with mock.patch("memorylab.storage._host_identity", return_value="host-a"), \
                    mock.patch("memorylab.storage._pid_liveness", return_value="alive"), \
                    mock.patch("memorylab.storage._process_start_identity",
                               return_value="procfs-start-ticks:999"):
                report = budget.audit()

            self.assertIn("live-ticket", report["active_reservations"])
            self.assertEqual(report["reaped_reservations"], [])

    def test_foreign_host_reservation_is_never_probed_or_reaped(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            budget = self.make_budget(root)
            self.write_ledger(
                budget, {"foreign-ticket": self.owned_entry(host="host-b")}
            )

            with mock.patch("memorylab.storage._host_identity", return_value="host-a"), \
                    mock.patch("memorylab.storage._pid_liveness",
                               side_effect=AssertionError("foreign PID must not be probed")):
                report = budget.audit()

            self.assertIn("foreign-ticket", report["active_reservations"])

    def test_permission_uncertain_owner_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            budget = self.make_budget(root)
            self.write_ledger(budget, {"uncertain-ticket": self.owned_entry()})

            with mock.patch("memorylab.storage._host_identity", return_value="host-a"), \
                    mock.patch("memorylab.storage._pid_liveness", return_value="unknown"):
                report = budget.audit()

            self.assertIn("uncertain-ticket", report["active_reservations"])

    def test_malformed_and_legacy_entries_fail_closed_for_reaping(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            budget = self.make_budget(root)
            malformed = self.owned_entry()
            malformed["pid"] = "123"
            legacy = {"name": "legacy", "cap": 2048, "pid": 456, "created_ns": 1}
            self.write_ledger(budget, {"malformed": malformed, "legacy": legacy})

            with mock.patch("memorylab.storage._host_identity", return_value="host-a"), \
                    mock.patch("memorylab.storage._pid_liveness",
                               side_effect=AssertionError("invalid owner must not be probed")):
                report = budget.audit()

            self.assertIn("malformed", report["active_reservations"])
            self.assertIn("legacy", report["active_reservations"])
            self.assertEqual(report["reaped_reservations"], [])

    def test_reaped_capacity_is_available_to_next_reservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            budget = self.make_budget(root)
            stale_cap = budget.steady - budget.CONTROL_ALLOWANCE - 8192
            self.write_ledger(
                budget, {"dead-ticket": self.owned_entry(cap=stale_cap)}
            )

            def liveness(pid):
                return "dead" if pid == 123 else "alive"

            with mock.patch("memorylab.storage._host_identity", return_value="host-a"), \
                    mock.patch("memorylab.storage._pid_liveness", side_effect=liveness), \
                    mock.patch("memorylab.storage._process_start_identity", return_value=None):
                with budget.reserve("replacement", 4096) as ticket:
                    report = budget.audit()
                    self.assertIn(ticket, report["active_reservations"])
                    self.assertNotIn("dead-ticket", report["active_reservations"])
                    self.assertEqual(report["reaped_reservations"][0]["ticket"], "dead-ticket")

    def test_atomic_write_is_bounded_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            budget = self.make_budget(root)

            target = budget.atomic_write(
                "artifacts/result.bin", 5, lambda handle: handle.write(b"12345")
            )
            self.assertEqual(target.read_bytes(), b"12345")

            with self.assertRaisesRegex(BudgetError, "Refusing to overwrite"):
                budget.atomic_write(
                    "artifacts/result.bin", 5, lambda handle: handle.write(b"other")
                )
            self.assertEqual(target.read_bytes(), b"12345")

            with self.assertRaisesRegex(BudgetError, "exceed 4 bytes"):
                budget.atomic_write(
                    "artifacts/too-large.bin", 4, lambda handle: handle.write(b"12345")
                )
            self.assertFalse((root / "artifacts" / "too-large.bin").exists())
            self.assertEqual(list((root / "artifacts").glob(".staging-*")), [])

    def test_over_limit_reservation_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            budget = self.make_budget(root)

            with self.assertRaisesRegex(BudgetError, "Peak reservation"):
                with budget.reserve("too-large", budget.steady):
                    self.fail("over-limit reservation was admitted")
            self.assertEqual(budget.audit()["active_reservations"], {})

    def test_unregistered_external_symlink_blocks_reservations(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "project"
            external = base / "external"
            root.mkdir()
            external.mkdir()
            (external / "shared.bin").write_bytes(b"outside-project")
            link = root / "external-link"
            link.symlink_to(external, target_is_directory=True)

            budget = self.make_budget(root)
            report = budget.scan()
            self.assertEqual(len(report["unregistered_symlinks"]), 1)
            self.assertEqual(
                Path(report["unregistered_symlinks"][0]["link"]),
                link.parent.resolve() / link.name,
            )
            self.assertEqual(
                Path(report["unregistered_symlinks"][0]["target"]), external.resolve()
            )

            with self.assertRaisesRegex(BudgetError, "Register external symlink targets"):
                with budget.reserve("blocked-by-symlink", 1024):
                    self.fail("reservation should not be admitted")


class BoundedFileTests(unittest.TestCase):
    def test_exact_limit_allowed_and_overrun_rejected_before_write(self):
        raw = io.BytesIO()
        bounded = BoundedFile(raw, 5)

        self.assertEqual(bounded.write(b"123"), 3)
        self.assertEqual(bounded.write(b"45"), 2)
        self.assertEqual(raw.getvalue(), b"12345")

        with self.assertRaisesRegex(BudgetError, "exceed 5 bytes"):
            bounded.write(b"6")
        self.assertEqual(raw.getvalue(), b"12345")
        self.assertEqual(bounded.tell(), 5)

    def test_seek_uses_reserved_extent_and_high_water(self):
        raw = io.BytesIO()
        bounded = BoundedFile(raw, 5)
        bounded.write(b"12345")

        self.assertEqual(bounded.seek(-1, 2), 4)
        bounded.write(b"X")
        self.assertEqual(raw.getvalue(), b"1234X")
        self.assertEqual(bounded.seek(-5, 2), 0)

        with self.assertRaisesRegex(BudgetError, "Seek outside reserved extent"):
            bounded.seek(6)
        with self.assertRaisesRegex(BudgetError, "Seek outside reserved extent"):
            bounded.seek(-1)

    def test_limit_must_be_nonnegative_integer(self):
        with self.assertRaises(ValueError):
            BoundedFile(io.BytesIO(), -1)
        with self.assertRaises(ValueError):
            BoundedFile(io.BytesIO(), 1.5)


if __name__ == "__main__":
    unittest.main()
