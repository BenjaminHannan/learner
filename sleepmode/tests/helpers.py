import os
import shutil
import tempfile
import unittest

from sleepmode.config import Config


def make_cfg(root, **kw):
    d = dict(home=os.path.join(root, "home"), pause_others=os.path.join(root, "PAUSE_OTHERS"),
             assistant_running=os.path.join(root, "ASSISTANT_RUNNING"), diary_dir=os.path.join(root, "diary"),
             hour_s=0.2, poll_s=0.01, checkin_reserve_s=0.02, kill_grace_s=2.0, budget_slack_s=0.3,
             min_sleep_hours=1.0, mail_enabled=False, calendar_enabled=False)
    d.update(kw)
    return Config(**d)


class TmpCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sleepmode-test-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.cfg = make_cfg(self.root)
