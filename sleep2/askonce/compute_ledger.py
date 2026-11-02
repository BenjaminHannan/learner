"""Compute accounting in token-passes: a trained token = 3 units (forward+backward), a reference-only forward token = 1 unit.
Also counts pre-written text items (the stand-in for Batches calls) per arm per night. Pure Python."""
from .config import ANCHOR_W, LEDGER_TOL  # noqa: F401  (ANCHOR_W re-exported for readers)

TRAIN, REF = 3, 1


def item_units(item, length_fn):
    """Units of one training item. sft: 3*len. pair: 3*(chosen+rejected) trained + 1*(chosen+rejected) reference forward."""
    if item["kind"] == "sft":
        return {"train": TRAIN * length_fn(item["prompt"], item["target"]), "ref": 0}
    n = length_fn(item["prompt"], item["chosen"]) + length_fn(item["prompt"], item["rejected"])
    return {"train": TRAIN * n, "ref": REF * n}


def anchor_units(n_steps, anchor_len):
    """One anchor sequence per optimizer step: student forward+backward (3) + teacher forward (1). Identical in every arm."""
    return {"train": TRAIN * anchor_len * n_steps, "ref": REF * anchor_len * n_steps}


def total(parts):
    return sum(p["train"] + p["ref"] for p in parts)


def night_ledger(shared_items, slice_items, n_steps, anchor_len, length_fn, calls):
    sh = [item_units(i, length_fn) for i in shared_items]
    sl = [item_units(i, length_fn) for i in slice_items]
    an = anchor_units(n_steps, anchor_len)
    return {"shared": total(sh), "slice": total(sl), "anchor": an["train"] + an["ref"], "total": total(sh) + total(sl) + an["train"] + an["ref"],
            "calls": calls, "n_shared": len(shared_items), "n_slice": len(slice_items)}


def spread(totals):
    """(max-min)/mean of per-arm totals."""
    v = list(totals.values())
    m = sum(v) / len(v)
    return (max(v) - min(v)) / m if m else 0.0


def assert_equal(per_arm, tol=LEDGER_TOL, what=""):
    """per_arm: {arm: ledger dict}. Raises if token-pass totals differ by more than tol (as a fraction of the mean) or Batches-call counts differ."""
    sp = spread({a: l["total"] for a, l in per_arm.items()})
    if sp > tol:
        raise AssertionError(f"compute ledger {what}: arms differ by {100 * sp:.1f}% > {100 * tol:.0f}%: " + str({a: l["total"] for a, l in per_arm.items()}))
    calls = {a: l["calls"] for a, l in per_arm.items()}
    if len(set(calls.values())) != 1:
        raise AssertionError(f"batches-call counts differ {what}: {calls}")
    return sp
