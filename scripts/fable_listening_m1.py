"""Milestone 1 -- LISTENING mode over the notebook contract, with template replies.

No model and no English parser yet (decided: the learned talker and the parser wait until
this works end to end).  Input is a STRUCTURED line; the reply is a deterministic template.

  person Mira                 a new person (always new, even if the name exists)
  alias Tommy = Tom           another name for a known person
  teach Mira city = Lisbon    a fact whose value is plain text
  teach Mira mother -> Ana    a fact whose value is a person
  correct Mira city = Paris   an explicit correction
  ask Mira mother city        a question (hop loop is hard-coded)
  forget Mira city            retract the current taught value
  quote <anything>            reported speech / hypothetical: writes nothing
  yes | no | pick E0002       answers to LISTENING's own clarifying question

LISTENING rules enforced here (design/v3/30-modes/decided-inputs-fable.md):
  * the only writer of ``taught`` rows; says "Saved" only after the notebook returns SAVED
  * ambiguous name -> ask which one, never guess, never merge
  * a different value without ``correct`` -> ask before changing
  * quotes and hypotheticals write nothing
  * a pending clarifying question is remembered; an unrelated line cancels it and says so
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import uuid

import fable_notebook_contract as C

FUNCTIONAL_BY_DEFAULT = True


class Listening:
    def __init__(self, notebook: C.Notebook) -> None:
        self.nb = notebook
        self.pending: dict | None = None
        self.turn = 0

    def _eid(self, tag: str) -> str:
        return f"turn{self.turn:05d}-{tag}-{uuid.uuid4().hex[:8]}"

    # ------------------------------------------------------------ name handling
    def _person(self, name: str, create: bool, picked: str | None = None):
        """Returns (entity_id, None) or (None, reply). ``picked`` answers an earlier AMBIGUOUS."""
        if picked:
            return picked, None
        found = self.nb.resolve(name)
        if found.status == C.OK:
            return found.detail["entity_id"], None
        if found.status == C.AMBIGUOUS:
            return None, found
        if create:
            made = self.nb.new_entity(self._eid("person"), name)
            return made.detail["entity_id"], None
        return None, found

    def _relation(self, relation: str) -> None:
        known = {e["relation"] for e in self.nb.events if e["kind"] == "RELATION"}
        if relation not in known:
            self.nb.declare_relation(self._eid("rel"), relation, FUNCTIONAL_BY_DEFAULT)

    # ------------------------------------------------------------------- turns
    def hear(self, line: str) -> str:
        self.turn += 1
        words = line.strip().split()
        if not words:
            return "I didn't catch anything."
        act, rest = words[0].lower(), words[1:]

        if act in ("yes", "no", "pick"):
            return self._answer_pending(act, rest)
        note = ""
        if self.pending is not None:
            self.pending = None
            note = "(I dropped my earlier question.) "

        try:
            if act == "quote":
                return note + "I didn't save that, because it was not you telling me a fact."
            if act == "person" and rest:
                made = self.nb.new_entity(self._eid("person"), " ".join(rest))
                return note + made.say()
            if act == "alias" and "=" in rest:
                cut = rest.index("=")
                return note + self._alias(" ".join(rest[:cut]), " ".join(rest[cut + 1:]))
            if act in ("teach", "correct") and len(rest) >= 4 and rest[2] in ("=", "->"):
                return note + self._teach(rest[0], rest[1], rest[2], " ".join(rest[3:]),
                                          correction=(act == "correct"))
            if act == "ask" and len(rest) >= 2:
                return note + self._ask(rest[0], rest[1:])
            if act == "forget" and len(rest) == 2:
                return note + self._forget(rest[0], rest[1])
        except C.LogCorrupt as exc:
            return f"I could NOT save that: the notebook reported a problem ({exc})."
        return note + C.Result(C.BAD_REQUEST, {"reason": "I did not understand the line"}).say()

    def _alias(self, alias: str, name: str, picked: str | None = None) -> str:
        entity_id, problem = self._person(name, create=False, picked=picked)
        if problem is not None:
            return self._clarify(problem, {"kind": "alias", "alias": alias, "name": name})
        return self.nb.add_alias(self._eid("alias"), entity_id, alias).say()

    def _teach(self, name, relation, arrow, value_text, correction, picked=None, picked_obj=None):
        resume = {"kind": "teach", "name": name, "relation": relation, "arrow": arrow,
                  "value_text": value_text, "correction": correction,
                  "picked": picked, "picked_obj": picked_obj}
        subject, problem = self._person(name, create=True, picked=picked)
        if problem is not None:
            return self._clarify(problem, dict(resume, slot="picked"))
        resume["picked"] = subject
        if arrow == "->":
            obj, problem = self._person(value_text, create=True, picked=picked_obj)
            if problem is not None:
                return self._clarify(problem, dict(resume, slot="picked_obj"))
            value = {"entity": obj}
        else:
            value = {"literal": value_text}
        self._relation(relation)
        raw = f"{'correct' if correction else 'teach'} {name} {relation} {arrow} {value_text}"
        result = self.nb.assert_fact(self._eid("fact"), "listening", "taught", subject,
                                     relation, value, correction=correction, raw=raw)
        if result.status == C.CONFLICT:
            self.pending = dict(resume, kind="confirm", picked_obj=value.get("entity"))
        return result.say()

    def _ask(self, name: str, relations: list[str], picked: str | None = None) -> str:
        if picked is None:
            result = self.nb.ask(name, relations)
            if result.status == C.AMBIGUOUS:
                return self._clarify(result, {"kind": "ask", "name": name, "relations": relations})
            return result.say()
        return self.nb.ask(name, relations, entity_id=picked).say()

    def _forget(self, name: str, relation: str, picked: str | None = None) -> str:
        entity_id, problem = self._person(name, create=False, picked=picked)
        if problem is not None:
            return self._clarify(problem, {"kind": "forget", "name": name, "relation": relation})
        rows = [row for row in self.nb.current(entity_id, relation) if row["source"] == "taught"]
        if not rows:
            return C.Result(C.MISSING_FACT, {"subject": self.nb.entities[entity_id],
                                             "relation": relation}).say()
        for row in rows:
            self.nb.retract(self._eid("forget"), "listening", row["fact_id"], "Ben asked")
        return f"Forgotten: {self.nb.entities[entity_id]}'s {relation}."

    def _clarify(self, problem: C.Result, resume: dict) -> str:
        if problem.status == C.AMBIGUOUS:
            self.pending = dict(resume, choices=problem.detail["ids"])
        return problem.say()

    def _answer_pending(self, act: str, rest: list[str]) -> str:
        pending, self.pending = self.pending, None
        if pending is None:
            return "I wasn't waiting for an answer."
        if pending["kind"] == "confirm":
            if act == "yes":
                return self._teach(pending["name"], pending["relation"], pending["arrow"],
                                   pending["value_text"], True, pending["picked"],
                                   pending.get("picked_obj"))
            return "Okay, I left it as it was." if act == "no" else "Please answer yes or no."
        if act != "pick" or not rest or rest[0] not in pending.get("choices", []):
            self.pending = pending
            return "Please answer with: pick <one of the IDs I listed>."
        choice = rest[0]
        if pending["kind"] == "teach":
            pending[pending["slot"]] = choice
            return self._teach(pending["name"], pending["relation"], pending["arrow"],
                               pending["value_text"], pending["correction"],
                               pending["picked"], pending["picked_obj"])
        if pending["kind"] == "ask":
            return self._ask(pending["name"], pending["relations"], picked=choice)
        if pending["kind"] == "alias":
            return self._alias(pending["alias"], pending["name"], picked=choice)
        return self._forget(pending["name"], pending["relation"], picked=choice)


SCRIPT = [  # (line, text the reply must contain, taught rows after the turn)
    ("teach Mira city = Lisbon", "Saved: Mira's city is Lisbon", 1),
    ("teach Mira mother -> Ana", "Saved: Mira's mother is Ana", 2),
    ("teach Ana city = Porto", "Saved", 3),
    ("ask Mira mother city", "Porto.", 3),
    ("ask Mira pet", "I don't know Mira's pet", 3),
    ("ask Zed city", "I don't know anyone called Zed", 3),
    ("teach Mira city = Paris", "Do you want me to change it to Paris", 3),
    ("no", "left it as it was", 3),
    ("ask Mira city", "Lisbon.", 3),
    ("teach Mira city = Paris", "Do you want me to change it", 3),
    ("yes", "Saved: Mira's city is Paris", 4),
    ("ask Mira city", "Paris.", 4),
    ("correct Mira city = Rome", "Saved: Mira's city is Rome", 5),
    ("quote Tom said Mira lives in Oslo", "didn't save", 5),
    ("ask Mira city", "Rome.", 5),
    ("person Mira", "Saved: Mira is E0003", 5),
    ("ask Mira city", "Which one do you mean", 5),
    ("pick E0001", "Rome.", 5),
    ("teach Mira pet = cat", "Which one do you mean", 5),
    ("pick E0003", "Saved: Mira's pet is cat", 6),
    ("ask Mira pet", "Which one do you mean", 6),
    ("ask Ana city", "(I dropped my earlier question.) Porto.", 6),
    ("alias Mira K = Mira", "Which one do you mean", 6),
    ("pick E0003", "another name for Mira", 6),
    ("ask Mira K pet", "Which one do you mean", 6),   # known limit: multi-word names need the parser
    ("alias MK = Mira", "Which one", 6),
    ("pick E0003", "another name", 6),
    ("ask MK pet", "cat.", 6),
    ("forget MK pet", "Forgotten", 6),
    ("ask MK pet", "I don't know Mira's pet", 6),
    ("ask Mira city mother", "Which one do you mean", 6),
    ("pick E0001", "not someone I can look up", 6),
    ("yes", "wasn't waiting", 6),
]


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        ear = Listening(C.Notebook(tmp))
        bad = 0
        for line, must, rows in SCRIPT:
            reply = ear.hear(line)
            taught = sum(1 for e in ear.nb.events if e["kind"] == "FACT" and e["source"] == "taught")
            ok = must in reply and taught == rows
            bad += not ok
            print(f"{'PASS' if ok else 'FAIL'}  > {line}\n        {reply}" + ("" if ok else f"   [wanted '{must}', rows {rows}, got {taught}]"))
        again = Listening(C.Notebook(tmp))  # restart: everything must still be there
        restart_ok = again.hear("ask Ana city") == "Porto."
        print("restart:", "PASS" if restart_ok else "FAIL")
    print("SELFTEST", "PASS" if bad == 0 and restart_ok else f"FAIL ({bad} turns)")
    return 0 if bad == 0 and restart_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="LISTENING mode, milestone 1")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--notebook", help="folder for a persistent notebook; then type lines")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.notebook:
        parser.print_help()
        return 0
    ear = Listening(C.Notebook(args.notebook))
    for line in sys.stdin:
        print(ear.hear(line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
