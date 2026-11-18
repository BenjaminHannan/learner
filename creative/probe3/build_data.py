"""Probe-3 training data (PREREG.md): Haiku's test sets on the 372 non-target tasks -> filtered, <= 2 per task (seed 0), 10% of tasks held out.
Usage: build_data.py [--haiku haiku_train_probes.jsonl] [--results DIR] [--out DIR]   -> train.jsonl, val.jsonl {prompt, target, task}"""
import argparse, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probe1"))
from probe_common import *  # noqa
import replay, write_probes as wp
from analyze import valid, passes

DEFAULT_HAIKU = MNT + "probe3/data/haiku_train_probes.jsonl"
MAX_SETS, VAL_FRAC, SEED = 2, 0.10, 0


def target_text(checks):
    return json.dumps({"checks": checks}, separators=(",", ":"), ensure_ascii=False)


def keep_reason(task, row, ref=None):
    """None if the set is kept, else why not: parse / size / invalid / reference."""
    ch = row.get("checks")
    if not row.get("parse_ok") or not isinstance(ch, list):
        return "parse"
    if not 2 <= len(ch) <= 6:
        return "size"
    if not all(valid(c) for c in ch):
        return "invalid"
    w, reply = ref or replay.replay_reference(task)
    return None if all(passes(c, w, reply) for c in ch) else "reference"


def build(rows, tasks, targets, max_sets=MAX_SETS, val_frac=VAL_FRAC, seed=SEED):
    """-> (train, val, stats). rows: Haiku probe records; tasks: all tasks; targets: ids to exclude (asserted absent)."""
    byid, targets = {t["id"]: t for t in tasks}, set(targets)
    seen = {r["task"] for r in rows}
    assert not seen & targets, f"target tasks in the Haiku file: {sorted(seen & targets)[:5]}"
    assert seen <= set(byid), f"unknown tasks: {sorted(seen - set(byid))[:5]}"
    refs, why, kept = {}, {}, {}
    for r in sorted(rows, key=lambda r: (r["task"], r["sample"])):
        t = byid[r["task"]]
        refs.setdefault(t["id"], replay.replay_reference(t))
        k = keep_reason(t, r, refs[t["id"]])
        why[k or "kept"] = why.get(k or "kept", 0) + 1
        if k is None:
            kept.setdefault(t["id"], []).append(r["checks"])
    rng, picked = random.Random(seed), {}
    for tid in sorted(kept):
        picked[tid] = rng.sample(kept[tid], min(max_sets, len(kept[tid])))
    ids = sorted(picked)
    rng.shuffle(ids)
    nval = max(1, round(val_frac * len(ids))) if len(ids) > 1 else 0
    val_ids = set(ids[:nval])
    mk = lambda tid, ch: dict(prompt=wp.task_prompt(byid[tid], with_state=True), target=target_text(ch), task=tid)  # noqa
    train = [mk(t, c) for t in sorted(picked) if t not in val_ids for c in picked[t]]
    val = [mk(t, c) for t in sorted(picked) if t in val_ids for c in picked[t]]
    assert not {r["task"] for r in train + val} & targets
    return train, val, dict(rows=len(rows), tasks_in_file=len(seen), **why, tasks_with_kept=len(kept), train_tasks=len(ids) - nval, val_tasks=nval,
                            train_sets=len(train), val_sets=len(val))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--haiku", default=DEFAULT_HAIKU)
    ap.add_argument("--results", default=DEFAULT_RESULTS, help="Guess-1 run dir; target.json names the 48 excluded tasks")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    if not os.path.exists(a.haiku):
        sys.exit(f"missing {a.haiku} (Haiku batch not collected yet)")
    train, val, st = build(read_jsonl(a.haiku), load_tasks(), target_ids(a.results))
    os.makedirs(a.out, exist_ok=True)
    for nm, d in (("train", train), ("val", val)):
        with open(os.path.join(a.out, nm + ".jsonl"), "w") as f:
            f.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in d)
    print(json.dumps(st, indent=1))
    print(f"train {len(train)} sets, val {len(val)} sets -> {a.out}")


if __name__ == "__main__":
    main()
