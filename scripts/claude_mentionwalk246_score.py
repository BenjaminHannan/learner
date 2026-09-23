#!/usr/bin/env python3
"""Exp 246 runner + scorer (dev cases and the shared ask panel 243).

Subcommands (run from the repo root):
  run   --arm base228|mine --cases dev|panel --out ROWS.jsonl --work DIR
        one fresh work dir per case: setup turns, then the question turn;
        records replies, stored triples after setup / after question and
        the question turn's wall time (process_file only).
  dev   --base ROWS --mine ROWS            -> M2 verdict (exit 0 PASS, 1 FAIL)
  check                                    -> panel schema + seal check
        (SCHEMA-MISMATCH -> exit 3, no verdict; SEAL-MISMATCH -> exit 4)
  panel --base ROWS --mine ROWS            -> M1a-M1f + M5 (schema check first)

Scoring rules = askpanel243-schema.txt (identical across 245-251):
  right (ANSWER): every gold part ("A; B" -> parts) appears in the reply,
    case-insensitive, AND the reply does not start with "I don't know" /
    "I do not know".
  wrong value: the reply contains a value (3rd element) of the item's
    stated_facts that is neither a gold part nor in allowed_mentions
    (ABSTAIN items: any stated value); case-insensitive whole words.
  question write: stored triples after the question != after the setup.
  control: reply byte-identical to base228.jsonl base_reply.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ARMS = {
    "base228": ("scripts/claude_loop228_agent.py",
                "artifacts/claude-determinism228-20260922/loop228-config.json"),
    "mine": ("scripts/claude_loop246_agent.py",
             "artifacts/claude-mentionwalk246-20260922/loop246-config.json"),
}
DEV = ROOT / "artifacts/claude-mentionwalk246-20260922/dev246.jsonl"
PANEL_DIR = ROOT / "artifacts/claude-askpanel243-20260922"
MY_FAMILY = "compose"

PANEL_FIELDS = ["id", "family", "setup", "question", "twin_question", "gold",
                "expect", "stated_facts", "note", "allowed_mentions"]
BASE_FIELDS = ["id", "base_setup_replies", "stored_after_setup", "base_reply",
               "stored_after_question", "twin_reply", "base_right",
               "twin_right"]
FAMILIES = [("compose", 16), ("no_apos", 16), ("whats", 12),
            ("first_person", 12), ("verb_subject", 12), ("my_relation", 16),
            ("direction", 10), ("combo", 8), ("control", 12),
            ("untaught", 10)]
EXPECT = {"compose": "ANSWER", "no_apos": "ANSWER", "whats": "ANSWER",
          "first_person": "ANSWER", "verb_subject": "ANSWER",
          "my_relation": "ANSWER", "combo": "ANSWER",
          "direction": "ABSTAIN", "untaught": "ABSTAIN",
          "control": "UNCHANGED"}


# ------------------------------------------------------------------ helpers
def load_jsonl(path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(
        encoding="utf-8").splitlines() if line.strip()]


def gold_parts(gold) -> list[str]:
    if gold is None:
        return []
    if isinstance(gold, list):
        return [str(g).strip() for g in gold if str(g).strip()]
    return [p.strip() for p in str(gold).split(";") if p.strip()]


def is_right(reply: str, gold) -> bool:
    r = str(reply)
    if r.startswith("I don't know") or r.startswith("I do not know"):
        return False
    parts = gold_parts(gold)
    return bool(parts) and all(p.lower() in r.lower() for p in parts)


def has_word(reply: str, value: str) -> bool:
    v = str(value).strip()
    if not v:
        return False
    return re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", str(reply),
                     re.IGNORECASE) is not None


def wrong_values(reply: str, facts, gold, allowed, abstain: bool) -> list[str]:
    ok = set() if abstain else {p.lower() for p in gold_parts(gold)}
    ok |= {str(a).lower() for a in (allowed or [])}
    out = []
    for f in facts or []:
        v = str(f[2])
        if v.lower() in ok:
            continue
        if has_word(reply, v) and v not in out:
            out.append(v)
    return out


def tset(triples) -> list:
    return sorted(tuple(map(str, t)) for t in (triples or []))


# ------------------------------------------------------------------ run
def cmd_run(args) -> int:
    import fable_loop90_agent as L90
    import fable_marks123_all as M
    agent, cfg = ARMS[args.arm]
    _mod, dcls, _b, _c = M.load_agent(str(ROOT / agent))
    base_cfg = M.load_base_cfg(str(ROOT / cfg))
    cases = load_jsonl(DEV if args.cases == "dev"
                       else PANEL_DIR / "panel.jsonl")
    work = Path(args.work)
    out = []
    for i, c in enumerate(cases):
        root = work / f"c{i:03d}"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = M.make_daemon(dcls, base_cfg, root)

        def say(j, text):
            f = root / "inbox" / f"m{j:02d}.txt"
            f.write_text(text, encoding="utf-8")
            t0 = time.perf_counter()
            d.process_file(f)
            dt = time.perf_counter() - t0
            rep = (root / "outbox" / f"m{j:02d}.txt").read_text(
                encoding="utf-8").strip()
            return rep, dt

        setup_replies = [say(j, t)[0] for j, t in enumerate(c["setup"])]
        st1 = tset(L90.notebook_triples(d.loop.nb))
        reply, dt = say(len(c["setup"]), c["question"])
        st2 = tset(L90.notebook_triples(d.loop.nb))
        out.append({"id": c["id"], "arm": args.arm,
                    "setup_replies": setup_replies,
                    "stored_after_setup": st1, "reply": reply,
                    "stored_after_question": st2, "q_seconds": dt})
        shutil.rmtree(root, ignore_errors=True)
    Path(args.out).write_text("".join(json.dumps(r) + "\n" for r in out),
                              encoding="utf-8")
    print(f"ran {len(out)} {args.cases} cases on {args.arm} -> {args.out}")
    return 0


# ------------------------------------------------------------------ dev (M2)
def cmd_dev(args) -> int:
    cases = {c["id"]: c for c in load_jsonl(DEV)}
    base = {r["id"]: r for r in load_jsonl(args.base)}
    mine = {r["id"]: r for r in load_jsonl(args.mine)}
    fails, moves, n = [], [], {"cause": [0, 0], "keep": [0, 0],
                               "trap": [0, 0]}
    writes = 0
    for cid, c in cases.items():
        b, m = base[cid], mine[cid]
        facts = m["stored_after_setup"]
        # dev rule: a stored value the question itself names is an echo,
        # not a leak (e.g. the asked person is someone's spouse)
        echo = [f[2] for f in facts if has_word(c["question"], f[2])]
        w = m["stored_after_question"] != m["stored_after_setup"]
        writes += int(w)
        if c["kind"] == "cause":
            ok = is_right(m["reply"], c["gold"]) and not wrong_values(
                m["reply"], facts, c["gold"], echo, False)
        elif c["kind"] == "keep":
            ok = (m["reply"] == b["reply"] and is_right(b["reply"], c["gold"])
                  and not wrong_values(m["reply"], facts, c["gold"], echo,
                                       False))
        else:
            ok = not wrong_values(m["reply"], facts, None, echo, True)
        ok = ok and not w
        n[c["kind"]][0] += int(ok)
        n[c["kind"]][1] += 1
        if m["reply"] != b["reply"]:
            moves.append(f"{cid} [{c['kind']}] {c['question']!r}: "
                         f"{b['reply'][:70]!r} -> {m['reply'][:70]!r}")
        if not ok:
            fails.append(f"{cid} [{c['kind']}] {c['question']!r} -> "
                         f"{m['reply']!r} write={w}")
    for k, (a, t) in n.items():
        print(f"M2 {k}: {a}/{t}")
    print(f"M2 question writes: {writes}")
    print(f"moves vs base228 ({len(moves)}):")
    for x in moves:
        print("  " + x)
    print(f"misses ({len(fails)}):")
    for x in fails:
        print("  " + x)
    ok = not fails and writes == 0
    print("M2:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ------------------------------------------------------------------ schema
def schema_errors() -> list[str]:
    errs = []
    for fn in ("panel.jsonl", "base228.jsonl", "README.md",
               "SEAL.sha256.txt"):
        if not (PANEL_DIR / fn).exists():
            errs.append(f"missing file {fn}")
    if errs:
        return errs
    try:
        panel = load_jsonl(PANEL_DIR / "panel.jsonl")
        base = load_jsonl(PANEL_DIR / "base228.jsonl")
    except Exception as exc:  # noqa: BLE001
        return [f"unreadable jsonl: {exc}"]
    if len(panel) != 124 or len(base) != 124:
        errs.append(f"line counts panel={len(panel)} base={len(base)}")
    for r in panel:
        if sorted(r) != sorted(PANEL_FIELDS):
            errs.append(f"panel fields {r.get('id')}: {sorted(r)}")
    for r in base:
        if sorted(r) != sorted(BASE_FIELDS):
            errs.append(f"base fields {r.get('id')}: {sorted(r)}")
    if errs:
        return errs
    want_ids = [f"q243-{i:03d}" for i in range(1, 125)]
    if [r["id"] for r in panel] != want_ids:
        errs.append("panel ids not q243-001..124 in order")
    if [r["id"] for r in base] != [r["id"] for r in panel]:
        errs.append("base228 ids do not match panel ids/order")
    order = [f for f, k in FAMILIES for _ in range(k)]
    fams = [r["family"] for r in panel]
    if fams != order:
        bad = sorted(set(fams) - set(EXPECT))
        errs.append(f"family blocks/counts differ (unknown={bad})")
    for r in panel:
        fam = r["family"]
        if fam not in EXPECT:
            continue
        if r["expect"] != EXPECT[fam]:
            errs.append(f"{r['id']} expect {r['expect']!r} for {fam}")
        if not (isinstance(r["setup"], list) and r["setup"]
                and all(isinstance(s, str) for s in r["setup"])):
            errs.append(f"{r['id']} setup not a non-empty list of strings")
        if not (isinstance(r["question"], str)
                and r["question"].rstrip().endswith("?")):
            errs.append(f"{r['id']} question not a '?' string")
        if fam in ("direction", "control", "untaught"):
            if r["twin_question"] is not None:
                errs.append(f"{r['id']} twin_question must be null")
        elif not isinstance(r["twin_question"], str):
            errs.append(f"{r['id']} twin_question must be a string")
        if fam in ("direction", "untaught"):
            if r["gold"] is not None:
                errs.append(f"{r['id']} gold must be null")
            if r["allowed_mentions"] != []:
                errs.append(f"{r['id']} allowed_mentions must be []")
        elif not isinstance(r["gold"], str):
            errs.append(f"{r['id']} gold must be a string")
        if not isinstance(r["stated_facts"], list) or not all(
                isinstance(t, list) and len(t) == 3
                for t in r["stated_facts"]):
            errs.append(f"{r['id']} stated_facts not [s,r,v] triples")
        if not isinstance(r["allowed_mentions"], list):
            errs.append(f"{r['id']} allowed_mentions not a list")
    for r in base:
        if not isinstance(r["base_right"], bool):
            errs.append(f"{r['id']} base_right not bool")
        if not isinstance(r["base_reply"], str):
            errs.append(f"{r['id']} base_reply not a string")
    return errs


def seal_ok() -> tuple[bool, str]:
    lines = (PANEL_DIR / "SEAL.sha256.txt").read_text(
        encoding="utf-8").splitlines()
    seen = 0
    for line in lines:
        if not line.strip():
            continue
        h, p = line.split(None, 1)
        p = p.lstrip("*").strip()
        got = hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        if got != h:
            return False, f"{p}: sha mismatch"
        seen += 1
    return seen >= 2, f"{seen} files OK"


def cmd_check(_args) -> int:
    errs = schema_errors()
    if errs:
        print("SCHEMA-MISMATCH")
        for e in errs[:40]:
            print("  " + e)
        return 3
    ok, msg = seal_ok()
    if not ok:
        print("SEAL-MISMATCH " + msg)
        return 4
    print(f"schema OK; seal {msg}")
    return 0


# ------------------------------------------------------------------ panel
def cmd_panel(args) -> int:
    rc = cmd_check(args)
    if rc:
        return rc
    panel = load_jsonl(PANEL_DIR / "panel.jsonl")
    ref = {r["id"]: r for r in load_jsonl(PANEL_DIR / "base228.jsonl")}
    base = {r["id"]: r for r in load_jsonl(args.base)}
    mine = {r["id"]: r for r in load_jsonl(args.mine)}
    fam_right = {}
    wrong, writes, ctrl_same, other_bad, untaught_ok = [], [], 0, [], 0
    dir_new_leak, dir_old_leak, combo, moves = [], [], [], []
    rerun_diff = []
    for p in panel:
        pid, fam = p["id"], p["family"]
        m, b, rf = mine[pid], base[pid], ref[pid]
        abstain = p["expect"] == "ABSTAIN"
        right = is_right(m["reply"], p["gold"]) if p["expect"] == "ANSWER" \
            else None
        wv = wrong_values(m["reply"], p["stated_facts"], p["gold"],
                          p["allowed_mentions"], abstain)
        base_wv = wrong_values(rf["base_reply"], p["stated_facts"], p["gold"],
                               p["allowed_mentions"], abstain)
        if m["reply"] != rf["base_reply"]:
            moves.append(f"{pid} [{fam}] {p['question']!r}: "
                         f"{rf['base_reply'][:60]!r} -> {m['reply'][:80]!r}")
        if b["reply"] != rf["base_reply"]:
            rerun_diff.append(pid)
        if fam == "direction" and wv and base_wv:
            dir_old_leak.append(f"{pid} {wv} (base228 {base_wv})")
            new_part = [v for v in wv if v not in base_wv]
            if new_part:
                wrong.append(f"{pid} {new_part}")
                dir_new_leak.append(f"{pid} {new_part}")
        elif wv:
            wrong.append(f"{pid} [{fam}] {wv}: {m['reply'][:80]!r}")
            if fam == "direction":
                dir_new_leak.append(f"{pid} {wv}")
        if m["stored_after_question"] != m["stored_after_setup"]:
            writes.append(pid)
        if p["expect"] == "ANSWER":
            fam_right.setdefault(fam, [0, 0])
            fam_right[fam][0] += int(bool(right) and not wv)
            fam_right[fam][1] += 1
        if fam == "control":
            ctrl_same += int(m["reply"] == rf["base_reply"])
        if fam == "untaught":
            untaught_ok += int(not wv)
        if fam == "combo":
            combo.append(f"{pid} right={right} wrong={wv} "
                         f"{p['question']!r} -> {m['reply'][:80]!r}")
        if (fam not in (MY_FAMILY, "combo", "control", "direction",
                        "untaught") and rf["base_right"]
                and not (right and not wv)):
            other_bad.append(f"{pid} [{fam}] {m['reply'][:80]!r}")
    a, t = fam_right.get(MY_FAMILY, [0, 0])
    m1a = t > 0 and a * 10 >= 9 * t
    diffs = [mine[p["id"]]["q_seconds"] - base[p["id"]]["q_seconds"]
             for p in panel]
    med_ms = statistics.median(diffs) * 1000.0
    med_mine = statistics.median(mine[p["id"]]["q_seconds"]
                                 for p in panel) * 1000.0
    med_base = statistics.median(base[p["id"]]["q_seconds"]
                                 for p in panel) * 1000.0
    marks = [
        ("M1a", f"{MY_FAMILY} right {a}/{t} (bar >= 90%)", m1a),
        ("M1b", f"wrong values {len(wrong)} (bar 0)", not wrong),
        ("M1c", f"question writes {len(writes)} (bar 0)", not writes),
        ("M1d", f"control byte-identical {ctrl_same}/12", ctrl_same == 12),
        ("M1e", f"other-family losses {len(other_bad)}, untaught "
                f"{untaught_ok}/10, new direction leaks {len(dir_new_leak)}",
         not other_bad and untaught_ok == 10 and not dir_new_leak),
        ("M5", f"median added q time {med_ms:+.2f} ms (mine {med_mine:.2f},"
               f" base {med_base:.2f}; bar <= +5)", med_ms <= 5.0),
    ]
    for k, msg, ok in marks:
        print(f"{k}: {'PASS' if ok else 'FAIL'}  {msg}")
    print("per family right (ANSWER families):",
          {k: f"{v[0]}/{v[1]}" for k, v in fam_right.items()})
    print(f"M1f combo (no bar, {len(combo)}):")
    for x in combo:
        print("  " + x)
    for title, xs in (("wrong values", wrong), ("question writes", writes),
                      ("other-family losses", other_bad),
                      ("direction leaks already in base228", dir_old_leak),
                      ("new direction leaks", dir_new_leak),
                      ("moves vs base228.jsonl", moves),
                      ("same-session base228 rerun != base228.jsonl",
                       rerun_diff)):
        print(f"{title} ({len(xs)}):")
        for x in xs:
            print("  " + str(x))
    allok = all(ok for _, _, ok in marks)
    print("PANEL:", "PASS" if allok else "FAIL")
    return 0 if allok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--arm", choices=sorted(ARMS), required=True)
    r.add_argument("--cases", choices=["dev", "panel"], required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--work", required=True)
    d = sub.add_parser("dev")
    d.add_argument("--base", required=True)
    d.add_argument("--mine", required=True)
    sub.add_parser("check")
    p = sub.add_parser("panel")
    p.add_argument("--base", required=True)
    p.add_argument("--mine", required=True)
    args = ap.parse_args(argv)
    return {"run": cmd_run, "dev": cmd_dev, "check": cmd_check,
            "panel": cmd_panel}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
