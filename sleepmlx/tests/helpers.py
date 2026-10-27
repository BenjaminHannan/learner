import json
import tempfile
from pathlib import Path

from sleepmlx.backend import Clock, Guards
from sleepmlx.paths import Paths
from sleepmlx.profile import Renderer, load_profile
from sleepmlx.recipe import Config, Sleeper
from sleepmlx import diary as diary_mod

from .fakes import FakeBackend, FakeTime

FACTS_DAY1 = ["Remember that Marta works at Orbix", "Marta lives in Dalmore, send her the parcel", "Tomas is the mentor of Lena",
              "Lena owns Sunbird", "ok thanks"]
FACTS_DAY2 = ["Actually Pavel lives in Quillon", "Pavel works at Orbix now"]


def rec(user, answer="Sure.", model="k2-main", conv="c1", history=(), ts=1_700_000_000.0):
    msgs = [{"role": "system", "content": "You are the Desk."}] + list(history) + [{"role": "user", "content": user}]
    return {"ts": ts, "model": model, "conv_id": conv, "messages": msgs, "response": {"content": answer}, "status": 200}


def write_raw(raw_dir: Path, date: str, users, conv="c1"):
    raw_dir.mkdir(parents=True, exist_ok=True)
    lines, hist = [], []
    for k, u in enumerate(users):
        lines.append(json.dumps(rec(u, "Done %d." % k, conv=conv, history=hist, ts=1_700_000_000.0 + k)))
        hist += [{"role": "user", "content": u}, {"role": "assistant", "content": "Done %d." % k}]
    (raw_dir / (date + ".jsonl")).write_text("\n".join(lines) + "\n")


class Env:
    """A temp sleep home + raw diary, a fake clock and a fake model."""

    def __init__(self, days=(("2026-10-20", FACTS_DAY1),), profile="k2", **cfg):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.paths = Paths(root / "home", root / "raw", root)
        for date, users in days:
            write_raw(self.paths.diary_dir, date, users)
        self.prof = load_profile(profile)
        self.prof.template_mode = "manual"      # no tokenizer in the tests
        self.R = Renderer(self.prof, None)
        self.time = FakeTime()
        self.cfg = Config(scale=1.0, **cfg)
        self.logs = []

    def week(self):
        return diary_mod.build_week(self.paths.diary_dir, "Ben")

    def backend(self, **kw):
        return FakeBackend(self.time, **kw)

    def sleeper(self, be, budget=100000, guards=None):
        g = guards or Guards(self.paths, pressure=lambda: 1, now=self.time.now)
        clock = Clock(budget, g, now=self.time.now)
        return Sleeper(be, self.R, self.prof, self.cfg, self.paths, clock, self.logs.append)

    def close(self):
        self.tmp.cleanup()
