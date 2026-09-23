"""Parity + behaviour test for the key-pool variant (Claude, 2026-09-19).

    PY -B tests/test_premonition_key_pool.py

Checks, all on CPU (must pass before any GPU time):
  a  init parity: the state_dict is the baseline's tensors (identical values) plus EXACTLY
     writer.key_pool.weight / writer.key_pool.bias, which are a copy of writer.pool's; on a real validation
     batch the store keys, the store values and every teacher-mode loss equal the baseline's.
  b  parameter count = baseline + d_model + 1.
  c  gradient routing: the gold-phase loss (L_lm + L_ans only) leaves key_pool with no gradient while pool
     gets one; the ask loss of a teacher-mode forward does reach key_pool.
  d  key_pool is wired to the KEYS only: perturbing it moves the store keys and leaves the values alone.
  e  it composes with the relation shortcut, and a save -> premonition_first_card_probe.load_from round
     trip reproduces the same keys, values and losses.
  f  a 30-step CPU run of premonition_gpu_port.py --key-pool finishes and writes a checkpoint blob with
     key_pool: True (into a temporary directory, removed afterwards).
Plus: the new parameters land in the same AdamW weight-decay groups as writer.pool's.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

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


def _store(model, batch):
    """(keys, values) of the cards written for one batch."""
    import torch
    model.eval()
    with torch.no_grad():
        store = model.build_store(model.read(batch), batch)
    return store.keys.clone(), store.values.clone()


def _maxdiff(a, b):
    return float((a - b).abs().max())


def main() -> int:
    L.bootstrap()
    import torch
    import premonition_key_pool as KP
    import premonition_first_card_probe as P
    import premonition_relation_shortcut as RS
    torch.set_num_threads(4)
    failures = []

    def check(name, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + name + ((" :: " + detail) if detail else ""), flush=True)
        if not ok:
            failures.append(name)

    items = L.load_split("validation")
    batch = items[0][0]

    # ---- a. init parity -----------------------------------------------------------
    base = R.build(ARM, SEED)
    model = KP.build(ARM, SEED)
    bsd, msd = base.state_dict(), model.state_dict()
    extra = sorted(set(msd) - set(bsd))
    check("exactly two new state_dict keys", extra == sorted(KP.NEW_KEYS), str(extra))
    check("no baseline key is missing", not (set(bsd) - set(msd)))
    check("baseline tensors identical in value",
          all(torch.equal(bsd[k], msd[k]) for k in bsd), f"{len(bsd)} tensors")
    check("key_pool is a copy of pool",
          torch.equal(msd["writer.key_pool.weight"], msd["writer.pool.weight"])
          and torch.equal(msd["writer.key_pool.bias"], msd["writer.pool.bias"]))
    bk, bv = _store(base, batch)
    mk, mv = _store(model, batch)
    check("store keys identical at init", _maxdiff(bk, mk) <= 1e-6, f"max |dk| = {_maxdiff(bk, mk):.3e}")
    check("store values identical at init", _maxdiff(bv, mv) <= 1e-6, f"max |dv| = {_maxdiff(bv, mv):.3e}")
    stream = L.checked_train()
    train_items = [next(stream) for _ in range(2)]
    for mode, p_own in (("teacher", 0.0), ("own", 0.5), ("gold", 0.0)):
        for i, item in enumerate(train_items):
            a = _losses(base, item[0], mode, p_own, 1234 + i)
            b = _losses(model, item[0], mode, p_own, 1234 + i)
            check(f"loss parity at init mode={mode} batch={i}", a == b, f"{a} vs {b}")

    # ---- b. parameter count -------------------------------------------------------
    added = sum(p.numel() for p in model.parameters()) - sum(p.numel() for p in base.parameters())
    d = model.config.d_model
    check("added parameter count is d_model + 1", added == d + 1, f"{added} new params (d_model {d})")

    # ---- optimizer groups (AdamW: matrices decayed, vectors not) -------------------
    from premonition.train import MiniTrainer, mini_train_config
    trainer = MiniTrainer(KP.build(ARM, SEED), mini_train_config(), "cpu", flop_budget=1.0, seed=0)
    groups = trainer.optimizer.param_groups
    writer = trainer.model.writer

    def group_of(param):
        return next((i for i, g in enumerate(groups) if any(p is param for p in g["params"])), None)

    same_w = group_of(writer.key_pool.weight) == group_of(writer.pool.weight)
    same_b = group_of(writer.key_pool.bias) == group_of(writer.pool.bias)
    check("key_pool lands in the same optimizer groups as pool", same_w and same_b,
          "key_pool.weight -> group {} (decay {}), key_pool.bias -> group {} (decay {})".format(
              group_of(writer.key_pool.weight), groups[group_of(writer.key_pool.weight)]["weight_decay"],
              group_of(writer.key_pool.bias), groups[group_of(writer.key_pool.bias)]["weight_decay"]))

    # ---- c. gradient routing ------------------------------------------------------
    gold = KP.build(ARM, SEED)
    gold.train()
    out = gold(train_items[0][0], mode="gold", p_own=0.0, generator=torch.Generator().manual_seed(7))
    out["loss"].backward()
    kp_grad = gold.writer.key_pool.weight.grad
    pool_grad = gold.writer.pool.weight.grad
    check("gold-phase loss gives key_pool no gradient",
          kp_grad is None or float(kp_grad.abs().max()) == 0.0,
          "None" if kp_grad is None else f"max |g| = {float(kp_grad.abs().max()):.3e}")
    check("gold-phase loss does train pool",
          pool_grad is not None and float(pool_grad.abs().max()) > 0.0,
          f"max |g| = {float(pool_grad.abs().max()):.3e}")

    asker = KP.build(ARM, SEED)
    asker.train()
    out = asker(train_items[0][0], mode="teacher", p_own=0.0, generator=torch.Generator().manual_seed(7))
    out["ask"].backward()
    kp_grad = asker.writer.key_pool.weight.grad
    check("the ask loss reaches key_pool",
          kp_grad is not None and float(kp_grad.abs().max()) > 0.0,
          "None" if kp_grad is None else f"max |g| = {float(kp_grad.abs().max()):.3e}")

    # ---- d. key_pool moves the keys only ------------------------------------------
    moved = KP.build(ARM, SEED)
    k0, v0 = _store(moved, batch)
    with torch.no_grad():
        moved.writer.key_pool.weight.add_(torch.randn_like(moved.writer.key_pool.weight))
    k1, v1 = _store(moved, batch)
    check("perturbing key_pool changes the keys", _maxdiff(k0, k1) > 1e-4,
          f"max |dk| = {_maxdiff(k0, k1):.3e}")
    check("perturbing key_pool leaves the values alone", _maxdiff(v0, v1) == 0.0,
          f"max |dv| = {_maxdiff(v0, v1):.3e}")

    # ---- e. composes with the relation shortcut, and survives a save/load round trip
    combo = KP.build(ARM, SEED, shortcut=True)
    csd = combo.state_dict()
    check("combined state_dict has both the key pool and the shortcut tensors",
          all(k in csd for k in KP.NEW_KEYS) and all(f"{k}" in csd for k in RS.NEW_KEYS),
          f"{type(combo).__name__} / {type(combo.writer).__name__}")
    with torch.no_grad():                        # move both additions off their init values
        combo.writer.key_pool.weight.add_(0.3 * torch.randn_like(combo.writer.key_pool.weight))
        combo.rel_query.weight.add_(0.05 * torch.randn_like(combo.rel_query.weight))
        combo.rel_gate.bias.add_(0.1)
    before = _losses(combo, train_items[0][0], "teacher", 0.0, 5150)
    ck, cv = _store(combo, batch)
    check("the combined model runs a forward pass",
          all(v == v and abs(v) < 1e6 for v in before.values()), json.dumps(before))
    tmp = Path(tempfile.mkdtemp(prefix="keypool-roundtrip-"))
    try:
        from dataclasses import asdict
        torch.save({"state_dict": combo.state_dict(), "config": asdict(combo.config), "arm": ARM,
                    "seed": SEED, "relation_shortcut": True, "key_pool": True,
                    "model_class": type(combo).__name__,
                    "writer_class": type(combo.writer).__name__}, tmp / "combo.pt")
        loaded, blob = P.load_from("combo", str(tmp))
        lk, lv = _store(loaded, batch)
        after = _losses(loaded, train_items[0][0], "teacher", 0.0, 5150)
        check("round trip rebuilds both additions",
              type(loaded).__name__ == type(combo).__name__
              and type(loaded.writer).__name__ == type(combo.writer).__name__,
              f"{type(loaded).__name__} / {type(loaded.writer).__name__}")
        check("round trip reproduces the store", _maxdiff(ck, lk) == 0.0 and _maxdiff(cv, lv) == 0.0,
              f"max |dk| = {_maxdiff(ck, lk):.3e}, max |dv| = {_maxdiff(cv, lv):.3e}")
        check("round trip reproduces the losses", before == after, f"{before} vs {after}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- f. 30-step CPU smoke run through premonition_gpu_port.py ------------------
    smoke = Path(tempfile.mkdtemp(prefix="keypool-smoke-"))
    try:
        cmd = [sys.executable, "-B", str(ROOT / "scripts" / "premonition_gpu_port.py"),
               "--device", "cpu", "--autocast", "off", "--arm", ARM, "--seed", "0", "--steps", "30",
               "--key-pool", "--name", "smoke-keypool", "--out", str(smoke)]
        proc = subprocess.run(cmd, cwd=str(ROOT), env=dict(os.environ), capture_output=True, text=True)
        ok = proc.returncode == 0 and (smoke / "ckpt" / "smoke-keypool.pt").exists()
        if not ok:
            check("30-step CPU smoke run finishes", False, (proc.stdout + proc.stderr)[-1200:])
        else:
            blob = torch.load(smoke / "ckpt" / "smoke-keypool.pt", weights_only=False)
            run = json.loads((smoke / "runs" / "smoke-keypool.json").read_text())
            check("30-step CPU smoke run finishes", True,
                  f"{run['train_report'].get('steps')} steps, {run['seconds_train']} s train")
            check("smoke checkpoint blob records key_pool", blob.get("key_pool") is True
                  and run.get("key_pool") is True, f"blob key_pool={blob.get('key_pool')}, "
                                                   f"writer_class={blob.get('writer_class')}")
            check("smoke checkpoint carries the new tensors",
                  all(k in blob["state_dict"] for k in KP.NEW_KEYS))
            reloaded, _ = P.load_from("smoke-keypool", str(smoke / "ckpt"))
            trained = reloaded.state_dict()
            check("key_pool moved away from pool during training",
                  not torch.equal(trained["writer.key_pool.weight"], trained["writer.pool.weight"]),
                  "max |key_pool - pool| = {:.3e}".format(float(
                      (trained["writer.key_pool.weight"] - trained["writer.pool.weight"]).abs().max())))
    finally:
        shutil.rmtree(smoke, ignore_errors=True)

    print(("\nALL CHECKS PASSED" if not failures else "\nFAILURES: " + ", ".join(failures)), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
