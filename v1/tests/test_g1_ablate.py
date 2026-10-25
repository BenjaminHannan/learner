"""G1 ablation (design/v1/g1-ablate/PREREG.md): flag defaults, the verdict function, and a tiny CPU end-to-end smoke of v1.g1_ablate
(tiny random Ledger B2, synthetic skills data, --smoke sizes). The sealed test split is never opened."""
import json
import os
import tempfile

import pytest
import torch

from custom_io.data import CharVocab
from custom_io.models.ledger import Ledger
from creative import sleep
from v1 import g1 as g1mod, g1_ablate

SMALL = dict(copy=True, d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)


def fixture(d):
    v = CharVocab.build([])
    torch.manual_seed(0)
    ck = os.path.join(d, "tiny.pt")
    sleep.save_parent(Ledger(v, **SMALL), "ledger", SMALL, v, ck)
    data = os.path.join(d, "skills")
    os.makedirs(os.path.join(data, "dev"))
    rows = [dict(id=f"sk{i}", prompt=f"Ida has {10 + i} keys, loses 3, picks up {i}. end?", answer=str(7 + 2 * i), accepted=[str(7 + 2 * i)],
                 family="chain_ops", level=6, stage=6, variant="", steps=[f"{10 + i} - 3 = {7 + i}", f"{7 + i} + {i} = {7 + 2 * i}"])
            for i in range(1, 40)]
    for name in ("train.jsonl", os.path.join("dev", "in_dist.jsonl")):
        with open(os.path.join(data, name), "w") as f:
            f.write("\n".join(json.dumps(r) for r in rows) + "\n")
    return ck, data


def test_g1_norm_default_is_v1_and_validated(monkeypatch):
    assert g1mod.NORMS[0] == "none"
    g = g1mod.G1(None, [], None)
    assert g.norm == "none"
    with pytest.raises(ValueError):
        g1mod.G1(None, [], None, norm="bogus")
    seen = {}

    def fake(m, rows, bs=64, norm=None, **kw):
        seen["norm"] = norm
        raise RuntimeError("stop")
    monkeypatch.setattr(g1mod.kf, "kfac_stats", fake)
    m = Ledger(CharVocab.build([]), **SMALL)
    for norm, want in (("none", None), ("example", "example")):
        with pytest.raises(RuntimeError):
            g1mod.G1(m, [], CharVocab.build([]), norm=norm).begin(m)
        assert seen["norm"] == want


def test_verdict_pass_marks():
    arms = lambda hx, fx, ho: {"g1_empirical": dict(harm_w2=1.0, first_try_w2=10.0), "g1_example": dict(harm_w2=hx, first_try_w2=fx),
                               "g1_off": dict(harm_w2=ho, first_try_w2=12.0)}
    v = g1_ablate.verdict(arms(0.5, 11.0, 3.5))
    assert v["example_ok"]["passes"] and v["g1_buys_retention"]["passes"] and not v["proved_wrong"]["g1_benefit"]
    v = g1_ablate.verdict(arms(1.5, 10.0, 2.9))                    # example harms more; off is only 1.9 worse -> neither
    assert not v["example_ok"]["passes"] and not v["g1_buys_retention"]["passes"] and v["proved_wrong"]["g1_benefit"]
    assert not g1_ablate.verdict(arms(1.0, 12.5, 3.0))["example_ok"]["passes"]      # first-try gap 2.5 > 2
    assert g1_ablate.verdict({"g1_off": {}})["status"] == "incomplete"


def test_retention_hook_off_leaves_train_json_unchanged():
    from v1 import creative_sleep
    with tempfile.TemporaryDirectory() as d:
        ck, data = fixture(d)
        out = os.path.join(d, "o")
        info = creative_sleep.run_creative(out, ck, os.path.join(data, "train.jsonl"), data, pool_limit=64, dev_limit=16, n1=4, n2=8, T=1.0, updates_cap=2)
        assert "retention" not in info


def test_smoke_end_to_end_three_arms(monkeypatch):
    from creative import c2_stuck, stones
    rows, _ = stones.make_stone_rows(16, 0)

    def fake_w(pool, tries, seed, per_cap=2, arm="W"):      # a random tiny model fits nothing: feed fixed solver records (plumbing smoke only)
        recs = stones.solver_records(rows)
        return recs, {pool[0]["id"]: len(recs)}
    monkeypatch.setattr(c2_stuck, "w_records", fake_w)
    with tempfile.TemporaryDirectory() as d:
        ck, data = fixture(d)
        out = os.path.join(d, "out")
        assert g1_ablate.main(["--b2", ck, "--skills", data, "--out", out, "--seeds", "0", "--smoke"]) == 0
        res = json.load(open(os.path.join(out, "results.json")))
        assert set(res["arms"]) == set(g1_ablate.DEFAULT_ARMS) and res["verdict"]["status"] == "done"
        for r in res["per_run"]:
            assert set(r["retention"]) == {"W1", "W2"} and set(r["harm_vs_own_Nprime"]) == {"W1", "W2"}
            assert r["retention"]["W2"]["harm_points"] is not None
        norms = {r["arm"]: r["g1_norm"] for r in res["per_run"]}
        assert norms == {"g1_empirical": "none", "g1_example": "example", "g1_off": None}
        tj = json.load(open(os.path.join(out, "s0", "g1_off", "train.json")))
        assert tj["g1"] is False and tj["retention"]["W1"]["skills5"] is not None
        tj = json.load(open(os.path.join(out, "s0", "g1_example", "train.json")))
        assert tj["phases"]["W2_sleep"]["guard"]["norm"] == "example"


def test_light_arm_wiring_and_default_weight():
    import inspect
    assert inspect.signature(g1mod.G1.__init__).parameters["kl_weight"].default == g1mod.KL_WEIGHT == 30.0   # v1 unchanged
    assert "g1_light" in g1_ablate.ARMS and "g1_light" not in g1_ablate.DEFAULT_ARMS                          # opt-in only
    assert g1_ablate.KL_WEIGHT == {"g1_light": 10.0} and g1_ablate.NORM["g1_light"] == g1_ablate.NORM["g1_empirical"] == "none"
    arms = lambda ft, hl: {"g1_empirical": dict(harm_w2=2.0, first_try_w2=34.0), "g1_light": dict(harm_w2=hl, first_try_w2=ft),
                           "g1_off": dict(harm_w2=3.0, first_try_w2=39.0)}
    assert g1_ablate.verdict_light(arms(36.0, 2.0))["passes"]
    assert not g1_ablate.verdict_light(arms(35.9, 2.0))["passes"]
    assert not g1_ablate.verdict_light(arms(38.0, 2.1))["passes"]
    assert g1_ablate.verdict_light({"g1_off": {}})["status"] == "incomplete"
