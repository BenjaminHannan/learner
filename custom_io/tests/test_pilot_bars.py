"""python3 -m pytest custom_io/tests/test_pilot_bars.py -q   (pure Python, no data or GPU)"""
import json
import math
import os
import re
import subprocess
import sys

import pytest

from custom_io import pilot_bars as pb

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "pilot_bars.py")
EXAMPLE_SPEC = os.path.join(HERE, "pilot_bars_example_spec.json")

GAINS_8A_B2 = [0.03, 0.28, -1.11, 0.51, 0.73, 2.48]


def units(ds, prefix="u"):
    return [{"unit": "%s%d" % (prefix, i), "a": [0], "b": [d]} for i, d in enumerate(ds)]


def spec(rules=None, floor_sd=0.0, gate=None, default="UNRESOLVED"):
    s = {"floor_sd": floor_sd, "alpha_two_sided": 0.05, "anchors": {}, "rules": rules or [
        {"name": "ALWAYS", "conditions": [{"var": "n", "op": ">=", "value": 2}]}], "default": default}
    if gate:
        s["gate"] = gate
    return s


# (a) --------------------------------------------------------------- t quantiles
def test_t_quantiles_975_match_table():
    table = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262]
    for df, want in enumerate(table, start=1):
        assert round(pb.t_quantile(0.975, df), 3) == want, df


def test_t_quantile_95_df5():
    assert round(pb.t_quantile(0.95, 5), 3) == 2.015


def test_t_cdf_properties():
    assert pb.t_cdf(0.0, 4) == 0.5
    for df in (1, 3, 10):
        for t in (0.3, 1.7, 5.0):
            assert pb.t_cdf(t, df) + pb.t_cdf(-t, df) == pytest.approx(1.0, abs=1e-12)
    # df=1 is Cauchy: F(t) = 1/2 + atan(t)/pi
    assert pb.t_cdf(2.0, 1) == pytest.approx(0.5 + math.atan(2.0) / math.pi, abs=1e-12)
    # quantile inverts cdf, including the lower tail
    for p in (0.01, 0.2, 0.9, 0.995):
        assert pb.t_cdf(pb.t_quantile(p, 7), 7) == pytest.approx(p, abs=1e-10)
    assert pb.t_quantile(0.025, 5) == pytest.approx(-pb.t_quantile(0.975, 5))


# (b) --------------------------------------------------------------- published interval
def test_reproduces_8a_ladder_b2_interval():
    data = {"contrast": "8a B2 3M->10M", "unit": "seed", "pairs": units(GAINS_8A_B2, "s")}
    rep = pb.evaluate(data, spec(floor_sd=0.0))
    st = rep["stats"]
    assert st["n"] == 6 and st["df"] == 5
    assert st["mean"] == pytest.approx(0.487, abs=0.001)
    assert st["sd_obs"] == pytest.approx(1.169, abs=0.001)
    assert st["s"] == st["sd_obs"] and st["s_source"] == "observed"
    assert round(st["lo"], 2) == -0.74
    assert st["hi"] == pytest.approx(1.72, abs=0.011)  # the record rounds the upper bound; tool gives 1.71
    assert round(st["hi"], 2) == 1.71
    assert [u["d"] for u in rep["units"]] == GAINS_8A_B2


# (c) --------------------------------------------------------------- floor
def test_floor_binds_when_sd_obs_below_floor():
    ds = [1.0, 1.2, 0.8, 1.1]
    rep = pb.evaluate({"unit": "parent", "pairs": units(ds)}, spec(floor_sd=3.0))
    st = rep["stats"]
    assert st["sd_obs"] < 3.0
    assert st["s"] == 3.0 and st["s_source"] == "floor"
    assert st["half"] == pytest.approx(pb.t_quantile(0.975, 3) * 3.0 / 2.0, abs=1e-6)
    assert "[floor]" in rep["summary"]


def test_floor_does_not_bind_when_sd_obs_above():
    ds = [0.0, 6.0, -4.0, 5.0]
    rep = pb.evaluate({"unit": "parent", "pairs": units(ds)}, spec(floor_sd=3.0))
    st = rep["stats"]
    assert st["sd_obs"] > 3.0 and st["s"] == st["sd_obs"] and "[observed]" in rep["summary"]


