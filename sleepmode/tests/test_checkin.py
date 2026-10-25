import os
import unittest

from sleepmode import checkin, notify
from sleepmode.checkin import Item
from sleepmode.state import State
from sleepmode.tests.helpers import TmpCase, make_cfg


class FakeScanner:
    def __init__(self, name, items=None, fail=False):
        self.name, self.items, self.fail = name, items or [], fail

    def scan(self, cfg):
        if self.fail:
            raise RuntimeError("no permission")
        return self.items


class TriageTest(TmpCase):
    def test_rules(self):
        cfg = make_cfg(self.root, vip_senders=["Mom", "teacher@school.org"])
        items = [
            Item("1", "mail", "Mom <mom@x.com>", "hi", "", ""),
            Item("2", "mail", "shop", "Your order shipped", "", "nothing special"),
            Item("3", "mail", "bank", "Payment failed on card", "", ""),
            Item("4", "mail", "x", "newsletter", "", "due diligence is overrated, deadline: friday"),
            Item("5", "calendar", "", "Dentist", "", "", starts_in_min=45),
            Item("6", "calendar", "", "Party", "", "", starts_in_min=600),
            Item("7", "mail", "x", "Reminders about duet", "", ""),   # 'due' inside a word
        ]
        got = {i.id: r for i, r in checkin.triage(items, cfg)}
        self.assertEqual(sorted(got), ["1", "3", "4", "5"])
        self.assertEqual(got["1"], "VIP sender")

    def test_parse_records(self):
        out = checkin.FIELD.join(["a", "b", "c"]) + checkin.REC + "\n" + checkin.FIELD.join(["d", "e", "f"]) + checkin.REC
        self.assertEqual(checkin.parse_records(out, 3), [["a", "b", "c"], ["d", "e", "f"]])

    def test_mail_scanner_parses_osascript(self):
        out = checkin.FIELD.join(["m1", "Bob <b@x>", "URGENT: call", "Mon", "body"]) + checkin.REC
        old = checkin.run_osascript
        checkin.run_osascript = lambda script, timeout=60: out
        self.addCleanup(setattr, checkin, "run_osascript", old)
        items = checkin.MailAppScanner().scan(self.cfg)
        self.assertEqual(items[0].id, "mail:m1")
        self.assertEqual(items[0].subject, "URGENT: call")

    def test_calendar_scanner(self):
        out = checkin.FIELD.join(["u1", "Dentist", "Mon 3pm", "45"]) + checkin.REC
        old = checkin.run_osascript
        checkin.run_osascript = lambda script, timeout=60: out
        self.addCleanup(setattr, checkin, "run_osascript", old)
        it = checkin.CalendarScanner().scan(self.cfg)[0]
        self.assertEqual(it.starts_in_min, 45)

    def test_osascript_off_mac(self):
        old = notify.is_mac
        notify.is_mac = lambda: False
        self.addCleanup(setattr, notify, "is_mac", old)
        with self.assertRaises(RuntimeError):
            checkin.run_osascript("return 1")

    def test_imap_unconfigured_raises(self):
        with self.assertRaises(RuntimeError):
            checkin.ImapScanner().scan(self.cfg)

    def test_scripts_are_read_only(self):
        for s in (checkin.MAIL_SCRIPT, checkin.CAL_SCRIPT):
            for bad in ("delete", "move ", "set read status", "make new", "send "):
                self.assertNotIn(bad, s)


class RunTest(TmpCase):
    def setUp(self):
        super().setUp()
        self.cfg = make_cfg(self.root, vip_senders=["boss"])
        self.state = State(self.cfg)
        self.sent = []
        self.sender = lambda cfg, t, b: self.sent.append((t, b)) or {}

    def test_notify_and_dedupe(self):
        items = [Item("a", "mail", "boss@x", "hello", "", ""), Item("b", "mail", "x", "meh", "", "")]
        sc = [FakeScanner("mail", items)]
        r1 = checkin.run(self.cfg, self.state, sc, self.sender)
        self.assertEqual(len(r1["notified"]), 1)
        r2 = checkin.run(self.cfg, self.state, sc, self.sender)
        self.assertEqual(r2["notified"], [])
        self.assertEqual(len(self.sent), 1)
        self.assertIn("a", self.state.notified())
        self.assertEqual(len(self.state.events("checkin")), 2)

    def test_failing_scanner_is_skipped(self):
        sc = [FakeScanner("mail", fail=True), FakeScanner("cal", [Item("c", "calendar", "", "X", "", "", starts_in_min=5)])]
        r = checkin.run(self.cfg, self.state, sc, self.sender)
        self.assertIn("mail", r["errors"])
        self.assertEqual(len(r["notified"]), 1)
        self.assertEqual(len(self.state.events("checkin_scanner_error")), 1)

    def test_default_sender_writes_inbox(self):
        old = notify.display_notification
        notify.display_notification = lambda t, b: False
        self.addCleanup(setattr, notify, "display_notification", old)
        checkin.run(self.cfg, self.state, [FakeScanner("m", [Item("z", "mail", "boss", "s", "", "")])])
        self.assertIn("boss", self.cfg.inbox_path.read_text())


class NotifyTest(TmpCase):
    def test_quote(self):
        self.assertEqual(notify.applescript_quote('a "b" \\c'), '"a \\"b\\" \\\\c"')

    def test_off_mac_skips(self):
        old = notify.is_mac
        notify.is_mac = lambda: False
        self.addCleanup(setattr, notify, "is_mac", old)
        self.assertFalse(notify.display_notification("t", "b"))

    def test_inbox_newest_first_and_ntfy_off_by_default(self):
        calls = []
        old = (notify.display_notification, notify.ntfy_push)
        notify.display_notification = lambda t, b: False
        notify.ntfy_push = lambda *a: calls.append(a) or True
        self.addCleanup(lambda: (setattr(notify, "display_notification", old[0]), setattr(notify, "ntfy_push", old[1])))
        notify.send(self.cfg, "first", "1")
        notify.send(self.cfg, "second", "2")
        txt = self.cfg.inbox_path.read_text()
        self.assertLess(txt.index("second"), txt.index("first"))
        self.assertEqual(calls, [])
        self.cfg.ntfy_topic = "t"
        notify.send(self.cfg, "third", "3")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
