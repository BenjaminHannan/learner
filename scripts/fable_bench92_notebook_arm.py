#!/usr/bin/env python3
"""Experiment 92, notebook arm (STRUCTURED INPUT — triples, not English).

Runs every Fable-Edit-SCALE split from data/open/bench92/ through the SAME
notebook + QualifierAwareReasoner + scoring as exp 65 (imported read-only,
never edited):

  S1 3-hop single-edit      fresh notebook per item
  S2 4-hop single-edit      fresh notebook per item
  S3 multi-edit same chain  fresh notebook per item
  S4 batch 1,000 cases     ONE notebook taught everything, then all questions
  S5 conflicting edits      fresh notebook per item (edit, then override)
  S6 reversal at 3 hops     fresh notebook per item

Every item reported (correct/wrong/miss), nothing averaged. S4 additionally
reports per-query latency p50/p99 and notebook size.

Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench92_notebook_arm.py --selftest
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench92_notebook_arm.py --run
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench65_notebook_arm as B65  # noqa: E402 (read-only; never edited)
import fable_notebook_contract as C  # noqa: E402 (read-only; never edited)
from fable_qual56_reasoner import QualifierAwareReasoner  # noqa: E402

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench92-20260921"
DATA = ROOT / "data" / "open" / "bench92"

SPLITS = ["fable_edit92_s1_3hop", "fable_edit92_s2_4hop",
          "fable_edit92_s3_multiedit", "fable_edit92_s4_batch",
          "fable_edit92_s5_conflict", "fable_edit92_s6_rev3hop"]


def run_batch_s4(items: list[dict], scratch: Path) -> tuple[list[dict], dict]:
    """Teach all 1,000 cases into ONE notebook (case_id order), then ask all."""
    nb = C.Notebook(scratch / "s4-batch")
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

    # Phase 1: every case's originals (correction=False — cross-case
    # conflicts are REFUSED with CONFLICT; first writer wins, counted).
    for it in items:
        for k, t in enumerate([t for t in it["taught"] if not t.get("edit")]):
            res = nb.assert_fact(f"s4-o-{it['id']}-{k}", "listening",
                                 "taught", eid(t["subject"]), t["relation"],
                                 {"entity": eid(t["object"])},
                                 correction=False, raw=t.get("sentence_en"))
            taught_facts += 1
            if res.status == C.CONFLICT:
                conflicts += 1
    # Phase 2: every case's edits (correction=True — supersede, even
    # across cases; this is the interference under test).
    for it in items:
        for k, t in enumerate([t for t in it["taught"] if t.get("edit")]):
            res = nb.assert_fact(f"s4-e-{it['id']}-{k}", "listening",
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
        return lat_sorted[min(len(lat_sorted) - 1,
                              int(q * len(lat_sorted)))]
    ev_dir = scratch / "s4-batch"
    ev_files = sorted(ev_dir.glob("*.jsonl")) if ev_dir.exists() else []
    size = {"event_files": len(ev_files),
            "events_bytes": sum(p.stat().st_size for p in ev_files),
            "entities": len(eids), "relations": len(rels),
            "teach_attempts": taught_facts, "teach_conflicts": conflicts}
    try:
        size["events_lines"] = sum(1 for p in ev_files
                                   for _ in p.open(encoding="utf-8"))
    except OSError:
        size["events_lines"] = -1
    info = {"p50_ms": round(pct(0.50), 3), "p99_ms": round(pct(0.99), 3),
            "mean_ms": round(statistics.mean(lat), 3),
            "max_ms": round(max(lat), 3), **size}
    return rows, info


def cmd_run(_args) -> int:
    ART.mkdir(parents=True, exist_ok=True)
    scratch = ART / "scratch92"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    run_dir = ART / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    summary: dict[str, dict] = {}
    for stem in SPLITS:
        items = B65.load_items(DATA / f"{stem}.jsonl")
        if stem == "fable_edit92_s4_batch":
            rows, info = run_batch_s4(items, scratch / "s4")
            (run_dir / "bench92_s4_info.json").write_text(
                json.dumps(info, indent=1), encoding="utf-8")
            print(f"  S4 info: {json.dumps(info, sort_keys=True)}")
        else:
            rows = [B65.run_item(it, scratch / stem) for it in items]
        table = B65.score(rows)
        (run_dir / f"bench92_{stem.split('_')[2]}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        summary[stem] = table
        print(f"{stem}: items={len(rows)}")
        for typ, cell in sorted(table.items()):
            print(f"    {typ}: {cell}")
        fails = [r for r in rows if r["verdict"] in ("WRONG", "MISS")][:5]
        for r in fails:
            print("    FAIL:", json.dumps(r, ensure_ascii=False)[:300])
    (run_dir / "bench92_notebook_summary.json").write_text(
        json.dumps({"seconds": round(time.time() - t0, 1),
                    "summary": summary}, indent=1), encoding="utf-8")
    shutil.rmtree(scratch, ignore_errors=True)
    return 0


def cmd_selftest(_args) -> int:
    items = [
        {"id": "t3hop", "type": "mquake-s1-3hop", "expected": "answer",
         "frame": {"name": "Ann", "relations": ["lives_in", "capital_of",
                                                "mayor_of"]},
         "taught": [{"subject": "Ann", "relation": "lives_in",
                     "relation_label": "lives in", "object": "France",
                     "sentence_en": "x"},
                    {"subject": "France", "relation": "capital_of",
                     "relation_label": "capital of", "object": "Paris",
                     "sentence_en": "x"},
                    {"subject": "Paris", "relation": "mayor_of",
                     "relation_label": "mayor of", "object": "Hidalgo",
                     "sentence_en": "x"}],
         "question": "q", "gold": ["Hidalgo"], "gold_aliases": []},
        {"id": "tconf", "type": "mquake-s5-conflict", "expected": "answer",
         "frame": {"name": "Ann", "relations": ["lives_in", "capital_of"]},
         "taught": [{"subject": "Ann", "relation": "lives_in",
                     "relation_label": "lives in", "object": "France",
                     "sentence_en": "x"},
                    {"subject": "France", "relation": "capital_of",
                     "relation_label": "capital of", "object": "Paris",
                     "sentence_en": "x"},
                    {"subject": "France", "relation": "capital_of",
                     "relation_label": "capital of", "object": "Lyon",
                     "sentence_en": "y", "edit": True},
                    {"subject": "France", "relation": "capital_of",
                     "relation_label": "capital of", "object": "Paris",
                     "sentence_en": "x", "edit": True, "override": True}],
         "question": "q", "gold": ["Paris"], "gold_aliases": []},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        rows = [B65.run_item(it, Path(tmp)) for it in items]
        s4rows, info = run_batch_s4(items, Path(tmp))
    ok = ([r["verdict"] for r in rows] == ["correct", "correct"]
          and [r["verdict"] for r in s4rows] == ["correct", "correct"]
          and info["p50_ms"] >= 0 and info["entities"] > 0)
    print("selftest:", [r["verdict"] for r in rows],
          [r["verdict"] for r in s4rows], "->", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 92 notebook arm")
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
