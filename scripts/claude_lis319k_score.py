#!/usr/bin/env python3
"""lis-319k: corrections save at a lower bar (0.95 for facts the reader labels CORRECT, 0.995 for the rest).

bar:    python claude_lis319k_score.py bar --reads R --out R_NEW.jsonl [--mode CORRECT --at 0.95]
        writes the same reads with the confidence of every fact whose mode is CORRECT and conf >= 0.95 set to 1.0,
        so the usual scorers at 0.995 apply the new rule. Prints counts only.
pairs:  python claude_lis319k_score.py pairs --panel P --reads R_NEW.jsonl --out PAIRS.jsonl
        = claude_lis319_fullclaim_b.py pairs at 0.995 (NEW saves are a superset of OLD saves, so NEW's pairs cover both).
final:  python claude_lis319k_score.py final --panel P --reads R --pairs PAIRS.jsonl --verdicts J1 --verdicts J2 --out OUT.json
        whole-claim credit exactly as fullclaim_b final (exact first, then pairs both judges call same, one-to-one),
        plus: correction_right (credited gold facts with "correction": true), correction_gold, stale_saves (saved fact
        e2e-matching a "replaced" item of its row and no current fact), lookalike_saves (saves on rows of kind
        "lookalike"). Run it once on the OLD reads and once on the NEW reads with the same pairs and verdicts.
verdict: python claude_lis319k_score.py verdict --old OLD.json --new NEW.json
selftest: python claude_lis319k_score.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis319_fullclaim_b as FB  # noqa: E402
from claude_lis317_gates import e2e_match  # noqa: E402
from claude_lis319_fullclaim import key, load  # noqa: E402

T = 0.995


def bar(a):
    c = Counter()
    out = []
    for r in load(a.reads):
        facts = ((r.get("frame") or {}).get("facts") or [])
        confs = list(r.get("conf") or [])
        for i, f in enumerate(facts):
            if isinstance(f, dict) and f.get("mode") == a.mode and i < len(confs):
                c["mode_facts"] += 1
                if T > confs[i] >= a.at:
                    confs[i] = 1.0
                    c["raised"] += 1
        out.append(dict(r, conf=confs))
        c["reads"] += 1
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print(json.dumps(dict(c)))


def pairs(a):
    p, per_t = FB.walk(load(a.panel), load(a.reads), [T])
    Path(a.out).write_text("".join(json.dumps(x) + "\n" for x in p.values()), encoding="utf-8")
    print(json.dumps(dict(per_t[T][0]) | {"pairs": len(p)}))


def score(panel, reads, pair_rows, verdicts):
    p, per_t = FB.walk(panel, reads, [T])
    pid = {key(x["id"], x["saved"], x["gold"]): x["pid"] for x in pair_rows}
    missing = set(p) - set(pid)
    assert not missing, f"{len(missing)} pairs of these reads are not in the pairs file"
    V = [{int(r["pid"]): bool(r["same"]) for r in vs} for vs in verdicts]
    assert V and all(set(v) == set(pid.values()) for v in V), "a judge file does not cover every pair"
    same = {x for x in pid.values() if all(v[x] for v in V)}
    c, rows = per_t[T]
    byid = {row["id"]: row for row in panel}
    rd = {r["id"]: r for r in reads}
    out = Counter({k: 0 for k in ("saved_right_full", "saved_duplicate", "saved_wrong_full", "correction_right",
                                  "correction_gold", "stale_saves", "lookalike_rows", "lookalike_saves")})
    wrong_rows = set()
    for rid, _has_gold, items in rows:
        row = byid[rid]
        taken = set()
        for i in sorted(range(len(items)), key=lambda i: not items[i][0]):
            ex, ks = items[i]
            ok = list(ex) + [gi for k, gi in ks if pid[k] in same]
            free = [gi for gi in ok if gi not in taken]
            if free:
                taken.add(free[0])
                out["saved_right_full"] += 1
            elif ok:
                out["saved_duplicate"] += 1
            else:
                out["saved_wrong_full"] += 1
                wrong_rows.add(rid)
        out["correction_right"] += sum(bool(row["facts"][gi].get("correction")) for gi in taken)
        out["correction_gold"] += sum(bool(g.get("correction")) for g in row["facts"])
        saved = FB.saved_facts(row, rd.get(rid), T) if rd.get(rid) is not None else []
        rep = row.get("replaced") or []
        out["stale_saves"] += sum(1 for f in saved if any(e2e_match(f, g) for g in rep)
                                  and not any(e2e_match(f, g) for g in row["facts"]))
        if row.get("kind") == "lookalike":
            out["lookalike_rows"] += 1
            out["lookalike_saves"] += len(saved)
    out["wrong_turns_full"] = len(wrong_rows)
    return dict(c) | dict(out)


def final(a):
    res = score(load(a.panel), load(a.reads), load(a.pairs), [load(v) for v in a.verdicts])
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res))


def verdict(a):
    o, n = json.loads(Path(a.old).read_text()), json.loads(Path(a.new).read_text())
    m = {"K1": n["correction_right"] >= o["correction_right"] + 5,
         "K2": n["saved_wrong_full"] <= o["saved_wrong_full"] + 1,
         "K3": n["stale_saves"] <= o["stale_saves"],
         "K4": n["lookalike_saves"] <= o["lookalike_saves"] + 1}
    valid = o["correction_gold"] >= 40 and o["correction_gold"] - o["correction_right"] >= 8
    v = "INCONCLUSIVE" if not valid else ("PASS" if all(m.values()) else "FAIL")
    keys = ("correction_gold", "correction_right", "saved_right_full", "saved_wrong_full", "wrong_turns_full",
            "stale_saves", "lookalike_saves")
    print(json.dumps({"verdict": v, "proved_wrong": valid and n["correction_right"] - o["correction_right"] <= 1,
                      **m, **{k: [o[k], n[k]] for k in keys}}, indent=1))


def selftest(_a):
    import tempfile
    panel = [
        {"id": "d1-t1", "kind": "correction", "turn": "sorry, Wren is 13 not 12", "prev_reply": "",
         "facts": [{"owner": "Wren", "relation": "age", "value": "13", "correction": True}],
         "replaced": [{"owner": "Wren", "relation": "age", "value": "12"}]},
        {"id": "d1-t2", "kind": "lookalike", "turn": "is Wren 13 now?", "prev_reply": "", "facts": [], "replaced": []},
        {"id": "d1-t3", "kind": "short", "turn": "my dog is Pip", "prev_reply": "",
         "facts": [{"owner": "USER", "relation": "dog", "value": "Pip"}], "replaced": []}]
    reads = [
        {"id": "d1-t1", "frame": {"act": "CORRECT", "facts": [
            {"owner": "Wren", "rel": "age", "value": "13", "mode": "CORRECT"}]}, "conf": [0.97]},
        {"id": "d1-t2", "frame": {"act": "CHECK", "facts": []}, "conf": []},
        {"id": "d1-t3", "frame": {"act": "STATE", "facts": [
            {"owner": "me", "rel": "dog", "value": "Pip", "mode": "ASSERT"}]}, "conf": [0.97]}]
    ok = {}
    with tempfile.TemporaryDirectory() as d:
        rp, np_ = Path(d) / "r.jsonl", Path(d) / "n.jsonl"
        rp.write_text("".join(json.dumps(r) + "\n" for r in reads))
        bar(argparse.Namespace(reads=str(rp), out=str(np_), mode="CORRECT", at=0.95))
        new = load(np_)
        ok["raised_only_correct"] = new[0]["conf"] == [1.0] and new[2]["conf"] == [0.97]
        p, _ = FB.walk(panel, new, [T])
        prs = [dict(x) for x in p.values()]
        v = [{"pid": x["pid"], "same": True} for x in prs]
        so = score(panel, reads, prs, [v, v])
        sn = score(panel, new, prs, [v, v])
        ok["old_misses"] = so["correction_right"] == 0 and so["correction_gold"] == 1
        ok["new_credits"] = sn["correction_right"] == 1 and sn["saved_wrong_full"] == 0
        ok["lookalike_counted"] = sn["lookalike_rows"] == 1 and sn["lookalike_saves"] == 0
    for k, x in ok.items():
        print(("PASS " if x else "FAIL ") + k)
    print("LIS319K-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bar", "pairs", "final", "verdict", "selftest"])
    ap.add_argument("--panel")
    ap.add_argument("--reads")
    ap.add_argument("--pairs")
    ap.add_argument("--verdicts", action="append", default=[])
    ap.add_argument("--mode", default="CORRECT")
    ap.add_argument("--at", type=float, default=0.95)
    ap.add_argument("--old")
    ap.add_argument("--new")
    ap.add_argument("--out")
    a = ap.parse_args()
    return {"bar": bar, "pairs": pairs, "final": final, "verdict": verdict, "selftest": selftest}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
