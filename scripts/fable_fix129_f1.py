#!/usr/bin/env python3
"""Exp 129 F1 -- sealed punctuation probe set, both new loops.

≥40 teach/correct sentences across every teach path x with/without final
'.', '!', '?', trailing spaces, plus ≥8 abbreviation names. Each case runs
in a FRESH daemon dir through the mailbox (process_file). Bar: 0 failures,
where a failure is a stored subject/value with trailing sentence
punctuation, a dropped abbreviation period, a missing expected fact, or an
unexpected write.

Expectation kinds:
  teach: exactly the expected triple is added, nothing else, on that turn.
  clarify: 0 new facts on every turn (the exp-91 "?" screen still refuses
    '?' values; the exp-92-unaware 129a still clarifies 121-extra shapes).

'?' direct teaches clarify on the OLD loops too (pre-seal calibration:
"Was that a question?", 0 writes), so clarify-nowrite is the honest
pre-written expectation there -- the mixin does not change it.

Sealed cases snapshot: artifacts/fable-fix129-20260922/fable_fix129_f1_cases.json
(sha recorded in PASSMARKS.md BEFORE the registered run).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix129_f1.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_common as C129  # noqa: E402 (this experiment)
import fable_fix129_punct as P129  # noqa: E402 (this experiment's mixin)
import fable_loop90_agent as L90  # noqa: E402 (triples view, read-only)

ART = C129.ART129
CASES_PATH = ART / "fable_fix129_f1_cases.json"
REPORT_A = ART / "fable_fix129_f1_129a.json"
REPORT_B = ART / "fable_fix129_f1_129b.json"

CIT = "country_of_citizenship"

# (id, teach-path tag, turns, expect-kind, expect-triple-or-None, note)
CASES: list[tuple] = [
    # bench73 citizen path
    ("P01", "bench73", ["Nora Brightmore is a citizen of Italy."],
     "teach", ("Nora Brightmore", CIT, "Italy"), "final period"),
    ("P02", "bench73", ["Nora Brightmore is a citizen of Italy!"],
     "teach", ("Nora Brightmore", CIT, "Italy"), "bang"),
    ("P03", "bench73", ["Nora Brightmore is a citizen of Italy?"],
     "clarify", None, "question mark refused by old screen"),
    ("P04", "bench73", ["Nora Brightmore is a citizen of Italy.  "],
     "teach", ("Nora Brightmore", CIT, "Italy"), "trailing spaces"),
    ("P05", "bench73", ["Nora Brightmore is a citizen of Peru"],
     "teach", ("Nora Brightmore", CIT, "Peru"), "no-punct control"),
    # bench73 capital path
    ("P06", "bench73", ["The capital of Norland is Oslo."],
     "teach", ("Norland", "capital", "Oslo"), "final period"),
    ("P07", "bench73", ["The capital of Norland is Oslo!"],
     "teach", ("Norland", "capital", "Oslo"), "bang"),
    ("P08", "bench73", ["The capital of Norland is Oslo?"],
     "clarify", None, "question mark refused by old screen"),
    # bench73 official-language path
    ("P09", "bench73", ["The official language of Norland is Norse."],
     "teach", ("Norland", "official_language", "Norse"), "final period"),
    ("P10", "bench73", ["The official language of Norland is Norse!"],
     "teach", ("Norland", "official_language", "Norse"), "bang"),
    # correction-prefix path
    ("P11", "correction", ["Tessa Marlowe is a citizen of Spain",
                           "Actually, Tessa Marlowe is a citizen of Portugal."],
     "teach2", [("Tessa Marlowe", CIT, "Spain"),
                ("Tessa Marlowe", CIT, "Portugal")], "124 reteach shape"),
    ("P12", "correction", ["The capital of Zorland is Lima",
                           "No, the capital of Zorland is Quito."],
     "teach2", [("Zorland", "capital", "Lima"),
                ("Zorland", "capital", "Quito")], "No-prefix correction"),
    ("P13", "correction", ["Sorry, I meant Hugo's city is Paris."],
     "clarify", None, "sorry-prefix + possessive: one-word-name clarify"),
    # FakeEars possessive path (one-word names only)
    ("P14", "fake", ["Hugo's city is Oslo."],
     "teach", ("Hugo", "city", "Oslo"), "plain period (old: clean)"),
    ("P15", "fake", ["Hugo's city is Trondheim!"],
     "teach", ("Hugo", "city", "Trondheim"), "bang (old: LEAK)"),
    ("P16", "fake", ["Hugo's city is Bergen?"],
     "clarify", None, "question mark refused by old screen"),
    ("P17", "fake", ["Hugo's city is Bern"],
     "teach", ("Hugo", "city", "Bern"), "no-punct control"),
    # explicit-dot bench73 pattern control
    ("P18", "bench73", ["Elowen Frostmere is the apprentice of Orson Vell."],
     "teach", ("Elowen Frostmere", "apprentice_of", "Orson Vell"),
     "explicit-dot pattern control"),
    # spouse path
    ("P19", "bench73", ["Otto Vane is married to Zelda Quill."],
     "teach", ("Otto Vane", "spouse", "Zelda Quill"), "final period"),
    ("P20", "bench73", ["Otto Vane is married to Zelda Quill!"],
     "teach", ("Otto Vane", "spouse", "Zelda Quill"), "bang"),
    # exp-92 extra patterns (129b teaches; 129a clarifies, 0 writes)
    ("P21", "extra", ["Bram Stoker is employed by Westfield Press."],
     "teach-or-clarify", ("Bram Stoker", "employer", "Westfield Press"),
     "employer + period"),
    ("P22", "extra", ["Bram Stoker works in the field of Letters."],
     "teach-or-clarify", ("Bram Stoker", "occupation", "Letters"),
     "occupation + period"),
    ("P23", "extra", ["Clara's child is Milo Ray."],
     "teach", ("Clara", "child", "Milo Ray"),
     "possessive-child parses via shared FakeEars path: teach on both"),
    # more bench73 patterns
    ("P24", "bench73", ["Ovid Marlowe was born in the city of Sulmona."],
     "teach", ("Ovid Marlowe", "place_of_birth", "Sulmona"), "final period"),
    ("P25", "bench73", ["Vincent Auriol worked in the city of Lyon."],
     "teach", ("Vincent Auriol", "work_location", "Lyon"), "final period"),
    ("P26", "bench73", ["Highway Nine was performed by Bob Dylan."],
     "teach", ("Highway Nine", "performer", "Bob Dylan"), "final period"),
    ("P27", "bench73", ["The type of music that Felix Harmon plays is jazz!"],
     "teach", ("Felix Harmon", "genre", "jazz"), "bang"),
    ("P28", "bench73", ["India is located in the continent of Asia?"],
     "clarify", None, "question mark refused by old screen"),
    ("P29", "bench73",
     ["Johann Bach is affiliated with the religion of Lutheranism."],
     "teach", ("Johann Bach", "religion_or_worldview", "Lutheranism"),
     "final period"),
    ("P30", "bench73", ["Judah Halevi died in the city of Hebron!"],
     "teach", ("Judah Halevi", "place_of_death", "Hebron"), "bang"),
    # abbreviation names: trailing period must be KEPT
    ("P31", "abbrev", ["The capital of Freedonia is Washington, D.C."],
     "teach", ("Freedonia", "capital", "Washington, D.C."), "D.C. kept"),
    ("P32", "abbrev", ["Nina Petrova is a citizen of the U.S.S.R."],
     "teach", ("Nina Petrova", CIT, "the U.S.S.R."), "U.S.S.R. kept"),
    ("P33", "abbrev", ["Otis Redding is a citizen of the U.K.."],
     "teach", ("Otis Redding", CIT, "the U.K."), "double period -> one"),
    ("P34", "abbrev", ["June Carter was born in the city of St. Louis."],
     "teach", ("June Carter", "place_of_birth", "St. Louis"), "St. kept"),
    ("P35", "abbrev", ["May Carter was born in the city of St. Paul!"],
     "teach", ("May Carter", "place_of_birth", "St. Paul"), "bang + St."),
    ("P36", "abbrev", ["Ray Holt worked in the city of Mt. Rainier."],
     "teach", ("Ray Holt", "work_location", "Mt. Rainier"), "Mt. kept"),
    ("P37", "abbrev", ["Gus Webb worked in the city of Ft. Worth?"],
     "clarify", None, "question mark refused by old screen"),
    ("P38", "abbrev", ["Ike Turner is a citizen of the U.S.A."],
     "teach", ("Ike Turner", CIT, "the U.S.A."), "U.S.A. kept"),
    ("P39", "abbrev", ["The capital of Pacifica is St. Albans."],
     "teach", ("Pacifica", "capital", "St. Albans"), "mid-value abbrev"),
    ("P40", "abbrev", ["Zed's city is St. Louis."],
     "teach", ("Zed", "city", "St. Louis"), "possessive + abbrev"),
    # subject spans and quotes
    ("P41", "subject", ["Actually, Gus Webb. is a citizen of Chile."],
     "teach", ("Gus Webb", CIT, "Chile"), "subject trailing period"),
    ("P42", "quotes", ['Nina Simone is a citizen of "France".'],
     "teach", ("Nina Simone", CIT, "France"), "quoted value"),
    ("P43", "bench73", ["Boeing was founded by William Boeing."],
     "teach", ("Boeing", "founded_by", "William Boeing"), "final period"),
    ("P44", "bench73",
     ["The headquarters of Contoso is located in the city of Redmond."],
     "teach", ("Contoso", "headquarters_location", "Redmond"),
     "final period"),
    ("P45", "bench73", ["Lady Macbeth was created by William Shakespeare!"],
     "teach", ("Lady Macbeth", "creator", "William Shakespeare"), "bang"),
]


def dump_cases() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    blob = [{"id": c[0], "path": c[1], "turns": c[2], "expect": c[3],
             "expect_triple": c[4], "note": c[5]} for c in CASES]
    CASES_PATH.write_text(json.dumps(blob, indent=1, ensure_ascii=False)
                          + "\n", encoding="utf-8")


def triples_of(loop) -> set[tuple]:
    return set(L90.notebook_triples(loop.nb))


def run_arm(arm: str, factory) -> dict:
    blob = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    scratch = ART / f"f1-tmp-{arm}"
    rows = []
    n_fail = 0
    for case in blob:
        root = scratch / case["id"]
        if root.exists():
            import shutil
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        daemon = factory(root)
        nb = daemon.loop.nb
        rec = {"id": case["id"], "turns": [], "added": []}
        for i, text in enumerate(case["turns"]):
            before = triples_of(daemon.loop)
            fname = f"t{i:02d}.txt"
            (root / "inbox" / fname).write_text(text, encoding="utf-8")
            daemon.process_file(root / "inbox" / fname)
            reply = (root / "outbox" / fname).read_text(
                encoding="utf-8").strip()
            added = sorted(triples_of(daemon.loop) - before)
            rec["turns"].append({"text": text, "reply": reply[:160],
                                 "added": added})
            rec["added"].extend(added)
        # judge
        fails: list[str] = []
        kind = case["expect"]
        eff = kind
        if kind == "teach-or-clarify":
            eff = "teach" if arm == "loop129b" else "clarify"
        if eff in ("teach", "teach2"):
            want = case["expect_triple"]
            want = [tuple(want)] if isinstance(want[0], str) else [
                tuple(w) for w in want]
            got = [tuple(a) for a in rec["added"]]
            if sorted(got) != sorted(want):
                fails.append(f"added {got} != expected {want}")
        else:
            if rec["added"]:
                fails.append(f"clarify-case wrote {rec['added']}")
        for (s, r, o) in rec["added"]:
            for span, tag in ((s, "subject"), (o, "value")):
                # Failure = span still carries STRIPPABLE sentence
                # punctuation. Abbreviation-licensed trailing periods
                # (strip is a fixpoint, e.g. "Washington, D.C.") pass.
                if span and P129.strip_sentence_punct(span) != span:
                    fails.append(f"stored {tag} keeps punct: {span!r}")
        rec["verdict"] = "FAIL" if fails else "OK"
        rec["reasons"] = fails
        rows.append(rec)
        n_fail += (1 if fails else 0)
        print(f"F1 {arm} {case['id']}: {rec['verdict']}"
              + (f" {fails}" if fails else ""), flush=True)
    rep = {"mark": "F1", "arm": arm, "n": len(rows), "failures": n_fail,
           "pass": n_fail == 0, "rows": rows}
    return rep


def main() -> int:
    dump_cases()
    t0 = time.time()
    reps = {}
    for arm, factory in (("loop129a", C129.new_daemon129a),
                         ("loop129b", C129.new_daemon129b)):
        reps[arm] = run_arm(arm, factory)
    (REPORT_A).write_text(json.dumps(reps["loop129a"], indent=1,
                                     ensure_ascii=False), encoding="utf-8")
    (REPORT_B).write_text(json.dumps(reps["loop129b"], indent=1,
                                     ensure_ascii=False), encoding="utf-8")
    secs = round(time.time() - t0, 1)
    ok = reps["loop129a"]["pass"] and reps["loop129b"]["pass"]
    print(f"F1: 129a failures={reps['loop129a']['failures']} "
          f"129b failures={reps['loop129b']['failures']} "
          f"-> {'PASS' if ok else 'FAIL'} ({secs} s)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
