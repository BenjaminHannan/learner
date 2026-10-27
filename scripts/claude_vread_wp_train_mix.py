#!/usr/bin/env python3
"""vread wrong-person diagnosis step 4: how many backref practice rows have a rival, and how often is the owner NOT the
newest person? Gold labels only (no reads, no model): counts the composition of the vector arm's train rows, its
calibration rows and the dev rows, with the same person/recency definitions as claude_vread_wp_table.py
(person = a name in the dialog's kept gold cards with a whole-word copy in the prompt; recency = end of its last copy).

  python -B scripts/claude_vread_wp_train_mix.py --out artifacts/claude-vread-wrongperson-20260928/train_mix.json
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_vread_wp_common as C  # noqa: E402


def mix(rows):
    names = C.dialog_names(rows)
    b = Counter()
    for r in rows:
        if r["family"] != "backref":
            continue
        regions = C.regions_of(r)
        d = r["id"].rsplit("-t", 1)[0]
        pres = []
        for n in sorted(names[d]):
            cp = C.copies_text(n, r, regions)
            if cp:
                pres.append((n, max(c1 for _, _, c1 in cp)))
        pres.sort(key=lambda x: -x[1])
        order = [n for n, _ in pres]
        b["backref_rows"] += 1
        for g in r["cards"]:
            if g["owner"] == "me" or g["owner"] not in order:
                b["cards_owner_me_or_not_found"] += 1
                continue
            b["backref_cards_named_owner"] += 1
            rank = order.index(g["owner"])
            b[f"persons_{min(len(order), 3)}{'+' if len(order) >= 3 else ''}"] += 1
            if len(order) >= 2:
                b["cards_with_rival_named"] += 1
                b["rival_and_owner_newest" if rank == 0 else "rival_and_owner_not_newest"] += 1
    return dict(sorted(b.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {side: mix(C.dev_rows(side)) for side in ("train", "cal", "dev")}
    # all sides: non-backref rows whose gold owner is a named person (context: the owner is in the turn there)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
