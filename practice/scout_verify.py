"""Container-side check of the scout's finds (run AFTER the Mac run, with the API key in the environment; the key is never printed).
usage: LEARNER_ANTHROPIC_API_KEY=... python -m practice.scout_verify --finds path/to/finds.jsonl [--out practice/data/scout_pool.jsonl] [--max N] [--dry-run]
Each find is re-checked locally (shape, test100 12-word shingle, 8-gram Jaccard > 0.5 against practice/test/sibling puzzles and against each other), then Sonnet
(Message Batches, same helper as practice/testgen) is asked whether the puzzle and the answer are consistent and the puzzle is self-contained. Only "yes" is kept.
The output rows have the practice-pool fields (id, kind, prompt, answer, answer_type, source, title) plus source_url / answer_url. A Sonnet "yes" is a check, not a proof."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from practice.scout import Dedup, JACCARD_MAX, PDATA, check_shape, jl, load_reference  # noqa: E402
from practice.web import Guard, shingle_hashes  # noqa: E402

LABEL = "scout_verify"

PROMPT = """You are checking a puzzle that was copied from a web page by an automated scout. Decide two things.
1. CONSISTENT: is the stated answer correct for the puzzle as written? Work it out yourself; do not trust the answer.
2. SELF-CONTAINED: can a solver answer from the text alone (no missing figure, picture, link, table, earlier part, or outside file), with exactly one clear final answer in the stated form?

Puzzle title: {title}
Puzzle:
{prompt}

Stated answer ({answer_type}): {answer}

Reply with only a JSON object: {{"consistent": true or false, "self_contained": true or false, "verdict": "yes" or "no", "note": "one short sentence"}}
verdict is "yes" only if both are true."""


def build_requests(rows, req, model):
    return [req(r["id"], model, PROMPT.format(title=r["title"], prompt=r["prompt"], answer=r["answer"], answer_type=r["answer_type"]), max_tokens=3000) for r in rows]


def prefilter(finds, data_dir=PDATA):
    """-> (kept rows, rejected {id: reason}). Local checks only."""
    test, _, dd = load_reference(data_dir)
    guard = Guard(test)
    kept, rej, seen = [], {}, Dedup()
    for r in finds:
        rid = r.get("id", "?")
        clean, why = check_shape(dict(r))
        if clean is None:
            rej[rid] = why
            continue
        if guard.sh and shingle_hashes(clean["prompt"]) & guard.sh:
            rej[rid] = "test_overlap"
            continue
        j, other = dd.nearest(clean["prompt"])
        j2, other2 = seen.nearest(clean["prompt"])
        if max(j, j2) > JACCARD_MAX:
            rej[rid] = "duplicate:" + str(other if j >= j2 else other2)
            continue
        seen.add(rid, clean["prompt"])
        kept.append({**r, **clean, "id": rid})
    return kept, rej


def parse_verdict(text):
    from sleep2.askonce.batches import parse_json
    try:
        o = parse_json(text)
        return bool(o.get("verdict") == "yes" and o.get("consistent") is True and o.get("self_contained") is True), str(o.get("note", ""))[:200]
    except Exception:  # noqa: BLE001
        return False, "unparsable reply"


def to_pool_row(r, note=""):
    return {"id": r["id"], "kind": "scout", "prompt": r["prompt"], "answer": r["answer"], "answer_type": r["answer_type"], "source": "scout", "title": r["title"],
            "source_url": r["source_url"], "answer_url": r["answer_url"], "topic": r.get("topic"), "sonnet_note": note}


def main(argv=None, run_batch=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--finds", required=True)
    ap.add_argument("--out", default=str(PDATA / "scout_pool.jsonl"))
    ap.add_argument("--max", type=int, default=1000)
    ap.add_argument("--dry-run", action="store_true", help="local checks only; no API call")
    a = ap.parse_args(argv)
    from sleep2.askonce.batches import req
    from sleep2.askonce.config import SONNET
    rows, rej = prefilter(jl(a.finds))
    rows = rows[:a.max]
    print(f"finds {len(rows) + len(rej)}: {len(rows)} pass the local checks, {len(rej)} rejected {sorted(set(v.split(':')[0] for v in rej.values()))}", flush=True)
    if a.dry_run or not rows:
        return 0
    if run_batch is None:
        from sleep2.askonce.batches import run_batch
    out, _ = run_batch(build_requests(rows, req, SONNET), LABEL)
    keep, no = [], 0
    for r in rows:
        ok, note = parse_verdict(out.get(r["id"], ""))
        if ok:
            keep.append(to_pool_row(r, note))
        else:
            no += 1
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in keep:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"kept {len(keep)} of {len(rows)} (Sonnet said no/unsure/unparsable for {no}); wrote {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
