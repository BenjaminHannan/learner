#!/usr/bin/env python3
"""Experiment 60 sealed eval (run AFTER the wave, with FABLE43J_HARD=1).

For each arm (dict/signedsat/control) and seed (6001/6002/6003): loads the
trained checkpoint, re-evaluates exact-match per skill on lengths {4-12,16,32,
64} (100 fresh inputs per skill per length, same gate43/eval RNG as the rig)
plus a 512 probe (20 inputs per skill, report only), and logs the selector
audit (DICT: softmax probs per counter) and lam audit (SIGNED-SAT).
Writes eval60.json next to the checkpoints and prints tables.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

import fable_cardfold_sleep as C
import fable_counter60_dict as M
import fable_transport43g as T

SEALED_LENGTHS = (4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 32, 64)
PROBE_LENGTH = 512
PER_OP = 100
PROBE_PER_OP = 20
SKILLS = [op for op, _ in C.OLD_PROGRAMS]

ARMS = {"dict": M.DictCounter, "signedsat": M.SignedSat, "control": M.S59.V2.BalancedStart}


def exact_table(model: T.Transport, seed: int, lengths, per_op: int) -> dict:
    model.eval()
    table = {}
    with torch.inference_mode():
        for length in lengths:
            row = {}
            for op, program in C.OLD_PROGRAMS:
                rng = C.make_rng(f"gate43/eval/{op}/{length}", seed)
                inputs: set[str] = set()
                while len(inputs) < per_op:
                    inputs.add(C.random_digit_string(rng, length))
                acc, _ = T.score_old(model, C.examples_for_program(op, program, sorted(inputs)))
                row[op] = acc
            table[str(length)] = row
    return table


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=Path, required=True)
    p.add_argument("--seeds", type=int, nargs="+", default=[6001, 6002, 6003])
    a = p.parse_args()
    out = {}
    for arm, cls in ARMS.items():
        out[arm] = {}
        for seed in a.seeds:
            model = cls()
            blob = torch.load(a.runs / arm / f"base-seed{seed}.pt", map_location="cpu", weights_only=True)
            model.load_state_dict(blob["state"])
            table = exact_table(model, seed, SEALED_LENGTHS, PER_OP)
            probe = exact_table(model, seed, (PROBE_LENGTH,), PROBE_PER_OP)
            audit = {}
            with torch.inference_mode():
                if hasattr(model, "sel"):
                    probs = model.sel.softmax(-1).tolist()
                    audit["selector_probs"] = [[round(float(v), 4) for v in row] for row in probs]
                    audit["p_flip"] = [round(float(v[1]), 4) for v in probs]
                if hasattr(model, "w"):
                    audit["lams"] = [round(float(v), 4) for v in torch.tanh(model.w)]
            out[arm][str(seed)] = {"sealed": table, "probe512": probe[str(PROBE_LENGTH)], **audit}
            sealed_min = min(v for row in table.values() for v in row.values())
            probe_min = min(probe[str(PROBE_LENGTH)].values())
            print(f"{arm} seed {seed}: sealed_min={sealed_min:.2f} probe512_min={probe_min:.2f} audit={audit}", flush=True)
    (a.runs / "eval60.json").write_text(json.dumps(out, indent=1))
    print("wrote eval60.json")


if __name__ == "__main__":
    main()
