"""Practice-1M: the whole Practice-1 experiment on one Apple-Silicon Mac, with live web tools. One orchestrator, one model server at a time.
  ~/learner-ops/.venv/bin/python -m practice.mac_run --out ~/learner-ops/practice1m [--practice-n 120] [--tries 2] [--nights 3]
Order: preflight -> K2 q4 locate/download/convert -> 5-minute speed bench -> A0 eval (shared) -> for arm in P, C: 3 x (day -> night [-> eval after nights 1 and 3]).
Everything is written incrementally under --out; re-running the same command resumes (finished phases are skipped, unfinished day/eval phases continue
from their last saved try). status.json is a heartbeat; summary.json holds test100 per-puzzle scores for every arm/night and the paired tests.
Machine rules (Ben's shared M3): >= 20 GB free disk always; ~/learner-ops/PAUSE_OTHERS present (and not ours) -> stop our server and wait;
~/learner-ops/ASSISTANT_RUNNING present -> a ~21 GB assistant is resident: our peak must stay < 8 GB (q4 K2 for serving AND training, concurrency <= 2, training
memory limit 7 GB), back off on memory-pressure warning. q4 is used for both serving and training in every mode so the arms stay comparable."""
import argparse
import hashlib
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import lessons as L
from . import pe_pool
from .gen import OpenAIBackend, ServerManager
from .grade import is_correct  # noqa: F401
from .tools import CLOSE_TAGS as _CLOSE_TAGS
STOPS_CFG = list(_CLOSE_TAGS) + ["<|ifm|im_end|>"]
from .harness import Harness, render, start_messages, summarize
from .tools import MAX_TURNS
from .web import WEB

HERE = Path(__file__).resolve().parent
PDATA = HERE / "data"
OPS = Path(os.path.expanduser("~/learner-ops"))
PRESSURE_REFUSE = int(os.environ.get("P1M_PRESSURE_REFUSE", "2"))  # 4: run through warn, back off only on critical (M1, coordinator 2026-10-26)
MIN_FREE_RAM_GB, ASSIST_PEAK_GB, MIN_FREE_DISK_GB = 12.0, 8.0, 8.0  # disk floor 20 -> 8 GB (Practice-1M: a macOS update download was eating the disk; our runs write MBs)
MAX_NEW, MAX_CTX = 512, 4096
OURS = "practice1m"
K2_Q4_CANDIDATES = ["mlx-community/K2-Horizon-3.7B-4bit", "mlx-community/K2-Horizon-3.7B-4bit-mlx", "mlx-community/K2-Horizon-3.7B-q4"]
K2_SRC = "IFM/K2-Horizon-3.7B"
# Mac night size (smaller than the Kaggle 256x2 + 64 pairs: QLoRA on a laptop); identical for both arms; recorded in config.json
MAC_NIGHT = {"n_sft": 128, "epochs": 1, "n_pairs": 32, "steps": 32, "lr": 1e-4, "rank": 16, "beta": 0.1, "dpo_w": L.DPO_W, "train_max_tokens": 2048, "dpo": True}


class StopRun(Exception):
    pass


def jl(path):
    return [json.loads(l) for l in open(path) if l.strip()] if Path(path).exists() else []


def jl_append(path, rec):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def jdump(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"  # unique per thread: status() is called from worker threads concurrently
    Path(tmp).write_text(json.dumps(obj, indent=1, ensure_ascii=False))
    os.replace(tmp, path)


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


# ---------------------------------------------------------------- system probes (all take a `run` callable so tests can fake them)
def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except Exception:  # noqa: BLE001
        return ""


def parse_vm_stat(txt):
    """-> free-ish RAM in GB (free + inactive + speculative + purgeable pages)."""
    m = re.search(r"page size of (\d+) bytes", txt)
    ps = int(m.group(1)) if m else 16384
    tot = 0
    for key in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable"):
        m = re.search(key + r":\s+(\d+)", txt)
        tot += int(m.group(1)) if m else 0
    return tot * ps / 2 ** 30


def free_ram_gb(run=_run):
    return parse_vm_stat(run(["vm_stat"]))


def swap_used_gb(run=_run):
    m = re.search(r"used = ([\d.]+)([MG])", run(["sysctl", "vm.swapusage"]))
    return (float(m.group(1)) / (1024 if m.group(2) == "M" else 1)) if m else 0.0


def pressure_level(run=_run):
    """1 normal, 2 warn, 4 critical (kern.memorystatus_vm_pressure_level); falls back to `memory_pressure` free percentage."""
    t = run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).strip()
    if t.isdigit():
        return int(t)
    m = re.search(r"free percentage:\s*(\d+)%", run(["memory_pressure"]))
    if m:
        p = int(m.group(1))
        return 4 if p < 5 else 2 if p < 15 else 1
    return 1


def free_disk_gb(path):
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    return shutil.disk_usage(p).free / 2 ** 30


