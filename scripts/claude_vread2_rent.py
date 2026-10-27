#!/usr/bin/env python3
"""vread2 rental control (vector-reader thread, 2026-09-28): one vast.ai job, run from the cloud container over HTTPS.

Based on scripts/claude_vread_rent.py. The proxy adds the vast key to console.vast.ai requests; this script never
reads or prints a key and prints only chosen fields of each API reply. No credential is put on the machine, and
nothing on the machine listens for connections from outside.
Copy-back (vread's log route cut lines at 500 characters, and its checkpoint came back empty): at the end the job
writes MANIFEST.sha256 (also printed to the container log) and base64 text parts of every export file (the 4
checkpoints and results.tar.gz) in two sizes, /job/b64/big (8 MB parts) and /job/b64/small (1 MB parts). After the
instance is stopped, `pull` reads each part with vast `execute` (cat, as vread read its text files), joins them,
decodes and checks every sha256 against the manifest. The instance is destroyed only after that check passes.
  pack    --out DIR                pack.tar.xz of the sealed files at HEAD + SEAL, the job (below) with its sha filled
                                   in, args.json (bash -c job vread2 chunk1 chunk2 ...)
  search                           1 RTX 4090 (the card vread used), verified, reliability >= 0.98, CUDA >= 12.8
  create  --offer ID --args DIR/args.json --label L [--dryrun]
  status  --id ID
  logs    --id ID --out FILE
  waitlog --id ID [--max-min 240]  returns once the container log shows the job finished
  pull    --id ID --out RUNDIR     (stopped instance) every export file through execute + cat, sha256 checked
  stop / destroy --id ID           destroy confirms the instance is gone from the list
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import subprocess
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
API = "https://console.vast.ai/api/v0"
IMAGE = "pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime"
FILES = ["scripts/claude_vread_data.py", "scripts/claude_vread_model.py", "scripts/claude_vread2_data.py",
         "scripts/claude_vread2_model.py", "scripts/claude_lis300_common.py", "scripts/claude_lis319_common.py",
         "scripts/claude_lis300_compiler.py", "scripts/claude_rsn358a_run.py", "scripts/claude_rsn358a_envs.py",
         "scripts/claude_blurt1.py", "design/v3/60-listener/relation-names.txt",
         "artifacts/claude-vread-20260927/data/build.json", "artifacts/claude-vread-20260927/data/dialogs.json.xz",
         "artifacts/claude-vread-20260927/data/rows.json.xz",
         "artifacts/claude-vread2-20260928/data/build.json", "artifacts/claude-vread2-20260928/data/dialogs.json.xz",
         "artifacts/claude-vread2-20260928/data/rows.json.xz"]
CHUNK = 100_000

JOB = r'''# vread2 rental job (vector-reader thread, 2026-09-28), from scripts/claude_vread2_rent.py.
set -u
PACK_SHA=__PACK_SHA__
BASE_REV=87179e5c1f455ef22e6223592d2d61351b525bfc
J=${JOBDIR:-/job}
say() { echo "=== $* $(date -u +%FT%TZ)"; }
mkdir -p "$J/checks" "$J/out" "$J/export" && cd "$J" || exit 1
finish() {   # $1 = DONE or FAIL
  cd "$J"
  (sha256sum out/*/*.pt 2>/dev/null) | tee out/weights_sha.log
  cp out/*/*.pt export/ 2>/dev/null
  ls out/*.log out/*/*.jsonl out/*/*.json out/*/*.log out/*/*.rc checks/* 2>/dev/null > files.txt
  tar -czf export/results.tar.gz -T files.txt 2>/dev/null
  (cd export && sha256sum *.pt results.tar.gz 2>/dev/null > MANIFEST.sha256)
  mkdir -p b64/big b64/small
  for f in export/*.pt export/results.tar.gz; do
    [ -f "$f" ] || continue
    n=$(basename "$f")
    base64 -w 76 "$f" > "b64/$n.b64"
    split -b 8000000 -d -a 3 "b64/$n.b64" "b64/big/$n.b64.p"
    split -b 1000000 -d -a 3 "b64/$n.b64" "b64/small/$n.b64.p"
  done
  (cd b64 && wc -c big/* small/*) > export/PARTS.txt
  say "MANIFEST"; cat export/MANIFEST.sha256
  say "PARTS $(ls b64/big | wc -l) big, $(ls b64/small | wc -l) small"
  say "VREAD2 $1"
  sleep 14400
  exit 0
}
fail() { say "VREAD2-FAIL $*"; finish FAIL; }
say "VREAD2 START"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | tee checks/gpu.txt
echo "cpus $(nproc)"; free -g | head -2; df -h / | tail -1
printf '%s' "$@" | base64 -d > pack.tar.xz
echo "$PACK_SHA  pack.tar.xz" | sha256sum -c || fail "pack sha256"
python -c "import tarfile; tarfile.open('pack.tar.xz', 'r:xz').extractall('.')" || fail "pack untar"
sha256sum -c SEAL-pack.sha256.txt > checks/pack_files.txt 2>&1 || { cat checks/pack_files.txt; fail "file sha256"; }
echo "pack files ok: $(wc -l < checks/pack_files.txt)"
python -c "import torch,sys;print('python',sys.version.split()[0],'torch',torch.__version__,torch.version.cuda,torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-')" 2>&1 | tee checks/torch.txt
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1)
[ "${used:-0}" -gt 2000 ] && fail "GPU busy: $used MiB in use before any run"
PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "transformers==5.17.0" accelerate safetensors huggingface_hub numpy > checks/pip.log 2>&1 \
  || { tail -5 checks/pip.log; fail "pip"; }
python -c "import transformers,torch;print('transformers',transformers.__version__,'torch',torch.__version__)" 2>&1 | tee checks/versions.txt
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error PYTHONUTF8=1 TOKENIZERS_PARALLELISM=false
BASE=$(python -c "from huggingface_hub import snapshot_download as s; print(s('openbmb/MiniCPM5-1B', revision='$BASE_REV'))" 2> checks/download.err) \
  || { tail -3 checks/download.err; fail "model download"; }
export HF_HUB_OFFLINE=1
(cd "$BASE" && sha256sum *.safetensors) | tee checks/base_sha.txt
say "UNPACK"
python -B scripts/claude_vread_data.py unpack --data artifacts/claude-vread-20260927/data --out rows --tokenizer "$BASE" \
  > checks/unpack.json 2>&1 || { tail -5 checks/unpack.json; fail "unpack"; }
python -B scripts/claude_vread2_data.py unpack --data artifacts/claude-vread2-20260928/data --out rows --tokenizer "$BASE" \
  > checks/unpack_fresh.json 2>&1 || { tail -5 checks/unpack_fresh.json; fail "unpack fresh"; }
cat checks/unpack.json checks/unpack_fresh.json
say "CHECKS"
python -B scripts/claude_vread2_model.py gradcheck --base "$BASE" --rows rows/train.cards.jsonl --device cuda \
  > checks/gradcheck.json 2> checks/gradcheck.err || { tail -5 checks/gradcheck.err; fail "gradcheck"; }
tail -1 checks/gradcheck.json
python -B scripts/claude_vread_model.py ptrcheck --base "$BASE" --rows rows/train.cards.jsonl --n 50 > checks/ptrcheck.json \
  2> checks/ptrcheck.err || { tail -5 checks/ptrcheck.err; fail "ptrcheck"; }
python -B scripts/claude_vread2_model.py copycheck --base "$BASE" --rows rows/train.cards.jsonl > checks/copycheck.json \
  2> checks/copycheck.err || { tail -5 checks/copycheck.err; fail "copycheck"; }
tail -qn1 checks/ptrcheck.json checks/copycheck.json
[ "${DRYRUN:-0}" = 1 ] && { say "DRYRUN stop"; finish DONE; }
run_seed() {   # train A and B at one seed, then each reads the calibration slice and the fresh rows
  s=$1; o=out/s$s; mkdir -p $o
  timeout 100m python -B scripts/claude_vread2_model.py train --base "$BASE" --train rows/train.cards.jsonl --seed $s \
    --out $o > $o/train.log 2>&1; echo "train rc=$?" > $o/train.rc
  for arm in A B; do
    for part in cal fresh; do
      timeout 40m python -B scripts/claude_vread2_model.py read --base "$BASE" --ckpt $o/$arm-s$s.pt --arm $arm \
        --rows rows/$part.cards.jsonl --out $o/${part}_$arm-s$s.jsonl > $o/read_${part}_$arm.log 2>&1
      echo "read $part $arm rc=$?" >> $o/read.rc
    done
  done
}
(while true; do sleep 300; echo "=== TICK $(date -u +%H:%M:%S) gpu $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader) | $(tail -qn1 out/s327/train_log.jsonl out/s331/train_log.jsonl 2>/dev/null | cut -c1-90 | tr '\n' ' ')"; done) &
TICK=$!
say "TRAIN + READ, seeds 327 and 331 side by side"
run_seed 327 &
P1=$!
run_seed 331 &
P2=$!
wait $P1 $P2
kill $TICK 2>/dev/null
cat out/s*/train.rc out/s*/read.rc; tail -qn1 out/s*/read_*.log
wc -l out/s*/*.jsonl
finish DONE
'''


def call(method, path, body=None, timeout=60):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            d = json.loads(e.read().decode() or "{}")
        except Exception:
            d = {}
        return {"success": False, "http": e.code, "error": d.get("error"), "msg": d.get("msg")}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def pack(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    for f in FILES + ["scripts/claude_vread2_rent.py"]:
        blob = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{f}"], capture_output=True).stdout
        assert blob == (REPO / f).read_bytes(), f"{f} differs from HEAD {head}"
    seal = "".join(f"{sha((REPO / f).read_bytes())}  {f}\n" for f in FILES)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        for f in FILES:
            t.add(REPO / f, arcname=f)
        info = tarfile.TarInfo("SEAL-pack.sha256.txt")
        info.size, info.mtime = len(seal.encode()), 0
        t.addfile(info, io.BytesIO(seal.encode()))
    data = buf.getvalue()
    (out / "pack.tar.xz").write_bytes(data)
    (out / "SEAL-pack.sha256.txt").write_text(seal)
    job = JOB.replace("__PACK_SHA__", sha(data))
    b64 = base64.b64encode(data).decode()
    args = ["bash", "-c", job, "vread2"] + [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
    (out / "args.json").write_text(json.dumps(args))
    print(json.dumps({"head": head, "pack_sha256": sha(data), "pack_bytes": len(data), "chunks": len(args) - 4,
                      "args_bytes": len(json.dumps(args))}))


def search(a):
    q = {"verified": {"eq": True}, "rentable": {"eq": True}, "rented": {"eq": False}, "type": "on-demand",
         "num_gpus": {"eq": 1}, "gpu_ram": {"gte": 23000}, "reliability": {"gte": 0.98},
         "cuda_max_good": {"gte": 12.8}, "disk_space": {"gte": 60}, "inet_down": {"gte": 300},
         "cpu_cores_effective": {"gte": 8}, "order": [["dph_total", "asc"]], "limit": 200}
    offers = call("POST", "/bundles/", q).get("offers") or []
    keep = [o for o in offers if o.get("gpu_name") == "RTX 4090"]
    for o in keep[: a.n]:
        print(json.dumps({k: o.get(k) for k in ("id", "gpu_name", "gpu_ram", "dph_total", "reliability", "inet_down",
                                                 "cpu_cores_effective", "cpu_ram", "disk_space", "cuda_max_good",
                                                 "geolocation", "machine_id")}))


def create(a):
    args = json.loads(Path(a.args).read_text())
    if a.dryrun:
        args[2] = "export DRYRUN=1\n" + args[2]
    body = {"client_id": "me", "image": IMAGE, "disk": 60, "label": a.label, "runtype": "args", "args": args,
            "target_state": "running"}
    r = call("PUT", f"/asks/{a.offer}/", body, timeout=120)
    print(json.dumps({"success": r.get("success"), "new_contract": r.get("new_contract"), "error": r.get("error"),
                      "msg": r.get("msg"), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))


def inst(i):
    r = call("GET", f"/instances/{i}/")
    x = r.get("instances") or {}
    return (x[0] if x else {}) if isinstance(x, list) else x


def status(a):
    x = inst(a.id)
    print(json.dumps({k: x.get(k) for k in ("id", "label", "actual_status", "intended_status", "cur_state",
                                             "status_msg", "gpu_name", "dph_total", "start_date", "duration",
                                             "machine_id")}))


def log_text(i, tail=400):
    r = call("PUT", f"/instances/request_logs/{i}/", {"tail": str(tail)})
    url = r.get("result_url")
    if not url:
        return ""
    for _ in range(12):
        time.sleep(5)
        try:
            return get(url, 60).decode("utf-8", "replace")
        except Exception:
            continue
    return ""


def logs(a):
    text = log_text(a.id, a.tail)
    Path(a.out).write_text(text)
    short = [ln for ln in text.splitlines() if len(ln) < 400]
    print("\n".join(short[-a.show:]))


def waitlog(a):
    """poll the container log every 3 minutes until the job says VREAD2 DONE / FAIL (or --max-min passes)"""
    t0 = time.time()
    while time.time() - t0 < a.max_min * 60:
        text = log_text(a.id)
        hit = [ln for ln in text.splitlines() if "VREAD2 DONE" in ln or "VREAD2 FAIL" in ln or "VREAD2-FAIL" in ln]
        if hit:
            print(json.dumps({"found": hit[-3:], "waited_min": round((time.time() - t0) / 60, 1)}))
            return
        if inst(a.id).get("actual_status") in ("exited", "stopped", "offline"):
            break
        time.sleep(180)
    print(json.dumps({"found": None, "status": inst(a.id).get("actual_status"),
                      "waited_min": round((time.time() - t0) / 60, 1)}))


def exec_cat(i, path, tries=3):
    for _ in range(tries):
        r = call("PUT", f"/instances/command/{i}/", {"command": f"cat {path}"})
        url = r.get("result_url")
        if not url:
            time.sleep(10)
            continue
        for _ in range(36):
            time.sleep(5)
            try:
                return get(url, 300)
            except Exception:
                continue
    return None


def pull(a):
    """(instance stopped) MANIFEST, PARTS and every base64 part via execute + cat; join, decode, sha256 check"""
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    man = (exec_cat(a.id, "/job/export/MANIFEST.sha256") or b"").decode()
    parts = (exec_cat(a.id, "/job/export/PARTS.txt") or b"").decode()
    (out / "MANIFEST.sha256").write_text(man)
    (out / "PARTS.txt").write_text(parts)
    want = dict(reversed(ln.split(None, 1)) for ln in man.splitlines() if ln.strip())
    sizes = {p: int(n) for n, p in (ln.split() for ln in parts.splitlines() if ln.strip()) if p != "total"}
    res = {}
    for name, h in sorted(want.items()):
        res[name] = {"sha_ok": False}
        for size in ("big", "small"):
            ps = sorted(p for p in sizes if p.startswith(f"{size}/{name}.b64.p"))
            chunks = []
            for p in ps:
                b = exec_cat(a.id, f"/job/b64/{p}")
                if b is None or len(b) != sizes[p]:
                    chunks = None
                    break
                chunks.append(b)
            if not chunks:
                continue
            data = base64.b64decode(b"".join(chunks))
            if sha(data) == h:
                (out / name).write_bytes(data)
                res[name] = {"bytes": len(data), "sha_ok": True, "parts": f"{len(ps)} {size}"}
                break
        print(json.dumps({name: res[name]}), flush=True)
    if res.get("results.tar.gz", {}).get("sha_ok"):
        with tarfile.open(out / "results.tar.gz", "r:gz") as t:
            t.extractall(out, filter="data")
    print(json.dumps({"all_sha_ok": bool(res) and all(v["sha_ok"] for v in res.values()), "files": len(res)}))


def stop(a):
    r = call("PUT", f"/instances/{a.id}/", {"state": "stopped"})
    print(json.dumps({"stop": r.get("success"), "msg": r.get("msg")}))


def destroy(a):
    r = call("DELETE", f"/instances/{a.id}/")
    print(json.dumps({"destroy": r.get("success"), "msg": r.get("msg")}))
    time.sleep(5)
    ids = [i.get("id") for i in (call("GET", "/instances/").get("instances") or [])]
    print(json.dumps({"still_listed": int(a.id) in ids}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pack", "search", "create", "status", "logs", "waitlog", "pull", "stop",
                                    "destroy"])
    ap.add_argument("--out")
    ap.add_argument("--offer")
    ap.add_argument("--args")
    ap.add_argument("--label", default="claude-vread2-run1")
    ap.add_argument("--dryrun", action="store_true")
    ap.add_argument("--id")
    ap.add_argument("--max-min", type=float, default=240)
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--tail", type=int, default=2000)
    ap.add_argument("--show", type=int, default=40)
    a = ap.parse_args()
    {"pack": pack, "search": search, "create": create, "status": status, "logs": logs, "waitlog": waitlog,
     "pull": pull, "stop": stop, "destroy": destroy}[a.cmd](a)


if __name__ == "__main__":
    main()
