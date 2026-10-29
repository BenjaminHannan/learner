"""Sleep Mode worker: `python -m sleepmlx.worker`  (the CommandWorker entry).

Contract (sleepmode/workers.py CommandWorker): reads env SLEEPMODE_BUDGET_S (seconds for this chunk), SLEEPMODE_OUT (JSON path to write),
SLEEPMODE_PRACTICE (os.pathsep-joined practice files; accepted, not used) and SLEEPMODE_WORKDIR. Writes
{"quiz": float|null, "steps": int, "interrupted": bool, ...info}. quiz = recall % on the night's held-out cards, only on the chunk where the night
finishes (null otherwise). `general` (the 40-question score) rides along for the scheduler's forgetting guard.
Stops cleanly (checkpoint, then exit 0) on SIGTERM, when ~/learner-ops/ASSISTANT_RUNNING or PAUSE_OTHERS appears, on memory pressure > 1,
or when the chunk budget is nearly spent. The next chunk resumes the night.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Callable, Optional

from . import diary as diary_mod
from . import lessons as L_mod
from .backend import Clock, Guards, available_ram_bytes
from .paths import Paths, appdata_root, is_windows, ops_dir, read_json, write_json
from .profile import Renderer, load_profile
from .recipe import Config, Sleeper, next_day


def cfg_from_env(env=os.environ, prof=None) -> Config:
    c = Config()
    for k, v in ((prof.recipe if prof is not None else {}) or {}).items():   # profile overrides first, then env
        if hasattr(c, k):
            setattr(c, k, v)
    c.who = env.get("SLEEPMLX_WHO", c.who)
    rt = (prof.runtime if prof is not None else {}) or {}
    c.llama_cpp_dir = env.get("SLEEPMLX_LLAMA_CPP_DIR") or rt.get("llama_cpp_dir") or c.llama_cpp_dir
    c.llama_server = env.get("SLEEPMLX_LLAMA_SERVER") or rt.get("llama_server") or c.llama_server
    c.base_gguf = env.get("SLEEPMLX_BASE_GGUF") or rt.get("base_gguf") or c.base_gguf
    if prof is not None and prof.model_dir:
        c.gguf_base_dir = prof.expanded_model_dir
    for name, cast in (("SLEEPMLX_NIGHT_BUDGET_S", float), ("SLEEPMLX_SCALE", float), ("SLEEPMLX_MIN_CARDS", int), ("SLEEPMLX_MIN_ITEM_DAYS", int),
                       ("SLEEPMLX_SEED", int), ("SLEEPMLX_HARM_MAX", float), ("SLEEPMLX_CARD_SHAPE", str),
                       ("SLEEPMLX_REPLAY_MODE", str), ("SLEEPMLX_REPLAY_MAX_TOKENS", int)):
        if env.get(name):
            setattr(c, {"SLEEPMLX_NIGHT_BUDGET_S": "night_budget_s", "SLEEPMLX_SCALE": "scale", "SLEEPMLX_MIN_CARDS": "min_cards",
                        "SLEEPMLX_MIN_ITEM_DAYS": "min_item_days", "SLEEPMLX_SEED": "seed", "SLEEPMLX_HARM_MAX": "harm_max", "SLEEPMLX_CARD_SHAPE": "card_shape",
                        "SLEEPMLX_REPLAY_MODE": "replay_mode", "SLEEPMLX_REPLAY_MAX_TOKENS": "replay_max_tokens"}[name], cast(env[name]))
    return c


def choose_backend(prof) -> str:
    if prof.backend in ("mlx", "torch"):
        return prof.backend
    try:
        import mlx.core  # noqa: F401
        return "mlx"
    except ImportError:
        return "torch"


def make_backend(prof, env=os.environ):
    """Load the model for `prof` and wrap it in the MLX or the torch backend. -> (backend, tokenizer)."""
    rt = prof.runtime or {}
    kind = choose_backend(prof)
    tok_budget = int(env.get("SLEEPMLX_TOK_BUDGET", rt.get("tok_budget", 256)))
    gc = env.get("SLEEPMLX_GC", "1" if rt.get("grad_ckpt", True) else "0") != "0"
    gen_batch = int(env.get("SLEEPMLX_GEN_BATCH", rt.get("gen_batch", 8)))
    if kind == "mlx":
        from . import model as M
        model, tok = M.load(prof.expanded_model_dir, prof.loader, prof.loader_path, prof.trust_remote_code)
        be = M.MLXBackend(model, tok, prof, prof.expanded_model_dir, tok_budget=tok_budget, grad_ckpt=gc, gen_batch=gen_batch,
                          mem_limit=float(env.get("SLEEPMLX_MEM_LIMIT", rt.get("mem_limit", 5e9))),
                          cache_limit=float(env.get("SLEEPMLX_CACHE_LIMIT", rt.get("cache_limit", 0.5e9))))
        return be, tok
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    from . import torch_backend as T
    src = torch_source(prof)
    model, tok = T.load(src, prof.trust_remote_code, mps_gb=T.mps_cap_gb(rt.get("mps_mem_gb")))
    return T.TorchBackend(model, tok, prof, src, tok_budget=tok_budget, grad_ckpt=gc, gen_batch=gen_batch), tok


class ModelMissing(RuntimeError):
    pass


def download_command(prof) -> str:
    return "huggingface-cli download %s --local-dir %s" % (prof.hf_id, prof.expanded_model_dir)


def torch_source(prof) -> str:
    """The local HF dir if the profile names one, else the HF id (downloaded into the HF cache). A configured dir that is missing is an error
    that prints the exact download command."""
    if prof.model_dir:
        if os.path.isdir(prof.expanded_model_dir):
            return prof.expanded_model_dir
        if prof.hf_id:
            raise ModelMissing("model dir %s is missing. Download it with:\n  %s" % (prof.expanded_model_dir, download_command(prof)))
        raise ModelMissing("model dir %s is missing" % prof.expanded_model_dir)
    return prof.hf_id or prof.expanded_model_dir




def run_chunk(env=None, backend_factory: Optional[Callable] = None, dry_run: bool = False, log: Callable[[str], None] = print,
              guards: Optional[Guards] = None, only_date: Optional[str] = None, profile: Optional[str] = None,
              memory_available: Optional[Callable[[], Optional[float]]] = None) -> dict:
    """One chunk. Returns the dict that goes to SLEEPMODE_OUT. backend_factory(prof) -> (backend, tokenizer) (tests pass a fake)."""
    env = dict(os.environ if env is None else env)
    t0 = time.time()
    paths = _paths_from(env) if "SLEEPMLX_HOME" in env else Paths.from_env()
    paths.mk()
    budget = float(env.get("SLEEPMODE_BUDGET_S", "1200"))
    prof = load_profile(profile, env)
    cfg = cfg_from_env(env, prof)
    guards = guards or Guards(paths)
    guards.min_free_gb = float(prof.runtime.get("min_free_ram_gb", 1.0))
    out = {"quiz": None, "steps": 0, "interrupted": False, "profile": prof.name}
    r = guards.reason()
    if not r and getattr(guards, "_hot", 0):   # one high memory reading: look again before loading the model, not after
        time.sleep(min(guards.poll_s, 10.0))
        guards._last = -1e18
        r = guards.reason()
    if r:
        out.update(interrupted=True, stop_reason=r, message="not started: " + r)
        return out
    # A completed night can still owe a served check. Recover it before the
    # no-new-day shortcut and before loading a trainer alongside llama-server.
    from . import served as served_mod
    if not dry_run and served_mod.pending_check(paths):
        result = served_mod.finish_pending(paths, prof, cfg, log=log)
        out.update(status="served_check", served=result, elapsed_s=time.time() - t0,
                   message="served check pending" if result.get("pending") else "finished pending served check")
        return out
    # A durable decision that cannot authorize publication needs an explicit
    # re-gate, not another multi-GB model load. Use the exact finalization guard
    # before reading the diary or allocating a backend; do not repair the night.
    if not dry_run and paths.night_json.exists():
        from .checkpoint import Checkpoints
        checkpoints = Checkpoints(paths)
        night, checkpoint_items = checkpoints.load()
        if night and not night.get("dry_run") and night.get("phase") in ("finalize", "done"):
            probe = Sleeper(None, None, prof, cfg, paths, None, log)
            probe.N, probe._checkpoints = night, checkpoints
            probe.load_items(checkpoint_items)
            reason = probe._finalization_block_reason()
            if reason:
                probe._block_finalization(out, reason)
                out.update(resumed=True, phase=night["phase"], date=night.get("date"),
                           day=night.get("day"), elapsed_s=time.time() - t0)
                return out
    week = diary_mod.build_week(paths.diary_dir, cfg.who, ignore_file=diary_mod.ensure_ignore(paths.ignore),
                                feedback=L_mod.read_feedback(paths.userdata_dir))
    week["helper_state"] = L_mod.read_helpers(paths.userdata_dir)
    week["idea_verdicts"] = L_mod.read_idea_verdicts(paths.userdata_dir)
    state = read_json(paths.state, {}) or {}
    resuming = paths.night_json.exists()
    if not resuming and not next_day(week, state) and not only_date:
        out.update(status="no_new_day", message="no new diary day to sleep on", days_in_diary=len(week["dates"]), slept=len(state.get("slept_days", [])))
        return out
    # Reserve enough available RAM for the CPU base and its training overhead
    # before loading; the smaller runtime guard applies once weights are resident.
    required = float(prof.runtime.get("preload_free_ram_gb", 0))
    if required and (backend_factory is None and not env.get("SLEEPMLX_BACKEND") or memory_available is not None):
        available = (memory_available or available_ram_bytes)()
        if available is None:
            out.update(error="Cannot check available memory; install or repair psutil before sleeping.")
            return out
        if available < required * 1e9:
            out.update(interrupted=True, stop_reason="memory_pressure", message="not started: sleep needs about %.1f GB of available memory before loading" % required)
            return out
    if backend_factory is None and env.get("SLEEPMLX_BACKEND"):   # 'module:function' returning (backend, tokenizer); tests and other runtimes
        import importlib
        mod, _, fn = env["SLEEPMLX_BACKEND"].partition(":")
        backend_factory = getattr(importlib.import_module(mod), fn)
    be, tok = (backend_factory or make_backend)(prof)
    sl = None
    try:
        clock = Clock(budget, guards)
        sl = Sleeper(be, Renderer(prof, tok), prof, cfg, paths, clock, log)
        res = sl.run(week, dry_run=dry_run, only_date=only_date)
    finally:
        be.close()
    # the served check starts a llama-server: unload the trainer's model first (an 8 GB Mac cannot hold both)
    if getattr(sl, "served_pending", None):
        sl.be = None
        del be
        import gc
        gc.collect()
        try:
            import torch
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
        except Exception:
            pass
        sl.finish_served(res)
    out.update({k: v for k, v in res.items() if k not in ("steps",)})
    out["steps"] = int(res.get("steps") or 0)
    out["quiz"] = res.get("quiz")
    out["interrupted"] = bool(res.get("interrupted"))
    out["elapsed_s"] = time.time() - t0
    return out


def _paths_from(env) -> Paths:
    home = Path(os.path.expanduser(env["SLEEPMLX_HOME"]))
    # ops and the diary default as in Paths.from_env, not home.parent: a SLEEPMLX_HOME outside learner-ops (a test copy) lost the diary
    ops = Path(os.path.expanduser(env["LEARNER_OPS"])) if env.get("LEARNER_OPS") else ops_dir()
    diary_d = appdata_root() / "diary" if is_windows() else ops / "diary" / "raw"
    diary = Path(os.path.expanduser(env.get("SLEEPMLX_DIARY_DIR", str(diary_d))))
    ud = env.get("SLEEPMLX_USERDATA")
    return Paths(home, diary, ops, Path(os.path.expanduser(ud)) if ud else None)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sleepmlx.worker")
    ap.add_argument("--dry-run", action="store_true", help="tag and write cards only; no training, adapter untouched")
    ap.add_argument("--profile", default=None, help="lfm3 (default: lfm3_mps on macOS, lfm3_cuda / lfm3_cpu elsewhere) | k2 | a profile name or json path")
    ap.add_argument("--date", default=None, help="sleep this diary date (YYYY-MM-DD) instead of the oldest unslept one")
    ap.add_argument("--budget-s", type=float, default=None, help="chunk budget (default: env SLEEPMODE_BUDGET_S)")
    ap.add_argument("--out", default=None, help="output json (default: env SLEEPMODE_OUT)")
    a = ap.parse_args(argv)
    env = dict(os.environ)
    if a.budget_s:
        env["SLEEPMODE_BUDGET_S"] = str(a.budget_s)
    out_path = Path(a.out or env.get("SLEEPMODE_OUT", "sleepmlx_chunk_out.json"))
    paths = Paths.from_env()
    paths.mk()
    guards = Guards(paths)

    def on_term(signum, frame):
        guards.signal("sigterm")

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)

    def log(msg):
        line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
        print(line, flush=True)
        try:
            with open(str(paths.log), "a") as f:
                f.write(line + "\n")
        except OSError:
            pass

    rc = 0
    try:
        out = run_chunk(env, dry_run=a.dry_run, log=log, guards=guards, only_date=a.date, profile=a.profile)
    except Exception as e:  # never leave SLEEPMODE_OUT missing
        if isinstance(e, ModelMissing):
            print(str(e), file=sys.stderr, flush=True)
        else:
            traceback.print_exc()
        out = {"quiz": None, "steps": 0, "interrupted": False, "error": "%s: %s" % (type(e).__name__, e)}
        rc = 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out))
    log("chunk done: %s" % {k: v for k, v in out.items() if k in ("quiz", "steps", "status", "phase", "message", "stop_reason", "error")})
    return rc


if __name__ == "__main__":
    sys.exit(main())