# ---------------------------------------------------------------- data
def load_pool(practice_n=None, data_dir=PDATA):
    rows = jl(data_dir / "practice_pool.jsonl") + jl(data_dir / "sonnet_pool.jsonl") + jl(data_dir / "pe_pool.jsonl")
    keep = ("id", "kind", "prompt", "answer", "answer_type", "source", "title")
    full = [{k: r.get(k) for k in keep} for r in rows]
    sub = sorted(full, key=lambda p: sha("practice1|" + p["id"]))  # same order for both arms (same key as the Kaggle job)
    return (sub[:practice_n] if practice_n else sub), full


def load_eval_sets(data_dir=PDATA):
    keep = ("id", "kind", "prompt", "answer", "answer_type", "source")
    f = lambda rows: [{k: r.get(k) for k in keep} for r in rows]  # noqa: E731
    return f(jl(data_dir / "test100.jsonl")), f(jl(data_dir / "sibling60.jsonl")), jl(data_dir / "test100.jsonl")


def puzzle_scores(recs):
    by = {}
    for r in recs:
        by.setdefault(r["id"], []).append(r["correct"])
    return {k: round(sum(v) / len(v), 4) for k, v in by.items()}


def signflip_p(a, b, n_mc=20000, seed=0):
    """Two-sided paired sign-flip test on per-puzzle score differences (Monte Carlo; exact enumeration when <= 14 non-zero differences)."""
    d = [a[k] - b[k] for k in a if k in b and a[k] != b[k]]
    if not d:
        return 1.0
    obs = abs(sum(d))
    if len(d) <= 14:
        import itertools
        c = sum(abs(sum(s * x for s, x in zip(sg, d))) >= obs - 1e-12 for sg in itertools.product((1, -1), repeat=len(d)))
        return c / 2 ** len(d)
    rng = random.Random(seed)
    c = sum(abs(sum(x if rng.random() < 0.5 else -x for x in d)) >= obs - 1e-12 for _ in range(n_mc))
    return (c + 1) / (n_mc + 1)


