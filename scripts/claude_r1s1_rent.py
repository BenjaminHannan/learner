#!/usr/bin/env python3
"""R1 stage 1 rental control (steals-8 thread, 2026-10-20): one vast.ai job, run from the cloud container over HTTPS.

DRAFT. Adapted from scripts/claude_vread2_rent.py (copied and changed, not imported). Follows
design/v3/30-modes/330-rent-kit.md and design/steals-2026-10-17/R1-STAGE1-BID.md. The agent proxy adds the vast key to
console.vast.ai requests; this script never reads or prints a key and prints only chosen fields of each API reply.
Nothing here books anything by itself: `create` prints the request and sends it only with --yes.

  pack    --stage {1a,1b} [--flop-budget F] [--seal REL] [--price REL] [--allow-dirty] --out DIR
              pack.tar.xz (code, card, seal, data at HEAD) + SEAL-pack.sha256.txt + args.json
              1a: timing smoke, needs --flop-budget; 1b: the sealed card, refuses --flop-budget and needs the card,
              a SEAL file that matches the card and the runner, and the PRICE.json (from the runner's `price` on 1a's
              runs) that fixes F, all committed
  search  [--n 12] [--max-dph 0.8]    1 RTX 5090, on-demand, verified, reliability >= 0.98 (read-only)
  create  --offer ID --args DIR/args.json [--label L] [--dryrun] [--yes]
              without --yes: prints the request, sends nothing
  status  --id ID
  cost    --id ID [--stage S]         dph x uptime = running dollars against the stage's hard stop (exit 3 when reached)
  logs    --id ID --out FILE
  waitlog --id ID [--stage S] [--max-min 360]
              exit 0 DONE, 2 job FAIL, 3 HARD STOP (instance stopped), 4 not running after 6 min, 5 no new log line
              for 10 min, 6 timeout or instance gone, 7 price unreadable (instance stopped)
  pull    --id ID --out RUNDIR [--with-ckpt]   export files read back with vast execute + cat, sha256 checked; writes
              RUNDIR/PULL_OK.json only when every check passed
  stop    --id ID
  destroy --id ID (--pulled RUNDIR | --abandon)   refuses without a passed pull (or --abandon for nothing-to-pull,
              e.g. never started); only for labels this thread created; confirms the instance is gone
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
API = "https://console.vast.ai/api/v0"
IMAGE = "pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel"
TORCH_PIN = "2.11.0"                       # rent kit TORCH VERSION rule: training jobs pin torch 2.11.0
LABEL_PREFIX = "claude-steals8-r1s1-"
STAGES = ("1a", "1b")
HARD_STOP = {"1a": 0.30, "1b": 2.50}       # dollars, bid section 4
JOB_TIMEOUT = {"1a": "45m", "1b": "330m"}
RUNNER = "scripts/premonition_steals_r1_stage1.py"
CARD = "design/steals-2026-10-17/R1-STAGE1-CARD.md"
SEAL_DEFAULT = "artifacts/claude-steals-20261017/r1-stage1/SEAL.sha256.txt"
PRICE_DEFAULT = "artifacts/claude-steals-20261017/r1-stage1/PRICE.json"
CODE_DIRS = ["premonition", "learnlab", "memorylab"]
DATA_DIRS = ["data/tokenizer", "data/english/raw", "data/village/patterns"]
CHUNK = 100_000
MAX_ARGS_BYTES = 1_800_000                 # exec argument limit is about 2 MB; refuse a bigger pack
START_MIN = 6                              # rent kit: not running within 6 min -> destroy and retry
WATCHDOG_MIN = 10                          # rent kit: no new log line for 10 min -> watchdog
DONE_MARK, FAIL_MARKS = "=== R1S1 DONE", ("=== R1S1 FAIL", "=== R1S1-FAIL")
PULL_OK = "PULL_OK.json"

JOB = r'''# R1 stage 1 rental job (steals-8 thread, 2026-10-20), from scripts/claude_r1s1_rent.py.
set -u
PACK_SHA=__PACK_SHA__
STAGE=__STAGE__
TORCH_PIN=__TORCH_PIN__
SEAL_REL=__SEAL_REL__
J=${JOBDIR:-/job}
ROOT=$J/tree
OUT=$ROOT/out/$STAGE
RUNNER=scripts/premonition_steals_r1_stage1.py
say() { echo "=== $* $(date -u +%FT%TZ)"; }
mkdir -p "$J/checks" "$J/export" "$ROOT" && cd "$J" || exit 1
finish() {   # $1 = DONE or FAIL
  kill $TICK 2>/dev/null
  cd "$J"
  rm -rf export/* b64
  [ -d "$OUT" ] && tar -czf export/out.tar.gz --exclude=ckpt -C "$ROOT/out" "$STAGE" -C "$J" checks 2>/dev/null
  [ -d "$OUT/ckpt" ] && tar -czf export/ckpt.tar.gz -C "$ROOT/out" "$STAGE/ckpt" 2>/dev/null
  [ -f export/out.tar.gz ] || tar -czf export/out.tar.gz -C "$J" checks 2>/dev/null
  echo "$1 rc=${RC:-na}" > export/STATUS.txt
  (cd export && sha256sum out.tar.gz ckpt.tar.gz 2>/dev/null > MANIFEST.sha256)
  mkdir -p b64/big b64/small
  for f in export/out.tar.gz export/ckpt.tar.gz; do
    [ -f "$f" ] || continue
    n=$(basename "$f")
    base64 -w 76 "$f" > "b64/$n.b64"
    split -b 8000000 -d -a 3 "b64/$n.b64" "b64/big/$n.b64.p"
    split -b 1000000 -d -a 3 "b64/$n.b64" "b64/small/$n.b64.p"
  done
  (cd b64 && wc -c big/* small/*) > export/PARTS.txt
  say "MANIFEST"; cat export/MANIFEST.sha256
  say "PARTS $(ls b64/big | wc -l) big, $(ls b64/small | wc -l) small"
  say "R1S1 $1"
  sleep 14400
  exit 0
}
fail() { say "R1S1-FAIL $*"; finish FAIL; }
(while true; do sleep 120; echo "=== TICK $(date -u +%H:%M:%S) | $(tail -qn1 "$J/checks/run.out" 2>/dev/null | cut -c1-120) | kb=$(du -sk "$J" 2>/dev/null | cut -f1)"; done) &
TICK=$!
say "R1S1 START stage $STAGE"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | tee checks/gpu.txt
echo "cpus $(nproc)"; free -g | head -2; df -h / | tail -1
printf '%s' "$@" | base64 -d > pack.tar.xz
echo "$PACK_SHA  pack.tar.xz" | sha256sum -c || fail "pack sha256"
python3 -c "import tarfile; tarfile.open('pack.tar.xz', 'r:xz').extractall('tree')" || fail "pack untar"
cd "$ROOT" || fail "no tree"
sha256sum -c SEAL-pack.sha256.txt > "$J/checks/pack_files.txt" 2>&1 || { tail -5 "$J/checks/pack_files.txt"; fail "file sha256"; }
echo "pack files ok: $(wc -l < "$J/checks/pack_files.txt")"
TORCH_CHECK='import torch,sys;ok=torch.cuda.is_available();print("torch",torch.__version__,"cuda",torch.version.cuda,ok,torch.cuda.get_device_name(0) if ok else "-");sys.exit(0 if ok else 1)'
python3 -c "$TORCH_CHECK" 2>&1 | tee "$J/checks/torch_image.txt"
if [ "$TORCH_PIN" != none ]; then
  PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "torch==$TORCH_PIN" > "$J/checks/pip.log" 2>&1 \
    || { tail -5 "$J/checks/pip.log"; fail "pip torch"; }
  pip uninstall -y torchvision torchaudio >> "$J/checks/pip.log" 2>&1
fi
python3 -c "$TORCH_CHECK" 2>&1 | tee "$J/checks/torch.txt"
[ "${PIPESTATUS[0]}" = 0 ] || fail "torch/cuda check"
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1)
[ "${used:-0}" -gt 2000 ] && fail "GPU busy: $used MiB in use before any run"
export PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
[ "${DRYRUN:-0}" = 1 ] && { say "DRYRUN stop"; finish DONE; }
say "BUILD"
python3 -B $RUNNER build --root "$ROOT" --workers "$(nproc)" > "$J/checks/build.out" 2> "$J/checks/build.err" \
  || { tail -5 "$J/checks/build.err"; fail "build"; }
DATA_REL=$(grep '^{' "$J/checks/build.out" | tail -1 | python3 -c "import json,sys;print(json.loads(sys.stdin.read())['data_rel'])")
[ -n "$DATA_REL" ] || fail "no data_rel in build output"
echo "data_rel $DATA_REL"
mkdir -p "$OUT"
__SEAL_COPY__
say "RUN stage $STAGE"
timeout __TIMEOUT__ python3 -B $RUNNER run --root "$ROOT" --data-rel "$DATA_REL" --out "$OUT" __RUN_FLAGS__ 2>&1 | tee "$J/checks/run.out"
RC=${PIPESTATUS[0]}
[ "$RC" = 0 ] || fail "run rc=$RC"
python3 -B $RUNNER verify --out "$OUT" || fail "manifest verify on the box"
grep -m1 Verdict "$OUT/RUN-NOTE.md"
finish DONE
'''


# ----------------------------------------------------------------------------- HTTP
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


# ----------------------------------------------------------------------------- pack
def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)


def listed(allow_dirty):
    """Files to pack: git-tracked under the code and data dirs (plus untracked, not ignored, with --allow-dirty)."""
    cmd = ["ls-files", "-z", "--cached"] + (["--others", "--exclude-standard"] if allow_dirty else [])
    out = git(*cmd, "--", *CODE_DIRS, *DATA_DIRS).stdout.decode().split("\0")
    return sorted({f for f in out if f and not f.endswith(".pyc") and "__pycache__" not in f})


def check_head(files, allow_dirty):
    """Every packed file must equal its blob at HEAD. Returns the dirty list (empty unless --allow-dirty)."""
    dirty = []
    for f in files:
        blob = git("show", f"HEAD:{f}")
        if blob.returncode != 0 or blob.stdout != (REPO / f).read_bytes():
            dirty.append(f)
    if dirty and not allow_dirty:
        raise SystemExit(f"{len(dirty)} file(s) differ from HEAD or are not committed, e.g. {dirty[:5]}")
    return dirty


def parse_seal(text):
    return {ln.split()[1]: ln.split()[0] for ln in text.splitlines() if len(ln.split()) >= 2}


def check_card_seal(seal_rel, price_rel):
    """1b: the card, the seal and the price exist at HEAD; the seal holds the sha256 of the card and of the runner."""
    for f in (CARD, seal_rel, price_rel):
        if not (REPO / f).is_file():
            raise SystemExit(f"stage 1b needs {f}, which does not exist")
    check_head([CARD, seal_rel, price_rel, RUNNER], False)
    if not json.loads((REPO / price_rel).read_text()).get("flop_budget"):
        raise SystemExit(f"{price_rel} holds no flop_budget")
    sealed = parse_seal((REPO / seal_rel).read_text())
    for f in (CARD, RUNNER):
        if sealed.get(f) != sha((REPO / f).read_bytes()):
            raise SystemExit(f"{seal_rel} does not match {f} (sealed {sealed.get(f)}); refusing to pack stage 1b")


def make_job(stage, pack_sha, flop, seal_rel, torch_pin, price_rel=PRICE_DEFAULT):
    if stage == "1a":
        flags, seal_copy = f"--flop-budget {float(flop)!r} --unsealed --seeds 0", ""
    else:
        flags = f'--seeds 0 1 2 --price "$ROOT/{price_rel}"'
        seal_copy = f'cp "$ROOT/{seal_rel}" "$OUT/SEAL.sha256.txt" || fail "seal copy"'
    text = JOB
    for key, val in (("__PACK_SHA__", pack_sha), ("__STAGE__", stage), ("__TORCH_PIN__", torch_pin),
                     ("__SEAL_REL__", seal_rel if stage == "1b" else "-"), ("__SEAL_COPY__", seal_copy),
                     ("__TIMEOUT__", JOB_TIMEOUT[stage]), ("__RUN_FLAGS__", flags)):
        text = text.replace(key, val)
    return text


def pack(a):
    stage = a.stage
    if stage == "1a":
        if a.flop_budget is None:
            raise SystemExit("stage 1a needs --flop-budget F")
        if not a.flop_budget > 0:
            raise SystemExit("--flop-budget must be positive")
    else:
        if a.flop_budget is not None:
            raise SystemExit("stage 1b is the sealed card: the card fixes F, --flop-budget is refused")
        if a.allow_dirty:
            raise SystemExit("--allow-dirty is for the 1a smoke only")
        check_card_seal(a.seal, a.price)
    files = listed(a.allow_dirty)
    extra = [CARD] if (REPO / CARD).is_file() else []
    if stage == "1b":
        extra += [a.seal, a.price]
    files = sorted(set(files) | {RUNNER, *extra})
    for f in files:
        if not (REPO / f).is_file():
            raise SystemExit(f"{f} does not exist")
    dirty = check_head(files, a.allow_dirty)
    head = git("rev-parse", "HEAD").stdout.decode().strip()
    seal = "".join(f"{sha((REPO / f).read_bytes())}  {f}\n" for f in files)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        def norm(i):
            i.uid = i.gid = 0
            i.uname = i.gname = ""
            i.mtime = 0
            return i
        for f in files:
            t.add(REPO / f, arcname=f, filter=norm)
        info = tarfile.TarInfo("SEAL-pack.sha256.txt")
        info.size, info.mtime = len(seal.encode()), 0
        t.addfile(info, io.BytesIO(seal.encode()))
    data = buf.getvalue()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pack.tar.xz").write_bytes(data)
    (out / "SEAL-pack.sha256.txt").write_text(seal)
    job = make_job(stage, sha(data), a.flop_budget, a.seal, a.torch, a.price)
    b64 = base64.b64encode(data).decode()
    args = ["bash", "-c", job, f"r1s1-{stage}"] + [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
    size = len(json.dumps(args))
    if size > MAX_ARGS_BYTES:
        raise SystemExit(f"args are {size} bytes, over {MAX_ARGS_BYTES}; shrink the pack")
    (out / "args.json").write_text(json.dumps(args))
    print(json.dumps({"stage": stage, "head": head, "dirty": dirty, "pack_sha256": sha(data), "pack_bytes": len(data),
                      "files": len(files), "chunks": len(args) - 4, "args_bytes": size,
                      "flop_budget": a.flop_budget}))


# ----------------------------------------------------------------------------- search / create
def search(a):
    q = {"verified": {"eq": True}, "rentable": {"eq": True}, "rented": {"eq": False}, "type": "on-demand",
         "num_gpus": {"eq": 1}, "gpu_name": {"eq": "RTX 5090"}, "gpu_ram": {"gte": 30000},
         "reliability": {"gte": 0.98}, "cuda_max_good": {"gte": 12.8}, "disk_space": {"gte": 60},
         "inet_down": {"gte": 200}, "cpu_cores_effective": {"gte": 8}, "order": [["dph_total", "asc"]], "limit": 100}
    offers = call("POST", "/bundles/", q).get("offers") or []
    keep = [o for o in offers if o.get("gpu_name") == "RTX 5090" and (o.get("dph_total") or 0) <= a.max_dph]
    for o in keep[: a.n]:
        row = {k: o.get(k) for k in ("id", "gpu_name", "gpu_ram", "dph_total", "reliability", "inet_down",
                                     "cpu_cores_effective", "cpu_ram", "disk_space", "cuda_max_good",
                                     "geolocation", "machine_id")}
        dph = o.get("dph_total") or 0
        row["hours_to_stop"] = {s: round(HARD_STOP[s] / dph, 2) if dph else None for s in STAGES}
        print(json.dumps(row))


def job_stage(args):
    m = re.search(r"^STAGE=(1a|1b)$", args[2], re.M) if len(args) > 2 else None
    if not m:
        raise SystemExit("args.json does not look like this controller's pack (no STAGE= line)")
    return m.group(1)


def create(a):
    args = json.loads(Path(a.args).read_text())
    stage = job_stage(args)
    label = a.label or LABEL_PREFIX + stage
    if label != LABEL_PREFIX + stage:
        raise SystemExit(f"label must be {LABEL_PREFIX}{stage} for this pack, got {label}")
    if not str(a.offer).isdigit():
        raise SystemExit("--offer must be a numeric vast offer id")
    if a.dryrun:
        args[2] = "export DRYRUN=1\n" + args[2]
    body = {"client_id": "me", "image": IMAGE, "disk": a.disk, "label": label, "runtype": "args", "args": args,
            "target_state": "running"}
    if not a.yes:
        shown = {**body, "args": f"<bash -c, job script of {len(args[2])} chars, stage {stage}, "
                                 f"{len(args) - 4} base64 chunks; job sha256 {sha(args[2].encode())[:16]}>"}
        print(json.dumps({"sent": False, "would_send": {"method": "PUT", "path": f"/asks/{a.offer}/", "body": shown},
                          "hard_stop_usd": HARD_STOP[stage], "dryrun": a.dryrun,
                          "note": "nothing was sent; repeat with --yes to rent"}, indent=1))
        return
    live = [i for i in (call("GET", "/instances/").get("instances") or []) if i.get("label") == label]
    if live:
        print(json.dumps({"sent": False, "DUPLICATE": [i.get("id") for i in live]}))
        raise SystemExit(1)
    r = call("PUT", f"/asks/{a.offer}/", body, timeout=120)
    print(json.dumps({"sent": True, "success": r.get("success"), "new_contract": r.get("new_contract"),
                      "error": r.get("error"), "msg": r.get("msg"),
                      "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))


# ----------------------------------------------------------------------------- status / cost / logs
def inst(i):
    r = call("GET", f"/instances/{i}/")
    x = r.get("instances") or {}
    return (x[0] if x else {}) if isinstance(x, list) else x


def status(a):
    x = inst(a.id)
    print(json.dumps({k: x.get(k) for k in ("id", "label", "actual_status", "intended_status", "cur_state",
                                             "status_msg", "gpu_name", "dph_total", "start_date", "duration",
                                             "machine_id")}))


def stage_of(label, given=None):
    if given:
        return given
    m = re.fullmatch(re.escape(LABEL_PREFIX) + r"(1a|1b)", label or "")
    if not m:
        raise SystemExit(f"cannot tell the stage from label {label!r}; pass --stage")
    return m.group(1)


def running_cost(x, now, floor_hours=0.0):
    """dph x uptime. Uptime is now - start_date from the status reply (the vast `duration` field if no start_date),
    never less than `floor_hours`. After a stop this keeps counting wall time, so it is an upper bound."""
    dph = x.get("dph_total")
    start = x.get("start_date")
    hours = (now - float(start)) / 3600 if start is not None else (x.get("duration") or 0) / 3600
    hours = max(hours, floor_hours, 0.0)
    return {"dph": dph, "hours": hours, "usd": None if dph is None else float(dph) * hours}


def over_stop(usd, stage):
    return usd is not None and usd >= HARD_STOP[stage]


def cost(a):
    x = inst(a.id)
    stage = stage_of(x.get("label"), a.stage)
    c = running_cost(x, time.time())
    over = over_stop(c["usd"], stage)
    print(json.dumps({"id": a.id, "label": x.get("label"), "stage": stage, "status": x.get("actual_status"),
                      "dph": c["dph"], "uptime_h": round(c["hours"], 3),
                      "usd": None if c["usd"] is None else round(c["usd"], 4), "hard_stop_usd": HARD_STOP[stage],
                      "over": over}))
    if c["usd"] is None or over:
        raise SystemExit(3)


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


def progress_key(text):
    """The log's last lines with the clock stripped from heartbeat lines: it changes only when the job makes progress
    (a new runner line, or the job directory growing)."""
    lines = [re.sub(r"^=== TICK \d\d:\d\d:\d\d ", "TICK ", ln) for ln in text.splitlines()[-6:]]
    return "\n".join(lines)


def stop_instance(i):
    return call("PUT", f"/instances/{i}/", {"state": "stopped"})


def waitlog(a):
    """Poll every --poll seconds until the job says DONE / FAIL. Stops (not destroys) the instance and exits 3 when the
    running dollars reach the stage's hard stop. Other exits: see the module docstring."""
    t0 = time.time()
    first = inst(a.id)
    stage = stage_of(first.get("label"), a.stage)
    key, changed, ever_running, blind = None, t0, False, 0
    while True:
        now = time.time()
        x = inst(a.id)
        state = x.get("actual_status")
        ever_running = ever_running or state == "running"
        c = running_cost(x, now)
        blind = blind + 1 if c["usd"] is None else 0
        text = log_text(a.id) if state == "running" else ""
        lines = text.splitlines()
        done = any(DONE_MARK in ln for ln in lines)
        failed = [ln for ln in lines if any(m in ln for m in FAIL_MARKS)]

        def out(code, tag, **extra):
            print(json.dumps({"exit": code, "event": tag, "usd": None if c["usd"] is None else round(c["usd"], 4),
                              "hard_stop_usd": HARD_STOP[stage], "status": state,
                              "waited_min": round((now - t0) / 60, 1), **extra}))
            raise SystemExit(code)
        if over_stop(c["usd"], stage):
            r = stop_instance(a.id)
            out(3, "HARD-STOP", stopped=r.get("success"), job_done=done)
        if blind >= 3:
            r = stop_instance(a.id)
            out(7, "COST-UNKNOWN", stopped=r.get("success"))
        if done:
            out(0, "DONE", found=[ln for ln in lines if DONE_MARK in ln][-1:])
        if failed:
            out(2, "JOB-FAIL", found=failed[-3:])
        if state in ("exited", "stopped", "offline") and ever_running:
            out(6, "INSTANCE-ENDED")
        if state != "running" and not ever_running and now - t0 > START_MIN * 60:
            out(4, "NOT-RUNNING", note="destroy by exact id and try another host")
        if state == "running":
            k = progress_key(text)
            if k != key:
                key, changed = k, now
            elif now - changed > WATCHDOG_MIN * 60:
                out(5, "WATCHDOG", note="no new log line for 10 min")
        if now - t0 > a.max_min * 60:
            out(6, "TIMEOUT")
        time.sleep(a.poll)


