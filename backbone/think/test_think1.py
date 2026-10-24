"""All Think-1 CPU tests (IMPL-SPEC section 5):  python backbone/think/test_think1.py [--real] [--only NAME ...]

T1-T7, T9, T10 + TP/TC/TR/TB come from test_think1_board.py, X1-X4 from test_xent.py, S1 from test_summarize.py. Here: T8 (same seed,
same stage-2 losses), TO (data order = train.py's), TH (hits are stored in file order; gates off = arm a), TG (mechanics gate, incl. the
abort path), TR (run_box.sh job order and skips, stub python), SM (`think1.py --smoke` end to end, then summarize prints a verdict line).
Test names for --only: BOARD (T1-T7, T9, T10, TP, TC, TR-api, TB), XENT, S1, T8, TO, TH, TG, TR, SM.
Needs the venv with torch CPU, transformers 5.20.2 and peft; `--real` adds the real-0.8B checks (HF_HOME=<cache> HF_HUB_OFFLINE=1).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import random
import re
import sys
import tempfile
import time
import traceback
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import think1 as K  # noqa: E402
import board as B  # noqa: E402
import train as T  # noqa: E402

VILLAGE = "/tmp/claude-0/-home-user-learner/08e723bd-e536-5532-87e4-68b871893d12/scratchpad/village"
_FX = {}


def fixture():
    """Shared temp dir with smoke data (village rows if present, else synthetic) and a finished smoke arm a, seed 0 (its adapter feeds the stage-2 arms)."""
    if not _FX:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        data = K.smoke_data(VILLAGE, root)
        _FX.update(tmp=tmp, root=root, data=data)
        rc = K.run_arm(arm_args("a", 0, "base"))
        assert rc == 0
    return _FX


def arm_args(arm, seed, sub, steps=6, extra=()):
    r = Path(_FX["root"]) if _FX else None
    if r is None:
        raise RuntimeError("call fixture() first")
    a = K.parse(["--smoke", "--arm", arm, "--seed", str(seed), "--out", str(r / sub / f"{arm}_s{seed}"), "--data", str(_FX["data"]),
                 "--steps", str(steps), "--limit-eval", "4", "--a-adapter", str(r / "base" / "a_s0" / "adapter"), *extra])
    a.steps1, a.max_len, a.bsz, a.micro_bsz, a.log_every = 6, 256, 8, 4, 10**6
    return a


def load(args):
    return json.loads((Path(args.out) / f"result_{args.arm}_s{args.seed}.json").read_text())


# ---------------------------------------------------------------- T8, TO

def test_t8_same_seed_same_losses():
    fixture()
    out = {}
    for name, arm, seed in (("r1", "t", 0), ("r2", "t", 0), ("r3", "t", 1), ("r4", "a", 0), ("r5", "a", 0)):
        a = arm_args(arm, seed, name, steps=10)
        assert K.run_arm(a) == 0
        out[name] = load(a)
    l1, l2, l3 = (out[k]["train"]["step_losses"] for k in ("r1", "r2", "r3"))
    assert len(l1) == 10 and l1 == l2, "same seed, different stage-2 losses"
    assert l1 != l3, "different seed gave the same losses (the control has no teeth)"
    assert out["r4"]["train"]["step_losses"] == out["r5"]["train"]["step_losses"] and len(out["r4"]["train"]["step_losses"]) == 10
    assert out["r1"]["eval"] == out["r2"]["eval"]
    s1 = torch.load(Path(arm_args("t", 0, "r1").out) / "think_block.pt")["state_dict"]
    s2 = torch.load(Path(arm_args("t", 0, "r2").out) / "think_block.pt")["state_dict"]
    assert all(torch.equal(s1[k], s2[k]) for k in s1), "trained boards differ for the same seed"
    print(f"T8 same seed -> identical 10-step losses {['%.4f' % x for x in l1[:3]]}..., boards equal; seed 1 differs ({l3[0]:.4f} vs {l1[0]:.4f}); stage-1 arm a also identical")


def test_to_data_order():
    """Stage 1 draws rows exactly as train.py does; stage 2 uses Random(seed + 1000) and is the same stream for every stage-2 arm."""
    n, seed, bsz = 100, 3, 16
    rng, order_idx, want = random.Random(seed), [], []
    for _ in range(9):  # train.py's loop, verbatim
        if not order_idx:
            order_idx = list(range(n))
            rng.shuffle(order_idx)
        want.append([order_idx.pop() for _ in range(min(bsz, len(order_idx)))])
    g = K.batches(n, seed, bsz)
    assert [next(g) for _ in range(9)] == want
    g1, g2 = K.batches(n, seed + 1000, bsz), K.batches(n, seed + 1000, bsz)
    assert [next(g1) for _ in range(5)] == [next(g2) for _ in range(5)]
    assert next(K.batches(n, seed, bsz)) != next(K.batches(n, seed + 1000, bsz))
    steps1 = [i for _ in range(0, 1) for i in next(K.batches(86238, 0, 16))]
    print(f"TO data order = train.py's (first stage-1 batch {steps1[:4]}...), stage-2 stream is seed+1000 and shared")


# ---------------------------------------------------------------- TH, TG

def test_th_hits_in_file_order_and_gates_off_is_arm_a():
    fx = fixture()
    from peft import PeftModel
    a = arm_args("t", 0, "th")
    lm, tok = T.load_model(a, torch.device("cpu"), torch.float32)
    torch.nn.init.normal_(lm.model.embed_tokens.weight, std=0.5)  # token-dependent logits, and no all-zero padding row
    pm = PeftModel.from_pretrained(lm, str(Path(fx["root"]) / "base" / "a_s0" / "adapter")).eval()
    r = T.Runner(pm.base_model.model)
    enc = T.Encoder(tok, 256)
    rows = T.read_jsonl(Path(fx["data"]) / "validation.jsonl")
    # make the answers equal to arm a's own greedy output for every other row, so hits are 1 exactly there and the check has teeth
    prompts = [enc.prompt(x)[0] for x in rows]
    preds = [T.greedy(r, [p], torch.device("cpu"), enc.eos)[0] for p in prompts]
    rows = [dict(x, answer=tok.decode(p, skip_special_tokens=True) if i % 2 == 0 else "zzz-never") for i, (x, p) in enumerate(zip(rows, preds))]
    want = "".join("1" if i % 2 == 0 else "0" for i in range(len(rows)))
    args = K.parse(["--smoke", "--out", "/tmp/unused", "--eval-bsz", "4"])
    for rev in (False, True):
        e = K.eval_greedy(r, enc, rows, torch.device("cpu"), args, reverse=rev)
        assert e["hits"] == want and e["n"] == len(rows) and e["row_offset"] == 0, (rev, e["hits"], want)
    torch.manual_seed(0)
    board = B.ThinkBoard.from_model(r.lm, tok, K=4)
    with torch.no_grad():
        board.alpha.copy_(3 * torch.randn_like(board.alpha))
    tags = {"gatesoff8": ("off", 8, None), "L16": ("plain", 16, 6), "swap8": ("swap", 8, None), "mean8": ("mean", 8, None), "rep1_8": ("rep", 8, None)}
    ev = K.eval_board(r, board, enc, rows, tags, args, torch.device("cpu"))
    assert ev["gatesoff8"]["hits"] == want, "gates off must equal arm a, row for row, in file order"
    assert ev["L16"]["n"] == 6 and len(ev["L16"]["hits"]) == 6, "L16 is scored on the first nmax rows only"
    assert all(len(ev[t]["hits"]) == len(rows) for t in ("swap8", "mean8", "rep1_8"))
    mb = [enc.train_example(x) for x in rows[:3]]  # open gates must move the logits, or the gates-off equality above says nothing
    C, mask, p, lt, ans = K.micro_inputs(r, mb, torch.device("cpu"))
    with torch.no_grad():
        kv = B.think(board, r, C, mask, p, 2, keep={2}, stats=False)[0][2]
        on = B.answer_logits(r, board.gate(), C, mask, p, lt, ans, kv)[0]
        off = B.answer_logits(r, torch.zeros_like(board.alpha), C, mask, p, lt, ans, kv)[0]
    assert (on - off).abs().max() > 1e-3, "open gates change nothing: the gates-off check is vacuous"
    print(f"TH hits in file order (descending and reversed batches); gatesoff8 == arm a on {len(rows)} rows; board hits {ev['swap8']['hits']} (swap), {ev['mean8']['hits']} (mean)")


def test_tg_mechanics_gate():
    ok = dict(alpha_mean=0.05, cos_across=0.5, clamp5=0.1)
    assert K.gate_reason(ok) is None
    for k, v, word in (("alpha_mean", 0.019, "alpha"), ("cos_across", 0.951, "cosine"), ("clamp5", 0.91, "pinned")):
        assert word in K.gate_reason({**ok, k: v}), k
    assert K.gate_reason({**ok, "alpha_mean": 0.02, "cos_across": 0.95, "clamp5": 0.9}) is None  # thresholds are strict
    assert not K.diverged([1.0] * 20) and not K.diverged([1.0] * 20 + [1.9] * 20) and K.diverged([1.0] * 20 + [2.1] * 20)
    assert not K.diverged([1.0] * 19 + [50.0])  # needs more than 20 steps
    fx = fixture()
    a = arm_args("t", 0, "gate", steps=6, extra=("--gate-step", "2", "--gate-enforce"))
    a.log_every = 10**6
    rc = K.run_arm(a)
    res = load(a)
    assert rc == 3 and res["aborted"] and "mechanics gate at step 2" in res["aborted"], res["aborted"]
    assert res["eval"] == {"validation": {}, "dev": {}} and len(res["train"]["step_losses"]) == 2
    assert (Path(a.out) / "think_block.pt").exists()
    from subprocess import run
    r = run([sys.executable, str(HERE / "think1.py"), "--smoke", "--arm", "t", "--seed", "0", "--out", str(Path(fx["root"]) / "gate2"), "--gate-step", "2",
             "--gate-enforce", "--steps", "4", "--limit-eval", "4"], capture_output=True, text=True, cwd=str(HERE.parent.parent))
    # the CLI path needs the smoke a adapter in gate2/smoke/a_s0, which does not exist: it must fail loudly, not silently
    assert r.returncode != 0 and "needs the stage-1 adapter" in (r.stdout + r.stderr), r.stderr[-300:]
    print(f"TG gate thresholds strict; divergence rule; abort path: exit 3, aborted={res['aborted']!r}, no eval; missing adapter -> clear error")


# ---------------------------------------------------------------- run_box.sh

STUB = r"""#!/usr/bin/env bash
script=$1; shift
echo "$(basename $script) $*" >> "$LOG"
case "$script" in
  *think1.py)
    while [ $# -gt 0 ]; do case "$1" in --arm) arm=$2;; --seed) seed=$2;; --out) out=$2;; esac; shift; done
    case "$FAIL" in *"$arm"*) exit 1;; esac
    mkdir -p "$out"
    case "$arm" in aplus|t|t1|tw) [ -f "$out/../a_s$seed/adapter/adapter_config.json" ] || { echo "no a adapter" >&2; exit 4; };;
                   bplus) [ -f "$out/../b_s$seed/adapter/adapter_config.json" ] || exit 4;; esac
    mkdir -p "$out"; echo '{}' > "$out/result_${arm}_s${seed}.json"
    case "$arm" in a|b) mkdir -p "$out/adapter"; echo '{}' > "$out/adapter/adapter_config.json";; esac;;
  *summarize.py) echo "VERDICT: INCOMPLETE";;
