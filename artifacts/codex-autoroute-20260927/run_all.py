#!/usr/bin/env python3
"""Sequential paired MPS execution; never launches another job after STOP."""
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    plan = [(seed, arm) for seed in range(41, 47)
            for arm in (("baseline", "late_replay") if seed % 2 else ("late_replay", "baseline"))]
    note = HERE / "DRIVER-RUN-NOTE.md"
    if not note.exists():
        stamp = subprocess.check_output(["date", "-u"], text=True).strip()
        machine = subprocess.check_output(["hostname"], text=True).strip()
        note.write_text(f"# Sequential AR1 driver\n\nStart (`date -u`): {stamp}\n\nMachine: {machine}; PID {os.getpid()}.\n\nChild PIDs appear in driver.jsonl and each run's RUN-NOTE.md.\n")
    with (HERE / "driver.jsonl").open("a", buffering=1) as log:
        for seed, arm in plan:
            if (HERE / "STOP").exists():
                return 20
            result = HERE / "run" / f"{arm}-s{seed}" / "result.json"
            if result.exists() and json.loads(result.read_text()).get("complete"):
                continue
            cmd = [sys.executable, "-B", str(HERE / "run_experiment.py"), "--arm", arm, "--seed", str(seed)]
            if result.parent.exists():
                if (result.parent / "interruption.pt").exists():
                    cmd.append("--resume")
                else:
                    raise RuntimeError(f"Unfinished run requires inspection: {result.parent}")
            child = subprocess.Popen(cmd, cwd=HERE.parents[1])
            log.write(json.dumps(dict(seed=seed, arm=arm, pid=child.pid, command=cmd)) + "\n")
            code = child.wait()
            log.write(json.dumps(dict(seed=seed, arm=arm, exit_code=code)) + "\n")
            if code:
                return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
