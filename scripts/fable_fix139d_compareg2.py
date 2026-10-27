#!/usr/bin/env python3
"""Experiment 139d G2 -- per-case compare of marks123 outputs vs marks139c.

Compares artifacts/fable-tail139d-20260922/marks139d against the frozen
artifacts/fable-tailwords139c-20260922/marks139c. Semantic level: per-case
verdict + reply/observed text. Byte level: normalized JSON (volatile keys
dropped: timings, tmp paths, pids, replied_before_kill counts,
statuses-metadata, sleep SKIP reason that names the agent file).
Bar: semantic moves only on PASSMARKS-predicted cases (predicted: none).

Usage: python -B scripts/fable_fix139d_compareg2.py [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts" / "fable-tailwords139c-20260922" / "marks139c"
NEW = ROOT / "artifacts" / "fable-tail139d-20260922" / "marks139d"

VOLATILE_SUBSTR = ("second", "elapsed", "wall", "timing", "took", "duration",
                   "pid", "tmp", "heartbeat", "replied_before_kill",
                   "statuses", "date", "time_", "_at", "path", "dir_",
                   "_dir", "workdir", "reason")
VERDICT_KEYS = ("agent_verdict", "verdict", "status", "result", "outcome")
TEXT_KEYS = ("agent_final", "observed", "reply", "final", "text", "answer",
             "response", "output")


def norm(obj):
    if isinstance(obj, dict):
        return {k: norm(v) for k, v in obj.items()
                if not any(s in k.lower() for s in VOLATILE_SUBSTR)}
    if isinstance(obj, list):
        return [norm(v) for v in obj]
    return obj


def case_rows(doc):
    """Yield (id, verdict, text) triples from a report-shaped doc."""
    rows = []
    if isinstance(doc, dict):
        for key in ("rows", "cases", "results", "items"):
            if isinstance(doc.get(key), list):
                cand = doc[key]
                break
        else:
            cand = [doc]
    elif isinstance(doc, list):
        cand = doc
    else:
        return rows
    for r in cand:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id", r.get("case", r.get("name", "?"))))
        verdict = next((str(r[k]) for k in VERDICT_KEYS if k in r), "?")
        text = next((str(r[k]) for k in TEXT_KEYS if k in r), "")
        rows.append((rid, verdict, text))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 139d G2 compare")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    base_files = sorted(p.relative_to(BASE) for p in BASE.rglob("*.json")
                        if "tmp" not in str(p.relative_to(BASE)))
    base_jsonl = sorted(p.relative_to(BASE) for p in BASE.rglob("*.jsonl")
                        if "tmp" not in str(p.relative_to(BASE)))
    sem_moves: list[dict] = []
    byte_diffs: list[str] = []
    missing: list[str] = []
    for rel in base_files:
        nb, nn = BASE / rel, NEW / rel
        if not nn.exists():
            missing.append(str(rel))
            continue
        b = json.loads(nb.read_text(encoding="utf-8"))
        n = json.loads(nn.read_text(encoding="utf-8"))
        br = {i: (v, t) for i, v, t in case_rows(b)}
        nr = {i: (v, t) for i, v, t in case_rows(n)}
        for cid, (bv, bt) in br.items():
            if cid not in nr:
                sem_moves.append({"file": str(rel), "id": cid,
                                  "loop139c": (bv, bt[:120]),
                                  "loop139d": "MISSING"})
            elif nr[cid] != (bv, bt):
                sem_moves.append({"file": str(rel), "id": cid,
                                  "loop139c": (bv, bt[:120]),
                                  "loop139d": (nr[cid][0],
                                               nr[cid][1][:120])})
        for cid in nr:
            if cid not in br:
                sem_moves.append({"file": str(rel), "id": cid,
                                  "loop139c": "MISSING",
                                  "loop139d": nr[cid]})
        if norm(b) != norm(n):
            byte_diffs.append(str(rel))
    for rel in base_jsonl:
        nb, nn = BASE / rel, NEW / rel
        if not nn.exists():
            missing.append(str(rel))
            continue
        bl = [json.loads(x) for x in nb.read_text(encoding="utf-8")
              .splitlines() if x.strip()]
        nl = [json.loads(x) for x in nn.read_text(encoding="utf-8")
              .splitlines() if x.strip()]
        bmap = {str(r.get("id", i)): (json.dumps(
            {k: v for k, v in r.items()
             if not any(s in k.lower() for s in VOLATILE_SUBSTR)},
            sort_keys=True)) for i, r in enumerate(bl)}
        nmap = {str(r.get("id", i)): (json.dumps(
            {k: v for k, v in r.items()
             if not any(s in k.lower() for s in VOLATILE_SUBSTR)},
            sort_keys=True)) for i, r in enumerate(nl)}
        for cid, bt in bmap.items():
            if nmap.get(cid) != bt:
                sem_moves.append({"file": str(rel), "id": cid,
                                  "loop139c": bt[:160],
                                  "loop139d": (nmap.get(cid) or
                                               "MISSING")[:160]})
        if norm(bl) != norm(nl) and str(rel) not in [
                m["file"] for m in sem_moves]:
            byte_diffs.append(str(rel) + " (cosmetic-only)")
    out = {"semantic_moves": sem_moves, "n_semantic_moves": len(sem_moves),
           "byte_diffs_normalized": byte_diffs, "missing": missing}
    dest = Path(args.out) if args.out else (
        ROOT / "artifacts" / "fable-tail139d-20260922" / "g2-compare.json")
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"G2 compare: {len(sem_moves)} semantic moves, "
          f"{len(byte_diffs)} normalized byte diffs, "
          f"{len(missing)} missing")
    for m in sem_moves[:30]:
        print(f"  MOVE {m}")
    print(f"wrote {dest}")
    return 0 if not sem_moves else 1


if __name__ == "__main__":
    sys.exit(main())
