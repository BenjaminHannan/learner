#!/usr/bin/env python3
"""Experiment 80: ONE-CHANGE noise-mismatch stress of the live sleep recipe (exp 46).

Live recipe imported read-only from scripts/fable_hardgate46.py (which itself
patches fable_reasoner44.fit_word with harden-before-gate and sets the robust
loss eps=0.10 via fable_noisyteacher45). Single change vs exp 46: the TRUE
number of wrong teacher answers in 20 episodes varies over
(0, 2, 4, 6, 8, 10, 20); epsilon stays fixed at 0.10. Same 4-fold CV gate
(0.80 / 0.90), same optimiser/start/checkpoints, same villages/words, same
60-start audit (evaluation only). One seed per invocation; 3 words x 7 levels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

import fable_hardgate46 as H46

N = H46.N
R44 = H46.R44
WRONGS = (0, 2, 4, 6, 8, 10, 20)

assert abs(N.EPS - 0.10) < 1e-12, f"live recipe epsilon changed: {N.EPS}"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    torch.set_num_threads(1)
    assert abs(N.EPS - 0.10) < 1e-12
    if not (a.out / f"base-seed{a.seed}.pt").exists():
        R44.stage_base(a.seed, a.out, False)
    train_v = R44.make_village("train60", a.seed, R44.TRAIN_N, "T")
    fresh_v = R44.make_village("fresh60", a.seed, R44.TRAIN_N, "F")
    m_train, m_fresh = R44.notebook_matrices(train_v), R44.notebook_matrices(fresh_v)
    base_state = torch.load(a.out / f"base-seed{a.seed}.pt", map_location="cpu", weights_only=True)["state"]
    base_model = R44.Reasoner()
    base_model.load_state_dict(base_state)
    probe_qs = R44.base_probe(fresh_v, a.seed, R44.EVAL_PER_SET)
    before = R44.predict(base_model, fresh_v, m_fresh, probe_qs)
    rows = []
    for w in range(R44.N_WORDS):
        fresh_qs = R44.sample_set(fresh_v, f"eval/word{w}/fresh60", a.seed, R44.EVAL_PER_SET, (1,), "resolvable",
                                  vocab=(R44.R + w,))
        for wrong in WRONGS:
            eps = N.episodes(train_v, w, a.seed, wrong)
            mode = f"hard80-wrong{wrong}"
            rec = R44.sleep_word(base_state, w, eps, train_v, m_train, a.seed, mode, before,
                                 probe_qs, fresh_v, m_fresh, fresh_qs, a.out)
            rec.pop("installed_logits", None)
            rec["path"] = str(a.out / f"word-seed{a.seed}-{mode}-{R44.WORD_NAMES[w]}-ep{len(eps)}.pt")
            rec = H46.audit(rec, w, train_v, m_train)
            rec.update(wrong=wrong, seed=a.seed, eps_fixed=0.10,
                       true_chain=list(R44.WORD_CHAINS[w]))
            rows.append(rec)
            print(json.dumps({k: rec.get(k) for k in ("seed", "word", "wrong", "installed", "fresh_accuracy",
                                                      "routed_chain", "audit_disagree_of_60", "chosen_updates")}),
                  flush=True)
    (a.out / f"hard80-seed{a.seed}.json").write_text(json.dumps(
        {"seed": a.seed, "eps_fixed": 0.10, "wrongs": list(WRONGS), "rows": rows,
         "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=1))


if __name__ == "__main__":
    main()
