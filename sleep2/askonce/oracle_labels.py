"""Deterministic truth from the sim (what really was a regret / annoyance). Used only to score the tagger, never for training."""
import re
from pathlib import Path

from .config import jl_read


def oracle_labels(oracle_dir):
    out = []
    for p in sorted(Path(oracle_dir).glob("day*.jsonl"), key=lambda p: int(re.findall(r"\d+", p.name)[0])):
        for o in jl_read(p):
            if o["regret"]:
                out.append({"day": o["day"], "req_id": o["req_id"], "type": "regret"})
            if o["annoyance"]:
                out.append({"day": o["day"], "req_id": o["req_id"], "type": "annoyance"})
    return out
