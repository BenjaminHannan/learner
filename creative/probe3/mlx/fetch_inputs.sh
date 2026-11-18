#!/usr/bin/env bash
# Step zero for the Mac: make sure the Probe-3 inputs are on disk.
# The repo already carries small copies under creative/probe3/inputs/ (about 7.5 MB, checked by MANIFEST.json), so on the Mac this normally only verifies them:
#     fetch_inputs.sh                      # verify ../inputs against MANIFEST.json (sha256)
# Where the copies come from (cloud side, /mnt/project-files exists there), and what run_m3.sh takes as arguments:
#   Guess-1 run dir     inputs/guess1_run/           target.json + a SLIM results.jsonl (only what replay/analyze read; verified identical reports vs the 21 MB original)
#                       cloud original: /mnt/project-files/creative/guess1/out-seed2/guess1-seed2/run/{target.json,results.jsonl}
#   Pick-1 SELF scores  inputs/pick1/k2_scores.jsonl        cloud: /mnt/project-files/creative/pick1/out/pick1/k2_scores.jsonl
#   Pools               inputs/pick1/pools.jsonl            cloud: /mnt/project-files/creative/pick1/pools.jsonl   (so pick1/pools.py and Guess-1's run.py are not needed on the Mac)
#   Haiku train probes  inputs/haiku_train_probes.jsonl     cloud: /mnt/project-files/creative/probe3/data/haiku_train_probes.jsonl
# To rebuild the copies on the cloud side:   python3 creative/probe3/mlx/make_inputs.py [--mnt /mnt/project-files/creative/]
# To use the ORIGINAL files instead (copy them to the Mac yourself, e.g. with scp), pass their paths to run_m3.sh as arguments 2-5; analyze.py/replay.py/build_data.py accept either layout.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); IN=${1:-$HERE/../inputs}
[ -f "$IN/MANIFEST.json" ] || { echo "no $IN/MANIFEST.json: copy creative/probe3/inputs/ from the repo (git pull), or run make_inputs.py on the cloud side"; exit 4; }
python3 - "$IN" <<'PY'
import hashlib, json, os, sys
d = sys.argv[1]
man = json.load(open(os.path.join(d, "MANIFEST.json")))
bad = [k for k, v in man.items() if not os.path.exists(os.path.join(d, k)) or hashlib.sha256(open(os.path.join(d, k), "rb").read()).hexdigest() != v["sha256"]]
print(f"{len(man)} input files, {sum(v['bytes'] for v in man.values()) / 1e6:.1f} MB; " + ("MISMATCH or missing: " + ", ".join(bad) if bad else "all present and unchanged"))
sys.exit(1 if bad else 0)
PY
