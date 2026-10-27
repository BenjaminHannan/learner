#!/usr/bin/env python3
"""Prepare registered code-checked AR2 panels; no model construction or updates."""
import json
import os
import platform
import subprocess
import time

import run_experiment as X


def main():
    assert X.REGISTRATION != "PENDING_REGISTRATION"
    registered = subprocess.check_output(
        ["git", "show", f"{X.REGISTRATION}:artifacts/codex-autoroute-20260927/hard_replay/PASSMARKS.md"],
        cwd=X.REPO)
    assert registered == (X.HERE / "PASSMARKS.md").read_bytes()
    start = X.utc()
    started = time.monotonic()
    note = X.HERE / "RUN-NOTE.md"
    if not note.exists():
        note.write_text(f"# AR2 registered preparation\n\n"
                        "Fresh panel-seed search (`date -u`): Sun Sep 27 14:23:55 UTC 2026. No matches.\n\n"
                        f"Panel preparation start (`date -u`): {start}\n\n"
                        f"Machine: {platform.node()}; preparation PID {os.getpid()}.\n\n"
                        f"Registration, already pushed before this run: {X.REGISTRATION}.\n\n"
                        "Command: `python -B artifacts/codex-autoroute-20260927/hard_replay/prepare_panels.py`.\n\n"
                        "No model construction or optimizer updates in panel preparation. The later "
                        "preflight and driver record their own UTC times, machine and PIDs.\n")
    out = dict(start_utc=start, machine=platform.node(), pid=os.getpid(),
               registration_commit=X.REGISTRATION, model_constructions=0,
               optimizer_updates=0, panels={})
    unique = {kind: set() for kind in X.KINDS}
    totals = {kind: 0 for kind in X.KINDS}
    for seed in X.SEEDS:
        data = X.panels(seed)
        path = X.HERE / "panels" / f"seed{seed}.json"
        out["panels"][str(seed)] = dict(panel_seed=data["panel_seed"],
                                        diagnostic_seed=data["diagnostic_seed"],
                                        sha256=X.sha(path), duplicate_rejections=data["duplicate_rejections"])
        for name in ("final", "diagnostic"):
            for row in data[name]:
                unique[row["env"]].add(row["id"])
                totals[row["env"]] += 1
        print(f"Validated panels for seed {seed}: 600 final, 300 diagnostic", flush=True)
    out["cross_seed_inputs"] = {kind: dict(total=totals[kind], unique=len(unique[kind]))
                                 for kind in X.KINDS}
    out["end_utc"] = X.utc()
    out["minutes"] = (time.monotonic() - started) / 60
    report = X.HERE / "PANEL-PREPARATION.json"
    assert not report.exists(), "refuse overwrite"
    X.write_json(report, out)
    print(json.dumps(out, indent=2), flush=True)


if __name__ == "__main__":
    main()
