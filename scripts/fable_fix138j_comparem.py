#!/usr/bin/env python3
"""Exp 138j marks123 pilot comparison -- per-case diff of a marks123 run
against the sealed marks138i outputs (pilot helper; also used post-seal
to verify the registered run). Compares verdict + reply/final text per
case id; reports moves by suite. Usage: compare_marks138j.py <mydir>."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts" / "fable-agent138i-20260922" / "marks138i"


def rows_of(report: dict):
    rows = report.get("rows", report.get("cases", []))
    if isinstance(rows, dict):
        rows = [{"id": k, **(v if isinstance(v, dict) else {"v": v})}
                for k, v in rows.items()]
    return rows


def key_text(r: dict) -> str:
    for k in ("agent_final", "final", "reply", "agent_reply", "got",
              "verdict", "agent_verdict", "status"):
        if k in r and isinstance(r[k], str):
            pass
    verdict = r.get("agent_verdict", r.get("verdict", r.get("status")))
    text = r.get("agent_final", r.get("final", r.get("reply",
             r.get("agent_reply", r.get("got", r.get("observed", ""))))))
    extra = ""
    if "facts_delta" in r or "taught_delta" in r:
        extra = f"||fd={r.get('facts_delta')}/td={r.get('taught_delta')}"
    return f"{verdict}||{str(text)[:300]}{extra}"


def cmp_report(name: str, mine: Path, base: Path) -> dict:
    m = json.loads(mine.read_text(encoding="utf-8"))
    b = json.loads(base.read_text(encoding="utf-8"))
    mr = {r.get("id", i): r for i, r in enumerate(rows_of(m))}
    br = {r.get("id", i): r for i, r in enumerate(rows_of(b))}
    moves, new_wrong, only_mine, only_base = [], 0, [], []
    for i, r in mr.items():
        if i not in br:
            only_mine.append(i)
            continue
        if key_text(r) != key_text(br[i]):
            moves.append({"id": i,
                          "base": key_text(br[i])[:160],
                          "mine": key_text(r)[:160]})
    for i in br:
        if i not in mr:
            only_base.append(i)
    return {"suite": name, "n_mine": len(mr), "n_base": len(br),
            "moves": moves, "only_mine": only_mine,
            "only_base": only_base}


def main() -> int:
    mydir = Path(sys.argv[1])
    total_moves = 0
    for name in ("p2", "p4", "rt110", "q1", "rt81", "soak", "q4",
                 "sleep", "bench"):
        mine = mydir / f"{name}-report.json"
        base = BASE / f"{name}-report.json"
        if not mine.exists() or not base.exists():
            print(f"{name}: missing report, skip")
            continue
        rep = cmp_report(name, mine, base)
        print(f"{name}: n={rep['n_mine']}/{rep['n_base']} "
              f"moves={len(rep['moves'])} only_mine={rep['only_mine']} "
              f"only_base={rep['only_base']}")
        for mv in rep["moves"][:30]:
            print(f"  MOVE {mv['id']}: base={mv['base']!r}")
            print(f"                mine={mv['mine']!r}")
        total_moves += len(rep["moves"])
    for sub in ("l1", "l2", "l3", "l4", "l5z1", "l5z2", "l6"):
        mine = mydir / "p3" / f"{sub}-report.json"
        base = BASE / "p3" / f"{sub}-report.json"
        if not mine.exists():
            mine = mydir / f"{sub}-report.json"
        if not base.exists():
            base = BASE / f"{sub}-report.json"
        if not mine.exists() or not base.exists():
            print(f"p3/{sub}: missing report, skip")
            continue
        rep = cmp_report(f"p3/{sub}", mine, base)
        print(f"p3/{sub}: n={rep['n_mine']}/{rep['n_base']} "
              f"moves={len(rep['moves'])}")
        for mv in rep["moves"][:30]:
            print(f"  MOVE {mv['id']}: base={mv['base']!r}")
            print(f"                mine={mv['mine']!r}")
        total_moves += len(rep["moves"])
    for name in ("bench-rows-fable_edit_200",
                 "bench-rows-s2fresh_4hop"):
        mine = mydir / f"{name}.jsonl"
        base = BASE / f"{name}.jsonl"
        if not mine.exists() or not base.exists():
            print(f"{name}: missing rows, skip")
            continue
        mr = [json.loads(l) for l in mine.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        br = [json.loads(l) for l in base.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        mb = {r.get("id"): r for r in mr}
        bb = {r.get("id"): r for r in br}
        moves = [i for i in mb if i in bb and (
            mb[i].get("verdict") != bb[i].get("verdict") or str(
                mb[i].get("reply", "")) != str(bb[i].get("reply", "")))]
        print(f"{name}: n={len(mr)}/{len(br)} moves={len(moves)}")
        for i in moves[:20]:
            print(f"  MOVE {i}: base={bb[i].get('verdict')} "
                  f"{str(bb[i].get('reply',''))[:100]!r} mine={mb[i].get('verdict')} "
                  f"{str(mb[i].get('reply',''))[:100]!r}")
        total_moves += len(moves)
    # Single-object suites: compare scalar fields.
    for name, fields in (
            ("q1", ("f5_ok", "m5_ok", "f5_reply", "m5_reply")),
            ("sleep", ("skipped", "reason")),
            ("soak", ("completed", "kill9s", "lost", "wrong",
                      "doubled_replies", "audit_lost_pairs",
                      "audit_dup_pairs", "audit_wrong_pairs"))):
        mine = mydir / f"{name}-report.json"
        base = BASE / f"{name}-report.json"
        if not mine.exists() or not base.exists():
            continue
        m = json.loads(mine.read_text(encoding="utf-8"))
        b = json.loads(base.read_text(encoding="utf-8"))
        diffs = [f for f in fields
                 if json.dumps(m.get(f), sort_keys=True)
                 != json.dumps(b.get(f), sort_keys=True)]
        print(f"{name}: scalar-diffs={diffs}")
        if name == "soak":
            print(f"  soak wrong_detail mine={json.dumps(m.get('wrong_detail'))[:400]}")
            print(f"  soak wrong_detail base={json.dumps(b.get('wrong_detail'))[:400]}")
        total_moves += len(diffs)
    print(f"TOTAL moves={total_moves}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
