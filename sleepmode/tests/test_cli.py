import unittest

from sleepmode import cli
from sleepmode.tests.helpers import TmpCase


class Ok:
    name = "mail"
    def scan(self, cfg): return [1, 2]


class Denied:
    name = "calendar"
    def scan(self, cfg): raise PermissionError("-1743")


class PreflightTest(TmpCase):
    def test_table(self):
        rows = {r[0]: r for r in cli.preflight(self.cfg, [Ok(), Denied()])}
        self.assertTrue(rows["mail"][1])
        self.assertFalse(rows["calendar"][1])
        self.assertIn("Automation", rows["calendar"][2])
        self.assertTrue(rows["python run"][1])
        self.assertIn("sandbox", rows)

    def test_keep_awake_flags(self):
        calls = []
        old = (cli.sys.platform, cli.shutil.which, cli.subprocess.Popen)
        cli.sys.platform = "darwin"
        cli.shutil.which = lambda n: "/usr/bin/caffeinate"
        cli.subprocess.Popen = lambda cmd, **k: calls.append(cmd)
        self.addCleanup(lambda: (setattr(cli.sys, "platform", old[0]), setattr(cli.shutil, "which", old[1]),
                                 setattr(cli.subprocess, "Popen", old[2])))
        cli.keep_awake()
        self.assertEqual(calls[0][:3], ["caffeinate", "-ims", "-w"])


if __name__ == "__main__":
    unittest.main()
