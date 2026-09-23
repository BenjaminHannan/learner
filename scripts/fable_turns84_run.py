"""Exp 84 -- run the 60 natural turns through the glue loop and score each turn.

Reads data/open/turns84/turns.jsonl, feeds turns in order through
AgentLoop(FakeEars/FakeMouth/LookupReasoner), and scores every turn against its
expected entry: exact status match, answer match for OK, and no wrong writes.

Writes (under --out, default artifacts/fable-turns84-20260921/):
  per_turn.jsonl   one scored row per turn (never averaged, every turn listed)
  summary.json     integer counts + U1..U4 marks
  loop-state/      fresh notebook + loop state for this run (wiped at start)

Stdlib only. Deterministic: single ordered pass, no seeds, no sampling.

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
        python -B scripts/fable_turns84_run.py
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

WORKTREE = Path(__file__).resolve().parent.parent
if str(WORKTREE / "scripts") not in sys.path:
    sys.path.insert(0, str(WORKTREE / "scripts"))

import fable_agent_loop as A  # noqa: E402

TURNS = WORKTREE / "data" / "open" / "turns84" / "turns.jsonl"
DEFAULT_OUT = WORKTREE / "artifacts" / "fable-turns84-20260921"

# Turns whose expected outcome is CLARIFY are FakeEars template limits by
# construction (documented per-turn in turns.jsonl rationale); anything that
# parses is scored against the doorway + notebook contract.
EARS_LIMIT_TURNS = {34, 49, 50, 51, 52, 53, 54, 55, 56, 58, 59, 60}


def observed_status(record: dict) -> str:
    kind = record.get("kind")
    if kind == "clarify":
        return "CLARIFY"
    if kind == "answer":
        return str(record.get("status"))
    if kind == "write":
        text = record.get("text", "")
        if record.get("wrote") and text.startswith("Saved"):
            return "SAVED"
        if "already have" in text:
            return "DUPLICATE_OK"
        if "change it to" in text:
            return "CONFLICT"
        if "Which one do you mean" in text:
            return "AMBIGUOUS"
        return "WRITE_OTHER"
    return f"KIND_{kind}"


def show_value(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], f"?{value['entity']}")
    return str(value.get("literal"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 84 natural-turns acceptance run")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    state_dir = out / "loop-state"
    if state_dir.exists():
        shutil.rmtree(state_dir)

    rows = [json.loads(line) for line in TURNS.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    assert [r["n"] for r in rows] == list(range(1, 61)), "turns must be n=1..60 in order"

    # Huge sleep threshold: sleep must never fire mid-transcript (StubSleeper
    # changes nothing, but a SLEEP tick would muddy the per-turn table).
    loop = A.AgentLoop(state_dir, sleep_threshold=10 ** 9)

    per_turn = []
    for row in rows:
        n, text = row["n"], row["turn"]
        exp = row["expected"]
        before_facts = {f["fact_id"]: f for f in loop.nb.facts.values()}
        before_entities = dict(loop.nb.entities)
        nb_events_before = len(loop.nb.events)

        loop.submit(text)
        events = loop.run_until_idle()
        listen = [e for e in events if e["mode"] == A.LISTENING]
        assert len(listen) == 1, f"turn {n}: expected 1 LISTENING tick, got {len(events)}"
        records = listen[0]["detail"]["records"]
        said = listen[0]["said"]
        assert all(e["mode"] == A.LISTENING for e in events), \
            f"turn {n}: unexpected non-LISTENING tick {[e['mode'] for e in events]}"

        new_facts = [f for fid, f in loop.nb.facts.items() if fid not in before_facts]
        new_entities = {eid: name for eid, name in loop.nb.entities.items()
                        if eid not in before_entities}

        obs = observed_status(records[0]) if len(records) == 1 else "MULTI_RECORD"
        status_match = obs == exp["status"]

        answer_match: bool | None = None
        if exp["status"] == "OK":
            answer_match = (records[0].get("kind") == "answer"
                            and records[0].get("fields", {}).get("answer") == exp["answer"])

        # ---- wrong-write audit (U1): every new FACT row must be the intended one,
        # and non-write turns must add no FACT rows at all.
        wrong = 0
        wrong_detail: list[str] = []
        if exp["status"] == "SAVED":
            want = exp["write"]
            if not new_facts:
                wrong += 1
                wrong_detail.append("expected a write, notebook gained no FACT row")
            for fact in new_facts:
                subj = loop.nb.entities.get(fact["subject"], "?")
                got = (subj, fact["relation"], show_value(loop.nb, fact["value"]))
                want_triple = (want["subject"], want["relation"], want["value"])
                if got != want_triple:
                    wrong += 1
                    wrong_detail.append(f"FACT {fact['fact_id']}: got {got}, want {want_triple}")
            allowed = set(exp.get("new_entities", []))
            for eid, name in new_entities.items():
                if name not in allowed:
                    wrong += 1
                    wrong_detail.append(f"unexpected ENTITY {eid}={name!r}")
        else:
            for fact in new_facts:
                wrong += 1
                wrong_detail.append(
                    f"unexpected FACT {fact['fact_id']}: "
                    f"({loop.nb.entities.get(fact['subject'], '?')}, "
                    f"{fact['relation']}, {show_value(loop.nb, fact['value'])})")
            for eid, name in new_entities.items():
                wrong += 1
                wrong_detail.append(f"unexpected ENTITY {eid}={name!r} on a non-write turn")

        per_turn.append({
            "n": n, "turn": text, "kind": row["kind"],
            "expected_status": exp["status"], "observed_status": obs,
            "status_match": bool(status_match), "answer_match": answer_match,
            "said": said,
            "notebook_events_added": len(loop.nb.events) - nb_events_before,
            "new_fact_ids": [f["fact_id"] for f in new_facts],
            "wrong_writes": wrong, "wrong_detail": wrong_detail,
            "limit_class": ("ears-template-limit (expected; real ears replaces it)"
                            if n in EARS_LIMIT_TURNS else "parsed-ok"),
        })

    def sel(kind=None, statuses=()):
        return [t for t in per_turn
                if (kind is None or t["kind"] == kind)
                and (not statuses or t["expected_status"] in statuses)]

    questions = sel("question")
    messy = sel("messy")
    summary = {
        "turns": len(per_turn),
        "status_match": sum(t["status_match"] for t in per_turn),
        "wrong_writes_total": sum(t["wrong_writes"] for t in per_turn),
        "question_turns": len(questions),
        "question_match": sum(t["status_match"] and t["wrong_writes"] == 0
                              for t in questions),
        "question_wrong_answers": sum(
            1 for t in questions
            if t["observed_status"] == "OK"
            and (t["answer_match"] is not True)),
        "messy_turns": len(messy),
        "messy_ok": sum(1 for t in messy if (
            (t["expected_status"] == "CLARIFY" and t["observed_status"] == "CLARIFY")
            or (t["expected_status"] == "SAVED" and t["status_match"]
                and t["answer_match"] is not False)) and t["wrong_writes"] == 0),
        "messy_wrong_writes": sum(t["wrong_writes"] for t in messy),
        "marks": {},
    }
    summary["marks"]["U1_zero_wrong_writes"] = summary["wrong_writes_total"] == 0
    summary["marks"]["U2_questions_ge_13_of_15_no_wrong"] = (
        summary["question_match"] >= 13 and summary["question_wrong_answers"] == 0)
    summary["marks"]["U3_messy_clarify_or_correct"] = (
        summary["messy_ok"] == 5 and summary["messy_wrong_writes"] == 0)
    summary["marks"]["U4_table_with_limit_classes"] = all(
        "limit_class" in t for t in per_turn)

    (out / "per_turn.jsonl").write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in per_turn) + "\n",
        encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"turns={summary['turns']} status_match={summary['status_match']}/60 "
          f"wrong_writes={summary['wrong_writes_total']}")
    print(f"questions: match={summary['question_match']}/15 "
          f"wrong_answers={summary['question_wrong_answers']}")
    print(f"messy: ok={summary['messy_ok']}/5 "
          f"wrong_writes={summary['messy_wrong_writes']}")
    for name, ok in summary["marks"].items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    failing = [t["n"] for t in per_turn if not t["status_match"] or t["wrong_writes"]]
    print("failing_turns=" + (",".join(map(str, failing)) or "none"))
    for t in per_turn:
        if not t["status_match"] or t["wrong_writes"]:
            print(f"  turn {t['n']}: {t['turn']!r} expected={t['expected_status']} "
                  f"observed={t['observed_status']} said={t['said']!r} "
                  f"wrong={t['wrong_detail']}")
    return 0 if all(summary["marks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