esac
"""


def test_box_script():
    """run_box.sh drives think1.py for every arm, in dependency order, skipping finished jobs (stub python; no torch)."""
    import os
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        stub, log = tmp / "fakepy", tmp / "log"
        stub.write_text(STUB)
        stub.chmod(0o755)
        (tmp / "out" / "data").mkdir(parents=True)
        (tmp / "out" / "data" / "DATA_REPORT.json").write_text("{}")

        def box(jobs, fail="", flags=""):
            log.write_text("")
            env = dict(os.environ, THINK_JOBS=jobs, PYTHON=str(stub), OUT=str(tmp / "out"), TARBALL="0", LOG=str(log), FAIL=fail, THINK_FLAGS=flags)
            r = subprocess.run(["bash", str(HERE / "run_box.sh")], env=env, capture_output=True, text=True)
            assert r.returncode == 0, r.stdout + r.stderr
            return [l.split() for l in log.read_text().splitlines()], r.stdout

        def runs(calls):
            return [(c[c.index("--arm") + 1], c[c.index("--seed") + 1]) for c in calls if c[0] == "think1.py"]

        calls, out = box("t:0,bplus:0,aplus:1,tw:0")
        assert runs(calls) == [("a", "0"), ("t", "0"), ("b", "0"), ("bplus", "0"), ("a", "1"), ("aplus", "1"), ("tw", "0")], runs(calls)
        assert calls[-1][0] == "summarize.py" and "--data" in calls[-1] and not any(c[0] == "train.py" for c in calls)
        assert all("--steps" not in c for c in calls if c[0] == "think1.py"), "no global STEPS"
        calls, _ = box("t:0,bplus:0,aplus:1")
        assert runs(calls) == [], ("finished jobs must be skipped", runs(calls))
        import shutil
        shutil.rmtree(tmp / "out" / "think" / "a_s1" / "adapter")
        calls, _ = box("aplus:1")
        assert runs(calls) == [("a", "1")], "result without adapter: retrain the stage-1 arm, then the (finished) job is skipped"
        calls, out = box("t:5,a:6,zz:0", fail="a")
        assert runs(calls) == [("a", "5"), ("a", "6")] and "t seed 5 skipped" in out and "unknown arm zz" in out, (runs(calls), out)
        calls, _ = box("t1:7", flags="--limit-eval+10")
        assert [c for c in calls if c[0] == "think1.py" and "t1" in c][0][-2:] == ["--limit-eval", "10"]
        r = subprocess.run(["bash", "-n", str(HERE / "run_box.sh")], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    print("TR run_box.sh: every arm via think1.py, a/b run first when an adapter is missing, finished jobs skipped, failures isolated, flags passed")


# ---------------------------------------------------------------- SM, TS

EXPECT = {
    "a": {"validation": {"main", "main_repeat"}, "dev": {"main"}},
    "b": {"validation": {"main", "pass1"}, "dev": {"main", "pass1"}},
    "aplus": {"validation": {"main"}, "dev": {"main"}}, "bplus": {"validation": {"main"}, "dev": {"main"}},
    "t": {"validation": {"L0", "L1", "L2", "L4", "L8", "L12", "L16", "L24", "swap8", "mean8", "rep1_8", "gatesoff8"}, "dev": {"L0", "L1", "L8"}},
    "t1": {"validation": {"L0", "L1", "L8"}, "dev": {"L1"}}, "tw": {"validation": {"L1"}, "dev": set()},
}


def test_sm_smoke_all_arms():
    src = VILLAGE if Path(VILLAGE).exists() else "/nonexistent"
    with tempfile.TemporaryDirectory() as tmp:
        buf, t0 = io.StringIO(), time.time()
        with contextlib.redirect_stdout(buf):
            rc = K.main(["--smoke", "--seed", "0", "--data", src, "--out", tmp])
        out, root = buf.getvalue(), Path(tmp) / "smoke"
        assert rc == 0, out[-2000:]
        res = {}
        for arm, want in EXPECT.items():
            f = root / f"{arm}_s0" / f"result_{arm}_s0.json"
            assert f.exists(), f"missing {f}"
            r = res[arm] = json.loads(f.read_text())
            assert r["arm"] == arm and r["seed"] == 0 and r["aborted"] is None, (arm, r["aborted"])
            assert {s: set(r["eval"][s]) for s in ("validation", "dev")} == want, (arm, {s: set(r["eval"][s]) for s in ("validation", "dev")})
            for split in want:
                for tag, e in r["eval"][split].items():
                    assert e["n"] == len(e["hits"]) and set(e["hits"]) <= {"0", "1"} and e["row_offset"] == 0 and 0 <= e["acc"] <= 1, (arm, split, tag)
            assert r["train"]["loss_curve"] and len(r["train"]["step_losses"]) == 6 and r["label_nums"]
            assert r["steps_stage1"] == 6 and r["steps_stage2"] == (0 if arm in ("a", "b") else 6)
        for arm in ("a", "b", "aplus", "bplus"):
            assert (root / f"{arm}_s0" / "adapter" / "adapter_config.json").exists()
        for arm in ("t", "t1", "tw"):
            assert (root / f"{arm}_s0" / "think_block.pt").exists()
        assert res["tw"]["k_slots"] == 144 and res["t"]["k_slots"] == 16 and res["t1"]["k_slots"] == 16
        assert res["aplus"]["stage1_adapter"].endswith("a_s0/adapter") and res["bplus"]["stage1_adapter"].endswith("b_s0/adapter")
        assert all(res[a]["stage1_adapter"].endswith("a_s0/adapter") for a in ("t", "t1", "tw"))
        assert res["b"]["loops"] == 3 and res["b"]["loop_block"] == [0, 4] and res["a"]["loops"] == 1
        assert len(res["t"]["train"]["gate_log"]) >= 1 and len(res["t"]["train"]["dev_log"]) >= 1 and res["t"]["train"]["gate_check"]["step"] == 4
        if (HERE / "summarize.py").exists():
            m = re.search(r"^VERDICT: (PASS|WRONG|PARTIAL|FUTILE-STOP|INCOMPLETE)\b", out, re.M)
            assert m, "summarize printed no verdict line:\n" + out[-1500:]
            verdict = m.group(0)
        else:
            verdict = "summarize.py absent: skipped"
        print(f"SM smoke ran 7 arms in {time.time() - t0:.0f}s, adapters handed on, result tags as in the spec; {verdict}")


# ---------------------------------------------------------------- runner

def board_tests(TB, real):
    fails = TB.run(real)
    assert not fails, f"board tests failed: {fails}"


def run_all(real=False, only=None):
    import test_think1_board as TB
    import test_xent as TX
    import test_summarize as TS
    tests = [("BOARD", lambda: board_tests(TB, real)),
             ("XENT", TX.run_all), ("S1", TS.test_s1), ("T8", test_t8_same_seed_same_losses), ("TO", test_to_data_order),
             ("TH", test_th_hits_in_file_order_and_gates_off_is_arm_a), ("TG", test_tg_mechanics_gate), ("TR", test_box_script), ("SM", test_sm_smoke_all_arms)]
    fails = []
    for name, fn in tests:
        if only and name.lower() not in [o.lower() for o in only]:
            continue
        t0 = time.time()
        try:
            fn()
            print(f"PASS {name} ({time.time() - t0:.0f}s)", flush=True)
        except Exception:
            traceback.print_exc()
            print(f"FAIL {name}", flush=True)
            fails.append(name)
    print("think1 tests:", "ALL PASSED" if not fails else f"FAILED {fails}")
    return fails


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    sys.exit(1 if run_all(a.real, a.only) else 0)