class Mac:
    def __init__(self, a, run=_run, server=None):
        self.a, self.sysrun = a, run
        self.out = Path(os.path.expanduser(a.out))
        self.out.mkdir(parents=True, exist_ok=True)
        self.py = a.python or sys.executable
        self.server = server or ServerManager(self.py, a.port, str(self.out / "server_logs"), self.log)
        if getattr(a, "harness", "native") == "opencode":
            from .oc_lessons import load_template
            self.server.extra = ["--chat-template", load_template(a.chat_template)]  # K2 sees the `tools` list; the stock template always thinks
        self.phase, self.phase_t0, self.last_log, self.phases = "init", time.time(), "", jl(self.out / "phases.jsonl")
        self.t0 = time.time()
        self.stop_flag = False
        self.peak_rss_mb = 0.0
        self.lock = threading.Lock()
        self.tok = None
        self.make_backend = self._make_backend
        self.train_fn = self._train_subprocess
        self.pause_enabled = True
        self.mem_wait_s = a.mem_wait_s

    # ------------------------------------------------------------ logging / heartbeat
    def log(self, msg):
        line = f"[{time.strftime('%H:%M:%S')} +{(time.time() - getattr(self, 't0', time.time())) / 60:.0f}m] {msg}"
        self.last_log = line
        print(line, flush=True)
        try:
            with open(self.out / "run.log", "a") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def status(self, **kw):
        st = {"phase": self.phase, "phase_started": self.phase_t0, "updated": time.time(), "updated_iso": time.strftime("%Y-%m-%dT%H:%M:%S"), "last_log": self.last_log,
              "assistant_running": self.assistant(), "pressure_level": pressure_level(self.sysrun), "free_ram_gb": round(free_ram_gb(self.sysrun), 1),
              "free_disk_gb": round(free_disk_gb(self.out), 1), "server": self.server.cur, "server_rss_mb": round(self.server.rss_mb()), "pid": os.getpid()}
        st.update(kw)
        jdump(self.out / "status.json", st)

    def heartbeat(self):
        def loop():
            while not self.stop_flag:
                try:
                    self.peak_rss_mb = max(self.peak_rss_mb, self.server.rss_mb())
                    self.status()
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(30)
        threading.Thread(target=loop, daemon=True).start()

    # ------------------------------------------------------------ machine rules
    def assistant(self):
        return (OPS / "ASSISTANT_RUNNING").exists()

    def concurrency(self):
        return min(self.a.concurrency, 2) if self.assistant() else self.a.concurrency

    def paused_by_others(self):
        f = OPS / "PAUSE_OTHERS"
        if not f.exists():
            return False
        try:
            return not f.read_text().strip().startswith(OURS)
        except OSError:
            return True

    def preflight(self):
        ram, disk, swap = free_ram_gb(self.sysrun), free_disk_gb(self.out), swap_used_gb(self.sysrun)
        need = ASSIST_PEAK_GB if self.assistant() else MIN_FREE_RAM_GB
        info = {"free_ram_gb": round(ram, 1), "free_disk_gb": round(disk, 1), "swap_used_gb": round(swap, 1), "assistant_running": self.assistant(), "need_ram_gb": need,
                "pressure_level": pressure_level(self.sysrun)}
        self.log(f"preflight {info}")
        if ram < need:
            raise StopRun(f"refusing to start: free RAM {ram:.1f} GB < {need} GB")
        if disk < MIN_FREE_DISK_GB:
            raise StopRun(f"refusing to start: free disk {disk:.1f} GB < {MIN_FREE_DISK_GB} GB")
        if info["pressure_level"] >= PRESSURE_REFUSE:
            raise StopRun("refusing to start: memory pressure is warn/critical")
        return info

    def wait_pause_others(self):
        """PAUSE_OTHERS present and not ours: stop our server, wait until it is gone, then restart what was running."""
        if not (self.pause_enabled and self.paused_by_others()):
            return
        with self.lock:
            if not self.paused_by_others():
                return
            cur = self.server.cur
            self.log("PAUSE_OTHERS present: stopping our server and waiting")
            self.server.stop()
            while self.paused_by_others():
                self.status(waiting="PAUSE_OTHERS")
                time.sleep(self.a.poll_s)
            self.log("PAUSE_OTHERS gone: resuming")
            if cur:
                self.server.start(*cur)

    def backoff_memory(self, hard=False):
        """Wait (up to mem_wait_s) while pressure is warn/critical. hard: raise StopRun if still bad afterwards (between phases)."""
        t0 = time.time()
        while pressure_level(self.sysrun) >= PRESSURE_REFUSE:
            if time.time() - t0 > self.mem_wait_s:
                if hard:
                    raise StopRun("memory pressure stayed warn/critical; stopping cleanly (re-run to resume)")
                return
            self.status(waiting="memory pressure")
            time.sleep(min(self.a.poll_s, 15))

    def gate(self):
        """Before every request: honour PAUSE_OTHERS and back off on memory pressure."""
        if self.stop_flag:
            raise StopRun("stopped")
        self.wait_pause_others()
        self.backoff_memory(hard=False)

    def checkpoint(self, label):
        """Between phases."""
        if self.stop_flag:
            raise StopRun("stopped by signal")
        self.wait_pause_others()
        if free_disk_gb(self.out) < MIN_FREE_DISK_GB:
            raise StopRun(f"free disk below {MIN_FREE_DISK_GB} GB before {label}")
        self.backoff_memory(hard=True)
        need = ASSIST_PEAK_GB if self.assistant() else MIN_FREE_RAM_GB
        if free_ram_gb(self.sysrun) < min(need, 6.0) and not self.server.cur:
            raise StopRun(f"free RAM very low before {label}")

    def run_phase(self, name, fn):
        self.checkpoint(name)
        self.phase, self.phase_t0, self.peak_rss_mb = name, time.time(), 0.0
        self.log(f"=== phase {name} (assistant={self.assistant()}, concurrency={self.concurrency()})")
        self.status()
        res = fn() or {}
        rec = {"phase": name, "seconds": round(time.time() - self.phase_t0), "peak_server_rss_mb": round(self.peak_rss_mb), "assistant_running": self.assistant(), **res}
        jl_append(self.out / "phases.jsonl", rec)
        self.phases.append(rec)
        self.log(f"phase {name} done in {rec['seconds']}s peak server RSS {rec['peak_server_rss_mb']} MB")
        self.summary()

    # ------------------------------------------------------------ model
    def locate_model(self):
        a = self.a
        if a.model:
            return str(Path(os.path.expanduser(a.model)))
        md = OPS / "models"
        md.mkdir(parents=True, exist_ok=True)
        for d in sorted(md.glob("*")):
            if (d / "config.json").exists() and re.search(r"k2", d.name, re.I) and re.search(r"4bit|q4", d.name, re.I):
                self.log(f"using existing {d}")
                return str(d)
        try:
            from huggingface_hub import HfApi
            api = HfApi()
        except ImportError:
            api = None
        for repo in K2_Q4_CANDIDATES:
            size = self._repo_gb(api, repo)
            if size is None:
                continue
            self._need_disk(size * 1.2, f"download {repo}")
            dest = md / repo.split("/")[1]
            from huggingface_hub import snapshot_download
            snapshot_download(repo, local_dir=str(dest))
            return str(dest)
        size = self._repo_gb(api, K2_SRC) or 8.0
        self._need_disk(size + 4.0 + size * 0.3, "convert K2 to q4 (download + output)")
        dest = md / "K2-Horizon-3.7B-4bit"
        r = subprocess.run([self.py, "-m", "mlx_lm.convert", "--hf-path", K2_SRC, "-q", "--q-bits", "4", "--mlx-path", str(dest)])
        if r.returncode:
            raise StopRun("mlx_lm.convert failed (is K2 supported by this mlx-lm?)")
        return str(dest)

    def _repo_gb(self, api, repo):
        if api is None:
            return None
        try:
            info = api.model_info(repo, files_metadata=True)
            return sum((s.size or 0) for s in info.siblings) / 2 ** 30
        except Exception:  # noqa: BLE001
            return None

    def _need_disk(self, gb, what):
        free = free_disk_gb(self.out)
        if free - gb < MIN_FREE_DISK_GB:
            raise StopRun(f"refusing to {what}: needs ~{gb:.1f} GB, free {free:.1f} GB, floor {MIN_FREE_DISK_GB} GB")

    def load_tok(self, model):
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
        self.bos = tok.bos_token or ""
        ids = tok("a", add_special_tokens=True).input_ids
        self.strip_bos = bool(self.bos and tok.bos_token_id is not None and ids and ids[0] == tok.bos_token_id)
        return tok

    # ------------------------------------------------------------ generation phases
    def _make_backend(self, conc):
        # send_seed=False: mlx_lm.server serves any request carrying a seed one at a time (no batched decode); unseeded = ~4.5x throughput
        return OpenAIBackend(self.server.base_url, self.model, workers=conc, send_seed=False, strip_prefix=self.bos if getattr(self, "strip_bos", False) else "", gate=self.gate, log=self.log)

    def serve(self, adapter):
        conc = self.concurrency()
        self.server.ensure(self.model, adapter, conc)
        return conc

    def harness(self, conc):
        if self.a.harness == "opencode":  # PREREG-2 addendum 1: the OpenCode agent that OpenBot runs, K2 behind practice/k2_proxy (in-process)
            from .oc_harness import OpenCodeHarness
            if getattr(self, "_oc", None) is None or self._oc.concurrency != conc:
                self._oc = OpenCodeHarness(None, str(self.out / "proxy_logs"), upstream=self.server.base_url, concurrency=conc, timeout=self.a.oc_timeout,
                                           max_steps=self.a.oc_steps, web=self.a.web, log=self.log)
            return self._oc
        be = self.make_backend(conc)
        return Harness(None, self.tok, 0.7, MAX_NEW, MAX_CTX, conc, MAX_TURNS, log=self.log, backend=be, workers=4, progress_s=120)

    def run_tries(self, file, puzzles, tries, adapter, seed, label):
        """Resumable: runs only the (puzzle, try) pairs missing from `file`; each finished try is appended immediately."""
        have = {(r["id"], r["try"]) for r in jl(file)}
        conc = self.serve(adapter)
        H = self.harness(conc)
        errs = []
        for k in range(tries):
            todo = [p for p in puzzles if (p["id"], k) not in have]
            if not todo:
                continue

            def on_done(rec, k=k):
                rec["try"] = k
                if rec.get("end") == "error":  # not scored: redone below after a server restart
                    errs.append((rec["id"], k, rec.get("error", "")[:200]))
                    return
                if rec.get("harness") == "opencode":  # lesson segments as K2 saw them, then drop the 13 KB tools copy
                    from .oc_lessons import oc_segments
                    try:
                        rec["segs"] = oc_segments(rec, self.tok, self.a.chat_template, bos=self.bos, train_bare_answers=True)  # stored as served; lessons.target_of applies the bare-answer rule
                    except Exception as e:  # noqa: BLE001
                        rec["segs_error"] = repr(e)
                    rec.pop("proxy_tools", None)
                jl_append(file, rec)
            H.run(todo, 1, seed=seed * 10 + k, on_done=on_done, label=f"{label} try{k}")
        for rnd in range(3):  # Practice-2 M3 stage 0: a Metal OOM killed the generation thread and every later try errored and was scored wrong
            have = {(r["id"], r["try"]) for r in jl(file)}
            redo = [(p, k) for k in range(tries) for p in puzzles if (p["id"], k) not in have]
            if not redo or not errs:
                break
            self.log(f"{label}: {len(errs)} errored tries (e.g. {errs[-1][2]!r}); restarting the server and redoing {len(redo)} (round {rnd + 1})")
            errs.clear()
            self.server.stop()
            conc = self.serve(adapter)
            H = self.harness(conc)
            for k in sorted({k for _, k in redo}):
                def on_done2(rec, k=k):
                    rec["try"] = k
                    if rec.get("end") == "error":
                        errs.append((rec["id"], k, rec.get("error", "")[:200]))
                        if rnd < 2:
                            return
                    on_done(rec, k) if rec.get("end") != "error" else jl_append(file, rec)
                H.run([p for p, kk in redo if kk == k], 1, seed=seed * 10 + k + 1000 * (rnd + 1), on_done=on_done2, label=f"{label} redo{rnd + 1} try{k}")
        recs = jl(file)
        self.peak_rss_mb = max(self.peak_rss_mb, self.server.rss_mb())
        return {"n": len(recs), **{k: v for k, v in summarize(recs).items() if k in ("acc", "tool_calls_per_try", "answered", "gen_tokens_per_try")},
                "web_calls": sum(len(r.get("web", [])) for r in recs), "web_blocked": sum(1 for r in recs for e in r.get("web", []) if e.get("status") == "blocked"),
                "tok_per_s": round(H.stats["gen_tokens"] / max(1e-9, H.stats["gen_s"]), 1)}

    def eval_phase(self, tag, arm_dir, adapter):
        d = self.out / arm_dir
        res = self.run_tries(d / f"eval_{tag}_test.jsonl", self.test, self.a.test_tries, adapter, 7, f"eval {tag} test")
        self.run_tries(d / f"eval_{tag}_sib.jsonl", self.sib, 1, adapter, 8, f"eval {tag} sib")
        return res

    def day_phase(self, arm, n, adapter):
        return self.run_tries(self.out / arm / f"day{n}.jsonl", self.pool, self.a.tries, adapter, 100 + n, f"day {arm}{n}")

    # ------------------------------------------------------------ night
    def _train_subprocess(self, spec):
        sf = Path(spec["out"]).parent / (Path(spec["out"]).name + "_spec.json")
        jdump(sf, spec)
        r = subprocess.run([self.py, "-m", "practice.mlx_train", "--spec", str(sf)], cwd=str(HERE.parent))
        if r.returncode:
            raise StopRun("mlx_train failed")
        return json.loads((Path(spec["out"]) / "train_stats.json").read_text())

    def night_phase(self, arm, n):
        d = self.out / arm
        adir = d / "adapters" / f"night{n}"
        store = []
        for k in range(1, n + 1):
            store += jl(d / f"day{k}.jsonl")
        night = self.a.night
        L.TRAIN_BARE_ANSWERS = getattr(self.a, "train_bare_answers", False)
        if getattr(self.a, "harness", "native") == "opencode":
            night = dict(night, train_max_tokens=max(night["train_max_tokens"], self.a.oc_train_tokens))  # OpenCode prompts alone are ~4k tokens
        dd = getattr(self, "rg_mode", False)  # Practice-2: one win per solved puzzle; C gets exactly P's item counts
        ref = d.parent / "P" / f"night{n}_lessons.json"
        if dd and arm == "C" and ref.exists():
            r = json.loads(ref.read_text())
            night = dict(night, n_sft=max(1, r.get("sft_unique", 0)), n_pairs=r.get("pairs", 0))
        items, st = L.build_lessons(arm, store, self.tok, self.a.seed, n, night["n_sft"], night["epochs"], night["n_pairs"], night["train_max_tokens"], dedup=dd)
        st["tool_note"] = "transcripts over train_max_tokens are not lessons"
        self.server.stop()  # one model in memory at a time
        if not items:
            adir.mkdir(parents=True, exist_ok=True)
            (adir / "EMPTY").write_text("no lessons: the base model is used")
            return {"lessons": st, "empty": True}
        from .mlx_train import lessons_to_jsonl
        lj = d / f"lessons_night{n}.jsonl"
        lessons_to_jsonl(items, lj, self.bos)
        spec = {"model": self.model, "out": str(adir), "lessons_jsonl": str(lj), "steps": max(1, min(night["steps"], max(st.get("sft_examples", 0), st.get("pairs", 0)))), "lr": night["lr"], "rank": night["rank"], "beta": night["beta"],
                "dpo_w": night["dpo_w"], "seed": self.a.seed * 100 + n, "max_tokens": night["train_max_tokens"]}
        if self.assistant():
            spec["mem_limit_gb"] = 7.0
        tr = self.train_fn(spec)
        jdump(d / f"night{n}_lessons.json", st)
        return {"lessons": st, "train": {k: tr.get(k) for k in ("seconds", "peak_gb", "items")}, "loss_first_last": [tr["loss_by_step"][0], tr["loss_by_step"][-1]] if tr.get("loss_by_step") else None}

    def adapter_of(self, arm, n):
        if n == 0:
            return None
        ad = self.out / arm / "adapters" / f"night{n}"
        return None if (ad / "EMPTY").exists() else str(ad)

    def night_done(self, arm, n):
        ad = self.out / arm / "adapters" / f"night{n}"
        return (ad / "train_stats.json").exists() or (ad / "EMPTY").exists()

    # ------------------------------------------------------------ bench
    def bench(self):
        f = self.out / "bench.json"
        if f.exists():
            return
        self.serve(None)
        be0 = self.make_backend(1)
        prompt = render(start_messages(self.test[0]), True, self.tok.bos_token or "")
        secs = max(20, self.a.bench_s // 3)
        res = {}
        for c in [x for x in (1, 2, 4) if x <= max(1, self.concurrency())]:
            be = self.make_backend(c)
            end = time.time() + secs
            tok_n, lock = [0], threading.Lock()

            def worker(i):
                while time.time() < end:
                    be.gate and be.gate()
                    before = be.completion_tokens
                    be._one(prompt, 256, 0.7, i)
                    with lock:
                        tok_n[0] = be.completion_tokens
            ts = [threading.Thread(target=worker, args=(i,)) for i in range(c)]
            t = time.time()
            [x.start() for x in ts]
            [x.join() for x in ts]
            res[str(c)] = {"aggregate_tok_s": round(be.completion_tokens / (time.time() - t), 1), "per_stream_tok_s": round(be.completion_tokens / (time.time() - t) / c, 1)}
            self.peak_rss_mb = max(self.peak_rss_mb, self.server.rss_mb())
            self.log(f"bench c={c}: {res[str(c)]}")
        res["peak_server_rss_mb"] = round(self.peak_rss_mb)
        jdump(f, res)
        return res

    # ------------------------------------------------------------ summary
    def summary(self):
        tags = {}
        for tag, arm_dir in [("A0", "A0")] + [(f"{arm}{n}", arm) for arm in ("P", "C") for n in (1, 2, 3)]:
            recs = jl(self.out / arm_dir / f"eval_{tag}_test.jsonl")
            if recs:
                sib = jl(self.out / arm_dir / f"eval_{tag}_sib.jsonl")
                tags[tag] = {"test100_per_puzzle": puzzle_scores(recs), "test100_mean": round(sum(puzzle_scores(recs).values()) / max(1, len(puzzle_scores(recs))), 4),
                             "test_summary": summarize(recs), "sibling_acc": summarize(sib)["acc"] if sib else None}
        cmp = {}
        pairs = [(f"P{n}", "A0") for n in (1, 2, 3)] + [(f"P{n}", f"C{n}") for n in (1, 2, 3)] + [(f"C{n}", "A0") for n in (1, 2, 3)]
        for x, y in pairs:
            if x in tags and y in tags:
                cmp[f"{x}_vs_{y}"] = {"diff_points": round(100 * (tags[x]["test100_mean"] - tags[y]["test100_mean"]), 1),
                                      "p_signflip": round(signflip_p(tags[x]["test100_per_puzzle"], tags[y]["test100_per_puzzle"]), 4)}
        jdump(self.out / "summary.json", {"evals": tags, "comparisons": cmp, "phases": self.phases[-60:], "config": self.config(), "updated": time.strftime("%Y-%m-%dT%H:%M:%S")})

    def config(self):
        a = self.a
        return {"model": getattr(self, "model", None), "quant": "q4 for serving and training (QLoRA)", "night": a.night, "dpo": a.night["dpo"], "tries": a.tries, "test_tries": a.test_tries,
                "sib_tries": 1, "practice_n": a.practice_n, "pool_size": len(getattr(self, "pool", [])), "nights": a.nights, "eval_nights": sorted(a.eval_nights), "web": a.web, "web_eval": a.web_eval,
                "concurrency": a.concurrency, "caps": {"max_new": MAX_NEW, "max_turns": MAX_TURNS, "max_ctx": MAX_CTX}, "stop": STOPS_CFG, "share_day1": a.share_day1,
                "no_dpo_note": None, "arc_easy_200": "not run on the Mac"}

    # ------------------------------------------------------------ main
    def run(self):
        a = self.a
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "stop_flag", True))
        try:
            self.heartbeat()
            self.preflight()
            self.phase = "model"
            self.model = self.locate_model()
            self.tok = self.load_tok(self.model)
            if a.web and not (PDATA / "pe_pool.jsonl").exists():
                pe_pool.build(100, PDATA / "pe_pool.jsonl", log=self.log, soft=True)  # no PE if it fails
            self.pool, full = load_pool(a.practice_n)
            self.test, self.sib, test_rows = load_eval_sets()
            self.sib = self.sib[:a.sib_n] if a.sib_n >= 0 else self.sib
            WEB.configure(a.web, test_rows, full)
            self.log(f"pool {len(self.pool)} (pe {sum(1 for p in self.pool if p['id'].startswith('pe-'))}) test {len(self.test)} sibling {len(self.sib)} web={a.web}")
            jdump(self.out / "config.json", self.config())
            if not a.skip_bench:
                self.run_phase("bench", self.bench)
            self.run_phase("eval_A0", lambda: self.with_web(a.web_eval, lambda: self.eval_phase("A0", "A0", None))) if not self.done_eval("A0", "A0") else None
            for arm in a.arms:
                for n in range(1, a.nights + 1):
                    prev = self.adapter_of(arm, n - 1)
                    if not self.day_done(arm, n):
                        if a.share_day1 and n == 1 and arm != a.arms[0] and (self.out / a.arms[0] / "day1.jsonl").exists():
                            shutil.copy(self.out / a.arms[0] / "day1.jsonl", self.out / arm / "day1.jsonl")
                        else:
                            self.run_phase(f"day_{arm}{n}", lambda arm=arm, n=n, prev=prev: self.with_web(a.web, lambda: self.day_phase(arm, n, prev)))
                    if not self.night_done(arm, n):
                        self.run_phase(f"night_{arm}{n}", lambda arm=arm, n=n: self.night_phase(arm, n))
                    if n in a.eval_nights and not self.done_eval(f"{arm}{n}", arm):
                        self.run_phase(f"eval_{arm}{n}", lambda arm=arm, n=n: self.with_web(a.web_eval, lambda: self.eval_phase(f"{arm}{n}", arm, self.adapter_of(arm, n))))
            self.phase = "finished"
            self.log("all phases finished")
            self.summary()
            return 0
        except StopRun as e:
            self.phase = "stopped"
            self.log(f"STOPPED: {e}")
            self.status(stopped=str(e))
            return 3
        finally:
            self.stop_flag = True
            self.server.stop()

    def with_web(self, on, fn):
        old = WEB.enabled
        WEB.enabled = bool(on) and self.a.web
        try:
            return fn()
        finally:
            WEB.enabled = old

    def day_done(self, arm, n):
        have = {(r["id"], r["try"]) for r in jl(self.out / arm / f"day{n}.jsonl")}
        return all((p["id"], k) in have for p in self.pool for k in range(self.a.tries))

    def done_eval(self, tag, arm_dir):
        t = {(r["id"], r["try"]) for r in jl(self.out / arm_dir / f"eval_{tag}_test.jsonl")}
        s = {r["id"] for r in jl(self.out / arm_dir / f"eval_{tag}_sib.jsonl")}
        return all((p["id"], k) in t for p in self.test for k in range(self.a.test_tries)) and all(p["id"] in s for p in self.sib)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="~/learner-ops/practice1m")
    ap.add_argument("--model", default=None, help="path of an MLX q4 K2 (default: find/download/convert under ~/learner-ops/models)")
    ap.add_argument("--python", default=None, help="python with mlx-lm (default: this interpreter)")
    ap.add_argument("--port", type=int, default=8089)
    ap.add_argument("--harness", choices=["native", "opencode"], default="native", help="opencode = the agent OpenBot runs (PREREG-2 addendum 1)")
    ap.add_argument("--chat-template", default=None, help="opencode: K2 template file for mlx_lm.server and lessons (default: oc_lessons search path)")
    ap.add_argument("--oc-timeout", type=float, default=600, help="opencode: seconds per try")
    ap.add_argument("--train-bare-answers", action="store_true", help="opencode: also train the bare final <answer> turns (off since PREREG-2 addendum 2)")
    ap.add_argument("--oc-train-tokens", type=int, default=6144, help="opencode: lesson length cap for the nights")
    ap.add_argument("--oc-steps", type=int, default=8, help="opencode: model calls per try")
    ap.add_argument("--practice-n", type=int, default=120)
    ap.add_argument("--tries", type=int, default=None, help="tries per practice puzzle (default 2; 4 in Practice-2 mode)")
    ap.add_argument("--rg-skills", help="Practice-2: comma-separated Reasoning Gym skills, or auto (read <out>/stage0.json)")
    ap.add_argument("--stage0", action="store_true", help="Practice-2 stage 0: base model, --stage0-n puzzles x 1 try per candidate -> <out>/stage0.json")
    ap.add_argument("--stage0-n", type=int, default=40)
    ap.add_argument("--rg-day-n", type=int, default=1000, help="fresh puzzles per day (seed 1000+day)")
    ap.add_argument("--rg-test-n", type=int, default=300)
    ap.add_argument("--test-tries", type=int, default=2)
    ap.add_argument("--nights", type=int, default=3)
    ap.add_argument("--eval-nights", default="1,3")
    ap.add_argument("--arms", default="P,C")
    ap.add_argument("--sib-n", type=int, default=-1, help="use only the first N sibling puzzles (0 = skip the sibling set, -1 = all)")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-web", dest="web", action="store_false", help="turn the live web tools off")
    ap.add_argument("--no-web-eval", dest="web_eval", action="store_false", help="no web in the test evals (default: same tools as practice)")
    ap.add_argument("--share-day1", action="store_true", help="C reuses P's day-1 tries (both are the base model); saves one day")
    ap.add_argument("--skip-bench", action="store_true")
    ap.add_argument("--bench-s", type=int, default=300)
    ap.add_argument("--mem-wait-s", type=int, default=600)
    ap.add_argument("--poll-s", type=int, default=30)
    for k, v in MAC_NIGHT.items():
        if k not in ("dpo",):
            ap.add_argument("--" + k.replace("_", "-"), dest="night_" + k, type=type(v), default=v)
    a = ap.parse_args(argv)
    a.rg = bool(a.stage0 or a.rg_skills)
    a.tries = a.tries or (4 if a.rg else 2)
    a.arms = [x for x in a.arms.split(",") if x]
    a.eval_nights = {int(x) for x in a.eval_nights.split(",") if x}
    a.night = {k: getattr(a, "night_" + k) if k != "dpo" else True for k in MAC_NIGHT}
    return a


