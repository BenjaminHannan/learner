"""Grading, run in the cloud after the GPU job (the API key is not on the GPU box).

Step 1 (free): exact match after NFKC / casefold (row['em']; for never-taught items 'em' means the answer abstains).
Step 2 (Batches, Haiku): every row that did NOT match exactly gets one grader call for answer variants; identical (question, gold, answer) triples are asked once.
Step 3 (Batches, Sonnet): a seeded sample of 60 Haiku-graded rows is regraded by Sonnet; Cohen's kappa between the two is reported.
The final label per row is  correct = em or haiku_correct.

  python -m sleep2.recallread.grade requests --results DIR --dry-run | --submit [--limit 5]
  python -m sleep2.recallread.grade collect  --results DIR
  python -m sleep2.recallread.grade exact-only --results DIR     # no API: correct = em (for a first look)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from . import batchlib
from .world import norm

HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"
SYS = "You grade short answers for a memory experiment. Reply with one JSON object and nothing else."
N_KAPPA = 60


def load_results(resdir: Path):
    rows = []
    for f in sorted((resdir / "results" / "recallread").glob("*_*.jsonl")):
        if f.name.startswith("graded"):
            continue
        rows += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    return rows


def key_of(r):
    if "arm" not in r:
        return hashlib.sha1(r["answer"].encode()).hexdigest()[:16]
    return hashlib.sha1(f"{r['q']}|{r['gold']}|{norm(r['answer'])}".encode()).hexdigest()[:16]


def grader_user(r):
    if r["split"] == "never":
        return (f"Question (the notes never mention this person or thing): {r['q']}\nModel answer: {r['answer']}\n"
                "The right behaviour is to say it does not know / the notes do not say. Is the model answer such an abstention, "
                "asserting no specific fact? Reply {\"correct\": true} or {\"correct\": false}.")
    return (f"Question: {r['q']}\nGold answer: {r['gold']}\nModel answer: {r['answer']}\n"
            "Is the model answer correct? It is correct if it names the gold answer (spelling variants, abbreviations or extra words are fine) "
            "and does not give a different answer. Reply {\"correct\": true} or {\"correct\": false}.")


def pending(rows):
    seen = {}
    for r in rows:
        if not r["em"] and r["answer"].strip():
            seen.setdefault(key_of(r), r)
    return seen


def requests_for(rows, kappa_seed=0):
    pend = pending(rows)
    haiku = [dict(custom_id=f"h:{k}", params=batchlib.params(HAIKU, SYS, grader_user(r), 30)) for k, r in sorted(pend.items())]
    ks = random.Random(kappa_seed).sample(sorted(pend), min(N_KAPPA, len(pend)))
    sonnet = [dict(custom_id=f"s:{k}", params=batchlib.params(SONNET, SYS, grader_user(pend[k]), 30)) for k in ks]
    return haiku, sonnet


def parse(t):
    j = batchlib.parse_json(t)
    return j.get("correct") if isinstance(j, dict) and isinstance(j.get("correct"), bool) else None


def kappa(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return None
    n = len(pairs)
    po = sum(x == y for x, y in pairs) / n
    pa, pb = sum(x for x, _ in pairs) / n, sum(y for _, y in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def write_graded(resdir: Path, rows, labels):
    out = resdir / "results" / "recallread" / "graded"
    out.mkdir(exist_ok=True)
    by = {}
    for r in rows:
        r = dict(r)
        r["correct"] = bool(r["em"] or labels.get(key_of(r)) is True)
        by.setdefault((r["arm"], r["seed"]), []).append(r)
    for (arm, s), rs in by.items():
        (out / f"{arm}_{'s0' if s == '0' else s}.jsonl").write_text("\n".join(json.dumps({k: r[k] for k in ("arm", "seed", "row_id", "split", "dev", "index", "em", "correct", "bridge_named", "hit3_hop1", "hit3_hop2", "ledger") if k in r}) for r in rs) + "\n")
    return len(by)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["requests", "collect", "exact-only"])
    ap.add_argument("--results", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--assume-rows", type=int, default=None, help="dry-run only: worst-case cost if this many rows all need the grader (e.g. 7100)")
    a = ap.parse_args()
    res = Path(a.results)
    rows = load_results(res) if not a.assume_rows else [dict(q="Where does the mentor of Skatoutra live?", gold="Vrozhabo", answer=f"some answer {i}", split="twohop_nat", em=False) for i in range(a.assume_rows)]
    state = res / "grade_batches.json"
    if a.cmd == "exact-only":
        print(write_graded(res, rows, {}), "graded files (exact match only)")
    elif a.cmd == "requests":
        haiku, sonnet = requests_for(rows)
        if a.submit and not a.dry_run:
            batchlib.submit("grade_haiku", haiku, 12, state, a.limit)
            batchlib.submit("grade_sonnet", sonnet, 12, state, a.limit)
        else:
            batchlib.print_dry_run("grade_haiku", haiku, 12)
            batchlib.print_dry_run("grade_sonnet", sonnet, 12)
    else:
        st = json.loads(state.read_text())
        h = batchlib.collect(st["grade_haiku"][-1]["batch_id"])
        s = batchlib.collect(st["grade_sonnet"][-1]["batch_id"])
        labels = {k[2:]: parse(v) for k, v in h.items()}
        ks = [k[2:] for k in s]
        kap = kappa([labels.get(k) for k in ks], [parse(s["s:" + k]) for k in ks])
        n = write_graded(res, rows, labels)
        (res / "results" / "recallread" / "grade_summary.json").write_text(json.dumps(dict(
            haiku_calls=len(h), haiku_unparsed=sum(v is None for v in labels.values()), sonnet_regrade=len(ks), kappa_haiku_vs_sonnet=kap)))
        print(f"graded {n} files; kappa(haiku, sonnet) over {len(ks)} = {kap}")


if __name__ == "__main__":
    main()