# (d) --------------------------------------------------------------- replicates averaged within unit
def test_replicates_averaged_within_unit_df_is_units_minus_one():
    pairs = [
        {"unit": "s1", "a": [1.0, 3.0], "b": [5.0, 9.0]},   # d = 7 - 2 = 5
        {"unit": "s2", "a": [0.0, 2.0], "b": [2.0, 4.0]},   # d = 3 - 1 = 2
        {"unit": "s3", "a": [2.0, 2.0], "b": [3.0, 5.0]},   # d = 4 - 2 = 2
    ]
    rep = pb.evaluate({"unit": "seed", "pairs": pairs}, spec())
    st = rep["stats"]
    assert [u["d"] for u in rep["units"]] == [5.0, 2.0, 2.0]
    assert st["n"] == 3 and st["df"] == 2           # not 6 replicates / df 5
    assert st["mean"] == pytest.approx(3.0)
    assert st["sd_obs"] == pytest.approx(math.sqrt(3.0))
    assert st["t"] == pytest.approx(4.303, abs=0.001)
    assert st["half"] == pytest.approx(4.303 * math.sqrt(3.0) / math.sqrt(3.0), abs=0.002)
    # unequal replicate counts between arms are fine and still averaged
    rep2 = pb.evaluate({"unit": "seed", "pairs": [{"unit": "x", "a": [1], "b": [2, 4]}, {"unit": "y", "a": [0], "b": [1]}]}, spec())
    assert [u["d"] for u in rep2["units"]] == [2.0, 1.0]


def test_duplicate_units_and_single_unit_rejected():
    with pytest.raises(ValueError):
        pb.evaluate({"pairs": [{"unit": "s", "a": [0], "b": [1]}, {"unit": "s", "a": [0], "b": [2]}]}, spec())
    with pytest.raises(ValueError):
        pb.evaluate({"pairs": units([1.0])}, spec())


# (e) --------------------------------------------------------------- ordering, gate, default
RULES = [
    {"name": "FIRST", "conditions": [{"var": "mean", "op": ">=", "value": 1}]},
    {"name": "SECOND", "conditions": [{"var": "mean", "op": ">=", "value": 0}]},
]


def test_first_matching_rule_wins_and_all_rules_reported():
    rep = pb.evaluate({"pairs": units([2.0, 3.0, 4.0])}, spec(RULES))
    assert rep["verdict"] == "FIRST" and rep["rule_fired"] == "FIRST" and rep["decided_by"] == "rule"
    assert [r["all_held"] for r in rep["rules"]] == [True, True]   # SECOND also held but did not fire
    rep = pb.evaluate({"pairs": units([0.2, 0.4, 0.6])}, spec(RULES))
    assert rep["verdict"] == "SECOND"
    assert [r["all_held"] for r in rep["rules"]] == [False, True]
    failed = rep["rules"][0]["conditions"][0]
    assert failed["status"] == "failed" and failed["actual"] == pytest.approx(0.4) and failed["value"] == 1


def test_all_conditions_must_hold():
    rules = [{"name": "BOTH", "conditions": [{"var": "mean", "op": ">=", "value": 1}, {"var": "lo", "op": ">", "value": 5}]}]
    rep = pb.evaluate({"pairs": units([2.0, 3.0, 4.0])}, spec(rules))
    assert rep["verdict"] == "UNRESOLVED"
    assert [c["held"] for c in rep["rules"][0]["conditions"]] == [True, False]


def test_default_verdict_when_nothing_holds():
    rules = [{"name": "NEVER", "conditions": [{"var": "mean", "op": ">", "value": 100}]}]
    rep = pb.evaluate({"unit": "parent", "pairs": units([1.0, 2.0, 3.0])}, spec(rules, default="UNRESOLVED"))
    assert rep["verdict"] == "UNRESOLVED" and rep["decided_by"] == "default" and rep["rule_fired"] is None
    assert rep["summary"].startswith("VERDICT: UNRESOLVED")


def test_gate_checked_before_rules():
    gate = {"var": "sd_obs", "op": ">", "value": 8.0, "verdict": "GATE_FAIL_EXTEND"}
    wide = [-12.0, 20.0, 0.0, 30.0]            # mean 9.5 would satisfy FIRST/SECOND, but sd_obs > 8
    rep = pb.evaluate({"unit": "parent", "pairs": units(wide)}, spec(RULES, gate=gate))
    assert rep["stats"]["sd_obs"] > 8.0
    assert rep["verdict"] == "GATE_FAIL_EXTEND" and rep["decided_by"] == "gate" and rep["rule_fired"] is None
    assert rep["gate"][0]["held"] and "GATE sd_obs" in rep["summary"]
    rep = pb.evaluate({"unit": "parent", "pairs": units([2.0, 3.0, 4.0])}, spec(RULES, gate=gate))
    assert rep["verdict"] == "FIRST" and not rep["gate"][0]["held"]


