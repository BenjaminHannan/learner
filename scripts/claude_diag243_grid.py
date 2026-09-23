"""Exp 243 (diagnosis only): boundary grid for "declines while the answer
is stored" on 138i (+ the 228 src guard, via scripts/claude_loop228_agent.py).

Factors: family (star = extra facts on the subject; chain = extra facts
hang off the subject's object; me = the user as subject) x stored facts
(1/2/3/5) x taught-name case (title/lower) x asked-name case
(title/lower/upper) x name kind (one-word/two-word) x question form
(incl. apostrophe / no apostrophe / "whats"). Every question in a dialog
is asked after all facts are taught; asks are read-only.

A cell counts toward the decline tally only when the needed triple is
really in the notebook (checked from STORED triples, case-insensitive).

Usage: python -B scripts/claude_diag243_grid.py <workdir> <out.jsonl> [--workers N]
"""
from __future__ import annotations

import json
import shutil
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, "scripts")

CFG = "artifacts/fable-agent138i-20260922/loop138i-config.json"
DECLINE_MARKS = ("I do not know that from what you taught me",
                 "didn't understand", "say it another way",
                 "I don't know anyone called")


def star_facts(X):  # all on X; order fixed, spouse first
    return [(f"{X} is married to Sella Marne", ("spouse", "Sella Marne")),
            (f"{X}'s city is Selwick.", ("city", "Selwick")),
            (f"{X}'s boss is Ottoline.", ("boss", "Ottoline")),
            (f"{X}'s friend is Tamsin.", ("friend", "Tamsin")),
            (f"{X}'s pet is Button.", ("pet", "Button"))]


def chain_facts(X):  # X has ONE relation; the chain continues past it
    return [(f"{X} is married to Sella Marne", ("spouse", "Sella Marne")),
            ("Sella Marne's boss is Ottoline.", None),
            ("Ottoline's friend is Tamsin.", None),
            ("Tamsin's boss is Garrow.", None),
            ("Garrow's city is Quellport.", None)]


def forms(A):
    """Question forms for asked-name surface A -> (form_id, text, rel)."""
    return [
        ("married_to", f"Who is {A} married to?", "spouse"),
        ("spouse_apos", f"Who is {A}'s spouse?", "spouse"),
        ("spouse_noapos", f"Who is {A}s spouse?", "spouse"),
        ("where_live", f"Where does {A} live?", "city"),
        ("city_apos", f"What is {A}'s city?", "city"),
        ("city_noapos", f"What is {A}s city?", "city"),
        ("whats_city_apos", f"whats {A}'s city?", "city"),
        ("whats_city_noapos", f"whats {A}s city?", "city"),
        ("whatq_city_apos", f"What's {A}'s city?", "city"),
        ("boss_apos", f"Who is {A}'s boss?", "boss"),
        ("boss_noapos", f"Who is {A}s boss?", "boss"),
        ("whats_boss_noapos", f"whats {A}s boss?", "boss"),
    ]


ME_FACTS = [("My city is Harlow Cross.", ("city", "Harlow Cross")),
            ("My boss is Ottoline.", ("boss", "Ottoline")),
            ("My spouse is Sella Marne.", ("spouse", "Sella Marne")),
            ("My friend is Tamsin.", ("friend", "Tamsin")),
            ("My pet is Button.", ("pet", "Button"))]
ME_FORMS = [("me_where_live", "Where do I live?", "city"),
            ("me_where_live_lower", "where do i live?", "city"),
            ("me_where_live_upper", "WHERE DO I LIVE?", "city"),
            ("me_city", "What is my city?", "city"),
            ("me_whats_city", "whats my city?", "city"),
            ("me_whatq_city", "What's my city?", "city"),
            ("me_boss", "Who is my boss?", "boss"),
            ("me_married_to", "Who am I married to?", "spouse"),
            ("me_spouse", "Who is my spouse?", "spouse"),
            ("me_live_where", "Where is my city?", "city")]


def case(name, how):
    return {"title": name, "lower": name.lower(), "upper": name.upper()}[how]


