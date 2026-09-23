#!/usr/bin/env python3
"""Exp 224a RE-SCORER: re-score STORED suite rows with each frozen scorer's
own abstain/decline check replaced by fable_decline224.is_decline.

No agent is run. For every stored row it computes two verdicts on the SAME
row: FROZEN (the scorer's own check, recomputed) and DECLINE (the same
scorer with only its abstain/clarify check swapped for is_decline, by
monkeypatching the frozen module attribute in this process or, where the
check is inline in a runner, by a verbatim copy of the verdict block with
only the check swapped). A row "changes" when FROZEN != DECLINE. The
FROZEN recompute is also compared to the verdict stored in the row
(sanity: the re-scorer reproduces the frozen scorer).

Suites (row sources are found by filename under --rows-dir, so a sealed
base folder OR a fable_suitediff.py --out folder both work):
  rt136       fable_fix139b_redteam136 verdict (stored triples only; it has
              no reply check, so no change is possible by construction)
  rt143       fable_redteam143_run.run_case verdict block (abstain markers)
  sessions152 fable_session152_run.judge with is_clarify -> is_decline
  bench       fable_bench121_run.classify_v2 with _ABSTAIN_RES -> is_decline
              (4 splits: new_121_4hop, old_s2fresh_4hop, bench132_4hop,
              edit200); golds read from the frozen data files
  marks123    stored fable_marks123_all.py rows: bench (fable_bench113_run
              classify_v2 patched the same way), rt81 (its "must" strings are
              content checks, NOT swapped; recomputed for sanity only),
              rt110 (fable_redteam110_runner.judge with is_abstain ->
              is_decline; INFORMATIONAL: rt110 is outside the suitediff
              marks123 subset p4/q1/bench/rt81 and outside the 224a bar).
              p2/p3/p4/q1/soak have no abstain check: listed, not
              re-scored.

Never edits any file but --out. Run:
  python3 -B scripts/fable_rescore224.py --rows-dir artifacts/fable-agent138i-20260922 \
      --out artifacts/fable-decline224-20260922/a1-138i.json
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent

import fable_decline224 as D  # noqa: E402

BENCH_DATA = {
    "new_121_4hop": ROOT / "data" / "open" / "bench121"
    / "fable_edit121_4hop.jsonl",
    "old_s2fresh_4hop": None,  # resolved from fable_bench121_run.DATA_OLD
    "bench132_4hop": ROOT / "data" / "open" / "bench132"
    / "fable_edit132_4hop.jsonl",
    "edit200": ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl",
}
BENCH_FRAGS = {
    "new_121_4hop": ("new_121_4hop",),
    "old_s2fresh_4hop": ("s2fresh_4hop",),
    "bench132_4hop": ("bench132_4hop",),
    "edit200": ("edit200",),
}
RT81_GENERIC_MUSTS = ("another way", "don't know", "didn't catch")


# ------------------------------------------------------------------ helpers
def load_any(path: Path):
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except ValueError:
        return [json.loads(x) for x in text.splitlines() if x.strip()]


def unwrap(obj) -> list:
    if isinstance(obj, list):
        return obj
    for k in ("rows", "cases"):
        if isinstance(obj.get(k), list):
            return obj[k]
    raise ValueError("cannot unwrap rows")


EXCLUDE: list[str] = ["marks"]


def find(rows_dir: Path, frags: tuple[str, ...], exclude=None):
    exclude = EXCLUDE if exclude is None else exclude
    for p in sorted(rows_dir.rglob("*.json*")):
        s = str(p.relative_to(rows_dir))
        if "scratch" in s or "-tmp" in s or "work-" in s:
            continue
        if any(e in s for e in exclude):
            continue
        if all(f in p.name for f in frags):
            return p
    return None


def find_marks_dir(rows_dir: Path):
    for p in sorted(rows_dir.rglob("rt81-report.json")):
        return p.parent
    return None


class _DeclineRe:
    """Stands in for one compiled abstain regex: .search(low) -> is_decline."""

    def search(self, low):
        return is_decline_or_none(low)


def is_decline_or_none(low):
    return True if D.is_decline(low) else None


@contextlib.contextmanager
def patched(mod, name, value):
    old = getattr(mod, name)
    setattr(mod, name, value)
    try:
        yield
    finally:
        setattr(mod, name, old)


def summarize(suite: str, recs: list[dict], src) -> dict:
    changes = [r for r in recs if r["frozen"] != r["decline"]]
    insane = [r for r in recs if r.get("stored") is not None
              and r["stored"] != r["frozen"] and not r.get("fs_dependent")]
    return {"suite": suite, "source": str(src), "n": len(recs),
            "changes": len(changes), "change_rows": changes,
            "frozen_counts": dict(Counter(r["frozen"] for r in recs)),
            "decline_counts": dict(Counter(r["decline"] for r in recs)),
            "sanity_mismatch": len(insane),
            "sanity_rows": insane[:20]}


# ------------------------------------------------------------------ suites
def rt136(rows_dir: Path) -> dict:
    p = find(rows_dir, ("136",)) or find(rows_dir, ("rt136",))
    recs = []
    for r in unwrap(load_any(p)):
        stored = r.get("stored") or []
        exp = r["expect"]
        if r.get("verdict") == "HARNESS-ERROR":
            v = "HARNESS-ERROR"
        elif exp == "nowrite":
            v = "OK" if not stored else "WRONG-WRITE"
        else:
            v = ("OK" if stored == [list(exp)] else
                 "MISSED" if not stored else "WRONG-WRITE")
        recs.append({"id": r["id"], "stored": r.get("verdict"), "frozen": v,
                     "decline": v, "reply": str(r.get("reply", ""))[:160]})
    return summarize("rt136", recs, p)


def _rt143_verdict(rec: dict, abst: bool, R143) -> str:
    # verbatim verdict block of fable_redteam143_run.run_case (lines
    # 108-132), with only `abst` supplied by the caller.
    if rec.get("verdict") == "HARNESS-ERROR":
        return "HARNESS-ERROR"
    reply = rec["reply"]
    exp = rec["expected"]
    extracted = R143.extract_answer(reply)
    if exp == "abstain":
        return "OK" if abst else "WRONG-ANSWER"
    if R143.norm(extracted) == R143.norm(exp) and R143.norm(exp):
        return "OK"
    return "MISSED" if abst else "WRONG-ANSWER"


def rt143(rows_dir: Path) -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (read-only)
    markers = json.loads(R143.CASES_PATH.read_text(
        encoding="utf-8"))["abstain_markers"]
    p = find(rows_dir, ("143",))
    recs = []
    for r in unwrap(load_any(p)):
        low = str(r.get("reply", "")).lower()
        vf = _rt143_verdict(r, any(m.lower() in low for m in markers), R143)
        vd = _rt143_verdict(r, D.is_decline(r.get("reply", "")), R143)
        recs.append({"id": r["id"], "stored": r.get("verdict"), "frozen": vf,
                     "decline": vd, "reply": str(r.get("reply", ""))[:160]})
    return summarize("rt143", recs, p)


def sessions152(rows_dir: Path) -> dict:
    import fable_session152_run as S  # noqa: E402 (judge, read-only)
    p = find(rows_dir, ("sessions152",))
    obj = load_any(p)
    recs = []
    for sid, turns in obj.items():
        for t in turns:
            vf = S.judge(t)["verdict"]
            with patched(S, "is_clarify", D.is_decline):
                vd = S.judge(t)["verdict"]
            recs.append({"id": f"{sid}#{t['n']}", "stored": t.get("verdict"),
                         "frozen": vf, "decline": vd,
                         "text": str(t.get("text", ""))[:80],
                         "expect": t.get("expect"),
                         "reply": str(t.get("reply", ""))[:160]})
    return summarize("sessions152", recs, p)


def _bench_golds(split: str, B) -> dict:
    path = BENCH_DATA[split] or Path(str(B.DATA_OLD))
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            it = json.loads(line)
            out[it["id"]] = [str(g) for g in list(it.get("gold", []))
                             + list(it.get("gold_aliases", []))]
    return out


def _classify_both(B, reply: str, golds: list[str]) -> tuple[str, str]:
    vf = B.classify_v2(reply, golds)[0]
    with patched(B, "_ABSTAIN_RES", [_DeclineRe()]):
        vd = B.classify_v2(reply, golds)[0]
    return vf, vd


def bench(rows_dir: Path) -> list[dict]:
    import fable_bench121_run as B  # noqa: E402 (scorer v2, read-only)
    reps = []
    for split, frags in BENCH_FRAGS.items():
        p = find(rows_dir, frags)
        if p is None:
            reps.append({"suite": f"bench:{split}", "missing": True, "n": 0,
                         "changes": 0, "sanity_mismatch": 0})
            continue
        golds = _bench_golds(split, B)
        recs = []
        for r in unwrap(load_any(p)):
            vf, vd = _classify_both(B, r["reply"], golds[r["id"]])
            recs.append({"id": r["id"], "stored": r.get("verdict"),
                         "frozen": vf, "decline": vd,
                         "reply": str(r["reply"])[:160]})
        reps.append(summarize(f"bench:{split}", recs, p))
    return reps


def marks123(rows_dir: Path) -> list[dict]:
    mdir = find_marks_dir(rows_dir)
    if mdir is None:
        return [{"suite": "marks123", "missing": True, "n": 0, "changes": 0,
                 "sanity_mismatch": 0}]
    reps = []
    import fable_bench113_run as B113  # noqa: E402 (scorer v2, read-only)
    for p in sorted(mdir.glob("bench-rows-*.jsonl")):
        recs = []
        for r in unwrap(load_any(p)):
            vf, vd = _classify_both(B113, r["reply"], r["golds"])
            recs.append({"id": r["id"], "stored": r.get("verdict"),
                         "frozen": vf, "decline": vd,
                         "reply": str(r["reply"])[:160]})
        reps.append(summarize(f"marks123:{p.stem}", recs, p))
    # rt81: must-check on the generic decline strings
    import fable_redteam81_probe as P81  # noqa: E402 (sealed steps)
    steps = {}
    for seq_id, _d, sts in P81.SEQS:
        for i, st in enumerate(sts):
            steps[f"{seq_id}-{i + 1:02d}"] = st
    p = mdir / "rt81-report.json"
    if p.exists():
        recs = []
        for c in load_any(p)["cases"]:
            st = steps.get(c["id"], {})
            m = re.match(r"reply=(\".*?\"|'.*?') taught_delta",
                         str(c.get("observed", "")), re.S)
            stored = c.get("verdict")
            if not m or not st.get("must"):
                recs.append({"id": c["id"], "stored": stored,
                             "frozen": stored, "decline": stored,
                             "note": "no must-check"})
                continue
            reply = ast.literal_eval(m.group(1))
            must = st["must"]
            pre = "CRASH=" in c["observed"] or (
                st.get("nowrite") and c.get("facts_delta", 0) > 0)
            if pre:
                vf = vd = stored
            else:
                # rt81 "must" is a content check, not an abstain check: it
                # is NOT swapped (the 224b sentences carry "another way" /
                # "don't know" themselves). Pilot: swapping it moved 3 rows.
                f_fail = must not in reply
                d_fail = f_fail
                # verdict after a passed must-check is the stored one when
                # the stored one came from a later branch; else OK.
                later = stored if stored != "UNCLEAR" else "OK"
                vf = "UNCLEAR" if f_fail else later
                vd = "UNCLEAR" if d_fail else later
            recs.append({"id": c["id"], "stored": stored, "frozen": vf,
                         "decline": vd, "must": must,
                         "reply": reply[:160]})
        reps.append(summarize("marks123:rt81", recs, p))
    # rt110: judge with is_abstain patched (filesystem checks unchanged)
    p = mdir / "rt110-report.json"
    if p.exists():
        import fable_redteam110_runner as R110  # noqa: E402 (judge)
        cases = {c["id"]: c for c in R110.RC.CASES} if hasattr(
            R110.RC, "CASES") else {}
        recs = []
        for r in load_any(p)["rows"]:
            case = cases.get(r["id"])
            if case is None:
                continue
            res = {"log": r["log"], "harness_error": r.get("harness_error"),
                   "root": str(mdir / "rt110-tmp" / "__missing__"),
                   "info": {}}
            exp = case.get("expect", {})
            fs = bool(exp.get("vanished") or exp.get("all_done"))
            vf = R110.judge(case, res)["verdict"]
            with patched(R110, "is_abstain", D.is_decline):
                vd = R110.judge(case, res)["verdict"]
            recs.append({"id": r["id"], "stored": r.get("agent_verdict"),
                         "frozen": vf, "decline": vd, "fs_dependent": fs})
        rep = summarize("marks123:rt110", recs, p)
        rep["informational"] = True
        reps.append(rep)
    reps.append({"suite": "marks123:p2/p3/p4/q1/soak", "n": 0, "changes": 0,
                 "sanity_mismatch": 0,
                 "note": "no abstain/decline check in these suites"})
    return reps


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--exclude", default="",
                    help="comma list of extra path fragments to skip "
                    "(e.g. g1bench-h in the 138i folder, which holds 138h rows)")
    args = ap.parse_args(argv)
    EXCLUDE.extend(x for x in args.exclude.split(",") if x)
    rows_dir = Path(args.rows_dir)
    reps = [rt136(rows_dir), rt143(rows_dir), sessions152(rows_dir)]
    reps += bench(rows_dir)
    reps += marks123(rows_dir)
    total = sum(r.get("changes", 0) for r in reps
                if not r.get("informational"))
    out = {"rows_dir": str(rows_dir), "total_changes": total,
           "suites": reps}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    for r in reps:
        print(f"{r['suite']:28s} n={r.get('n', 0):4d} "
              f"changes={r.get('changes', 0)} "
              f"sanity_mismatch={r.get('sanity_mismatch', 0)}"
              f"{' (informational, outside bar)' if r.get('informational') else ''}"
              f"{' MISSING' if r.get('missing') else ''}")
    print(f"TOTAL verdict changes: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
