#!/usr/bin/env python3
"""vread wrong-person diagnosis step 1: reproduce the '16 against 4' count from the raw dev reads (helper W).

Definition (from scripts/claude_vread2_score.py owner_bins, lines 96-118, and artifacts/claude-vread2-20260928/PASSMARKS.md
lines 97-103): in a backref dev row, every emitted card at ANY confidence takes the first unused gold card with the same
relation and state (preferring one equal in owner and value). If the gold owner is a name (not "me"): right owner = read
owner equals the gold owner (lower-cased); owner_me_instead = read owner is "me"; otherwise wrong person. A rival is a
different person name from the dialog's gold cards (non-me owners, and values of person relations) with a whole-word copy
in the prompt. Same rule for the LoRA reader's cards (frame facts as cards, claude_vread_score.lora_cards).
Copies here are text-only (no tokenizer on this machine).

  python -B scripts/claude_vread_wp_repro.py --out artifacts/claude-vread-wrongperson-20260928/repro.json
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_vread_wp_common as C  # noqa: E402


def run(rows, reads_by_arm, names):
    res = {}
    detail = {}
    for arm, rd in reads_by_arm.items():
        b = Counter()
        det = []
        for r in rows:
            if r["family"] != "backref":
                continue
            regions = C.regions_of(r)
            dn = names[r["id"].rsplit("-t", 1)[0]]
            read = rd.get(r["id"])
            cards = (read or {}).get("cards") or [] if arm == "vector" else C.lora_cards(read)
            gold = r["cards"]
            b["backref_rows"] += 1
            b["gold_cards"] += len(gold)
            b["gold_cards_owner_named"] += sum(g["owner"] != "me" for g in gold)
            for c, k in C.match_cards(cards, gold):
                if k is None:
                    b["emitted_no_gold_same_rel_state"] += 1
                    continue
                g = gold[k]
                if g["owner"] == "me":
                    b["matched_gold_owner_me"] += 1
                    continue
                b["matched"] += 1
                rivals = sorted(n for n in dn if C.norm(n) != C.norm(g["owner"]) and n != "me"
                                and C.copies_text(n, r, regions))
                if rivals:
                    b["rival_named:matched"] += 1
                if C.norm(c["owner"]) == C.norm(g["owner"]):
                    b["right_owner"] += 1
                    kind = "right"
                elif c["owner"] == "me":
                    b["owner_me_instead"] += 1
                    kind = "me"
                else:
                    b["wrong_person"] += 1
                    kind = "wrong"
                    if rivals:
                        b["rival_named:wrong_person"] += 1
                if kind != "right":
                    det.append({"id": r["id"], "kind": kind, "rival_named": bool(rivals), "gold_owner": g["owner"],
                                "read_owner": c["owner"], "rel": g["rel"], "value_ok": C.norm(c["value"]) == C.norm(g["value"]),
                                "conf": c.get("conf")})
        res[arm] = dict(sorted(b.items()))
        detail[arm] = det
    return res, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = C.dev_rows()
    names = C.dialog_names(rows)
    rd = {"vector": {x["id"]: x for x in C.load_jsonl(C.V1 / "run/out/vec_dev_reads.jsonl")},
          "lora": {x["id"]: x for x in C.load_jsonl(C.V1 / "run/out/lora_dev_reads.jsonl")}}
    res, det = run(rows, rd, names)
    out = {"counts": res, "non_right_cards": det}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
