#!/usr/bin/env python3
"""Exp 258 scorer (read-only on everything it scores).

panel: claude_comment258_score.py panel <panel_dir> <mine_rows> <base252b_arm_rows>
  Schema check first (corrtail258-spec): files present, exact fields,
  8 families with exact counts, ids t258-001..080 in order and matching in
  panel.jsonl and base252b.jsonl. Any mismatch: prints SCHEMA-MISMATCH,
  exits 3, no verdict (VOID).
  Then scores both arms with the spec's rules; keep and control items are
  right only if turn_reply, followup_reply and every stored list are
  byte-identical to the writer's base252b.jsonl. Prints the M1 marks.
dev: claude_comment258_score.py dev <dev258.jsonl> <mine_rows> <base_rows>
  Same item rules (no schema check); keep and control identity is checked
  against <base_rows> (the 252b arm run in the same session). Restart items'
  "extra" checks: must_not value absent (whole word), must value present.
m3: claude_comment258_score.py m3 <corrpanel252_dir> <252b_rows> <mine_rows> <ids,comma,separated|->
  Rows compared on every field but ms_per_turn. Bars: moved ids == the
  predicted ids; 0 new wrong values (followup contains an expect_gone value
  whole word, where 252b's did not); 0 new junk writes.
moves: claude_comment258_score.py moves <base_rows> <mine_rows> <ids|->
  Rows compared on every field but ms_per_turn; moved ids vs predicted.
suites: claude_comment258_score.py suites <252b sd dir> <mine sd dir>
  M4: move lists / class counts / new_* equal to 252b's per suite, no
  new WRONG / WRONG-WRITE / junk / lost OK classes; row files reported.
smoke: claude_comment258_score.py smoke <252b.json> <mine.json>
  Every field equal except agent / config / label / seconds / paths.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PANEL_FIELDS = ["id", "family", "setup", "turn", "followup", "stated_facts",
                "target", "expect_gone", "expect_store", "gold_followup",
                "note"]
BASE_FIELDS = ["id", "setup_replies", "stored_after_setup", "turn_reply",
               "stored_after_turn", "followup_reply", "stored_after_followup",
               "base_right", "base_wrong_value", "base_false_claim"]
FAMILIES = {"that_denial": 12, "that_correction": 12, "pure_denial_that": 10,
            "other_tail_denial": 10, "keep": 8, "question_tail": 6,
            "unstored_tail": 6, "control": 16}
FAM_ORDER = list(FAMILIES)
PANEL_FILES = ["panel.jsonl", "base252b.jsonl", "make_panel.py", "run_base.py",
               "README.md", "SEAL.sha256.txt"]
CAUSE3 = ("that_denial", "that_correction", "pure_denial_that")


def T(xs) -> set:
    return {tuple(str(v).lower() for v in x) for x in (xs or [])}


def ww(needle: str, hay: str) -> bool:
    if not needle:
        return False
    return re.search(r"(?<!\w)" + re.escape(str(needle)) + r"(?!\w)",
                     str(hay), re.IGNORECASE) is not None


def load_rows(p) -> dict:
    out = {}
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def mismatch(msg: str) -> int:
    print(f"SCHEMA-MISMATCH: {msg}")
    sys.exit(3)


def schema_check(d: Path):
    for f in PANEL_FILES:
        if not (d / f).is_file():
            mismatch(f"missing file {f}")
    items, base = [], []
    try:
        for line in (d / "panel.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                items.append(json.loads(line))
        for line in (d / "base252b.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                base.append(json.loads(line))
    except Exception as e:  # noqa: BLE001
        mismatch(f"unreadable jsonl: {e}")
    if len(items) != 80 or len(base) != 80:
        mismatch(f"line counts panel={len(items)} base={len(base)} (want 80)")
    for it in items:
        if sorted(it) != sorted(PANEL_FIELDS):
            mismatch(f"panel fields {it.get('id')}: {sorted(it)}")
        if it["family"] not in FAMILIES:
            mismatch(f"unknown family {it['family']!r} at {it['id']}")
        if not isinstance(it["setup"], list) or not it["setup"]:
            mismatch(f"setup not a non-empty list at {it['id']}")
        for k in ("stated_facts", "expect_gone", "expect_store"):
            if not isinstance(it[k], list) or any(
                    not isinstance(x, list) or len(x) != 3 for x in it[k]):
                mismatch(f"{k} not a list of triples at {it['id']}")
        if it["target"] is not None and (not isinstance(it["target"], list)
                                         or len(it["target"]) != 3):
            mismatch(f"target not a triple or null at {it['id']}")
        if it["gold_followup"] is not None and not isinstance(
                it["gold_followup"], str):
            mismatch(f"gold_followup not str/null at {it['id']}")
        for k in ("turn", "followup", "note"):
            if not isinstance(it[k], str):
                mismatch(f"{k} not a string at {it['id']}")
    for b in base:
        if sorted(b) != sorted(BASE_FIELDS):
            mismatch(f"base fields {b.get('id')}: {sorted(b)}")
    counts = {}
    for it in items:
        counts[it["family"]] = counts.get(it["family"], 0) + 1
    if counts != FAMILIES:
        mismatch(f"family counts {counts}")
    want = [f"t258-{n:03d}" for n in range(1, 81)]
    if [it["id"] for it in items] != want:
        mismatch("panel ids are not t258-001..080 in order")
    if [b["id"] for b in base] != want:
        mismatch("base252b ids do not match panel ids in order")
    seq = [FAM_ORDER.index(it["family"]) for it in items]
    if seq != sorted(seq):
        print("WARNING: families not in the spec's block order (not a "
              "listed schema check; scoring goes on)")
    return items, {b["id"]: b for b in base}


def score_item(it: dict, r: dict, ref: dict | None) -> dict:
    sas, sat = T(r["stored_after_setup"]), T(r["stored_after_turn"])
    saf = T(r["stored_after_followup"])
    es, eg = T(it["expect_store"]), T(it["expect_gone"])
    allowed = sas | es
    store_ok = es <= sat and not (eg & sat) and sat <= allowed
    junk = not (sat <= allowed) or not (saf <= allowed)
    fr = r["followup_reply"]
    gone_vals = [x[2] for x in it["expect_gone"]]
    wrong_value = any(ww(v, fr) for v in gone_vals)
    gold = it.get("gold_followup")
    if gold is not None:
        parts = [p.strip() for p in gold.split(";") if p.strip()]
        followup_ok = (all(p.lower() in fr.lower() for p in parts)
                       and not fr.lower().startswith(("i don't know",
                                                      "i do not know")))
    else:
        followup_ok = not wrong_value
    followup_write = saf != sat
    tgt = it.get("target")
    tr = r["turn_reply"]
    false_claim = bool(
        tgt is not None and T([tgt]) <= sas and T([tgt]) <= sat
        and re.search(r"don't have|do not have", tr, re.IGNORECASE)
        and ww(tgt[2], tr))
    right = store_ok and followup_ok and not followup_write and not false_claim
    ident = None
    if it["family"] in ("keep", "control") and ref is not None:
        ident = all(r[k] == ref[k] for k in (
            "turn_reply", "followup_reply", "stored_after_setup",
            "stored_after_turn", "stored_after_followup"))
        right = right and ident
    if it["family"] == "unstored_tail" and re.search(r"removed|updated", tr,
                                                     re.IGNORECASE):
        right = False
    extra_ok = None
    if it.get("extra"):
        extra_ok = True
        for (q, must_not, must), rep in zip(it["extra"],
                                            r.get("extra_replies", [])):
            if must_not and ww(must_not, rep):
                extra_ok = False
            if must and not ww(must, rep):
                extra_ok = False
        right = right and extra_ok
    return {"right": right, "store_ok": store_ok, "junk_write": junk,
            "followup_ok": followup_ok, "wrong_value": wrong_value,
            "followup_write": followup_write, "false_claim": false_claim,
            "identical": ident, "extra_ok": extra_ok}


def tally(items, rows, refs) -> dict:
    fam: dict = {}
    per = {}
    for it in items:
        s = score_item(it, rows[it["id"]], refs.get(it["id"]) if refs else None)
        per[it["id"]] = s
        f = fam.setdefault(it["family"], {"n": 0, "right": 0, "junk": 0,
                                          "wrong_value": 0, "false_claim": 0,
                                          "followup_write": 0})
        f["n"] += 1
        f["right"] += int(s["right"])
        f["junk"] += int(s["junk_write"])
        f["wrong_value"] += int(s["wrong_value"])
        f["false_claim"] += int(s["false_claim"])
        f["followup_write"] += int(s["followup_write"])
    return {"families": fam, "items": per}


def panel(d, mine, basearm) -> int:
    d = Path(d)
    items, base = schema_check(d)
    print("schema OK")
    M, B = load_rows(mine), load_rows(basearm)
    for it in items:
        if it["id"] not in M or it["id"] not in B:
            mismatch(f"row missing for {it['id']}")
    tm = tally(items, M, base)
    tb = tally(items, B, base)
    # the writer's own base fields, for reference
    wb = {"base_right": {}, "base_wrong_value": {}, "base_false_claim": {}}
    for it in items:
        for k in wb:
            wb[k][it["family"]] = wb[k].get(it["family"], 0) + int(
                bool(base[it["id"]][k]))
    fm, fb = tm["families"], tb["families"]
    junk_all = sum(f["junk"] for f in fm.values())
    junk_all_b = sum(f["junk"] for f in fb.values())
    wv3 = sum(fm[f]["wrong_value"] for f in CAUSE3)
    fc3 = sum(fm[f]["false_claim"] for f in CAUSE3)
    newly_wrong_other = [i for i in (it["id"] for it in items
                                     if it["family"] == "other_tail_denial")
                         if tb["items"][i]["right"] and not tm["items"][i]["right"]]
    marks = [
        ("that_denial >= 10/12", fm["that_denial"]["right"] >= 10,
         fm["that_denial"]["right"], fb["that_denial"]["right"]),
        ("that_correction >= 10/12", fm["that_correction"]["right"] >= 10,
         fm["that_correction"]["right"], fb["that_correction"]["right"]),
        ("pure_denial_that >= 9/10", fm["pure_denial_that"]["right"] >= 9,
         fm["pure_denial_that"]["right"], fb["pure_denial_that"]["right"]),
        ("junk writes over 80 == 0", junk_all == 0, junk_all, junk_all_b),
        ("wrong values in 3 families == 0", wv3 == 0, wv3,
         sum(fb[f]["wrong_value"] for f in CAUSE3)),
        ("false claims in 3 families == 0", fc3 == 0, fc3,
         sum(fb[f]["false_claim"] for f in CAUSE3)),
        ("other_tail_denial newly wrong vs 252b == 0",
         not newly_wrong_other, len(newly_wrong_other), 0),
        ("question_tail 6/6", fm["question_tail"]["right"] == 6,
         fm["question_tail"]["right"], fb["question_tail"]["right"]),
        ("unstored_tail 6/6", fm["unstored_tail"]["right"] == 6,
         fm["unstored_tail"]["right"], fb["unstored_tail"]["right"]),
        ("keep 8/8 (byte-identical to base252b)", fm["keep"]["right"] == 8,
         fm["keep"]["right"], fb["keep"]["right"]),
        ("control 16/16 (byte-identical to base252b)",
         fm["control"]["right"] == 16, fm["control"]["right"],
         fb["control"]["right"]),
    ]
    for name, ok, a, b in marks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: mine={a} 252b={b}")
    for f in FAM_ORDER:
        print(f"family {f}: mine {fm[f]} | 252b {fb[f]}")
    print("writer base fields per family:", json.dumps(wb))
    moved = [i for i in tm["items"] if tm["items"][i] != tb["items"][i]
             or M[i]["turn_reply"] != B[i]["turn_reply"]]
    print("items whose rows or scores differ between arms:", moved)
    for it in items:
        a, b = tm["items"][it["id"]], tb["items"][it["id"]]
        print(f"{it['id']} {it['family']}: mine right={a['right']} "
              f"junk={a['junk_write']} wv={a['wrong_value']} fc={a['false_claim']}"
              f" | 252b right={b['right']} junk={b['junk_write']} "
              f"wv={b['wrong_value']} fc={b['false_claim']}")
    verdict = all(ok for _n, ok, _a, _b in marks)
    print("M1", "PASS" if verdict else "FAIL")
    return 0


def dev(cases, mine, basearm) -> int:
    items = [json.loads(line) for line in
             Path(cases).read_text(encoding="utf-8").splitlines() if line.strip()]
    M, B = load_rows(mine), load_rows(basearm)
    tm, tb = tally(items, M, B), tally(items, B, B)
    for f in tm["families"]:
        print(f"family {f}: mine {tm['families'][f]} | 252b {tb['families'][f]}")
    for it in items:
        a, b = tm["items"][it["id"]], tb["items"][it["id"]]
        flag = "" if a == b else "  MOVE"
        print(f"{it['id']} {it['family']}: mine right={a['right']} "
              f"junk={a['junk_write']} wv={a['wrong_value']} "
              f"fc={a['false_claim']} | 252b right={b['right']} "
              f"junk={b['junk_write']}{flag}")
    return 0


def m3(d, base_rows, mine_rows, ids) -> int:
    d = Path(d)
    items = {json.loads(l)["id"]: json.loads(l) for l in
             (d / "panel.jsonl").read_text(encoding="utf-8").splitlines()
             if l.strip()}
    B, M = load_rows(base_rows), load_rows(mine_rows)
    pred = set() if ids in ("-", "") else set(ids.split(","))
    moved, new_wrong, new_junk = [], [], []
    for i, b in B.items():
        m = M[i]
        if {k: v for k, v in b.items() if k != "ms_per_turn"} != \
                {k: v for k, v in m.items() if k != "ms_per_turn"}:
            moved.append(i)
        it = items[i]
        gone = [x[2] for x in it.get("expect_gone", [])]
        wb = any(ww(v, b["followup_reply"]) for v in gone)
        wm = any(ww(v, m["followup_reply"]) for v in gone)
        if wm and not wb:
            new_wrong.append(i)
        allowed = T(m["stored_after_setup"]) | T(it.get("expect_store", []))
        jm = not (T(m["stored_after_turn"]) <= allowed) or not (
            T(m["stored_after_followup"]) <= allowed)
        allowed_b = T(b["stored_after_setup"]) | T(it.get("expect_store", []))
        jb = not (T(b["stored_after_turn"]) <= allowed_b) or not (
            T(b["stored_after_followup"]) <= allowed_b)
        if jm and not jb:
            new_junk.append(i)
    for i in moved:
        print(f"MOVE {i}: turn {B[i]['turn_reply']!r} -> {M[i]['turn_reply']!r}"
              f" | followup {B[i]['followup_reply']!r} -> "
              f"{M[i]['followup_reply']!r} | store {B[i]['stored_after_turn']}"
              f" -> {M[i]['stored_after_turn']}")
    ok = set(moved) == pred and not new_wrong and not new_junk
    print(json.dumps({"moved": moved, "predicted": sorted(pred),
                      "unpredicted": sorted(set(moved) - pred),
                      "missing": sorted(pred - set(moved)),
                      "new_wrong_values": new_wrong, "new_junk": new_junk,
                      "M3_pass": ok}, indent=1))
    return 0


def moves(base_rows, mine_rows, ids) -> int:
    B, M = load_rows(base_rows), load_rows(mine_rows)
    pred = set() if ids in ("-", "") else set(ids.split(","))
    moved = [i for i in B if {k: v for k, v in B[i].items() if k != "ms_per_turn"}
             != {k: v for k, v in M[i].items() if k != "ms_per_turn"}]
    print(json.dumps({"n_moved": len(moved), "moved": moved,
                      "unpredicted": sorted(set(moved) - pred),
                      "missing": sorted(pred - set(moved)),
                      "moves_as_predicted": set(moved) == pred}, indent=1))
    return 0


def suites(base_dir, mine_dir) -> int:
    """M4: per suite, moves / class counts / new_* lists equal to 252b's,
    0 new WRONG / WRONG-WRITE / junk / lost OK, and rows equal to 252b's
    except the timing field "seconds"."""
    bd, md = Path(base_dir), Path(mine_dir)
    out, ok = {}, True
    for s in ("rt136", "rt143", "sessions152", "bench"):
        a = json.loads((bd / f"{s}-diff.json").read_text())
        b = json.loads((md / f"{s}-diff.json").read_text())
        same = {k: a[k] == b[k] for k in ("moves", "class_counts", "n_moves",
                                           "new_wrong", "new_wrong_write",
                                           "new_junk")}
        cc = b.get("class_counts", {})
        bad = {k: v for k, v in cc.items() if v and any(
            t in k for t in ("new WRONG", "junk", "lost OK"))}
        out[s] = {"same_as_252b": same, "bad_classes": bad}
        ok = ok and all(same.values()) and not bad
    rows_diff = {}
    for f in sorted(p.name for p in bd.iterdir() if "rows" in p.name):
        def L(path):
            txt = path.read_text(encoding="utf-8")
            try:
                whole = json.loads(txt)
                recs = whole if isinstance(whole, list) else [whole]
            except json.JSONDecodeError:
                recs = [json.loads(x) for x in txt.splitlines() if x.strip()]

            def clean(x):
                if isinstance(x, dict):
                    return {k: clean(v) for k, v in x.items()
                            if k not in ("seconds", "ms", "ms_per_turn",
                                         "elapsed", "wall")}
                if isinstance(x, list):
                    return [clean(v) for v in x]
                return x
            return [clean(r) for r in recs]
        if not (md / f).exists():
            rows_diff[f] = "missing"
            ok = False
            continue
        n = sum(1 for x, y in zip(L(bd / f), L(md / f)) if x != y)
        if n or len(L(bd / f)) != len(L(md / f)):
            rows_diff[f] = n
    out["rows_differing_besides_seconds"] = rows_diff
    out["M4_pass"] = ok
    print(json.dumps(out, indent=1))
    return 0


def smoke(a, b) -> int:
    A = json.loads(Path(a).read_text())
    Bv = json.loads(Path(b).read_text())
    skip = {"agent", "config", "label", "seconds", "out", "work", "workdir",
            "root", "path"}
    diffs = []

    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in set(x) | set(y):
                if k in skip:
                    continue
                walk(x.get(k), y.get(k), f"{path}.{k}")
        elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
            for n, (p, q) in enumerate(zip(x, y)):
                walk(p, q, f"{path}[{n}]")
        elif x != y:
            diffs.append((path, x, y))
    walk(A, Bv, "")
    for p, x, y in diffs:
        print(f"DIFF {p}: {x!r} -> {y!r}")
    print(json.dumps({"n_diffs": len(diffs), "M5_pass": not diffs}))
    return 0


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "panel":
        sys.exit(panel(*sys.argv[2:5]))
    if mode == "dev":
        sys.exit(dev(*sys.argv[2:5]))
    if mode == "m3":
        sys.exit(m3(*sys.argv[2:6]))
    if mode == "moves":
        sys.exit(moves(*sys.argv[2:5]))
    if mode == "suites":
        sys.exit(suites(*sys.argv[2:4]))
    if mode == "smoke":
        sys.exit(smoke(*sys.argv[2:4]))
    print(__doc__)
    sys.exit(2)
