"""Export TEACH and GEN to the student contract: JSONL, one example per line, FRESH-EN-R3 shape, family = kind name.
200,000 counts QUESTIONS in both arms. ASCII, len(panel)+1+len(question) <= 208, canonical_answer <= 32. Drops any row whose
passage/paraphrase from FRESH-EN-R3, NEW-KINDS-R5, NEW-KINDS2-R6, GEN-HELDOUT-R4 appears verbatim.
Usage: python3 export.py --teach out/teach_all.jsonl --gen out/gen_200k.jsonl --dest DIR   (inputs are the flat row files)"""
import argparse, json, hashlib, random
from pathlib import Path
from collections import Counter, defaultdict
from teach import ascii_clean, contract_ok, norm

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--teach"); ap.add_argument("--gen"); ap.add_argument("--dest", required=True); ap.add_argument("--rows", type=int, default=200000)
a = ap.parse_args()
dest = Path(a.dest); dest.mkdir(parents=True, exist_ok=True)
ev, evq = set(), set()
for f in ("FRESH-EN-R3", "NEW-KINDS-R5", "NEW-KINDS2-R6", "GEN-HELDOUT-R4"):
    for e in json.load(open(HERE / "eval" / f"{f}.json"))["examples"]:
        ev |= {norm(e["source_text"]), norm(e["paraphrase"])}
        evq |= {norm(q["question"]) for q in e["questions"]}
manifest = {}
for arm, src in (("teach", a.teach), ("gen", a.gen)):
    if not src:
        continue
    rows, drop, qonly = [], Counter(), 0
    for l in open(src):
        r = json.loads(l)
        for k in ("source_text", "paraphrase", "question", "canonical_answer"):
            r[k] = ascii_clean(r[k])
        r["accepted_answers"] = [ascii_clean(x) for x in r["accepted_answers"]]
        if not contract_ok(r["source_text"], r["paraphrase"], r["question"], r["canonical_answer"]):
            drop["contract"] += 1; continue
        if {norm(r["source_text"]), norm(r["paraphrase"])} & ev:
            drop["eval_passage_verbatim"] += 1; continue
        if norm(r["question"]) in evq:
            qonly += 1          # question text alone repeats (generic questions); passage never does, so the row is kept
        rows.append(r)
    random.Random(1).shuffle(rows) if arm == "teach" else None
    rows = rows[:a.rows]
    assert len(rows) == a.rows, (arm, len(rows), dict(drop))
    ex = defaultdict(lambda: None); order = []
    for r in rows:
        key = (r["kind"], r["source_text"], r["paraphrase"])
        if ex[key] is None:
            ex[key] = {"id": f"{arm}_{len(order)}", "family": r["kind"], "source_text": r["source_text"], "paraphrase": r["paraphrase"], "questions": []}; order.append(key)
        ex[key]["questions"].append({"question": r["question"], "type": r["type"], "canonical_answer": r["canonical_answer"], "accepted_answers": r["accepted_answers"]})
    p = dest / f"{arm}.jsonl"
    with open(p, "w") as f:
        for k in order:
            f.write(json.dumps(ex[k]) + "\n")
    nq = sum(len(ex[k]["questions"]) for k in order)
    assert nq == a.rows
    manifest[arm] = {"file": p.name, "examples": len(order), "questions": nq, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size,
                     "per_family": dict(Counter(ex[k]["family"] for k in order)), "types": dict(Counter(q["type"] for k in order for q in ex[k]["questions"])),
                     "dropped_at_export": dict(drop), "question_text_equal_to_an_eval_question_kept": qonly}
    print(arm, manifest[arm]["examples"], "examples", nq, "questions", manifest[arm]["sha256"][:12], dict(drop))
(dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))
