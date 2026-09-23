#!/usr/bin/env python3
"""Exp 248 runner + scorer (dev cases and the shared ask panel 243).

  dev   --out DIR            run dev248.jsonl on base228 and 248, score M2
  panel --out DIR            schema check, run panel on base228 and 248, score M1/M5
  panel --schema-only        schema check only (SCHEMA-MISMATCH -> exit 3)

Every dialog gets its own fresh work dir under --work (never the repo-root
notebook/). Arms run in the same process, interleaved item by item, so the
timing comparison (M5) is paired and shares machine load.
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

DEV = REPO / "artifacts/claude-whats248-20260922/dev248.jsonl"
BASE_CFG = REPO / "artifacts/claude-determinism228-20260922/loop228-config.json"
MY_CFG = REPO / "artifacts/claude-whats248-20260922/loop248-config.json"
PANEL_DIR = REPO / "artifacts/claude-askpanel243-20260922"

MY_FAMILY = "whats"
PANEL_FIELDS = {"id", "family", "setup", "question", "twin_question", "gold",
                "expect", "stated_facts", "note", "allowed_mentions"}
BASE_FIELDS = {"id", "base_setup_replies", "stored_after_setup", "base_reply",
               "stored_after_question", "twin_reply", "base_right",
               "twin_right"}
FAMILY_COUNTS = {"compose": 16, "no_apos": 16, "whats": 12,
                 "first_person": 12, "verb_subject": 12, "my_relation": 16,
                 "direction": 10, "combo": 8, "control": 12, "untaught": 10}
EXPECT = {"compose": "ANSWER", "no_apos": "ANSWER", "whats": "ANSWER",
          "first_person": "ANSWER", "verb_subject": "ANSWER",
          "my_relation": "ANSWER", "combo": "ANSWER", "direction": "ABSTAIN",
          "untaught": "ABSTAIN", "control": "UNCHANGED"}


# ------------------------------------------------------------------ scoring
def is_decline(reply: str) -> bool:
    r = reply.strip().lower().replace("’", "'")
    return r.startswith("i don't know") or r.startswith("i do not know")


def gold_parts(gold):
    if gold is None:
        return []
    if isinstance(gold, list):
        return [str(g).strip() for g in gold if str(g).strip()]
    return [p.strip() for p in str(gold).split(";") if p.strip()]


def has_word(reply: str, value: str) -> bool:
    v = str(value).strip()
    if not v:
        return False
    pat = r"(?<!\w)" + re.escape(v) + r"(?!\w)"
    return re.search(pat, reply, re.I) is not None


def is_right(reply: str, gold) -> bool:
    parts = gold_parts(gold)
    low = reply.lower()
    return bool(parts) and all(p.lower() in low for p in parts) and \
        not is_decline(reply)


def wrong_values(reply: str, stated, gold, allowed, abstain: bool):
    ok = set() if abstain else {p.lower() for p in gold_parts(gold)}
    ok |= set() if abstain else {str(a).lower() for a in (allowed or [])}
    bad = []
    for fact in stated or []:
        val = str(fact[2])
        if val.lower() in ok:
            continue
        if has_word(reply, val) and val not in bad:
            bad.append(val)
    return bad


def trip_key(trips):
    return sorted(tuple(str(x) for x in t) for t in trips)


# ------------------------------------------------------------------ running
def load_arms():
    import fable_marks123_all as M  # noqa: E402 (read-only)
    import claude_loop228_agent as A228  # noqa: E402
    import claude_loop248_agent as A248  # noqa: E402
    base_cfg = M.load_base_cfg(str(BASE_CFG))
    my_cfg = M.load_base_cfg(str(MY_CFG))
    return {"base228": (A228.Loop228Daemon, base_cfg),
            "248": (A248.Loop248Daemon, my_cfg)}, M


def run_dialog(M, dcls, cfg, root: Path, setup, question):
    import fable_loop90_agent as L90  # noqa: E402
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    d = M.make_daemon(dcls, cfg, root)

    def say(j, text):
        f = root / "inbox" / f"m{j:02d}.txt"
        f.write_text(text, encoding="utf-8")
        t0 = time.perf_counter()
        d.process_file(f)
        dt = time.perf_counter() - t0
        return (root / "outbox" / f"m{j:02d}.txt").read_text(
            encoding="utf-8").strip(), dt

    setup_replies = [say(j, t)[0] for j, t in enumerate(setup)]
    after_setup = [list(x) for x in L90.notebook_triples(d.loop.nb)]
    reply, dt = say(len(setup), question)
    after_q = [list(x) for x in L90.notebook_triples(d.loop.nb)]
    shutil.rmtree(root, ignore_errors=True)
    return {"setup_replies": setup_replies, "stored_after_setup": after_setup,
            "reply": reply, "stored_after_question": after_q,
            "q_seconds": dt}


def run_both(items, work: Path, out_rows: Path):
    arms, M = load_arms()
    rows = []
    with out_rows.open("w", encoding="utf-8") as fh:
        for i, it in enumerate(items):
            row = {"id": it["id"]}
            for arm, (dcls, cfg) in arms.items():
                r = run_dialog(M, dcls, cfg, work / f"{arm}-{i:03d}",
                               it["setup"], it["question"])
                row[arm] = r
            rows.append(row)
            fh.write(json.dumps(row) + "\n")
            fh.flush()
    return rows


# ---------------------------------------------------------------------- dev
def score_dev(items, rows):
    lines, fails = [], []
    tally = {"right": [0, 0], "trap": [0, 0], "same": [0, 0]}
    qwrites = 0
    for it, row in zip(items, rows):
        mine, base = row["248"], row["base228"]
        wrote = trip_key(mine["stored_after_setup"]) != trip_key(
            mine["stored_after_question"])
        if it["question"].rstrip().endswith("?") and wrote:
            qwrites += 1
        kind = it["kind"]
        if kind == "right":
            ok = is_right(mine["reply"], it["gold"]) and not wrong_values(
                mine["reply"], it["stated"], it["gold"], [], False)
        elif kind == "trap":
            ok = not wrong_values(mine["reply"], it["stated"], None, [], True)
        else:
            ok = (mine["reply"] == base["reply"] and
                  trip_key(mine["stored_after_question"]) ==
                  trip_key(base["stored_after_question"]))
        tally[kind][0] += int(ok)
        tally[kind][1] += 1
        base_ok = None
        if kind == "right":
            base_ok = is_right(base["reply"], it["gold"])
        mark = "OK  " if ok else "MISS"
        lines.append(f"{mark} {it['id']} {kind:5s} {it['question']!r} -> "
                     f"{mine['reply']!r}" + (f"  [base right={base_ok}]"
                                             if base_ok is not None else "")
                     + ("  QWRITE" if wrote else ""))
        if not ok:
            fails.append(it["id"])
    passed = (tally["right"][0] == tally["right"][1] and
              tally["trap"][0] == tally["trap"][1] and
              tally["same"][0] == tally["same"][1] and qwrites == 0)
    summary = (f"M2 dev: right {tally['right'][0]}/{tally['right'][1]}, "
               f"traps clean {tally['trap'][0]}/{tally['trap'][1]}, "
               f"must-not-change {tally['same'][0]}/{tally['same'][1]}, "
               f"question writes {qwrites} -> {'PASS' if passed else 'FAIL'}")
    return lines, summary, passed


# -------------------------------------------------------------------- panel
def schema_mismatch(msg: str):
    print(f"SCHEMA-MISMATCH: {msg}")
    sys.exit(3)


def load_panel_checked():
    for name in ("panel.jsonl", "base228.jsonl", "README.md",
                 "SEAL.sha256.txt"):
        if not (PANEL_DIR / name).is_file():
            schema_mismatch(f"missing file {name}")
    try:
        panel = [json.loads(x) for x in (PANEL_DIR / "panel.jsonl").read_text(
            encoding="utf-8").splitlines() if x.strip()]
        base = [json.loads(x) for x in (PANEL_DIR / "base228.jsonl").read_text(
            encoding="utf-8").splitlines() if x.strip()]
    except Exception as exc:  # noqa: BLE001
        schema_mismatch(f"unreadable jsonl: {exc}")
    if len(panel) != 124 or len(base) != 124:
        schema_mismatch(f"line counts panel={len(panel)} base={len(base)}")
    counts = {}
    for i, (p, b) in enumerate(zip(panel, base)):
        if not isinstance(p, dict) or set(p) != PANEL_FIELDS:
            schema_mismatch(f"panel line {i+1} fields {sorted(p) if isinstance(p, dict) else p}")
        if not isinstance(b, dict) or set(b) != BASE_FIELDS:
            schema_mismatch(f"base228 line {i+1} fields {sorted(b) if isinstance(b, dict) else b}")
        want_id = f"q243-{i+1:03d}"
        if p["id"] != want_id or b["id"] != want_id:
            schema_mismatch(f"line {i+1} ids {p['id']!r}/{b['id']!r} != {want_id}")
        fam = p["family"]
        if fam not in FAMILY_COUNTS:
            schema_mismatch(f"{p['id']} unknown family {fam!r}")
        if p["expect"] != EXPECT[fam]:
            schema_mismatch(f"{p['id']} family {fam} expect {p['expect']!r}")
        counts[fam] = counts.get(fam, 0) + 1
    if counts != FAMILY_COUNTS:
        schema_mismatch(f"family counts {counts}")
    return panel, base


def score_panel(panel, base, rows):
    by_fam = {}
    lines = []
    wrong_total, qw_total = 0, 0
    ctrl_same = 0
    regress, untaught_clean, new_leaks, old_leaks = [], 0, [], []
    diffs = []
    for p, b, row in zip(panel, base, rows):
        mine, live_base = row["248"], row["base228"]
        reply = mine["reply"]
        fam, exp = p["family"], p["expect"]
        abstain = exp == "ABSTAIN"
        bad = wrong_values(reply, p["stated_facts"], p["gold"],
                           p["allowed_mentions"], abstain)
        wrote = trip_key(mine["stored_after_setup"]) != trip_key(
            mine["stored_after_question"])
        wrong_total += int(bool(bad))
        qw_total += int(wrote)
        if exp == "ANSWER":
            right = is_right(reply, p["gold"])
        elif exp == "ABSTAIN":
            right = not bad
        else:
            right = reply == b["base_reply"]
        if fam == "control":
            ctrl_same += int(reply == b["base_reply"])
        if fam == "untaught":
            untaught_clean += int(not bad)
        if fam == "direction":
            base_bad = wrong_values(b["base_reply"], p["stated_facts"], None,
                                    [], True)
            if bad and not base_bad:
                new_leaks.append(p["id"])
            elif bad:
                old_leaks.append(p["id"])
        if fam not in ("control", MY_FAMILY, "combo") and b["base_right"] and \
                (not right or (exp == "ANSWER" and is_decline(reply))):
            regress.append(p["id"])
        f = by_fam.setdefault(fam, [0, 0])
        f[0] += int(right)
        f[1] += 1
        diffs.append(1000.0 * (mine["q_seconds"] - live_base["q_seconds"]))
        lines.append(
            f"{'OK  ' if right else 'MISS'} {p['id']} {fam:12s} "
            f"{p['question']!r} -> {reply!r}"
            + (f" WRONG{bad}" if bad else "") + (" QWRITE" if wrote else "")
            + ("" if reply == b["base_reply"] else "  [changed vs base228]")
            + ("" if live_base["reply"] == b["base_reply"]
               else "  [live base228 differs from file]"))
    fam_n = by_fam.get(MY_FAMILY, [0, 0])
    med = statistics.median(diffs) if diffs else float("nan")
    marks = {
        "M1a": (fam_n[0], fam_n[1], fam_n[0] * 10 >= 9 * fam_n[1]),
        "M1b": (wrong_total, 124, wrong_total == 0),
        "M1c": (qw_total, 124, qw_total == 0),
        "M1d": (ctrl_same, 12, ctrl_same == 12),
        "M1e": (len(regress), untaught_clean, new_leaks, old_leaks,
                not regress and untaught_clean == 10 and not new_leaks),
        "M5_median_ms": (round(med, 2), med <= 5.0),
    }
    return lines, by_fam, marks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dev", "panel"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--work", default=None)
    ap.add_argument("--schema-only", action="store_true")
    ap.add_argument("--panel-dir", default=None,
                    help="scorer self-test only; registered runs use the default")
    args = ap.parse_args(argv)
    global PANEL_DIR
    if args.panel_dir:
        PANEL_DIR = Path(args.panel_dir)
    if args.mode == "panel":
        panel, base = load_panel_checked()
        print("schema OK: 124 items, 10 families, counts and labels match")
        if args.schema_only:
            return 0
        items = [{"id": p["id"], "setup": p["setup"],
                  "question": p["question"]} for p in panel]
    else:
        items = [json.loads(x) for x in DEV.read_text(
            encoding="utf-8").splitlines() if x.strip()]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work) if args.work else out / "work"
    t0 = time.time()
    rows = run_both(items, work, out / "rows.jsonl")
    shutil.rmtree(work, ignore_errors=True)
    if args.mode == "dev":
        lines, summary, _ = score_dev(items, rows)
        text = "\n".join(lines + ["", summary,
                                  f"wall {time.time()-t0:.1f}s"])
    else:
        lines, by_fam, marks = score_panel(panel, base, rows)
        fam_txt = ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in by_fam.items())
        text = "\n".join(lines + ["", "families (248 right): " + fam_txt,
                                  "marks: " + json.dumps(marks),
                                  f"wall {time.time()-t0:.1f}s"])
    (out / "score.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
