#!/usr/bin/env python3
"""Exp 260: direct row compare of two saved suite outputs (json or jsonl).

  rowdiff <a> <b>        prints the moved units, exit 0

Every field is compared except wall-clock timing fields (seconds, sec,
elapsed, ms). A "unit" is the nearest enclosing record with an "id"
(else "n" inside a named list), so a moved unit is one item/turn.
"""
import json
import sys
from pathlib import Path

TIMING = {"seconds", "sec", "elapsed", "ms", "wall", "time_s"}


def load(p):
    t = Path(p).read_text(encoding="utf-8")
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return [json.loads(x) for x in t.splitlines() if x.strip()]


def units(o, label="", out=None):
    """Map unit label -> canonical JSON of the unit (timing removed)."""
    if out is None:
        out = {}
    if isinstance(o, dict):
        if "id" in o or ("n" in o and label):
            key = f"{label}/{o.get('id', o.get('n'))}"
            out[key] = json.dumps(strip(o), sort_keys=True)
            return out
        for k, v in o.items():
            if k in TIMING:
                continue
            if isinstance(v, (dict, list)):
                units(v, f"{label}/{k}" if label else k, out)
            else:
                out[f"{label}/{k}"] = json.dumps(v)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, (dict, list)):
                units(v, label or "[]", out)
                if not (isinstance(v, dict) and ("id" in v or "n" in v)):
                    pass
            else:
                out[f"{label}[{i}]"] = json.dumps(v)
    return out


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in TIMING}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def main(a, b):
    ua, ub = units(load(a)), units(load(b))
    moved = sorted(k for k in set(ua) | set(ub) if ua.get(k) != ub.get(k))
    print(f"units a={len(ua)} b={len(ub)} moved={len(moved)}")
    for k in moved:
        print("MOVED", k)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
