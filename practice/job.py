"""Practice-1 lane (one lane = one chain on one GPU):
  A0 eval (sealed test100 x2, sibling60 x2, ARC-Easy 200) -> 3 x (day on the practice pool x2 tries -> night -> eval).
  python -m practice.job --arm P --lane 0 --out $OUT [--practice-n N] [--deadline-s S] [--pilot] [--smoke]
Everything is saved incrementally to <out>/<arm>/ (results/*.json, day/*.jsonl, eval/*.jsonl, timing.json). --pilot times a small slice and prints the
projected full-run hours and a suggested practice-pool size."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from sleep2.askonce.config import DATA as ASK_DATA
from sleep2.askonce.config import MODEL_ID, jdump, jload
from sleep2.askonce.eval_moves import eval_arc
from sleep2.askonce.job_common import Logger, assert_finite_forward, device_dtype, env_info
from sleep2.askonce.model_io import get_tokenizer, load_model

from . import night as N
from .harness import Harness, render, start_messages, summarize

HERE = Path(__file__).resolve().parent
PDATA = HERE / "data"
N_NIGHTS = 3
TRIES = 2  # module defaults; overridden by --nights / --tries
LANE_BUDGET_H = 10.0


def jl(path):
    return [json.loads(l) for l in open(path) if l.strip()] if Path(path).exists() else []


def jl_append(path, rec):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


def load_sets(data_dir=PDATA, practice_n=None):
    pool = jl(data_dir / "practice_pool.jsonl") + jl(data_dir / "sonnet_pool.jsonl")  # the Sonnet pool is added when present
    pool = sorted(pool, key=lambda p: h("practice1|" + p["id"]))  # same deterministic order for both arms, so a smaller pool is the same subset
    if practice_n:
        pool = pool[:practice_n]
    test = jl(data_dir / "test100.jsonl")
    sib = jl(data_dir / "sibling60.jsonl")
    keep = ("id", "kind", "prompt", "answer", "answer_type", "source")
    f = lambda rows: [{k: r.get(k) for k in keep} for r in rows]  # noqa: E731  (drops reference solvers etc.)
    return f(pool), f(test), f(sib)


def puzzle_scores(recs):
    by = {}
    for r in recs:
        by.setdefault(r["id"], []).append(r["correct"])
    return {k: round(sum(v) / len(v), 4) for k, v in by.items()}


class Lane:
    def __init__(self, a):
        self.a = a
        self.out = Path(a.out) / a.arm
        self.out.mkdir(parents=True, exist_ok=True)
        self.log = Logger(self.out / "lane.log")
        self.t0 = time.time()
        self.end = self.t0 + a.deadline_s
        self.timing = {}
        self.dev, self.dt = device_dtype()
        name = a.model
        if a.smoke:
            from sleep2.askonce.model_io import make_tiny
            from .tools import SYSTEM_PROMPT
            name = "tiny:" + make_tiny(self.out / "tiny", [SYSTEM_PROMPT, "<tool>python</tool><input>print(1)</input> ANSWER: 1 0 1 2 3 4 5 6 7 8 9"] * 20)
        self.log("env", env_info())
        self.tok = get_tokenizer(name)
        self.model = load_model(name, self.dt, self.dev)
        assert_finite_forward(self.model, self.tok, self.log)
        self.pool, self.test, self.sib = load_sets(PDATA, a.practice_n)
        arc = json.loads((ASK_DATA / "arc_easy_500.json").read_text())
        self.arc = arc[: a.arc_n]
        self.log(f"pool {len(self.pool)} test {len(self.test)} sibling {len(self.sib)} arc {len(self.arc)}")
        self.H = Harness(self.model, self.tok, 0.7, 768, 6000, a.bs, log=self.log)
        from .library import get_library
        get_library()  # build the BM25 index once, before worker threads call search()
        self.trainer = None
        self.store = []

    # ------------------------------------------------------------------
    def stamp(self, key, t):
        self.timing[key] = round(time.time() - t, 1)
        jdump(self.out / "timing.json", dict(self.timing, elapsed_s=round(time.time() - self.t0, 1)))

    def active_model(self):
        return self.trainer.pm if self.trainer else self.model

    def evaluate(self, tag, test=None, sib=None, arc=None, tries=None, seed=0):
        tries = tries or self.a.tries
        t = time.time()
        self.H.model = self.active_model()
        res = {"tag": tag}
        for name, ps in (("test", test if test is not None else self.test), ("sibling", sib if sib is not None else self.sib)):
            recs = self.H.run(ps, tries, seed * 10 + (1 if name == "test" else 2), deadline=self.end, label=f"{tag}/{name}")
            for r in recs:
                jl_append(self.out / "eval" / f"{tag}_{name}.jsonl", r)
            res[name] = dict(summarize(recs), puzzle_scores=puzzle_scores(recs))
        t_arc = time.time()
        res["arc_easy"] = eval_arc(self.active_model(), self.tok, self.arc if arc is None else arc, self.log)
        res["arc_seconds"] = round(time.time() - t_arc, 1)
        res["seconds"] = round(time.time() - t, 1)
        jdump(self.out / "results" / f"{tag}.json", res)
        self.log(f"EVAL {tag}: test {res['test']['acc']} sibling {res['sibling']['acc']} arc {res['arc_easy']['acc']} tools/try {res['test']['tool_calls_per_try']} ({res['seconds']}s)")
        return res

    def day(self, n, seed, deadline):
        t = time.time()
        self.H.model = self.active_model()
        path = self.out / "day" / f"day{n}.jsonl"
        recs = self.H.run(self.pool, self.a.tries, seed, deadline=deadline, on_done=lambda r: jl_append(path, r), label=f"day{n}")
        self.store += recs
        s = dict(summarize(recs), planned=len(self.pool) * self.a.tries, seconds=round(time.time() - t, 1))
        jdump(self.out / "results" / f"day{n}.json", s)
        self.log(f"DAY {n}: {s}")
        return s

    def night(self, n, seed, n_steps=None, n_sft=None, epochs=None, n_pairs=None, arm=None):
        t = time.time()
        n_steps, n_sft, epochs, n_pairs = n_steps or self.a.steps, n_sft or self.a.n_sft, epochs or self.a.epochs, n_pairs if n_pairs is not None else self.a.n_pairs
        if self.trainer:
            self.model = self.trainer.release()
            self.trainer = None
        anchors = [render(start_messages(p), True, self.tok.bos_token or "") for p in self.pool[:50]]
        self.trainer, st = N.train_night(self.model, self.tok, arm or self.a.arm, self.store, seed, n, self.dev, self.dev == "cuda" and str(self.dt) == "torch.float16",
                                         anchors, n_steps, n_sft, epochs, n_pairs, log=self.log)
        st["seconds_total"] = round(time.time() - t, 1)
        jdump(self.out / "results" / f"night{n}.json", st)
        return st

    # ------------------------------------------------------------------
    def run(self):
        a = self.a
        seed = a.seed
        t = time.time()
        self.evaluate("A0", seed=seed)
        self.stamp("eval_A0_s", t)
        eval_s, night_s = self.timing["eval_A0_s"] * 1.15, a.night_est_s  # until measured
        for n in range(1, a.nights + 1):
            left = self.end - time.time()
            if left < eval_s + night_s + 600:
                self.log(f"stopping before day {n}: {left / 60:.0f} min left")
                break
            t = time.time()
            self.day(n, seed * 100 + n, deadline=self.end - eval_s - night_s * 1.1)
            self.stamp(f"day{n}_s", t)
            t = time.time()
            self.night(n, seed)
            self.stamp(f"night{n}_s", t)
            night_s = self.timing[f"night{n}_s"]
            t = time.time()
            self.evaluate(f"{self.a.arm}{n}", seed=seed * 100 + n)
            self.stamp(f"eval{n}_s", t)
            eval_s = self.timing[f"eval{n}_s"] * 1.1
        self.log("lane done", f"{(time.time() - self.t0) / 3600:.2f} h")

    def pilot(self):
        """20 practice + 20 test puzzles (one try each) and a 10-step night; project the full lane."""
        a = self.a
        npz = min(20, len(self.pool))
        pool, test = self.pool[:npz], self.test[:20]
        t = time.time()
        self.H.model = self.model
        r_test = self.H.run(test, 1, 1, label="pilot/test-base")
        s_base = (time.time() - t) / max(1, len(r_test))
        t = time.time()
        r_day = self.H.run(pool, 1, 2, label="pilot/day-base")
        s_day_base = (time.time() - t) / max(1, len(r_day))
        self.store = r_day
        t = time.time()
        n_sft, n_pairs = 20, 8
        st = self.night(1, 1, n_steps=10, n_sft=n_sft, epochs=1, n_pairs=n_pairs, arm="C")  # C builds lessons from all tries, so it runs even with 0 wins
        night_s = time.time() - t
        t = time.time()
        self.H.model = self.active_model()
        r_ad = self.H.run(test, 1, 3, label="pilot/test-adapter")
        s_ad = (time.time() - t) / max(1, len(r_ad))
        t = time.time()
        eval_arc(self.active_model(), self.tok, self.arc[:20], self.log)
        arc_s = (time.time() - t) / 20 * 200
        tr = st.get("train", {})
        units_each = max(1, st["n_items"])
        # one training sequence ~ one unit; a pair costs about 2.4 sequences (two sequences + reference forwards)
        seq_equiv_pilot = n_sft + 2.4 * st.get("pairs", 0)
        night_full = night_s * (2 * N.N_SFT + 2.4 * N.N_PAIRS) / max(1.0, seq_equiv_pilot)
        eval_full = (len(self.test) + len(self.sib)) * TRIES * s_ad + arc_s
        eval_a0 = (len(self.test) + len(self.sib)) * TRIES * s_base + arc_s
        s_day_ad = s_day_base * s_ad / max(1e-9, s_base)
        fixed = eval_a0 + N_NIGHTS * (night_full + eval_full)
        budget = LANE_BUDGET_H * 3600 * 0.95
        avail = budget - fixed
        n_tries_fit = int(avail // (N_NIGHTS * s_day_ad)) if avail > 0 else 0
        n_pz = n_tries_fit // TRIES
        full_pool = len(load_sets(PDATA)[0])
        proj_h = (fixed + N_NIGHTS * full_pool * TRIES * s_day_ad) / 3600
        out = {"arm": a.arm, "sec_per_try_test_base": round(s_base, 1), "sec_per_try_day_base": round(s_day_base, 1), "sec_per_try_test_adapter": round(s_ad, 1),
               "sec_per_try_day_adapter_est": round(s_day_ad, 1), "pilot_night_s": round(night_s, 1), "pilot_night_train": tr.get("seconds"),
               "night_full_est_s": round(night_full), "eval_full_est_s": round(eval_full), "eval_A0_est_s": round(eval_a0), "arc200_est_s": round(arc_s),
               "full_pool_size": full_pool, "projected_full_run_h_with_full_pool": round(proj_h, 2), "suggested_practice_n": max(0, min(full_pool, n_pz)),
               "fixed_h": round(fixed / 3600, 2), "pilot_acc_test": summarize(r_test)["acc"], "pilot_tools_per_try": summarize(r_test)["tool_calls_per_try"],
               "pilot_day": summarize(r_day), "pilot_night": st, "gen_stats": self.H.stats, "peak_mem_gb": tr.get("peak_mem_gb")}
        jdump(self.out / "pilot.json", out)
        self.log("PILOT", json.dumps(out)[:2000])
        print(f"PILOT: {s_day_ad:.1f} s per practice try (adapter), {s_base:.1f} s per test try (base); full run with the whole pool "
              f"({full_pool}) = {proj_h:.1f} h; suggested practice-pool size for a 10 h lane: {out['suggested_practice_n']}", flush=True)
        return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["P", "C"], required=True)
    ap.add_argument("--lane", type=int, default=0)
    ap.add_argument("--out", default=os.environ.get("OUT", "out"))
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--practice-n", type=int, default=None)
    ap.add_argument("--deadline-s", type=float, default=LANE_BUDGET_H * 3600)
    ap.add_argument("--night-est-s", type=float, default=2400)
    ap.add_argument("--arc-n", type=int, default=200)
    ap.add_argument("--bs", type=int, default=12)
    ap.add_argument("--nights", type=int, default=N_NIGHTS)
    ap.add_argument("--tries", type=int, default=TRIES)
    ap.add_argument("--steps", type=int, default=N.N_STEPS)
    ap.add_argument("--n-sft", type=int, default=N.N_SFT)
    ap.add_argument("--epochs", type=int, default=N.EPOCHS)
    ap.add_argument("--n-pairs", type=int, default=N.N_PAIRS)
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    if a.seed is None:
        a.seed = 1 + a.lane
    lane = Lane(a)
    return lane.pilot() if a.pilot else lane.run()


if __name__ == "__main__":
    main()
