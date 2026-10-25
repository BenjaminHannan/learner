#!/usr/bin/env python3
"""Stage-1 Vast controller (lean version of v1/rent.py's pattern; the agent proxy adds the Vast key, this never reads it).

  pack   --out DIR --env "STEPS=2000 MAXLEN=2048 ARMS=a0,a"        code + job script -> DIR/args.json
         (Loop-1L: --env "LOOP_ARMS=a,b,c LOOP_SEEDS=0,1,2,3" [--slim] [--hours 4]; create with --disk 120 for the 48 GB model)
  search [--gpu "A100 SXM4"] [--max-dph 0.7]
  create --offer ID --args DIR/args.json --label NAME --hours H     rents; the box stops itself after H hours
  status | logs ID | cat ID PATH | stop ID | destroy ID

The box runs backbone/run_box.sh from the pack, then prints '=== BB DONE' and stops itself.
Results come back with `cat` (Vast's command API), so nothing needs ssh.
"""
from __future__ import annotations

import argparse, base64, io, json, sys, tarfile, time, urllib.error, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
API = "https://console.vast.ai/api/v0"
IMAGE = "pytorch/pytorch:2.9.1-cuda12.8-cudnn9-devel"
FILES = ["backbone", "learnlab", "data/village/patterns"]
CHUNK = 100_000
BAD_MACHINES = {54987}  # 2026-10-24: never uploaded logs or command output, offline mid-run (Think-1 s0/s1)

JOB = r'''set -u
ENVLINE="__ENV__"
HOURS=__HOURS__
LABEL0="__LABEL__"
J=/job; mkdir -p $J && cd $J
if [ -f $J/.started ]; then echo "=== BB RESTART-REFUSED"; fi
self_stop() {
  python3 - <<'PY' || true
import os, urllib.request
r = urllib.request.Request("https://console.vast.ai/api/v0/instances/" + os.environ["CONTAINER_ID"] + "/", data=b'{"state": "stopped"}',
    method="PUT", headers={"Authorization": "Bearer " + os.environ["CONTAINER_API_KEY"], "Content-Type": "application/json"})
print(urllib.request.urlopen(r, timeout=30).read()[:200])
PY
}
if [ ! -f $J/.started ]; then
  touch $J/.started
  shift 0
  printf '%s' "$@" | tr -d ' ' | base64 -d > pack.tgz && mkdir -p tree && python3 -c "import tarfile;tarfile.open('pack.tgz').extractall('tree')" || { echo "=== BB FAIL unpack"; self_stop; exit 0; }
  cd tree
  echo "=== BB START $(date -u +%FT%TZ) $ENVLINE"
  ( while sleep 300; do python3 backbone/label_report.py "$LABEL0" >/dev/null 2>&1; echo "=== TICK $(date -u +%T) $(tail -c 300 out/run_box.log 2>/dev/null | tr '\n' ' ' | tail -c 200)"; done ) &
  env $ENVLINE timeout -k 30 $((HOURS*3600 - 600)) bash backbone/run_box.sh
  echo "=== BB DONE rc=$? $(date -u +%FT%TZ)"
  python3 backbone/label_report.py "$LABEL0 DONE"
fi
sleep 1200   # leave time to pull results before stopping
self_stop
sleep infinity
'''


def call(method, path, body=None, timeout=60):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return {"success": False, "http": e.code, "body": e.read().decode()[:300]}
    except Exception as e:
        return {"success": False, "error": type(e).__name__, "msg": str(e)[:200]}


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


SLIM_SKIP = ("assistant_data/data/train.jsonl", "assistant_data/data/eval.jsonl", "assistant_data/data/sample50.jsonl")


def pack(a):
    # FILES holds the whole backbone/ dir, so the Loop-1L code (backbone/loop/loop1l.py) and its data
    # (backbone/assistant_data/data/{train,eval}.jsonl, tools.json; ~2.5 MB gz, ~3.3 MB of args) ride along by default.
    # --slim leaves the jsonl data out (~0.2 MB); run_box.sh then downloads it from GitHub raw.
    skip = SLIM_SKIP if a.slim else ()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for f in FILES:
            t.add(REPO / f, arcname=f, filter=lambda i: None if "__pycache__" in i.name or i.name.endswith(".pyc") or i.name.endswith(skip) else i)
    b64 = base64.b64encode(buf.getvalue()).decode()
    job = JOB.replace("__ENV__", a.env).replace("__HOURS__", str(a.hours)).replace("__LABEL__", a.label)
    args = ["bash", "-c", job, "bb"] + [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "args.json").write_text(json.dumps(args))
    print(json.dumps({"pack_bytes": len(buf.getvalue()), "args_bytes": len(json.dumps(args)), "env": a.env, "hours": a.hours}))