# ----------------------------------------------------------------------------- pull
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


def safe_extract(path, dest, mode):
    with tarfile.open(path, mode) as t:
        if hasattr(tarfile, "data_filter"):
            t.extractall(dest, filter="data")
        else:
            for m in t.getmembers():
                if m.name.startswith(("/", "..")) or ".." in Path(m.name).parts or not (m.isfile() or m.isdir()):
                    raise ValueError(f"unsafe tar member {m.name}")
            t.extractall(dest)


def inner_check(out, with_ckpt):
    """The runner's own MANIFEST.sha256 (inside the exported stage dir) against the extracted files. Returns
    (found, bad); ckpt/ lines are skipped unless the ckpt tarball was pulled."""
    found, bad = False, []
    for man in sorted(out.glob("*/MANIFEST.sha256")):
        found = True
        for line in man.read_text().splitlines():
            if not line.strip():
                continue
            digest, name = line.split(maxsplit=1)
            if name.startswith("ckpt/") and not with_ckpt:
                continue
            p = man.parent / name
            if not p.is_file() or sha(p.read_bytes()) != digest:
                bad.append(f"{man.parent.name}/{name}")
    return found, bad


def pull(a):
    """MANIFEST, STATUS, PARTS and every base64 part of the export via execute + cat; join, decode, sha256 check,
    extract, then the runner's inner manifest. PULL_OK.json is written only if all of it passed."""
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / PULL_OK).unlink(missing_ok=True)
    man = (exec_cat(a.id, "/job/export/MANIFEST.sha256") or b"").decode()
    parts = (exec_cat(a.id, "/job/export/PARTS.txt") or b"").decode()
    job_status = (exec_cat(a.id, "/job/export/STATUS.txt") or b"").decode().strip()
    (out / "MANIFEST.sha256").write_text(man)
    (out / "PARTS.txt").write_text(parts)
    (out / "STATUS.txt").write_text(job_status + "\n")
    want = dict(reversed(ln.split(None, 1)) for ln in man.splitlines() if ln.strip())
    sizes = {p: int(n) for n, p in (ln.split() for ln in parts.splitlines() if ln.strip()) if p != "total"}
    skipped = [] if a.with_ckpt else [n for n in want if n == "ckpt.tar.gz"]
    res = {}
    for name, h in sorted(want.items()):
        if name in skipped:
            continue
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
    tar_ok = bool(res) and "out.tar.gz" in res and all(v["sha_ok"] for v in res.values())
    inner_found, inner_bad = False, []
    if tar_ok:
        safe_extract(out / "out.tar.gz", out, "r:gz")
        if a.with_ckpt and "ckpt.tar.gz" in res:
            safe_extract(out / "ckpt.tar.gz", out, "r:gz")
        inner_found, inner_bad = inner_check(out, a.with_ckpt)
    job_done = job_status.startswith("DONE")
    inner_ok = not inner_bad and (inner_found or not job_done)
    ok = tar_ok and inner_ok and bool(job_status)
    print(json.dumps({"all_sha_ok": tar_ok, "inner_manifest_found": inner_found, "inner_bad": inner_bad,
                      "job_status": job_status, "ckpt_skipped": bool(skipped), "pull_ok": ok}))
    if ok:
        (out / PULL_OK).write_text(json.dumps({"id": int(a.id), "ok": True, "job_status": job_status,
                                               "files": sorted(res), "inner_manifest_found": inner_found,
                                               "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
    else:
        raise SystemExit(1)


# ----------------------------------------------------------------------------- stop / destroy
def stop(a):
    r = stop_instance(a.id)
    print(json.dumps({"stop": r.get("success"), "msg": r.get("msg")}))


def pulled_ok(path, i):
    f = Path(path) / PULL_OK
    try:
        d = json.loads(f.read_text())
    except Exception:
        return False
    return d.get("ok") is True and d.get("id") == int(i)


def destroy(a):
    if not a.abandon and not (a.pulled and pulled_ok(a.pulled, a.id)):
        raise SystemExit(f"refusing to destroy {a.id}: no passed pull ({PULL_OK}) for it in {a.pulled!r}; run `pull` "
                         "first, or pass --abandon if there is nothing to pull")
    label = inst(a.id).get("label") or ""
    if not label.startswith(LABEL_PREFIX):
        raise SystemExit(f"refusing to destroy {a.id}: label {label!r} was not created by this thread "
                         f"(must start with {LABEL_PREFIX})")
    r = call("DELETE", f"/instances/{a.id}/")
    print(json.dumps({"destroy": r.get("success"), "msg": r.get("msg"), "abandon": a.abandon}))
    time.sleep(5)
    ids = [i.get("id") for i in (call("GET", "/instances/").get("instances") or [])]
    gone = int(a.id) not in ids
    print(json.dumps({"still_listed": not gone}))
    if not gone:
        raise SystemExit(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **kw):
        p = sub.add_parser(name, **kw)
        p.set_defaults(fn=fn)
        return p
    p = add("pack", pack)
    p.add_argument("--stage", choices=STAGES, required=True)
    p.add_argument("--flop-budget", type=float, default=None)
    p.add_argument("--seal", default=SEAL_DEFAULT)
    p.add_argument("--price", default=PRICE_DEFAULT)
    p.add_argument("--torch", default=TORCH_PIN, help="torch version to pip install on the box, or `none`")
    p.add_argument("--allow-dirty", action="store_true", help="1a only: pack the working tree, not HEAD")
    p.add_argument("--out", required=True)
    p = add("search", search)
    p.add_argument("--n", type=int, default=12)
    p.add_argument("--max-dph", type=float, default=0.8)
    p = add("create", create)
    p.add_argument("--offer", required=True)
    p.add_argument("--args", required=True)
    p.add_argument("--label", default=None)
    p.add_argument("--disk", type=int, default=60)
    p.add_argument("--dryrun", action="store_true")
    p.add_argument("--yes", action="store_true", help="actually send the request (rents the machine)")
    for name, fn in (("status", status), ("cost", cost), ("logs", logs), ("waitlog", waitlog), ("pull", pull),
                     ("stop", stop), ("destroy", destroy)):
        p = add(name, fn)
        p.add_argument("--id", required=True)
        if name in ("cost", "waitlog"):
            p.add_argument("--stage", choices=STAGES, default=None)
        if name == "logs":
            p.add_argument("--out", required=True)
            p.add_argument("--tail", type=int, default=2000)
            p.add_argument("--show", type=int, default=40)
        if name == "waitlog":
            p.add_argument("--max-min", type=float, default=360)
            p.add_argument("--poll", type=float, default=120)
        if name == "pull":
            p.add_argument("--out", required=True)
            p.add_argument("--with-ckpt", action="store_true", help="also pull ckpt.tar.gz (the six checkpoints)")
        if name == "destroy":
            p.add_argument("--pulled", default=None, help="RUNDIR of a passed `pull`")
            p.add_argument("--abandon", action="store_true", help="nothing to pull (never started / failed to start)")
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
