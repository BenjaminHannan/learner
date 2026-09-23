#!/usr/bin/env python3
"""Agent 4 (WIRING) -- the persistent agent: real parts, one process Ben can talk to.

    uv run --offline --no-project --python 3.12 --with torch --with numpy \
        python -B scripts/fable_wire51_run.py --state-dir artifacts/fable-wire51-20260921/agent

Everything is wrapped, nothing else is edited.  The loop (fable_agent_loop) keeps its
own state.json + hash-chained notebook; this runner adds:

  * decisions.jsonl -- append-only, hash-chained log of EVERY decision (turn, actions,
    records, said, sleep/think events).  A torn last line (kill -9 mid-write) is kept
    out of the way on resume and never corrupts the next append.
  * resume -- restart on the same --state-dir continues from the event log; a torn
    notebook tail is repaired by the notebook contract itself.
  * --replay N -- cold-start the 40-turn script N times and count taught rows, wrong
    writes, correct answers and abstentions.
  * --selftest -- offline checks (no model, no network).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A                    # noqa: E402
import fable_notebook_contract as C             # noqa: E402
import fable_wire51_adapters as AD              # noqa: E402
import fable_wire51_script40 as S               # noqa: E402

DECISIONS = "decisions.jsonl"
ARTIFACT = SCRIPTS.parent / "artifacts" / "fable-wire51-20260921"
SEED_PEOPLE = ("Ben", "self")


# ------------------------------------------------------------------ decisions log
def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def repair_decisions(path: Path) -> str | None:
    """Keep only whole hash-chained lines; a torn tail is saved aside."""
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8")
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    good: list[str] = []
    prev = "0" * 64
    torn_at = None
    for i, line in enumerate(lines):
        try:
            event = json.loads(line)
            if event.get("prev") != prev:
                raise ValueError("chain broken")
            prev = event["hash"]
            good.append(line)
        except Exception:
            torn_at = i
            break
    if torn_at is None:
        return None
    kept = "\n".join(good) + ("\n" if good else "")
    (path.parent / "decisions-torn-tail.txt").write_text(
        "\n".join(lines[torn_at:]), encoding="utf-8")
    tmp = path.with_suffix(".tmp")
    tmp.write_text(kept, encoding="utf-8")
    os.replace(tmp, path)
    return f"repaired decisions log: kept {len(good)} lines, saved torn tail"


class DecisionLog:
    def __init__(self, folder: Path) -> None:
        self.path = folder / DECISIONS
        self.prev = "0" * 64
        self.n = 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    self.prev, self.n = event["hash"], int(event.get("n", self.n))
                except Exception:
                    break
        self.n += 1

    def write(self, event: dict) -> None:
        payload = dict(event, n=self.n, prev=self.prev)
        payload["hash"] = _sha(json.dumps(payload, sort_keys=True, ensure_ascii=False))
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.prev, self.n = payload["hash"], self.n + 1


# ----------------------------------------------------------------------- the runner
class Runner:
    def __init__(self, state_dir, *, ears_mode="auto", sleep_threshold=A.SLEEP_THRESHOLD,
                 base_url=None, model=None, checkpoint=None, seed=4102,
                 thinker=True, echo=False) -> None:
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        note = repair_decisions(self.dir / DECISIONS)
        self.loop, self.parts = AD.build_loop(
            state_dir, ears_mode=ears_mode, sleep_threshold=sleep_threshold,
            base_url=base_url, model=model, checkpoint=checkpoint, seed=seed,
            thinker=thinker, echo_confirm=echo)
        self.log = DecisionLog(self.dir)
        if note:
            self.loop.notes.append(note)
        self.ears = self.parts["ears"]
        if not self.loop.nb.entities:                       # cold start: the two identities
            for name in SEED_PEOPLE:
                reply = self.loop.listening.hear(f"person {name}")
                self.log.write({"event": "seed", "person": name, "reply": reply})
            self.loop._save()

    # ------------------------------------------------------------------- one turn
    def turn(self, text: str, *, kind: str = "live", turn_index: int | None = None) -> list[str]:
        facts_before = set(self.loop.nb.facts)
        entities_before = set(self.loop.nb.entities)
        self.loop.submit(text)
        events = self.loop.run_until_idle()
        said = [line for event in events for line in event["said"]]
        facts_after = set(self.loop.nb.facts)
        entities_after = set(self.loop.nb.entities)
        self.log.write({
            "event": "turn", "kind": kind, "turn_index": turn_index, "text": text,
            "ears": self.ears.last_source,
            "new_facts": sorted(facts_after - facts_before),
            "new_entities": sorted(entities_after - entities_before),
            "said": said,
            "events": [{"mode": e["mode"], "detail": e["detail"], "said": e["said"],
                        "log_size": e["log_size"]} for e in events],
            "counters": dict(self.loop.counters),
        })
        return said

    def stats(self) -> dict:
        nb = self.loop.nb
        taught = [f for f in nb.facts.values() if f["source"] == "taught"]
        return {
            "ticks": self.loop.tick,
            "counters": dict(self.loop.counters),
            "taught_rows": len(taught),
            "active_taught_rows": sum(1 for f in taught if nb.active(f["fact_id"])),
            "entities": len(nb.entities),
            "notebook_events": len(nb.events),
            "experience_log": len(self.loop.experience),
            "ears_backend": self.ears.mode,
            "ears_last": self.ears.last_source,
            "bridge_failures": self.ears.bridge_failures,
            "fallback_turns": self.ears.fallback_turns,
            "reasoner_backend": self.parts["reasoner"].backend,
            "router_ready": self.parts["reasoner"].router_ready,
            "router_runs": self.parts["reasoner"].router_runs,
            "router_agree": self.parts["reasoner"].router_agree,
            "router_disagree": self.parts["reasoner"].router_disagree,
            "router_skips": self.parts["reasoner"].router_skips,
            "word_lookups": self.parts["reasoner"].word_lookups,
            "word_episodes_queued": len(self.parts["reasoner"].episodes),
            "sleeps": self.parts["sleeper"].sleeps,
            "sleep_installs": self.parts["sleeper"].installs,
        }


# -------------------------------------------------------------------------- replay
def _value_display(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], value["entity"])
    return str(value.get("literal", ""))


def score_turn(run: Runner, turn: dict, before_facts: set, before_entities: set,
               said: str) -> dict:
    nb = run.loop.nb
    new_facts = [nb.facts[fid] for fid in set(nb.facts) - before_facts]
    new_entities = set(nb.entities) - before_entities
    kind, expect = turn["kind"], turn.get("expect", {})
    out = {"kind": kind, "text": turn["text"], "said": said,
           "new_facts": len(new_facts), "new_entities": len(new_entities),
           "wrong_write": False, "missing_write": False, "correct": False,
           "abstained": False, "note": ""}

    expected = expect.get("fact")
    if kind in (S.TEACH, S.PICK) and expected:
        subject, relation, value, correction = expected
        match = False
        if len(new_facts) == 1:
            row = new_facts[0]
            got = (nb.entities.get(row["subject"], ""), row["relation"],
                   _value_display(nb, row["value"]))
            want = (subject, relation, value)
            match = got == want and row["source"] == "taught" and \
                bool(row.get("supersedes")) == bool(correction)
        if match:
            out["correct"] = True
        elif new_facts:
            out["wrong_write"] = True
            out["note"] = f"expected {expected}, got " + str(
                [(nb.entities.get(f['subject'], ''), f['relation'],
                  _value_display(nb, f['value'])) for f in new_facts])
        else:
            out["missing_write"] = True
            out["note"] = "expected a fact, none written"
    elif kind == S.AMBIG:
        if new_facts:
            out["wrong_write"] = True
            out["note"] = "ambiguous teach wrote before the pick"
    elif kind == S.CREATE:
        if len(new_entities) != 1 or new_facts:
            out["note"] = f"entities {len(new_entities)}, facts {len(new_facts)}"
            out["wrong_write"] = bool(new_facts)
    elif kind in (S.ONE_HOP, S.TWO_HOP):
        if new_facts:
            out["wrong_write"] = True
            out["note"] = "a question wrote a fact"
        if expect.get("answer", "").lower() in said.lower():
            out["correct"] = True
        else:
            out["note"] = f"expected {expect.get('answer')!r}"
    elif kind == S.UNANSWERABLE:
        if new_facts:
            out["wrong_write"] = True
            out["note"] = "an unanswerable question wrote a fact"
        phrase = expect.get("abstain", "")
        phrases = phrase if isinstance(phrase, (list, tuple)) else (phrase,)
        if any(str(p).lower() in said.lower() for p in phrases) and not new_facts:
            out["abstained"] = True
        else:
            out["note"] = f"expected abstention containing {phrases!r}"
    elif kind in (S.TRAP, S.SMALLTALK):
        if new_facts:
            out["wrong_write"] = True
            out["note"] = "trap/small talk wrote a fact"
    return out


def replay(state_root: Path, runs: int, *, ears_mode: str, sleep_threshold: int,
           base_url: str | None, checkpoint: str | None, seed: int,
           echo: bool = False) -> dict:
    reports = []
    for index in range(1, runs + 1):
        folder = state_root / f"cold-{index}"
        if folder.exists():
            shutil.rmtree(folder)
        run = Runner(folder, ears_mode=ears_mode, sleep_threshold=sleep_threshold,
                     base_url=base_url, checkpoint=checkpoint, seed=seed, thinker=False,
                     echo=echo)
        per_turn = []
        for i, turn in enumerate(S.TURNS, 1):
            text = S.expand(turn["text"], run.loop.nb.aliases)
            before_facts = set(run.loop.nb.facts)
            before_entities = set(run.loop.nb.entities)
            said = " ".join(run.turn(text, kind=turn["kind"], turn_index=i))
            entry = score_turn(run, turn, before_facts, before_entities, said)
            entry["ears_source"] = run.ears.last_source
            per_turn.append(entry)
        stats = run.stats()
        taught = [f for f in run.loop.nb.facts.values() if f["source"] == "taught"]
        report = {
            "run": index,
            "turns": len(S.TURNS),
            "taught_rows": len(taught),
            "active_taught_rows": sum(1 for f in taught if run.loop.nb.active(f["fact_id"])),
            "superseded_taught_rows": len(taught) - sum(
                1 for f in taught if run.loop.nb.active(f["fact_id"])),
            "wrong_writes": sum(1 for t in per_turn if t["wrong_write"]),
            "missing_writes": sum(1 for t in per_turn if t["missing_write"]),
            "unexpected_entities": sum(
                t["new_entities"] for t in per_turn
                if t["kind"] in (S.ONE_HOP, S.TWO_HOP, S.UNANSWERABLE, S.TRAP,
                                 S.SMALLTALK, S.PICK)),
            "questions": sum(1 for t in per_turn
                             if t["kind"] in (S.ONE_HOP, S.TWO_HOP, S.UNANSWERABLE)),
            "correct_answers": sum(1 for t in per_turn
                                   if t["kind"] in (S.ONE_HOP, S.TWO_HOP) and t["correct"]),
            "wrong_answers": sum(1 for t in per_turn
                                 if t["kind"] in (S.ONE_HOP, S.TWO_HOP) and not t["correct"]),
            "abstentions": sum(1 for t in per_turn if t["abstained"]),
            "missed_abstentions": sum(
                1 for t in per_turn
                if t["kind"] == S.UNANSWERABLE and not t["abstained"]),
            "two_hop": sum(1 for t in per_turn if t["kind"] == S.TWO_HOP),
            "two_hop_correct": sum(1 for t in per_turn
                                   if t["kind"] == S.TWO_HOP and t["correct"]),
            "traps": sum(1 for t in per_turn if t["kind"] == S.TRAP),
            "smalltalk": sum(1 for t in per_turn if t["kind"] == S.SMALLTALK),
            "ears_english": sum(1 for t in per_turn
                                if str(t.get("ears_source", "")).startswith("english")),
            "stats": stats,
            "sleeps": stats["sleeps"],
            "per_turn": per_turn,
        }
        reports.append(report)
    aggregate = {"runs": runs, "per_run": reports}
    for key in ("turns", "taught_rows", "active_taught_rows", "wrong_writes",
                "missing_writes", "unexpected_entities", "questions", "correct_answers",
                "wrong_answers", "abstentions", "missed_abstentions", "two_hop",
                "two_hop_correct", "traps", "smalltalk", "sleeps"):
        aggregate[key] = [r[key] for r in reports]
    return aggregate


# ---------------------------------------------------------------------------- REPL
HELP = """Commands:
  <any English sentence>   teach me, ask me, chat
  /stats                   counters (turns, writes, sleeps, router checks)
  think                    run one THINKING tick now (needs an assigned topic)
  assign <topic>           give THINKING a topic (web search on the next think)
  review / approve <id> / reject <id>   the quarantine review desk
  ears auto|english|fake   switch the ears slot
  /help                    this text
  /quit                    save and exit (kill -9 is also safe)"""


def repl(run: Runner) -> int:
    for note in run.loop.notes:
        print(f"[note] {note}", flush=True)
    stats = run.stats()
    print(f"fable is listening ({stats['ears_backend']} ears, "
          f"{stats['reasoner_backend']}, {stats['taught_rows']} taught rows). "
          f"Type /help.", flush=True)
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in ("/quit", "/exit"):
            return 0
        if line == "/help":
            print(HELP)
            continue
        if line == "/stats":
            print(json.dumps(run.stats(), indent=1, sort_keys=True))
            continue
        if line.startswith("ears "):
            mode = line.split(None, 1)[1].strip()
            if mode in ("auto", "english", "fake"):
                run.ears.mode = mode
                print(f"ears = {mode}")
            else:
                print("ears must be auto, english or fake")
            continue
        if line == "assign" or line.startswith("assign "):
            topic = line.split(None, 1)[1] if " " in line else ""
            print(run.parts["thinking"].assign(topic) if topic else "assign <topic>")
            continue
        if line == "think":
            event = run.loop.step() if not run.loop.busy() else None
            if event is None:
                print("I still have a turn to finish first.")
            else:
                thought = event["detail"].get("thought")
                run.log.write({"event": "think", "detail": event["detail"]})
                print((thought or {}).get("said") if isinstance(thought, dict)
                      else (thought or "Nothing to think about."))
            continue
        if line == "review":
            print(run.parts["thinking"].review())
            continue
        if line.startswith(("approve ", "reject ")):
            verb, fid = line.split(None, 1)
            print(getattr(run.parts["thinking"], verb)(fid.strip()))
            continue
        said = run.turn(line)
        print(" ".join(said) or "(okay)", flush=True)


# ------------------------------------------------------------------------ selftest
def _selftest() -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name, ok, note=""):
        results.append((name, bool(ok), note))
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{note}]" if note and not ok else ""))

    for name, ok, note in S.check_composition():
        check("script: " + name, ok, note)

    act = AD.line_to_action("teach Mira city = Lisbon")
    check("mapper: teach", act == {"act": "teach", "name": "Mira", "relation": "city",
                                   "value": "Lisbon", "is_person": False}, str(act))
    act = AD.line_to_action("teach Mira mother -> Ana")
    check("mapper: person-valued teach", act["is_person"] and act["value"] == "Ana", str(act))
    act = AD.line_to_action("ask Ana friend city")
    check("mapper: two-hop ask", act == {"act": "ask", "name": "Ana",
                                         "relations": ["friend", "city"]}, str(act))
    act = AD.line_to_action('teach "Mary Jane" city = "New York"')
    check("mapper: quoted atoms", act["name"] == "Mary Jane" and act["value"] == "New York",
          str(act))
    act = AD.line_to_action("quote Tom said hi")
    check("mapper: quote passthrough", act["line"].startswith("quote"), str(act))

    mouth = AD.TemplateMouth()
    ok_line = mouth.say({"kind": "answer", "status": C.OK, "name": "Mira",
                         "relations": ["city"], "fields": {"answer": "Lisbon"}})
    miss = mouth.say({"kind": "answer", "status": C.MISSING_FACT, "name": "Mira",
                      "relations": ["pet"],
                      "fields": {"subject": "Mira", "relation": "pet"}})
    check("mouth: OK template", ok_line == "Mira's city is Lisbon.", repr(ok_line))
    check("mouth: MISSING_FACT template", miss == "I don't know Mira's pet.", repr(miss))

    ears = AD.EnglishEars(mode="fake")
    check("ears: fake mode parses a statement",
          ears.hear("Mira's city is Lisbon.")[0]["act"] == "teach", "")
    dead = AD.EnglishEars(mode="auto", base_url="http://127.0.0.1:9")
    actions = dead.hear("Mira's city is Lisbon.")
    check("ears: auto falls back when the bridge is down",
          dead.last_source == "fake-fallback" and actions[0]["act"] == "teach"
          and dead.fallback_turns == 1, dead.last_source)
    strict = AD.EnglishEars(mode="english", base_url="http://127.0.0.1:9")
    try:
        strict.hear("Mira's city is Lisbon.")
        check("ears: english mode reports a dead bridge", False, "no exception")
    except (RuntimeError, OSError):
        check("ears: english mode reports a dead bridge", True, "")

    with tempfile.TemporaryDirectory() as tmp:
        run = Runner(tmp, ears_mode="fake")
        said = " ".join(run.turn("Mira's city is Lisbon."))
        said2 = " ".join(run.turn("Who is Mira's city?"))
        check("runner: teach + ask through the full wire",
              "Saved" in said and said2.endswith("Lisbon."), f"{said!r} {said2!r}")
        sleeper = run.parts["sleeper"]
        outcome = sleeper.sleep(list(run.loop.experience), run.loop.nb)
        check("sleeper: clean audit accepts",
              outcome["accepted"] and outcome["audit"]["violations"] == []
              and outcome["recipe"]["attempted"] is False, json.dumps(outcome)[:200])
        stats = run.stats()
        check("stats: every slot reported",
              stats["reasoner_backend"] and "router_runs" in stats
              and stats["sleeps"] == 1, str(stats["sleeps"]))
        check("stats: reasoner50 preferred when present",
              stats["reasoner_backend"] == "fable_reasoner50", stats["reasoner_backend"])

        # the Exp 44 wrap is the fallback path (prefer50=False still answers)
        fb = AD.NotebookReasoner(tmp, prefer50=False)
        tiny = run.loop.nb
        rec = fb.answer({"name": "Mira", "relations": ["city"]}, tiny)
        check("reasoner: 44-wrap fallback still answers",
              rec.get("status") == C.OK and rec["fields"].get("answer") == "Lisbon",
              json.dumps(rec)[:200])

        # kill -9 mid-session, then resume from the event log
        child = subprocess.Popen(
            [sys.executable, "-B", str(SCRIPTS / "fable_wire51_run.py"),
             "--state-dir", tmp, "--ears", "fake", "--once", "Ana's city is Porto."],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        child.wait(timeout=60)
        again = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "fable_wire51_run.py"),
             "--state-dir", tmp, "--ears", "fake", "--once", "Who is Ana's city?"],
            capture_output=True, text=True, timeout=60)
        check("runner: resume answers from the event log",
              "Porto" in again.stdout, f"{again.stdout!r} {again.stderr[-200:]!r}")

        # a torn decisions tail must not block the next append
        dec = Path(tmp) / DECISIONS
        with open(dec, "a", encoding="utf-8") as handle:
            handle.write('{"n": 99, "event": "tur')
        resumed = Runner(tmp, ears_mode="fake")
        resumed.turn("Kai's city is Oslo.")
        ok = any("repaired decisions" in n for n in resumed.loop.notes)
        check("runner: torn decisions tail repaired on resume", ok, str(resumed.loop.notes))

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"{passed}/{len(results)} tests passed")
    print("SELFTEST", "PASS" if passed == len(results) else "FAIL")
    return 0 if passed == len(results) else 1


# ---------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Wiring: the persistent agent (doc 51)")
    parser.add_argument("--state-dir", help="folder holding notebook/ + state.json + decisions")
    parser.add_argument("--once", help="one turn, print the reply, exit")
    parser.add_argument("--turns", help="file of turns, one per line, then exit")
    parser.add_argument("--replay", type=int, metavar="N",
                        help="cold-start the 40-turn script N times and report counts")
    parser.add_argument("--report", help="where to write the replay report json")
    parser.add_argument("--ears", choices=("auto", "english", "fake"), default="auto")
    parser.add_argument("--sleep-threshold", type=int, default=A.SLEEP_THRESHOLD)
    parser.add_argument("--base-url", default=None, help="Qwen bridge (default 127.0.0.1:18081)")
    parser.add_argument("--checkpoint", default=None, help="Exp 44 base checkpoint .pt")
    parser.add_argument("--seed", type=int, default=4102)
    parser.add_argument("--echo", action="store_true",
                        help="enable the English adapter's extra write echo-confirmation")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.replay:
        root = Path(args.state_dir) if args.state_dir else ARTIFACT / "runs"
        report = replay(root, args.replay, ears_mode=args.ears,
                        sleep_threshold=args.sleep_threshold, base_url=args.base_url,
                        checkpoint=args.checkpoint, seed=args.seed, echo=args.echo)
        text = json.dumps(report, indent=1, sort_keys=True)
        out = Path(args.report) if args.report else ARTIFACT / "replay-report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        for key in ("turns", "taught_rows", "wrong_writes", "missing_writes",
                    "correct_answers", "wrong_answers", "abstentions", "missed_abstentions",
                    "two_hop_correct", "sleeps", "unexpected_entities"):
            print(f"{key}: {report[key]}")
        print(f"report -> {out}")
        return 0

    if not args.state_dir or not (args.once or args.turns):
        parser.print_help()
        return 0

    run = Runner(args.state_dir, ears_mode=args.ears,
                 sleep_threshold=args.sleep_threshold, base_url=args.base_url,
                 checkpoint=args.checkpoint, seed=args.seed, echo=args.echo)
    if args.once:
        print(" ".join(run.turn(args.once)), flush=True)
        return 0
    if args.turns:
        for line in Path(args.turns).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                print(" ".join(run.turn(line)) or "(okay)", flush=True)
        return 0
    return repl(run)


if __name__ == "__main__":
    sys.exit(main())
