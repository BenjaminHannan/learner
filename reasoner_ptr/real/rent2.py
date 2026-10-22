#!/usr/bin/env python3
"""vast control for the real-pipeline pointer test: same calls as ../rent.py, different pack and job.
Pack = the 15 real pipeline modules pinned at PR #33 commit 34608a1 (git show) + this folder's runner and data."""
import base64, hashlib, io, json, subprocess, sys, tarfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import rent
PIN = "34608a1aeb24e8a855602d72bc23ad90d72253ed"
MODS = ["scripts/cap256_launch/calculator_runtime.py", "scripts/claude_blurt1.py", "scripts/claude_fewex_net.py",
        "scripts/claude_rsn358a_envs.py", "scripts/sol_spatial_attention_core.py", "scripts/sol_spatial_poc_ordered_v2.py",
        "scripts/sol_spatial_poc_plain.py", "scripts/sol_stop_adapter.py", "scripts/sol_stop_ordered_api2.py",
        "scripts/sol_translator_decoder.py", "scripts/sol_translator_english.py", "scripts/sol_translator_english_v6.py",
        "scripts/sol_translator_grounding.py", "scripts/sol_translator_provenance.py", "scripts/sol_translator_runtime.py"]
OWN = ["run_story.py", "gen_story.py", "gen_story2.py", "EVAL-FORM-R2.json", "PASS-MARKS-R2.md"]
JOB = r'''set -u
J=/job; mkdir -p $J/out $J/export; cd $J
say() { echo "=== $* $(date -u +%FT%TZ)"; }
finish() {
  cd $J; tar -czf export/results.tar.gz out
  (cd export && sha256sum results.tar.gz > MANIFEST.sha256)
  mkdir -p b64 && base64 -w 76 export/results.tar.gz > b64/r.b64 && split -b 1000000 -d -a 3 b64/r.b64 b64/r.p
  (cd b64 && wc -c r.p*) > export/PARTS.txt
  say "MANIFEST"; cat export/MANIFEST.sha256; say "PTRREAL $1"; sleep 14400; exit 0; }
say "PTRREAL START"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
printf '%s' "$@" | base64 -d > pack.tar.xz
echo "__SHA__  pack.tar.xz" | sha256sum -c || finish FAIL
mkdir -p bundle && python -c "import tarfile; tarfile.open('pack.tar.xz','r:xz').extractall('bundle')"
PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "transformers==5.18.0" accelerate > out/pip.log 2>&1 || { tail -3 out/pip.log; finish FAIL; }
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1
python -c "from huggingface_hub import snapshot_download as s; s('LiquidAI/LFM2.5-1.2B-Instruct', revision='0f604ada3f766f9f257460c4c9f0b5d6f69d431b')" || finish FAIL
cd bundle/pointer_test && python -c "import gen_story2 as g, hashlib, json; f=g.eval_form(); print('eval rebuilt', hashlib.sha256(json.dumps(f, indent=0).encode()).hexdigest())"; sha256sum EVAL-FORM-R2.json; cd $J/bundle
PIDS=""
for A in __ARMS__; do python pointer_test/run_story.py --arm $A --seed __SEED__ --out $J/out > $J/out/run-$A.out 2>&1 & PIDS="$PIDS $!"; done
(while true; do sleep 180; for f in $J/out/run-*.out; do grep " step " $f | tail -1 | cut -c1-100; done; done) & TICK=$!
wait $PIDS; kill $TICK
for f in $J/out/run-*.out; do grep -E "Traceback|Error" $f | head -3; grep RESULT-JSON $f | cut -c1-300; done
finish DONE
'''


def pack(seed, arms, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        for m in MODS:
            b = subprocess.run(["git", "-C", str(HERE), "show", f"{PIN}:pipeline/{m}"], capture_output=True, check=True).stdout
            ti = tarfile.TarInfo(m); ti.size = len(b); t.addfile(ti, io.BytesIO(b))
        for f in OWN:
            t.add(HERE / f, arcname=f"pointer_test/{f}")
    data = buf.getvalue(); h = hashlib.sha256(data).hexdigest()
    job = JOB.replace("__SHA__", h).replace("__ARMS__", " ".join(arms)).replace("__SEED__", str(seed))
    b64 = base64.b64encode(data).decode()
    args = ["bash", "-c", job, "ptrreal"] + [b64[i:i + rent.CHUNK] for i in range(0, len(b64), rent.CHUNK)]
    (out / "args.json").write_text(json.dumps(args))
    print(json.dumps({"seed": seed, "pack_sha256": h, "bytes": len(data)}))


if __name__ == "__main__":
    pack(int(sys.argv[1]), sys.argv[2].split(","), sys.argv[3])
