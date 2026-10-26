"""Practice-1 lane (one lane = one chain on one GPU):
  A0 eval (sealed test100 x2, sibling60 x1, ARC-Easy 200) -> 3 x (day on the practice pool x2 tries -> night), eval after nights 1 and 3.
  python -m practice.job --arm P --lane 0 --out $OUT [--practice-n N] [--deadline-s S] [--pilot] [--smoke] [--backend auto|hf|vllm]
Everything is saved incrementally to <out>/<arm>/ (results/*.json, day/*.jsonl, eval/*.jsonl, adapters/nightN, timing.json, config.json). --pilot times a
small slice (pilot.json is rewritten after every stage) and projects the full-run hours and a suggested practice-pool size.

Backends. hf: the model stays loaded in this process (HF generate, stop at </input>, sticky batch size). vllm / auto: this process only orchestrates; every
generation phase (eval, day) and every night runs in its own subprocess (`python -m practice.job --spec FILE`), so vLLM and the HF training model never share
the GPU and the memory is freed when the subprocess exits. The night saves its peft adapter (adapters/nightN); the next generation subprocess serves it as a
vLLM LoRARequest without merging. If vLLM cannot be imported, or a phase fails with it, the lane falls back (vllm -> vllm-eager -> hf) and says so in the log.
Caps, equal for every arm: MAX_NEW 512 per turn, MAX_TURNS 6, MAX_CTX 4096."""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from sleep2.askonce.config import DATA as ASK_DATA
from sleep2.askonce.config import MODEL_ID, jdump, jload
from sleep2.askonce.eval_moves import eval_arc
from sleep2.askonce.job_common import Logger, assert_finite_forward, device_dtype, env_info
from sleep2.askonce.model_io import get_tokenizer, load_model

from . import night as N
from .tools import CLOSE_TAGS as _CLOSE_TAGS
STOPS_CFG = list(_CLOSE_TAGS) + ["<|ifm|im_end|>"]
from .harness import Harness, render, start_messages, summarize
from .tools import MAX_TURNS

HERE = Path(__file__).resolve().parent
PDATA = HERE / "data"
N_NIGHTS = 3
TRIES = 2  # module defaults; overridden by --nights / --tries
LANE_BUDGET_H = 10.0
PLAN_H = 9.5            # the full lane must fit this (projection)
MAX_NEW, MAX_CTX = 512, 4096   # MAX_TURNS comes from tools (6); all three are the same for every arm
VLLM_UTIL = 0.85


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




