#!/usr/bin/env python3
"""lis-320 Luna wording with one added texting-style sentence (reading thread, 2026-09-27; ADDENDUM-10).
New file; claude_lis320_luna.py and claude_lis320_glm.py stay as sealed.

Luna pilot 7 tripped PILOT-THRESHOLDS item 2: 0 of 404 kept turns had an apostrophe-less contraction (bar 0.12; DEV
chats 0.253, GLM pilot 6 0.405). The item's registered response is to change the messiness part of the instruction.
Pilot 7's fresh reader also found the long turns padded with remarks about the message itself ("just putting this here",
"this might come out rambly"), which read unlike texting and put hedge words next to facts. The change: one sentence
appended to the "How the user writes" paragraph of claude_lis320_glm.HEAD (text in STYLE_ADD below); everything else, the writer and the call path, is claude_lis320_luna's. The MUST INCLUDE rule is unchanged, so
names and values are still typed exactly.
    python -B scripts/claude_lis320_luna2.py --seeds S.jsonl --out raw.jsonl --workers 3 --max-minutes 70
    python -B scripts/claude_lis320_luna2.py --selftest        (no network)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis320_glm as G  # noqa: E402
import claude_lis320_luna as LU  # noqa: E402

ANCHOR = ('Never copy words of the plan itself (such as "first person", "owner", "relation", "intent") into a message.')
STYLE_ADD = (" Most of these users type fast: they skip apostrophes in contractions (dont, im, thats, cant, didnt, ive), "
             "start messages in lowercase, and never talk about the message itself (no \"just putting this here\", "
             "\"that's all i wanted to say\", \"this might come out rambly\").")


def install():
    if STYLE_ADD not in G.HEAD:
        assert G.HEAD.count(ANCHOR) == 1, "anchor sentence not found once in claude_lis320_glm.HEAD"
        G.HEAD = G.HEAD.replace(ANCHOR, ANCHOR + STYLE_ADD)


def selftest():
    from claude_lis320_seed import make_seeds
    d = make_seeds(3, 1)[0]
    before = G.build_prompt(d)
    install()
    after = G.build_prompt(d)
    assert after == before.replace(ANCHOR, ANCHOR + STYLE_ADD) and after.count(STYLE_ADD) == 1
    install()
    assert G.build_prompt(d).count(STYLE_ADD) == 1          # idempotent
    LU.selftest()                                          # writer, rows and failure path unchanged (no network)
    print("lis320 luna2 selftest ok (one style sentence added to the prompt; no network)")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    install()
    return LU.main()


if __name__ == "__main__":
    sys.exit(main())
