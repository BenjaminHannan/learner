#!/usr/bin/env python3
"""gram-361 packets and marks (artifacts/claude-gram361-20260925/PASSMARKS.md).

  prep  RUN_DIR PANEL OUT   -> OUT/gram{A,B}/items.jsonl, OUT/key_{A,B}.json (grammar: union of both arms'
                               distinct replies + 336's 40 planted errors + 40 planted clean, seeds 3611/3612);
                               OUT/judge/pairs.jsonl, OUT/key_judge.json (helpfulness, sides shuffled, seed 3613)
  score RUN_DIR OUT         -> prints the marks (needs OUT/grades_{A,B}.jsonl and OUT/judge/verdicts.jsonl)
RUN_DIR holds arm_t07.jsonl and arm_t03.jsonl from scripts/claude_gram361.py.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path


GIVE_UP = "well enough to save"


def ld(p: Path) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def wr(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def prep(run: Path, panel: Path, out: Path) -> None:
    import claude_gram360_gradeprep as GP
    arms = {a: ld(run / f"arm_{a}.jsonl") for a in ("t07", "t03")}
    sets: dict[str, list[str]] = {}
    for a, rows in arms.items():
        for r in rows:
            if r["reply"] and a not in sets.setdefault(r["reply"], []):
                sets[r["reply"]].append(a)
    for g, seed in (("A", 3611), ("B", 3612)):
        items = [(t, {"sets": s, "planted_error": False, "planted_clean": False}) for t, s in sets.items()]
        items += [(e, {"sets": [], "planted_error": True, "planted_clean": False}) for e in GP.ERRS]
        items += [(c, {"sets": [], "planted_error": False, "planted_clean": True}) for c in GP.CLEAN_B]
        random.Random(seed).shuffle(items)
        wr(out / f"gram{g}/items.jsonl", [{"id": f"{g}{i:04d}", "text": t} for i, (t, _) in enumerate(items)])
        (out / f"key_{g}.json").write_text(json.dumps({f"{g}{i:04d}": k for i, (_, k) in enumerate(items)}),
                                           encoding="utf-8")
    turns = {(t["conv_id"], t["turn_index"]): t for t in ld(panel)}
    rng, pairs, key = random.Random(3613), [], {}
    by = {a: {(r["conv_id"], r["turn_index"]): r["reply"] for r in rows} for a, rows in arms.items()}
    for (cid, ti) in sorted(by["t07"]):
        before = [turns[(cid, j)]["user_text"] for j in range(ti)]
        order = ["t07", "t03"]
        rng.shuffle(order)
        pid = f"J{len(pairs):04d}"
        key[pid] = order
        pairs.append({"id": pid, "earlier_user_messages": before, "user": turns[(cid, ti)]["user_text"],
                      "reply_1": by[order[0]][(cid, ti)], "reply_2": by[order[1]][(cid, ti)]})
    wr(out / "judge/pairs.jsonl", pairs)
    (out / "key_judge.json").write_text(json.dumps(key), encoding="utf-8")
    print(json.dumps({"grammar_lines": len(sets), "pairs": len(pairs)}))


def score(run: Path, out: Path) -> None:
    res: dict = {}
    for g in ("A", "B"):
        key = json.loads((out / f"key_{g}.json").read_text(encoding="utf-8"))
        ok = {r["id"]: bool(r["ok"]) for r in ld(out / f"grades_{g}.jsonl")}
        r = {"missing": sum(1 for i in key if i not in ok),
             "planted_caught": sum(1 for i, k in key.items() if k["planted_error"] and ok.get(i) is False),
             "clean_kept": sum(1 for i, k in key.items() if k["planted_clean"] and ok.get(i) is True)}
        r["valid"] = r["planted_caught"] >= 36 and r["clean_kept"] >= 36 and r["missing"] == 0
        ids_by_text = {it["text"]: it["id"] for it in ld(out / f"gram{g}/items.jsonl")}
        for a in ("t07", "t03"):
            rows = ld(run / f"arm_{a}.jsonl")
            good = sum(1 for x in rows if x["reply"] and ok.get(ids_by_text.get(x["reply"])) is True)
            n = sum(1 for x in rows if x["reply"])
            r[a] = [good, n, round(100.0 * good / max(1, n), 1)]
        r["gain"] = round(r["t03"][2] - r["t07"][2], 1)
        res[g] = r
    kj = json.loads((out / "key_judge.json").read_text(encoding="utf-8"))
    win = Counter()
    for v in ld(out / "judge/verdicts.jsonl"):
        pick = v["better"]                       # "1", "2" or "tie"
        win["tie" if pick == "tie" else kj[v["id"]][int(pick) - 1]] += 1
    res["judge"] = dict(win)
    tot = sum(win.values())
    res["t03_win_or_tie_pct"] = round(100.0 * (win["t03"] + win["tie"]) / max(1, tot), 1)
    for a in ("t07", "t03"):
        rows = ld(run / f"arm_{a}.jsonl")
        c = Counter(x["reply"] for x in rows)
        res[f"{a}_gave_up_kept"] = sum(1 for x in rows if GIVE_UP in x["reply"].lower())
        res[f"{a}_most_common"] = c.most_common(1)[0][1] if c else 0
        res[f"{a}_distinct"] = len(c)
        res[f"{a}_turns"] = len(rows)
    v = [res[g] for g in ("A", "B")]
    res["P361.1"] = "PASS" if all(x["valid"] and x["t03"][2] >= 97.0 for x in v) else "FAIL"
    res["P361.2"] = "PASS" if all(x["valid"] and x["gain"] >= 8.0 for x in v) else "FAIL"
    res["P361.3"] = "PASS" if res["t03_win_or_tie_pct"] >= 50.0 else "FAIL"
    res["P361.4"] = "PASS" if res["t03_gave_up_kept"] <= res["t07_gave_up_kept"] + 3 else "FAIL"
    res["P361.5"] = "PASS" if res["t03_most_common"] <= 0.05 * res["t03_turns"] else "FAIL"
    res["proved_wrong"] = any(x["valid"] and x["gain"] < 3.0 for x in v)
    print(json.dumps(res, sort_keys=True))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if sys.argv[1] == "prep":
        prep(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    else:
        score(Path(sys.argv[2]), Path(sys.argv[3]))
