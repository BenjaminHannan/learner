#!/usr/bin/env python3
"""Dev-bank save diagnosis for lis-319 (reading thread, 2026-09-26). DEV only (artifacts/claude-e2e331-dev-20260924).

Which taught facts does the lis-319 reader read right, and at what confidence and mode? Answers the "Answering from
memory" thread's list of facts build G never saved, and feeds the 0.98 vs 0.995 decision. Prints counts only.

rows:     python claude_lis319k_devbank.py rows --bank BANK --run ARM_G.jsonl --out ROWS.jsonl
          one reader row per teach/correct turn: {"id": "<life>#<turn>", "turn", "prev_reply", "history"} with the
          build's own earlier replies from ARM_G (history = earlier [user, reply] pairs of that life, the reader uses 6).
classify: python claude_lis319k_devbank.py classify --bank BANK --rows ROWS.jsonl --reads READS.jsonl [--facts F1,F2,..]
          --out OUT.json. For each taught fact (or only the listed fact ids): the best read fact of its teach turn that
          e2e-matches it -> saved (conf >= 0.995 and compiler ok), below_bar (by mode: conf in [0.98, 0.995), [0.95, 0.98),
          < 0.95), compiler_reject, or not_read (no read fact matches). Counts per class and, for listed ids, the class
          per fact id (ids and classes only).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis300_compiler as CMP  # noqa: E402
from claude_lis317_gates import e2e_match  # noqa: E402
from claude_lis319_fullclaim import load  # noqa: E402

T = 0.995


def rows(a):
    turns = load(Path(a.bank) / "turns.jsonl")
    run = {(r["life_id"], r["turn_index"]): r for r in load(a.run) if r["kind"] == "user"}
    hist, out, c = {}, [], Counter()
    for t in sorted(turns, key=lambda t: (t["life_id"], t["turn_index"])):
        life, i = t["life_id"], t["turn_index"]
        h = hist.setdefault(life, [])
        if t["kind"] in ("teach", "correct"):
            out.append({"id": f"{life}#{i}", "turn": t["user_text"], "prev_reply": h[-1][1] if h else "",
                        "history": [list(x) for x in h]})
            c[t["kind"]] += 1
        r = run.get((life, i))
        c["missing_run_row"] += r is None
        h.append((t["user_text"], (r or {}).get("reply", "")))
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print(json.dumps(dict(c) | {"rows": len(out)}))


def cls(f, row, read):
    fr = (read or {}).get("frame") or {}
    facts = [x for x in (fr.get("facts") or []) if isinstance(x, dict)]
    confs = (read or {}).get("conf") or []
    best = None
    for i, x in enumerate(facts):
        if not e2e_match(x, {"owner": f["owner"], "relation": f["relation"], "value": f["value"]}):
            continue
        cf = confs[i] if i < len(confs) else 0.0
        ok = CMP.check_fact(x, row["turn"], row.get("prev_reply", "")) is None
        mode = x.get("mode", "?")
        if not ok:
            k = f"compiler_reject:{mode}"
        elif cf >= T:
            k = "saved"
        else:
            band = "0.98-0.995" if cf >= 0.98 else ("0.95-0.98" if cf >= 0.95 else "<0.95")
            k = f"below_bar:{mode}:{band}"
        rank = 0 if k == "saved" else 1 if k.startswith("below_bar") else 2
        if best is None or rank < best[0]:
            best = (rank, k)
    return best[1] if best else ("no_read" if read is None else "not_read")


def classify(a):
    truth = load(Path(a.bank) / "truth.jsonl")
    rw = {r["id"]: r for r in load(a.rows)}
    rd = {r["id"]: r for r in load(a.reads)}
    want = set(a.facts.split(",")) if a.facts else None
    c, per = Counter(), {}
    for f in truth:
        if f.get("taught_turn") is None or (want and f["fact_id"] not in want):
            continue
        rid = f"{f['life_id']}#{f['taught_turn']}"
        if rid not in rw:
            c["teach_row_missing"] += 1
            continue
        k = cls(f, rw[rid], rd.get(rid))
        c[k] += 1
        if want:
            per[f["fact_id"]] = k
    out = {"facts": sum(c.values()), "classes": dict(sorted(c.items()))} | ({"per_fact": per} if want else {})
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out["classes"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["rows", "classify"])
    ap.add_argument("--bank", default="artifacts/claude-e2e331-dev-20260924")
    ap.add_argument("--run")
    ap.add_argument("--rows")
    ap.add_argument("--reads")
    ap.add_argument("--facts")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    {"rows": rows, "classify": classify}[a.cmd](a)


if __name__ == "__main__":
    main()
