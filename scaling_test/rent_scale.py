#!/usr/bin/env python3
"""vast pack for the fair-scaling test: one box per seed, several runs per box (own arguments each).
Pack = the 15 real pipeline modules pinned at PR #33 commit 34608a1 + this folder. Usage:
  rent_scale.py SEED OUTDIR [extra_arm|-] "args run 1" "args run 2" ...   (run args include --arm and size flags)"""
import base64, hashlib, io, json, subprocess, sys, tarfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rent, rent2, rent3
OWN = ["run_english.py", "gen_english.py", "english_training_candidates_v3.json", "FRESH-EN-R3.json", "GEN-HELDOUT-R4.json",
       "NEW-KINDS-S.json", "PASS-MARKS-SCALE.md"]
LOOP = 'for A in __ARMS__; do python english_test/run_english.py --arm $A --seed __SEED__ __XARGS__ --out $J/out > $J/out/run-$A.out 2>&1 & PIDS="$PIDS $!"; done'


def pack(seed, out, extra, runs):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        for m in rent2.MODS:
            b = subprocess.run(["git", "-C", str(HERE), "show", f"{rent2.PIN}:pipeline/{m}"], capture_output=True, check=True).stdout
            ti = tarfile.TarInfo(m); ti.size = len(b); t.addfile(ti, io.BytesIO(b))
        for f in OWN:
            t.add(HERE / f, arcname=f"english_test/{f}")
    data = buf.getvalue(); h = hashlib.sha256(data).hexdigest()
    assert LOOP in rent3.JOB, "loop line changed"
    cmds = " ".join(f'python english_test/run_english.py --seed {seed} {r} --extra-eval english_test/NEW-KINDS-S.json --out $J/out > $J/out/run-{i}.out 2>&1 & PIDS="$PIDS $!";' for i, r in enumerate(runs))
    ex = f"python english_test/run_english.py --arm {extra} --extra-eval english_test/NEW-KINDS-S.json --out $J/out > $J/out/run-{extra}.out 2>&1;" if extra else ""
    job = rent3.JOB.replace(LOOP, cmds).replace("__SHA__", h).replace("__EXTRA__", ex).replace(
        "sha256sum FRESH-EN-R3.json", "sha256sum NEW-KINDS-S.json FRESH-EN-R3.json")
    b64 = base64.b64encode(data).decode()
    args = ["bash", "-c", job, "engreal"] + [b64[i:i + rent.CHUNK] for i in range(0, len(b64), rent.CHUNK)]
    (out / "args.json").write_text(json.dumps(args))
    print(json.dumps({"seed": seed, "pack_sha256": h, "bytes": len(data)}))


if __name__ == "__main__":
    pack(int(sys.argv[1]), sys.argv[2], sys.argv[3] if sys.argv[3] != "-" else "", sys.argv[4:])
