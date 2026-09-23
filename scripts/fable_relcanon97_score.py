"""Exp 97 scoring: import canon() from exp-63 read-only and score the sealed panel once.

Run exactly once for the registered run (introspection + scoring happen in
this single invocation; the sealed panel is never modified). Stdlib only
apart from the read-only canon import.
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts" / "fable-relcanon97-20260921"

ABSTAIN = {
    "unknown", "unsure", "missing_fact", "missing", "abstain", "abstained",
    "none", "null", "n_a", "unk", "uncertain", "cannot_tell", "no_match",
}


def canon_norm(s: str) -> str:
    return s.strip().lower().replace("-", "_").replace(" ", "_")


def coerce(raw) -> tuple[str, str]:
    """Return (raw_repr, normalised)."""
    r = raw
    if isinstance(r, (tuple, list)) and r:
        r = r[0]
    if isinstance(r, dict):
        for k in ("relation", "id", "canonical", "label", "value"):
            if r.get(k) is not None:
                r = r[k]
                break
        else:
            r = str(r)
    rep = repr(r)
    if r is None:
        return rep, "none"
    return rep, canon_norm(str(r))


def resolve_entry(mod):
    cands = []
    if hasattr(mod, "canon"):
        cands.append(("canon", getattr(mod, "canon")))
    for k, v in vars(mod).items():
        if callable(v) and "canon" in k.lower() and k != "canon":
            cands.append((k, v))
    log = {"module_dir": sorted(vars(mod).keys()), "tried": []}
    for name, fn in cands:
        try:
            sig = str(inspect.signature(fn))
        except Exception:
            sig = "?"
        try:
            out = fn("capital")
            _, n = coerce(out)
            log["tried"].append({"name": name, "sig": sig, "probe_ok": True})
            log["chosen"] = name
            return fn, log
        except Exception as ex:  # noqa: BLE001
            log["tried"].append(
                {"name": name, "sig": sig, "probe_ok": False, "err": repr(ex)})
    raise RuntimeError(f"no callable canon entry found: {json.dumps(log)}")


def score(fn, items):
    rows = []
    for it in items:
        raw = fn(it["phrase"])
        rep, n = coerce(raw)
        gold_n = canon_norm(it["gold"])
        if n in ABSTAIN:
            verdict = "abstain"
        elif n == gold_n:
            verdict = "correct"
        else:
            verdict = "wrong"
        rows.append({"id": it["id"], "phrase": it["phrase"], "gold": it["gold"],
                     "raw": rep, "norm": n, "verdict": verdict})
    return rows


def main() -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    import fable_relcanon63_canon as canon_mod  # noqa: E402  read-only use

    fn, log = resolve_entry(canon_mod)
    print("ENTRY:", json.dumps(log))

    par = json.loads((ART / "test_paraphrases.json").read_text(encoding="utf-8"))
    fab = json.loads((ART / "test_fabricated.json").read_text(encoding="utf-8"))
    near = json.loads((ART / "test_nearmiss.json").read_text(encoding="utf-8"))
    assert len(par) == 300 and len(fab) == 150 and len(near) == 50

    rp, rf, rn = score(fn, par), score(fn, fab), score(fn, near)
    (ART / "results_full.json").write_text(
        json.dumps({"entry": log, "paraphrases": rp, "fabricated": rf,
                    "nearmiss": rn}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")

    def tally(rows):
        c = {"correct": 0, "abstain": 0, "wrong": 0}
        for r in rows:
            c[r["verdict"]] += 1
        return c

    tp, tf, tn = tally(rp), tally(rf), tally(rn)
    print(f"PARAPHRASE n=300 correct={tp['correct']} abstain={tp['abstain']} "
          f"wrong={tp['wrong']} K1_pass={tp['wrong'] <= 3}")
    print(f"FABRICATED n=150 unknown={tf['abstain']} "
          f"concrete={tf['correct'] + tf['wrong']} K2_pass={tf['abstain'] >= 147}")
    print(f"NEARMISS n=50 correct={tn['correct']} abstain={tn['abstain']} "
          f"wrong={tn['wrong']} K3_pass={tn['wrong'] == 0}")
    print("--- WRONG (paraphrase) ---")
    for r in rp:
        if r["verdict"] == "wrong":
            print(f"{r['id']} | {r['phrase']!r} | gold={r['gold']!r} | raw={r['raw']}")
    print("--- CONCRETE (fabricated; expected UNKNOWN) ---")
    for r in rf:
        if r["verdict"] != "abstain":
            print(f"{r['id']} | {r['phrase']!r} | raw={r['raw']}")
    print("--- NEARMISS (all 50) ---")
    for r in rn:
        print(f"{r['id']} | {r['phrase']!r} | gold={r['gold']!r} | "
              f"raw={r['raw']} | {r['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
