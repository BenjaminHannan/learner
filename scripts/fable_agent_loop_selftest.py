"""Self-test for the glue loop (scripts/fable_agent_loop.py).

Offline, standard library only, no model anywhere.  Every test prints PASS or FAIL and the
process exits non-zero if any of them fails.

    uv run --offline --no-project --python 3.12 python -B scripts/fable_agent_loop_selftest.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A          # noqa: E402
import fable_notebook_contract as C   # noqa: E402

LOOP_PATH = SCRIPTS / "fable_agent_loop.py"
THREE_FACTS = ["Mira's city is Lisbon.", "Mira's mother is Ana.", "Ana's city is Porto."]

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, note: str = "") -> None:
    RESULTS.append((name, bool(ok), note))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{note}]" if note and not ok else ""))


def _loop(folder, **kw) -> A.AgentLoop:
    return A.AgentLoop(folder, **kw)


def _teach_three(loop) -> list[str]:
    return [" ".join(loop.turn(line)) for line in THREE_FACTS]


# --------------------------------------------------------------------- tests
def test_teach_and_hops(folder) -> tuple[bool, str]:
    loop = _loop(folder)
    saved = _teach_three(loop)
    one = " ".join(loop.turn("Who is Mira's city?"))
    two = " ".join(loop.turn("Who is Mira's mother's city?"))
    ok = (all("Saved" in line for line in saved)
          and one.endswith("Lisbon.") and two.endswith("Porto."))
    return ok, f"saved={saved} one={one!r} two={two!r}"


def test_unknown_question_no_write(folder) -> tuple[bool, str]:
    loop = _loop(folder)
    _teach_three(loop)
    before = len(loop.nb.events)
    said = " ".join(loop.turn("Who is Mira's pet?"))
    after = len(loop.nb.events)
    return ("I don't know" in said and before == after), f"{said!r} events {before}->{after}"


def test_unparseable_clarifies(folder) -> tuple[bool, str]:
    loop = _loop(folder)
    _teach_three(loop)
    before = len(loop.nb.events)
    a = " ".join(loop.turn("bananas"))
    b = " ".join(loop.turn("The weather sure is nice today"))
    after = len(loop.nb.events)
    ok = ("understand" in a or "another way" in a) and "Please say it like" in b and before == after
    return ok, f"a={a!r} b={b!r} events {before}->{after}"


def test_correction_follows_contract(folder) -> tuple[bool, str]:
    loop = _loop(folder)
    _teach_three(loop)
    first = [f for f in loop.nb.facts.values() if f["relation"] == "city"
             and f["value"] == {"literal": "Lisbon"}][0]["fact_id"]
    conflict = " ".join(loop.turn("Mira's city is Paris."))
    kept = " ".join(loop.turn("Who is Mira's city?"))
    refused = " ".join(loop.turn("no"))
    still = " ".join(loop.turn("Who is Mira's city?"))
    fixed = " ".join(loop.turn("Actually, Mira's city is Paris."))
    now = " ".join(loop.turn("Who is Mira's city?"))
    old_row = loop.nb.facts[first]
    ok = ("change it to Paris" in conflict and kept.endswith("Lisbon.")
          and "left it as it was" in refused and still.endswith("Lisbon.")
          and "Saved" in fixed and now.endswith("Paris.")
          and old_row["value"] == {"literal": "Lisbon"} and not loop.nb.active(first))
    return ok, f"conflict={conflict!r} refused={refused!r} fixed={fixed!r} now={now!r}"


def test_sleep_at_threshold(folder) -> tuple[bool, str]:
    sleeper = A.StubSleeper()
    loop = _loop(folder, sleeper=sleeper, sleep_threshold=3)
    for line in THREE_FACTS:
        loop.submit(line)
    modes = [loop.step()["mode"] for _ in range(2)]
    early = list(sleeper.requests)
    modes.append(loop.step()["mode"])
    third = list(sleeper.requests)
    sleep_event = loop.step()
    after_log = list(loop.experience)
    next_mode = loop.step()["mode"]
    ok = (modes == [A.LISTENING] * 3 and early == [] and third == []
          and sleep_event["mode"] == A.SLEEP and sleeper.requests == [3]
          and sleep_event["detail"]["accepted"] is False and len(after_log) == 3
          and next_mode == A.THINKING)
    return ok, (f"modes={modes} requests={sleeper.requests} log={len(after_log)} "
                f"next={next_mode}")


def test_save_kill_resume(folder) -> tuple[bool, str]:
    child = subprocess.Popen(
        [sys.executable, "-B", str(LOOP_PATH), "--state-dir", str(folder), "--repl"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1)
    replies = []
    try:
        for line in THREE_FACTS:
            child.stdin.write(line + "\n")
            child.stdin.flush()
            replies.append(child.stdout.readline().strip())
        child.terminate()                         # killed mid-session, no clean shutdown
        child.wait(timeout=20)
    finally:
        if child.poll() is None:
            child.kill()
    again = subprocess.run(
        [sys.executable, "-B", str(LOOP_PATH), "--state-dir", str(folder),
         "--once", "Who is Mira's mother's city?"],
        capture_output=True, text=True, timeout=60)
    resumed = _loop(folder)
    state = json.loads((Path(folder) / A.STATE_NAME).read_text(encoding="utf-8"))
    ok = (all("Saved" in reply for reply in replies) and "Porto" in again.stdout
          and resumed.counters["turns"] >= 3 and state["tick"] >= 3
          and not list(Path(folder).glob(A.STATE_NAME + ".tmp*")))
    return ok, f"replies={replies} resumed={again.stdout.strip()!r} err={again.stderr[-200:]!r}"


def test_corrupt_leftovers_survive(folder) -> tuple[bool, str]:
    loop = _loop(folder)
    _teach_three(loop)
    folder = Path(folder)
    (folder / f"{A.STATE_NAME}.tmp999").write_text('{"version": 1, "tick": 4, "inb',
                                                   encoding="utf-8")       # truncated temp
    after_tmp = " ".join(_loop(folder).turn("Who is Mira's mother's city?"))
    log = folder / A.NOTEBOOK_DIR / C.LOG_NAME
    with open(log, "a", encoding="utf-8") as handle:                       # torn notebook tail
        handle.write('{"kind": "FACT", "event_id": "torn", "fact_')
    healed = _loop(folder)
    after_torn = " ".join(healed.turn("Who is Mira's mother's city?"))
    can_write = " ".join(healed.turn("Ana's pet is a cat."))
    (folder / A.STATE_NAME).write_text("{not json", encoding="utf-8")       # corrupt state
    fresh = _loop(folder)
    after_state = " ".join(fresh.turn("Who is Mira's mother's city?"))
    ok = (after_tmp.endswith("Porto.") and after_torn.endswith("Porto.")
          and "Saved" in can_write and after_state.endswith("Porto.")
          and any("torn" in note for note in healed.notes)
          and any("state file unusable" in note for note in fresh.notes))
    return ok, (f"tmp={after_tmp!r} torn={after_torn!r} write={can_write!r} "
                f"state={after_state!r} notes={healed.notes + fresh.notes}")


def test_ambiguous_question_survives_restart(folder) -> tuple[bool, str]:
    loop = _loop(folder)
    _teach_three(loop)
    first = loop.nb.resolve("Mira").detail["entity_id"]
    loop.nb.new_entity("second-mira", "Mira")            # a second person with the same name
    asked = " ".join(loop.turn("Who is Mira's city?"))
    resumed = _loop(folder)                              # the pending question must survive
    picked = " ".join(resumed.turn(f"pick {first}"))
    ok = ("more than one Mira" in asked and "Which one do you mean" in asked
          and resumed.question_pending is None and picked.endswith("Lisbon."))
    return ok, f"asked={asked!r} picked={picked!r}"


TESTS = [
    ("teach 3 facts, then 1-hop and 2-hop answers", test_teach_and_hops),
    ("unknown question -> I don't know, no write", test_unknown_question_no_write),
    ("unparseable turn -> clarification, no write", test_unparseable_clarifies),
    ("correction follows the notebook contract", test_correction_follows_contract),
    ("ambiguous name -> pick, pending survives restart", test_ambiguous_question_survives_restart),
    ("sleep fires exactly at the threshold, log intact", test_sleep_at_threshold),
    ("SAVE - KILL - RESUME across processes", test_save_kill_resume),
    ("corrupt temp file / torn tail survive resume", test_corrupt_leftovers_survive),
]


def main() -> int:
    for name, fn in TESTS:
        with tempfile.TemporaryDirectory() as folder:
            try:
                ok, note = fn(folder)
            except Exception as exc:              # a crash is a failed test, not a crashed run
                ok, note = False, f"{type(exc).__name__}: {exc}"
        check(name, ok, note)
    passed = sum(ok for _, ok, _ in RESULTS)
    print(f"{passed}/{len(RESULTS)} tests passed")
    print("SELFTEST", "PASS" if passed == len(RESULTS) else "FAIL")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
