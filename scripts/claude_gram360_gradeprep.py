#!/usr/bin/env python3
"""gram-360 grading files: two blind shuffled sets (graders A and B) = rule_raw U rule_final U all_final
+ 40 planted errors + 40 planted clean lines, taken unchanged from 336's generator
(artifacts/claude-e2e336-20260924/judges/judge_prep336.py, the "# M7 grammar" block), seeds 3601 and 3602.

  python -B scripts/claude_gram360_gradeprep.py CHECK_OUT GRADE_OUT
Writes GRADE_OUT/gram{A,B}/items.jsonl ({"id","text"}) and GRADE_OUT/key_{A,B}.json (which set(s) each line is in).
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / "artifacts/claude-e2e336-20260924/judges/judge_prep336.py").read_text(encoding="utf-8")
BLOCK = SRC[SRC.index("# M7 grammar"):SRC.index("replies = ")]
NS: dict = {}
exec(BLOCK, NS)                                     # defines CLEAN, plant, errs, cleanB
ERRS, CLEAN_B = NS["errs"], NS["cleanB"]


def main() -> int:
    chk, out = Path(sys.argv[1]), Path(sys.argv[2])
    sets = {}
    for name in ("rule_raw", "rule_final", "all_final"):
        for x in (json.loads(l)["text"] for l in (chk / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
                  if l.strip()):
            sets.setdefault(x, []).append(name)
    for g, seed in (("A", 3601), ("B", 3602)):
        items = [(t, {"sets": s, "planted_error": False, "planted_clean": False}) for t, s in sets.items()]
        items += [(e, {"sets": [], "planted_error": True, "planted_clean": False}) for e in ERRS]
        items += [(c, {"sets": [], "planted_error": False, "planted_clean": True}) for c in CLEAN_B]
        random.Random(seed).shuffle(items)
        d = out / f"gram{g}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "items.jsonl").write_text("".join(json.dumps({"id": f"{g}{i:04d}", "text": t}, ensure_ascii=False)
                                               + "\n" for i, (t, _) in enumerate(items)), encoding="utf-8")
        (out / f"key_{g}.json").write_text(json.dumps({f"{g}{i:04d}": k for i, (_, k) in enumerate(items)}),
                                           encoding="utf-8")
    print(json.dumps({"lines": len(sets), "planted_errors": len(ERRS), "planted_clean": len(CLEAN_B)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
