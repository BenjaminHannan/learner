#!/usr/bin/env python3
"""vread rental control (vector-reader thread, 2026-09-27): one vast.ai job, run from the cloud container over HTTPS.

The proxy adds the vast key to console.vast.ai requests. This script never reads or prints a key: it prints only
chosen fields of each API reply (a create reply can carry an instance-scoped key, which is dropped unprinted).
  pack    --out DIR          pack.tar.xz of the sealed files at HEAD (+ SEAL-pack.sha256.txt), the job script with its
                             sha filled in, and args.json (bash -c job vread chunk1 chunk2 ...; chunks of 100,000 chars)
  search                     offers: 1 GPU with >= 23 GB, verified, reliability >= 0.98, on-demand, CUDA >= 12.8,
                             disk >= 60 GB, download >= 300 Mbps; cheapest first
  create  --offer ID --args DIR/args.json --label L [--dryrun]
  status  --id ID
  logs    --id ID --out FILE [--tail 20000]
  fetch   --log FILE --out DIR       the RESULTS block -> sha256 checked -> untarred
  destroy --id ID                    then confirms it is gone
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
API = "https://console.vast.ai/api/v0"
IMAGE = "pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime"
FILES = ["scripts/claude_vread_data.py", "scripts/claude_vread_model.py", "scripts/claude_lis300_train.py",
         "scripts/claude_lis319_read.py", "scripts/claude_lis300_read.py", "scripts/claude_lis300_common.py",
         "scripts/claude_lis319_common.py", "scripts/claude_lis300_compiler.py", "scripts/claude_rsn358a_run.py",
         "scripts/claude_rsn358a_envs.py", "scripts/claude_blurt1.py", "design/v3/60-listener/relation-names.txt",
         "artifacts/claude-vread-20260927/data/build.json", "artifacts/claude-vread-20260927/data/dialogs.json.xz",
         "artifacts/claude-vread-20260927/data/rows.json.xz"]
CHUNK = 100_000


def call(method, path, body=None, timeout=60):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def pack(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    for f in FILES + ["scripts/claude_vread_job.sh"]:   # every packed file must equal its committed version
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
    job = (REPO / "scripts/claude_vread_job.sh").read_text().replace("__PACK_SHA__", sha(data))
    b64 = base64.b64encode(data).decode()
    chunks = [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
    args = ["bash", "-c", job, "vread"] + chunks
    (out / "args.json").write_text(json.dumps(args))
    print(json.dumps({"head": head, "pack_sha256": sha(data), "pack_bytes": len(data), "chunks": len(chunks),
                      "args_bytes": len(json.dumps(args)), "job_sha256": sha(job.encode())}))


def search(a):
    q = {"verified": {"eq": True}, "rentable": {"eq": True}, "rented": {"eq": False}, "type": "on-demand",
         "num_gpus": {"eq": 1}, "gpu_ram": {"gte": 23000}, "reliability": {"gte": 0.98},
         "cuda_max_good": {"gte": 12.8}, "disk_space": {"gte": 60}, "inet_down": {"gte": 300},
         "cpu_cores_effective": {"gte": 8}, "order": [["dph_total", "asc"]], "limit": 200}
    offers = call("POST", "/bundles/", q).get("offers") or []
    keep = [o for o in offers if o.get("gpu_name") in ("RTX 4090", "RTX 5090", "RTX 3090", "RTX A6000", "L40S",
                                                        "RTX 6000Ada", "A100 PCIE", "A100 SXM4", "L40")]
    for o in keep[: a.n]:
        print(json.dumps({k: o.get(k) for k in ("id", "gpu_name", "gpu_ram", "dph_total", "reliability", "inet_down",
                                                 "cpu_cores_effective", "cpu_ram", "disk_space", "cuda_max_good",
                                                 "total_flops", "geolocation", "machine_id")}))


def create(a):
    args = json.loads(Path(a.args).read_text())
    if a.dryrun:
        args[2] = "export DRYRUN=1\n" + args[2]
    body = {"client_id": "me", "image": IMAGE, "disk": 60, "label": a.label, "runtype": "args", "args": args,
            "target_state": "running"}
    r = call("PUT", f"/asks/{a.offer}/", body, timeout=120)
    print(json.dumps({"success": r.get("success"), "new_contract": r.get("new_contract"), "error": r.get("error"),
                      "msg": r.get("msg"), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))


def status(a):
    r = call("GET", f"/instances/{a.id}/")
    i = r.get("instances") or {}
    if isinstance(i, list):
        i = i[0] if i else {}
    print(json.dumps({k: i.get(k) for k in ("id", "label", "actual_status", "intended_status", "cur_state",
                                             "status_msg", "gpu_name", "dph_total", "start_date", "duration",
                                             "image_uuid", "machine_id")}))


def logs(a):
    r = call("PUT", f"/instances/request_logs/{a.id}/", {"tail": str(a.tail)})
    url = r.get("result_url")
    assert url, {k: r.get(k) for k in ("success", "error", "msg")}
    text = None
    for _ in range(12):
        time.sleep(5)
        try:
            with urllib.request.urlopen(url, timeout=60) as x:
                text = x.read().decode("utf-8", "replace")
            break
        except Exception:
            continue
    assert text is not None, "log not ready"
    Path(a.out).write_text(text)
    lines = text.splitlines()
    shown = [ln for ln in lines if len(ln) < 400]
    print(f"{len(lines)} lines; last {a.show} short lines:")
    print("\n".join(shown[-a.show:]))


def fetch(a):
    lines = Path(a.log).read_text().splitlines()
    b = next(i for i, ln in enumerate(lines) if "RESULTS-BEGIN" in ln)
    e = next(i for i, ln in enumerate(lines) if "RESULTS-END" in ln and i > b)
    want = lines[b].split("RESULTS-BEGIN")[1].split()[0]
    data = base64.b64decode("".join(lines[b + 1:e]))
    assert sha(data) == want, (sha(data), want)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.tar.gz").write_bytes(data)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as t:
        t.extractall(out, filter="data")
        names = t.getnames()
    print(json.dumps({"results_sha256": want, "sha_ok": True, "bytes": len(data), "files": len(names)}))


def destroy(a):
    r = call("DELETE", f"/instances/{a.id}/")
    print(json.dumps({"destroy": r.get("success"), "msg": r.get("msg")}))
    time.sleep(5)
    ids = [i.get("id") for i in (call("GET", "/instances/").get("instances") or [])]
    print(json.dumps({"still_listed": int(a.id) in ids}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pack", "search", "create", "status", "logs", "fetch", "destroy"])
    ap.add_argument("--out")
    ap.add_argument("--offer")
    ap.add_argument("--args")
    ap.add_argument("--label", default="claude-vread-run1")
    ap.add_argument("--dryrun", action="store_true")
    ap.add_argument("--id")
    ap.add_argument("--tail", type=int, default=20000)
    ap.add_argument("--show", type=int, default=30)
    ap.add_argument("--log")
    ap.add_argument("--n", type=int, default=12)
    a = ap.parse_args()
    {"pack": pack, "search": search, "create": create, "status": status, "logs": logs, "fetch": fetch,
     "destroy": destroy}[a.cmd](a)


if __name__ == "__main__":
    main()
