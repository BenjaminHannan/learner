#!/usr/bin/env python3
"""Experiment 65, notebook arm (STRUCTURED INPUT — triples, not English).

For each Fable-Edit-200 item: open a FRESH notebook, teach the item's
triples (original MQuAKE facts first, then the counterfactual edit with
correction=True so the edit supersedes), ask the item's question frame via
the qualifier-aware reasoner (qual56 wrapper over reasoner50, no
qualifiers here), and score exact match after normalisation. Abstentions
(non-OK statuses) and WRONG answers (OK with a wrong value) are counted
separately.

This arm feeds triples, not English, because the ears are still in
training (rung 1 registered FAIL on coverage; rung 2 in progress). The
English-input arm awaits ears rung 2.

Additive, offline, Mac CPU, one thread. Imports fable_notebook_contract
and fable_qual56_reasoner read-only (never edits them).

Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench65_notebook_arm.py --selftest
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench65_notebook_arm.py --run
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
from fable_qual56_reasoner import QualifierAwareReasoner  # noqa: E402

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench65-20260921"
DATA_DEFAULT = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"

ABSTAIN = (C.MISSING_FACT, C.BROKEN_CHAIN, C.UNKNOWN_ENTITY, C.AMBIGUOUS)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", s.lower())).strip()


def load_items(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def run_item(item: dict, scratch: Path) -> dict:
    """Teach one item's triples to a fresh notebook, ask, score."""
    nb = C.Notebook(scratch / item["id"])
    eids: dict[str, str] = {}

    def eid(name: str) -> str:
        if name not in eids:
            res = nb.new_entity(f"ent-{len(eids)}", name)
            assert res.status == C.SAVED, res
            eids[name] = res.detail["entity_id"]
        return eids[name]

    taught = item["taught"]
    for i, rel in enumerate(sorted({t["relation"] for t in taught})):
        res = nb.declare_relation(f"rel-{i}", rel, True)
        assert res.status in (C.SAVED, C.DUPLICATE_OK), res

    teach_notes = []
    for phase in (False, True):  # originals first, then the edit (supersedes)
        for k, t in enumerate([t for t in taught if bool(t.get("edit")) == phase]):
            res = nb.assert_fact(f"f-{'e' if phase else 'o'}-{k}", "listening",
                                 "taught", eid(t["subject"]), t["relation"],
                                 {"entity": eid(t["object"])},
                                 correction=phase, raw=t.get("sentence_en"))
            if res.status not in (C.SAVED, C.DUPLICATE_OK):
                teach_notes.append(f"{t['subject']}/{t['relation']}: {res.status}")
    reasoner = QualifierAwareReasoner()
    frame = dict(item["frame"])
    t0 = time.perf_counter()
    rec = reasoner.answer(frame, nb)
    ms = (time.perf_counter() - t0) * 1000
    contract = nb.ask(frame.get("name", ""), list(frame.get("relations") or []),
                      entity_id=frame.get("entity_id"))
    out = {"id": item["id"], "type": item["type"], "expected": item["expected"],
           "status": rec["status"], "contract_status": contract.status,
           "teach_notes": teach_notes, "ms": round(ms, 3)}
    if rec["status"] == C.OK:
        out["answer"] = rec["fields"].get("answer")
    if item["expected"] == "abstain":
        out["verdict"] = ("abstain_ok" if rec["status"] in ABSTAIN
                          else ("WRONG" if rec["status"] == C.OK else "MISS"))
    else:
        golds = {norm(g) for g in item["gold"] + item.get("gold_aliases", [])}
        if rec["status"] == C.OK:
            out["verdict"] = ("correct" if norm(rec["fields"].get("answer", ""))
                              in golds else "WRONG")
        else:
            out["verdict"] = "MISS"
    return out


def score(rows: list[dict]) -> dict:
    table: dict[str, dict[str, int]] = {}
    for r in rows:
        cell = table.setdefault(r["type"], {"n": 0, "correct": 0, "wrong": 0,
                                            "miss": 0, "abstain_ok": 0,
                                            "contract_disagree": 0})
        cell["n"] += 1
        v = r["verdict"]
        cell["correct" if v in ("correct", "abstain_ok") else
             "wrong" if v == "WRONG" else "miss"] += 1
        if r["status"] != r["contract_status"]:
            cell["contract_disagree"] += 1
    return table


def cmd_run(args) -> int:
    items = load_items(Path(args.data))
    ART.mkdir(parents=True, exist_ok=True)
    scratch = ART / "scratch"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    t0 = time.time()
    rows = [run_item(it, scratch) for it in items]
    secs = time.time() - t0
    table = score(rows)
    run_dir = ART / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "bench65_rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in rows) + "\n", encoding="utf-8")
    (run_dir / "bench65_table.json").write_text(
        json.dumps({"seconds": round(secs, 1), "table": table,
                    "items": len(rows)}, indent=1), encoding="utf-8")
    shutil.rmtree(scratch, ignore_errors=True)
    print(f"items={len(rows)} seconds={secs:.1f}")
    for typ, cell in table.items():
        print(f"  {typ}: {cell}")
    wrong = [r for r in rows if r["verdict"] == "WRONG"]
    miss = [r for r in rows if r["verdict"] == "MISS"]
    print(f"WRONG={len(wrong)} MISS={len(miss)}")
    for r in (wrong + miss)[:10]:
        print("  FAIL:", json.dumps(r, ensure_ascii=False))
    return 0


def cmd_selftest(_args) -> int:
    items = [
        {"id": "t1", "type": "mquake-twohop", "expected": "answer",
         "frame": {"name": "Ann", "relations": ["lives_in", "capital_of"]},
         "taught": [{"subject": "Ann", "relation": "lives_in",
                     "relation_label": "lives in", "object": "France",
                     "sentence_en": "Ann lives in France."},
                    {"subject": "France", "relation": "capital_of",
                     "relation_label": "capital of", "object": "Paris",
                     "sentence_en": "The capital of France is Paris."}],
         "question": "q", "gold": ["Paris"], "gold_aliases": []},
        {"id": "t2", "type": "abstain-absent", "expected": "abstain",
         "frame": {"name": "Ghost", "relations": ["lives_in"]},
         "taught": [{"subject": "Ann", "relation": "lives_in",
                     "relation_label": "lives in", "object": "France",
                     "sentence_en": "Ann lives in France."}],
         "question": "q", "gold": [], "gold_aliases": []},
        {"id": "t3", "type": "abstain-broken", "expected": "abstain",
         "frame": {"name": "Ann", "relations": ["lives_in", "never_taught_rel"]},
         "taught": [{"subject": "Ann", "relation": "lives_in",
                     "relation_label": "lives in", "object": "France",
                     "sentence_en": "Ann lives in France."}],
         "question": "q", "gold": [], "gold_aliases": []},
    ]
    with tempfile.TemporaryDirectory(dir=str(ART if ART.exists()
                                     else None)) as tmp:
        rows = [run_item(it, Path(tmp)) for it in items]
    verdicts = [r["verdict"] for r in rows]
    ok = (verdicts == ["correct", "abstain_ok", "abstain_ok"]
          and all(r["status"] == r["contract_status"] for r in rows))
    print("selftest verdicts:", verdicts, "->", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 65 notebook arm (structured input)")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--data", default=str(DATA_DEFAULT))
    args = ap.parse_args()
    if args.selftest:
        return cmd_selftest(args)
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
