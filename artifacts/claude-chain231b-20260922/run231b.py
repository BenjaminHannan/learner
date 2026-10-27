#!/usr/bin/env python3
"""Exp 231b driver: 231's sealed runner/scorer, unchanged, with two new arms.

The scoring rules are 231's (scripts/claude_chain231_run.py, sealed in
artifacts/claude-chain231-20260922/SEAL.sha256.txt, sha a4575fcb...). This
driver imports that module read-only, checks its sha first, adds two arm
entries to its CONFIGS dict at runtime and calls its own run_arm /
score_one / answerable functions. It never re-implements a scoring rule.

Arms:
  221x232c = scripts/claude_loop221x232c_agent.py + loop221x232c-config.json
  231b     = scripts/claude_loop231b_agent.py     + loop231b-config.json
Saved rows (reported only): plain 221 and plain 231 from
artifacts/claude-chain231-20260922/{panel,dev}/rows-*.jsonl.

ANSWERABLE (brief): 231's answerable() applied to the 231b arm's rows
(every setup turn saved on 231b). Also reported per arm.

Usage (repo root):
  python -B artifacts/claude-chain231b-20260922/run231b.py run --arm 231b \
      --items F --out DIR
  python -B artifacts/claude-chain231b-20260922/run231b.py score-dev --out DIR
  python -B artifacts/claude-chain231b-20260922/run231b.py score-panel --out DIR

Panel schema check (driver-side, before any scoring; OPUS-RULES contract):
the panel must load through 231's load_items() to exactly 72 items whose id
set equals the id set of 231's saved panel rows (all three arms), each with
a non-empty question and a list of setup turns; the item kinds must be in
{answer, yes, no, abstain}. Otherwise print SCHEMA-MISMATCH and exit 3.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

HERE = ROOT / "artifacts/claude-chain231b-20260922"
OLD = ROOT / "artifacts/claude-chain231-20260922"
PANEL = ROOT / "artifacts/claude-chainpanel231-20260922/panel.jsonl"
DEV = OLD / "dev231.jsonl"
SCORER = SCRIPTS / "claude_chain231_run.py"
SCORER_SHA = "a4575fcbd09756dab0bbb5679c362c9e060bd3f655d3cd9a8fba620052635c66"
FLAG_ID = "c231-013"  # 231's scorer flag on a true reply (reported apart)
NEW_ARMS = ("221x232c", "231b")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _scorer():
    got = _sha(SCORER)
    if got != SCORER_SHA:
        print(f"SCORER SHA MISMATCH {got}", flush=True)
        sys.exit(4)
    import claude_chain231_run as S  # noqa: E402 (sealed 231, read-only)
    S.CONFIGS["221x232c"] = ("claude_loop221x232c_agent",
                             "build_agent221x232c", "DEFAULT_CONFIG221X232C",
                             HERE / "loop221x232c-config.json")
    S.CONFIGS["231b"] = ("claude_loop231b_agent", "build_agent231b",
                         "DEFAULT_CONFIG231B", HERE / "loop231b-config.json")
    return S


def _rows(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _grade_all(S, items, rows: dict) -> dict:
    """grades[arm][id], answerable[arm][id] via 231's own functions."""
    g, ans = {}, {}
    for a, rr in rows.items():
        g[a] = {it["id"]: S.score_one(it, rr[it["id"]]) for it in items}
        ans[a] = {it["id"]: S.answerable(it, rr[it["id"]]) for it in items}
    return {"grade": g, "answerable": ans}


def _failing_setups(S, it, row) -> list[dict]:
    """Setup turns that did not land (same logic as answerable())."""
    turns, wrote = it["setup"], row.get("setup_wrote") or []
    bad = []
    for i, t in enumerate(turns):
        if i < len(wrote) and wrote[i]:
            continue
        if S._YN.match(t.strip()):
            bad.append(i)
            continue
        nxt = i + 1
        if not (nxt < len(turns) and S._YN.match(turns[nxt].strip())
                and nxt < len(wrote) and wrote[nxt]):
            bad.append(i)
    return [{"turn": turns[i], "reply": (row.get("setup_replies") or
                                         [""] * len(turns))[i]}
            for i in bad]


def _arm_summary(items, G, arm, ans_ref) -> dict:
    s = {"RIGHT": 0, "WRONG": 0, "ABSTAIN": 0, "OTHER": 0,
         "by_family": {}, "answerable": {"n": 0, "RIGHT": 0, "n_na": 0,
                                         "RIGHT_na": 0, "n_abstain": 0,
                                         "RIGHT_abstain": 0}}
    for it in items:
        gr = G["grade"][arm][it["id"]]
        s[gr] += 1
        f = s["by_family"].setdefault(it["family"], {"n": 0, "RIGHT": 0})
        f["n"] += 1
        f["RIGHT"] += int(gr == "RIGHT")
        if ans_ref[it["id"]]:
            A = s["answerable"]
            A["n"] += 1
            A["RIGHT"] += int(gr == "RIGHT")
            k = "abstain" if it["kind"] == "abstain" else "na"
            A["n_" + k] += 1
            A["RIGHT_" + k] += int(gr == "RIGHT")
    return s


