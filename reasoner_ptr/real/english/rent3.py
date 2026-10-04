#!/usr/bin/env python3
"""vast pack for the English rerun (round 3): rent2's pinned PR #33 modules + this folder. Usage: rent3.py SEED arms OUTDIR [lm_alone]"""
import base64, hashlib, io, json, subprocess, sys, tarfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent.parent))
import rent, rent2
OWN = ["run_english.py", "english_training_candidates_v3.json", "FRESH-EN-R3.json", "PASS-MARKS-R3.md"]
JOB = rent2.JOB.replace("cd bundle/pointer_test && python -c \"import gen_story2 as g, hashlib, json; f=g.eval_form(); print('eval rebuilt', hashlib.sha256(json.dumps(f, indent=0).encode()).hexdigest())\"; sha256sum EVAL-FORM-R2.json; cd $J/bundle",
                        "cd bundle/english_test && sha256sum FRESH-EN-R3.json english_training_candidates_v3.json; cd $J/bundle")
assert JOB != rent2.JOB
JOB = JOB.replace("python pointer_test/run_story.py --arm $A --seed __SEED__", "python english_test/run_english.py --arm $A --seed __SEED__")
JOB = JOB.replace("wait $PIDS; kill $TICK", "wait $PIDS; __EXTRA__ kill $TICK").replace("PTRREAL", "ENGREAL")


def pack(seed, arms, out, extra):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        for m in rent2.MODS:
            b = subprocess.run(["git", "-C", str(HERE), "show", f"{rent2.PIN}:pipeline/{m}"], capture_output=True, check=True).stdout
            ti = tarfile.TarInfo(m); ti.size = len(b); t.addfile(ti, io.BytesIO(b))
        for f in OWN:
            t.add(HERE / f, arcname=f"english_test/{f}")
    data = buf.getvalue(); h = hashlib.sha256(data).hexdigest()
    ex = "python english_test/run_english.py --arm lm_alone --out $J/out > $J/out/run-lm_alone.out 2>&1;" if extra else ""
    job = JOB.replace("__SHA__", h).replace("__ARMS__", " ".join(arms)).replace("__SEED__", str(seed)).replace("__EXTRA__", ex)
    b64 = base64.b64encode(data).decode()
    args = ["bash", "-c", job, "engreal"] + [b64[i:i + rent.CHUNK] for i in range(0, len(b64), rent.CHUNK)]
    (out / "args.json").write_text(json.dumps(args))
    print(json.dumps({"seed": seed, "pack_sha256": h, "bytes": len(data)}))


if __name__ == "__main__":
    pack(int(sys.argv[1]), sys.argv[2].split(","), sys.argv[3], len(sys.argv) > 4)
