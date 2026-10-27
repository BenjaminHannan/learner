#!/usr/bin/env python3
"""Exp 221b -- unit checks for the stored-relation fallback (sealed).

U1 stem rule pairs (founded~founding, graduate~graduation, coaches~coach,
   owns~owner, opening~open) and non-pairs (born/birth, doctor/physician).
U2 non-taught rows are never read by the fallback: a sleep-derived row, a
   proposed row and a web-quarantine row (written straight into the scratch
   notebook, the way sleep/thinking would) give no fallback fire, and a
   forgotten taught row gives no fire either. A fresh agent per check.
Prints one line per check and "UNIT: n/n".
"""

from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_loop221b_agent as B  # noqa: E402


def agent():
    cfg = copy.deepcopy(B.DEFAULT_CONFIG221B)
    cfg["state_dir"] = tempfile.mkdtemp(prefix="u221b-")
    cfg["sleep_threshold"] = 100000
    return B.build_agent221b(cfg)


def main() -> int:
    res = []
    for a, b, same in [("founded", "founding", True),
                       ("graduate", "graduation", True),
                       ("coaches", "coach", True), ("owns", "owner", True),
                       ("opening", "open", True), ("born", "birth", False),
                       ("doctor", "physician", False)]:
        ok = (B.stem221b(a) == B.stem221b(b)) == same
        res.append(ok)
        print(("OK  " if ok else "FAIL"), f"U1 {a}~{b} same={same}")
    # U2: non-taught sources
    for src, actor, extra in [("sleep-derived", "sleep", {}),
                              ("proposed", "creative", {}),
                              ("web-quarantine", "thinking",
                               {"provenance": {"url": "https://example.org",
                                               "quoted_span": "x"}})]:
        loop = agent()
        loop.turn("Tova Renn's dentist is Oro Blaine.")
        nb = loop.nb
        eid = nb.resolve("Tova Renn").detail["entity_id"]
        r = nb.assert_fact(f"u-{src}", actor, src, eid, "landlord",
                           {"literal": "Ada Wren"}, **extra)
        reply = " ".join(loop.turn("Who is the landlord of Tova Renn?"))
        stage = str(getattr(loop.ears, "last_stage", ""))
        ok = stage != B.STAGE221B
        res.append(ok)
        print(("OK  " if ok else "FAIL"), f"U2 {src} row ({r.status}) "
              f"-> stage {stage!r} reply {reply!r}")
    loop = agent()
    loop.turn("Tova Renn's landlord is Ada Wren.")
    loop.turn("Forget Tova Renn's landlord.")
    reply = " ".join(loop.turn("Who is the landlord of Tova Renn?"))
    stage = str(getattr(loop.ears, "last_stage", ""))
    ok = stage != B.STAGE221B and "Ada Wren" not in reply
    res.append(ok)
    print(("OK  " if ok else "FAIL"), f"U2 forgotten -> stage {stage!r} "
          f"reply {reply!r}")
    print(f"UNIT: {sum(res)}/{len(res)}")
    return 0 if all(res) else 1


if __name__ == "__main__":
    sys.exit(main())
