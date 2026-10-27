#!/usr/bin/env python3
"""y1t-H1 judging and marks (artifacts/claude-y1tH1-20260926/PASSMARKS-y1t-H1.md). Wrong-as-fact thread, 2026-09-26,
written before any y1t-H1 run. New file. Prints counts only, never words.

  prep  PANEL SCORE OUT           sf-401's packet prep (claude_sf401_judges.prep) with seed 4013 -> OUT/asks.jsonl,
                                  OUT/key_asks.json
  split OUT J1 J2                 claude_sf401_judges.split -> OUT/split_ids.json
  marks PANEL SCORE OUT J1 J2 J3  H1a-H1d, the INCONCLUSIVE rule and the report rows (J3 may be an empty file)
  --selftest                      plumbing check on sf-401's own run rows (counts only; fake judges)

SCORE is claude_y1tH1_score.py's output folder (arm_A.jsonl, arm_B.jsonl, judge_asks_A.jsonl, judge_asks_B.jsonl).
Final verdict = judge 1 when judges 1 and 2 agree, else judge 3. "Right" = RIGHT + RIGHT_CONFIRM (336 score_ask).
Decoy asks = decoys.jsonl checked_by. Edit asks map to a correction style through gold.uses_facts and
corrections.jsonl new_fact.
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from math import ceil
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_e2e336_score as SC  # noqa: E402
import claude_sf401_judges as J  # noqa: E402

SEED = 4013
ld = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]  # noqa: E731


def prep(panel: Path, score: Path, out: Path) -> None:
    J.SEED401 = SEED
    J.prep(panel, score, out)


def final_by_ask(score: Path, out: Path, j1: Path, j2: Path, j3: Path) -> dict:
    key = json.loads((out / "key_asks.json").read_text(encoding="utf-8"))
    packets = {p["id"]: p for p in ld(out / "asks.jsonl")}
    v1, v2, v3 = J._verdicts(j1), J._verdicts(j2), J._verdicts(j3)
    missing = [i for i in key if i not in v1 or i not in v2 or (v1[i] != v2[i] and i not in v3)]
    if missing:
        raise SystemExit(f"y1tH1 marks: {len(missing)} packets lack a verdict")
    rows = []
    for arm in ("A", "B"):
        rows += [dict(p, _arm=arm) for p in ld(score / f"judge_asks_{arm}.jsonl")]
    random.Random(SEED).shuffle(rows)
    res = {}
    for i, p in enumerate(rows):
        pid = f"Q{i:04d}"
        assert key[pid] == p["_arm"] and packets[pid]["reply"] == p["reply"], "prep order mismatch"
        res[(p["_arm"], p["life_id"], p["turn_index"])] = v1[pid] if v1[pid] == v2[pid] else v3[pid]
    return res


def marks(panel: Path, score: Path, out: Path, j1: Path, j2: Path, j3: Path) -> dict:
    turns = ld(panel / "turns.jsonl")
    tk = {(t["life_id"], t["turn_index"]): t for t in turns}
    truth = {f["fact_id"]: f for f in ld(panel / "truth.jsonl")}
    corr = {c["new_fact"]: c for c in ld(panel / "corrections.jsonl")}
    decoy_asks = {(d["life_id"], d["checked_by"]) for d in ld(panel / "decoys.jsonl")}
    final = final_by_ask(score, out, j1, j2, j3)
    judges = {"packets": len(final), "splits": len(json.loads((out / "split_ids.json").read_text()))
              if (out / "split_ids.json").exists() else None}
    m = {}
    for arm in ("A", "B"):
        c = defaultdict(Counter)
        for r in ld(score / f"arm_{arm}.jsonl"):
            t = tk.get((r["life_id"], r["turn_index"]))
            if t is None or t["kind"] != "ask":
                c["join"]["miss"] += 1
                continue
            k = SC.score_ask(t, r, None)
            right = k in ("RIGHT", "RIGHT_CONFIRM")
            wrong = final.get((arm, r["life_id"], r["turn_index"])) == "wrong"
            group = "edit" if t["ask_type"] == "edit" else ("never_told" if t["ask_type"] == "never_told"
                                                              else "control")
            c[group][k] += 1
            c["right"][group] += right
            c["wrong"]["edit" if group == "edit" else "other"] += wrong
            if (r["life_id"], r["turn_index"]) in decoy_asks:
                c["decoy"]["asks"] += 1
                c["decoy"]["right"] += right
                c["decoy"]["judged_wrong"] += wrong
            if group == "edit":
                news = [f for f in t["gold"]["uses_facts"] if f in corr]
                style = str(corr[news[0]]["style"]) if len(news) == 1 else "unlinked"
                c[f"style_{style}"]["asks"] += 1
                c[f"style_{style}"]["right"] += right
                c[f"style_{style}"]["judged_wrong"] += wrong
                if wrong and len(news) == 1:
                    old = str(truth[corr[news[0]]["old_fact"]]["value"]).lower()
                    c["wrong"]["edit_names_old_value"] += old in str(r["reply"]).lower()
        m[arm] = c
    wa, wb = m["A"]["wrong"]["edit"], m["B"]["wrong"]["edit"]
    table = [
        ("H1a", "judged wrong, edit asks", wa, wb, wb <= wa - max(4, ceil(wa / 3))),
        ("H1b", "right, edit asks", m["A"]["right"]["edit"], m["B"]["right"]["edit"],
         m["B"]["right"]["edit"] >= m["A"]["right"]["edit"] - 3),
        ("H1c", "right, decoy asks", m["A"]["decoy"]["right"], m["B"]["decoy"]["right"],
         m["B"]["decoy"]["right"] >= m["A"]["decoy"]["right"] - 2),
        ("H1d", "judged wrong, all other asks", m["A"]["wrong"]["other"], m["B"]["wrong"]["other"],
         m["B"]["wrong"]["other"] <= m["A"]["wrong"]["other"]),
    ]
    inconclusive = wa < 8
    print("| Row | What | A | B | Verdict |\n|---|---|---|---|---|")
    for row, what, a, b, ok in table:
        v = "INCONCLUSIVE" if (row == "H1a" and inconclusive) else ("PASS" if ok else "FAIL")
        print(f"| {row} | {what} | {a} | {b} | {v} |")
    fails = [r for r, *_x, ok in table if not ok and not (r == "H1a" and inconclusive)]
    overall = "FAIL" if fails else ("INCONCLUSIVE" if inconclusive else "PASS")
    print(f"overall: {overall}")
    report = {"judges": judges, "overall": overall,
              "arms": {a: {k: dict(v) for k, v in sorted(m[a].items())} for a in m}}
    print(json.dumps(report, sort_keys=True))
    return report


def selftest() -> int:
    """sf-401's run rows (already scored there) through this pipeline with fake judges; counts only."""
    R = HERE.parent / "artifacts/claude-sf401-20260926"
    panel = R / "panel"
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "run").mkdir()
        tk = {(t["life_id"], t["turn_index"]): t for t in ld(panel / "turns.jsonl")}
        for arm in ("A", "B"):
            with open(d / "run" / f"rows_{arm}.jsonl", "w", encoding="utf-8") as fh:
                for r in ld(R / f"run/arm_{arm}.jsonl"):
                    t = tk.get((r["life_id"], r["turn_index"]))
                    if r["kind"] == "user" and t is not None and t["kind"] == "ask":
                        fh.write(json.dumps({"life_id": r["life_id"], "turn_index": r["turn_index"],
                                             "kind": "ask", "reply": r["reply"]}) + "\n")
        rc = subprocess.call([sys.executable, "-B", str(HERE / "claude_y1tH1_score.py"), str(panel), str(d / "run"),
                              str(d / "score")], stdout=subprocess.DEVNULL)
        assert rc == 0, rc
        out = d / "judges"
        prep(panel, d / "score", out)
        pk = ld(out / "asks.jsonl")
        for name, verdict in (("j1", "wrong"), ("j2", "wrong")):
            (out / f"{name}.jsonl").write_text("".join(json.dumps({"id": p["id"], "verdict": verdict,
                                                                   "reason": "fake"}) + "\n" for p in pk))
        (out / "j3.jsonl").write_text("")
        J.split(out, out / "j1.jsonl", out / "j2.jsonl")
        rep = marks(panel, d / "score", out, out / "j1.jsonl", out / "j2.jsonl", out / "j3.jsonl")
        wc = {a: sum(1 for _ in ld(d / "score" / f"judge_asks_{a}.jsonl")) for a in ("A", "B")}
        got = {a: rep["arms"][a]["wrong"]["edit"] + rep["arms"][a]["wrong"]["other"] for a in ("A", "B")}
        assert got == wc, (got, wc)
        assert sum(rep["arms"]["A"]["decoy"].values()) > 0
        print(f"y1tH1 marks selftest ok: fake all-wrong judges give judged wrong = mechanical wrong candidates {wc}")
    return 0


def main() -> int:
    cmd, a = sys.argv[1], [Path(x) for x in sys.argv[2:]]
    if cmd == "--selftest":
        return selftest()
    if cmd == "prep":
        prep(*a)
    elif cmd == "split":
        J.split(*a)
    elif cmd == "marks":
        marks(*a)
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
