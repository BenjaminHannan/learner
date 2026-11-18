"""Tagger precision / recall against the oracle. Flags label-noise-limited if precision < 0.8 (prereg).
  python -m sleep2.askonce.report_tagger TAGS_JSONL ORACLE_DIR [OUT_JSON]"""
import json
import sys

from .config import jdump, jl_read
from .oracle_labels import oracle_labels


def prf(tags, truth):
    out = {}
    for typ in ("regret", "annoyance", "all"):
        t = {(x["req_id"], x["type"]) for x in tags if typ in (x["type"], "all")}
        o = {(x["req_id"], x["type"]) for x in truth if typ in (x["type"], "all")}
        tp = len(t & o)
        out[typ] = {"tagged": len(t), "oracle": len(o), "tp": tp, "precision": round(tp / len(t), 3) if t else None, "recall": round(tp / len(o), 3) if o else None}
    out["label_noise_limited"] = bool(out["all"]["precision"] is not None and out["all"]["precision"] < 0.8)
    return out


if __name__ == "__main__":
    r = prf(jl_read(sys.argv[1]), oracle_labels(sys.argv[2]))
    print(json.dumps(r, indent=1))
    if len(sys.argv) > 3:
        jdump(sys.argv[3], r)
