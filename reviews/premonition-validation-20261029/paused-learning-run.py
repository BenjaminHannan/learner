"""Research-only coordinated pause, bounded diagnostic, independent restoration.

No production files are edited. The only runtime mutations are an exclusively
owned PAUSE_OTHERS marker, the approved public process pause, and standard serve
restoration. Run only after explicit resource coordination with root.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import uuid

import psutil

ROOT = Path(__file__).resolve().parent
PYTHON = "/Users/ben-hannan/learner-ops/speedbench/venv312/bin/python"
OPS = Path("/Users/ben-hannan/learner-ops")
SERVICE = OPS / "assistant"
RUN = SERVICE / "run"
MARKER = OPS / "PAUSE_OTHERS"
MODEL = str(OPS / "lfm3/gguf/LFM3-1.7B-QAD-Q4_0.gguf")
EXPECTED_CACHE_SHA = "c57a18b6e9418d0d05dfb6fcf6daf22c54343be6d4ec3df0b6e4285c445d7fbb"


def durable(path, value, exclusive=False):
    path = Path(path)
    if exclusive and path.exists():
        raise FileExistsError(path)
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    with tmp.open("x") as stream:
        json.dump(value, stream, indent=2); stream.write("\n")
        stream.flush(); os.fsync(stream.fileno())
    if exclusive:
        # A hard link publishes exclusively without replacing an old artifact.
        os.link(tmp, path); tmp.unlink()
    else:
        os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def request(endpoint):
    with urllib.request.urlopen("http://127.0.0.1:18080/" + endpoint, timeout=2) as response:
        return json.load(response)


def health():
    try: return request("health").get("status") == "ok"
    except Exception: return False


def listener_present():
    try:
        with socket.create_connection(("127.0.0.1", 18080), timeout=.5): return True
    except OSError: return False


def identity(pid):
    p = psutil.Process(pid)
    return {"pid": pid, "created": p.create_time(), "argv": p.cmdline(), "cwd": p.cwd()}


def matching(item):
    try:
        p = psutil.Process(item["pid"])
        return p if p.create_time() == item["created"] and p.cmdline() == item["argv"] and p.status() != psutil.STATUS_ZOMBIE else None
    except psutil.NoSuchProcess: return None


def native_identity():
    item = identity(int((RUN / "big.pid").read_text().strip()))
    args = item["argv"]
    for flag, expected in (("--model", MODEL), ("--alias", "lfm3"), ("--port", "18080")):
        if flag not in args or args[args.index(flag) + 1] != expected:
            raise RuntimeError("public native LFM identity mismatch: " + flag)
    if not args[0].endswith("/lfm3/llama.cpp/build/bin/llama-server"):
        raise RuntimeError("unrecognized public executable")
    return item


def quiet_snapshot(public):
    """Counts only; never retain prompt bodies, request content, or diary text."""
    slots = request("slots")
    if not isinstance(slots, list) or not slots:
        raise RuntimeError("native slots unavailable; cannot establish an idle window")
    processing = sum(row.get("is_processing") is not False for row in slots)
    connections = 0
    for item in (public, identity(int((RUN / "gateway.pid").read_text().strip()))):
        p = matching(item)
        if p is None: raise RuntimeError("service identity changed while checking idle")
        connections += sum(c.status == psutil.CONN_ESTABLISHED for c in p.net_connections(kind="tcp"))
    return {"processing_slots": processing, "established_connections": connections}


def resource():
    level = int(subprocess.check_output(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], text=True, timeout=3).strip())
    return {"pressure": level, "available_gib": psutil.virtual_memory().available / 1024 ** 3}


def claim_marker(path, content):
    with Path(path).open("x") as stream:
        stream.write(content); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def release_marker(path, content):
    path = Path(path)
    try:
        if path.read_text() == content:
            path.unlink()
            return True
    except FileNotFoundError: return False
    raise RuntimeError("pause marker changed; preserving an unowned reservation")


def diagnostic_jobs(output=None):
    jobs = []
    for p in psutil.process_iter(["pid", "cmdline", "status"]):
        args = p.info["cmdline"] or []
        if any(a.endswith("/lfm-learning-diagnostic.py") for a in args) and p.info["status"] != psutil.STATUS_ZOMBIE:
            if output is None or ("--output" in args and args[args.index("--output") + 1] == output):
                jobs.append(identity(p.pid))
    return jobs


def stop_owned(item):
    p = matching(item)
    if p is None: return
    if os.getpgid(p.pid) != p.pid:
        raise RuntimeError("diagnostic does not own its process group")
    members = [p] + p.children(recursive=True)
    os.killpg(p.pid, signal.SIGTERM)
    _, alive = psutil.wait_procs(members, timeout=6)
    # A detached restorer cannot reap the original wrapper's child. A zombie
    # is a confirmed exit with no model resources, not a target for SIGKILL.
    alive = [q for q in alive if q.is_running() and q.status() != psutil.STATUS_ZOMBIE]
    if alive:
        os.killpg(p.pid, signal.SIGKILL)
        _, alive = psutil.wait_procs(alive, timeout=6)
    if any(p.is_running() and p.status() != psutil.STATUS_ZOMBIE for p in alive):
        raise RuntimeError("owned diagnostic exit not established; restoration blocked")
    return getattr(p, "returncode", None)


def verify_restored(obligation):
    public = native_identity()
    if public["argv"] != obligation["public"]["argv"] or not health():
        raise RuntimeError("restored public args or health differ")
    models = request("v1/models")
    if not any(row.get("id") == "lfm3" for row in models.get("data", [])):
        raise RuntimeError("restored native alias missing")
    marker = (OPS / "ASSISTANT_RUNNING").read_text()
    if "big pid: " + str(public["pid"]) not in marker:
        raise RuntimeError("ASSISTANT_RUNNING has stale public PID")
    watchdog = psutil.Process(int((RUN / "watchdog.pid").read_text().strip()))
    if watchdog.status() == psutil.STATUS_ZOMBIE or not any(a.endswith("/watchdog.sh") for a in watchdog.cmdline()):
        raise RuntimeError("restored watchdog bookkeeping is not live")
    return public


def restore(obligation_path):
    obligation_path = Path(obligation_path)
    obligation = json.loads(obligation_path.read_text())
    stem = obligation_path.with_suffix("")
    ready = Path(str(stem) + "-restorer-ready.json")
    result_path = Path(str(stem) + "-restoration.json")
    control_path = Path(obligation["control"])
    durable(ready, {"restorer": identity(os.getpid()), "ready_at": time.time()}, exclusive=True)
    while True:
        state = json.loads(control_path.read_text()) if control_path.exists() else {}
        if state.get("restore_requested") or matching(obligation["wrapper"]) is None or time.time() >= obligation["restoration_deadline"]:
            break
        time.sleep(1)
    lock = open(str(stem) + ".restore-lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        state = json.loads(control_path.read_text()) if control_path.exists() else {}
        # Recover the tiny Popen->manifest race by the exact unique output path.
        for job in diagnostic_jobs(obligation["output"]): stop_owned(job)
        if state.get("diagnostic") and matching(state["diagnostic"]):
            raise RuntimeError("owned diagnostic still alive")
        if diagnostic_jobs():
            raise RuntimeError("another HF diagnostic is active; do not stack public model")
        if health():
            restored = verify_restored(obligation)
            try: released = release_marker(obligation["pause_marker"], obligation["marker_content"])
            except RuntimeError: released = False  # preserve a new, unowned reservation
            durable(result_path, {"status": "restored", "method": "already-running", "public": restored,
                                  "owned_marker_removed": released})
            return
        release_marker(obligation["pause_marker"], obligation["marker_content"])
        if listener_present():
            raise RuntimeError("an unrecognized/loading listener occupies the public port; preserve it")
        # Keep standard serve.sh safety guards. Do not use --yes or launch while
        # pressure is elevated. Failure is an explicit durable recovery duty.
        for _ in range(45):
            if resource()["pressure"] == 1: break
            time.sleep(2)
        else: raise RuntimeError("memory did not return to normal; restoration deferred")
        if hashlib.sha256((SERVICE / "config.sh").read_bytes()).hexdigest() != obligation["config_sha256"]:
            raise RuntimeError("service config changed; refusing a possibly different model")
        serve_log = open(str(stem) + "-serve.log", "ab", buffering=0)
        launcher = subprocess.Popen(["/bin/bash", str(SERVICE / "serve.sh"), "--autostart"], cwd=str(SERVICE),
                                    stdin=subprocess.DEVNULL, stdout=serve_log, stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(60):
            if health():
                restored = verify_restored(obligation)
                durable(result_path, {"status": "restored", "method": "serve.sh --autostart", "launcher_pid": launcher.pid,
                                      "public": restored, "health": 200, "restored_at": time.time()})
                return
            if launcher.poll() not in (None, 0):
                raise RuntimeError("standard launcher failed; explicit restoration obligation remains")
            time.sleep(2)
        raise RuntimeError("standard launcher did not restore health; explicit restoration obligation remains")
    except Exception as error:
        durable(result_path, {"status": "restore-failed-explicit-obligation", "error": type(error).__name__ + ": " + str(error),
                              "obligation": str(obligation_path), "at": time.time()})
        raise
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN); lock.close()


def run(label):
    if not re.fullmatch(r"[a-z0-9-]{1,60}", label): raise ValueError("invalid unique run label")
    stem = ROOT / ("lfm3-learning-continuation-64-" + label)
    output, log_path, resources_path, obligation_path, control_path = [Path(str(stem) + suffix) for suffix in
        (".json", ".log", "-resources.jsonl", "-obligation.json", "-control.json")]
    if any(p.exists() for p in (output, log_path, resources_path, obligation_path, control_path)):
        raise FileExistsError("existing artifact; choose a new label")
    if MARKER.exists(): raise RuntimeError("preexisting PAUSE_OTHERS preserved; cannot reserve this run")
    public = native_identity()
    if not health(): raise RuntimeError("public service not healthy before pause")
    # An idle slot alone misses gateway work queued before reaching the model.
    # Require a sustained zero-connection idle window; any unknown work aborts.
    for _ in range(8):
        sample = quiet_snapshot(public)
        if any(sample.values()): raise RuntimeError("public service has current/queued work; no pause")
        time.sleep(2)
    cache = ROOT / "lfm3-learning-continuation-64-retry-20261029-2055-replay-cache.json"
    if hashlib.sha256(cache.read_bytes()).hexdigest() != EXPECTED_CACHE_SHA: raise RuntimeError("teacher fixture altered")
    control = {"restore_requested": False}
    durable(control_path, control, exclusive=True)
    obligation = {"version": 1, "authorized": True, "public": public, "wrapper": identity(os.getpid()),
                  "output": str(output), "control": str(control_path), "pause_marker": str(MARKER),
                  "marker_content": "Owned Premonition research pause " + uuid.uuid4().hex + "\n",
                  "config_sha256": hashlib.sha256((SERVICE / "config.sh").read_bytes()).hexdigest(),
                  "restoration_deadline": time.time() + 560, "created_at": time.time()}
    durable(obligation_path, obligation, exclusive=True)
    restore_stem = obligation_path.with_suffix("")
    side_log = open(str(restore_stem) + "-restorer.log", "ab", buffering=0)
    restorer = subprocess.Popen([PYTHON, str(Path(__file__).resolve()), "--restore-obligation", str(obligation_path)],
                               stdin=subprocess.DEVNULL, stdout=side_log, stderr=subprocess.STDOUT, start_new_session=True)
    child = None
    started = None
    stop_reason = None
    try:
        ready = Path(str(restore_stem) + "-restorer-ready.json")
        for _ in range(50):
            if ready.exists(): break
            if restorer.poll() is not None: raise RuntimeError("independent restorer did not start")
            time.sleep(.1)
        else: raise RuntimeError("independent restorer not acknowledged")
        # Last idle check is immediately before signaling the exact public PID.
        if any(quiet_snapshot(public).values()): raise RuntimeError("work arrived before pause; no pause")
        claim_marker(MARKER, obligation["marker_content"])
        if matching(public) is None: raise RuntimeError("public identity changed before pause")
        psutil.Process(public["pid"]).terminate()
        psutil.Process(public["pid"]).wait(timeout=15)
        control["public_paused_at"] = time.time(); durable(control_path, control)
        if listener_present(): raise RuntimeError("public model auto-restarted; preserving it, aborting diagnostic")
        sample = resource()
        if sample["pressure"] != 1 or sample["available_gib"] < 8:
            raise RuntimeError("insufficient post-pause headroom: " + str(sample))
        prior = json.loads((ROOT / "lfm3-learning-diagnostic-64.json").read_text())
        command = [PYTHON, "-u", str(ROOT / "lfm-learning-diagnostic.py"), "--allow-model-load",
                   "--model-dir", str(OPS / "lfm3/hf"), "--output", str(output), "--steps", "64", "--seed", "0",
                   "--budget-seconds", "500", "--mps-mem-gb", "8", "--replay-mode", "continuation",
                   "--expected-adapter-sha256", prior["initial_adapter_files"]["adapter_model.safetensors"],
                   "--expected-replay-cache", str(cache)]
        with log_path.open("x") as log, resources_path.open("x") as resources:
            child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            control["diagnostic"] = identity(child.pid); durable(control_path, control)
            started, hot = time.monotonic(), 0
            while child.poll() is None:
                sample = {"elapsed_s": time.monotonic() - started, **resource()}
                resources.write(json.dumps(sample) + "\n"); resources.flush()
                hot = hot + 1 if sample["pressure"] > 1 else 0
                if sample["elapsed_s"] > 520: stop_reason = "outer-watchdog-520s"
                elif hot >= 2: stop_reason = "sustained-memory-pressure"
                elif sample["available_gib"] < 1: stop_reason = "critical-remaining-memory"
                elif listener_present(): stop_reason = "public-autorestarted-preserve-public"
                if stop_reason:
                    status = stop_owned(control["diagnostic"])
                    if status is not None: child.returncode = int(status)
                    break
                time.sleep(2)
            child.wait()
            resources.write(json.dumps({"event": "diagnostic-finished", "exit_code": child.returncode,
                                        "stop_reason": stop_reason, "elapsed_s": time.monotonic() - started}) + "\n")
            resources.flush(); os.fsync(resources.fileno())
    finally:
        if child is not None and child.poll() is None:
            status = stop_owned(control["diagnostic"])
            if status is not None: child.returncode = int(status)
            child.wait()
        control["restore_requested"] = True; durable(control_path, control)
        result_path = Path(str(restore_stem) + "-restoration.json")
        for _ in range(100):
            if result_path.exists(): break
            time.sleep(2)
        if not result_path.exists(): raise RuntimeError("independent restorer still has an outstanding obligation: " + str(obligation_path))
        restored = json.loads(result_path.read_text())
        print(json.dumps({"output": str(output), "diagnostic_exit": child.returncode if child else None,
                          "stop_reason": stop_reason, "restoration": restored}, indent=2))
        if restored["status"] != "restored": raise RuntimeError("public restoration remains an explicit obligation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-label")
    parser.add_argument("--restore-obligation", type=Path)
    args = parser.parse_args()
    def interrupted(*_): raise KeyboardInterrupt("wrapper interrupted; independent restorer remains responsible")
    signal.signal(signal.SIGTERM, interrupted)
    if args.restore_obligation: restore(args.restore_obligation)
    elif args.run_label: run(args.run_label)
    else: parser.error("--run-label or --restore-obligation required")
