"""Exp 93 post-run analysis -- deterministic demo of the ghost-tick mechanism.

During the registered soak (stopped at turn 17,716 on a doubled reply), the
hypothesis was: a kill -9 landing between AgentLoop.submit()'s state save and
the end-of-step state save leaves the in-flight turn text in state.json's
loop.inbox; after reboot the daemon never drains loop.inbox itself, so the
stale text is re-executed as a ghost tick inside the NEXT turn() call, and its
reply sentence is prepended to that turn's outbox reply.

This script demonstrates the resurrection deterministically (no timing luck)
using the sealed classes only:

  1. fresh dir; loop.turn("teach Alice")      -> Saved (baseline)
  2. loop.submit("teach Bob")                  -> state.json now holds
     inbox=["teach Bob"] (this is the exact disk state a kill -9
     mid-turn leaves behind)
  3. loop2 = AgentLoop(same dir)               -> simulates the reboot
     (loads inbox=["teach Bob"] from state.json)
  4. loop2.turn("teach Carol")                 -> reply contains BOTH the
     ghost sentence for Bob AND the real sentence for Carol

PASS = the Carol reply contains a Bob sentence (ghost resurrection proven).
Stdlib only.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as G  # noqa: E402


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="soak93_ghost_"))
    try:
        loop = G.AgentLoop(str(tmp / "state"))
        r1 = loop.turn("Alice's city is Paris.")
        print("baseline:", r1)
        assert any("Saved" in s for s in r1), r1

        # Freeze the exact disk state a kill -9 mid-turn leaves: the text is
        # in state.json's inbox, never drained.
        loop.submit("Bob's city is Rome.")

        rebooted = G.AgentLoop(str(tmp / "state"))  # the "reboot"
        print("reboot restored loop.inbox:", rebooted.inbox)
        assert rebooted.inbox == ["Bob's city is Rome."], rebooted.inbox

        said = rebooted.turn("Carol's city is Madrid.")
        reply = " ".join(said)
        print("carol reply:", reply)
        ghost = "Rome" in reply
        real = "Madrid" in reply
        print("ghost sentence present:", ghost, "| real sentence present:", real)
        print("GHOST93", "PASS" if (ghost and real) else "FAIL")
        return 0 if (ghost and real) else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
