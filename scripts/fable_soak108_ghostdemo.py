"""Exp 108 G1 -- the exp-93 ghost reproducer (GHOST93) against the fixed daemon.

Same scenario as scripts/fable_soak93_ghostdemo.py (sealed, unedited), plus the
mailbox-level half a real kill leaves behind:

  Part A (loop level, GHOST93 verbatim): fresh dir; loop.turn(teach Alice);
  loop.submit(teach Bob) -- the exact disk state a kill -9 mid-turn leaves;
  reboot; boot_reconcile (the one change); turn(teach Carol).
  GHOST93 showed the Carol reply containing BOTH the Bob ghost sentence and
  the real Carol sentence. G1 PASS = the Carol reply contains Carol ONLY.

  Part B (mailbox level): fresh daemon108 dir; inbox file t000001 (Alice)
  processed; then a kill-9 mid-turn is simulated exactly: loop.submit(Bob
  text) plants the state.json ghost AND inbox/t000002.txt still holds Bob's
  text with no outbox reply yet. Reboot as Daemon108 (reconcile runs on boot);
  process t000002; then t000003 (Carol). G1 PASS = Bob's reply is exactly one
  sentence, Carol's reply is exactly one sentence, receipts show each id
  processed once, and Bob's fact is stored exactly once.

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

import fable_daemon108_run as D108  # noqa: E402 (the wrapper under test)


def main() -> int:
    ok = True

    # ---- Part A: GHOST93 verbatim, through the fixed boot path ----
    tmp = Path(tempfile.mkdtemp(prefix="soak108_ghostA_"))
    try:
        d1 = D108.Daemon108(tmp / "daemon", idle_seconds=3600)
        r1 = d1.loop.turn("Alice's city is Paris.")
        assert any("Saved" in s for s in r1), r1
        d1.loop.submit("Bob's city is Rome.")  # kill-9-mid-turn disk state
        rebooted = D108.Daemon108(tmp / "daemon", idle_seconds=3600)
        print("A: dropped_loop_inbox =",
              rebooted.reconcile_report["dropped_loop_inbox"])
        said = rebooted.loop.turn("Carol's city is Madrid.")
        reply = " ".join(said)
        print("A: carol reply:", reply)
        ghost = "Rome" in reply
        real = "Madrid" in reply
        part_a = (not ghost) and real
        print("A: ghost sentence present:", ghost, "| real present:", real)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- Part B: mailbox level, exactly one reply per id ----
    tmp = Path(tempfile.mkdtemp(prefix="soak108_ghostB_"))
    try:
        root = tmp / "daemon"
        d1 = D108.Daemon108(root, idle_seconds=3600)
        (root / "inbox" / "t000001.txt").write_text(
            "Alice's city is Paris.\n", encoding="utf-8")
        d1.process_file(root / "inbox" / "t000001.txt")
        # Exact kill-mid-turn state: ghost in state.json + mailbox file
        # still in inbox + no outbox reply.
        (root / "inbox" / "t000002.txt").write_text(
            "Bob's city is Rome.\n", encoding="utf-8")
        d1.loop.submit("Bob's city is Rome.")
        d2 = D108.Daemon108(root, idle_seconds=3600)  # reboot: reconcile
        print("B: reconcile =", rebooted is not None and
              d2.reconcile_report)
        d2.process_file(root / "inbox" / "t000002.txt")
        (root / "inbox" / "t000003.txt").write_text(
            "Carol's city is Madrid.\n", encoding="utf-8")
        d2.process_file(root / "inbox" / "t000003.txt")
        bob = (root / "outbox" / "t000002.txt").read_text(
            encoding="utf-8").strip()
        carol = (root / "outbox" / "t000003.txt").read_text(
            encoding="utf-8").strip()
        print("B: bob reply:", bob)
        print("B: carol reply:", carol)
        receipts = D108.read_receipts(root)
        counts: dict[str, int] = {}
        for r in receipts:
            counts[r["file"]] = counts.get(r["file"], 0) + 1
        import fable_notebook_contract as C
        nb = C.Notebook(root / "notebook")
        rome_facts = sum(
            1 for e in nb.events
            if e.get("kind") == "FACT"
            and str(e.get("value", {}).get("literal", "")) == "Rome")
        part_b = (bob == "Saved: Bob's city is Rome."
                  and carol == "Saved: Carol's city is Madrid."
                  and counts.get("t000002.txt") == 1
                  and counts.get("t000003.txt") == 1
                  and rome_facts == 1)
        print("B: receipts/file =", counts, "| Rome FACT rows =", rome_facts)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("GHOST108", "PASS" if (part_a and part_b) else "FAIL",
          f"(A={part_a} B={part_b})")
    ok = part_a and part_b
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