def search(a):
    # best value first: Vast's DLPerf score per $/h (--sort price for cheapest first); mainland-China hosts are skipped (Hugging Face is blocked there)
    q = {"gpu_name": {"eq": a.gpu}, "num_gpus": {"eq": 1}, "gpu_ram": {"gte": a.min_vram * 1024}, "rentable": {"eq": True}, "reliability2": {"gte": a.min_rel},
         "dph_total": {"lte": a.max_dph}, "disk_space": {"gte": 80}, "inet_down": {"gte": 300}, "cuda_max_good": {"gte": 12.8}, "cpu_ram": {"gte": a.min_ram * 1024}}
    r = call("POST", "/bundles/", q)
    offers = [o for o in r.get("offers") or [] if not (o.get("geolocation") or "").endswith("CN") and o.get("machine_id") not in BAD_MACHINES]
    offers.sort(key=(lambda o: o["dph_total"]) if a.sort == "price" else (lambda o: -(o.get("dlperf_per_dphtotal") or 0)))
    for o in offers[:a.n]:
        print(o["id"], o["gpu_name"], round(o["dph_total"], 3), "$/h", "dlperf/$", round(o.get("dlperf_per_dphtotal") or 0), "rel", round(o.get("reliability2") or 0, 4),
              "machine", o.get("machine_id"), round(o["gpu_ram"] / 1024), "GB", round((o.get("cpu_ram") or 0) / 1024), "GB-RAM", o.get("cpu_cores_effective"), round(o.get("inet_down", 0)), o.get("geolocation"))


def create(a):
    args = json.loads(Path(a.args).read_text())
    body = {"client_id": "me", "image": IMAGE, "disk": a.disk, "label": a.label, "runtype": "args", "args": args, "target_state": "running"}
    r = call("PUT", f"/asks/{a.offer}/", body, timeout=120)
    print(json.dumps({k: r.get(k) for k in ("success", "new_contract", "error", "msg", "http", "body")}))


def status(a):
    for i in call("GET", "/instances/").get("instances", []):
        print(i["id"], i.get("label"), i.get("gpu_name"), i.get("actual_status"), round(i.get("dph_total") or 0, 3),
              round((time.time() - (i.get("start_date") or time.time())) / 3600, 2), "h")


def logs(a):
    r = call("PUT", f"/instances/request_logs/{a.id}/", {"tail": str(a.tail)})
    url = r.get("result_url")
    if not url:
        sys.exit(f"no log url: {r}")
    for _ in range(8):
        time.sleep(4)
        try:
            print("\n".join(l[:400] for l in get(url).decode("utf-8", "replace").splitlines()[-a.show:])); return
        except Exception:
            pass
    sys.exit("log not ready")


def cat(a):
    r = call("PUT", f"/instances/command/{a.id}/", {"command": f"cat {a.path}"})
    url = r.get("result_url")
    if not url:
        sys.exit(f"no url: {r}")
    for _ in range(30):
        time.sleep(5)
        try:
            data = get(url, 300)
            (sys.stdout.buffer.write(data) if not a.out else Path(a.out).write_bytes(data)); return
        except Exception:
            pass
    sys.exit("command output not ready")


def main():
    p = argparse.ArgumentParser(); s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("pack"); x.add_argument("--out", required=True); x.add_argument("--label", default="claude-bb"); x.add_argument("--env", default=""); x.add_argument("--hours", type=int, default=3); x.add_argument("--slim", action="store_true", help="leave assistant_data/data/*.jsonl out of the pack")
    x = s.add_parser("search"); x.add_argument("--gpu", default="A100 SXM4"); x.add_argument("--max-dph", type=float, default=0.8); x.add_argument("--n", type=int, default=8); x.add_argument("--min-vram", type=int, default=0)
    x.add_argument("--min-rel", type=float, default=0.99); x.add_argument("--min-ram", type=int, default=24, help="host RAM in GB"); x.add_argument("--sort", choices=("value", "price"), default="value")
    x = s.add_parser("create"); x.add_argument("--offer", required=True); x.add_argument("--args", required=True); x.add_argument("--label", required=True); x.add_argument("--disk", type=int, default=80)
    s.add_parser("status")
    x = s.add_parser("logs"); x.add_argument("id"); x.add_argument("--tail", type=int, default=300); x.add_argument("--show", type=int, default=40)
    x = s.add_parser("cat"); x.add_argument("id"); x.add_argument("path"); x.add_argument("--out")
    for n in ("stop", "destroy"):
        x = s.add_parser(n); x.add_argument("id")
    a = p.parse_args()
    if a.cmd == "stop":
        print(call("PUT", f"/instances/{a.id}/", {"state": "stopped"}))
    elif a.cmd == "destroy":
        print(call("DELETE", f"/instances/{a.id}/"))
    else:
        globals()[a.cmd](a)


if __name__ == "__main__":
    main()
