#!/usr/bin/env python3
"""vast.ai control for the two-doors test (adapted from scripts/claude_vread2_rent.py on PR #29's branch).
The proxy adds the vast key; this script never reads or prints a key. Code goes in as a base64 pack in the
container args. Copy-back: results tar -> base64 parts, read with vast `execute` + cat, sha256 checked, before destroy.
  pack --arms A,B --out DIR | search | create --offer ID --args DIR/args.json --label L | status/logs/waitlog/pull/destroy --id ID
"""
import argparse, base64, hashlib, io, json, tarfile, time, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://console.vast.ai/api/v0"
IMAGE = "pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime"
FILES = ["gen_story.py", "model_ptr.py", "train_ptr.py", "EVAL-FORM.json", "PASS-MARKS.md"]
CHUNK = 100_000
JOB = r'''set -u
J=/job; mkdir -p $J/out $J/export; cd $J
say() { echo "=== $* $(date -u +%FT%TZ)"; }
finish() {
  cd $J; tar -czf export/results.tar.gz out
  (cd export && sha256sum results.tar.gz > MANIFEST.sha256)
  mkdir -p b64 && base64 -w 76 export/results.tar.gz > b64/r.b64 && split -b 1000000 -d -a 3 b64/r.b64 b64/r.p
  (cd b64 && wc -c r.p*) > export/PARTS.txt
  say "MANIFEST"; cat export/MANIFEST.sha256; say "TWODOORS $1"; sleep 14400; exit 0; }
say "TWODOORS START"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
printf '%s' "$@" | base64 -d > pack.tar.xz
echo "__SHA__  pack.tar.xz" | sha256sum -c || { say FAIL-pack; finish FAIL; }
python -c "import tarfile; tarfile.open('pack.tar.xz','r:xz').extractall('.')"
PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "transformers==5.18.0" accelerate > out/pip.log 2>&1 || { tail -3 out/pip.log; finish FAIL; }
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false
python -c "from huggingface_hub import snapshot_download as s; s('LiquidAI/LFM2.5-1.2B-Instruct')" || finish FAIL
sha256sum EVAL-FORM.json
for ARM in __ARMS__; do
  say "WAVE $ARM"
  PIDS=""
  for S in 0 1 2 3 4 5; do python train_ptr.py --arm $ARM --seed $S --out out > out/run-$ARM-$S.out 2>&1 & PIDS="$PIDS $!"; done
  (while true; do sleep 120; for f in out/run-$ARM-*.out; do grep -E " step " $f | tail -1 | cut -c1-120; done; done) & TICK=$!
  wait $PIDS; kill $TICK 2>/dev/null
  for f in out/run-$ARM-*.out; do grep -E "Traceback|Error" $f | head -3; grep RESULT-JSON $f | cut -c1-400; done
done
finish DONE
'''


