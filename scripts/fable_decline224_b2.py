#!/usr/bin/env python3
"""Exp 224b mark B2 checker: loop224 suite rows vs stored loop138i rows.

Inputs: a fable_suitediff.py --out folder for loop224 (--new), the sealed
138i base folder, the fable_rescore224.py report on the --new folder
(--rescore; run with --exclude diff), and the sealed 224a A1 report on the
138i folder (--a1).

What it checks, on EVERY row of every barred suite (not only suitediff's
listed moves): it walks the base row and the new row in parallel and
collects every differing leaf (keys named "seconds" ignored).
  verdict move  : a differing leaf whose key is "verdict"
  glue move     : a differing string leaf where the new text equals the base
                  text with each occurrence of the 138i glue replaced by one
                  of the three 224 sentences (regex full match, >= 1 swap)
  other move    : anything else (must be 0)
Type check for each glue swap, against the input that produced that reply:
  row reply / extracted / observed -> the row's own input (rt136 text,
  rt143 case question, sessions turn text, bench question from the frozen
  data file, rt81 turn); teach_replies[i] / yes_replies[i] -> a teach /
  confirm turn (statement side).  Expected kind: Q2 when the input is
  question-shaped (ends with "?" or the exp-151 predicate fires), else S1.
Decline scoring: verdicts scored with is_decline equal the frozen verdicts
on both sides (A1 on the 138i rows; --rescore on the 224 rows, 0 changes
and 0 sanity mismatches), so is_decline verdict moves == stored verdict
moves counted here.

  python3 -B scripts/fable_decline224_b2.py --new <dir> --rescore <json> \\
      --a1 artifacts/fable-decline224-20260922/224a/a1-138i.json --out <json>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent
import fable_decline224 as DEC  # noqa: E402
import fable_qmark151_core as Q151  # noqa: E402
import fable_rescore224 as R  # noqa: E402 (loaders + bench data paths)

BASE = ROOT / "artifacts" / "fable-agent138i-20260922"
RT143_CASES = ROOT / "artifacts" / "fable-redteam143-20260922" \
    / "fable_redteam143_cases.json"
SPLITS = ["new_121_4hop", "old_s2fresh_4hop", "bench132_4hop", "edit200"]
IGNORE_KEYS = {"seconds"}
KIND_OF = {v: k for k, v in DEC.NEW_SENTENCES224.items()}
_ALT = "(" + "|".join(re.escape(s) for s in DEC.NEW_SENTENCES224.values()) + ")"


def question_shaped(text: str) -> bool:
    t = " ".join(str(text).split())
    if t.endswith("?"):
        return True
    try:
        return bool(Q151.should_rewrite_151(t))
    except Exception:  # noqa: BLE001
        return False


def glue_swap(b: str, n: str):
    if DEC.GLUE138 not in b:
        return truncated_swap(b, n)
    pat = re.escape(b).replace(re.escape(DEC.GLUE138), _ALT)
    m = re.fullmatch(pat, n, flags=re.S)
    if not m:
        return None
    return [KIND_OF[g] for g in m.groups()]


def truncated_swap(b: str, n: str):
    """Echo fields that store a truncated copy of the reply (sessions152
    "why"): base = P + a >= 40-char prefix of the glue running to the end,
    new = P + one whole 224 sentence (or its prefix of the same length)."""
    i = b.find(DEC.GLUE138[:40])
    if i < 0 or not DEC.GLUE138.startswith(b[i:]) or n[:i] != b[:i]:
        return None
    tail = n[i:]
    for kind, s in DEC.NEW_SENTENCES224.items():
        if tail == s or (s.startswith(tail) and len(tail) == len(b) - i):
            return [kind]
    return None


def walk(b, n, path, out):
    if isinstance(b, dict) and isinstance(n, dict):
        for k in sorted(set(b) | set(n)):
            if k in IGNORE_KEYS:
                continue
            if k not in b or k not in n:
                out.append((path + [k], b.get(k, "<absent>"),
                            n.get(k, "<absent>")))
            else:
                walk(b[k], n[k], path + [k], out)
    elif isinstance(b, list) and isinstance(n, list) and len(b) == len(n):
        for i, (x, y) in enumerate(zip(b, n)):
            walk(x, y, path + [i], out)
    elif b != n:
        out.append((path, b, n))


def by_id(rows) -> dict:
    return {str(r.get("id", r.get("case_id"))): r for r in rows}


def load_suites(new: Path) -> list[tuple[str, dict, dict, dict]]:
    """(suite, base rows by id, new rows by id, inputs by id)."""
    out = []
    # rt136
    b = by_id(R.unwrap(R.load_any(BASE / "g2frozen" / "redteam136-loop138i.json")))
    n = by_id(R.unwrap(R.load_any(new / "rt136-rows.json")))
    out.append(("rt136", b, n, {k: v.get("text") for k, v in b.items()}))
    # rt143
    cases = by_id(json.loads(RT143_CASES.read_text(encoding="utf-8"))["cases"])
    b = by_id(R.unwrap(R.load_any(BASE / "g2frozen" / "redteam143-loop138i.json")))
    n = by_id(R.unwrap(R.load_any(new / "rt143-rows.json")))
    out.append(("rt143", b, n, {k: cases.get(k, {}).get("question")
                                for k in b}))
    # sessions152
    def flat(d):
        return {f"{s}#{t['n']}": t for s, turns in d.items() for t in turns}
    b = flat(R.load_any(BASE / "g2frozen" / "sessions152-loop138i.json"))
    n = flat(R.load_any(new / "sessions152-rows.json"))
    out.append(("sessions152", b, n, {k: v.get("text") for k, v in b.items()}))
    # bench 4 splits
    import fable_bench121_run as B121  # noqa: E402
    for s in SPLITS:
        data = R.BENCH_DATA[s] or Path(B121.DATA_OLD)
        qs = {}
        for line in Path(data).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                qs[str(r["id"])] = r.get("question")
        b = by_id(R.unwrap(R.load_any(
            BASE / "g1bench" / f"fable_benchv3_loop138i_{s}_rows.jsonl")))
        n = by_id(R.unwrap(R.load_any(new / f"bench-{s}-rows.jsonl")))
        out.append((f"bench:{s}", b, n, {k: qs.get(k) for k in b}))
    # marks123 subset: rt81 + bench rows (+ p4 / q1 reports whole-file)
    mb, mn = BASE / "marks138i", new / "marks123"
    b = by_id(R.load_any(mb / "rt81-report.json")["cases"])
    n = by_id(R.load_any(mn / "rt81-report.json")["cases"])
    out.append(("marks123:rt81", b, n, {k: v.get("turn") for k, v in b.items()}))
    for f in ("bench-rows-fable_edit_200.jsonl", "bench-rows-s2fresh_4hop.jsonl"):
        b = by_id(R.unwrap(R.load_any(mb / f)))
        n = by_id(R.unwrap(R.load_any(mn / f)))
        out.append((f"marks123:{f}", b, n,
                    {k: v.get("question") for k, v in b.items()}))
    for f in ("p4-report.json", "q1-report.json"):
        b, n = R.load_any(mb / f), R.load_any(mn / f)
        out.append((f"marks123:{f}", {"whole": b}, {"whole": n}, {}))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True)
    ap.add_argument("--rescore", required=True)
    ap.add_argument("--a1", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    new = Path(args.new)
    rep = {"suites": [], "glue_moves": [], "verdict_moves": [],
           "other_moves": [], "type_mismatch": [], "missing_rows": []}
    for suite, b, n, inputs in load_suites(new):
        if set(b) != set(n):
            rep["missing_rows"].append({"suite": suite,
                                        "only_base": sorted(set(b) - set(n)),
                                        "only_new": sorted(set(n) - set(b))})
        moved = 0
        for rid in sorted(set(b) & set(n)):
            diffs: list = []
            walk(b[rid], n[rid], [], diffs)
            if diffs:
                moved += 1
            for path, x, y in diffs:
                tag = {"suite": suite, "id": rid,
                       "path": ".".join(map(str, path))}
                if path and path[-1] == "verdict":
                    rep["verdict_moves"].append({**tag, "base": x, "new": y})
                    continue
                kinds = glue_swap(x, y) if isinstance(x, str) and \
                    isinstance(y, str) else None
                if kinds is None:
                    rep["other_moves"].append({**tag, "base": x, "new": y})
                    continue
                if "teach_replies" in path or "yes_replies" in path:
                    inp, side = None, "teach/confirm turn"
                    want = "S1"
                else:
                    inp = inputs.get(rid)
                    side = "row input"
                    want = None if inp is None else (
                        "Q2" if question_shaped(inp) else "S1")
                rec = {**tag, "kinds": kinds, "input": inp, "input_side": side,
                       "expected": want, "new": y}
                rep["glue_moves"].append(rec)
                if want is None or any(k != want for k in kinds):
                    rep["type_mismatch"].append(rec)
        rep["suites"].append({"suite": suite, "n_base": len(b),
                              "n_new": len(n), "rows_moved": moved})
    rs = json.loads(Path(args.rescore).read_text(encoding="utf-8"))
    a1 = json.loads(Path(args.a1).read_text(encoding="utf-8"))
    bar = lambda d: [s for s in d["suites"] if not s.get("informational")]  # noqa: E731
    rep["rescore_new_changes"] = sum(s["changes"] for s in bar(rs))
    rep["rescore_new_sanity"] = sum(s["sanity_mismatch"] for s in bar(rs))
    rep["a1_base_changes"] = sum(s["changes"] for s in bar(a1))
    rep["counts"] = {k: len(rep[k]) for k in (
        "glue_moves", "verdict_moves", "other_moves", "type_mismatch",
        "missing_rows")}
    rep["moved_row_ids"] = sorted({f"{g['suite']}:{g['id']}"
                                   for g in rep["glue_moves"]})
    rep["pass"] = (not rep["verdict_moves"] and not rep["other_moves"]
                   and not rep["type_mismatch"] and not rep["missing_rows"]
                   and rep["rescore_new_changes"] == 0
                   and rep["rescore_new_sanity"] == 0
                   and rep["a1_base_changes"] == 0)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    for s in rep["suites"]:
        print(f"{s['suite']:<40} rows={s['n_base']:>4} moved={s['rows_moved']}")
    print(json.dumps(rep["counts"]), "rescore_new", rep["rescore_new_changes"],
          rep["rescore_new_sanity"], "a1", rep["a1_base_changes"],
          "moved_rows", len(rep["moved_row_ids"]),
          "PASS" if rep["pass"] else "FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
