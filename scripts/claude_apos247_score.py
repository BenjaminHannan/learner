"""Exp 247 scorer: panel schema check + scoring rules (askpanel243 schema),
and the dev-case scoring.

  python scripts/claude_apos247_score.py check --panel-dir DIR
  python scripts/claude_apos247_score.py panel --panel-dir DIR --rows ROWS [--out F]
  python scripts/claude_apos247_score.py dev --rows ROWS [--out F]

Schema mismatch -> prints SCHEMA-MISMATCH and exits 3 (VOID, no verdict).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

PANEL_FIELDS = ["id", "family", "setup", "question", "twin_question", "gold",
                "expect", "stated_facts", "note", "allowed_mentions"]
BASE_FIELDS = ["id", "base_setup_replies", "stored_after_setup", "base_reply",
               "stored_after_question", "twin_reply", "base_right",
               "twin_right"]
FAMILY_COUNTS = {"compose": 16, "no_apos": 16, "whats": 12,
                 "first_person": 12, "verb_subject": 12, "my_relation": 16,
                 "direction": 10, "combo": 8, "control": 12, "untaught": 10}
FAMILY_ORDER = list(FAMILY_COUNTS)
EXPECT = {f: "ANSWER" for f in ("compose", "no_apos", "whats", "first_person",
                                "verb_subject", "my_relation", "combo")}
EXPECT.update({"direction": "ABSTAIN", "untaught": "ABSTAIN",
               "control": "UNCHANGED"})
MY_FAMILY = "no_apos"
DECLINE_STARTS = ("i don't know", "i do not know", "i don’t know")


def mismatch(msg: str):
    print("SCHEMA-MISMATCH: " + msg)
    sys.exit(3)


def _load_jsonl(path: Path, label: str) -> list:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            mismatch(f"{label}: blank line {n}")
        try:
            rows.append(json.loads(line))
        except Exception as exc:
            mismatch(f"{label}: line {n} not JSON ({exc})")
    return rows


def schema_check(panel_dir) -> tuple[list, list]:
    d = Path(panel_dir)
    for name in ("panel.jsonl", "base228.jsonl", "README.md",
                 "SEAL.sha256.txt"):
        if not (d / name).is_file():
            mismatch(f"missing file {name}")
    panel = _load_jsonl(d / "panel.jsonl", "panel.jsonl")
    base = _load_jsonl(d / "base228.jsonl", "base228.jsonl")
    if len(panel) != 124 or len(base) != 124:
        mismatch(f"line counts panel={len(panel)} base={len(base)} (want 124)")
    for i, r in enumerate(panel):
        if not isinstance(r, dict) or sorted(r) != sorted(PANEL_FIELDS):
            mismatch(f"panel line {i+1} fields {sorted(r) if isinstance(r, dict) else r}")
        if r["id"] != "q243-%03d" % (i + 1):
            mismatch(f"panel line {i+1} id {r['id']!r}")
        fam = r["family"]
        if fam not in FAMILY_COUNTS:
            mismatch(f"{r['id']} unknown family {fam!r}")
        if r["expect"] != EXPECT[fam]:
            mismatch(f"{r['id']} expect {r['expect']!r} for {fam}")
        if not isinstance(r["setup"], list) or not r["setup"] or \
                not all(isinstance(s, str) for s in r["setup"]):
            mismatch(f"{r['id']} setup")
        if not isinstance(r["question"], str) or \
                not r["question"].rstrip().endswith("?"):
            mismatch(f"{r['id']} question")
        if fam in ("direction", "control", "untaught"):
            if r["twin_question"] is not None:
                mismatch(f"{r['id']} twin_question must be null")
        elif not isinstance(r["twin_question"], str):
            mismatch(f"{r['id']} twin_question must be a string")
        if fam in ("direction", "untaught"):
            if r["gold"] is not None:
                mismatch(f"{r['id']} gold must be null")
            if r["allowed_mentions"] != []:
                mismatch(f"{r['id']} allowed_mentions must be []")
        elif not isinstance(r["gold"], str) or not r["gold"].strip():
            mismatch(f"{r['id']} gold must be a string")
        if not isinstance(r["stated_facts"], list) or not all(
                isinstance(t, list) and len(t) == 3 for t in r["stated_facts"]):
            mismatch(f"{r['id']} stated_facts")
        if not isinstance(r["allowed_mentions"], list) or not all(
                isinstance(a, str) for a in r["allowed_mentions"]):
            mismatch(f"{r['id']} allowed_mentions")
        if not isinstance(r["note"], str):
            mismatch(f"{r['id']} note")
    got = Counter(r["family"] for r in panel)
    if dict(got) != FAMILY_COUNTS:
        mismatch(f"family counts {dict(got)}")
    order = [r["family"] for r in panel]
    blocks = [f for i, f in enumerate(order) if i == 0 or order[i - 1] != f]
    if blocks != FAMILY_ORDER:
        mismatch(f"family block order {blocks}")
    for i, (p, b) in enumerate(zip(panel, base)):
        if not isinstance(b, dict) or sorted(b) != sorted(BASE_FIELDS):
            mismatch(f"base228 line {i+1} fields")
        if b["id"] != p["id"]:
            mismatch(f"base228 line {i+1} id {b['id']!r} != {p['id']!r}")
        if not isinstance(b["base_right"], bool):
            mismatch(f"{b['id']} base_right not bool")
        if p["twin_question"] is None:
            if b["twin_reply"] is not None or b["twin_right"] is not None:
                mismatch(f"{b['id']} twin fields must be null")
        elif not isinstance(b["twin_right"], bool):
            mismatch(f"{b['id']} twin_right not bool")
        if not isinstance(b["base_reply"], str):
            mismatch(f"{b['id']} base_reply")
    return panel, base


# ------------------------------------------------------------ rules
def gold_parts(gold) -> list[str]:
    if gold is None:
        return []
    return [g.strip() for g in str(gold).split(";") if g.strip()]


def has_word(reply: str, value: str) -> bool:
    v = str(value).strip()
    if not v:
        return False
    pat = r"(?<![A-Za-z0-9])" + re.escape(v) + r"(?![A-Za-z0-9])"
    return re.search(pat, reply, re.IGNORECASE) is not None


def is_decline(reply: str) -> bool:
    return reply.strip().lower().startswith(DECLINE_STARTS)


def right_answer(reply: str, gold) -> bool:
    parts = gold_parts(gold)
    return bool(parts) and all(p.lower() in reply.lower() for p in parts) \
        and not is_decline(reply)


def wrong_values(reply: str, values, gold, allowed, abstain: bool) -> list:
    ok = set() if abstain else {g.lower() for g in gold_parts(gold)}
    ok |= set() if abstain else {a.lower() for a in allowed}
    out = []
    for v in values:
        if str(v).lower() in ok:
            continue
        if has_word(reply, v):
            out.append(v)
    return sorted(set(out))


def wrote(row) -> bool:
    a = sorted(tuple(t) for t in row["stored_after_setup"])
    b = sorted(tuple(t) for t in row["stored_after_question"])
    return a != b


# ------------------------------------------------------------ panel
def score_panel(panel_dir, rows_path, out=None) -> int:
    panel, base = schema_check(panel_dir)
    rows = {}
    for line in Path(rows_path).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        rows[(r["id"], r["arm"])] = r
    lines = []
    tot = Counter()
    fam = defaultdict(Counter)
    moves = []
    leaks_base = []
    dt = []
    for p, b in zip(panel, base):
        mine = rows.get((p["id"], "mine"))
        fresh = rows.get((p["id"], "base228"))
        if mine is None or fresh is None:
            print(f"MISSING ROW {p['id']}")
            return 2
        reply = mine["reply"]
        f = p["family"]
        values = [t[2] for t in p["stated_facts"]]
        abstain = p["expect"] == "ABSTAIN"
        wv = wrong_values(reply, values, p["gold"], p["allowed_mentions"], abstain)
        qw = wrote(mine)
        tot["items"] += 1
        tot["wrong_value_items"] += bool(wv)
        tot["question_writes"] += qw
        tot["fresh_base_matches_file"] += (fresh["reply"] == b["base_reply"])
        dt.append(mine["q_seconds"] - fresh["q_seconds"])
        if p["expect"] == "ANSWER":
            ok = right_answer(reply, p["gold"])
        elif p["expect"] == "ABSTAIN":
            ok = not wv
        else:
            ok = reply == b["base_reply"]
        fam[f]["n"] += 1
        fam[f]["right"] += ok
        fam[f]["wrong_value"] += bool(wv)
        fam[f]["writes"] += qw
        changed = reply != b["base_reply"]
        fam[f]["changed_vs_base"] += changed
        if f == "direction" and not b["base_right"]:
            leaks_base.append(p["id"])
        rec = {"id": p["id"], "family": f, "question": p["question"],
               "gold": p["gold"], "right": ok, "base_right": b["base_right"],
               "wrong_values": wv, "question_write": qw,
               "changed_vs_base": changed, "reply": reply,
               "base_reply": b["base_reply"]}
        if changed or ok != b["base_right"]:
            moves.append(rec)
        # M1e: other families base_right true -> wrong or decline
        rec["m1e_regress"] = bool(
            f not in (MY_FAMILY, "combo") and b["base_right"] and
            (not ok or (p["expect"] == "ANSWER" and is_decline(reply))))
        rec["new_leak"] = bool(f == "direction" and b["base_right"] and wv)
        lines.append(rec)
    my = fam[MY_FAMILY]
    m1a_bar = -(-9 * my["n"] // 10)
    marks = {
        "M1a": (my["right"], my["n"], my["right"] >= m1a_bar),
        "M1b": (tot["wrong_value_items"], 124, tot["wrong_value_items"] == 0),
        "M1c": (tot["question_writes"], 124, tot["question_writes"] == 0),
        "M1d": (fam["control"]["right"], fam["control"]["n"],
                fam["control"]["right"] == fam["control"]["n"]),
    }
    regress = [r["id"] for r in lines if r["m1e_regress"]]
    new_leaks = [r["id"] for r in lines if r["new_leak"]]
    unt = fam["untaught"]
    marks["M1e"] = (len(regress) + len(new_leaks), 0,
                    not regress and not new_leaks and unt["right"] == unt["n"])
    med = statistics.median(dt) * 1000.0
    marks["M5"] = (round(med, 2), 5.0, med <= 5.0)
    print("family table (right / n, wrong-value items, question writes, "
          "changed vs base228 file):")
    for f in FAMILY_ORDER:
        c = fam[f]
        print(f"  {f:13s} {c['right']:3d}/{c['n']:<3d} wv={c['wrong_value']} "
              f"w={c['writes']} changed={c['changed_vs_base']}")
    print("fresh base228 reply == base228.jsonl base_reply:",
          tot["fresh_base_matches_file"], "/ 124")
    print("M1e regressions:", regress, "new direction leaks:", new_leaks,
          "base228 direction leaks (listed, not counted):", leaks_base)
    print("combo items (M1f, no bar):")
    for r in lines:
        if r["family"] == "combo":
            print(f"  {r['id']} right={r['right']} wv={r['wrong_values']} "
                  f"{r['question']!r} -> {r['reply'][:120]!r}")
    for k, (a, b2, ok) in marks.items():
        print(f"{k}: {a} / {b2} -> {'PASS' if ok else 'FAIL'}")
    verdict = all(ok for _a, _b, ok in marks.values())
    print("PANEL VERDICT:", "PASS" if verdict else "FAIL")
    if out:
        Path(out).write_text(json.dumps(
            {"marks": marks, "families": {k: dict(v) for k, v in fam.items()},
             "moves": moves, "regress": regress, "new_leaks": new_leaks,
             "base_direction_leaks": leaks_base, "median_added_ms": med,
             "items": lines}, indent=1), encoding="utf-8")
    return 0 if verdict else 1


# ------------------------------------------------------------ dev
def score_dev(rows_path, out=None) -> int:
    rows = defaultdict(dict)
    for line in Path(rows_path).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        rows[r["id"]][r["arm"]] = r
    cnt = defaultdict(Counter)
    items = []
    setup_diff = 0
    for cid in sorted(rows):
        mine, base = rows[cid]["mine"], rows[cid]["base228"]
        f = mine["family"]
        reply = mine["reply"]
        values = sorted({t[2] for t in mine["stored_after_setup"]})
        gold = mine.get("gold")
        allowed = mine.get("allowed_mentions", [])
        qw = wrote(mine)
        setup_diff += mine["setup_replies"] != base["setup_replies"]
        if f == "fix":
            wv = wrong_values(reply, values, gold, allowed, False)
            ok = right_answer(reply, gold) and not wv and not qw
        elif f == "keep":
            wv = wrong_values(reply, values, gold, allowed, gold is None)
            ok = reply == base["reply"] and not qw
        elif f == "trap":
            wv = [v for v in wrong_values(reply, values, None, [], True)
                  if v.lower() not in {a.lower() for a in allowed}]
            ok = not wv and not qw
        else:  # outside
            wv = wrong_values(reply, values, gold, allowed, False)
            ok = not wv and not qw
        cnt[f]["n"] += 1
        cnt[f]["ok"] += ok
        cnt[f]["writes"] += qw
        cnt[f]["wv"] += bool(wv)
        cnt[f]["base_right"] += (right_answer(base["reply"], gold)
                                 if f in ("fix", "outside") else 0)
        items.append({"id": cid, "family": f, "ok": ok, "wv": wv, "write": qw,
                      "question": mine["question"], "reply": reply,
                      "base_reply": base["reply"]})
        print(f"{cid} {f:7s} {'OK ' if ok else 'BAD'} {mine['question']!r} -> "
              f"{reply[:90]!r}" + (f"  WV={wv}" if wv else "")
              + ("  WRITE" if qw else ""))
    for f in ("fix", "keep", "trap", "outside"):
        c = cnt[f]
        extra = f" (base228 right {c['base_right']})" if f in ("fix", "outside") else ""
        print(f"{f:7s} ok {c['ok']}/{c['n']} writes={c['writes']} "
              f"wrong-value={c['wv']}{extra}")
    print("setup replies differing between arms:", setup_diff)
    ok = all(cnt[f]["ok"] == cnt[f]["n"] for f in ("fix", "keep", "trap",
                                                    "outside")) \
        and setup_diff == 0
    print("DEV VERDICT (M2):", "PASS" if ok else "FAIL")
    if out:
        Path(out).write_text(json.dumps({"counts": {k: dict(v) for k, v in cnt.items()},
                                         "items": items}, indent=1),
                             encoding="utf-8")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["check", "panel", "dev"])
    ap.add_argument("--panel-dir", default="artifacts/claude-askpanel243-20260922")
    ap.add_argument("--rows")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.mode == "check":
        schema_check(a.panel_dir)
        print("SCHEMA OK")
        return 0
    if a.mode == "panel":
        return score_panel(a.panel_dir, a.rows, a.out)
    return score_dev(a.rows, a.out)


if __name__ == "__main__":
    sys.exit(main())