def score_panel(out: Path) -> int:
    S = _scorer()
    items = S.load_items(PANEL)
    old = {a: _rows(OLD / "panel" / f"rows-{a}.jsonl")
           for a in ("138i", "221", "231")}
    # ---- schema check (before any scoring)
    ids = [it["id"] for it in items]
    bad = []
    if len(items) != 72 or len(set(ids)) != 72:
        bad.append(f"count {len(items)} / unique {len(set(ids))}")
    for a, rr in old.items():
        if set(rr) != set(ids):
            bad.append(f"id set differs from saved rows-{a}")
    for it in items:
        if not it["question"].strip() or not isinstance(it["setup"], list):
            bad.append(f"{it['id']} question/setup")
        if it["kind"] not in ("answer", "yes", "no", "abstain"):
            bad.append(f"{it['id']} kind {it['kind']}")
    new = {}
    for a in NEW_ARMS:
        p = out / f"rows-{a}.jsonl"
        if not p.exists():
            bad.append(f"missing {p.name}")
            continue
        new[a] = _rows(p)
        if set(new[a]) != set(ids):
            bad.append(f"id set differs in {p.name}")
    if bad:
        print("SCHEMA-MISMATCH", bad, flush=True)
        return 3
    rows = {"221": old["221"], "231": old["231"], **new}
    G = _grade_all(S, items, rows)
    ans_b = G["answerable"]["231b"]
    res: dict = {"answerable_ref": "231b", "arms": {}, "items": []}
    for a in rows:
        res["arms"][a] = _arm_summary(items, G, a, ans_b)
        res["arms"][a]["writes"] = sum(int(bool(rows[a][i]["wrote"]))
                                       for i in ids)
        res["arms"][a]["answerable_own"] = sum(G["answerable"][a].values())
    # regrade check: saved 221/231 grades must equal 231's scores.json
    prev = json.loads((OLD / "panel/scores.json").read_text("utf-8"))
    res["regrade_diffs_vs_231_scores"] = [
        (x["id"], a) for x in prev["items"] for a in ("221", "231")
        if x[a] != G["grade"][a][x["id"]]]
    gb, gx = G["grade"]["231b"], G["grade"]["221x232c"]
    flag_same = rows["231b"][FLAG_ID]["reply"] == old["231"][FLAG_ID]["reply"]
    m1a_ids = [i for i in ids if gb[i] == "WRONG"
               and not (i == FLAG_ID and flag_same)]
    ans_ids = [i for i in ids if ans_b[i]]
    na_ids = [i for i in ans_ids
              if next(it for it in items if it["id"] == i)["kind"] != "abstain"]
    rb = sum(gb[i] == "RIGHT" for i in ans_ids)
    rx = sum(gx[i] == "RIGHT" for i in ans_ids)
    rb_na = sum(gb[i] == "RIGHT" for i in na_ids)
    lost_x = [i for i in ids if gx[i] == "RIGHT" and gb[i] != "RIGHT"]
    lost_231 = [i for i in ids if G["grade"]["231"][i] == "RIGHT"
                and gb[i] != "RIGHT"]
    d = [rows["231b"][i]["ms"] - rows["221x232c"][i]["ms"] for i in ids]
    lat = {"median": round(statistics.median(d), 2),
           "p90": round(sorted(d)[int(0.9 * (len(d) - 1))], 2)}
    marks = {
        "M1a_wrong_231b_counted": len(m1a_ids), "M1a_ids": m1a_ids,
        "M1a_flag_item": {"id": FLAG_ID, "grade_231b": gb[FLAG_ID],
                          "reply_same_as_231": flag_same},
        "M1a_pass": len(m1a_ids) == 0,
        "M1b_question_writes_231b": res["arms"]["231b"]["writes"],
        "M1b_pass": res["arms"]["231b"]["writes"] == 0,
        "M1c_answerable_n": len(ans_ids), "M1c_231b_right": rb,
        "M1c_221x232c_right": rx, "M1c_pass": rb >= rx + 20,
        "M1d_n": len(na_ids), "M1d_231b_right": rb_na,
        "M1d_pct": round(100.0 * rb_na / max(1, len(na_ids)), 1),
        "M1d_pass": len(na_ids) > 0 and rb_na >= 0.85 * len(na_ids),
        "M1e_lost_vs_221x232c": lost_x, "M1e_lost_vs_231": lost_231,
        "M1e_pass": not lost_x and not lost_231,
        "M5_latency_231b_minus_221x232c_ms": lat,
        "M5_pass": lat["median"] <= 10.0,
    }
    res["marks"] = marks
    blocked = {}
    for a in rows:
        blocked[a] = {i: _failing_setups(
            S, next(it for it in items if it["id"] == i), rows[a][i])
            for i in ids if not G["answerable"][a][i]}
    res["blocked"] = blocked
    lines = ["| id | family | kind | ans(231b) | question | 221 | 231 | "
             "221x232c | 231b | 231b reply |", "|" + "---|" * 10]
    for it in items:
        i = it["id"]
        rec = {"id": i, "family": it["family"], "kind": it["kind"],
               "question": it["question"], "gold": it["gold"],
               "answerable_231b": ans_b[i],
               "answerable": {a: G["answerable"][a][i] for a in rows},
               "grade": {a: G["grade"][a][i] for a in rows},
               "reply": {a: rows[a][i]["reply"] for a in rows},
               "stage_231b": rows["231b"][i].get("stage", ""),
               "ms": {a: rows[a][i].get("ms") for a in NEW_ARMS}}
        res["items"].append(rec)
        lines.append(f"| {i} | {it['family']} | {it['kind']} | "
                     f"{'yes' if ans_b[i] else 'BLOCKED'} | {it['question']} "
                     f"| " + " | ".join(G["grade"][a][i] for a in
                                        ("221", "231", "221x232c", "231b"))
                     + f" | {rows['231b'][i]['reply']} |")
    (out / "scores231b.json").write_text(json.dumps(res, indent=1),
                                         encoding="utf-8")
    (out / "cases.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"arms": {a: {k: v for k, v in s.items()
                                   if k != "by_family"}
                               for a, s in res["arms"].items()},
                      "marks": marks,
                      "regrade_diffs": res["regrade_diffs_vs_231_scores"],
                      "blocked_counts": {a: len(b) for a, b in
                                         blocked.items()}}, indent=1))
    ok = all(marks[k] for k in marks if k.endswith("_pass"))
    print("PANEL MARKS:", "all pass" if ok else "FAIL", flush=True)
    return 0


