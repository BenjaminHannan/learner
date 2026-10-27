"""Exp 63 (doc 68): registered test runner. Reads the FROZEN sealed inputs
(artifacts/fable-relcanon63-20260921/test_{paraphrases,fabricated}.json),
runs canon over them plus the dev.jsonl inverse round trip, recomputes the
521-coverage count, and writes results.json. No RNG, deterministic, one process.

Exit 0 always (it reports; PASS/FAIL vs PASSMARKS is judged by the reader).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fable_relcanon63_canon import canon, INVERSE_TABLE  # noqa: E402

ART = ROOT / "artifacts" / "fable-relcanon63-20260921"
FRAMES = ROOT / "data" / "open" / "webred" / "frames"
TABLE_DIR = ROOT / "data" / "open" / "wikidata-props"

A3_RELATIONS = {"capital", "capital of", "mother", "father", "child"}


def main() -> int:
    paras = json.loads((ART / "test_paraphrases.json").read_text(encoding="utf-8"))
    fabs = json.loads((ART / "test_fabricated.json").read_text(encoding="utf-8"))
    assert len(paras) == 300 and len(fabs) == 200

    a1_correct = a1_wrong = a1_abstain = 0
    for item in paras:
        name, _pid, flag = canon(item["input"])
        if name is None:
            a1_abstain += 1
        elif name == item["gold"] and flag is False:
            a1_correct += 1
        else:
            a1_wrong += 1

    a2_unknown = sum(1 for t in fabs if canon(t) == (None, None, False))

    dev_rows = [json.loads(l) for l in
                (FRAMES / "dev.jsonl").read_text(encoding="utf-8").splitlines()]
    a3_rows = [r for r in dev_rows if r.get("relation") in A3_RELATIONS]
    a3_agree = 0
    a3_rt_total = a3_rt_ok = 0
    a3_no_inverse = 0
    for r in a3_rows:
        name, pid, flag = canon(r["relation"])
        if name != r["relation"] or pid != r.get("relation_id") or flag is not False:
            continue
        a3_agree += 1
        edge = INVERSE_TABLE.get(r["relation"])
        if not edge:
            a3_no_inverse += 1
            continue
        a3_rt_total += 1
        inv_name, inv_pid = edge["inverse_name"], edge["inverse_relation_id"]
        direct = canon(inv_name)
        back = canon(inv_name + " (inverse)")
        fwd = canon(r["relation"] + " (inverse)")
        if (direct == (inv_name, inv_pid, False)
                and back == (r["relation"], r.get("relation_id"), True)
                and fwd == (inv_name, inv_pid, True)):
            a3_rt_ok += 1

    vocab = set(json.loads((FRAMES / "relations.json").read_text(
        encoding="utf-8"))["counts"])
    alias_table = json.loads((TABLE_DIR / "alias_table.json").read_text(
        encoding="utf-8"))
    covered = sorted({c for c in alias_table.values() if c in vocab})

    results = {
        "a1": {"correct": a1_correct, "wrong": a1_wrong, "abstain": a1_abstain,
               "n": 300},
        "a2": {"unknown": a2_unknown, "n": 200},
        "a3": {"rows": len(a3_rows), "agree": a3_agree,
               "roundtrip_total": a3_rt_total, "roundtrip_ok": a3_rt_ok,
               "no_declared_inverse": a3_no_inverse},
        "a4": {"covered": len(covered), "vocab": len(vocab)},
    }
    (ART / "results.json").write_text(json.dumps(results, indent=1),
                                      encoding="utf-8")
    print(json.dumps(results, indent=1))
    print(f"A1 paraphrase: {a1_correct}/300 correct, {a1_wrong} wrong, "
          f"{a1_abstain} abstain")
    print(f"A2 fabricated: {a2_unknown}/200 UNKNOWN")
    print(f"A3 dev rows: {len(a3_rows)} rows, {a3_agree} agree; round trip "
          f"{a3_rt_ok}/{a3_rt_total} ({a3_no_inverse} rows, no declared inverse)")
    print(f"A4 coverage: {len(covered)}/{len(vocab)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
