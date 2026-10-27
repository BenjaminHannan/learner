"""Step 4 -- the GLUE LOOP: one persistent agent that ties the existing parts together.

Everything real is behind a small interface, so our own ears / mouth / reasoner can be
plugged in later without touching this file:

    Ears      English turn            -> list of actions (or a clarification request)
    Reasoner  question action + notebook -> result record (a discrete status, never a guess)
    Mouth     result record           -> one English sentence
    Sleeper   full experience log     -> accepted / rejected     (never decided by a model)
    Thinker   notebook                -> optional THINKING work  (absent by default)

The notebook contract (fable_notebook_contract) and LISTENING (fable_listening_m1) are
IMPORTED, not re-implemented: every write still goes through LISTENING, so the taught-only
write right, the CONFLICT question and the "which Mira?" question all still hold.

MODES (design/v3/30-modes): one ``step()`` advances exactly one tick and returns an event.
    SLEEP      the experience log reached a FIXED size threshold (a number, not a judgement)
    LISTENING  a user turn is waiting
    WORK       a task is queued (stub: does nothing yet)
    THINKING   the idle default (stub unless a thinker is plugged in)

PERSISTENCE: the notebook is its own append-only fsynced log; the rest of the state
(inbox, experience log, mode, pending question, counters) is written to ``state.json`` with
write-temp-then-os.replace after every single tick.  A crash between two ticks loses at most
the tick in flight, and a torn notebook tail or a leftover temp file is repaired on resume.

    python fable_agent_loop.py --state-dir DIR --once "Mira's city is Lisbon."
    python fable_agent_loop.py --state-dir DIR --repl
    python fable_agent_loop.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Protocol, runtime_checkable

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C          # noqa: E402
import fable_listening_m1 as L               # noqa: E402

STATE_VERSION = 1
STATE_NAME = "state.json"
NOTEBOOK_DIR = "notebook"
SLEEP_THRESHOLD = 20        # fixed size; sleep is never the model's decision
MAX_HOPS = 3
MAX_TICKS_PER_RUN = 1000

LISTENING, THINKING, SLEEP, WORK = "LISTENING", "THINKING", "SLEEP", "WORK"


# ------------------------------------------------------------------ interfaces
@runtime_checkable
class Ears(Protocol):
    def hear(self, turn: str) -> list[dict]:
        """English turn -> actions. An action it cannot read must be {'act': 'clarify'}."""


@runtime_checkable
class Mouth(Protocol):
    def say(self, record: dict) -> str:
        """Result record -> one English sentence. Content words come from the record only."""


@runtime_checkable
class Reasoner(Protocol):
    def answer(self, question: dict, notebook) -> dict:
        """{'name', 'relations', 'entity_id'?} -> result record with a discrete status."""


@runtime_checkable
class Sleeper(Protocol):
    def sleep(self, experience: list[dict], notebook) -> dict:
        """Called only when the log is full. Returns {'accepted': bool, ...}."""


@runtime_checkable
class Thinker(Protocol):
    def think(self, notebook) -> dict | None:
        """Optional idle work. None means 'nothing to do'."""


# ------------------------------------------------------- deterministic offline fakes
PERSON_RELATIONS = {"mother", "father", "sister", "brother", "friend", "boss",
                    "teacher", "wife", "husband", "neighbour", "neighbor", "partner"}
_APOS = r"['’]s\b\s*"
_QUESTION = re.compile(r"^\s*(?:who|what|where)\s+(?:is|are)\s+(.+?)\s*[?.]?\s*$", re.I)
_CORRECTION = re.compile(r"^\s*(?:actually|no,)\s*,?\s*(.*)$", re.I)
_STATEMENT = re.compile(r"^\s*(.+?)\s+is\s+(.+?)\s*\.?\s*$", re.I)
_PICK = re.compile(r"^\s*pick\s+(E\d+)\s*\.?\s*$", re.I)
_YESNO = re.compile(r"^\s*(yes|no)\s*\.?\s*$", re.I)


def _chain(text: str) -> list[str]:
    return [part.strip() for part in re.split(_APOS, text.strip()) if part.strip()]


def _clarify(text: str) -> dict:
    return {"act": "clarify", "text": text}


class FakeEars:
    """A tiny template parser. Test scaffolding for the loop -- NOT the real ears."""

    def hear(self, turn: str) -> list[dict]:
        turn = " ".join(str(turn).split())
        if not turn:
            return [_clarify("I didn't catch anything.")]
        found = _PICK.match(turn)
        if found:
            return [{"act": "answer", "value": "pick", "id": found.group(1)}]
        found = _YESNO.match(turn)
        if found:
            return [{"act": "answer", "value": found.group(1).lower()}]
        found = _QUESTION.match(turn)
        if found:
            parts = _chain(found.group(1))
            if len(parts) < 2 or len(parts) > MAX_HOPS + 1:
                return [_clarify(f"I can only follow 1 to {MAX_HOPS} steps, like "
                                 f"\"Who is Mira's mother's city?\".")]
            return [{"act": "ask", "name": parts[0],
                     "relations": [self._relation(p) for p in parts[1:]]}]
        correction = False
        found = _CORRECTION.match(turn)
        if found and found.group(1):
            correction, turn = True, found.group(1)
        found = _STATEMENT.match(turn)
        if found:
            left, value = found.group(1), found.group(2).rstrip(".")
            parts = _chain(left)
            if len(parts) != 2:
                return [_clarify("Please say it like \"Mira's city is Lisbon.\".")]
            name, relation = parts[0], self._relation(parts[1])
            if " " in name:
                return [_clarify("I can only handle one-word names so far.")]
            if not value:
                return [_clarify("I didn't get the value.")]
            return [{"act": "correct" if correction else "teach", "name": name,
                     "relation": relation, "value": value,
                     "is_person": relation in PERSON_RELATIONS}]
        return [_clarify("I didn't understand that. Could you say it another way?")]

    @staticmethod
    def _relation(surface: str) -> str:
        return "_".join(surface.strip().lower().split())


class FakeMouth:
    """Template sentences. Every content word is copied out of the result record."""

    def say(self, record: dict) -> str:
        kind = record.get("kind")
        if kind in ("write", "clarify", "note"):
            return record.get("text", "")
        if kind != "answer":
            return ""
        status, fields = record.get("status"), dict(record.get("fields") or {})
        if status == C.OK:
            owner = "'s ".join([record["name"]] + [part.replace("_", " ")
                                                   for part in record["relations"]])
            sentence = f"{owner} is {fields.get('answer')}."
            if fields.get("source") == "web-verified":
                sentence += " (I read that online; you didn't tell me.)"
            return sentence
        return C.Result(status, fields).say()


class LookupReasoner:
    """1-3 hop lookup through the notebook contract's own hard-coded hop loop."""

    def answer(self, question: dict, notebook) -> dict:
        name = question["name"]
        relations = list(question["relations"])
        if not 1 <= len(relations) <= MAX_HOPS:
            return {"kind": "answer", "status": C.BAD_REQUEST, "name": name,
                    "relations": relations, "fields": {"reason": f"need 1-{MAX_HOPS} hops"}}
        result = notebook.ask(name, relations, entity_id=question.get("entity_id"))
        return {"kind": "answer", "status": result.status, "name": name,
                "relations": relations, "fields": dict(result.detail)}