def call(method, path, body=None, timeout=60):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try: d = json.loads(e.read().decode() or "{}")
        except Exception: d = {}
        return {"success": False, "http": e.code, "error": d.get("error"), "msg": d.get("msg")}


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def pack(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        for f in FILES: t.add(HERE / f, arcname=f)
    data = buf.getvalue(); h = hashlib.sha256(data).hexdigest()
    job = JOB.replace("__SHA__", h).replace("__ARMS__", " ".join(a.arms.split(",")))
    b64 = base64.b64encode(data).decode()
    args = ["bash", "-c", job, "twodoors"] + [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
    (out / "args.json").write_text(json.dumps(args))
    print(json.dumps({"pack_sha256": h, "bytes": len(data), "arms": a.arms}))


def search(a):
    q = {"verified": {"eq": True}, "rentable": {"eq": True}, "rented": {"eq": False}, "type": "on-demand",
         "num_gpus": {"eq": 1}, "gpu_ram": {"gte": 23000}, "reliability": {"gte": 0.98}, "cuda_max_good": {"gte": 12.8},
         "disk_space": {"gte": 40}, "inet_down": {"gte": 300}, "cpu_cores_effective": {"gte": 8},
         "order": [["dph_total", "asc"]], "limit": 100}
    offers = call("POST", "/bundles/", q).get("offers") or []
    for o in [o for o in offers if o.get("gpu_name") in (a.gpus.split(",") if a.gpus else ("RTX 3090", "RTX 4090", "RTX 3090 Ti"))][: a.n]:
        print(json.dumps({k: o.get(k) for k in ("id", "gpu_name", "dph_total", "reliability", "inet_down",
                                                 "cpu_cores_effective", "cpu_ram", "disk_space", "geolocation")}))


def create(a):
    body = {"client_id": "me", "image": IMAGE, "disk": 40, "label": a.label, "runtype": "args",
            "args": json.loads(Path(a.args).read_text()), "target_state": "running"}
    r = call("PUT", f"/asks/{a.offer}/", body, timeout=120)
    print(json.dumps({"success": r.get("success"), "new_contract": r.get("new_contract"), "error": r.get("error"),
                      "msg": r.get("msg"), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))


def inst(i):
    x = call("GET", f"/instances/{i}/").get("instances") or {}
    return (x[0] if x else {}) if isinstance(x, list) else x


def status(a):
    x = inst(a.id)
    print(json.dumps({k: x.get(k) for k in ("id", "label", "actual_status", "status_msg", "gpu_name", "dph_total",
                                             "start_date", "duration")}))


def log_text(i, tail=3000):
    url = call("PUT", f"/instances/request_logs/{i}/", {"tail": str(tail)}).get("result_url")
    for _ in range(12):
        if not url: return ""
        time.sleep(5)
        try: return get(url, 60).decode("utf-8", "replace")
        except Exception: continue
    return ""


def logs(a):
    t = log_text(a.id); Path(a.out).write_text(t) if a.out else None
    print("\n".join(t.splitlines()[-a.show:]))


def exec_cat(i, path):
    for _ in range(3):
        url = call("PUT", f"/instances/command/{i}/", {"command": f"cat {path}"}).get("result_url")
        if not url: time.sleep(10); continue
        for _ in range(36):
            time.sleep(5)
            try: return get(url, 300)
            except Exception: continue
    return None


def pull(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    man = (exec_cat(a.id, "/job/export/MANIFEST.sha256") or b"").decode()
    parts = (exec_cat(a.id, "/job/export/PARTS.txt") or b"").decode()
    want = man.split()[0] if man.strip() else None
    names = [p for n, p in (ln.split() for ln in parts.splitlines() if ln.strip()) if p != "total"]
    sizes = {p: int(n) for n, p in (ln.split() for ln in parts.splitlines() if ln.strip()) if p != "total"}
    chunks = []
    for p in sorted(names):
        b = exec_cat(a.id, f"/job/b64/{p}")
        if b is None or len(b) != sizes[p]:
            print(json.dumps({"part_fail": p})); return
        chunks.append(b)
    data = base64.b64decode(b"".join(chunks))
    ok = want is not None and hashlib.sha256(data).hexdigest() == want
    if ok:
        (out / "results.tar.gz").write_bytes(data)
        with tarfile.open(out / "results.tar.gz", "r:gz") as t: t.extractall(out, filter="data")
    print(json.dumps({"sha_ok": ok, "bytes": len(data), "parts": len(names)}))


def destroy(a):
    r = call("DELETE", f"/instances/{a.id}/")
    time.sleep(5)
    ids = [i.get("id") for i in (call("GET", "/instances/").get("instances") or [])]
    print(json.dumps({"destroy": r.get("success"), "still_listed": int(a.id) in ids}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pack", "search", "create", "status", "logs", "pull", "destroy"])
    ap.add_argument("--out"); ap.add_argument("--arms", default="A,B"); ap.add_argument("--offer"); ap.add_argument("--args")
    ap.add_argument("--label", default="claude-twodoors"); ap.add_argument("--id"); ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--show", type=int, default=40); ap.add_argument("--gpus", default="")
    a = ap.parse_args()
    {"pack": pack, "search": search, "create": create, "status": status, "logs": logs, "pull": pull, "destroy": destroy}[a.cmd](a)


if __name__ == "__main__":
    main()
