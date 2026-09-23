#!/usr/bin/env python3
"""Exp 237b M1 panel scorer (sealed before the panel is opened).

Usage: score.py panel.jsonl base221.jsonl rows237b.jsonl rows221.jsonl out.json

1. SCHEMA CHECK (before any scoring). Any mismatch prints SCHEMA-MISMATCH
   with the reason and exits with code 3 (run VOID, no verdict).
   panel.jsonl: exactly 80 lines; each line has exactly the fields
     id, family, setup, question, expect, gold, note;
     id like "a237b-001", unique; setup is a list; question a string;
     families and counts: synonym 30, new_relation 20, date 10, trap 10,
     control 10; expect: synonym/new_relation/date ANSWER, trap ABSTAIN,
     control UNCHANGED; gold a non-empty string for ANSWER items, null for
     trap items.
   base221.jsonl: exactly 80 lines; each has exactly the fields id,
     base_reply, stored_after_setup; ids = the panel ids.
   stored_after_setup must be readable: a list whose items are triples
     [s, r, v] (list/tuple of 3) or dicts with a value field
     (value/object/val/o/y), or "s | r | v" strings. Otherwise mismatch.
   Run rows (both arms) must have exactly the panel ids.
2. RULES.
   gold parts  = gold split on ";" (stripped, non-empty).
   right       = every gold part appears in the reply (case-insensitive
                 substring) and the reply does not start with
                 "I don't know" / "I do not know" (straight or curly ').
   values      = the stored values (3rd element) in stored_after_setup.
   wrong value = a value that is not a gold part (compared lower-case
                 with a leading a/an/the dropped; for traps: any value)
                 appearing in the reply as a whole word, case-insensitive.
   new wrong   = a wrong value in the 237b reply that is not also a wrong
                 value in base_reply (same item).
   trap        = value-giving if any value appears; NEW if base_reply is
                 not value-giving. Base value-giving traps are listed.
   control     = reply byte-identical to base_reply (both stripped).
   writes      = question turns whose stored triples changed.
   M5          = median(q_ms 237b) - median(q_ms 221 arm), panel questions.
   Bars: synonym >= 85 %, new_relation >= 80 %, date >= 80 %, 0 NEW
   value-giving traps, control 10/10, 0 new wrong values, 0 writes,
   M5 <= +5 ms.
"""
import json
import re
import statistics
import sys

FIELDS = {"id", "family", "setup", "question", "expect", "gold", "note"}
BFIELDS = {"id", "base_reply", "stored_after_setup"}
FAMS = {"synonym": (30, "ANSWER"), "new_relation": (20, "ANSWER"),
        "date": (10, "ANSWER"), "trap": (10, "ABSTAIN"),
        "control": (10, "UNCHANGED")}
VKEYS = ("value", "object", "val", "o", "y")


def mismatch(why):
    print(f"SCHEMA-MISMATCH: {why}")
    sys.exit(3)


def load(path):
    try:
        return [json.loads(l) for l in open(path, encoding="utf-8")
                if l.strip()]
    except Exception as e:  # noqa: BLE001
        mismatch(f"{path} unreadable: {e}")


def values_of(stored, where):
    if not isinstance(stored, list):
        mismatch(f"{where}: stored_after_setup is not a list")
    out = []
    for it in stored:
        if isinstance(it, (list, tuple)) and len(it) == 3:
            out.append(str(it[2]))
        elif isinstance(it, dict) and any(k in it for k in VKEYS):
            out.append(str(next(it[k] for k in VKEYS if k in it)))
        elif isinstance(it, str) and it.count("|") == 2:
            out.append(it.split("|")[2])
        else:
            mismatch(f"{where}: unreadable stored_after_setup item {it!r}")
    return [v.strip().rstrip(".").strip() for v in out if v.strip()]


def art(v):
    """lower-case, leading a/an/the dropped (gold-part comparison only)."""
    v = str(v).strip().lower()
    return re.sub(r"^(a|an|the)\s+", "", v)


def has(v, text):
    return re.search(r"(?<!\w)" + re.escape(v.lower()) + r"(?!\w)",
                     text.lower()) is not None


