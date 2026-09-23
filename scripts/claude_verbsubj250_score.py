#!/usr/bin/env python3
"""Exp 250 runner + scorer (dev cases and the shared ask panel 243).

  dev   : python -B scripts/claude_verbsubj250_score.py dev --out DIR
  schema: python -B scripts/claude_verbsubj250_score.py schema
  panel : python -B scripts/claude_verbsubj250_score.py panel --out DIR

Both arms (base228 and loop250) run each item in its own fresh work dir,
interleaved item by item in one session (timing for M5). Replies come from the
daemon outbox exactly as a user sees them; stored triples are the live
notebook's active taught facts (fable_loop90_agent.notebook_triples).

Scoring rules = artifacts/.../askpanel243-schema.txt (director, 2026-09-22):
  right (ANSWER): every gold part in reply (case-insensitive) AND reply does
    not start with "I don't know" / "I do not know".
  wrong value: reply contains a stated value (whole word, case-insensitive)
    that is neither a gold part nor in allowed_mentions (ABSTAIN: any value).
  question write: stored triples after the question != after the setup.
  control: reply byte-identical to base228 base_reply.
Schema check on load; any mismatch -> SCHEMA-MISMATCH, exit 3, no verdict.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

DEV = REPO / "artifacts/claude-verbsubj250-20260922/dev250.jsonl"
PANEL_DIR = REPO / "artifacts/claude-askpanel243-20260922"
ARMS = {
    "base228": ("scripts/claude_loop228_agent.py",
                "artifacts/claude-determinism228-20260922/loop228-config.json"),
    "loop250": ("scripts/claude_loop250_agent.py",
                "artifacts/claude-verbsubj250-20260922/loop250-config.json"),
}
MY_FAMILY = "verb_subject"

PANEL_FIELDS = {"id", "family", "setup", "question", "twin_question", "gold",
                "expect", "stated_facts", "note", "allowed_mentions"}
BASE_FIELDS = {"id", "base_setup_replies", "stored_after_setup", "base_reply",
               "stored_after_question", "twin_reply", "base_right",
               "twin_right"}
FAMILY_COUNTS = {"compose": 16, "no_apos": 16, "whats": 12,
                 "first_person": 12, "verb_subject": 12, "my_relation": 16,
                 "direction": 10, "combo": 8, "control": 12, "untaught": 10}
FAMILY_EXPECT = {"compose": "ANSWER", "no_apos": "ANSWER", "whats": "ANSWER",
                 "first_person": "ANSWER", "verb_subject": "ANSWER",
                 "my_relation": "ANSWER", "combo": "ANSWER",
                 "direction": "ABSTAIN", "untaught": "ABSTAIN",
                 "control": "UNCHANGED"}


# ------------------------------------------------------------------ scoring
def is_decline(reply: str) -> bool:
    r = reply.strip().lower().replace("’", "'")
    return r.startswith("i don't know") or r.startswith("i do not know")


def gold_parts(gold) -> list[str]:
    if gold is None:
        return []
    if isinstance(gold, list):
        return [str(g).strip() for g in gold if str(g).strip()]
    return [p.strip() for p in str(gold).split(";") if p.strip()]


def has_word(reply: str, value: str) -> bool:
    value = str(value).strip()
    if not value:
        return False
    return re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", reply,
                     re.IGNORECASE) is not None


def right(reply: str, gold) -> bool:
    parts = gold_parts(gold)
    return bool(parts) and all(p.lower() in reply.lower() for p in parts) \
        and not is_decline(reply)


def wrong_values(reply: str, stated, gold, allowed, expect: str) -> list[str]:
    ok = set()
    if expect != "ABSTAIN":
        ok = {g.lower() for g in gold_parts(gold)}
        ok |= {str(a).strip().lower() for a in (allowed or [])}
    out = []
    for triple in stated or []:
        v = str(triple[2]).strip()
        if v and v.lower() not in ok and has_word(reply, v):
            out.append(v)
    return sorted(set(out))


def canon(triples) -> list:
    return sorted([list(map(str, t)) for t in triples])


# ------------------------------------------------------------------ running
class Arm:
    def __init__(self, name: str, work: Path) -> None:
        import fable_marks123_all as M
        agent, cfg = ARMS[name]
        self.name = name
        self.M = M
        _mod, self.dcls, _b, _c = M.load_agent(str(REPO / agent))
        self.cfg = M.load_base_cfg(str(REPO / cfg))
        self.work = work / name

    def dialog(self, key: str, setup: list[str], question: str) -> dict:
        import fable_loop90_agent as L90
        root = self.work / key
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = self.M.make_daemon(self.dcls, self.cfg, root)
        setup_replies = []
        for j, t in enumerate(setup):
            f = root / "inbox" / f"m{j:02d}.txt"
            f.write_text(t)
            d.process_file(f)
            setup_replies.append(
                (root / "outbox" / f"m{j:02d}.txt").read_text().strip())
        after_setup = canon(L90.notebook_triples(d.loop.nb))
        f = root / "inbox" / "q.txt"
        f.write_text(question)
        t0 = time.perf_counter()
        d.process_file(f)
        dt = time.perf_counter() - t0
        reply = (root / "outbox" / "q.txt").read_text().strip()
        after_q = canon(L90.notebook_triples(d.loop.nb))
        return {"setup_replies": setup_replies, "stored_after_setup":
                after_setup, "reply": reply, "stored_after_question": after_q,
                "q_seconds": dt}


def run_both(arms: dict, k: int, key: str, setup, question) -> dict:
    """Both arms on one item; the arm order alternates item by item so
    neither arm always pays the first-run cost (fair M5 timing)."""
    order = list(arms) if k % 2 == 0 else list(arms)[::-1]
    return {n: arms[n].dialog(key, setup, question) for n in order}


# ------------------------------------------------------------------ dev
def run_dev(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    cases = [json.loads(x) for x in DEV.read_text().splitlines() if x.strip()]
    arms = {n: Arm(n, out / "work") for n in ARMS}
    rows, fails = [], []
    for k, c in enumerate(cases):
        res = run_both(arms, k, c["id"], c["setup"], c["question"])
        b, m = res["base228"], res["loop250"]
        stated = m["stored_after_setup"]
        qwrite = m["stored_after_question"] != m["stored_after_setup"]
        setup_same = b["setup_replies"] == m["setup_replies"]
        if c["kind"] == "fix":
            wv = wrong_values(m["reply"], stated, c["gold"], c["allowed"],
                              "ANSWER")
            ok = right(m["reply"], c["gold"]) and not wv
        elif c["kind"] == "trap":
            wv = wrong_values(m["reply"], stated, None, [], "ABSTAIN")
            ok = not wv
        else:
            wv = []  # keep items: byte-identical to the live base228 reply
            ok = m["reply"] == b["reply"]
        ok = ok and not qwrite and setup_same
        row = {"id": c["id"], "kind": c["kind"], "question": c["question"],
               "gold": c["gold"], "base_reply": b["reply"],
               "reply": m["reply"], "ok": ok, "wrong_values": wv,
               "question_write": qwrite, "setup_replies_same": setup_same,
               "base_right": right(b["reply"], c["gold"])
               if c["kind"] == "fix" else None,
               "base_s": b["q_seconds"], "mine_s": m["q_seconds"]}
        rows.append(row)
        if not ok:
            fails.append(row)
        print(f"{c['id']} {c['kind']:4s} {'OK ' if ok else 'BAD'} "
              f"{c['question']!r} -> {m['reply']!r}", flush=True)
    (out / "dev250-rows.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows))
    by = {}
    for r in rows:
        k = by.setdefault(r["kind"], [0, 0])
        k[0] += int(r["ok"])
        k[1] += 1
    moves = sum(1 for r in rows if r["kind"] == "fix" and not r["base_right"]
                and r["ok"])
    summary = {"by_kind": by, "question_writes":
               sum(r["question_write"] for r in rows),
               "wrong_values": sum(len(r["wrong_values"]) for r in rows),
               "fix_moves_decline_to_right": moves,
               "median_added_ms": 1000 * statistics.median(
                   r["mine_s"] - r["base_s"] for r in rows),
               "all_ok": not fails}
    (out / "dev250-summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return 0 if not fails else 1


# ------------------------------------------------------------------ schema
def mismatch(msg: str):
    print(f"SCHEMA-MISMATCH: {msg}")
    sys.exit(3)


def load_panel() -> tuple[list[dict], list[dict]]:
    for fn in ("panel.jsonl", "base228.jsonl", "README.md",
               "SEAL.sha256.txt"):
        if not (PANEL_DIR / fn).is_file():
            mismatch(f"missing file {fn}")
    try:
        panel = [json.loads(x) for x in
                 (PANEL_DIR / "panel.jsonl").read_text().splitlines()
                 if x.strip()]
        base = [json.loads(x) for x in
                (PANEL_DIR / "base228.jsonl").read_text().splitlines()
                if x.strip()]
    except Exception as e:  # noqa: BLE001
        mismatch(f"unreadable jsonl: {e}")
    if len(panel) != 124 or len(base) != 124:
        mismatch(f"line counts panel={len(panel)} base228={len(base)}")
    for i, p in enumerate(panel):
        if not isinstance(p, dict) or set(p) != PANEL_FIELDS:
            mismatch(f"panel line {i+1} fields {sorted(p) if isinstance(p, dict) else p}")
    for i, b in enumerate(base):
        if not isinstance(b, dict) or set(b) != BASE_FIELDS:
            mismatch(f"base228 line {i+1} fields {sorted(b) if isinstance(b, dict) else b}")
    want_ids = [f"q243-{k:03d}" for k in range(1, 125)]
    if sorted(p["id"] for p in panel) != want_ids:
        mismatch("panel ids are not q243-001..q243-124")
    if [p["id"] for p in panel] != [b["id"] for b in base]:
        mismatch("ids differ between panel.jsonl and base228.jsonl")
    counts = {}
    for p in panel:
        fam = p["family"]
        if fam not in FAMILY_COUNTS:
            mismatch(f"unknown family {fam!r} ({p['id']})")
        counts[fam] = counts.get(fam, 0) + 1
        if p["expect"] != FAMILY_EXPECT[fam]:
            mismatch(f"{p['id']} family {fam} expect {p['expect']!r}")
        if not isinstance(p["setup"], list) or not p["setup"]:
            mismatch(f"{p['id']} setup empty or not a list")
        if not isinstance(p["question"], str):
            mismatch(f"{p['id']} question not a string")
        if not isinstance(p["stated_facts"], list) or not isinstance(
                p["allowed_mentions"], list):
            mismatch(f"{p['id']} stated_facts/allowed_mentions not lists")
        if p["expect"] == "ANSWER" and not gold_parts(p["gold"]):
            mismatch(f"{p['id']} ANSWER item without gold")
    if counts != FAMILY_COUNTS:
        mismatch(f"family counts {counts}")
    return panel, base


def run_schema() -> int:
    load_panel()
    print("SCHEMA OK: 124 items, 10 families with exact counts, expect "
          "labels, ids match")
    return 0


# ------------------------------------------------------------------ panel
def run_panel(out: Path) -> int:
    panel, base = load_panel()
    out.mkdir(parents=True, exist_ok=True)
    arms = {n: Arm(n, out / "work") for n in ARMS}
    rows = []
    for k, (p, b) in enumerate(zip(panel, base)):
        res = run_both(arms, k, p["id"], p["setup"], p["question"])
        m, lb = res["loop250"], res["base228"]
        exp = p["expect"]
        stated = p["stated_facts"]
        wv = wrong_values(m["reply"], stated, p["gold"],
                          p["allowed_mentions"], exp)
        base_wv = wrong_values(b["base_reply"], stated, p["gold"],
                               p["allowed_mentions"], exp)
        qwrite = m["stored_after_question"] != m["stored_after_setup"]
        row = {"id": p["id"], "family": p["family"], "expect": exp,
               "question": p["question"], "gold": p["gold"],
               "base_reply_file": b["base_reply"],
               "base_reply_live": lb["reply"], "reply": m["reply"],
               "base_right": b["base_right"],
               "right": right(m["reply"], p["gold"]) if exp == "ANSWER"
               else None,
               "decline": is_decline(m["reply"]),
               "wrong_values": wv, "base_wrong_values": base_wv,
               "question_write": qwrite,
               "byte_same_as_file": m["reply"] == b["base_reply"],
               "live_base_same_as_file": lb["reply"] == b["base_reply"],
               "base_s": lb["q_seconds"], "mine_s": m["q_seconds"]}
        rows.append(row)
        print(f"{p['id']} {p['family']:12s} {exp:9s} "
              f"{'R' if row['right'] else '-'} wv={wv} "
              f"{p['question']!r} -> {m['reply']!r}", flush=True)
    (out / "panel250-rows.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows))

    fam = [r for r in rows if r["family"] == MY_FAMILY]
    m1a = sum(1 for r in fam if r["right"] and not r["wrong_values"])
    m1b = sum(1 for r in rows if r["wrong_values"])
    m1c = sum(1 for r in rows if r["question_write"])
    ctrl = [r for r in rows if r["family"] == "control"]
    m1d = sum(1 for r in ctrl if r["byte_same_as_file"])
    regress = [r["id"] for r in rows
               if r["family"] not in (MY_FAMILY, "combo", "control")
               and r["expect"] == "ANSWER" and r["base_right"]
               and (not r["right"] or r["decline"])]
    unt = [r for r in rows if r["family"] == "untaught"]
    unt_ok = sum(1 for r in unt if not r["wrong_values"])
    direc = [r for r in rows if r["family"] == "direction"]
    new_leaks = [r["id"] for r in direc
                 if r["wrong_values"] and not r["base_wrong_values"]]
    old_leaks = [r["id"] for r in direc if r["base_wrong_values"]]
    combo = [{"id": r["id"], "right": r["right"], "wrong_values":
              r["wrong_values"], "reply": r["reply"]}
             for r in rows if r["family"] == "combo"]
    added = [1000 * (r["mine_s"] - r["base_s"]) for r in rows]
    med = statistics.median(added)
    marks = {
        "M1a": {"right": m1a, "of": len(fam),
                "pass": m1a >= 0.9 * len(fam)},
        "M1b": {"wrong_value_items": m1b, "pass": m1b == 0},
        "M1c": {"question_writes": m1c, "pass": m1c == 0},
        "M1d": {"byte_identical": m1d, "of": len(ctrl),
                "pass": m1d == len(ctrl)},
        "M1e": {"regressions": regress, "untaught_ok": unt_ok,
                "untaught_of": len(unt), "direction_new_leaks": new_leaks,
                "direction_base_leaks_listed": old_leaks,
                "pass": not regress and unt_ok == len(unt) and not new_leaks},
        "M1f_combo": combo,
        "M5": {"median_added_ms": round(med, 3), "pass": med <= 5.0},
        "live_base_matches_file": sum(r["live_base_same_as_file"]
                                      for r in rows),
    }
    marks["M1_pass"] = all(marks[k]["pass"] for k in
                           ("M1a", "M1b", "M1c", "M1d", "M1e"))
    (out / "panel250-marks.json").write_text(json.dumps(marks, indent=1))
    print(json.dumps(marks, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dev", "schema", "panel"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.mode == "schema":
        return run_schema()
    if not a.out:
        ap.error("--out needed")
    out = Path(a.out)
    return run_dev(out) if a.mode == "dev" else run_panel(out)


if __name__ == "__main__":
    sys.exit(main())
