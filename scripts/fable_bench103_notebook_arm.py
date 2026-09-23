#!/usr/bin/env python3
"""Experiment 103, ARM A (notebook, S4 batch): exactly ONE change.

Change = the S4 case list only: S4-clean drops every case whose edited
(subject, relation) slot is also edited to a different value by another
case, or whose gold chain (any taught triple) passes through such a slot.
The reasoner and the notebook are NOT touched (imported read-only).

Also reports, as a separate observable (not a change): how many S4 edit
teaches were corrections overwriting a value an EARLIER *different* case
had taught (teach-order simulation; own-case originals excluded).

Plus the B3 control: notebook arm (unchanged code path) on S2-fresh.

Every split reported (correct/wrong/miss + n), never averaged.

Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench103_notebook_arm.py --selftest
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench103_notebook_arm.py --run
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench65_notebook_arm as B65  # noqa: E402 (read-only; never edited)
import fable_notebook_contract as C  # noqa: E402 (read-only; never edited)
from fable_qual56_reasoner import QualifierAwareReasoner  # noqa: E402 (read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench103-20260921"
DATA92 = ROOT / "data" / "open" / "bench92"
DATA103 = ROOT / "data" / "open" / "bench103"


def build_s4_clean(items: list[dict]) -> tuple[list[dict], dict]:
    """One change: filter the case list. Returns (kept, report)."""
    slot_objs: dict[tuple[str, str], set[str]] = defaultdict(set)
    for it in items:
        for t in it["taught"]:
            if t.get("edit"):
                slot_objs[(t["subject"], t["relation"])].add(t["object"])
    conflicted = {s for s, objs in slot_objs.items() if len(objs) > 1}
    kept, dropped_editors, dropped_passthru = [], [], []
    for it in items:
        ed = [(t["subject"], t["relation"]) for t in it["taught"] if t.get("edit")]
        allslots = [(t["subject"], t["relation"]) for t in it["taught"]]
        if any(s in conflicted for s in ed):
            dropped_editors.append(it["id"])
        elif any(s in conflicted for s in allslots):
            dropped_passthru.append(it["id"])
        else:
            kept.append(it)
    report = {
        "n_total": len(items),
        "n_conflicted_slots": len(conflicted),
        "conflicted_slots": sorted(
            ({"subject": s, "relation": r, "objects": sorted(slot_objs[(s, r)])}
             for (s, r) in conflicted),
            key=lambda d: (d["subject"], d["relation"])),
        "n_dropped_editors": len(dropped_editors),
        "n_dropped_passthru_only": len(dropped_passthru),
        "n_dropped_total": len(dropped_editors) + len(dropped_passthru),
        "n_kept": len(kept),
        "dropped_editors": dropped_editors,
        "dropped_passthru_only": dropped_passthru,
    }
    return kept, report


def count_cross_case_overwrites(items: list[dict]) -> dict:
    """Observable only: edit teaches overwriting an EARLIER case's value."""
    cur: dict[tuple[str, str], str] = {}
    src: dict[tuple[str, str], str] = {}
    for it in items:
        for t in [t for t in it["taught"] if not t.get("edit")]:
            cur.setdefault((t["subject"], t["relation"]), t["object"])
            src.setdefault((t["subject"], t["relation"]), it["id"])
    n = 0
    examples = []
    for it in items:
        for t in [t for t in it["taught"] if t.get("edit")]:
            s = (t["subject"], t["relation"])
            if s in cur and cur[s] != t["object"] and src[s] != it["id"]:
                n += 1
                if len(examples) < 10:
                    examples.append({"case": it["id"], "slot": list(s),
                                     "earlier_case": src[s],
                                     "earlier_value": cur[s],
                                     "new_value": t["object"]})
            cur[s] = t["object"]
            src[s] = it["id"]
    return {"cross_case_correction_overwrites": n, "examples": examples}


def run_batch(items: list[dict], scratch: Path) -> tuple[list[dict], dict]:
    """Shared-notebook batch run (same regime as exp 92 S4; list is the change)."""
    nb = C.Notebook(scratch / "batch")
    eids: dict[str, str] = {}
    conflicts = 0
    taught_facts = 0

    def eid(name: str) -> str:
        if name not in eids:
            res = nb.new_entity(f"ent-{len(eids)}", name)
            assert res.status == C.SAVED, res
            eids[name] = res.detail["entity_id"]
        return eids[name]

    rels = sorted({t["relation"] for it in items for t in it["taught"]})
    for i, rel in enumerate(rels):
        res = nb.declare_relation(f"rel-{i}", rel, True)
        assert res.status in (C.SAVED, C.DUPLICATE_OK), res

    for it in items:
        for k, t in enumerate([t for t in it["taught"] if not t.get("edit")]):
            res = nb.assert_fact(f"o-{it['id']}-{k}", "listening",
                                 "taught", eid(t["subject"]), t["relation"],
                                 {"entity": eid(t["object"])},
                                 correction=False, raw=t.get("sentence_en"))
            taught_facts += 1
            if res.status == C.CONFLICT:
                conflicts += 1
    for it in items:
        for k, t in enumerate([t for t in it["taught"] if t.get("edit")]):
            res = nb.assert_fact(f"e-{it['id']}-{k}", "listening",
                                 "taught", eid(t["subject"]), t["relation"],
                                 {"entity": eid(t["object"])},
                                 correction=True, raw=t.get("sentence_en"))
            taught_facts += 1
    reasoner = QualifierAwareReasoner()
    rows, lat = [], []
    for it in items:
        frame = dict(it["frame"])
        t0 = time.perf_counter()
        rec = reasoner.answer(frame, nb)
        ms = (time.perf_counter() - t0) * 1000
        lat.append(ms)
        golds = {B65.norm(g) for g in it["gold"] + it.get("gold_aliases", [])}
        contract = nb.ask(frame.get("name", ""),
                          list(frame.get("relations") or []))
        row = {"id": it["id"], "type": it["type"], "expected": it["expected"],
               "status": rec["status"], "contract_status": contract.status,
               "ms": round(ms, 3)}
        if rec["status"] == C.OK:
            row["answer"] = rec["fields"].get("answer")
            row["verdict"] = ("correct" if B65.norm(
                rec["fields"].get("answer", "")) in golds else "WRONG")
        else:
            row["verdict"] = "MISS"
        rows.append(row)
    lat_sorted = sorted(lat)

    def pct(q):
        return lat_sorted[min(len(lat_sorted) - 1, int(q * len(lat_sorted)))]
    info = {"p50_ms": round(pct(0.50), 3), "p99_ms": round(pct(0.99), 3),
            "mean_ms": round(statistics.mean(lat), 3),
            "max_ms": round(max(lat), 3),
            "entities": len(eids), "relations": len(rels),
            "teach_attempts": taught_facts, "teach_conflicts": conflicts}
    return rows, info


