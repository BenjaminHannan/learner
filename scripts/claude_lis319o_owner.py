#!/usr/bin/env python3
"""lis-319o: the compiler accepts an owner named earlier in the chat (reading thread, 2026-09-26). One change, no retraining.

Why: lis-319k's diagnosis (artifacts/claude-lis319k-20260926/VERIFY.md) found that 16 of 60 corrections the lis-319 reader
read were thrown out by claude_lis300_compiler.check_fact as owner_not_span. A correction often names its owner earlier
("Wren is 12" ... "sorry, she's 13"), and the check only looks in this turn and the assistant's previous reply.
The change: when check_fact says owner_not_span and the owner occurs as whole words in the row's history (the earlier user
turns and replies the reader was shown), the fact is checked on as usual: value in the turn and owner != value. Every
other check is unchanged. The owner still has to be written in the chat, character for character.

pairs / final: same as claude_lis319k_score.py (T 0.995), with the patched check; --rows gives each row's history
          (claude_lis319_rows.py output). Prints counts only.
dev:      python claude_lis319o_owner.py dev --dev DEV.jsonl --pred PRED.jsonl   (lis-319 dev rows; history from the prompt)
selftest: python claude_lis319o_owner.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis300_compiler as CMP  # noqa: E402
from claude_lis319_fullclaim import load  # noqa: E402

ORIG = CMP.check_fact


def hist_text(history):
    return "\n".join(str(x) for pair in (history or []) for x in pair)


def check_fact_hist(f, turn, prev, hist):
    r = ORIG(f, turn, prev)
    if r != "owner_not_span" or not CMP.whole_word_span(str(f.get("owner", "")), hist or ""):
        return r
    val = str(f.get("value", ""))
    asked = (prev or "").strip().endswith("?")
    if not (CMP.whole_word_span(val, turn) or (asked and CMP.whole_word_span(val, prev))):
        return "value_not_span"
    if str(f.get("owner", "")).strip().lower() == val.strip().lower():
        return "owner_equals_value"
    return None


def patch(rows):
    ctx = {}
    for r in rows:
        ctx.setdefault((r["turn"], r.get("prev_reply", "")), hist_text(r.get("history")))
    CMP.check_fact = lambda f, turn, prev: check_fact_hist(f, turn, prev, ctx.get((turn, prev or ""), ""))
    return len(ctx)


def run_k(a, cmd):
    rows = load(a.rows)
    patch(rows)
    import claude_lis319k_score as K
    if cmd != "final":
        return getattr(K, cmd)(a)
    res = K.score(load(a.panel), load(a.reads), load(a.pairs), [load(v) for v in a.verdicts])
    res |= admitted(load(a.panel), rows, load(a.reads), load(a.pairs), [load(v) for v in a.verdicts])
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res))


def admitted(panel, rows, reads, pair_rows, verdicts):
    """O4: saves the change admits (the old check says owner_not_span) and whether the judges credit them.
    wrong = no exact gold match and no pair both judges call same; wrong_owner = of those, a gold fact of the row has the
    same relation and value but another owner; on_ambiguous = admitted saves on lookalike rows with reason "ambiguous"."""
    from claude_lis319_fullclaim import key
    from claude_lis319_fullclaim_b import exact_b
    from claude_lis317_gates import n
    hist = {r["id"]: hist_text(r.get("history")) for r in rows}
    pid = {key(x["id"], x["saved"], x["gold"]): x["pid"] for x in pair_rows}
    same = {p for p in pid.values() if all({int(v["pid"]): bool(v["same"]) for v in vs}[p] for vs in verdicts)}
    rd = {r["id"]: r for r in reads}
    c = Counter({"admitted_saves": 0, "admitted_wrong": 0, "admitted_wrong_owner": 0, "admitted_on_ambiguous": 0})
    for row in panel:
        r = rd.get(row["id"])
        facts = [x for x in (((r or {}).get("frame") or {}).get("facts") or []) if isinstance(x, dict)]
        confs = (r or {}).get("conf") or []
        for i, f in enumerate(facts):
            if (confs[i] if i < len(confs) else 0.0) < 0.995:
                continue
            if ORIG(f, row["turn"], row.get("prev_reply", "")) != "owner_not_span":
                continue
            if check_fact_hist(f, row["turn"], row.get("prev_reply", ""), hist.get(row["id"], "")) is not None:
                continue
            c["admitted_saves"] += 1
            c["admitted_on_ambiguous"] += row.get("reason") == "ambiguous"
            gold = row.get("facts") or []
            ok = any(exact_b(f, g) for g in gold) or any(pid.get(key(row["id"], f, g)) in same for g in gold)
            if not ok:
                c["admitted_wrong"] += 1
                c["admitted_wrong_owner"] += any(g.get("relation", g.get("rel")) == f.get("rel")
                                                 and n(g["value"]) == n(f.get("value")) for g in gold)
    return dict(c)


def dev(a):
    rows = {r["id"]: r for r in load(a.dev)}
    c = Counter()
    for p in load(a.pred):
        r = rows.get(p["id"])
        if r is None:
            continue
        pr = r["prompt"]
        hist = pr.split("Earlier chat:\n", 1)[-1].split("\nAssistant said:", 1)[0] if "Earlier chat:" in pr else ""
        gold = [g for g in ((r.get("frame") or {}).get("facts") or []) if isinstance(g, dict)]
        facts = [x for x in (((p.get("frame") or {}).get("facts")) or []) if isinstance(x, dict)]
        confs = p.get("conf") or []
        for i, f in enumerate(facts):
            if ORIG(f, r["turn"], r.get("prev_reply", "")) != "owner_not_span":
                continue
            c["owner_not_span"] += 1
            if check_fact_hist(f, r["turn"], r.get("prev_reply", ""), hist) is not None:
                continue
            c["now_ok"] += 1
            if (confs[i] if i < len(confs) else 0.0) < 0.995:
                continue
            ok = any(str(g.get("owner", "")).lower() == str(f.get("owner", "")).lower() and g.get("rel") == f.get("rel")
                     and str(g.get("value", "")).lower() == str(f.get("value", "")).lower() for g in gold)
            c["new_saves_exact_gold" if ok else "new_saves_not_exact_gold"] += 1
            c[f"new_saves_mode:{f.get('mode')}"] += 1
    print(json.dumps(dict(sorted(c.items()))))


def selftest(_a):
    h = hist_text([["my niece Wren is 12", "Nice!"]])
    cases = [
        ({"owner": "Wren", "rel": "age", "value": "13", "mode": "CORRECT"}, "sorry, she's 13", "", h, None),
        ({"owner": "Wren", "rel": "age", "value": "13", "mode": "CORRECT"}, "sorry, she's 13", "", "", "owner_not_span"),
        ({"owner": "Tamsin", "rel": "age", "value": "13", "mode": "CORRECT"}, "sorry, she's 13", "", h, "owner_not_span"),
        ({"owner": "Wren", "rel": "age", "value": "14", "mode": "CORRECT"}, "sorry, she's 13", "", h, "value_not_span"),
        ({"owner": "Wren", "rel": "age", "value": "13", "mode": "CHECK"}, "is she 13?", "", h, "mode:CHECK"),
        ({"owner": "wren", "rel": "age", "value": "13", "mode": "CORRECT"}, "sorry, she's 13", "", h, "owner_not_span"),
    ]
    ok = [check_fact_hist(f, t, p, hh) == want for f, t, p, hh, want in cases]
    for (f, t, _p, _h, want), g in zip(cases, ok):
        print(("PASS " if g else "FAIL ") + f"{f['owner']}/{f['value']}/{f['mode']} -> {want}")
    n = patch([{"turn": "sorry, she's 13", "prev_reply": "", "history": [["my niece Wren is 12", "Nice!"]]}])
    ok.append(n == 1 and CMP.check_fact(cases[0][0], "sorry, she's 13", "") is None)
    CMP.check_fact = ORIG
    print("LIS319O-SELFTEST " + ("PASS" if all(ok) else "FAIL"))
    return 0 if all(ok) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pairs", "final", "dev", "selftest"])
    ap.add_argument("--panel")
    ap.add_argument("--rows")
    ap.add_argument("--reads")
    ap.add_argument("--pairs")
    ap.add_argument("--verdicts", action="append", default=[])
    ap.add_argument("--dev")
    ap.add_argument("--pred")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd in ("pairs", "final"):
        return run_k(a, a.cmd) or 0
    return {"dev": dev, "selftest": selftest}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
