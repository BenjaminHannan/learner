#!/usr/bin/env python3
"""Swarm screen C0 + S0 rental control (coordinator approval of 2026-10-20), run from the cloud container over HTTPS.

Based on scripts/claude_vread2_rent.py. The proxy adds the vast key to console.vast.ai requests; this script never
reads or prints a key and prints only chosen fields of each API reply. No credential is put on the machine (the repo
is public: the job fetches the sealed commit by its sha, so HEAD == PIN is a cryptographic pin of every file), and
nothing on the machine listens for connections from outside. This file is rental tooling, outside the sealed code:
the box runs `scripts/premonition_swarm_box.sh` at PIN, unchanged.

The job (JOB below) runs the approved operating rules: bash >= 4.4 checked first, the GPU idle, a clean checkout at
PIN, then ONE box invocation `PIN=... DPH=... BOX_START=... bash scripts/premonition_swarm_box.sh` (PART=all, no
MAXH, no C0_EXTRA, no STOP_OVERRIDE). Whatever the box's exit code (0 done, 2 refused, 3 stop-and-ask, 4 deadline or
sub-cap, 5 a step failed), it exports OUT's JSON and logs (never checkpoints) and, on exit 0, the box's own
swarm-screen-out.tgz, as sha256-checked base64 parts. After the instance is stopped, `pull` reads every part with
vast `execute` (cat), joins, decodes and checks each sha256; the instance is destroyed only after that check passes.

  search                              RTX 4090 offers at <= --max-dph (default 0.494: 8.5 h x DPH <= $4.20)
  create  --offer ID --label L        BOX_START = now (before the request, so billing is never undercounted);
                                      DPH = the offer's dph_total rounded UP to 4 decimals; refuses above --max-dph
  status  --id ID                     billed rate, state, start
  logs    --id ID --out FILE
  waitlog --id ID [--max-min 600]     returns once the job log shows SWARM DONE / SWARM EXIT
  pull    --id ID --out RUNDIR        (stopped instance) every export file through execute + cat, sha256 checked
  stop / destroy --id ID              destroy confirms the instance is gone from the list
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://console.vast.ai/api/v0"
IMAGE = "pytorch/pytorch:2.14.1-cuda12.6-cudnn9-runtime"   # the dry run's torch 2.14.1; the code parses on 3.11+
REPO_URL = "https://github.com/BenjaminHannan/learner"
PIN = "34d8d0635529f6c712c5f8e7630976054bfd84d4"            # RUNCARD-S0 seal (code identical to 0d7a2e633)
MAX_DPH = 0.494                                              # 8.5 h x DPH <= $4.20 (the box refuses above)
DISK_GB = 80
ROUND_MARGIN = 0.002                                         # $/h on top of dph_total (which includes the 80 GB disk:
                                                             # the search asks with allocated_storage = DISK_GB)

JOB = r'''# swarm screen C0 + S0 rental job, from scripts/claude_swarm_rent.py (coordinator approval 2026-10-20)
set -u
export PIN=__PIN__
export DPH=__DPH__ BOX_START=__BOX_START__ CAP=__CAP__
J=${JOBDIR:-/job}
REPO=$J/repo
OUT=$REPO/artifacts/claude-swarm-screen-20261018/out
say() { echo "=== $* $(date -u +%FT%TZ)"; }
mkdir -p "$J/checks" "$J/export" && cd "$J" || exit 1
finish() {   # $1 = the box's exit code (or a job failure)
  cd "$J"
  if [ -d "$OUT" ]; then
    (cd "$OUT" && find . -type f \( -name '*.json' -o -name '*.log' -o -name '*.md' -o -name '*.txt' -o -name '*.tsv' \) \
       -not -path './ckpt/*' -not -path './c0-probe/*' | sort > "$J/files.txt")
    tar -czf export/out-files.tgz -C "$OUT" -T "$J/files.txt" 2>/dev/null
    [ -f "$OUT/swarm-screen-out.tgz" ] && cp "$OUT/swarm-screen-out.tgz" export/
  fi
  [ -f "$REPO/artifacts/claude-swarm-screen-20261018/money-ledger.json" ] && cp "$REPO/artifacts/claude-swarm-screen-20261018/money-ledger.json" export/
  tar -czf export/checks.tgz checks 2>/dev/null
  (cd export && sha256sum * > MANIFEST.sha256)
  mkdir -p b64
  for f in export/*; do
    n=$(basename "$f"); [ "$n" = MANIFEST.sha256 ] && continue
    base64 -w 76 "$f" > "b64/$n.b64"
    split -b 1000000 -d -a 3 "b64/$n.b64" "b64/$n.b64.p"
    rm "b64/$n.b64"
  done
  (cd b64 && wc -c ./*.p*) > export/PARTS.txt
  say "MANIFEST"; cat export/MANIFEST.sha256
  say "SWARM EXIT rc=$1"
  [ -f "$OUT/box.log" ] && tail -n 5 "$OUT/box.log"
  say "SWARM DONE"
  sleep 28800
  exit 0
}
fail() { say "SWARM JOB-FAIL $*"; finish "job:$*"; }
say "SWARM START pin $PIN dph $DPH box_start $BOX_START"
# operating rule 1: bash >= 4.4 (empty-array expansions under set -u)
echo "bash $BASH_VERSION" | tee checks/bash.txt
[ "${BASH_VERSINFO[0]}" -gt 4 ] || { [ "${BASH_VERSINFO[0]}" -eq 4 ] && [ "${BASH_VERSINFO[1]}" -ge 4 ]; } || fail "bash < 4.4"
nvidia-smi --query-gpu=name,uuid,memory.total,driver_version --format=csv,noheader 2>&1 | tee checks/gpu.txt
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1)
[ "${used:-0}" -gt 2000 ] && fail "GPU busy: $used MiB in use before any run"
echo "cpus $(nproc)"; free -g | head -2; df -h / | tail -1
python -c "import torch,sys;print('python',sys.version.split()[0],'torch',torch.__version__,torch.version.cuda,torch.cuda.is_available())" 2>&1 | tee checks/torch.txt
command -v git > /dev/null || { (apt-get update -qq && apt-get install -y -qq git) > checks/apt.log 2>&1 || fail "git install"; }
say "CHECKOUT"
git init -q "$REPO" && git -C "$REPO" remote add origin "$REPO_URL" || fail "git init"
git -C "$REPO" fetch -q --depth 1 origin "$PIN" > checks/fetch.log 2>&1 || { tail -3 checks/fetch.log; fail "git fetch"; }
git -C "$REPO" -c advice.detachedHead=false checkout -q FETCH_HEAD > checks/checkout.log 2>&1 || fail "git checkout"
[ "$(git -C "$REPO" rev-parse HEAD)" = "$PIN" ] || fail "HEAD is not PIN"
say "BOX"
cd "$REPO"
bash scripts/premonition_swarm_box.sh > "$J/checks/box.out" 2>&1
rc=$?
finish "$rc"
'''.replace("__PIN__", PIN).replace("$REPO_URL", REPO_URL)


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


def offers(max_dph):
    q = {"verified": {"eq": True}, "rentable": {"eq": True}, "rented": {"eq": False}, "type": "on-demand",
         "num_gpus": {"eq": 1}, "gpu_ram": {"gte": 23000}, "reliability": {"gte": 0.98},
         "cuda_max_good": {"gte": 12.6}, "disk_space": {"gte": DISK_GB}, "inet_down": {"gte": 300},
         "cpu_cores_effective": {"gte": 8}, "allocated_storage": DISK_GB, "order": [["dph_total", "asc"]],
         "limit": 200}
    found = call("POST", "/bundles/", q).get("offers") or []
    return [o for o in found if o.get("gpu_name") == "RTX 4090" and o.get("dph_total", 99) <= max_dph]


def search(a):
    for o in offers(a.max_dph)[: a.n]:
        print(json.dumps({k: o.get(k) for k in ("id", "gpu_name", "gpu_ram", "dph_total", "reliability", "inet_down",
                                                 "cpu_cores_effective", "cpu_ram", "disk_space", "cuda_max_good",
                                                 "geolocation", "machine_id")}))


def job_for(dph: str, box_start: int, cap: str = "4.20") -> str:
    return JOB.replace("__DPH__", dph).replace("__BOX_START__", str(box_start)).replace("__CAP__", cap)


def create(a):
    offer = next((o for o in offers(a.max_dph) if str(o.get("id")) == str(a.offer)), None)
    if offer is None:
        print(json.dumps({"refused": f"offer {a.offer} is not an RTX 4090 offer at <= ${a.max_dph}/h right now"}))
        return
    dph = f"{math.ceil((offer['dph_total'] + ROUND_MARGIN) * 10000) / 10000:.4f}"     # rounded up: never undercounts
    if float(dph) > a.max_dph:
        print(json.dumps({"refused": f"DPH {dph} with the storage margin is above ${a.max_dph}/h"}))
        return
    box_start = int(time.time())                                         # before the request: billing is covered
    body = {"client_id": "me", "image": IMAGE, "disk": DISK_GB, "label": a.label, "runtype": "args",
            "args": ["bash", "-c", job_for(dph, box_start, a.cap), "swarm"], "target_state": "running"}
    if a.dryrun:
        print(json.dumps({"dryrun": True, "offer": offer.get("id"), "dph": dph, "box_start": box_start,
                          "job_bytes": len(body["args"][2])}))
        return
    r = call("PUT", f"/asks/{a.offer}/", body, timeout=120)
    print(json.dumps({"success": r.get("success"), "new_contract": r.get("new_contract"), "error": r.get("error"),
                      "msg": r.get("msg"), "dph": dph, "cap": a.cap, "box_start": box_start,
                      "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(box_start))}), flush=True)
    new = r.get("new_contract")
    if not new:
        return
    for _ in range(6):                       # the billed rate must not exceed the DPH the box counts with
        time.sleep(5)
        billed = inst(new).get("dph_total")
        if billed is not None:
            break
    if billed is None or billed > float(dph):
        call("DELETE", f"/instances/{new}/")
        print(json.dumps({"destroyed": new, "reason": f"billed {billed} $/h > the box's DPH {dph} (or unknown)"}))
    else:
        print(json.dumps({"billed_dph": billed, "box_dph": dph, "ok": True}))


def inst(i):
    r = call("GET", f"/instances/{i}/")
    x = r.get("instances") or {}
    return (x[0] if x else {}) if isinstance(x, list) else x


def status(a):
    x = inst(a.id)
    out = {k: x.get(k) for k in ("id", "label", "actual_status", "intended_status", "cur_state", "status_msg",
                                 "gpu_name", "dph_total", "start_date", "duration", "machine_id")}
    if a.dph is not None and x.get("dph_total") is not None:     # the box counts with DPH; it must not be below billing
        out["billed_within_box_dph"] = x["dph_total"] <= float(a.dph)
    print(json.dumps(out))


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
    """poll the container log every 3 minutes until the job says SWARM DONE (or --max-min passes)"""
    t0 = time.time()
    while time.time() - t0 < a.max_min * 60:
        text = log_text(a.id)
        hit = [ln for ln in text.splitlines() if "SWARM EXIT" in ln or "SWARM DONE" in ln or "JOB-FAIL" in ln]
        if any("SWARM DONE" in ln for ln in hit):
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
    want.pop("PARTS.txt", None)
    sizes = {p.removeprefix("./"): int(n) for n, p in (ln.split() for ln in parts.splitlines() if ln.strip())
             if p != "total"}
    res = {}
    for name, h in sorted(want.items()):
        ps = sorted(p for p in sizes if p.startswith(f"{name}.b64.p"))
        chunks = []
        for p in ps:
            b = exec_cat(a.id, f"/job/b64/{p}")
            if b is None or len(b) != sizes[p]:
                chunks = None
                break
            chunks.append(b)
        ok = False
        if chunks:
            data = base64.b64decode(b"".join(chunks))
            ok = sha(data) == h
            if ok:
                (out / name).write_bytes(data)
        res[name] = {"sha_ok": ok, "parts": len(ps)}
        print(json.dumps({name: res[name]}), flush=True)
    for name in ("out-files.tgz", "checks.tgz"):
        if res.get(name, {}).get("sha_ok"):
            with tarfile.open(out / name, "r:gz") as t:
                t.extractall(out / name.removesuffix(".tgz"), filter="data")
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
    ap.add_argument("cmd", choices=["search", "create", "status", "logs", "waitlog", "pull", "stop", "destroy", "job"])
    ap.add_argument("--out")
    ap.add_argument("--offer")
    ap.add_argument("--label", default="claude-swarm-screen-s0")
    ap.add_argument("--dryrun", action="store_true", help="create: print what would be sent, rent nothing")
    ap.add_argument("--max-dph", type=float, default=MAX_DPH)
    ap.add_argument("--cap", default="4.20", help="create: the box's CAP (the $4.20 total minus anything already spent)")
    ap.add_argument("--id")
    ap.add_argument("--max-min", type=float, default=600)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--tail", type=int, default=2000)
    ap.add_argument("--show", type=int, default=40)
    ap.add_argument("--dph", default=None, help="job: the DPH to fill in (rehearsal); status: the DPH the box uses")
    a = ap.parse_args()
    if a.cmd == "job":                                    # print the job script (rehearsal / review), rent nothing
        print(job_for(a.dph or "0.4600", int(time.time()), a.cap))
        return
    {"search": search, "create": create, "status": status, "logs": logs, "waitlog": waitlog, "pull": pull,
     "stop": stop, "destroy": destroy}[a.cmd](a)


if __name__ == "__main__":
    main()
