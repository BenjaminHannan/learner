#!/usr/bin/env python3
"""gram-364 mechanical checks (P364.3, P364.4) and the grading sets (P364.1, P364.2).

  python -B scripts/claude_gram364_check.py --bank BANK --run RUN/arm_P364.jsonl --log RUN/gram364_parts.jsonl \
      --out OUT

The run is one arm, P364 (330c + finisher v2), with the sidecar of every part (raw and final). gram-360's
rendering of the same raw parts is computed here with claude_gram360.realise and the same "seen" names (rebuilt per
life from the user's text in turn order, as install_gram360 does), so the comparison is paired: same parts, two
renderers. Checks, as gram-360's checker:
  P364.3  v2 rendering changes no score: is_confirm, the harness's confirm answer and the 336 ask class are the
          same on the raw reply and on the final reply; every part the rule agent did not produce is byte-identical.
  P364.4  no slot word lost between each raw part and its v2 rendering (words the renderer may add or swap set
          aside, now also "note", "about", "say(s)", "the").
Writes OUT/rule_raw.jsonl, OUT/rule_final360.jsonl, OUT/rule_final364.jsonl (distinct rule-agent parts),
OUT/all_final.jsonl (distinct whole replies, report only) and OUT/check.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_e2e336_run as R  # noqa: E402
import claude_e2e336_score as S  # noqa: E402
import claude_gram360 as G  # noqa: E402
import claude_gram360_check as C360  # noqa: E402

C360.FREE |= {"note", "about", "say", "says", "the"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    bank = Path(a.bank)
    turns = {(t["life_id"], t["turn_index"]): t for t in C360.load(bank / "turns.jsonl")}
    truth = C360.load(bank / "truth.jsonl")
    rows, log = C360.load(Path(a.run)), C360.load(Path(a.log))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    seen_by_dir: dict[str, set] = {}
    for lg in log:                                   # the names seen before each turn is rendered, per life
        s = seen_by_dir.setdefault(lg["dir"], set())
        s.update(G.names_seen(lg["text"]))
        lg["seen"] = set(s)

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
    rule_raw, f360, f364 = set(), set(), set()
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
            v360 = G.realise(p["raw"], lg["seen"])
            res["rule_parts_changed"] += p["raw"] != p["final"]
            res["rule_parts_differ_from_360"] += v360 != p["final"]
            rule_raw.add(p["raw"])
            f360.add(v360)
            f364.add(p["final"])
            if C360.words(p["raw"]) != C360.words(p["final"]):
                res["P364.4_word_losses"] += 1
                print("WORDS", json.dumps([p["raw"], p["final"]], ensure_ascii=False))
        if raw == fin:
            continue
        res["replies_changed"] += 1
        tidx = r["turn_index"]
        if R.is_confirm(raw) != R.is_confirm(fin):
            res["P364.3_confirm_flag"] += 1
        if R.is_confirm(fin) and R.confirm_answer(raw, truth, tidx) != R.confirm_answer(fin, truth, tidx):
            res["P364.3_confirm_answer"] += 1
        t = turns.get((r["life_id"], tidx))
        if r["kind"] == "user" and t and t["kind"] == "ask":
            conf = pairs[i + 1][0] if i + 1 < len(pairs) and pairs[i + 1][0]["kind"] == "confirm_answer" else None
            a_raw = S.score_ask(t, dict(r, reply=raw, confirm_asked=R.is_confirm(raw)), conf)
            a_fin = S.score_ask(t, r, conf)
            if a_raw != a_fin:
                res["P364.3_ask_class"] += 1
                print("ASK", tidx, a_raw, a_fin)
    for k in ("P364.3_confirm_flag", "P364.3_confirm_answer", "P364.3_ask_class", "P364.4_word_losses"):
        res.setdefault(k, 0)
    allf = sorted({r["reply"] for r in rows})
    for name, items in (("rule_raw", rule_raw), ("rule_final360", f360), ("rule_final364", f364), ("all_final", allf)):
        (out / f"{name}.jsonl").write_text("".join(json.dumps({"text": x}, ensure_ascii=False) + "\n"
                                                   for x in sorted(items)), encoding="utf-8")
    res.update({"rows": len(rows), "distinct_rule_raw": len(rule_raw), "distinct_rule_final360": len(f360),
                "distinct_rule_final364": len(f364), "distinct_all_final": len(allf)})
    res["P364.3"] = "PASS" if (res["P364.3_confirm_flag"] + res["P364.3_confirm_answer"] + res["P364.3_ask_class"]
                               + res["nonrule_changed"]) == 0 else "FAIL"
    res["P364.4"] = "PASS" if res["P364.4_word_losses"] == 0 else "FAIL"
    (out / "check.json").write_text(json.dumps(res, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(res, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
