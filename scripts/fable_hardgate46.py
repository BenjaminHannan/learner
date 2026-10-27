#!/usr/bin/env python3
"""Experiment 46: harden the router BEFORE the install gate.  ONE change from Experiment 45's robust arm.

Experiment 45's leftover failures died inside the cross-validation folds: the soft router had the right skill on
top at every stage, but enough probability was still spread across the others that answers fell under the 0.9
threshold and counted as misses.  Here, after every fit (each fold and the refit), phi is snapped to its single
best chain (one-hot, logits +/-30) before anything is predicted, scored or compared.  Gate thresholds, loss,
optimiser, start and checkpoints are unchanged.  A trained word is therefore always a single hard chain.
Extra AUDIT (evaluation only, not part of selection): every installed word is run from every start person of the
training village and compared with the true word; one disagreement = wrong install.
Imports Experiments 44/45 read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

import fable_noisyteacher45 as N

R44 = N.R44
N.ARM = "robust"
HARD_LOGIT = 30.0


def harden(logits: torch.Tensor) -> torch.Tensor:
    out = torch.full_like(logits, -HARD_LOGIT)
    out[torch.arange(logits.shape[0]), logits.argmax(-1)] = HARD_LOGIT
    return out


_soft_fit = N.fit_word


def fit_word(base_state, w, eps, v, m, updates, seed, tag, snapshots=()):
    model, saved = _soft_fit(base_state, w, eps, v, m, updates, seed, tag, snapshots)
    saved = {t: harden(p) for t, p in saved.items()}
    model.words[w].data.copy_(harden(model.words[w].data))
    return model, saved


R44.fit_word = fit_word


def audit(rec: dict, w: int, v, m) -> dict:
    """Run the installed hard chain from every start person; compare with the true word."""
    if not rec.get("installed"):
        return rec
    model = R44.Reasoner()
    model.load_state_dict(torch.load(rec["path"], map_location="cpu", weights_only=True))
    qs = [R44.Question(x, (R44.R + w,), R44.walk(v, x, R44.WORD_CHAINS[w])) for x in v.names]
    preds = R44.predict(model, v, m, qs)
    rec["audit_disagree_of_60"] = sum(p != (q.answer if q.answer is not None else R44.UNKNOWN)
                                      for p, q in zip(preds, qs))
    return rec


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    torch.set_num_threads(1)
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
        for wrong in (0, 2, 4, 20):
            eps = N.episodes(train_v, w, a.seed, wrong)
            mode = f"hard-wrong{wrong}"
            rec = R44.sleep_word(base_state, w, eps, train_v, m_train, a.seed, mode, before,
                                 probe_qs, fresh_v, m_fresh, fresh_qs, a.out)
            rec.pop("installed_logits", None)
            rec["path"] = str(a.out / f"word-seed{a.seed}-{mode}-{R44.WORD_NAMES[w]}-ep{len(eps)}.pt")
            rec = audit(rec, w, train_v, m_train)
            rec.update(wrong=wrong, seed=a.seed, true_chain=list(R44.WORD_CHAINS[w]))
            rows.append(rec)
            print(json.dumps({k: rec.get(k) for k in ("seed", "word", "wrong", "installed", "fresh_accuracy",
                                                      "routed_chain", "audit_disagree_of_60", "chosen_updates")}))
    (a.out / f"hard-seed{a.seed}.json").write_text(json.dumps(
        {"seed": a.seed, "rows": rows, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        indent=1))


if __name__ == "__main__":
    main()
