# Round 4 (more nights) on the PC: one run

Install: `pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128` plus the repo's other requirements; run from the repo root with `export PYTHONPATH=$PWD PYTHONHASHSEED=0`.

```bash
J=$HOME/r4; mkdir -p $J && python -m skills_curriculum.build --out $J/skills --train 200000 --dev-per-cell 40 --seed 1 \
&& python - <<'PY'
import hashlib, json, os, urllib.request
J = os.environ["J"]
assert json.load(open("skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json"))["files_sha256"] == json.load(open(J + "/skills/manifest.json"))["files_sha256"], "skills hashes differ"
data = urllib.request.urlopen("https://raw.githubusercontent.com/BenjaminHannan/learner/claude/b2-confirm-checkpoints/custom_io/checkpoints/33-b2-confirm/B2_s200/checkpoint.pt", timeout=120).read()
assert hashlib.sha256(data).hexdigest() == "94057436d98a485cb4ed0bc750244c2d86a2c744d249106276b15effe94b9d3a"
open(J + "/B2_s200.pt", "wb").write(data); print("setup ok")
PY
python -m creative.multistep --b2 $J/B2_s200.pt --skills $J/skills --out $J/out --cache-dir $J/dreamcache --device cuda --seeds 0 1 --round 4 --parallel 4
```

(`export J=$HOME/r4` first so the Python block sees it.) Arms: `base` and `nights4`, both reporting Hard after every night. Output: `$J/out/results.json` (verdict lines incl. the CURVE lines, `failed_arms`), per arm `$J/out/s<seed>/<arm>/train.json` (`night_scores`). Resumable: re-run the same command. Expected time: roughly 1.5 to 3 hours on one GPU (2 seeds; nights4 does 4 sleeps, base 2); not measured. The sealed test split is never read.