class StubSleeper:
    """Records that sleep was ASKED FOR and changes nothing. A real sleeper replaces it."""

    def __init__(self) -> None:
        self.requests: list[int] = []

    def sleep(self, experience: list[dict], notebook) -> dict:
        self.requests.append(len(experience))
        return {"accepted": False, "reason": "no sleeper is plugged in yet",
                "log_size": len(experience)}


# ------------------------------------------------------------------- the loop
class AgentLoop:
    def __init__(self, state_dir, *, ears: Ears | None = None, mouth: Mouth | None = None,
                 reasoner: Reasoner | None = None, sleeper: Sleeper | None = None,
                 thinker: Thinker | None = None,
                 sleep_threshold: int = SLEEP_THRESHOLD) -> None:
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / STATE_NAME
        self.ears = ears or FakeEars()
        self.mouth = mouth or FakeMouth()
        self.reasoner = reasoner or LookupReasoner()
        self.sleeper = sleeper or StubSleeper()
        self.thinker = thinker
        self.sleep_threshold = int(sleep_threshold)
        self.notes: list[str] = []

        self.nb = C.Notebook(self.dir / NOTEBOOK_DIR)
        if self.nb.torn_tail:                      # crash mid-write: keep the good prefix
            self.nb.repair_torn_tail()
            self.notes.append("repaired a torn notebook tail")
        self.listening = L.Listening(self.nb)

        self.tick = 0
        self.mode = THINKING
        self.inbox: list[str] = []
        self.work_queue: list[str] = []
        self.experience: list[dict] = []
        self.question_pending: dict | None = None
        self.sleep_mark = 0
        self.counters = {"turns": 0, "writes": 0, "answers": 0, "clarifications": 0,
                         "sleeps": 0, "work": 0, "thinks": 0}
        self._load()

    # ------------------------------------------------------------- persistence
    def _load(self) -> None:
        for stale in self.dir.glob(STATE_NAME + ".tmp*"):   # leftover half-written temps
            try:
                stale.unlink()
            except OSError:
                pass
        if not self.state_path.exists():
            return
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            if state.get("version") != STATE_VERSION:
                raise ValueError("unknown state version")
        except (OSError, ValueError) as exc:
            self.notes.append(f"state file unusable ({exc}); starting the loop state fresh")
            return
        self.tick = int(state.get("tick", 0))
        self.mode = state.get("mode", THINKING)
        self.inbox = list(state.get("inbox", []))
        self.work_queue = list(state.get("work_queue", []))
        self.experience = list(state.get("experience", []))
        self.question_pending = state.get("question_pending")
        self.sleep_mark = int(state.get("sleep_mark", 0))
        self.counters.update(state.get("counters", {}))
        self.listening.pending = state.get("listening_pending")
        self.listening.turn = int(state.get("listening_turn", 0))

    def _save(self) -> None:
        payload = {"version": STATE_VERSION, "tick": self.tick, "mode": self.mode,
                   "inbox": self.inbox, "work_queue": self.work_queue,
                   "experience": self.experience, "question_pending": self.question_pending,
                   "sleep_mark": self.sleep_mark, "counters": self.counters,
                   "listening_pending": self.listening.pending,
                   "listening_turn": self.listening.turn,
                   "sleep_threshold": self.sleep_threshold}
        tmp = self.dir / f"{STATE_NAME}.tmp{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self.state_path)      # atomic on Windows and on POSIX

    # ------------------------------------------------------------------ inputs
    def submit(self, turn: str) -> None:
        self.inbox.append(str(turn))
        self._save()

    def queue_work(self, task: str) -> None:
        self.work_queue.append(str(task))
        self._save()

    # ------------------------------------------------------------ the one tick
    def sleep_due(self) -> bool:
        return len(self.experience) >= self.sleep_mark + self.sleep_threshold

    def busy(self) -> bool:
        return bool(self.inbox or self.work_queue) or self.sleep_due()

    def step(self) -> dict:
        self.tick += 1
        if self.sleep_due():
            event = self._sleep_tick()
        elif self.inbox:
            event = self._listening_tick()
        elif self.work_queue:
            event = self._work_tick()
        else:
            event = self._thinking_tick()
        self.mode = event["mode"]
        self._save()
        return event

    def run_until_idle(self, limit: int = MAX_TICKS_PER_RUN) -> list[dict]:
        events = []
        while self.busy() and len(events) < limit:
            events.append(self.step())
        return events

    def turn(self, text: str) -> list[str]:
        """Convenience: one English turn in, the sentences the loop says back out."""
        self.submit(text)
        said: list[str] = []
        for event in self.run_until_idle():
            said.extend(event["said"])
        return said

    def _event(self, mode: str, detail: dict, said: list[str]) -> dict:
        return {"tick": self.tick, "mode": mode, "detail": detail, "said": said,
                "log_size": len(self.experience), "notebook_events": len(self.nb.events)}

    # ----------------------------------------------------------------- LISTENING
    def _listening_tick(self) -> dict:
        text = self.inbox.pop(0)
        self.counters["turns"] += 1
        records = [self._act(action) for action in self.ears.hear(text)]
        said = [line for line in (self.mouth.say(record) for record in records) if line]
        self.experience.append({"tick": self.tick, "kind": "turn", "text": text,
                                "statuses": [r.get("status", r["kind"]) for r in records]})
        return self._event(LISTENING, {"turn": text, "records": records}, said)

    def _act(self, action: dict) -> dict:
        act = action.get("act")
        if act == "clarify":
            self.counters["clarifications"] += 1
            return {"kind": "clarify", "text": action.get("text", "")}
        if act == "ask":
            return self._ask(action["name"], list(action["relations"]))
        if act == "answer":
            return self._answer(action)
        if act in ("teach", "correct"):
            arrow = "->" if action.get("is_person") else "="
            return self._write(f"{act} {action['name']} {action['relation']} "
                               f"{arrow} {action['value']}")
        if act in ("person", "alias", "forget", "quote"):
            return self._write(action["line"])
        return {"kind": "clarify", "text": "I didn't understand that."}

    def _ask(self, name: str, relations: list[str], entity_id: str | None = None) -> dict:
        record = self.reasoner.answer({"name": name, "relations": relations,
                                       "entity_id": entity_id}, self.nb)
        self.counters["answers"] += 1
        if record.get("status") == C.AMBIGUOUS:
            self.question_pending = {"name": name, "relations": relations,
                                     "ids": list(record["fields"].get("ids", []))}
        return record

    def _answer(self, action: dict) -> dict:
        if self.question_pending is not None:
            if action.get("value") == "pick" and action.get("id") in self.question_pending["ids"]:
                question, self.question_pending = self.question_pending, None
                return self._ask(question["name"], question["relations"], action["id"])
            self.counters["clarifications"] += 1
            return {"kind": "clarify", "text": "Please answer with: pick <one of the IDs I listed>."}
        line = f"pick {action['id']}" if action.get("value") == "pick" else action.get("value", "")
        return self._write(line)

    def _write(self, line: str) -> dict:
        before = len(self.nb.events)
        try:
            text = self.listening.hear(line)
        except C.LogCorrupt as exc:
            text = f"I could NOT save that: the notebook reported a problem ({exc})."
        wrote = len(self.nb.events) > before
        self.counters["writes"] += int(wrote)
        return {"kind": "write", "line": line, "text": text, "wrote": wrote,
                "pending": self.listening.pending is not None}

    # ---------------------------------------------------------- SLEEP / WORK / THINKING
    def _sleep_tick(self) -> dict:
        outcome = self.sleeper.sleep(list(self.experience), self.nb)
        accepted = bool(outcome.get("accepted"))
        if accepted:
            self.experience = []
            self.sleep_mark = 0
        else:
            self.sleep_mark = len(self.experience)   # don't ask again until it grows again
        self.counters["sleeps"] += 1
        return self._event(SLEEP, {"accepted": accepted, "outcome": outcome}, [])

    def _work_tick(self) -> dict:
        task = self.work_queue.pop(0)
        self.counters["work"] += 1
        self.experience.append({"tick": self.tick, "kind": "work", "text": task})
        return self._event(WORK, {"task": task, "done": False,
                                  "reason": "WORK is a stub; nothing is plugged in"}, [])

    def _thinking_tick(self) -> dict:
        thought = self.thinker.think(self.nb) if self.thinker is not None else None
        self.counters["thinks"] += 1
        return self._event(THINKING, {"thought": thought}, [])


# --------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="The glue loop (step 4)")
    parser.add_argument("--state-dir", help="folder that holds the notebook and state.json")
    parser.add_argument("--once", help="one English turn, then exit")
    parser.add_argument("--repl", action="store_true", help="one turn per stdin line")
    parser.add_argument("--sleep-threshold", type=int, default=SLEEP_THRESHOLD)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        import fable_agent_loop_selftest as T
        return T.main()
    if not args.state_dir or not (args.once or args.repl):
        parser.print_help()
        return 0

    loop = AgentLoop(args.state_dir, sleep_threshold=args.sleep_threshold)
    for note in loop.notes:
        print(f"[note] {note}", flush=True)
    if args.once:
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        print(" ".join(loop.turn(line)) or "(nothing to say)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
