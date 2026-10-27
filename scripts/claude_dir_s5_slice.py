#!/usr/bin/env python3
"""dir-s5 (2026-09-29): pick the 100-question LongMemEval-S dev slice by id only and hash it. New file.

Reads only question_id and question_type of longmemeval_s_cleaned.json (HF xiaowu0162/longmemeval-cleaned, sha256
pinned below). No question, answer or session text is read or printed. Order inside a group is by
sha256(SEED + ":" + question_id), so the pick does not depend on file order. Quotas (94 not-abstention + 6 abstention):
multi-session 23, temporal-reasoning 23, knowledge-update 14, single-session-user 13, single-session-assistant 11,
single-session-preference 10; then 6 abstention ids (question_id ends "_abs") from all 30. Abstention ids are
taken first and removed from their type's pool, so the type quotas are for not-abstention questions.

  python -B scripts/claude_dir_s5_slice.py build DATA.json OUTDIR     writes dev100.ids.txt, final400.ids.sha256.txt, SEAL
  python -B scripts/claude_dir_s5_slice.py check DATA.json            recomputes and compares with the committed files
"""
import hashlib, json, sys
from pathlib import Path

DATA_SHA = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
SEED = "dir-s5-2026-09-29"
QUOTA = {"multi-session": 23, "temporal-reasoning": 23, "knowledge-update": 14, "single-session-user": 13,
         "single-session-assistant": 11, "single-session-preference": 10}
N_ABS = 6
HERE = Path(__file__).resolve().parents[1] / "artifacts" / "claude-dir-s5-lme-20260929"


def key(qid):
    return hashlib.sha256((SEED + ":" + qid).encode()).hexdigest()


def pick(rows):
    """rows: list of (question_id, question_type). Returns (dev ids sorted, final ids sorted)."""
    ab = sorted((q for q, _ in rows if q.endswith("_abs")), key=key)[:N_ABS]
    dev = set(ab)
    for t, n in QUOTA.items():
        pool = sorted((q for q, ty in rows if ty == t and not q.endswith("_abs") and q not in dev), key=key)
        dev.update(pool[:n])
    assert len(dev) == 100, len(dev)
    final = sorted(q for q, _ in rows if q not in dev)
    return sorted(dev), final


def load(path):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != DATA_SHA:
        raise SystemExit("DATA-SHA-MISMATCH")
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return [(x["question_id"], x["question_type"]) for x in d]


def main():
    cmd, data = sys.argv[1], sys.argv[2]
    rows = load(data)
    dev, final = pick(rows)
    types = dict(rows)
    devtxt = "\n".join(f"{q}\t{types[q]}" for q in dev) + "\n"
    fh = hashlib.sha256("\n".join(final).encode()).hexdigest()
    if cmd == "build":
        out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
        (out / "dev100.ids.txt").write_text(devtxt)
        (out / "final400.ids.sha256.txt").write_text(fh + "  sha256 of the 400 remaining question_ids, sorted, joined by \\n (ids not stored)\n")
        (out / "SEAL-slice.sha256.txt").write_text(
            f"{hashlib.sha256(devtxt.encode()).hexdigest()}  dev100.ids.txt (as written)\n{DATA_SHA}  longmemeval_s_cleaned.json\n{fh}  final400 ids\n")
    else:
        assert (HERE / "dev100.ids.txt").read_text() == devtxt, "DEV-MISMATCH"
        print("slice ok", len(dev), fh)
    from collections import Counter
    print(Counter(types[q] for q in dev), sum(q.endswith("_abs") for q in dev), "abstention")


if __name__ == "__main__":
    main()
