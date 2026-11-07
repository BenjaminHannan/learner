#!/bin/zsh
# Trainer.py-compatible entrypoint for NIGHT-LEARN's scheduler.
# usage: tonight-remote.sh <verified-dataset.json> <quarantine-dir>
# Real-recording datasets are gated by remote_runner.py exactly like trainer.py:
# 01:00-07:00 local and >=20 minutes of Mac idle, re-checked while the PC trains.
set -euo pipefail
exec /Users/ben-hannan/learner-ops/p2venv/bin/python \
  /Users/ben-hannan/learner-ops/desk-always-on/desk/src/night-learn-remote/remote_runner.py "$@"
