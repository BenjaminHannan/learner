#!/usr/bin/env python3
"""Pack the LFM2.5-350M swap test: round 4 code (commit ba5b64aee, rent3 pack) with only --lm/--revision changed.
Usage: pack_small.py R4_ENGLISH_DIR SEED OUTDIR   (seed 0 also runs bare 350M zero-shot and 8-shot)."""
import base64, hashlib, io, json, subprocess, sys, tarfile
from pathlib import Path
E = Path(sys.argv[1]).resolve(); seed = int(sys.argv[2]); out = Path(sys.argv[3])
sys.path[:0] = [str(E), str(E.parent), str(E.parent.parent)]
import rent, rent2, rent3
LM = "--lm LiquidAI/LFM2.5-350M --revision 9e6c6ccf47cd318696e137d381a7ded8fe4df09f"
out.mkdir(parents=True, exist_ok=True)
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:xz") as t:
    for m in rent2.MODS:
        b = subprocess.run(["git", "-C", str(E), "show", f"{rent2.PIN}:pipeline/{m}"], capture_output=True, check=True).stdout
        ti = tarfile.TarInfo(m); ti.size = len(b); t.addfile(ti, io.BytesIO(b))
    for f in rent3.OWN:
        t.add(E / f, arcname=f"english_test/{f}")
data = buf.getvalue(); h = hashlib.sha256(data).hexdigest()
ex = "".join(f"python english_test/run_english.py --arm {a} {LM} --out $J/out > $J/out/run-{a}.out 2>&1;"
             for a in (("lm_alone", "lm_fewshot") if seed == 0 else ()))
job = (rent3.JOB.replace("__SHA__", h).replace("__ARMS__", "allptr").replace("__SEED__", str(seed))
       .replace("__EXTRA__", ex).replace("__XARGS__", f"--gen 8000 {LM}")
       .replace("s('LiquidAI/LFM2.5-1.2B-Instruct', revision='0f604ada3f766f9f257460c4c9f0b5d6f69d431b')",
                "s('LiquidAI/LFM2.5-350M', revision='9e6c6ccf47cd318696e137d381a7ded8fe4df09f')"))
assert "LFM2.5-350M', revision" in job and "__" not in job.replace("__name__", "")
b64 = base64.b64encode(data).decode()
args = ["bash", "-c", job, "engreal"] + [b64[i:i + rent.CHUNK] for i in range(0, len(b64), rent.CHUNK)]
(out / "args.json").write_text(json.dumps(args))
print(json.dumps({"seed": seed, "pack_sha256": h, "bytes": len(data)}))