def main():
    panel, base, rows, rows221 = (load(p) for p in sys.argv[1:5])
    # ---------------- schema
    if len(panel) != 80:
        mismatch(f"panel.jsonl has {len(panel)} lines, want 80")
    if len(base) != 80:
        mismatch(f"base221.jsonl has {len(base)} lines, want 80")
    ids = []
    cnt = {f: 0 for f in FAMS}
    for x in panel:
        if set(x) != FIELDS:
            mismatch(f"panel fields {sorted(x)} != {sorted(FIELDS)}")
        if not re.fullmatch(r"a237b-\d{3}", str(x["id"])):
            mismatch(f"bad id {x['id']!r}")
        if x["family"] not in FAMS:
            mismatch(f"unknown family {x['family']!r}")
        if x["expect"] != FAMS[x["family"]][1]:
            mismatch(f"{x['id']}: expect {x['expect']!r} for "
                     f"{x['family']}")
        if not isinstance(x["setup"], list) or not isinstance(
                x["question"], str):
            mismatch(f"{x['id']}: setup not a list / question not a string")
        if x["expect"] == "ANSWER" and not (isinstance(x["gold"], str)
                                            and x["gold"].strip()):
            mismatch(f"{x['id']}: ANSWER item without a gold string")
        if x["family"] == "trap" and x["gold"] is not None:
            mismatch(f"{x['id']}: trap gold is not null")
        cnt[x["family"]] += 1
        ids.append(x["id"])
    if len(set(ids)) != 80:
        mismatch("duplicate panel ids")
    for f, (n, _e) in FAMS.items():
        if cnt[f] != n:
            mismatch(f"family {f} has {cnt[f]} items, want {n}")
    for b in base:
        if set(b) != BFIELDS:
            mismatch(f"base221 fields {sorted(b)} != {sorted(BFIELDS)}")
        values_of(b["stored_after_setup"], b["id"])
    if {b["id"] for b in base} != set(ids):
        mismatch("base221 ids != panel ids")
    for nm, rr in (("rows237b", rows), ("rows221", rows221)):
        if sorted(r["id"] for r in rr) != sorted(ids):
            mismatch(f"{nm} ids != panel ids")
    print("SCHEMA OK")
    # ---------------- score
    B = {b["id"]: b for b in base}
    PN = {x["id"]: x for x in panel}
    R221 = {r["id"]: r for r in rows221}
    tot = {f: 0 for f in FAMS}
    right = {f: 0 for f in FAMS}
    cases, new_wrong_items, base_vg_traps, new_vg_traps = [], [], [], []
    writes = 0
    reproduced = 0
    for r in sorted(rows, key=lambda r: r["id"]):
        b = B[r["id"]]
        px = PN[r["id"]]
        fam = px["family"]
        rep = str(r["reply"]).strip()
        brep = str(b["base_reply"]).strip()
        vals = values_of(b["stored_after_setup"], r["id"])
        golds = [g.strip() for g in str(px["gold"] or "").split(";")
                 if g.strip()]
        gl = {art(g) for g in golds}
        wrong = sorted({v for v in vals if art(v) not in gl
                        and has(v, rep)})
        bwrong = sorted({v for v in vals if art(v) not in gl
                         and has(v, brep)})
        if fam == "trap":
            wrong = sorted({v for v in vals if has(v, rep)})
            bwrong = sorted({v for v in vals if has(v, brep)})
            ok = not wrong
            if bwrong:
                base_vg_traps.append(r["id"])
            if wrong and not bwrong:
                new_vg_traps.append(r["id"])
        elif fam == "control":
            ok = rep == brep
        else:
            low = rep.lower().replace("’", "'")
            ok = all(g.lower() in rep.lower() for g in golds) and not \
                low.startswith(("i don't know", "i do not know"))
        nw = sorted(set(wrong) - set(bwrong))
        if nw:
            new_wrong_items.append((r["id"], nw))
        wrote = bool(r.get("question_wrote"))
        writes += wrote
        tot[fam] += 1
        right[fam] += int(ok)
        r221 = R221[r["id"]]
        reproduced += int(str(r221["reply"]).strip() == brep)
        cases.append({"id": r["id"], "family": fam,
                      "question": px["question"],
                      "gold": golds, "reply": rep, "base_reply": brep,
                      "arm221_reply": str(r221["reply"]).strip(),
                      "moved_vs_base": rep != brep, "right": ok,
                      "wrong_values": wrong, "base_wrong_values": bwrong,
                      "new_wrong_values": nw, "question_wrote": wrote,
                      "q_ms": r.get("q_ms"), "q_ms_221": r221.get("q_ms")})
    m5 = (statistics.median(r["q_ms"] for r in rows)
          - statistics.median(r["q_ms"] for r in rows221))
    bars = {"synonym": 0.85, "new_relation": 0.80, "date": 0.80}
    marks = {}
    for f, bar in bars.items():
        marks[f"M1 {f}"] = (f"{right[f]}/{tot[f]}", right[f] >= bar * tot[f])
    marks["M1 trap new value-giving"] = (f"{len(new_vg_traps)}",
                                         not new_vg_traps)
    marks["M1 control identical"] = (f"{right['control']}/{tot['control']}",
                                     right["control"] == tot["control"])
    marks["M1 new wrong values"] = (f"{len(new_wrong_items)}",
                                    not new_wrong_items)
    marks["M1 question writes"] = (f"{writes}", writes == 0)
    marks["M5 median added ms"] = (f"{m5:+.2f}", m5 <= 5.0)
    summ = {"marks": {k: {"result": v[0], "pass": v[1]}
                      for k, v in marks.items()},
            "per_family": {f: [right[f], tot[f]] for f in FAMS},
            "trap_value_giving_in_base221": base_vg_traps,
            "trap_new_value_giving": new_vg_traps,
            "new_wrong_value_items": new_wrong_items,
            "arm221_reproduces_base221": f"{reproduced}/80",
            "M1_pass": all(v[1] for k, v in marks.items()
                           if k.startswith("M1")),
            "cases": cases}
    json.dump(summ, open(sys.argv[5], "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    for k, v in marks.items():
        print(f"{k}: {v[0]} {'pass' if v[1] else 'FAIL'}")
    print(f"trap value-giving already in base221: {base_vg_traps}")
    print(f"221 arm reproduces base221: {reproduced}/80")
    print("M1", "PASS" if summ["M1_pass"] else "FAIL")


if __name__ == "__main__":
    main()
