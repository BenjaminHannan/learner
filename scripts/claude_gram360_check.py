#!/usr/bin/env python3
"""gram-360 mechanical checks (P360.3, P360.4) and the grading sets (P360.1, P360.2).

  python -B scripts/claude_gram360_check.py --bank BANK --run RUN/arm_P360.jsonl --log RUN/gram360_parts.jsonl \
      --out OUT

Aligns the gram360 sidecar (one line per agent.turn call: each part, whether the rule agent produced it, raw and
final text) with the run rows, then:
  P360.3  rendering changes no score: is_confirm, the harness's confirm answer and the 336 ask class are the same
          on the raw reply and on the final reply; every part the rule agent did not produce is byte-identical.
  P360.4  no slot word lost: each rendered part has the same words as its raw part once case, "_", "-", list
          brackets and the words the renderer may add or swap (is/are, a/an, other/goes with, pronoun owners) are set
          aside.
Writes OUT/rule_raw.jsonl, OUT/rule_final.jsonl (distinct rule-agent parts before and after rendering),
OUT/all_final.jsonl (distinct whole replies of the run, report only) and OUT/check.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_e2e336_run as R  # noqa: E402
import claude_e2e336_score as S  # noqa: E402

FREE = {"is", "are", "s", "other", "does", "go", "goes", "with", "she", "he", "her", "his", "him", "they",
        "them", "their", "it", "its", "i", "me", "my", "you", "your", "and", "a", "an"}


def load(p: Path) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def words(s: str) -> Counter:
    s = re.sub(r"[_\-\[\]',.?!:;\"]", " ", s.lower())
    return Counter(re.sub(r"s$", "", w) for w in s.split() if w not in FREE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    bank = Path(a.bank)
    turns = {(t["life_id"], t["turn_index"]): t for t in load(bank / "turns.jsonl")}
    truth = load(bank / "truth.jsonl")
    rows, log = load(Path(a.run)), load(Path(a.log))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # align: each row's reply is the join of one sidecar line's final parts (preflight lines are skipped)
    j, pairs = 0, []
    for r in rows:
        while j < len(log) and " ".join(p["final"] for p in log[j]["parts"] if p["final"]) != r["reply"]:
            j += 1
        if j == len(log):
            print(json.dumps({"error": "sidecar does not align with the run", "row": r["turn_index"]}))
            return 1
        pairs.append((r, log[j]))
        j += 1

    res = Counter()
    rule_raw, rule_final = set(), set()
    for i, (r, lg) in enumerate(pairs):
        raw = " ".join(p["raw"] for p in lg["parts"] if p["raw"])
        fin = r["reply"]
        for p in lg["parts"]:
            if not p["rule"]:
                res["nonrule_parts"] += 1
                res["nonrule_changed"] += p["raw"] != p["final"]
                continue
            if not p["raw"]:
                continue
            res["rule_parts"] += 1
            res["rule_parts_changed"] += p["raw"] != p["final"]
            rule_raw.add(p["raw"])
            rule_final.add(p["final"])
            if words(p["raw"]) != words(p["final"]):
                res["P360.4_word_losses"] += 1
                print("WORDS", json.dumps([p["raw"], p["final"]], ensure_ascii=False))
        if raw == fin:
            continue
        res["replies_changed"] += 1
        tidx = r["turn_index"]
        if R.is_confirm(raw) != R.is_confirm(fin):
            res["P360.3_confirm_flag"] += 1
        if R.is_confirm(fin) and R.confirm_answer(raw, truth, tidx) != R.confirm_answer(fin, truth, tidx):
            res["P360.3_confirm_answer"] += 1
        t = turns.get((r["life_id"], tidx))
        if r["kind"] == "user" and t and t["kind"] == "ask":
            conf = pairs[i + 1][0] if i + 1 < len(pairs) and pairs[i + 1][0]["kind"] == "confirm_answer" else None
            a_raw = S.score_ask(t, dict(r, reply=raw, confirm_asked=R.is_confirm(raw)), conf)
            a_fin = S.score_ask(t, r, conf)
            if a_raw != a_fin:
                res["P360.3_ask_class"] += 1
                print("ASK", tidx, a_raw, a_fin)
    for k in ("P360.3_confirm_flag", "P360.3_confirm_answer", "P360.3_ask_class", "P360.4_word_losses"):
        res.setdefault(k, 0)
    allf = sorted({r["reply"] for r in rows})
    for name, items in (("rule_raw", sorted(rule_raw)), ("rule_final", sorted(rule_final)), ("all_final", allf)):
        (out / f"{name}.jsonl").write_text("".join(json.dumps({"text": x}, ensure_ascii=False) + "\n"
                                                   for x in items), encoding="utf-8")
    res.update({"rows": len(rows), "distinct_rule_raw": len(rule_raw), "distinct_rule_final": len(rule_final),
                "distinct_all_final": len(allf)})
    res["P360.3"] = "PASS" if (res["P360.3_confirm_flag"] + res["P360.3_confirm_answer"] + res["P360.3_ask_class"]
                               + res["nonrule_changed"]) == 0 else "FAIL"
    res["P360.4"] = "PASS" if res["P360.4_word_losses"] == 0 else "FAIL"
    (out / "check.json").write_text(json.dumps(res, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(res, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