def project(stages, a, full_pool, n_test, n_sib, budget_h=PLAN_H):
    """Project the full lane from the pilot stages (each: n, seconds, overhead_s, arc_seconds, arc_n). Returns the projection dict (empty if stages are missing)."""
    tb, db, ta, ni = stages.get("test_base"), stages.get("day_base"), stages.get("test_adapter"), stages.get("night")
    per = lambda st: st["seconds"] / max(1, st["n"])  # noqa: E731
    if not tb:
        return {}
    s_base = per(tb)
    s_day_base = per(db) if db else s_base
    s_ad = per(ta) if ta else s_base
    arc_st = ta or tb
    arc_s = (arc_st.get("arc_seconds") or 0) / max(1, arc_st.get("arc_n") or 1) * 200
    ovh = [st.get("overhead_s", 0) for st in stages.values() if st and "overhead_s" in st]
    overhead = sum(ovh) / len(ovh) if ovh else 0.0
    tries, sib_tries = TRIES, 1
    ev_tries = n_test * tries + n_sib * sib_tries
    if ni and ni.get("n_items"):
        seq_pilot = ni["n_sft_pilot"] + 2.4 * ni.get("pairs", 0)
        night_full = ni["seconds"] * (2 * N.N_SFT + 2.4 * N.N_PAIRS) / max(1.0, seq_pilot)
    else:
        night_full = 2400.0
    eval_a0 = ev_tries * s_base + arc_s
    eval_ad = ev_tries * s_ad + arc_s
    s_day_ad = s_day_base * s_ad / max(1e-9, s_base)
    phases = 1 + 3 * 2 + 2  # A0 eval, 3 x (day + night), evals after night 1 and 3
    fixed = eval_a0 + 3 * night_full + 2 * eval_ad + phases * overhead
    avail = budget_h * 3600 - fixed
    n_pz = int(avail // (3 * tries * s_day_ad)) if avail > 0 else 0
    proj_h = (fixed + 3 * full_pool * tries * s_day_ad) / 3600
    return {"sec_per_try_test_base": round(s_base, 1), "sec_per_try_day_base": round(s_day_base, 1), "sec_per_try_test_adapter": round(s_ad, 1),
            "sec_per_try_day_adapter_est": round(s_day_ad, 1), "night_full_est_s": round(night_full), "eval_A0_est_s": round(eval_a0), "eval_adapter_est_s": round(eval_ad),
            "arc200_est_s": round(arc_s), "phase_overhead_s": round(overhead, 1), "full_pool_size": full_pool, "fixed_h": round(fixed / 3600, 2),
            "projected_full_run_h_with_full_pool": round(proj_h, 2), "suggested_practice_n": max(0, min(full_pool, n_pz)), "plan_h": budget_h}



def kill_group(pgid):
    """SIGKILL a finished phase's whole process group (vLLM engine children survive their parent's exit)."""
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def kill_gpu_apps(idx):
    """Kill compute processes still holding GPU `idx` (only ever phase leftovers: the lane process itself never touches the GPU in subprocess mode)."""
    try:
        bus = subprocess.run(["nvidia-smi", "-i", idx, "--query-gpu=gpu_bus_id", "--format=csv,noheader"], capture_output=True, text=True, timeout=20).stdout.strip()
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_bus_id", "--format=csv,noheader"], capture_output=True, text=True, timeout=20).stdout
    except Exception:  # noqa: BLE001
        return
    for line in out.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 2 and parts[1] == bus and parts[0].isdigit() and int(parts[0]) != os.getpid():
            try:
                os.kill(int(parts[0]), signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass

class Lane:
    def __init__(self, a):
        g = lambda k, d=None: getattr(a, k, d)  # noqa: E731  (older namespaces lack the newer fields)
        self.a = a
        self.out = Path(a.out) / a.arm
        self.out.mkdir(parents=True, exist_ok=True)
        self.log = Logger(self.out / "lane.log")
        self.t0 = g("t0_epoch") or time.time()
        self.log.t0 = self.t0
        self.end = g("end_epoch") or (self.t0 + a.deadline_s)
        self.timing = {}
        self.dev, self.dt = device_dtype()
        self.kind = g("kind")            # set in a phase worker subprocess
        self.worker = bool(self.kind)
        self.wmode = g("worker_mode", "hf")
        self.adapter = g("adapter")      # peft adapter dir the next generation phase serves
        self.model = self.backend = self.trainer = None
        self.startup_s = 0.0
        name = a.model
        if a.smoke:
            from sleep2.askonce.model_io import make_tiny
            from .tools import SYSTEM_PROMPT
            name = "tiny:" + make_tiny(self.out / "tiny", [SYSTEM_PROMPT, "<tool>python</tool><input>print(1)</input> ANSWER: 1 0 1 2 3 4 5 6 7 8 9"] * 20)
        self.name = name
        self.modes, self.vpy, self.sub = ["hf"], sys.executable, False
        if not self.worker:
            self.probe_backends()
        if (not self.worker and not self.sub) or (self.worker and (self.kind == "night" or self.wmode == "hf")):  # CUDA is initialised only where HF runs
            self.log("env", env_info())
        self.tok = get_tokenizer(name)
        if g("rg_skill"):  # Practice-2: rgdata/ is written by rg_run (test set, day puzzles, or the stage-0 set); the sibling slot holds the sealed test100
            rd = Path(a.out) / "rgdata"
            _, test100, _ = load_sets(PDATA)
            self.pool, self.test, self.sib = jl(rd / "day1.jsonl")[:50], jl(rd / f"{g('rg_test', 'test')}.jsonl"), test100  # pool: night anchors only
        else:
            self.pool, self.test, self.sib = load_sets(PDATA, a.practice_n)
        arc = json.loads((ASK_DATA / "arc_easy_500.json").read_text())
        self.arc = arc[: a.arc_n]
        if not self.worker:
            self.log(f"pool {len(self.pool)} test {len(self.test)} sibling {len(self.sib)} arc {len(self.arc)}")
        from .library import get_library
        get_library()  # build the BM25 index once, before worker threads call search()
        t = time.time()
        if self.worker:
            self.setup_worker()
        elif not self.sub:
            self.model = load_model(name, self.dt, self.dev)
            assert_finite_forward(self.model, self.tok, self.log)
        self.startup_s = round(time.time() - t, 1)
        self.H = None
        if self.model is not None or self.backend is not None:
            self.H = Harness(self.model, self.tok, 0.7, MAX_NEW, MAX_CTX, a.bs, MAX_TURNS, log=self.log, backend=self.backend)
        if not self.worker:
            self.write_config()

    # ------------------------------------------------------------------ backend selection
    def probe_backends(self):
        a = self.a
        want = getattr(a, "backend", "hf")
        if a.smoke and os.environ.get("PRACTICE_TEST_SUB"):  # tests: exercise the subprocess plumbing with HF workers on the tiny model
            self.modes, self.sub = ["hf"], True
            self.log("backend: hf in subprocess phases (test)")
            return
        if a.smoke or want == "hf":
            self.log(f"backend: hf (requested={want}, smoke={a.smoke})")
            return
        self.vpy = os.environ.get("VLLM_PY") or sys.executable
        try:
            r = subprocess.run([self.vpy, "-c", "import vllm; print(vllm.__version__)"], capture_output=True, text=True, timeout=600)
            ok, info = r.returncode == 0, (r.stdout.strip() or r.stderr.strip()[-300:])
        except Exception as e:  # noqa: BLE001
            ok, info = False, repr(e)
        if ok:
            self.modes, self.sub = ["vllm", "vllm-eager", "hf"], True
            self.vllm_version = info
            self.log(f"backend: vllm {info} via {self.vpy}; generation and nights run in subprocesses; fallback order {self.modes}")
        else:
            self.log(f"backend: vllm NOT available ({info}); FALLING BACK to HF generate in this process")

    def write_config(self):
        a = self.a
        cfg = {"arm": a.arm, "max_new_per_turn": MAX_NEW, "max_turns": MAX_TURNS, "max_ctx": MAX_CTX, "temperature": 0.7, "stop": STOPS_CFG,
               "backend_requested": getattr(a, "backend", "hf"), "backend_modes": self.modes, "subprocess_phases": self.sub, "vllm_python": self.vpy if self.sub else None,
               "vllm_version": getattr(self, "vllm_version", None), "vllm": {"dtype": "float16", "max_model_len": MAX_CTX, "gpu_memory_utilization": VLLM_UTIL,
               "enable_prefix_caching": True, "enable_lora": True, "max_lora_rank": 16}, "hf_start_bs": a.bs, "tries": a.tries, "sibling_tries": getattr(a, "sib_tries", 1),
               "eval_nights": getattr(a, "eval_nights", "1,3"), "nights": a.nights, "practice_n": a.practice_n, "n_sft": a.n_sft, "epochs": a.epochs, "n_pairs": a.n_pairs,
               "steps": a.steps, "model": a.model}
        jdump(self.out / "config.json", cfg)

    def setup_worker(self):
        """Phase subprocess: load only what the phase needs (night: HF model; generation: vLLM engine or HF model [+ adapter])."""
        a = self.a
        if self.kind == "night" or self.wmode == "hf":
            self.model = load_model(self.name, self.dt, self.dev)
            assert_finite_forward(self.model, self.tok, self.log)
            if self.kind != "night" and self.adapter:
                from peft import PeftModel
                self.model = PeftModel.from_pretrained(self.model, self.adapter).eval()
                self.log(f"HF backend with adapter {self.adapter}")
        else:
            from .gen import VLLMBackend
            self.backend = VLLMBackend(self.name, self.tok, self.adapter, lora_id=int(getattr(a, "n", 0) or 0) + 1, max_len=MAX_CTX, util=VLLM_UTIL,
                                       eager=self.wmode == "vllm-eager", seed=a.seed, log=self.log)

    # ------------------------------------------------------------------
    def stamp(self, key, t):
        self.timing[key] = round(time.time() - t, 1)
        jdump(self.out / "timing.json", dict(self.timing, elapsed_s=round(time.time() - self.t0, 1)))

    def active_model(self):
        return self.trainer.pm if self.trainer else self.model

    def backend_name(self):
        return self.backend.describe() if self.backend is not None else "hf"

    def run_arc(self, arc):
        if self.backend is not None:
            return self.backend.arc_eval(arc, render)
        return eval_arc(self.active_model(), self.tok, arc, self.log)

    # ------------------------------------------------------------------ local phase bodies (in this process: in-process HF lane, or a phase worker)
    def _use_active(self):
        if self.backend is None:
            self.H.model = self.active_model()

    def _local(self, s):
        return {"eval": self._eval, "day": self._day, "night": self._night, "rollouts": self._rollouts}[s["kind"]](s)

    def _eval(self, s):
        tag, seed = s["tag"], s["seed"]
        tmap = s.get("tries_map") or {"test": self.a.tries, "sibling": getattr(self.a, "sib_tries", 1)}
        t = time.time()
        self._use_active()
        res = {"tag": tag, "backend": self.backend_name()}
        for name, ps, tr in [(k, v, tmap[k]) for k, v in (("test", self.test), ("sibling", self.sib)) if k in tmap]:
            path = self.out / "eval" / f"{tag}_{name}.jsonl"
            path.unlink(missing_ok=True)
            recs = self.H.run(ps, tr, seed * 10 + (1 if name == "test" else 2), deadline=self.end, label=f"{tag}/{name}")
            for r in recs:
                jl_append(path, r)
            res[name] = dict(summarize(recs), puzzle_scores=puzzle_scores(recs))
        t_arc = time.time()
        if self.arc:
            res["arc_easy"] = self.run_arc(self.arc)
        res["arc_seconds"] = round(time.time() - t_arc, 1)
        res["seconds"] = round(time.time() - t, 1)
        res["gen_stats"] = dict(self.H.stats)
        jdump(self.out / "results" / f"{tag}.json", res)
        self.log(f"EVAL {tag}: " + " ".join(f"{k} {res[k]['acc']}" for k in tmap) + f" arc {res.get('arc_easy', {}).get('acc')} ({res['seconds']}s)")
        return res

    def _day(self, s):
        n, seed = s["n"], s["seed"]
        t = time.time()
        self._use_active()
        path = self.out / "day" / f"day{n}.jsonl"
        path.unlink(missing_ok=True)
        ps = jl(s["puzzles"]) if s.get("puzzles") else self.pool  # Practice-2: fresh puzzles every day
        recs = self.H.run(ps, self.a.tries, seed, deadline=s.get("deadline"), on_done=lambda r: jl_append(path, r), label=f"day{n}")
        res = dict(summarize(recs), planned=len(ps) * self.a.tries, seconds=round(time.time() - t, 1), backend=self.backend_name(), gen_stats=dict(self.H.stats))
        jdump(self.out / "results" / f"day{n}.json", res)
        self.log(f"DAY {n}: {res}")
        return res

    def _store(self, n):
        """All tries gathered on days 1..n (read from the day files, so a night subprocess sees what the day subprocesses wrote)."""
        return [r for k in range(1, n + 1) for r in jl(self.out / "day" / f"day{k}.jsonl")]

    def _night(self, s):
        a = self.a
        n, seed = s["n"], s["seed"]
        t = time.time()
        n_steps, n_sft, epochs, n_pairs = None if s.get("auto_steps") else (s.get("steps") or a.steps), s.get("n_sft") or a.n_sft, s.get("epochs") or a.epochs, s["n_pairs"] if s.get("n_pairs") is not None else a.n_pairs
        if self.trainer:
            self.model = self.trainer.release()
            self.trainer = None
        anchors = [render(start_messages(p), True, self.tok.bos_token or "") for p in self.pool[:50]]
        self.trainer, st = N.train_night(self.model, self.tok, s.get("night_arm") or a.arm, self._store(n), seed, n, self.dev, self.dev == "cuda" and str(self.dt) == "torch.float16",
                                         anchors, n_steps, n_sft, epochs, n_pairs, log=self.log, dedup=bool(s.get("dedup")))
        adir = self.out / "adapters" / f"night{n}"
        self.trainer.pm.save_pretrained(str(adir))  # the next generation phase serves this (vLLM LoRARequest, never merged)
        st["adapter"] = str(adir)
        st["n_sft_pilot"] = n_sft
        st["seconds_total"] = round(time.time() - t, 1)
        jdump(self.out / "results" / f"night{n}.json", st)
        return st

    def _rollouts(self, s):
        """Free-form slice (pilot): `count` puzzles of set `which`, `tries` each, written to `dest`; optional ARC-Easy timing."""
        ps = {"test": self.test, "pool": self.pool, "sibling": self.sib}[s["which"]][: s["count"]]
        self._use_active()
        dest = self.out / s["dest"]
        dest.unlink(missing_ok=True)
        before = dict(self.H.stats)
        t = time.time()
        recs = self.H.run(ps, s["tries"], s["seed"], deadline=self.end, on_done=lambda r: jl_append(dest, r), label=s["name"])
        res = {"n": len(recs), "planned": len(ps) * s["tries"], "seconds": round(time.time() - t, 1), "backend": self.backend_name(), "summary": summarize(recs),
               "gen_tokens": self.H.stats["gen_tokens"] - before["gen_tokens"], "gen_s": round(self.H.stats["gen_s"] - before["gen_s"], 1),
               "tool_s": round(self.H.stats["tool_s"] - before["tool_s"], 1)}
        res["tok_per_s"] = round(res["gen_tokens"] / max(1e-9, res["gen_s"]), 1)
        if s.get("arc_n"):
            t = time.time()
            r = self.run_arc(self.arc[: s["arc_n"]])
            res.update(arc_seconds=round(time.time() - t, 1), arc_n=s["arc_n"], arc_acc=r["acc"])
        return res

    # ------------------------------------------------------------------ dispatch (in process, or one subprocess per phase with fallback)
    def phase(self, kind, name, **spec):
        spec.update(kind=kind, name=name)
        if not self.sub:
            t = time.time()
            res = self._local(spec)
            res["wall_s"], res["overhead_s"] = round(time.time() - t, 1), 0.0
            return res
        pdir = self.out / "phase"
        pdir.mkdir(exist_ok=True)
        while True:
            mode = self.modes[0]
            gen_phase = kind != "night"
            wm = mode if gen_phase else "hf"
            full = dict(vars(self.a), **spec, worker_mode=wm, t0_epoch=self.t0, end_epoch=self.end, adapter=self.adapter if gen_phase else None)
            sp, rp = pdir / f"{name}.spec.json", pdir / f"{name}.result.json"
            rp.unlink(missing_ok=True)
            sp.write_text(json.dumps(full))
            py = self.vpy if wm.startswith("vllm") else sys.executable
            env = dict(os.environ, VLLM_WORKER_MULTIPROC_METHOD="spawn")
            t = time.time()
            self.log(f"PHASE {name} [{wm}] start")
            with open(pdir / f"{name}.{wm}.out", "w") as fo:
                proc = subprocess.Popen([py, "-m", "practice.job", "--spec", str(sp)], cwd=str(HERE.parent), env=env, stdout=fo, stderr=subprocess.STDOUT,
                                        start_new_session=True)  # own process group, so leftover vLLM EngineCore children can be killed with it
                rc = proc.wait()
            wall = round(time.time() - t, 1)
            kill_group(proc.pid)
            self.wait_gpu_free()
            if rc == 0 and rp.exists():
                res = json.loads(rp.read_text())
                res["wall_s"], res["overhead_s"] = wall, round(wall - res.get("seconds_total", res.get("seconds", 0)) - res.get("arc_seconds", 0) * (kind == "rollouts"), 1)
                self.log(f"PHASE {name} [{wm}] ok in {wall}s")
                return res
            tail = (pdir / f"{name}.{wm}.out").read_text()[-1200:].replace("\n", " | ")
            if not gen_phase or wm == "hf":
                raise RuntimeError(f"phase {name} failed (rc {rc}): {tail}")
            self.modes.pop(0)
            self.log(f"WARNING vLLM backend failed in phase {name} (mode {wm}, rc {rc}): {tail}")
            self.log(f"WARNING falling back to {self.modes[0]} for the rest of the run (partial outputs of this phase are discarded and rerun)")

    def wait_gpu_free(self, limit_mib=1500, timeout_s=180):
        """After a phase subprocess exits, wait until its GPU memory is released (nvidia-smi); log the reading."""
        idx = (os.environ.get("CUDA_VISIBLE_DEVICES") or "0").split(",")[0]
        used = None
        for _ in range(timeout_s // 3):
            try:
                used = int(subprocess.run(["nvidia-smi", "-i", idx, "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True,
                                          timeout=20).stdout.strip().split()[0])
            except Exception:  # noqa: BLE001
                return
            if used < limit_mib:
                break
            kill_gpu_apps(idx)  # pilot 2: an orphaned vLLM engine kept 12 GB after its phase exited
            time.sleep(3)
        self.log(f"gpu {idx} memory used after phase: {used} MiB" + ("" if used is not None and used < limit_mib else "  WARNING not freed"))

    def evaluate(self, tag, seed=0):
        return self.phase("eval", f"eval_{tag}", tag=tag, seed=seed)

    def day(self, n, seed, deadline, **kw):
        return self.phase("day", f"day{n}", n=n, seed=seed, deadline=deadline, **kw)

    def night(self, n, seed, **kw):
        st = self.phase("night", f"night{n}", n=n, seed=seed, **kw)
        self.adapter = st["adapter"]
        return st

    # ------------------------------------------------------------------
    def run(self):
        a = self.a
        seed = a.seed
        eval_nights = {int(x) for x in str(getattr(a, "eval_nights", "1,3")).split(",") if x}
        t = time.time()
        self.evaluate("A0", seed=seed)
        self.stamp("eval_A0_s", t)
        eval_s, night_s = self.timing["eval_A0_s"] * 1.15, a.night_est_s  # until measured
        for n in range(1, a.nights + 1):
            left = self.end - time.time()
            n_ev = len([k for k in eval_nights if k >= n]) or 1
            if left < eval_s + night_s + 600:
                self.log(f"stopping before day {n}: {left / 60:.0f} min left")
                break
            t = time.time()
            self.day(n, seed * 100 + n, deadline=self.end - eval_s * n_ev - night_s * 1.1)
            self.stamp(f"day{n}_s", t)
            t = time.time()
            self.night(n, seed)
            self.stamp(f"night{n}_s", t)
            night_s = self.timing[f"night{n}_s"]
            if n in eval_nights or n == a.nights:
                t = time.time()
                self.evaluate(f"{a.arm}{n}", seed=seed * 100 + n)
                self.stamp(f"eval{n}_s", t)
                eval_s = self.timing[f"eval{n}_s"] * 1.1
        self.log("lane done", f"{(time.time() - self.t0) / 3600:.2f} h")

    def pilot(self):
        """12 test puzzles x1, 12 practice x1, a 10-step night, 12 test with the adapter (+20 ARC-Easy). pilot.json is rewritten after every stage."""
        a = self.a
        npz = 12
        out = {"arm": a.arm, "backend_modes": self.modes, "caps": {"max_new": MAX_NEW, "max_turns": MAX_TURNS, "max_ctx": MAX_CTX}, "stages": {}, "done": []}
        full_pool = len(load_sets(PDATA)[0])

        def save(stage=None):
            if stage:
                out["done"].append(stage)
            out["elapsed_min"] = round((time.time() - self.t0) / 60, 1)
            out["backend_now"] = self.modes[0]
            out["projection"] = project(out["stages"], a, full_pool, len(self.test), len(self.sib))
            jdump(self.out / "pilot.json", out)

        save()
        try:
            out["stages"]["test_base"] = self.phase("rollouts", "pilot_test_base", which="test", count=npz, tries=1, seed=1, dest="eval/pilot_test_base.jsonl")
            save("test_base")
            out["stages"]["day_base"] = self.phase("rollouts", "pilot_day_base", which="pool", count=npz, tries=1, seed=2, dest="day/day1.jsonl")
            save("day_base")
            st = self.night(1, 1, steps=10, n_sft=20, epochs=1, n_pairs=8, night_arm="C")  # C builds lessons from all tries, so it runs even with 0 wins
            st["seconds"] = st["seconds_total"]
            out["stages"]["night"] = st
            save("night")
            out["stages"]["test_adapter"] = self.phase("rollouts", "pilot_test_adapter", which="test", count=npz, tries=1, seed=3, dest="eval/pilot_test_adapter.jsonl", arc_n=20)
            save("test_adapter")
        except Exception as e:  # noqa: BLE001
            import traceback
            out["error"] = traceback.format_exc()[-3000:]
            save()
            self.log("PILOT stage failed:", repr(e))
            raise
        proj = out["projection"]
        self.log("PILOT", json.dumps(out)[:2500])
        print(f"PILOT [{out['backend_now']}]: {proj['sec_per_try_day_adapter_est']} s per practice try (adapter), {proj['sec_per_try_test_base']} s per test try (base); "
              f"full run with the whole pool ({full_pool}) = {proj['projected_full_run_h_with_full_pool']} h; suggested --practice-n for a {PLAN_H} h plan: "
              f"{proj['suggested_practice_n']}", flush=True)
        return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rg-skills", help="Practice-2: comma-separated Reasoning Gym skills, or auto (read <out>/stage0.json)")
    ap.add_argument("--stage0", action="store_true", help="Practice-2 stage 0: base model, 40 puzzles x 1 try per candidate skill (seed 100) -> <out>/stage0.json")
    ap.add_argument("--rg-day-n", type=int, default=1000, help="fresh puzzles per day (seed 1000+day)")
    ap.add_argument("--rg-test-n", type=int, default=300)
    ap.add_argument("--test-tries", type=int, default=2)
    ap.add_argument("--stage0-n", type=int, default=40)
    ap.add_argument("--arm", choices=["P", "C"])
    ap.add_argument("--lane", type=int, default=0)
    ap.add_argument("--out", default=os.environ.get("OUT", "out"))
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--practice-n", type=int, default=None)
    ap.add_argument("--deadline-s", type=float, default=LANE_BUDGET_H * 3600)
    ap.add_argument("--night-est-s", type=float, default=2400)
    ap.add_argument("--arc-n", type=int, default=200)
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--nights", type=int, default=N_NIGHTS)
    ap.add_argument("--tries", type=int, default=None, help="tries per practice puzzle (default 2; 4 in Practice-2 mode)")
    ap.add_argument("--steps", type=int, default=N.N_STEPS)
    ap.add_argument("--n-sft", type=int, default=N.N_SFT)
    ap.add_argument("--epochs", type=int, default=N.EPOCHS)
    ap.add_argument("--n-pairs", type=int, default=N.N_PAIRS)
    ap.add_argument("--backend", choices=["auto", "hf", "vllm"], default="auto")
    ap.add_argument("--eval-nights", default="1,3", help="nights after which the sealed test is run (A0 always is)")
    ap.add_argument("--sib-tries", type=int, default=1)
    ap.add_argument("--spec", help="internal: JSON file with all arguments of one phase subprocess")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    if a.spec:
        a = argparse.Namespace(**json.loads(Path(a.spec).read_text()))
        lane = Lane(a)
        res = lane._local(vars(a))
        res["startup_s"] = lane.startup_s
        Path(a.out, a.arm, "phase", f"{a.name}.result.json").write_text(json.dumps(res))
        lane.log(f"phase {a.name} done (startup {lane.startup_s}s)")
        sys.stdout.flush()
        os._exit(0)  # process death frees the GPU even if a vLLM engine thread would hang on shutdown
    if a.stage0 or a.rg_skills:
        from . import rg_run
        return rg_run.main(a)
    a.tries = a.tries or TRIES
    if not a.arm:
        ap.error("--arm is required")
    if a.seed is None:
        a.seed = 1 + a.lane
    lane = Lane(a)
    return lane.pilot() if a.pilot else lane.run()


if __name__ == "__main__":
    main()
