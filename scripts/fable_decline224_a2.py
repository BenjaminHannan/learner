#!/usr/bin/env python3
"""Exp 224a mark A2: is_decline accepts every census text + the three 224b
sentences, rejects the self-CANNOT answers, and rejects a deterministic
sample of real answers and save confirmations from the stored 138i rows.

Sample (fixed rule, no hand picking): the first 50 distinct "Saved:" teach
replies in artifacts/fable-agent138i-20260922/g2frozen/redteam143-loop138i.json
(teach_replies, file order) and the first 50 distinct replies whose stored
bench verdict is "correct" in g1bench/fable_benchv3_loop138i_edit200_rows.jsonl
(file order).

  python3 -B scripts/fable_decline224_a2.py --out <json>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent
import fable_decline224 as D  # noqa: E402

B138I = ROOT / "artifacts" / "fable-agent138i-20260922"


def sample() -> tuple[list[str], list[str]]:
    rt = json.loads((B138I / "g2frozen" / "redteam143-loop138i.json")
                    .read_text(encoding="utf-8"))
    saves: list[str] = []
    for r in rt["rows"] if isinstance(rt, dict) else rt:
        for t in r.get("teach_replies", []):
            if t.startswith("Saved:") and t not in saves:
                saves.append(t)
    answers: list[str] = []
    for line in (B138I / "g1bench" / "fable_benchv3_loop138i_edit200_rows"
                 ".jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["verdict"] == "correct" and r["reply"] not in answers:
            answers.append(r["reply"])
    return saves[:50], answers[:50]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    census_miss = [t for t, _ in D.CENSUS224 if not D.is_decline(t)]
    new_miss = [k for k, t in D.NEW_SENTENCES224.items()
                if not D.is_decline(t)]
    self_hit = [t for t, _ in D.SELF_CANNOT_ANSWERS224 if D.is_decline(t)]
    saves, answers = sample()
    save_hit = [t for t in saves if D.is_decline(t)]
    ans_hit = [t for t in answers if D.is_decline(t)]
    rejected = (len(saves) - len(save_hit)) + (len(answers) - len(ans_hit))
    rep = {"census_n": len(D.CENSUS224), "census_missed": census_miss,
           "new_n": len(D.NEW_SENTENCES224), "new_missed": new_miss,
           "self_cannot_n": len(D.SELF_CANNOT_ANSWERS224),
           "self_cannot_accepted": self_hit,
           "saves_n": len(saves), "saves_accepted": save_hit,
           "answers_n": len(answers), "answers_accepted": ans_hit,
           "rejected_real": rejected,
           "pass": (not census_miss and not new_miss and not save_hit
                    and not ans_hit and rejected >= 50)}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(f"census {len(D.CENSUS224) - len(census_miss)}/{len(D.CENSUS224)} "
          f"new {len(D.NEW_SENTENCES224) - len(new_miss)}/"
          f"{len(D.NEW_SENTENCES224)} self-cannot rejected "
          f"{len(D.SELF_CANNOT_ANSWERS224) - len(self_hit)}/"
          f"{len(D.SELF_CANNOT_ANSWERS224)} real rejected {rejected}/"
          f"{len(saves) + len(answers)} -> {'PASS' if rep['pass'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
