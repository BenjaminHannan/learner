#!/usr/bin/env python3
"""gram-364 grading files and marks P364.1 / P364.2 (artifacts/claude-gram364-20260925/PASSMARKS.md).

  prep  CHECK_OUT GRADE_OUT -> GRADE_OUT/gram{A,B}/items.jsonl, GRADE_OUT/key_{A,B}.json: the union of rule_raw,
                               rule_final360, rule_final364 and all_final (a line in several sets is graded once)
                               + 336's 40 planted errors + 40 planted clean lines, shuffled with seeds 3641 / 3642
  score GRADE_OUT           -> needs GRADE_OUT/grades_{A,B}.jsonl ({"id", "ok"}); prints counts only
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
SETS = ("rule_raw", "rule_final360", "rule_final364", "all_final")


def prep(chk: Path, out: Path) -> None:
    import claude_gram360_gradeprep as GP
    sets: dict[str, list[str]] = {}
    for name in SETS:
        for x in (json.loads(l)["text"] for l in (chk / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
                  if l.strip()):
            sets.setdefault(x, []).append(name)
    for g, seed in (("A", 3641), ("B", 3642)):
        items = [(t, {"sets": s, "planted_error": False, "planted_clean": False}) for t, s in sets.items()]
        items += [(e, {"sets": [], "planted_error": True, "planted_clean": False}) for e in GP.ERRS]
        items += [(c, {"sets": [], "planted_error": False, "planted_clean": True}) for c in GP.CLEAN_B]
        random.Random(seed).shuffle(items)
        d = out / f"gram{g}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "items.jsonl").write_text("".join(json.dumps({"id": f"{g}{i:04d}", "text": t}, ensure_ascii=False)
                                               + "\n" for i, (t, _) in enumerate(items)), encoding="utf-8")
        (out / f"key_{g}.json").write_text(json.dumps({f"{g}{i:04d}": k for i, (_, k) in enumerate(items)}),
                                           encoding="utf-8")
    print(json.dumps({"lines": len(sets), "planted_errors": len(GP.ERRS), "planted_clean": len(GP.CLEAN_B)}))


def score(d: Path) -> None:
    res: dict = {}
    for g in ("A", "B"):
        key = json.loads((d / f"key_{g}.json").read_text(encoding="utf-8"))
        ok = {r["id"]: bool(r["ok"]) for r in (json.loads(x) for x in
              (d / f"grades_{g}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip())}
        r = {"missing": sum(1 for i in key if i not in ok),
             "planted_caught": sum(1 for i, k in key.items() if k["planted_error"] and ok.get(i) is False),
             "clean_kept": sum(1 for i, k in key.items() if k["planted_clean"] and ok.get(i) is True)}
        r["valid"] = r["planted_caught"] >= 36 and r["clean_kept"] >= 36 and r["missing"] == 0
        for s in SETS:
            ids = [i for i, k in key.items() if s in k["sets"]]
            good = sum(1 for i in ids if ok.get(i) is True)
            r[s] = [good, len(ids), round(100.0 * good / max(1, len(ids)), 1)]
        r["gain"] = round(r["rule_final364"][2] - r["rule_final360"][2], 1)
        res[g] = r
    v = [res[g] for g in ("A", "B")]
    res["P364.1"] = "PASS" if all(x["valid"] and x["rule_final364"][2] >= 94.0 for x in v) else "FAIL"
    res["P364.2"] = "PASS" if all(x["valid"] and x["gain"] >= 3.0 for x in v) else "FAIL"
    res["proved_wrong"] = any(x["valid"] and x["gain"] < 1.0 for x in v)
    print(json.dumps(res, sort_keys=True))


if __name__ == "__main__":
    if sys.argv[1] == "prep":
        prep(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        score(Path(sys.argv[2]))