def cmd_run(_args) -> int:
    ART.mkdir(parents=True, exist_ok=True)
    run_dir = ART / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    scratch = ART / "scratch103nb"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    t0 = time.time()

    s4 = B65.load_items(DATA92 / "fable_edit92_s4_batch.jsonl")
    kept, clean_report = build_s4_clean(s4)
    overwrites = count_cross_case_overwrites(s4)
    (run_dir / "bench103_s4clean_report.json").write_text(
        json.dumps({**clean_report, **overwrites}, indent=1), encoding="utf-8")
    print(f"S4-clean: kept={clean_report['n_kept']} "
          f"dropped={clean_report['n_dropped_total']} "
          f"(editors={clean_report['n_dropped_editors']}, "
          f"passthru={clean_report['n_dropped_passthru_only']}) "
          f"conflicted_slots={clean_report['n_conflicted_slots']}")
    print(f"cross-case correction overwrites (observable): "
          f"{overwrites['cross_case_correction_overwrites']}")

    rows, info = run_batch(kept, scratch / "s4clean")
    table = B65.score(rows)
    (run_dir / "bench103_s4clean_rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in rows) + "\n", encoding="utf-8")
    (run_dir / "bench103_s4clean_info.json").write_text(
        json.dumps(info, indent=1), encoding="utf-8")
    print(f"S4-clean batch: items={len(rows)} info={json.dumps(info, sort_keys=True)}")
    for typ, cell in sorted(table.items()):
        print(f"    {typ}: {cell}")
    for r in [x for x in rows if x["verdict"] in ("WRONG", "MISS")][:5]:
        print("    FAIL:", json.dumps(r, ensure_ascii=False)[:300])

    fresh = B65.load_items(DATA103 / "fable_edit103_s2fresh_4hop.jsonl")
    fresh_rows = [B65.run_item(it, scratch / "s2fresh") for it in fresh]
    fresh_table = B65.score(fresh_rows)
    (run_dir / "bench103_s2fresh_notebook_rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in fresh_rows) + "\n", encoding="utf-8")
    print(f"S2-fresh notebook (control): items={len(fresh_rows)}")
    for typ, cell in sorted(fresh_table.items()):
        print(f"    {typ}: {cell}")

    (run_dir / "bench103_notebook_summary.json").write_text(
        json.dumps({"seconds": round(time.time() - t0, 1),
                    "s4clean": table, "s2fresh": fresh_table}, indent=1),
        encoding="utf-8")
    shutil.rmtree(scratch, ignore_errors=True)
    return 0


def cmd_selftest(_args) -> int:
    items = [
        {"id": "a", "type": "t", "expected": "answer",
         "frame": {"name": "Ann", "relations": ["lives_in", "capital_of"]},
         "taught": [{"subject": "Ann", "relation": "lives_in",
                     "object": "France", "sentence_en": "x"},
                    {"subject": "France", "relation": "capital_of",
                     "object": "Paris", "sentence_en": "x"},
                    {"subject": "France", "relation": "capital_of",
                     "object": "Lyon", "sentence_en": "y", "edit": True}],
         "question": "q", "gold": ["Lyon"], "gold_aliases": []},
        {"id": "b", "type": "t", "expected": "answer",
         "frame": {"name": "Bob", "relations": ["lives_in", "capital_of"]},
         "taught": [{"subject": "Bob", "relation": "lives_in",
                     "object": "Spain", "sentence_en": "x"},
                    {"subject": "France", "relation": "capital_of",
                     "object": "Paris", "sentence_en": "x"},
                    {"subject": "France", "relation": "capital_of",
                     "object": "Nice", "sentence_en": "y", "edit": True}],
         "question": "q", "gold": ["Nice"], "gold_aliases": []},
    ]
    kept, rep = build_s4_clean(items)
    ow = count_cross_case_overwrites(items)
    ok = (rep["n_conflicted_slots"] == 1 and rep["n_kept"] == 0
          and rep["n_dropped_editors"] == 2
          and ow["cross_case_correction_overwrites"] == 1)
    with tempfile.TemporaryDirectory() as tmp:
        rows, _info = run_batch(items, Path(tmp))
    ok = ok and all(r["verdict"] == "MISS" or r["verdict"] in
                    ("correct", "WRONG") for r in rows)
    print("selftest:", rep["n_kept"], ow["cross_case_correction_overwrites"],
          [r["verdict"] for r in rows], "->", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 103 Arm A notebook arm")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return cmd_selftest(args)
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
