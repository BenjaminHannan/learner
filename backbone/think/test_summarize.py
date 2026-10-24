"""CPU test S1 for summarize.py:  python backbone/think/test_summarize.py   (test_think1.py imports and calls test_s1)

Builds synthetic validation rows and synthetic result files with exact accuracies (hits = the k rows with the lowest difficulty
score plus per-run noise, so the arms are paired on the same rows) and checks the marks and the verdict:
PASS, WRONG (laps add nothing), FUTILE-STOP (seed 0 only), PARTIAL, INCOMPLETE, the G threshold to the hundredth, the R2 tolerance
from the eval-noise pair, aborted runs, the bootstrap, the slices against a plain-python recomputation, and the CLI.
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import summarize as SM

N = 2500
BANKS = ["q.where_before", "q.plan_get", "q.yn_at", "q.who_has", "q.count_at", "q.rule_place"]


def make_rows(n=N, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        rows.append({"id": f"validation-{i // 6}:q{i % 6}", "visit_id": f"validation-{i // 6}", "depth": int(rng.choice(7, p=[.05, .25, .2, .2, .15, .13, .02])),
                     "bank": BANKS[int(rng.integers(len(BANKS)))], "qtype": f"Q{int(rng.integers(1, 14))}", "question": "?", "answer": "x", "context": ""})
    return rows


def hit_string(u, pct, rng, noise=0.15, n=None):
    """Exactly round(pct% of n) hits, on the rows with the lowest difficulty + noise."""
    n = len(u) if n is None else n
    k = int(round(pct / 100 * n))
    order = np.argsort(u[:n] + noise * rng.normal(size=n), kind="stable")
    h = np.zeros(n, dtype=int)
    h[order[:k]] = 1
    return "".join(map(str, h))


class Lab:
    """Writes result files for a scenario: put(arm, seed, split, tag, pct) or put_hits(...)."""

    def __init__(self, root, n=N, seed=1):
        self.root, self.n = Path(root), n
        self.rng = np.random.default_rng(seed)
        self.u = np.random.default_rng(seed + 100).random(n)
        self.res = {}
        (self.root / "data").mkdir(parents=True, exist_ok=True)
        with open(self.root / "data" / "validation.jsonl", "w") as f:
            for r in make_rows(n):
                f.write(json.dumps(r) + "\n")
        self.rows = make_rows(n)

    def put(self, arm, seed, split, tag, pct, n=None):
        n = n or self.n
        h = hit_string(self.u, pct, self.rng, n=n)
        return self.put_hits(arm, seed, split, tag, h)

    def put_hits(self, arm, seed, split, tag, h):
        r = self.res.setdefault((arm, seed), {"arm": arm, "seed": seed, "model": "synthetic", "steps_stage1": 418, "steps_stage2": 1254,
                                              "params_trainable": 2644016 if arm.startswith("t") else 1000, "train": {"seconds": 3600.0},
                                              "aborted": None, "eval": {"validation": {}, "dev": {}}})
        r["eval"][split][tag] = {"acc": h.count("1") / len(h), "n": len(h), "hits": h, "row_offset": 0}
        return h

    def abort(self, arm, seed, why):
        self.res[(arm, seed)] = {"arm": arm, "seed": seed, "aborted": why, "eval": {}}

    def write(self):
        for (arm, seed), r in self.res.items():
            d = self.root / "out" / f"{arm}_s{seed}"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"result_{arm}_s{seed}.json").write_text(json.dumps(r))
        return self.root / "out", self.root / "data"


def scenario(root, seeds=(0, 1, 2), a=(66.80, 66.60, 66.40), repeat=66.76, b=(67.0, 67.2, 67.1), ap=(67.4, 67.6, 67.5),
             t=None, t1=None, swap=65.0, rep=70.4, bp=67.9, n=N):
    """t: {L: pct at seed 0}; per-seed offsets 0, +0.4, -0.4."""
    t = t or {0: 66.0, 1: 68.0, 2: 69.5, 4: 70.8, 8: 72.0, 12: 71.8}
    t1 = t1 or {0: 66.0, 1: 68.4, 8: 68.2}
    lab = Lab(root, n)
    off = {0: 0.0, 1: 0.4, 2: -0.4}
    for s in seeds:
        h = lab.put("a", s, "validation", "main", a[s])
        lab.put("a", s, "dev", "main", a[s] - 0.5, n=min(1000, n))
        if s == 0:
            lab.put("a", s, "validation", "main_repeat", repeat)
        lab.put("b", s, "validation", "main", b[s])
        lab.put("b", s, "validation", "pass1", 60.0)
        lab.put("aplus", s, "validation", "main", ap[s])
        for L, v in t.items():
            lab.put("t", s, "validation", f"L{L}", v + off[s])
        for L in (16, 24):
            lab.put("t", s, "validation", f"L{L}", 71.0 + off[s], n=min(1000, n))
        lab.put("t", s, "validation", "swap8", swap + off[s])
        lab.put("t", s, "validation", "mean8", 68.5 + off[s])
        lab.put("t", s, "validation", "rep1_8", rep + off[s])
        lab.put_hits("t", s, "validation", "gatesoff8", h)
        lab.put_hits("t", s, "validation", "ref0", h)
        for L in (0, 1, 8):
            lab.put("t", s, "dev", f"L{L}", t[min(L, 8)] - 1.0, n=min(1000, n))
        for L, v in t1.items():
            lab.put("t1", s, "validation", f"L{L}", v + off[s])
        lab.put("t1", s, "dev", "L1", t1[1] - 1.0, n=min(1000, n))
    if 0 in seeds:
        lab.put("bplus", 0, "validation", "main", bp)
        lab.put("tw", 0, "validation", "L1", 68.0)
    return lab


def run(lab, **kw):
    out, data = lab.write()
    return SM.summarize(out, data, **kw)


def marks(o):
    return {m["id"]: m for m in o["marks"]}


def test_s1():
    tmp = tempfile.TemporaryDirectory()
    R = Path(tmp.name)

    # ---- PASS
    lab = scenario(R / "pass")
    o = run(lab)
    mk = marks(o)
    assert o["verdict"] == "PASS", (o["verdict"], o["why"], {k: v["status"] for k, v in mk.items()})
    acc = lambda arm, s: 100 * lab.res[(arm, s)]["eval"]["validation"]["main"]["hits"].count("1") / N
    a_ref = max(66.72, np.mean([acc("a", s) for s in SM.SEEDS]), np.mean([acc("aplus", s) for s in SM.SEEDS]))
    b_ref = max(67.12, np.mean([acc("b", s) for s in SM.SEEDS]), acc("bplus", 0))
    assert abs(o["floors"]["A_ref"] - a_ref) < 1e-9 and abs(o["floors"]["B_ref"] - b_ref) < 1e-9 and b_ref > 67.9, o["floors"]
    assert abs(mk["G"]["need"] - (max(a_ref, b_ref) + 3.0)) < 1e-9 and abs(mk["G"]["value"] - 72.0) < 1e-9, mk["G"]
    assert all(mk[k]["status"] == "PASS" for k in ("G", "R1a", "R1b", "R2a", "R2b", "R2c", "R3a", "R3b", "R4a", "R4b")), {k: v["status"] for k, v in mk.items()}
    assert all(mk[k]["status"] == "clear" for k in ("W1", "W2", "W3", "W4", "F1", "F2", "F3", "F4"))
    assert abs(mk["R4a"]["value"] - (72.0 - 68.4)) < 1e-9 and abs(mk["R4b"]["value"] - 1.6) < 1e-9
    assert abs(o["lesions"]["swap_drop"] - 7.0) < 1e-9 and o["lesions"]["gates_off_rows_differing_from_a"] == 0
    assert o["lesions"]["gates_off_rows_differing_from_ref0"] == 0 and o["lesions"]["gates_off_ref0_seeds_checked"] == 3
    assert abs(o["bplus_extend"]["bplus_minus_b_s0"] - (acc("bplus", 0) - acc("b", 0))) < 1e-9 and o["bplus_extend"]["run_seeds_1_2"] is False  # 67.9 - 67.0 = 0.9
    assert "run bplus seeds 1-2" in SM.report(o)
    assert abs(o["noise"]["diff"] - 0.04) < 1e-9 and abs(o["noise"]["tol"] - 0.3) < 1e-9, o["noise"]
    # confidence intervals contain the point estimates, and the paired interval has about the textbook width
    for k in ("R4a", "R1a"):
        c = mk[k]["ci"]
        assert c["lo"] < c["value"] < c["hi"], c
    v8, vt1 = np.mean([SM.decode_hits(lab.res[("t", s)]["eval"]["validation"]["L8"]["hits"]) for s in SM.SEEDS], 0), \
        np.mean([SM.decode_hits(lab.res[("t1", s)]["eval"]["validation"]["L1"]["hits"]) for s in SM.SEEDS], 0)
    d = 100 * (v8 - vt1)
    c = mk["R4a"]["ci"]
    se_width = 2 * 1.96 * d.std() / np.sqrt(len(d))
    assert abs(d.mean() - mk["R4a"]["value"]) < 1e-9 and 0.85 < (c["hi"] - c["lo"]) / se_width < 1.15, (c, se_width)
    assert SM.boot({"x": v8, "y": vt1}, lambda m: m["x"] - m["y"]) == SM.boot({"x": v8, "y": vt1}, lambda m: m["x"] - m["y"]), "fixed seed"
    # the interval against the best floor is paired: vs arm a it is computed on the same rows
    assert mk["G"]["ci"] and mk["G"]["ci"]["lo"] is not None
    # slices and M1 / M2 against a plain-python recomputation from the rows
    for key, pick in (("M1", lambda r: r["bank"] in SM.CHAIN), ("M2", lambda r: r["depth"] >= 4)):
        idx = [i for i, r in enumerate(lab.rows) if pick(r)]
        want = 100 * float(np.mean([v8[i] - vt1[i] for i in idx]))
        got = o["secondary"][key]
        assert got["n"] == len(idx) and abs(got["value"] - want) < 1e-9, (key, got, want)
        assert got["status"] == ("PASS" if want >= (3.0 if key == "M1" else 2.0) - 1e-9 else "FAIL")
    sl = o["secondary"]["slices"]
    for name, pick in (("depth 0-3", lambda r: r["depth"] <= 3), ("bank q.yn_at", lambda r: r["bank"] == "q.yn_at"), ("qtype Q4", lambda r: r["qtype"] == "Q4")):
        idx = [i for i, r in enumerate(lab.rows) if pick(r)]
        assert sl[name]["n"] == len(idx) and abs(sl[name]["S8_minus_T1"]["value"] - 100 * float(np.mean([v8[i] - vt1[i] for i in idx]))) < 1e-9, name
    assert sum(sl[f"depth {d}"]["n"] for d in range(7)) == N
    text = SM.report(o)
    assert "VERDICT: PASS" in text and "G gain: PASS" in text and f"{max(a_ref, b_ref) + 3.0:.2f}" in text
    assert max(len(l) for l in text.splitlines()) <= 96, max(text.splitlines(), key=len)
    print(text)

    # ---- the bootstrap can resample whole stories instead of rows (wider or equal, still contains the estimate)
    oc = SM.summarize(R / "pass" / "out", R / "pass" / "data", cluster="visit")
    c2 = marks(oc)["R4a"]["ci"]
    assert c2["lo"] < c2["value"] < c2["hi"] and oc["verdict"] == "PASS"

    # ---- WRONG: laps add nothing
    flat = {0: 67.0, 1: 68.0, 2: 68.2, 4: 68.1, 8: 68.3, 12: 68.0}
    o = run(scenario(R / "wrong", t=flat, t1={0: 67.0, 1: 68.0, 8: 68.0}, swap=68.2, rep=68.2))
    mk = marks(o)
    assert o["verdict"] == "WRONG" and set(o["wrong_if"]) == {"W1", "W2", "W3", "W4"}, (o["verdict"], o["wrong_if"], o["why"])
    assert mk["G"]["status"] == "FAIL" and o["R"] == "FAIL"

    # ---- FUTILE-STOP: seed 0 only
    o = run(scenario(R / "futile", seeds=(0,), t={0: 66.5, 1: 67.0, 2: 67.4, 4: 67.5, 8: 67.5, 12: 67.4}, t1={0: 66.5, 1: 67.0, 8: 67.0}, swap=66.0))
    mk = marks(o)
    assert o["verdict"] == "FUTILE-STOP" and o["futility"]["triggered"] == ["F1", "F2", "F3"], (o["verdict"], o["futility"])
    assert mk["F4"]["status"] == "clear" and mk["G"]["status"] == SM.ND and mk["R1a"]["status"] == SM.ND and mk["W1"]["status"] == SM.ND
    # only the first futility rule fires: laps are real but small
    o = run(scenario(R / "small", seeds=(0,), t={0: 60.0, 1: 62.0, 2: 64.0, 4: 66.0, 8: 67.8, 12: 67.8}, t1={0: 60.0, 1: 62.0, 8: 62.0}, swap=62.0))
    assert o["verdict"] == "FUTILE-STOP" and o["futility"]["triggered"] == ["F1"] and o["futility"]["only_first"], o["futility"]
    assert "Think-1b" in SM.report(o)
    # seed 0 only and no rule fires: keep going
    o = run(scenario(R / "go", seeds=(0,)))
    assert o["verdict"] == "INCOMPLETE" and not o["futility"]["triggered"] and any("go on" in w for w in o["why"]), (o["verdict"], o["why"])
    assert "not-enough-data" in SM.report(o)

    # ---- PARTIAL: gain and slope pass, but the curve is not monotone
    o = run(scenario(R / "partial", t={0: 66.0, 1: 68.0, 2: 71.3, 4: 70.0, 8: 72.0, 12: 71.8}))
    mk = marks(o)
    assert o["verdict"] == "PARTIAL" and mk["G"]["status"] == "PASS" and mk["R2b"]["status"] == "FAIL" and not o["wrong_if"], (o["verdict"], {k: v["status"] for k, v in mk.items()})

    # ---- R2 tolerance follows the eval-noise pair
    drop = {0: 66.0, 1: 68.0, 2: 70.0, 4: 69.4, 8: 72.0, 12: 71.8}
    o = run(scenario(R / "tol_small", t=drop, repeat=66.76))
    assert marks(o)["R2b"]["status"] == "FAIL" and abs(o["noise"]["tol"] - 0.3) < 1e-9
    o = run(scenario(R / "tol_big", t=drop, repeat=66.40))
    assert marks(o)["R2b"]["status"] == "PASS" and abs(o["noise"]["tol"] - 0.8) < 1e-9, o["noise"]

    # ---- G is a >= test to the hundredth (N=2500: 70.12 is exactly 1753 hits)
    low = dict(a=(60.0,) * 3, b=(60.0,) * 3, ap=(60.0,) * 3, bp=60.0)
    for v, want in ((70.12, "PASS"), (70.08, "FAIL")):
        o = run(scenario(R / f"edge{v}", t={0: 66.0, 1: 68.0, 2: 69.0, 4: 70.0, 8: v, 12: v}, **low))
        # the per-seed offsets average to zero, so S(8) is v
        assert abs(marks(o)["G"]["value"] - v) < 1e-6 and abs(marks(o)["G"]["need"] - 70.12) < 1e-9
        assert marks(o)["G"]["status"] == want, (v, marks(o)["G"])

    # ---- gates-off lesion: the board-free decode of the same batches is the exact reference; arm a's path may differ by bf16 noise
    flip = lambda h, idx: "".join(("1" if c == "0" else "0") if i in idx else c for i, c in enumerate(h))
    lab = scenario(R / "noise")
    for sd in (0, 1):
        e = lab.res[("t", sd)]["eval"]["validation"]
        for tag in ("gatesoff8", "ref0"):
            e[tag]["hits"] = flip(e[tag]["hits"], {3, 50, 77})
    o = run(lab)
    assert o["lesions"]["gates_off_rows_differing_from_a"] == 6 and o["lesions"]["gates_off_rows_differing_from_ref0"] == 0, o["lesions"]
    text = SM.report(o)
    assert "path-confounded" in text and "(must be 0)" in text and max(len(l) for l in text.splitlines()) <= 96, [l for l in text.splitlines() if len(l) > 96]
    lab = scenario(R / "bug")
    e = lab.res[("t", 0)]["eval"]["validation"]
    e["gatesoff8"]["hits"] = flip(e["gatesoff8"]["hits"], {5})
    o = run(lab)
    assert o["lesions"]["gates_off_rows_differing_from_ref0"] == 1, o["lesions"]

    # ---- bplus seeds 1-2 only if bplus - b (seed 0) >= 1.0
    o = run(scenario(R / "bp_low", bp=67.5))
    assert o["bplus_extend"]["run_seeds_1_2"] is False and "(bplus:1,bplus:2): no (needs" in SM.report(o)
    o = run(scenario(R / "bp_high", bp=68.1))
    assert o["bplus_extend"]["run_seeds_1_2"] is True and "(bplus:1,bplus:2): yes (needs" in SM.report(o)
    o = run(scenario(R / "bp_edge", bp=68.0))
    assert o["bplus_extend"]["run_seeds_1_2"] is True  # exactly +1.00
    o = run(scenario(R / "bp_none", seeds=(1, 2)))
    assert o["bplus_extend"]["run_seeds_1_2"] is None

    # ---- a dependent trained on another copy of its stage-1 adapter is excluded from every mark
    lab = scenario(R / "sha")
    for sd in SM.SEEDS:
        lab.res[("a", sd)]["adapter_sha"] = f"aa{sd}" * 8
        lab.res[("b", sd)]["adapter_sha"] = f"bb{sd}" * 8
        for arm in ("t", "t1", "aplus"):
            lab.res[(arm, sd)]["stage1_adapter_sha"] = f"aa{sd}" * 8
    lab.res[("bplus", 0)]["stage1_adapter_sha"] = "bb0" * 8
    o = run(lab)
    assert o["verdict"] == "PASS" and not o["excluded"], (o["verdict"], o["excluded"])
    lab.res[("t", 1)]["stage1_adapter_sha"] = "cc" * 16  # a seed 1 was retrained after t seed 1 started from it
    lab.res[("bplus", 0)]["stage1_adapter_sha"] = "dd" * 16
    o = run(lab)
    text = SM.report(o)
    assert sorted((x["arm"], x["seed"]) for x in o["excluded"]) == [("bplus", 0), ("t", 1)], o["excluded"]
    assert o["verdict"] == "INCOMPLETE" and marks(o)["G"]["status"] == SM.ND and "EXCLUDED t seed 1" in text and "EXCLUDED bplus seed 0" in text, (o["verdict"], text[:600])
    assert o["floors"]["bplus"] is None and o["seeds"]["t"] == [0, 2]

    # ---- missing arm / aborted run: INCOMPLETE, and the abort is shown
    lab = scenario(R / "miss")
    del lab.res[("aplus", 2)]
    o = run(lab)
    assert marks(o)["G"]["status"] == SM.ND and o["verdict"] == "INCOMPLETE"
    lab = scenario(R / "abort")
    lab.abort("t", 1, "mean |tanh alpha| 0.004 < 0.02 at step 150")
    o = run(lab)
    text = SM.report(o)
    assert o["verdict"] == "INCOMPLETE" and o["aborted"][0]["arm"] == "t" and "ABORTED" in text and "tanh alpha" in text

    # ---- files that are not Think-1 results are skipped; missing data dir still gives the main marks
    (R / "pass" / "out" / "result_old.json").write_text(json.dumps({"arm": "a", "seed": 0, "validation": {"accuracy": 0.5}}))
    o = SM.summarize(R / "pass" / "out", R / "nowhere")
    assert o["verdict"] == "PASS" and any("not a Think-1 result file" in n for n in o["notes"]) and o["secondary"]["M1"]["status"] == SM.ND

    # ---- smoke-sized input (20 rows) and an empty directory do not crash
    o = run(scenario(R / "tiny", n=20))
    assert o["verdict"] in ("PASS", "WRONG", "PARTIAL", "INCOMPLETE", "FUTILE-STOP") and SM.report(o)
    (R / "empty").mkdir()
    o = SM.summarize(R / "empty", R / "nowhere")
    assert o["verdict"] == "INCOMPLETE" and "VERDICT: INCOMPLETE" in SM.report(o)

    # ---- CLI: text, and --json parses to the same verdict
    out, data = str(R / "pass" / "out"), str(R / "pass" / "data")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert SM.main([out, "--data", data, "--json"]) == 0
    j = json.loads(buf.getvalue())
    assert j["verdict"] == "PASS" and j["groups"]["G"] == "PASS"
    p = subprocess.run([sys.executable, str(HERE / "summarize.py"), out, "--data", data], capture_output=True, text=True)
    assert p.returncode == 0 and "VERDICT: PASS" in p.stdout, p.stderr[-500:]
    print("S1 ok: PASS / WRONG / FUTILE-STOP / PARTIAL / INCOMPLETE cases, G edge, R2 tolerance, bootstrap, slices, aborted run, CLI")
    tmp.cleanup()


if __name__ == "__main__":
    test_s1()