def test_gate_uses_observed_sd_not_floored_s():
    gate = {"var": "sd_obs", "op": ">", "value": 2.0, "verdict": "G"}
    rep = pb.evaluate({"pairs": units([1.0, 1.1, 0.9])}, spec(RULES, floor_sd=5.0, gate=gate))
    assert rep["verdict"] == "FIRST"


def test_all_ops():
    env = {"mean": 2.0}
    for op, want in {">=": True, ">": False, "<=": True, "<": False, "==": True}.items():
        assert pb.eval_cond({"var": "mean", "op": op, "value": 2}, env)["held"] is want, op
    with pytest.raises(ValueError):
        pb.validate_spec(spec([{"name": "X", "conditions": [{"var": "mean", "op": "!=", "value": 1}]}]))
    with pytest.raises(ValueError):   # an empty condition list would fire unconditionally
        pb.validate_spec(spec([{"name": "X", "conditions": []}]))
    with pytest.raises(ValueError):   # a string value is never evaluated
        pb.validate_spec(spec([{"name": "X", "conditions": [{"var": "mean", "op": ">", "value": "1+1"}]}]))


def test_extra_variables_and_missing_flagged():
    rules = [{"name": "RATE", "conditions": [{"var": "pass_count", "op": ">=", "value": 4}]}]
    rep = pb.evaluate({"pairs": units([1.0, 2.0, 3.0]), "extra": {"pass_count": 5}}, spec(rules))
    assert rep["verdict"] == "RATE" and rep["extra"] == {"pass_count": 5}
    rep = pb.evaluate({"pairs": units([1.0, 2.0, 3.0])}, spec(rules))   # extra not supplied
    assert rep["verdict"] == "UNRESOLVED" and rep["missing_vars"] == ["pass_count"]
    assert rep["rules"][0]["conditions"][0]["status"] == "missing" and "WARNING" in rep["summary"]
    with pytest.raises(ValueError):
        pb.evaluate({"pairs": units([1.0, 2.0]), "extra": {"mean": 1}}, spec(rules))


# (f) --------------------------------------------------------------- no eval
def test_source_contains_no_eval_call():
    src = open(SRC).read()
    assert not re.search(r"\beval\s*\(", src)
    assert not re.search(r"\bexec\s*\(", src)
    import ast
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in ("eval", "exec", "compile")


# example spec + CLI -------------------------------------------------------------------
def test_example_spec_is_marked_example_and_valid():
    s = json.load(open(EXAMPLE_SPEC))
    assert "EXAMPLE" in s["_EXAMPLE"] and "NOT THE SEALED" in s["_EXAMPLE"]
    assert pb.validate_spec(s) == (3.0, 0.05)
    assert [r["name"] for r in s["rules"]][:2] == ["SIZE_WINS", "SIZE_KILLED"]
    assert s["default"] == "UNRESOLVED" and s["gate"]["value"] == 8.0


def test_example_spec_size_killed_summary_6_parents():
    ds = [0.0, 1.0, 2.0, 1.5, 0.6, 1.5]       # mean 1.10, sd_obs < 3 so the floor binds
    rep = pb.evaluate({"contrast": "c", "unit": "parent", "pairs": units(ds)}, json.load(open(EXAMPLE_SPEC)))
    assert rep["verdict"] == "SIZE_KILLED"
    assert rep["summary"] == "VERDICT: SIZE_KILLED (mean +1.10 <= +2; hi +%.2f < +6; n=6 parents; s=3.00 [floor])" % rep["stats"]["hi"]
    assert "hi +4.25" in rep["summary"]   # 1.10 + 2.571*3.0/sqrt(6)


def test_cli_roundtrip(tmp_path):
    data = tmp_path / "in.json"
    out = tmp_path / "out.json"
    data.write_text(json.dumps({"contrast": "8a", "unit": "seed", "pairs": units(GAINS_8A_B2, "s")}))
    r = subprocess.run([sys.executable, SRC, str(data), EXAMPLE_SPEC, "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    rep = json.loads(out.read_text())
    assert rep["verdict"] == "SIZE_KILLED"
    assert r.stdout.strip().splitlines()[-1] == rep["summary"]
