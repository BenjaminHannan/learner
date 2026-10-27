"""Parity + behaviour test for the relation-shortcut variant (Claude, 2026-09-19).

    PY -B tests/test_premonition_relation_shortcut.py

Checks, all on CPU (must pass before any GPU time):
  1  state_dict = the baseline's tensors (identical values) + EXACTLY the three new ones
     (rel_query.weight, rel_gate.weight, rel_gate.bias), all zero at init.
  2  at init, lm/ask/ans/halt/loss in "teacher" and "own" mode equal the base model's EXACTLY on two
     frozen train batches.
  3  after a few optimiser steps W_r is non-zero (the path trains) and the four losses are still finite.
  4  relation-token selection: on the WHOLE validation split the selected token id lies in the relation id
     range of premonition/toy_ladder.py LadderSpec, for one-hop AND two-hop questions, and matches the
     relation the existing probe reads out of the question span.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402

ARM, SEED = "bypass-k1", 0


def _losses(model, batch, mode, p_own, seed):
    import torch
    gen = torch.Generator().manual_seed(seed)
    model.eval()
    with torch.no_grad():
        out = model(batch, mode=mode, p_own=p_own, generator=gen)
    return {k: float(out[k]) for k in ("lm", "ask", "ans", "halt", "loss")}


def main() -> int:
    L.bootstrap()
    import torch
    import premonition_relation_shortcut as RS
    torch.set_num_threads(4)
    failures = []

    def check(name, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + name + ((" :: " + detail) if detail else ""), flush=True)
        if not ok:
            failures.append(name)

    # ---- 1. state_dict = baseline + exactly three new tensors --------------------
    base = R.build(ARM, SEED)
    model = RS.build(ARM, SEED, shortcut=True)
    off = RS.build(ARM, SEED, shortcut=False)
    bsd, msd = base.state_dict(), model.state_dict()
    extra = sorted(set(msd) - set(bsd))
    check("exactly three new state_dict keys", extra == sorted(RS.NEW_KEYS), str(extra))
    check("no baseline key is missing", not (set(bsd) - set(msd)))
    check("baseline tensors identical in value",
          all(torch.equal(bsd[k], msd[k]) for k in bsd), f"{len(bsd)} tensors")
    check("the three new tensors are zero at init",
          all(float(msd[k].abs().max()) == 0.0 for k in RS.NEW_KEYS))
    added = sum(p.numel() for p in model.parameters()) - sum(p.numel() for p in base.parameters())
    d, k = model.config.d_model, model.config.key_dim
    check("added parameter count is d_model*key_dim + d_model + 1", added == d * k + d + 1,
          f"{added} new params (d_model {d}, key_dim {k})")

    # ---- 2. loss parity at init --------------------------------------------------
    stream = L.checked_train()
    items = [next(stream) for _ in range(2)]
    for mode, p_own in (("teacher", 0.0), ("own", 0.5)):
        for i, item in enumerate(items):
            a = _losses(base, item[0], mode, p_own, 1234 + i)
            b = _losses(model, item[0], mode, p_own, 1234 + i)
            c = _losses(off, item[0], mode, p_own, 1234 + i)
            check(f"loss parity at init mode={mode} batch={i}", a == b == c, f"{a} vs {b}")

    # ---- 3. the path trains ------------------------------------------------------
    trainee = RS.build(ARM, SEED, shortcut=True)
    trainee.train()
    opt = torch.optim.Adam(trainee.parameters(), lr=1e-3)
    losses = []
    for step in range(6):
        gen = torch.Generator().manual_seed(99 + step)
        out = trainee(items[step % 2][0], mode="teacher", p_own=0.0, generator=gen)
        opt.zero_grad()
        out["loss"].backward()
        opt.step()
        losses.append(round(float(out["loss"]), 4))
    w_norm = float(trainee.rel_query.weight.norm())
    check("W_r is non-zero after 6 optimiser steps", w_norm > 0.0, f"|W_r| = {w_norm:.6f}")
    check("gate parameters moved too",
          float(trainee.rel_gate.weight.norm()) > 0.0 or abs(float(trainee.rel_gate.bias)) > 0.0,
          f"|w_g| = {float(trainee.rel_gate.weight.norm()):.6f}, b_g = {float(trainee.rel_gate.bias):.6f}")
    final = _losses(trainee, items[0][0], "teacher", 0.0, 7)
    check("losses stay finite after training",
          all(v == v and abs(v) < 1e6 for v in final.values()), f"curve {losses} -> {final}")

    # ---- 4. relation-token selection on the whole validation split ---------------
    spec = L.spec()
    low, high = spec.relation(0), spec.relation(spec.relations - 1)
    bad_range = bad_match = 0
    seen = {1: 0, 2: 0}
    for batch, _supplied, hops in L.load_split("validation"):
        picked = RS.relation_token_ids(batch)
        for q in range(len(hops)):
            v = int(batch.q_visit[q])
            span = batch.tokens[v, int(batch.q_span[q, 0]):int(batch.q_span[q, 1])].tolist()
            hop = int(hops[q])
            seen[hop] = seen.get(hop, 0) + 1
            token = int(picked[q])
            bad_range += not (low <= token <= high)
            expect = span[3] if hop == 2 else span[2]
            bad_match += token != expect
    check("selected token is always a relation id", bad_range == 0,
          f"ids {low}-{high} (LINK is {spec.link}); {seen} questions, {bad_range} exceptions")
    check("selected token matches the question span's relation", bad_match == 0,
          f"{bad_match} exceptions over {sum(seen.values())} validation questions")

    print(("\nALL CHECKS PASSED" if not failures else "\nFAILURES: " + ", ".join(failures)), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