def build_cells():
    cells = []
    for fam in ("star", "chain"):
        for n in (1, 2, 3, 5):
            for kind, base in (("one", "Brannick"), ("two", "Joren Hale")):
                for tcase in ("title", "lower"):
                    X = case(base, tcase)
                    facts = (star_facts if fam == "star" else chain_facts)(X)[:n]
                    qs = []
                    for acase in ("title", "lower", "upper"):
                        A = case(base, acase)
                        for fid, q, rel in forms(A):
                            qs.append({"form": fid, "ask_case": acase,
                                       "q": q, "rel": rel})
                    cells.append({"family": fam, "n": n, "name_kind": kind,
                                  "teach_case": tcase, "subject": base,
                                  "facts": facts, "questions": qs})
    for n in (1, 2, 3, 5):
        cells.append({"family": "me", "n": n, "name_kind": "me",
                      "teach_case": "-", "subject": "USER",
                      "facts": ME_FACTS[:n],
                      "questions": [{"form": f, "ask_case": "-", "q": q,
                                     "rel": r} for f, q, r in ME_FORMS]})
    return cells


def run_cell(args):
    idx, cell, work = args
    import claude_loop228_agent as A228  # installs the 228 guard
    import fable_marks123_all as M
    import fable_loop90_agent as L90
    A228.install_srcguard228()
    base = M.load_base_cfg(CFG)
    root = Path(work) / f"c{idx:03d}"
    shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
    d = M.make_daemon(A228.Loop228Daemon, base, root)
    k = 0
    teach_replies = []

    def send(t):
        nonlocal k
        f = root / "inbox" / f"m{k:03d}.txt"; f.write_text(t)
        d.process_file(f)
        rep = (root / "outbox" / f"m{k:03d}.txt").read_text().strip()
        k += 1
        return rep
    for sent, _ in cell["facts"]:
        teach_replies.append(send(sent))
    stored = [tuple(x) for x in L90.notebook_triples(d.loop.nb)]
    subj = cell["subject"].lower()
    rows = []
    for q in cell["questions"]:
        want = [o for (s, r, o) in stored
                if s.lower() == subj and r == q["rel"]]
        rep = send(q["q"])
        is_stored = bool(want)
        correct = is_stored and any(w.lower() in rep.lower() for w in want)
        decline = any(m in rep for m in DECLINE_MARKS)
        outcome = ("correct" if correct else "decline" if decline
                   else "other")
        rows.append(dict(
            {kk: cell[kk] for kk in ("family", "n", "name_kind",
                                     "teach_case")},
            form=q["form"], ask_case=q["ask_case"], question=q["q"],
            relation=q["rel"], answer_stored=is_stored, stored_values=want,
            reply=rep, outcome=outcome,
            bad_decline=bool(is_stored and outcome == "decline"),
            bad_other=bool(is_stored and outcome == "other")))
    return {"idx": idx, "teach_replies": teach_replies, "stored": stored,
            "rows": rows}


def main():
    work, out = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) \
        if "--workers" in sys.argv else 1
    cells = build_cells()
    jobs = [(i, c, work) for i, c in enumerate(cells)]
    with Pool(workers) as p:
        res = p.map(run_cell, jobs, chunksize=1)
    with open(out, "w") as fh:
        for r in res:
            for row in r["rows"]:
                row["cell"] = r["idx"]
                fh.write(json.dumps(row) + "\n")
    meta = Path(out).with_suffix(".cells.json")
    meta.write_text(json.dumps([{"idx": r["idx"],
                                 "facts": [f for f, _ in cells[r["idx"]]["facts"]],
                                 "teach_replies": r["teach_replies"],
                                 "stored": r["stored"]} for r in res],
                               indent=1))
    n = sum(len(r["rows"]) for r in res)
    st = sum(row["answer_stored"] for r in res for row in r["rows"])
    bd = sum(row["bad_decline"] for r in res for row in r["rows"])
    bo = sum(row["bad_other"] for r in res for row in r["rows"])
    print(f"cells={len(cells)} questions={n} answer_stored={st} "
          f"declined_while_stored={bd} other_wrong_while_stored={bo}")


if __name__ == "__main__":
    main()
