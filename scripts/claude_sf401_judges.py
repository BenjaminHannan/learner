#!/usr/bin/env python3
"""sf-401 judging and marks (artifacts/claude-sf401-20260926/PASSMARKS.md). New file only. Prints counts only.

  prep  BANK SCORE OUT      A's and B's WRONG_CANDIDATE asks (SCORE/judge_asks_A.jsonl, judge_asks_B.jsonl) mixed
                            under neutral ids, shuffled with seed 4011 -> OUT/asks.jsonl (for the blind judges) and
                            OUT/key_asks.json (arm per id; never shown to a judge)
  split OUT J1 J2           ids where judges 1 and 2 disagree -> OUT/split_ids.json (for the third judge)
  marks BANK SCORE OUT J1 J2 [J3] [SF401_COUNTS]
                            applies the key and prints the mark table (M1-M5), INCONCLUSIVE rule, and report rows
Judge files: JSON Lines {"id": ..., "verdict": "wrong" | "ok", "reason": ...}.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

SEED401 = 4011
ld = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]  # noqa: E731


def prep(bank: Path, score: Path, out: Path) -> None:
    turns = {(t["life_id"], t["turn_index"]): t for t in ld(bank / "turns.jsonl")}
    truth = ld(bank / "truth.jsonl")
    rows = []
    for arm in ("A", "B"):
        for p in ld(score / f"judge_asks_{arm}.jsonl"):
            p = dict(p)
            p["_arm"] = arm
            rows.append(p)
    random.Random(SEED401).shuffle(rows)
    key, packets = {}, []
    for i, p in enumerate(rows):
        pid = f"Q{i:04d}"
        key[pid] = p["_arm"]
        t = turns[(p["life_id"], p["turn_index"])]
        valid = [{k: f[k] for k in ("owner", "relation", "value")} for f in truth
                 if f["life_id"] == p["life_id"] and f["taught_turn"] <= p["turn_index"]
                 and (f.get("valid_until_turn") is None or f["valid_until_turn"] > p["turn_index"])]
        packets.append({"id": pid, "question": t["user_text"], "reply": p["reply"], "facts_valid_now": valid})
    out.mkdir(parents=True, exist_ok=True)
    (out / "asks.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in packets),
                                    encoding="utf-8")
    (out / "key_asks.json").write_text(json.dumps(key), encoding="utf-8")
    print(json.dumps({"packets": len(packets), "A": sum(1 for v in key.values() if v == "A"),
                      "B": sum(1 for v in key.values() if v == "B")}))


def _verdicts(p: Path) -> dict:
    return {r["id"]: r["verdict"] for r in ld(p)}


def split(out: Path, j1: Path, j2: Path) -> None:
    a, b = _verdicts(j1), _verdicts(j2)
    ids = sorted(i for i in a if a[i] != b.get(i))
    (out / "split_ids.json").write_text(json.dumps(ids), encoding="utf-8")
    print(json.dumps({"judged": len(a), "agree": len(a) - len(ids), "splits": len(ids)}))


def _right(c: Counter) -> int:
    return c.get("RIGHT", 0) + c.get("RIGHT_CONFIRM", 0)


def marks(bank: Path, score: Path, out: Path, j1: Path, j2: Path, j3: Path | None, counts: Path | None) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import claude_e2e336_score as SC
    turns = ld(bank / "turns.jsonl")
    tk = {(t["life_id"], t["turn_index"]): t for t in turns}
    key = json.loads((out / "key_asks.json").read_text(encoding="utf-8"))
    packets = {p["id"]: p for p in ld(out / "asks.jsonl")}
    v1, v2 = _verdicts(j1), _verdicts(j2)
    v3 = _verdicts(j3) if j3 else {}
    missing = [i for i in key if i not in v1 or i not in v2 or (v1[i] != v2[i] and i not in v3)]
    if missing:
        raise SystemExit(f"sf401 marks: {len(missing)} packets lack a verdict")
    final = {i: (v1[i] if v1[i] == v2[i] else v3[i]) for i in key}
    # map packet ids back to (life, turn) through the score packets, in the prep order
    rows = []
    for arm in ("A", "B"):
        for p in ld(score / f"judge_asks_{arm}.jsonl"):
            p = dict(p)
            p["_arm"] = arm
            rows.append(p)
    random.Random(SEED401).shuffle(rows)
    wrong = Counter()
    for i, p in enumerate(rows):
        pid = f"Q{i:04d}"
        assert key[pid] == p["_arm"] and packets[pid]["reply"] == p["reply"], "prep order mismatch"
        if final[pid] == "wrong":
            kind = "edit" if p.get("ask_type") == "edit" else (
                "never_told" if p.get("ask_type") == "never_told" else "control")
            wrong[(p["_arm"], kind)] += 1
    mech = {}
    for arm in ("A", "B"):
        c = {"edit": Counter(), "control": Counter(), "never_told": Counter()}
        arows = ld(score.parent / "run" / f"arm_{arm}.jsonl") if (score.parent / "run").exists() else None
        if arows is None:
            raise SystemExit("sf401 marks: run/arm_*.jsonl not found next to score/")
        conf = {(r["life_id"], r["turn_index"]): r for r in arows if r["kind"] == "confirm_answer"}
        for r in arows:
            t = tk.get((r["life_id"], r["turn_index"]))
            if r["kind"] != "user" or t is None or t["kind"] != "ask":
                continue
            kind = "edit" if t["ask_type"] == "edit" else ("never_told" if t["ask_type"] == "never_told" else "control")
            c[kind][SC.score_ask(t, r, conf.get((r["life_id"], r["turn_index"])))] += 1
        c["confirms"] = sum(1 for r in arows if r.get("confirm_asked"))
        mech[arm] = c
    wA = sum(v for (a, _k), v in wrong.items() if a == "A")
    wB = sum(v for (a, _k), v in wrong.items() if a == "B")
    rows_out = [
        ("M1", "judged wrong, all asks", wA, wB, wB <= wA - 4),
        ("M2", "right, control asks", _right(mech["A"]["control"]), _right(mech["B"]["control"]),
         _right(mech["B"]["control"]) >= _right(mech["A"]["control"]) - 2),
        ("M3", "right, edit asks", _right(mech["A"]["edit"]), _right(mech["B"]["edit"]),
         _right(mech["B"]["edit"]) >= _right(mech["A"]["edit"])),
        ("M4", "don't know, control asks", mech["A"]["control"].get("ABSTAIN", 0),
         mech["B"]["control"].get("ABSTAIN", 0),
         mech["B"]["control"].get("ABSTAIN", 0) <= mech["A"]["control"].get("ABSTAIN", 0) + 2),
        ("M5", "judged wrong, control asks", wrong[("A", "control")], wrong[("B", "control")],
         wrong[("B", "control")] <= wrong[("A", "control")] + 1),
    ]
    inconclusive = wrong[("A", "edit")] < 5
    print("| Row | What | A | B | Verdict |")
    print("|---|---|---|---|---|")
    for r, what, a, b, ok in rows_out:
        verdict = "INCONCLUSIVE" if (r == "M1" and inconclusive) else ("PASS" if ok else "FAIL")
        print(f"| {r} | {what} | {a} | {b} | {verdict} |")
    others = all(ok for r, _w, _a, _b, ok in rows_out if r != "M1")
    overall = ("INCONCLUSIVE" if inconclusive and others else
               "PASS" if all(ok for *_x, ok in rows_out) else "FAIL")
    print(f"overall: {overall}")
    report = {"judged_wrong": {f"{a}_{k}": v for (a, k), v in sorted(wrong.items())},
              "judges": {"packets": len(key), "agree_1_2": sum(1 for i in key if v1[i] == v2[i]),
                         "third_used": sum(1 for i in key if v1[i] != v2[i])},
              "mechanical": {arm: {k: dict(v) if isinstance(v, Counter) else v for k, v in mech[arm].items()}
                             for arm in mech}}
    if counts and Path(counts).exists():
        tot = Counter()
        for c in ld(counts):
            tot.update({k: v for k, v in c.items() if k != "doubts_live"})
        report["sf401_counters_B"] = dict(sorted(tot.items()))
    print(json.dumps(report, sort_keys=True))


def main() -> int:
    cmd = sys.argv[1]
    a = [Path(x) for x in sys.argv[2:]]
    if cmd == "prep":
        prep(*a)
    elif cmd == "split":
        split(*a)
    elif cmd == "marks":
        bank, score, out, j1, j2 = a[:5]
        j3 = a[5] if len(a) > 5 else None
        counts = a[6] if len(a) > 6 else None
        marks(bank, score, out, j1, j2, j3, counts)
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