class MacRG(Mac):
    """Practice-2 on the Mac (PREREG-2, same layout idea as rg_run): <out>/stage0.json, <out>/<skill>/{rgdata,A0,P,C}/. Per skill: A0 eval, then for P and C
    nights x (day on fresh puzzles -> night); P evals after --eval-nights, C only after the last night; sealed test100 (first --sib-n puzzles; 0 = skip) at A0 (first
    skill) and after the last night of P. Resumable like Mac."""
    rg_mode = True

    def setup(self):
        a = self.a
        self.preflight()
        self.phase = "model"
        self.model = self.locate_model()
        self.tok = self.load_tok(self.model)
        _, full = load_pool(a.practice_n)
        self.sib, _, test_rows = load_eval_sets()
        self.sib = self.sib[:a.sib_n] if a.sib_n >= 0 else self.sib
        WEB.configure(a.web, test_rows, full)

    def rg_eval(self, tag, arm_dir, adapter, sib):
        d = self.out / arm_dir
        res = self.run_tries(d / f"eval_{tag}_test.jsonl", self.test, self.a.test_tries, adapter, 7, f"eval {tag} test")
        if sib and self.sib:
            self.run_tries(d / f"eval_{tag}_sib.jsonl", self.sib, self.a.test_tries, adapter, 8, f"eval {tag} sib")
        return res

    def rg_eval_done(self, tag, arm_dir, sib):
        d = self.out / arm_dir
        t = {(r["id"], r["try"]) for r in jl(d / f"eval_{tag}_test.jsonl")}
        s = {(r["id"], r["try"]) for r in jl(d / f"eval_{tag}_sib.jsonl")}
        return (all((p["id"], k) in t for p in self.test for k in range(self.a.test_tries))
                and (not (sib and self.sib) or all((p["id"], k) in s for p in self.sib for k in range(self.a.test_tries))))

    def stage0(self):
        from . import rg_pool as R
        a, root = self.a, Path(os.path.expanduser(self.a.out))
        if (root / "stage0.json").exists():
            return json.loads((root / "stage0.json").read_text())
        scores = {}
        only = a.rg_skills.split(",") if a.rg_skills and a.rg_skills != "auto" else None  # stage-0 redo of a few skills (M1, 2026-10-27)
        for skill in only or R.CANDIDATES:
            f = root / "stage0" / skill / "eval_S0_test.jsonl"
            ps = R.make_puzzles(skill, a.stage0_n, R.STAGE0_SEED)
            self.run_phase(f"stage0_{skill}", lambda ps=ps, f=f, skill=skill: self.run_tries(f, ps, 1, None, 7, f"stage0 {skill}"))
            recs = jl(f)
            scores[skill] = round(sum(r["correct"] for r in recs) / max(1, len(recs)), 4)
            self.log(f"stage0 {skill}: {scores[skill]}")
        picked, note = R.pick_skills(scores)
        out = {"n_puzzles": a.stage0_n, "tries": 1, "seed": R.STAGE0_SEED, "scores": scores, "picked": picked, "note": note}
        jdump(root / "stage0.json", out)
        self.log(f"stage0 picked {picked} {note}")
        return out

    def skill(self, root, skill, k):
        from .rg_run import write_sets
        a = self.a
        self.out = root / skill
        write_sets(self.out, skill, a, a.nights)
        self.test = jl(self.out / "rgdata" / "test.jsonl")
        last = a.nights
        if not self.rg_eval_done("A0", "A0", k == 0):
            self.run_phase("eval_A0", lambda: self.with_web(a.web_eval, lambda: self.rg_eval("A0", "A0", None, k == 0)))
        for arm in a.arms:
            for n in range(1, a.nights + 1):
                self.pool = jl(self.out / "rgdata" / f"day{n}.jsonl")
                prev = self.adapter_of(arm, n - 1)
                if not self.day_done(arm, n):
                    self.run_phase(f"day_{arm}{n}", lambda arm=arm, n=n, prev=prev: self.with_web(a.web, lambda: self.day_phase(arm, n, prev)))
                if not self.night_done(arm, n):
                    self.run_phase(f"night_{arm}{n}", lambda arm=arm, n=n: self.night_phase(arm, n))
                if (arm == "P" and (n in a.eval_nights or n == last)) or (arm == "C" and n == last):
                    sib = arm == "P" and n == last
                    if not self.rg_eval_done(f"{arm}{n}", arm, sib):
                        self.run_phase(f"eval_{arm}{n}", lambda arm=arm, n=n, sib=sib: self.with_web(a.web_eval, lambda: self.rg_eval(f"{arm}{n}", arm, self.adapter_of(arm, n), sib)))

    def run(self):
        from . import rg_pool as R
        a = self.a
        root = Path(os.path.expanduser(a.out))
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "stop_flag", True))
        try:
            self.heartbeat()
            self.setup()
            jdump(root / "rg_config.json", {k: v for k, v in vars(a).items() if isinstance(v, (int, float, str, bool, type(None), list, dict))})
            st = self.stage0() if a.stage0 else None
            if a.stage0 and a.rg_skills and a.rg_skills != "auto":
                self.log("stage0 only: --rg-skills named the skills to (re)score, no practice run")
                return
            if a.rg_skills:
                if a.rg_skills == "auto":
                    st = st or (json.loads((root / "stage0.json").read_text()) if (root / "stage0.json").exists() else None)
                    if not st:
                        raise StopRun("--rg-skills auto needs <out>/stage0.json (run --stage0 first)")
                    skills = st["picked"]
                else:
                    skills = a.rg_skills.split(",")
                bad = [s for s in skills if s not in R.CANDIDATES]
                if bad:
                    raise StopRun(f"unknown skill {bad}; candidates: {R.CANDIDATES}")
                for k, s in enumerate(skills):
                    self.skill(root, s, k)
            self.phase = "finished"
            self.log("all phases finished")
            return 0
        except StopRun as e:
            self.phase = "stopped"
            self.log(f"STOPPED: {e}")
            self.status(stopped=str(e))
            return 3
        finally:
            self.stop_flag = True
            self.server.stop()


def main(argv=None):
    a = parse_args(argv)
    return (MacRG(a) if a.rg else Mac(a)).run()


if __name__ == "__main__":
    sys.exit(main())
