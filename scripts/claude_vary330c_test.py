#!/usr/bin/env python3
"""vary330c unit tests (no model)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_e2e336_run as R  # noqa: E402
import claude_e2e336_score as S  # noqa: E402
import claude_vary330c as V  # noqa: E402


def test_markers():
    for v in V.HONEST_VARIANTS:
        low = v.lower()
        assert S.has(low, S.ABSTAIN_MARKERS), v
        assert not S.has(low, S.CLARIFY_MARKERS), v
        assert not R.is_confirm(v), v
    for v in V.ACK_VARIANTS:
        low = v.lower()
        assert not any(w in low for w in ("saved", "noted", "remember", "i'll")), v
        assert not S.has(low, S.CLARIFY_MARKERS) and not R.is_confirm(v), v


class Loop:
    def __init__(self, reply):
        self.reply = reply
        self.turn = lambda text: list(self.reply)


def test_wrap():
    lp = Loop([V.HONEST_LINE])
    V.install_vary330c(lp)
    got = [lp.turn(f"q{i}")[0] for i in range(40)]
    assert all(g in V.HONEST_VARIANTS for g in got)
    assert all(a != b for a, b in zip(got, got[1:]))
    assert len(set(got)) >= 6
    lp.reply = ["Okay."]
    assert lp.turn("my aunt lives in tromso")[0] in V.ACK_VARIANTS
    lp.reply = ["Saved: your city is leeds."]
    assert lp.turn("x") == ["Saved: your city is leeds."]
    lp.reply = ["Okay.", "Is that right?"]
    assert lp.turn("x") == ["Okay.", "Is that right?"]
    assert lp.vary330c_stats == {"honest": 40, "ack": 1}


if __name__ == "__main__":
    test_markers()
    test_wrap()
    print("vary330c tests: 2/2 OK")
