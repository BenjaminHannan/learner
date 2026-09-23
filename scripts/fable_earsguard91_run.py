"""Exp 91 -- registered run driver for marks G1-G4 (Mac CPU, offline, stdlib only).

  G1  both red-team-81 reproducers clarify with 0 writes through GuardedEars.
  G2  all 74 red-team-81 cases re-run through GuardedEars (case list imported
      from scripts/fable_redteam81_probe.py, never edited): list every case
      whose outcome changed vs bare FakeEars; none may become a wrong write.
  G3  the 60-turn acceptance file data/open/turns84/turns.jsonl through
      GuardedEars (scoring pieces imported from scripts/fable_turns84_run.py,
      never edited): bar 60/60 status match with 0 wrong writes.
  G4  daemon74 selftest (scripts/fable_daemon74_selftest.py, never edited)
      with GuardedEars(FakeEars) plugged in, by pointing its RUN at
      scripts/fable_earsguard91_daemon.py (the build_ears-hook launcher).

Writes under --out (default artifacts/fable-earsguard91-20260921/):
  fable_earsguard91_results.json  integer counts + full case tables
  g2_cases.jsonl                  per-case base-vs-guarded rows (every case listed)
  g3_per_turn.jsonl               per-turn rows (every turn listed)

  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_earsguard91_run.py --out artifacts/fable-earsguard91-20260921
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
WORKTREE = SCRIPTS.parent

import fable_agent_loop as A  # noqa: E402 (read-only)
from fable_earsguard91 import GuardedEars, QUESTION_MSG, SPLIT_MSG  # noqa: E402
from fable_redteam81_probe import SEQS  # noqa: E402 (read-only case list)
import fable_turns84_run as T84  # noqa: E402 (read-only scoring pieces)


def taught_facts(loop) -> int:
    return sum(1 for e in loop.nb.events
               if e["kind"] == "FACT" and e.get("source") == "taught")


def new_taught_literals(loop, before_ids: set):
    rows = []
    for fid, f in loop.nb.facts.items():
        if fid in before_ids or f.get("source") != "taught":
            continue
        val = f.get("value", {})
        lit = val.get("literal") if isinstance(val, dict) else val
        rows.append(str(lit))
    return rows


def forbidden_shape(lit: str) -> str | None:
    """Why a written literal would count as a wrong write (None = clean)."""
    import re
    if "?" in lit:
        return "contains ?"
    if ";" in lit:
        return "contains ;"
    if re.search(r"['\u2019][sS]\s+\S+\s+is\b", lit, re.IGNORECASE):
        return "packs a second possessive relation"
    if re.search(r"\band\b\s+\S*['\u2019][sS]\b", lit, re.IGNORECASE):
        return "packs and-possessive"
    if re.search(r"\b(is|are)\b", lit, re.IGNORECASE):
        return "packs a second copula"
    if len(lit.split()) > 6:
        return "longer than 6 words"
    return None


# ---------------------------------------------------------------- G1
def run_g1() -> dict:
    rows = []
    for turn, want_msg in [
        ("Mira's city is Lisbon?", QUESTION_MSG),
        ("Mira's city is Lisbon and Mira's pet is a cat.", SPLIT_MSG),
    ]:
        with tempfile.TemporaryDirectory(prefix="earsguard91_g1_") as folder:
            loop = A.AgentLoop(folder, ears=GuardedEars(A.FakeEars()))
            before = taught_facts(loop)
            reply = " ".join(loop.turn(turn))
            delta = taught_facts(loop) - before
            statuses = (loop.experience[-1]["statuses"] if loop.experience else [])
            clarify = statuses == ["clarify"] and want_msg in reply
            rows.append({"turn": turn, "reply": reply, "statuses": statuses,
                         "taught_delta": delta,
                         "clarify_with_msg": bool(clarify),
                         "pass": bool(clarify) and delta == 0})
    return {"rows": rows, "pass": all(r["pass"] for r in rows),
            "writes": sum(r["taught_delta"] for r in rows)}


# ---------------------------------------------------------------- G2
def run_seq(ears, seq_steps):
    """Run one red-team sequence through a fresh loop; return per-case rows."""
    import fable_redteam81_probe as P
    rows = []
    with tempfile.TemporaryDirectory(prefix="earsguard91_g2_") as folder:
        loop = A.AgentLoop(folder, ears=ears)
        for i, st in enumerate(seq_steps):
            if st["turn"] == "__SETUP_SECOND_MIRA__":
                loop.nb.new_entity("setup-second-mira", "Mira")
                rows.append({"setup": True, "taught_delta": 0,
                             "new_literals": []})
                continue
            before_n = taught_facts(loop)
            before_ids = set(loop.nb.facts.keys())
            reply = " ".join(loop.turn(st["turn"]))
            delta = taught_facts(loop) - before_n
            statuses = (loop.experience[-1]["statuses"] if loop.experience else [])
            rows.append({"setup": False, "turn": st["turn"],
                         "reply": reply, "statuses": statuses,
                         "taught_delta": delta,
                         "new_literals": new_taught_literals(loop, before_ids),
                         "nowrite": bool(st.get("nowrite"))})
    return rows


def run_g2() -> dict:
    cases = []
    for seq_id, _desc, steps in SEQS:
        base = run_seq(A.FakeEars(), steps)
        guarded = run_seq(GuardedEars(A.FakeEars()), steps)
        step_idx = [i for i, st in enumerate(steps)]
        bi = gi = 0
        for i, st in enumerate(steps):
            if st["turn"] == "__SETUP_SECOND_MIRA__":
                cases.append({"id": f"{seq_id}-{i + 1:02d}", "turn": st["turn"],
                              "setup": True, "changed": False,
                              "wrong_write": False, "wrong_detail": ""})
                bi += 1
                gi += 1
                continue
            b, g = base[bi], guarded[gi]
            bi += 1
            gi += 1
            changed = (b["reply"] != g["reply"]
                       or b["statuses"] != g["statuses"]
                       or b["taught_delta"] != g["taught_delta"])
            wrong_detail = []
            if g["nowrite"] and g["taught_delta"] > 0:
                wrong_detail.append(f"wrote {g['taught_delta']} FACT(s) on a nowrite turn")
            for lit in g["new_literals"]:
                why = forbidden_shape(lit)
                if why:
                    wrong_detail.append(f"value {lit[:80]!r}: {why}")
            cases.append({"id": f"{seq_id}-{i + 1:02d}", "turn": st["turn"],
                          "setup": False,
                          "base_reply": b["reply"], "base_statuses": b["statuses"],
                          "base_delta": b["taught_delta"],
                          "guarded_reply": g["reply"],
                          "guarded_statuses": g["statuses"],
                          "guarded_delta": g["taught_delta"],
                          "changed": changed,
                          "wrong_write": bool(wrong_detail),
                          "wrong_detail": "; ".join(wrong_detail)})
    real = [c for c in cases if not c.get("setup")]
    changed = [c["id"] for c in real if c["changed"]]
    wrong = [c["id"] for c in real if c["wrong_write"]]
    return {"n": len(cases), "changed": changed, "wrong_writes": wrong,
            "pass": len(wrong) == 0, "cases": cases}


# ---------------------------------------------------------------- G3
def run_g3(out: Path) -> dict:
    rows = [json.loads(line) for line in
            T84.TURNS.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [r["n"] for r in rows] == list(range(1, 61))
    state_dir = out / "loop-state91"
    import shutil
    if state_dir.exists():
        shutil.rmtree(state_dir)
    loop = A.AgentLoop(state_dir, ears=GuardedEars(A.FakeEars()),
                       sleep_threshold=10 ** 9)
    per_turn = []
    for row in rows:
        n, text, exp = row["n"], row["turn"], row["expected"]
        before_facts = {f["fact_id"]: f for f in loop.nb.facts.values()}
        before_entities = dict(loop.nb.entities)
        nb_events_before = len(loop.nb.events)
        loop.submit(text)
        events = loop.run_until_idle()
        listen = [e for e in events if e["mode"] == A.LISTENING]
        assert len(listen) == 1, f"turn {n}: expected 1 LISTENING tick"
        records = listen[0]["detail"]["records"]
        said = listen[0]["said"]
        assert all(e["mode"] == A.LISTENING for e in events)
        new_facts = [f for fid, f in loop.nb.facts.items()
                     if fid not in before_facts]
        new_entities = {eid: name for eid, name in loop.nb.entities.items()
                        if eid not in before_entities}
        obs = T84.observed_status(records[0]) if len(records) == 1 else "MULTI_RECORD"
        status_match = obs == exp["status"]
        answer_match = None
        if exp["status"] == "OK":
            answer_match = (records[0].get("kind") == "answer"
                            and records[0].get("fields", {}).get("answer") == exp["answer"])
        wrong, wrong_detail = 0, []
        if exp["status"] == "SAVED":
            want = exp["write"]
            if not new_facts:
                wrong += 1
                wrong_detail.append("expected a write, notebook gained no FACT row")
            for fact in new_facts:
                subj = loop.nb.entities.get(fact["subject"], "?")
                got = (subj, fact["relation"], T84.show_value(loop.nb, fact["value"]))
                if got != (want["subject"], want["relation"], want["value"]):
                    wrong += 1
                    wrong_detail.append(f"FACT {fact['fact_id']}: got {got}")
            for eid, name in new_entities.items():
                if name not in set(exp.get("new_entities", [])):
                    wrong += 1
                    wrong_detail.append(f"unexpected ENTITY {eid}={name!r}")
        else:
            for fact in new_facts:
                wrong += 1
                wrong_detail.append(f"unexpected FACT {fact['fact_id']}")
            for eid, name in new_entities.items():
                wrong += 1
                wrong_detail.append(f"unexpected ENTITY {eid}={name!r}")
        per_turn.append({"n": n, "turn": text,
                         "expected_status": exp["status"],
                         "observed_status": obs,
                         "status_match": bool(status_match),
                         "answer_match": answer_match, "said": said,
                         "wrong_writes": wrong, "wrong_detail": wrong_detail})
    match = sum(t["status_match"] for t in per_turn)
    wrong_total = sum(t["wrong_writes"] for t in per_turn)
    (out / "g3_per_turn.jsonl").write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in per_turn) + "\n",
        encoding="utf-8")
    return {"turns": len(per_turn), "status_match": match,
            "wrong_writes_total": wrong_total,
            "pass": match == 60 and wrong_total == 0, "failing": [
                t["n"] for t in per_turn
                if not t["status_match"] or t["wrong_writes"]]}


# ---------------------------------------------------------------- G4
def run_g4() -> dict:
    import fable_daemon74_selftest as S  # noqa: E402 (read-only)
    S.RUN = SCRIPTS / "fable_earsguard91_daemon.py"
    assert S.RUN.exists(), f"launcher missing: {S.RUN}"
    code = S.main()
    return {"selftest_exit": code, "pass": code == 0}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 91 registered run: G1-G4")
    ap.add_argument("--out", default=str(WORKTREE / "artifacts"
                                        / "fable-earsguard91-20260921"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    g1 = run_g1()
    print(f"G1 reproducers_clarify={sum(r['clarify_with_msg'] for r in g1['rows'])}/2 "
          f"writes={g1['writes']} {'PASS' if g1['pass'] else 'FAIL'}")
    for r in g1["rows"]:
        print(f"  > {r['turn']!r}\n    reply={r['reply']!r} statuses={r['statuses']} "
              f"delta={r['taught_delta']}")

    g2 = run_g2()
    print(f"G2 cases={g2['n']} changed={len(g2['changed'])} "
          f"wrong_writes={len(g2['wrong_writes'])} "
          f"{'PASS' if g2['pass'] else 'FAIL'}")
    print(f"  changed_cases={','.join(g2['changed']) or 'none'}")
    for c in g2["cases"]:
        if c.get("setup") or not c["changed"]:
            continue
        print(f"  {c['id']}: base={c['base_reply']!r} -> "
              f"guarded={c['guarded_reply']!r}")

    g3 = run_g3(out)
    print(f"G3 turns={g3['turns']} status_match={g3['status_match']}/60 "
          f"wrong_writes={g3['wrong_writes_total']} "
          f"{'PASS' if g3['pass'] else 'FAIL'}")

    g4 = run_g4()
    print(f"G4 daemon74_selftest_with_guard exit={g4['selftest_exit']} "
          f"{'PASS' if g4['pass'] else 'FAIL'}")

    results = {"G1": g1,
               "G2": {"n": g2["n"], "changed": g2["changed"],
                      "wrong_writes": g2["wrong_writes"], "pass": g2["pass"]},
               "G3": {k: g3[k] for k in ("turns", "status_match",
                                         "wrong_writes_total", "pass", "failing")},
               "G4": g4,
               "marks": {"G1_reproducers_clarify": g1["pass"],
                         "G2_no_new_wrong_write": g2["pass"],
                         "G3_turns60_zero_wrong": g3["pass"],
                         "G4_daemon_selftest": g4["pass"]}}
    (out / "fable_earsguard91_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "g2_cases.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in g2["cases"]) + "\n",
        encoding="utf-8")
    ok = all(results["marks"].values())
    print("EARSGUARD91", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
