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
        self.paths = Paths(root / "home", root / "raw", root, root / "userdata")   # never the real Desk folder
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


def write_verified_ledger(userdata_dir: Path, notes):
    """Give each (note_id, text) card note two agreeing sources on different domains, so option B lets it be trained on.
    Writes the same committed rows the Desk writes (desk/src/memory.js save with research)."""
    import hashlib
    from sleepmlx.webtruth import card_claims, norm_claim
    userdata_dir = Path(userdata_dir)
    userdata_dir.mkdir(parents=True, exist_ok=True)
    sha = lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest()
    rows = []
    for note_id, text in notes:
        for k, host in enumerate(("one.example.com", "two.example.org")):
            quote = "Reference page: " + " and ".join(c["object"] for c in card_claims(text)) + " noted here."
            tx = "tx-%s-%d" % (note_id, k)
            rows.append({"version": 1, "type": "research-note-prepare", "tx_id": tx, "note_id": note_id, "fact_sha256": sha(text), "topic": "card",
                         "claim_norm": norm_claim(text), "origin": "learn-research", "context": {"run_id": "r%d" % k, "thread_id": None, "helper_id": None},
                         "attribution": {"status": "attributed", "verified": False, "reason": None,
                                         "source": {"read_id": "read_0123456789abcdef", "tool_call_id": None, "url": "https://%s/p" % host, "page": 1,
                                                    "read_at": "2026-10-29T00:00:00Z", "quote": quote, "quote_sha256": sha(quote), "visible_body_sha256": sha(quote)}},
                         "expires": None, "prepared_at": "2026-10-29T00:00:00Z"})
            rows.append({"version": 1, "type": "research-note-commit", "tx_id": tx, "committed_at": "2026-10-29T00:00:01Z"})
    (userdata_dir / "memory-provenance.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
