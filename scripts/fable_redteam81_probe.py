"""Exp 81 -- RED TEAM probe of the LISTENING doorway (milestone 1) via English.

Under test (imported READ-ONLY, never modified, never fixed):
  scripts/fable_listening_m1.py  (LISTENING doorway: clarify-or-write)
  scripts/fable_agent_loop.py     (glue loop + FakeEars template parser, scaffolding)
  scripts/fable_notebook_contract.py (the only fact store)

Method: >= 60 adversarial ENGLISH turns in sequences through AgentLoop.turn()
(FakeEars ears, LookupReasoner, FakeMouth). Every turn records expected
(per docstring/design docs 36/54/decided-inputs), observed (exact reply text
+ notebook FACT delta), and verdict OK / BUG / UNCLEAR. Only doorway/contract
violations count as BUG; FakeEars scaffolding limits are noted, not BUGs.

  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_redteam81_probe.py --out artifacts/fable-redteam81-20260921
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

import fable_agent_loop as A  # noqa: E402  (read-only)

LONG_VAL = "Lis" * 2000

# Each step: turn, expected behaviour, substring the reply must contain,
# nowrite (no new taught FACT allowed), note. Sequences share one loop.
SEQS = [
    ("A_dup_firstname", "two people, one first name, then a question", [
        {"turn": "Mira's city is Lisbon.", "expect": "Saved Lisbon", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Mira's mother is Ana.", "expect": "Saved (creates Ana)", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Mira's city is Oslo.", "expect": "CONFLICT clarify, no silent 2nd value", "must": "change it", "nowrite": True, "note": ""},
        {"turn": "no", "expect": "keeps Lisbon", "must": "left it", "nowrite": True, "note": ""},
        {"turn": "Who is Mira's city?", "expect": "answers Lisbon", "must": "Lisbon", "nowrite": True, "note": ""},
        {"turn": "__SETUP_SECOND_MIRA__", "expect": "harness: 2nd Mira via contract (FakeEars has no person verb)",
         "must": "", "nowrite": True, "note": "setup, not a turn"},
        {"turn": "Who is Mira's city?", "expect": "ambiguous: asks which, never guesses", "must": "Which one", "nowrite": True, "note": ""},
    ]),
    ("B_corrections", "'actually, no --' partial corrections", [
        {"turn": "Mira's city is Lisbon.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Actually, Mira's city is Paris.", "expect": "correction supersedes -> Saved Paris", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Who is Mira's city?", "expect": "Paris", "must": "Paris", "nowrite": True, "note": ""},
        {"turn": "Actually, no \u2014 her city is Rome.", "expect": "pronoun -> clarify, no write (FakeEars: no pronouns)",
         "must": "say it like", "nowrite": True, "note": "FakeEars limitation"},
        {"turn": "No, Mira's city is Rome.", "expect": "'No,' prefix correction -> Saved Rome", "must": "Saved", "nowrite": False, "note": ""},
    ]),
    ("C_forget", "'forget what I said about X'", [
        {"turn": "Mira's city is Lisbon.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Forget what I said about Mira's city.", "expect": "clarify, no write (FakeEars: no forget verb)",
         "must": "another way", "nowrite": True, "note": "FakeEars limitation"},
        {"turn": "Who is Mira's city?", "expect": "still Lisbon (nothing forgotten)", "must": "Lisbon", "nowrite": True, "note": ""},
    ]),
    ("D_q_vs_s", "statement phrased as question and vice versa", [
        {"turn": "Mira's city is Lisbon?", "expect": "FakeEars strips '?', TEACHES (punctuation ignored)",
         "must": "Saved", "nowrite": False, "note": "FakeEars limitation: sharpest gap"},
        {"turn": "Who is Mira's city.", "expect": "question with '.' still answers Lisbon", "must": "Lisbon", "nowrite": True, "note": ""},
        {"turn": "Tell me Mira's city.", "expect": "imperative -> clarify, no write", "must": "another way", "nowrite": True, "note": "FakeEars limitation"},
        {"turn": "Is Mira's city Lisbon?", "expect": "yes/no Q -> clarify, no write", "must": "another way", "nowrite": True, "note": "FakeEars limitation"},
        {"turn": "Is it true that Mira's city is Lisbon?", "expect": "clarify, no write", "must": "one-word", "nowrite": True, "note": "FakeEars limitation"},
    ]),
    ("E_double", "double facts in one sentence", [
        {"turn": "Mira's city is Lisbon and Mira's pet is a cat.", "expect": "Saved with whole tail as ONE literal (FakeEars: no split)",
         "must": "Saved", "nowrite": False, "note": "FakeEars limitation"},
        {"turn": "Who is Mira's city?", "expect": "answers packed literal", "must": "Lisbon and Mira", "nowrite": True, "note": ""},
        {"turn": "Who is Mira's pet?", "expect": "MISSING (2nd fact lost)", "must": "don't know", "nowrite": True, "note": ""},
    ]),
    ("F_pronoun", "pronouns after two women mentioned", [
        {"turn": "Mira's city is Lisbon.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Ana's city is Porto.", "expect": "Saved (creates Ana)", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Her mother is Ana.", "expect": "clarify, no write ('Her mother' has no 's; FakeEars: no pronouns)",
         "must": "say it like", "nowrite": True, "note": "FakeEars limitation"},
        {"turn": "Who is her mother's city?", "expect": "UNKNOWN_ENTITY refusal, no write (pronoun passed as literal name)",
         "must": "don't know anyone", "nowrite": True, "note": "FakeEars limitation"},
    ]),
    ("G_typos", "typos in names", [
        {"turn": "Mira's city is Lisbon.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Mria's city is Paris.", "expect": "Saved as SEPARATE person (no fuzzy match; teach creates)",
         "must": "Saved", "nowrite": False, "note": "by design; FakeEars limitation"},
        {"turn": "Who is Mria's city?", "expect": "Paris", "must": "Paris", "nowrite": True, "note": ""},
        {"turn": "Who is Mira's city?", "expect": "Lisbon untouched", "must": "Lisbon", "nowrite": True, "note": ""},
    ]),
    ("H_norm", "capitalisation / whitespace / unicode variants", [
        {"turn": "Mira's city is Lisbon.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "  MIRA'S   CITY   IS   Porto.  ", "expect": "clarify, no write (FakeEars _APOS misses uppercase 'S)",
         "must": "say it like", "nowrite": True, "note": "FakeEars limitation"},
        {"turn": "MIRA's city is Porto.", "expect": "case normalised via contract _norm -> CONFLICT clarify",
         "must": "change it", "nowrite": True, "note": ""},
        {"turn": "yes", "expect": "confirm-yes corrects -> Saved Porto", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "M\u00edra's city is Oslo.", "expect": "Saved as separate person (accent not folded)", "must": "Saved", "nowrite": False, "note": "contract _norm folds case/space only"},
        {"turn": "\uff4d\uff49\uff52\uff41's city is Rome.", "expect": "Saved as separate person (fullwidth not folded)", "must": "Saved", "nowrite": False, "note": "same"},
        {"turn": "Who is Mira's city?", "expect": "Porto (original row)", "must": "Porto", "nowrite": True, "note": ""},
    ]),
    ("I_edges", "very long / empty / name-only turns", [
        {"turn": "", "expect": "clarify didn't-catch, no write", "must": "didn't catch", "nowrite": True, "note": ""},
        {"turn": "   ", "expect": "clarify didn't-catch, no write", "must": "didn't catch", "nowrite": True, "note": ""},
        {"turn": "Mira", "expect": "clarify, no write", "must": "another way", "nowrite": True, "note": ""},
        {"turn": "Mira's city is " + LONG_VAL + ".", "expect": "Saved huge literal, no crash", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Who is Mira's city?", "expect": "answers long literal", "must": "LisLis", "nowrite": True, "note": ""},
    ]),
    ("J_statuswords", "turn containing a notebook status word", [
        {"turn": "Mira's city is Lisbon.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Mira's city is SAVED.", "expect": "value word -> CONFLICT clarify, not confused", "must": "change it", "nowrite": True, "note": ""},
        {"turn": "no", "expect": "keeps Lisbon", "must": "left it", "nowrite": True, "note": ""},
        {"turn": "Mira's pet is MISSING_FACT.", "expect": "Saved literal status-word value", "must": "Saved", "nowrite": False, "note": "wording only"},
    ]),
    ("K_json", "turn that looks like JSON / structured line", [
        {"turn": '{"act": "teach", "name": "Mira"}', "expect": "clarify, no write (no JSON parsing)", "must": "another way", "nowrite": True, "note": ""},
        {"turn": "teach Mira city = Lisbon", "expect": "clarify (structured syntax is not English)", "must": "another way", "nowrite": True, "note": "FakeEars limitation"},
        {"turn": "Mira's city is Lisbon.", "expect": "Saved control", "must": "Saved", "nowrite": False, "note": ""},
    ]),
    ("L_selfref", "self-referential fact", [
        {"turn": "Mira's mother is Mira.", "expect": "Saved self-loop, no crash", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Who is Mira's mother's mother?", "expect": "Mira (self-loop terminates)", "must": "Mira", "nowrite": True, "note": ""},
        {"turn": "Mira's mother is Ana.", "expect": "CONFLICT clarify, no silent 2nd value", "must": "change it", "nowrite": True, "note": ""},
        {"turn": "Actually, Mira's mother is Ana.", "expect": "correction supersedes self-loop", "must": "Saved", "nowrite": False, "note": ""},
    ]),
    ("M_hops", "4-hop question vs <=3-hop rule", [
        {"turn": "Mira's mother is Ana.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Ana's mother is Bea.", "expect": "Saved (creates Bea)", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Bea's city is Porto.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Who is Mira's mother's mother's city?", "expect": "Porto (3 hops allowed: 4 chain parts)", "must": "Porto", "nowrite": True, "note": ""},
        {"turn": "Who is Mira's mother's mother's mother's city?", "expect": "clarify 1-to-3 steps, no write (true 4-hop)",
         "must": "1 to 3", "nowrite": True, "note": ""},
        {"turn": "Who is Mira's mother's city?", "expect": "MISSING_FACT: Ana's city never taught (harness chain is mother/mother/city)",
         "must": "don't know", "nowrite": True, "note": ""},
    ]),
    ("N_yesno", "'is it true that X?' yes/no questions", [
        {"turn": "Mira's city is Lisbon.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Is it true that Mira's city is Lisbon?", "expect": "clarify, no write (no yes/no answering)", "must": "one-word", "nowrite": True, "note": "FakeEars limitation"},
        {"turn": "What is Mira's city?", "expect": "Lisbon via what-question", "must": "Lisbon", "nowrite": True, "note": ""},
    ]),
    ("O_user", "asking about the user herself", [
        {"turn": "Mira's city is Lisbon.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "What is my mother?", "expect": "clarify + creates NOTHING (no personal inference)",
         "must": "1 to 3", "nowrite": True, "note": "", "check_no_entity": "my"},
        {"turn": "My city is Lisbon.", "expect": "clarify, no write ('My city' has no 's; no first-person handling)",
         "must": "say it like", "nowrite": True, "note": "FakeEars limitation"},
        {"turn": "Who is My's city?", "expect": "UNKNOWN_ENTITY, creates nothing (no personal inference)",
         "must": "don't know anyone", "nowrite": True, "note": "", "check_no_entity": "My"},
    ]),
    ("P_contra", "contradiction triggers clarify, yes path corrects", [
        {"turn": "Mira's city is Lisbon.", "expect": "Saved", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Mira's city is Paris.", "expect": "CONFLICT clarify", "must": "change it", "nowrite": True, "note": ""},
        {"turn": "yes", "expect": "Saved Paris", "must": "Saved", "nowrite": False, "note": ""},
        {"turn": "Who is Mira's city?", "expect": "Paris", "must": "Paris", "nowrite": True, "note": ""},
    ]),
    ("Q_quote", "reported speech / hypotheticals write nothing", [
        {"turn": "Tom said Mira lives in Oslo.", "expect": "clarify, no write, creates nobody", "must": "another way",
         "nowrite": True, "note": "", "check_no_entity": "Tom"},
        {"turn": "If Mira lived in Oslo, would that be nice?", "expect": "clarify, no write", "must": "another way", "nowrite": True, "note": ""},
        {"turn": "Mira's city is Lisbon.", "expect": "Saved control", "must": "Saved", "nowrite": False, "note": ""},
    ]),
]


def taught_facts(loop) -> int:
    return sum(1 for e in loop.nb.events if e["kind"] == "FACT" and e.get("source") == "taught")


def run() -> dict:
    cases: list[dict] = []
    for seq_id, desc, steps in SEQS:
        with tempfile.TemporaryDirectory() as folder:
            loop = A.AgentLoop(folder)
            for i, st in enumerate(steps):
                cid = f"{seq_id}-{i + 1:02d}"
                if st["turn"] == "__SETUP_SECOND_MIRA__":
                    loop.nb.new_entity("setup-second-mira", "Mira")
                    cases.append({"id": cid, "seq": seq_id, "turn": st["turn"],
                                  "expected": st["expect"], "observed": "setup: 2nd Mira entity added",
                                  "facts_delta": 0, "verdict": "OK", "note": st["note"]})
                    continue
                before = taught_facts(loop)
                ents_before = set(loop.nb.entities.values())
                try:
                    reply = " ".join(loop.turn(st["turn"]))
                    crashed = None
                except Exception as exc:  # noqa: BLE001 -- a crash is a finding
                    reply, crashed = "", f"{type(exc).__name__}: {exc}"
                delta = taught_facts(loop) - before
                statuses = (loop.experience[-1]["statuses"] if loop.experience else [])
                observed = f"reply={reply!r} statuses={statuses} taught_delta={delta}"
                if crashed is not None:
                    verdict, observed = "BUG", observed + f" CRASH={crashed}"
                    sev = "high"
                elif st.get("nowrite") and delta > 0:
                    verdict, sev = "BUG", "critical(question wrote)"
                elif st["must"] and st["must"] not in reply:
                    verdict, sev = "UNCLEAR", ""
                    observed += f" [wanted {st['must']!r}]"
                elif st.get("check_no_entity") and st["check_no_entity"] in {
                        a.lower() for a in loop.nb.aliases} | {e.lower() for e in loop.nb.entities.values()}:
                    verdict, sev = "BUG", "critical(personal inference)"
                    observed += f" [entity {st['check_no_entity']!r} exists]"
                else:
                    verdict, sev = "OK", ""
                # entity-proliferation notes are honesty flags, never verdict changes
                new_ents = set(loop.nb.entities.values()) - ents_before
                cases.append({"id": cid, "seq": seq_id, "turn": st["turn"],
                              "expected": st["expect"], "observed": observed,
                              "facts_delta": delta, "verdict": verdict,
                              "severity": sev, "note": st.get("note", ""),
                              "new_entities": sorted(new_ents)})
    nq = sum(1 for c in cases if c["turn"].strip().lower().startswith(("who ", "what ", "where ", "is "))
             or c["turn"].strip().endswith("?") and c["turn"] not in ("__SETUP_SECOND_MIRA__",))
    return {"cases": cases,
            "summary": {"n": len(cases),
                        "ok": sum(c["verdict"] == "OK" for c in cases),
                        "bug": sum(c["verdict"] == "BUG" for c in cases),
                        "unclear": sum(c["verdict"] == "UNCLEAR" for c in cases)}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    res = run()
    (out / "fable_redteam81_results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    turns = sum(1 for c in res["cases"] if c["turn"] != "__SETUP_SECOND_MIRA__")
    print(f"turns={turns} cases={res['summary']['n']} "
          f"OK={res['summary']['ok']} BUG={res['summary']['bug']} UNCLEAR={res['summary']['unclear']}")
    for c in res["cases"]:
        flag = "" if c["verdict"] == "OK" else "   <-- CHECK"
        t = c["turn"] if len(c["turn"]) < 80 else c["turn"][:77] + "..."
        print(f"{c['verdict']:7s} {c['id']:16s} > {t}{flag}")
        if c["verdict"] != "OK":
            print(f"         exp={c['expected']}\n         obs={c['observed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
