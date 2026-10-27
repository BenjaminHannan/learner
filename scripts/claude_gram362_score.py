#!/usr/bin/env python3
"""gram-362 packets and marks (artifacts/claude-gram362-20260925/PASSMARKS.md).

  prep  RUN_DIR PANEL OUT   -> OUT/gram{A,B}/items.jsonl, OUT/key_{A,B}.json (grammar: union of both arms'
                               distinct replies + 336's 40 planted errors + 40 planted clean, seeds 3631/3632);
                               OUT/judge/pairs.jsonl, OUT/key_judge.json (helpfulness, sides shuffled, seed 3633)
  score RUN_DIR OUT         -> prints the marks (needs OUT/grades_{A,B}.jsonl and OUT/judge/verdicts.jsonl)
RUN_DIR holds arm_base.jsonl and arm_critic.jsonl from scripts/claude_gram362.py.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path


GIVE_UP = "well enough to save"
HONEST = "I'm not sure. I don't think you've told me that yet."   # 338b's fixed line, not sampled
BAR1, BAR2 = 90.0, 5.0                     # PASSMARKS.md P362.1, P362.2


def ld(p: Path) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def wr(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def prep(run: Path, panel: Path, out: Path) -> None:
    import claude_gram360_gradeprep as GP
    arms = {a: ld(run / f"arm_{a}.jsonl") for a in ("base", "critic")}
    sets: dict[str, list[str]] = {}
    for a, rows in arms.items():
        for r in rows:
            if r["reply"] and a not in sets.setdefault(r["reply"], []):
                sets[r["reply"]].append(a)
    for g, seed in (("A", 3631), ("B", 3632)):
        items = [(t, {"sets": s, "planted_error": False, "planted_clean": False}) for t, s in sets.items()]
        items += [(e, {"sets": [], "planted_error": True, "planted_clean": False}) for e in GP.ERRS]
        items += [(c, {"sets": [], "planted_error": False, "planted_clean": True}) for c in GP.CLEAN_B]
        random.Random(seed).shuffle(items)
        wr(out / f"gram{g}/items.jsonl", [{"id": f"{g}{i:04d}", "text": t} for i, (t, _) in enumerate(items)])
        (out / f"key_{g}.json").write_text(json.dumps({f"{g}{i:04d}": k for i, (_, k) in enumerate(items)}),
                                           encoding="utf-8")
    turns = {(t["conv_id"], t["turn_index"]): t for t in ld(panel)}
    rng, pairs, key = random.Random(3633), [], {}
    by = {a: {(r["conv_id"], r["turn_index"]): r["reply"] for r in rows} for a, rows in arms.items()}
    for (cid, ti) in sorted(by["base"]):
        before = [turns[(cid, j)]["user_text"] for j in range(ti)]
        order = ["base", "critic"]
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
        for a in ("base", "critic"):
            rows = ld(run / f"arm_{a}.jsonl")
            good = sum(1 for x in rows if x["reply"] and ok.get(ids_by_text.get(x["reply"])) is True)
            n = sum(1 for x in rows if x["reply"])
            r[a] = [good, n, round(100.0 * good / max(1, n), 1)]
        r["gain"] = round(r["critic"][2] - r["base"][2], 1)
        res[g] = r
    kj = json.loads((out / "key_judge.json").read_text(encoding="utf-8"))
    win = Counter()
    for v in ld(out / "judge/verdicts.jsonl"):
        pick = v["better"]                       # "1", "2" or "tie"
        win["tie" if pick == "tie" else kj[v["id"]][int(pick) - 1]] += 1
    res["judge"] = dict(win)
    tot = sum(win.values())
    res["critic_win_or_tie_pct"] = round(100.0 * (win["critic"] + win["tie"]) / max(1, tot), 1)
    for a in ("base", "critic"):
        rows = ld(run / f"arm_{a}.jsonl")
        c = Counter(x["reply"] for x in rows)
        res[f"{a}_gave_up_kept"] = sum(1 for x in rows if GIVE_UP in x["reply"].lower())
        res[f"{a}_most_common"] = c.most_common(1)[0][1] if c else 0
        fixed = Counter(x["reply"] for x in rows if x["reply"] != HONEST and GIVE_UP not in x["reply"].lower())
        res[f"{a}_most_common_sampled"] = fixed.most_common(1)[0][1] if fixed else 0
        res[f"{a}_distinct"] = len(c)
        res[f"{a}_turns"] = len(rows)
        res[f"{a}_words"] = round(sum(len(x["reply"].split()) for x in rows) / max(1, len(rows)), 1)
    v = [res[g] for g in ("A", "B")]
    res["P362.1"] = "PASS" if all(x["valid"] and x["critic"][2] >= BAR1 for x in v) else "FAIL"
    res["P362.2"] = "PASS" if all(x["valid"] and x["gain"] >= BAR2 for x in v) else "FAIL"
    res["P362.3"] = "PASS" if res["critic_win_or_tie_pct"] >= 50.0 else "FAIL"
    res["P362.4"] = "PASS" if res["critic_gave_up_kept"] <= res["base_gave_up_kept"] + 3 else "FAIL"
    res["P362.5"] = "PASS" if res["critic_most_common_sampled"] <= 0.05 * res["critic_turns"] else "FAIL"
    res["proved_wrong"] = any(x["valid"] and x["gain"] < 2.0 for x in v)
    print(json.dumps(res, sort_keys=True))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if sys.argv[1] == "prep":
        prep(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    else:
        score(Path(sys.argv[2]), Path(sys.argv[3]))
