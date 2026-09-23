#!/usr/bin/env python3
"""43I length stress (measurement only, no training): at what input length does the learned-address
skill bank break?  Loads the saved 43I bases and slept routers, tests lengths 16..256."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

import fable_cardfold_sleep as C
import fable_transport43g as T
import fable_learnedaddr43i  # noqa: F401  (installs the learned-address bank into T)

LENGTHS = (16, 32, 64, 128, 256)
RUNS = Path(sys.argv[1])
out = {}
for seed in (4102, 4103, 4104, 4111, 4112, 4113):
    bank = T.Transport()
    bank.load_state_dict(torch.load(RUNS / f"base-seed{seed}.pt", weights_only=True)["state"])
    router = T.Router(T.Transport())
    router.load_state_dict(torch.load(RUNS / f"sleep-seed{seed}-ep20.pt", weights_only=True))
    rows = {}
    for n in LENGTHS:
        rng = C.make_rng(f"stress43i/{n}", seed)
        xs = sorted({C.random_digit_string(rng, n) for _ in range(100)})
        row = {}
        for op, program in C.OLD_PROGRAMS:
            acc, prob = T.score_old(bank.eval(), C.examples_for_program(op, program, xs))
            row[op] = [round(acc, 3), round(prob, 3)]
        row["CARDFOLD"] = round(T.accuracy(router.eval(), C.examples_for_program(C.CARDFOLD_OP, C.CARDFOLD, xs)), 3)
        rows[str(n)] = row
    out[str(seed)] = rows
    print(seed, {n: (min(v[0] for k, v in r.items() if k != "CARDFOLD"), r["CARDFOLD"]) for n, r in rows.items()})
(RUNS.parent / "stress.json").write_text(json.dumps(out, indent=1))
r = out["4102"]
for n in r:
    print(n, {k: v for k, v in r[n].items()})
