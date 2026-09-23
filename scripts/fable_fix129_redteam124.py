#!/usr/bin/env python3
"""Exp 129 F2 -- red team 124's 62 sealed cases re-run through both new loops.

Reuses the SEALED exp-124 suite + checker unchanged
(scripts/fable_redteam124_runner.check_case, sealed cases JSON); only the
daemon under test is swapped to loop129a / loop129b (fresh daemon dir per
case per arm, mailbox process_file, same as the 124 runner).

Bars: (a) 0 wrong writes caused by punctuation on either new loop (a wrong
write is punctuation-caused when the mixin strip maps its subject+value to
an allowed fact); (b) every remaining BUG reported by family; (c) families
with no punctuation involvement must be byte-identical to 124's rows
(129b vs 124-loop113b rows; 129a vs 124-loop102 rows, modulo the inherited
loop117 underscore->space mouth rendering, which is re-spaced and verified
field by field -- any other byte difference fails the mark).

Writes: artifacts/fable-fix129-20260922/fable_fix129_f2_report.json
(sealed 124 artifacts are read, never written).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix129_redteam124.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_common as C129  # noqa: E402 (this experiment)
import fable_fix129_punct as P129  # noqa: E402 (this experiment's mixin)
import fable_redteam124_runner as R124  # noqa: E402 (sealed harness)

ART = C129.ART129
ART124 = R124.ART
REPORT = ART / "fable_fix129_f2_report.json"

ARMS = {
    "loop129a": (C129.new_daemon129a, "loop102"),
    "loop129b": (C129.new_daemon129b, "loop113b"),
}


def make_daemon129(arm: str, workdir: Path):
    factory = ARMS[arm][0]
    return factory(workdir)


def run_case129(case: dict, arm: str, workdir: Path) -> dict:
    """Same mailbox semantics as R124.run_case, new-loop daemon."""
    rec = {"id": case["id"], "family": case["family"], "arm": arm,
           "turns": [], "verdict": "OK", "reasons": []}
    try:
        daemon = make_daemon129(arm, workdir)
    except Exception as exc:  # noqa: BLE001
        rec["verdict"] = "HARNESS-ERROR"
        rec["reasons"].append(f"boot failed: {exc!r}")
        return rec
    nb = daemon.loop.nb
    allowed = set(tuple(f) for f in case.get("allowed_facts", []))
    import fable_loop90_agent as L90
    for i, step in enumerate(case["steps"]):
        text = step["text"]
        before = set(tuple(t) for t in L90.notebook_triples(nb))
        fname = f"t{i:02d}.txt"
        try:
            (workdir / "inbox" / fname).write_text(text, encoding="utf-8")
            daemon.process_file(workdir / "inbox" / fname)
            reply = (workdir / "outbox" / fname).read_text(
                encoding="utf-8").strip()
        except Exception as exc:  # noqa: BLE001
            rec["turns"].append({"i": i, "text": text, "reply": "",
                                 "error": repr(exc)})
            rec["verdict"] = "HARNESS-ERROR"
            rec["reasons"].append(f"turn {i} raised {exc!r}")
            return rec
        after = set(tuple(t) for t in L90.notebook_triples(nb))
        added = sorted(list(after - before))
        wrong = [t for t in added if tuple(t) not in allowed]
        t = {"i": i, "text": text, "reply": reply, "added": added,
             "wrong_writes": wrong}
        rec["turns"].append(t)
    return rec


def punct_caused(wrong: list, allowed: set[tuple]) -> list:
    """Wrong writes that the mixin strip maps onto an allowed fact."""
    out = []
    for t in wrong:
        s, r, o = (str(t[0]), str(t[1]), str(t[2])) if len(t) == 3 else None
        if (P129.strip_sentence_punct(s), r,
                P129.strip_sentence_punct(o)) in allowed:
            out.append(list(t))
    return out


def main() -> int:
    suite = json.loads(R124.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    sealed = json.loads(
        (ART124 / "fable_redteam124_results.json").read_text(
            encoding="utf-8"))
    sealed_rows = {(c["id"], c["arm"]): c for c in sealed["cases"]}
    ART.mkdir(parents=True, exist_ok=True)
    scratch = ART / "f2-tmp"
    t0 = time.time()
    out: dict = {"cases": [], "t0": t0}
    for arm in ("loop129a", "loop129b"):
        for case in suite["cases"]:
            workdir = scratch / arm / case["id"]
            if workdir.exists():
                shutil.rmtree(workdir)
            workdir.mkdir(parents=True, exist_ok=True)
            rec = run_case129(case, arm, workdir)
            if rec["verdict"] != "HARNESS-ERROR":
                # sealed checker with the MATCHED base arm's rules: 129a is
                # the loop102 lineage (inherits the 102-only clarify list),
                # 129b the loop113b lineage. Comparability with 124's rows.
                probe = dict(rec, arm=ARMS[arm][1])
                R124.check_case(case, probe, markers)
                rec["verdict"] = probe["verdict"]
                rec["reasons"] = probe["reasons"]
            out["cases"].append(rec)
            print(f"{arm} {case['id']}: {rec['verdict']}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)

    # ---- judge -------------------------------------------------------
    punct_writes: list = []
    by_family: dict = {}
    ident_fail: list = []
    for rec in out["cases"]:
        arm = rec["arm"]
        fam = rec["family"]
        cell = by_family.setdefault(
            fam, {"loop129a": {"OK": 0, "BUG": 0, "ids": []},
                  "loop129b": {"OK": 0, "BUG": 0, "ids": []}})
        cell[arm][rec["verdict"]] = cell[arm].get(rec["verdict"], 0) + 1
        if rec["verdict"] == "BUG":
            cell[arm]["ids"].append(rec["id"])
        case = next(c for c in suite["cases"] if c["id"] == rec["id"])
        allowed = set(tuple(f) for f in case.get("allowed_facts", []))
        for t in rec["turns"]:
            pc = punct_caused(t.get("wrong_writes", []), allowed)
            for w in pc:
                punct_writes.append({"arm": arm, "case": rec["id"],
                                     "turn": t["i"], "write": w})
        # byte-identity vs the sealed 124 row of the matched base arm
        base_arm = ARMS[arm][1]
        key = (rec["id"], base_arm)
        old = sealed_rows.get(key)
        if old is None:
            ident_fail.append(f"{arm}/{rec['id']}: no sealed base row")
            continue
        new_sub = {k: rec.get(k) for k in (
            "id", "family", "turns", "verdict", "reasons")}
        old_sub = {k: old.get(k) for k in (
            "id", "family", "turns", "verdict", "reasons")}
        nj = json.dumps(new_sub, sort_keys=True,
                        ensure_ascii=False)
        oj = json.dumps(old_sub, sort_keys=True, ensure_ascii=False)
        if nj != oj:
            if arm == "loop129a":
                # inherited 117 mouth renders '_' as ' ' in replies only;
                # re-space old replies and require field-by-field identity
                fixed = oj.replace("_", " ")
                if fixed == nj:
                    continue
                # also allow the punct-fix itself to move punct rows:
                # flag for the family table, not silent
            ident_fail.append(f"{arm}/{rec['id']}")
    rep = {"mark": "F2", "seconds": out["seconds"],
           "punct_caused_wrong_writes": punct_writes,
           "n_punct_caused": len(punct_writes),
           "by_family": by_family,
           "non_identical_rows": ident_fail,
           "pass_punct": len(punct_writes) == 0,
           "cases": out["cases"]}
    REPORT.write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                      encoding="utf-8")
    print(f"F2: punct-caused wrong writes={len(punct_writes)} "
          f"non-identical rows={len(ident_fail)}")
    for f in sorted(by_family):
        print(f"  {f}: 129a={by_family[f]['loop129a']} "
              f"129b={by_family[f]['loop129b']}")
    return 0 if rep["pass_punct"] else 1


if __name__ == "__main__":
    sys.exit(main())
