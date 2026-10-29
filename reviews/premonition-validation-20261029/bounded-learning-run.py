"""Run the resource-cleared diagnostic; terminate only its owned process group."""
import json
import argparse
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parent
PYTHON = "/Users/ben-hannan/learner-ops/speedbench/venv312/bin/python"


def health():
    try:
        with urllib.request.urlopen("http://127.0.0.1:18080/health", timeout=3) as response:
            return {"status": response.status, "body": response.read().decode()}
    except Exception as error:
        return {"error": type(error).__name__ + ": " + str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-mode", choices=("prompt", "continuation"), default="prompt")
    parser.add_argument("--run-label", default="", help="Unique artifact suffix; never replaces an earlier run")
    args = parser.parse_args()
    stem = "lfm3-learning-diagnostic-64" if args.replay_mode == "prompt" else "lfm3-learning-continuation-64"
    if args.run_label:
        if not re.fullmatch(r"[a-z0-9-]{1,60}", args.run_label):
            parser.error("--run-label must contain only lowercase letters, digits, or hyphens")
        stem += "-" + args.run_label
    output, log_path, resource_path = (ROOT / (stem + suffix) for suffix in (".json", ".log", "-resources.jsonl"))
    if any(path.exists() for path in (output, log_path, resource_path)):
        raise ValueError("refusing to overwrite an existing experiment artifact")
    before = health()
    if before.get("status") != 200:
        raise RuntimeError("The public daytime model is not healthy before the diagnostic")
    pressure = int(subprocess.check_output(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], text=True, timeout=3).strip())
    available = psutil.virtual_memory().available / 1024 ** 3
    if pressure != 1 or available < 8:
        raise RuntimeError("insufficient pre-load headroom: pressure %s, available %.2f GiB" % (pressure, available))
    command = [PYTHON, "-u", str(ROOT / "lfm-learning-diagnostic.py"), "--allow-model-load",
               "--model-dir", "/Users/ben-hannan/learner-ops/lfm3/hf", "--output", str(output),
               "--steps", "64", "--seed", "0", "--budget-seconds", "300", "--mps-mem-gb", "8",
               "--replay-mode", args.replay_mode]
    if args.replay_mode == "continuation":
        prior = json.loads((ROOT / "lfm3-learning-diagnostic-64.json").read_text())
        command += ["--expected-adapter-sha256", prior["initial_adapter_files"]["adapter_model.safetensors"]]
    started = time.monotonic()
    stop_reason, hot = None, 0
    with log_path.open("w") as log, resource_path.open("w") as resources:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        resources.write(json.dumps({"event": "started", "pid": child.pid, "public_health": before}) + "\n")
        resources.flush()
        while child.poll() is None:
            pressure = int(subprocess.check_output(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], text=True, timeout=3).strip())
            available = psutil.virtual_memory().available / 1024 ** 3
            elapsed = time.monotonic() - started
            hot = hot + 1 if pressure > 1 else 0
            sample = {"elapsed_s": elapsed, "pressure": pressure, "available_gib": available}
            resources.write(json.dumps(sample) + "\n"); resources.flush()
            if elapsed > 320:
                stop_reason = "outer-watchdog-320s"
            elif hot >= 2:
                stop_reason = "sustained-memory-pressure"
            elif available < 1:
                stop_reason = "critical-remaining-memory"
            if stop_reason:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
                break
            time.sleep(2)
        result = {"event": "finished", "exit_code": child.wait(), "stop_reason": stop_reason,
                  "elapsed_s": time.monotonic() - started, "public_health": health(), "output": str(output)}
        resources.write(json.dumps(result) + "\n"); resources.flush()
        print(json.dumps(result, indent=2))
    return 0 if result["exit_code"] == 0 and result["public_health"].get("status") == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
