#!/usr/bin/env python3
"""Experiment 190b -- V2 marks123 per-case comparer (Muse).

Compares loop190b marks123 reports (produced one suite at a time via
scripts/fable_marks123_all.py --agent scripts/fable_loop190b_agent.py
--config artifacts/fable-reverse190b-20260922/loop190b-config.json
--out artifacts/fable-reverse190b-20260922/marks190b --suite <s>)
against the SEALED loop190 reports in
artifacts/fable-reverse190-20260922/marks190/ (read-only).

Volatile metadata is scrubbed before compare (seconds/timing, tmp/out
paths, the agent filename in the sleep SKIP reason, daemon PIDs):
everything else must be per-case identical. Zero moves predicted (the
190b rewording only fires on closed-shape reverse no-match turns with
unknown values; the 190 pre-seal scan found no such turns in any
marks123 suite). Any diff fails honestly.

Outputs the diff report into artifacts/fable-reverse190b-20260922/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix190_marks as M190  # noqa: E402 (comparers, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-reverse190b-20260922"
SEALED = ROOT / "artifacts" / "fable-reverse190-20260922" / "marks190"
MINE = ART / "marks190b"

DROP_KEYS = {"seconds", "total_seconds", "elapsed", "duration_s"}


def scrub(obj, out_a: str, out_b: str):
    if isinstance(obj, dict):
        return {k: scrub(v, out_a, out_b) for k, v in obj.items()
                if k not in DROP_KEYS}
    if isinstance(obj, list):
        return [scrub(v, out_a, out_b) for v in obj]
    if isinstance(obj, str):
        s = obj.replace("fable_loop190b_agent.py", "AGENT.py").replace(
            "fable_loop190_agent.py", "AGENT.py")
        s = s.replace(out_a, "$OUT").replace(out_b, "$OUT")
        return s
    return obj


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def cmp_bench_rows() -> list[str]:
    diffs: list[str] = []
    for name in ("bench-rows-fable_edit_200.jsonl",
                 "bench-rows-s2fresh_4hop.jsonl"):
        a, b = MINE / name, SEALED / name
        if not a.exists():
            return [f"marks-bench: missing {name} (suite not run?)"]
        rows_a = [json.loads(l) for l in a.read_text().splitlines()
                  if l.strip()]
        rows_b = [json.loads(l) for l in b.read_text().splitlines()
                  if l.strip()]
        mb = {r.get("id"): r for r in rows_b}
        for r in rows_a:
            o = mb.get(r.get("id"), {})
            if r.get("verdict") != o.get("verdict"):
                diffs.append(f"marks-bench {name} {r.get('id')}: 190="
                             f"{o.get('verdict')} 190b={r.get('verdict')}")
    return diffs


def main() -> int:
    out_a = str(MINE)
    out_b = str(SEALED)
    diffs: list[str] = []
    ran = []
    for name in ("p2-report.json", "p3-report.json", "p4-report.json",
                 "rt110-report.json", "q1-report.json", "rt81-report.json",
                 "sleep-report.json", "soak-report.json", "q4-report.json",
                 "bench-report.json"):
        a, b = MINE / name, SEALED / name
        if not a.exists():
            diffs.append(f"{name}: NOT RUN (no loop190b report)")
            continue
        ran.append(name)
        mine = scrub(load(a), out_a, out_b)
        sealed = scrub(load(b), out_a, out_b)
        diffs.extend(M190.cmp_report(name, mine, sealed))
    if (MINE / "bench-report.json").exists():
        diffs.extend(cmp_bench_rows())
    report = {"suites_compared": ran, "n_diffs": len(diffs),
              "diffs": diffs,
              "pass": (len(diffs) == 0 and len(ran) == 10)}
    (ART / "v2-marks-compare190b.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8")
    print(f"marks123 compare: {len(ran)}/10 suites, "
          f"{len(diffs)} diffs", flush=True)
    for d in diffs[:40]:
        print(f"  DIFF {d}", flush=True)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
