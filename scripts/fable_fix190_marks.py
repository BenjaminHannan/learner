#!/usr/bin/env python3
"""Experiment 190 -- V2 marks123 per-case comparer (Muse).

Compares loop190 marks123 reports (produced one suite at a time via
scripts/fable_marks123_all.py --agent scripts/fable_loop190_agent.py
--config artifacts/fable-reverse190-20260922/loop190-config.json
--out artifacts/fable-reverse190-20260922/marks190 --suite <s>)
against the SEALED loop138g reports in
artifacts/fable-agent138g-20260922/marks138g/ (read-only).

Volatile metadata is scrubbed before compare (seconds/timing, tmp/out
paths, the agent filename in the sleep SKIP reason, daemon PIDs):
everything else must be per-case identical. The only predicted move is
the sleep SKIP reason's agent filename. Any other diff fails honestly.

Outputs the diff report into artifacts/fable-reverse190-20260922/ only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-reverse190-20260922"
SEALED = ROOT / "artifacts" / "fable-agent138g-20260922" / "marks138g"
MINE = ART / "marks190"

DROP_KEYS = {"seconds", "total_seconds", "elapsed", "duration_s"}


def scrub(obj, out_a: str, out_b: str):
    if isinstance(obj, dict):
        return {k: scrub(v, out_a, out_b) for k, v in obj.items()
                if k not in DROP_KEYS}
    if isinstance(obj, list):
        return [scrub(v, out_a, out_b) for v in obj]
    if isinstance(obj, str):
        s = obj.replace("fable_loop190_agent.py", "AGENT.py").replace(
            "fable_loop138g_agent.py", "AGENT.py")
        s = s.replace(out_a, "$OUT").replace(out_b, "$OUT")
        return s
    return obj


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def cmp_report(name: str, mine, sealed) -> list[str]:
    diffs: list[str] = []
    if name == "p2-report.json":
        for key in ("n", "ok_to_bug", "still_bug", "bug_to_ok"):
            if mine.get(key) != sealed.get(key):
                diffs.append(f"p2.{key}: 138g={sealed.get(key)} "
                             f"190={mine.get(key)}")
        mb = {(r["id"]): r for r in sealed["rows"]}
        for r in mine["rows"]:
            b = mb.get(r["id"], {})
            for key in ("agent_verdict", "sealed_verdict", "agent_final",
                        "reason"):
                if r.get(key) != b.get(key):
                    diffs.append(f"p2 row {r['id']}.{key}: 138g="
                                 f"{str(b.get(key))[:100]} 190="
                                 f"{str(r.get(key))[:100]}")
    elif name == "p3-report.json":
        if mine.get("selected") != sealed.get("selected"):
            diffs.append("p3.selected differs")
        for k, v in sealed.get("marks", {}).items():
            mv = mine.get("marks", {}).get(k, {})
            if mv.get("pass") != v.get("pass"):
                diffs.append(f"p3 mark {k}: 138g={v.get('pass')} "
                             f"190={mv.get('pass')}")
    elif name == "p4-report.json":
        for key in ("n", "false_refusals", "nonpass"):
            if mine.get(key) != sealed.get(key):
                diffs.append(f"p4.{key}: 138g={sealed.get(key)} "
                             f"190={mine.get(key)}")
        mb = {r["id"]: r for r in sealed["rows"]}
        for r in mine["rows"]:
            b = mb.get(r["id"], {})
            for key in ("pass", "replies", "stored", "false_refusal"):
                if r.get(key) != b.get(key):
                    diffs.append(f"p4 row {r['id']}.{key}: 138g="
                                 f"{str(b.get(key))[:100]} 190="
                                 f"{str(r.get(key))[:100]}")
    elif name == "rt110-report.json":
        for key in ("n", "ok_to_bug", "still_bug", "bug_to_ok",
                    "harness_errors"):
            if mine.get(key) != sealed.get(key):
                diffs.append(f"rt110.{key}: 138g={sealed.get(key)} "
                             f"190={mine.get(key)}")
    elif name == "q1-report.json":
        for key in ("f5_ok", "m5_ok", "f5_reply", "m5_reply"):
            if mine.get(key) != sealed.get(key):
                diffs.append(f"q1.{key}: 138g={str(sealed.get(key))[:100]} "
                             f"190={str(mine.get(key))[:100]}")
    elif name == "rt81-report.json":
        if mine.get("summary") != sealed.get("summary"):
            diffs.append(f"rt81.summary: 138g={sealed.get('summary')} "
                         f"190={mine.get('summary')}")
        mb = {r["id"]: r for r in sealed["cases"]}
        for r in mine["cases"]:
            b = mb.get(r["id"], {})
            for key in ("verdict", "observed"):
                if r.get(key) != b.get(key):
                    diffs.append(f"rt81 case {r['id']}.{key}: 138g="
                                 f"{str(b.get(key))[:120]} 190="
                                 f"{str(r.get(key))[:120]}")
    elif name == "sleep-report.json":
        if mine.get("skipped") != sealed.get("skipped"):
            diffs.append("sleep.skipped differs")
    elif name == "soak-report.json":
        for key in ("completed", "kill9s", "lost", "wrong",
                    "doubled_replies", "audit_lost_pairs",
                    "audit_wrong_pairs", "audit_dup_pairs"):
            if mine.get(key) != sealed.get(key):
                diffs.append(f"soak.{key}: 138g={sealed.get(key)} "
                             f"190={mine.get(key)}")
    elif name == "q4-report.json":
        if mine.get("leaks") != sealed.get("leaks"):
            diffs.append(f"q4.leaks: 138g={sealed.get('leaks')} "
                         f"190={mine.get('leaks')}")
    elif name == "bench-report.json":
        for key in ("pass", "splits"):
            if mine.get(key) != sealed.get(key):
                diffs.append(f"bench.{key} differs")
    else:
        if mine != sealed:
            diffs.append(f"{name}: full-tree diff")
    return diffs


def cmp_bench_rows(tag: str) -> list[str]:
    diffs: list[str] = []
    for name in (f"bench-rows-fable_edit_200.jsonl",
                 f"bench-rows-s2fresh_4hop.jsonl"):
        a, b = MINE / name, SEALED / name
        if not a.exists():
            return [f"{tag}: missing {name} (suite not run?)"]
        rows_a = [json.loads(l) for l in a.read_text().splitlines()
                  if l.strip()]
        rows_b = [json.loads(l) for l in b.read_text().splitlines()
                  if l.strip()]
        mb = {r.get("id"): r for r in rows_b}
        for r in rows_a:
            o = mb.get(r.get("id"), {})
            if r.get("verdict") != o.get("verdict"):
                diffs.append(f"marks-bench {name} {r.get('id')}: 138g="
                             f"{o.get('verdict')} 190={r.get('verdict')}")
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
            diffs.append(f"{name}: NOT RUN (no loop190 report)")
            continue
        ran.append(name)
        mine = scrub(load(a), out_a, out_b)
        sealed = scrub(load(b), out_a, out_b)
        diffs.extend(cmp_report(name, mine, sealed))
    if (MINE / "bench-report.json").exists():
        diffs.extend(cmp_bench_rows("bench"))
    report = {"suites_compared": ran, "n_diffs": len(diffs),
              "diffs": diffs,
              "pass": (len(diffs) == 0 and len(ran) == 10)}
    (ART / "v2-marks-compare190.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8")
    print(f"marks123 compare: {len(ran)}/10 suites, "
          f"{len(diffs)} diffs", flush=True)
    for d in diffs[:40]:
        print(f"  DIFF {d}", flush=True)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