def score_dev(out: Path) -> int:
    S = _scorer()
    items = S.load_items(DEV)
    ids = [it["id"] for it in items]
    rows = {a: _rows(out / f"rows-{a}.jsonl") for a in NEW_ARMS}
    rows["231"] = _rows(OLD / "dev/rows-231.jsonl")
    rows["221"] = _rows(OLD / "dev/rows-221.jsonl")
    G = _grade_all(S, items, rows)
    ans_b = G["answerable"]["231b"]
    ans_231 = {it["id"]: S.answerable(it, rows["221"][it["id"]])
               for it in items}  # 231's own answerable set (on 221)
    gb = G["grade"]["231b"]
    old54 = [i for i in ids if ans_231[i]]
    ans_ids = [i for i in ids if ans_b[i]]
    abst = [i for i in ans_ids
            if next(it for it in items if it["id"] == i)["kind"] == "abstain"]
    m2 = {
        "answerable_231b_n": len(ans_ids),
        "answerable_231b_right": sum(gb[i] == "RIGHT" for i in ans_ids),
        "old54_n": len(old54),
        "old54_all_answerable_on_231b": all(ans_b[i] for i in old54),
        "old54_right_231b": sum(gb[i] == "RIGHT" for i in old54),
        "newly_answerable": [i for i in ans_ids if not ans_231[i]],
        "traps_n": len(abst), "traps_right": sum(gb[i] == "RIGHT"
                                                 for i in abst),
        "wrong_231b": [i for i in ids if gb[i] == "WRONG"],
        "writes_231b": sum(int(bool(rows["231b"][i]["wrote"])) for i in ids),
        "diffs_vs_231_reply": [i for i in ids if rows["231b"][i]["reply"]
                               != rows["231"][i]["reply"]],
        "grade_221x232c_right": sum(G["grade"]["221x232c"][i] == "RIGHT"
                                    for i in ans_ids),
        "misses_231b": [(i, gb[i]) for i in ans_ids if gb[i] != "RIGHT"],
    }
    m2["M2_pass"] = (m2["old54_all_answerable_on_231b"]
                     and m2["old54_right_231b"] == len(old54) == 54
                     and m2["answerable_231b_right"] == len(ans_ids)
                     and m2["traps_right"] == m2["traps_n"] == 15
                     and not m2["wrong_231b"] and m2["writes_231b"] == 0)
    detail = [{"id": i, "grade": {a: G["grade"][a][i] for a in rows},
               "answerable_231b": ans_b[i],
               "reply_231b": rows["231b"][i]["reply"],
               "reply_231": rows["231"][i]["reply"]} for i in ids]
    (out / "dev-scores231b.json").write_text(
        json.dumps({"M2": m2, "items": detail}, indent=1), encoding="utf-8")
    print(json.dumps(m2, indent=1))
    print("M2:", "pass" if m2["M2_pass"] else "FAIL", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "score-dev", "score-panel"])
    ap.add_argument("--arm", default=None)
    ap.add_argument("--items", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out)
    if args.mode == "run":
        S = _scorer()
        if args.arm not in NEW_ARMS:
            ap.error("arm must be 221x232c or 231b")
        S.run_arm(args.arm, S.load_items(Path(args.items)), out)
        return 0
    if args.mode == "score-dev":
        return score_dev(out)
    return score_panel(out)


if __name__ == "__main__":
    sys.exit(main())
