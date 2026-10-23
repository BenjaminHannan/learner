#!/usr/bin/env python3
"""V1 rental control: one vast.ai job at a time, run from the cloud container over HTTPS (adapted from scripts/claude_r1s1_rent.py,
which drove the steals R1 stage-1 boxes; same money pattern: BOX_START from `create`, wall-clock self-stop on the box, hard-stop
guard in `waitlog`, stop-then-pull with sha256 checks, destroy only after a passed pull).

DRAFT until the V1 review passes. The agent proxy adds the vast key; this script never reads or prints a key.
Nothing here rents by itself: `create` prints the request and sends it only with --yes, and every rental needs Ben's own click.

  pack    --kind gs|arm|plain|multistep|multistep2 --dph D --cap C --out DIR     code at HEAD (git-tracked: premonition learnlab memorylab v1 custom_io creative
                                                      mainbrain domain skills_curriculum + tokenizer + pattern bank + data hashes)
                                                      as pack.tar.xz + args.json; the box script is v1/box/<kind>.sh from the pack
  search  [--n 12] [--max-dph 0.8] [--gpu "RTX 4090"] [--min-ram 23000]
  create  --offer ID --args DIR/args.json [--dryrun] [--yes]
  status | cost | logs | waitlog | pull | stop | destroy   (as in the steals controller)
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
PINS = json.loads((REPO / "v1/PINS.json").read_text())
IMAGE = PINS["image"]
LABEL_PREFIX = "claude-v1-"
STAGES = ("gs", "gs2", "gs3", "arm", "plain", "multistep", "multistep2")
STAGE_CAP_DEFAULT = {"gs": 1.50, "gs2": 1.00, "gs3": 0.40, "arm": 20.0, "plain": 5.0, "multistep": 6.0, "multistep2": 6.0}      # coordinator ruling: Gate S GPU run <= $1.50; an arm <= $20 (spec)
HARD_STOP = dict(STAGE_CAP_DEFAULT)
SAFETY = 0.9
EXPORT_SECONDS = 900
PREJOB_S = 900
WALL_SAFETY = 0.95
CODE_DIRS = ["premonition", "learnlab", "memorylab", "v1", "custom_io", "creative", "mainbrain", "domain", "skills_curriculum"]
DATA_FILES = ["data/tokenizer/premonition-tok-v2.json", "data/tokenizer/premonition-tok-v2.manifest.json",
              "data/village/patterns/bank-v1.json", "design/v1/data/village-SHA256SUMS.txt", "design/v1/V1_PARAMS.md"]
CHUNK = 100_000
MAX_ARGS_BYTES = 1_800_000
START_MIN = PREJOB_S // 60
STOP_MARGIN_S = 120
WATCHDOG_MIN = 10
CLOSING = re.compile(r"(?:^|\s)=== V1G (DONE|FAIL|GATE)(?=\s|$)")
PULL_OK = "PULL_OK.json"
STAGE = "gs"

JOB_BODY = r'''# V1 rental job body (v1/rent.py). Setup, version checks, then the kind's own script from the pack (v1/box/<kind>.sh).
set -u
PACK_SHA=__PACK_SHA__
STAGE=__STAGE__
DPH=__DPH__
DEADLINE_S=__DEADLINE_S__
RUN_END=$((BOX_START + DEADLINE_S))
START=$(date +%s)
J=${JOBDIR:-/job}
ROOT=$J/tree
PY=${PY:-python3}
say() { echo "=== $* $(date -u +%FT%TZ)"; }
mkdir -p "$J/checks" "$J/export" "$ROOT" && cd "$J" || exit 1
finish() {   # $1 = DONE, FAIL or GATE; the closing mark waitlog stops the box on is printed last
  cd "$J"
  say "EXPORT start"
  rm -rf export/* b64
  (cd "$ROOT/out" 2>/dev/null && tar -czf "$J/export/out.tar.gz" --exclude=wake-ckpt --exclude='*.pt' . -C "$J" checks) 2>/dev/null
  [ -f export/out.tar.gz ] || tar -czf export/out.tar.gz -C "$J" checks 2>/dev/null
  (cd "$ROOT/out" 2>/dev/null && { find . \( -name D-final.pt -o -name plain-final.pt -o -name W2.pt -o -name W1.pt -o -name Nprime.pt \) -not -path './*/wake-ckpt/*' -not -path './multistep/*'; for lt in $(ls -t ./*/wake-ckpt/step-*.pt 2>/dev/null | head -1); do echo "$lt"; echo "$lt.sha256"; done; } | tar -czf "$J/export/ckpt.tar.gz" -T -) 2>/dev/null
  say "EXPORT tarred"
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
  echo "$1 rc=${RC:-na}${DRYRUN:+ dryrun=$DRYRUN}" > export/STATUS.txt
  kill $TICK 2>/dev/null
  say "MANIFEST"; cat export/MANIFEST.sha256
  say "V1G $1"
  sleep 600
  exit 0
}
fail() { say "V1G-FAIL $*"; finish FAIL; }
(while true; do sleep "${TICK_S:-120}"; echo "=== TICK $(date -u +%H:%M:%S) | $(tail -qn1 "$J/checks/run.out" 2>/dev/null | cut -c1-120) | kb=$(du -sk "$J" 2>/dev/null | cut -f1)"; done) &
TICK=$!
say "V1G START kind $STAGE"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | tee checks/gpu.txt
echo "cpus $(nproc)"; head -3 /proc/meminfo; df -h / | tail -1
printf '%s' "$@" | base64 -d > pack.tar.xz
echo "$PACK_SHA  pack.tar.xz" | sha256sum -c || fail "pack sha256"
$PY -c "import tarfile; tarfile.open('pack.tar.xz', 'r:xz').extractall('tree')" || fail "pack untar"
cd "$ROOT" || fail "no tree"
sha256sum -c SEAL-pack.sha256.txt > "$J/checks/pack_files.txt" 2>&1 || { tail -5 "$J/checks/pack_files.txt"; fail "file sha256"; }
echo "pack files ok: $(wc -l < "$J/checks/pack_files.txt")"
PINCHK='import json,sys,torch;p=json.load(open("v1/PINS.json"));ok=torch.cuda.is_available() and torch.__version__.split("+")[0]==p["torch"] and str(torch.version.cuda)==p["cuda"];print("torch",torch.__version__,"cuda",torch.version.cuda,torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-","PINNED" if ok else "NOT PINNED");sys.exit(0 if ok else 1)'
$PY -c "$PINCHK" 2>&1 | tee "$J/checks/torch.txt"
[ "${PIPESTATUS[0]}" = 0 ] || fail "torch/cuda not the pinned build (v1/PINS.json)"
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1)
[ "${used:-0}" -gt 2000 ] && fail "GPU busy: $used MiB in use before any run"
export PYTHONUTF8=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
[ "${DRYRUN:-0}" = 1 ] && { say "DRYRUN stop"; finish DONE; }
export J ROOT PY DPH BOX_START RUN_END
bash "$ROOT/v1/box/$STAGE.sh" 2>&1 | tee -a "$J/checks/run.out"
RC=${PIPESTATUS[0]}
[ "$RC" = 0 ] || fail "box script rc=$RC"
finish DONE
'''


# The job as sent: outer wrapper.
JOB = r'''# V1 rental job, outer wrapper (V1 assembly), from scripts/claude_v1g_rent.py.
# The swarm box's money pattern: BOX_START is the epoch just before the create request (set by `create`); the box
# ledger sits one level above the job directory, so a container restart cannot reset it, and a restart never reruns.
set -u
J=${JOBDIR:-/job}
BOX_START=__BOX_START__
DPH=__DPH__
CAP=__CAP__
WALL_FROM_BOX_S=__WALL_FROM_BOX_S__
LEDGER=$(dirname "$J")/v1g-box-ledger.json
SELF_STOP_PY='import json, os, sys, urllib.request
req = urllib.request.Request(os.environ.get("V1G_TEST_VAST_API", "https://console.vast.ai/api/v0") + "/instances/" + os.environ["CONTAINER_ID"] + "/",
    data=b"{\"state\": \"stopped\"}", method="PUT",
    headers={"Authorization": "Bearer " + os.environ["CONTAINER_API_KEY"], "Content-Type": "application/json"})
try:
    body = urllib.request.urlopen(req, timeout=30).read().decode()
except Exception as error:
    print(type(error).__name__, error, getattr(error, "read", lambda: b"")()[:200]); sys.exit(1)
print(body[:200]); sys.exit(0 if json.loads(body or "{}").get("success") is True else 1)'
self_stop() {   # ask Vast to stop this instance with the container's own key (python: the image need not have curl)
  if [ -z "${CONTAINER_ID:-}" ] || [ -z "${CONTAINER_API_KEY:-}" ]; then
    echo "=== V1G SELF-STOP no container key: exiting ends the container $(date -u +%FT%TZ)"; return
  fi
  for try in 1 2 3 4 5; do
    reply=$(timeout -k 5 45 ${PY:-python3} -c "$SELF_STOP_PY" 2>&1)   # a hard limit: DNS stalls too
    if [ $? = 0 ]; then
      echo "=== V1G SELF-STOP accepted (try $try) $(date -u +%FT%TZ)"; return
    fi
    echo "=== V1G SELF-STOP refused or failed (try $try): $(printf '%s' "$reply" | head -c 200)"
    sleep 10
  done
}
if [ -f "$LEDGER" ]; then          # this container already ran the job once: a restart never reruns it
  echo "=== V1G RESTART-REFUSED: $(cat "$LEDGER") $(date -u +%FT%TZ)"; self_stop; exit 0
fi
NOW=$(date +%s)
if ! [[ "$BOX_START" =~ ^[0-9]+$ ]] || [ "$BOX_START" -gt $((NOW + 60)) ]; then
  echo "=== V1G REFUSED: BOX_START '$BOX_START' is not the create time"; self_stop; exit 0
fi
END=$((BOX_START + WALL_FROM_BOX_S))
mkdir -p "$J" && printf '{"box_start": %s, "dph": %s, "cap": %s, "job_start": %s, "wall_end": %s}\n' \
  "$BOX_START" "$DPH" "$CAP" "$NOW" "$END" > "$LEDGER" || { echo "=== V1G REFUSED: cannot write $LEDGER"; self_stop; exit 0; }
WALL_S=$((END - NOW))
if [ "$WALL_S" -le 60 ]; then echo "=== V1G REFUSED: no money left (wall ends $END)"; self_stop; exit 0; fi
if [ -n "${WALL_S_TEST:-}" ] && [ "$WALL_S_TEST" -lt "$WALL_S" ]; then WALL_S=$WALL_S_TEST; fi   # tests: only shorter
export BOX_START
cat > "$J/job.sh" <<'V1G_JOB_EOF'
__BODY__
V1G_JOB_EOF
echo "=== V1G WALL $WALL_S s, ends $(date -u -d "@$END" +%FT%TZ 2>/dev/null || echo "$END") (box start $BOX_START)"
timeout -k 30 "${WALL_S}s" bash "$J/job.sh" "$@"
RC=$?
if [ "$RC" = 124 ] || [ "$RC" = 137 ]; then echo "=== V1G SELF-STOP wall deadline rc=$RC $(date -u +%FT%TZ)"; fi
self_stop
exit 0
'''


# ----------------------------------------------------------------------------- HTTP
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
    except Exception as e:   # URLError, socket timeout, connection reset, proxy failure, bad JSON: report, never raise
        return {"success": False, "error": type(e).__name__, "msg": str(e)[:200]}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


# ----------------------------------------------------------------------------- pack
FLOOR_S = PREJOB_S + 1800            # pre-job + setup/builds: the deadline must at least cover this plus some run
FLOOR_BY_KIND = {"gs3": 900}         # the small resume re-run needs only a short run


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)


def listed():
    out = git("ls-files", "-z", "--cached", "--", *CODE_DIRS, *DATA_FILES).stdout.decode().split("\0")
    return sorted({f for f in out if f and not f.endswith(".pyc") and "__pycache__" not in f
                   and "/results/" not in f and not f.startswith(("creative/results", "custom_io/results"))})


def check_head(files):
    dirty = []
    for f in files:
        blob = git("show", f"HEAD:{f}")
        if blob.returncode != 0 or blob.stdout != (REPO / f).read_bytes():
            dirty.append(f)
    if dirty:
        raise SystemExit(f"{len(dirty)} file(s) differ from HEAD or are not committed, e.g. {dirty[:5]}")


def deadline_seconds(dph, kind):
    return int(SAFETY * HARD_STOP[kind] / dph * 3600) - EXPORT_SECONDS


def run_deadline(dph, kind):
    if not (dph and dph > 0):
        raise SystemExit("--dph (the offer's $/h) is required")
    d = deadline_seconds(dph, kind)
    if d < FLOOR_BY_KIND.get(kind, FLOOR_S):
        raise SystemExit(f"at ${dph}/h the deadline is {d} s, under the floor {FLOOR_BY_KIND.get(kind, FLOOR_S)} s; find a cheaper box or raise the cap")
    return d


def wall_seconds(dph, kind):
    return int(WALL_SAFETY * HARD_STOP[kind] / dph * 3600)


def make_job(pack_sha, kind, dph):
    wall = wall_seconds(dph, kind)
    if wall < run_deadline(dph, kind) + EXPORT_SECONDS:
        raise SystemExit(f"the wall ({wall} s) leaves no room for the export after the run deadline")
    text = JOB.replace("__BODY__", JOB_BODY).replace("__WALL_FROM_BOX_S__", str(wall)).replace("__CAP__", repr(HARD_STOP[kind]))
    for key, val in (("__PACK_SHA__", pack_sha), ("__STAGE__", kind), ("__DPH__", repr(float(dph))),
                     ("__DEADLINE_S__", str(run_deadline(dph, kind)))):
        text = text.replace(key, val)
    return text


def pack(a):
    kind = a.kind
    if kind == "arm" and not a.arm:
        raise SystemExit("--arm floor|full is required for kind arm")
    HARD_STOP[kind] = float(a.cap)
    deadline = run_deadline(a.dph, kind)
    files = listed() + [f"v1/box/{kind}.sh"]
    files = sorted(set(files))
    for f in files:
        if not (REPO / f).is_file():
            raise SystemExit(f"{f} does not exist")
    check_head(files)
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
        extra = [("ARM.env", f"ARM={a.arm}\nSTEPS={a.steps}\nCAP={a.cap}\n")] if kind == "arm" else []
        if kind == "plain":      # the plain-transformer baseline (design/v1/plain-baseline): same ARM.env shape, ARM=plain
            extra = [("ARM.env", f"ARM=plain\nSTEPS={a.steps}\nCAP={a.cap}\n")]
        for name, content in (("SEAL-pack.sha256.txt", seal), ("COMMIT", head + "\n")) + tuple(extra):
            info = tarfile.TarInfo(name)
            info.size, info.mtime = len(content.encode()), 0
            t.addfile(info, io.BytesIO(content.encode()))
    data = buf.getvalue()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pack.tar.xz").write_bytes(data)
    (out / "SEAL-pack.sha256.txt").write_text(seal)
    (out / "COMMIT").write_text(head + "\n")
    job = make_job(sha(data), kind, a.dph)
    b64 = base64.b64encode(data).decode()
    args = ["bash", "-c", job, f"v1g-{kind}"] + [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
    size = len(json.dumps(args))
    if size > MAX_ARGS_BYTES:
        raise SystemExit(f"args are {size} bytes, over {MAX_ARGS_BYTES}; shrink the pack")
    (out / "args.json").write_text(json.dumps(args))
    print(json.dumps({"kind": kind, "head": head, "pack_sha256": sha(data), "pack_bytes": len(data), "files": len(files),
                      "chunks": len(args) - 4, "args_bytes": size, "dph": a.dph, "hard_stop_usd": HARD_STOP[kind],
                      "run_deadline_s": deadline, "floor_s": FLOOR_S}))


# ----------------------------------------------------------------------------- search / create
def offer_query(gpu, min_ram):
    return {"verified": {"eq": True}, "rentable": {"eq": True}, "rented": {"eq": False}, "type": "on-demand",
            "num_gpus": {"eq": 1}, "gpu_name": {"eq": gpu}, "gpu_ram": {"gte": min_ram},
            "reliability": {"gte": 0.98}, "cuda_max_good": {"gte": 12.8}, "disk_space": {"gte": 60},
            "inet_down": {"gte": 200}, "cpu_cores_effective": {"gte": 8}, "order": [["dph_total", "asc"]], "limit": 100}


OFFER_QUERY = offer_query("RTX 4090", 23000)


def search(a):
    global OFFER_QUERY
    OFFER_QUERY = offer_query(a.gpu, a.min_ram)
    offers = call("POST", "/bundles/", OFFER_QUERY).get("offers") or []
    keep = [o for o in offers if o.get("gpu_name") == a.gpu and (o.get("dph_total") or 0) <= a.max_dph]
    for o in keep[: a.n]:
        row = {k: o.get(k) for k in ("id", "gpu_name", "gpu_ram", "dph_total", "reliability", "inet_down", "cpu_cores_effective",
                                     "cpu_ram", "disk_space", "cuda_max_good", "geolocation", "machine_id")}
        print(json.dumps(row))


def job_stage(args):
    m = re.search(r"^STAGE=(gs3|gs2|gs|arm|plain|multistep2|multistep)$", args[2], re.M) if len(args) > 2 else None
    if not m:
        raise SystemExit("args.json does not look like this controller's pack (no STAGE= line)")
    return m.group(1)


def packed_cap(args):
    m = re.search(r"^CAP=([0-9.]+)$", args[2], re.M) if len(args) > 2 else None
    if not m:
        raise SystemExit("args.json carries no CAP= line (made by another controller)")
    return float(m.group(1))


def with_box_start(job, epoch):
    if job.count("BOX_START=__BOX_START__") != 1:
        raise SystemExit("args.json has no unset BOX_START line (made by another controller, or already sent)")
    return job.replace("BOX_START=__BOX_START__", f"BOX_START={int(epoch)}")


def create(a):
    global OFFER_QUERY
    OFFER_QUERY = offer_query(a.gpu, a.min_ram)
    args = json.loads(Path(a.args).read_text())
    stage = job_stage(args)
    label = a.label or f"{LABEL_PREFIX}{stage}"
    if not label.startswith(LABEL_PREFIX):
        raise SystemExit(f"label must start with {LABEL_PREFIX}")
    if not str(a.offer).isdigit():
        raise SystemExit("--offer must be a numeric vast offer id")
    set_cap(stage, packed_cap(args))
    if a.dryrun:
        args[2] = "export DRYRUN=1\n" + args[2]
    body = {"client_id": "me", "image": IMAGE, "disk": a.disk, "label": label, "runtype": "args", "args": args, "target_state": "running"}
    if not a.yes:
        shown = {**body, "args": f"<bash -c, job script of {len(args[2])} chars, kind {stage}, {len(args) - 4} base64 chunks; job sha256 {sha(args[2].encode())[:16]}>"}
        print(json.dumps({"sent": False, "would_send": {"method": "PUT", "path": f"/asks/{a.offer}/", "body": shown},
                          "hard_stop_usd": HARD_STOP[stage], "dryrun": a.dryrun, "note": "nothing was sent; repeat with --yes to rent"}, indent=1))
        return
    listing = call("GET", "/instances/")
    if not isinstance(listing.get("instances"), list):
        raise SystemExit(f"cannot read the instance list ({listing.get('http')} {listing.get('error')}); nothing was sent")
    m = re.search(r"^DPH=([0-9.e+-]+)$", args[2], re.M)
    packed = float(m.group(1)) if m else None
    offers = [o for o in call("POST", "/bundles/", OFFER_QUERY).get("offers") or [] if o.get("id") == int(a.offer)]
    offered = offers[0].get("dph_total") if offers else None
    if offered is None:
        raise SystemExit(f"offer {a.offer} is not in the filtered listing; nothing sent")
    if packed is None or offered > packed:
        raise SystemExit(f"offer {a.offer} costs {offered} $/h; the pack was made for at most {packed}; nothing sent")
    live = [i for i in listing["instances"] if i.get("label") == label]
    if live:
        print(json.dumps({"sent": False, "DUPLICATE": [i.get("id") for i in live]}))
        raise SystemExit(1)
    box_start = int(time.time())
    args[2] = with_box_start(args[2], box_start)
    r = call("PUT", f"/asks/{a.offer}/", body, timeout=120)
    print(json.dumps({"sent": True, "success": r.get("success"), "new_contract": r.get("new_contract"), "box_start": box_start,
                      "error": r.get("error"), "msg": r.get("msg"), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))


# ----------------------------------------------------------------------------- status / cost / logs
def inst(i):
    """The instance's record; {} when Vast lists no such instance; None when the request failed (state unknown)."""
    r = call("GET", f"/instances/{i}/")
    if r.get("http") == 404:
        return {}
    if "instances" not in r:
        return None
    x = r.get("instances") or {}
    return (x[0] if x else {}) if isinstance(x, list) else x


STOPPED = ("stopped", "exited", "offline")


def stop_confirmed(i, poll=10, recheck=6):
    """Stop the instance and return only once Vast confirms it: no longer listed, or intended_status "stopped" and not
    running (without an intended_status field: a stop request accepted and a stopped state). Network errors and
    refused requests are retried, the stop request again after every `recheck` polls; it never returns unconfirmed."""
    tries, accepted = 0, False
    while True:
        tries += 1
        r = stop_instance(i)
        accepted = accepted or r.get("success") is True
        for _ in range(recheck):
            time.sleep(poll)
            x = inst(i)
            if x is None:
                continue
            state, intended = x.get("actual_status"), x.get("intended_status")
            if not x or (intended == "stopped" and state != "running") or \
                    (intended is None and accepted and state in STOPPED):
                return {"confirmed": True, "tries": tries, "status": state or "gone", "intended": intended}
        print(json.dumps({"stop_unconfirmed": i, "tries": tries, "last_request": r.get("success"),
                          "error": r.get("error")}), file=sys.stderr, flush=True)


def status(a):
    x = inst(a.id) or {}
    print(json.dumps({k: x.get(k) for k in ("id", "label", "actual_status", "intended_status", "cur_state",
                                             "status_msg", "gpu_name", "dph_total", "start_date", "duration",
                                             "machine_id")}))


def stage_of(label, given=None):
    if given:
        return given
    m = re.fullmatch(re.escape(LABEL_PREFIX) + r"(gs3|gs2|gs|arm|plain|multistep2|multistep)[a-z0-9-]*", label or "")
    if not m:
        raise SystemExit(f"cannot tell the stage from label {label!r}; pass --stage")
    return m.group(1)


def running_cost(x, now, floor_hours=0.0):
    """dph x uptime. Uptime is now - start_date from the status reply (the vast `duration` field if no start_date),
    never less than `floor_hours`. After a stop this keeps counting wall time, so it is an upper bound."""
    dph = x.get("dph_total")
    start = x.get("start_date")
    if start is None and not x.get("duration"):          # no clock: the cost is unknown, never $0
        return {"dph": dph, "hours": None, "usd": None}
    hours = (now - float(start)) / 3600 if start is not None else x["duration"] / 3600
    hours = max(hours, floor_hours, 0.0)
    return {"dph": dph, "hours": hours, "usd": None if dph is None else float(dph) * hours}


def over_stop(usd, stage):
    return usd is not None and usd >= HARD_STOP[stage]


def cost(a):
    set_cap(job_stage(json.loads(Path(a.args).read_text())), packed_cap(json.loads(Path(a.args).read_text())))
    x = inst(a.id) or {}
    stage = stage_of(x.get("label"), a.stage)
    c = running_cost(x, time.time())
    over = over_stop(c["usd"], stage)
    print(json.dumps({"id": a.id, "label": x.get("label"), "stage": stage, "status": x.get("actual_status"),
                      "dph": c["dph"], "uptime_h": None if c["hours"] is None else round(c["hours"], 3),
                      "usd": None if c["usd"] is None else round(c["usd"], 4), "hard_stop_usd": HARD_STOP[stage],
                      "over": over}))
    if c["usd"] is None or over:
        raise SystemExit(3)


def log_text(i, tail=400, tries=6):
    """The container log's tail, or None when it could not be fetched (never confused with an empty log)."""
    r = call("PUT", f"/instances/request_logs/{i}/", {"tail": str(tail)}, timeout=30)
    url = r.get("result_url")
    if not url:
        return None
    for _ in range(tries):
        time.sleep(5)
        try:
            return get(url, 30).decode("utf-8", "replace")
        except Exception:
            continue
    return None


def logs(a):
    text = log_text(a.id, a.tail)
    if text is None:
        raise SystemExit("could not fetch the log; try again")
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


def time_limit_min(dph, stage=None):
    """waitlog's limit in minutes: the hard stop's hours at `dph` plus 30 min (a larger --max-min may extend it)."""
    return HARD_STOP[stage or STAGE] / float(dph) * 60 + 30


def closing_marks(lines):
    """The job's closing marks (`=== V1G DONE|FAIL|GATE`), found only on a line of their own."""
    found = {"DONE": [], "FAIL": [], "GATE": []}
    for ln in lines:
        m = CLOSING.search(ln)
        if m:
            found[m.group(1)].append(ln)
    return found


def waitlog(a):
    """The cap guard. Each poll: the status read, then the cost check at that moment, before anything else; then the
    closing marks, the time limit, the watchdog and the start check. Three failed polls in a row (a failed read, an
    unreadable cost, any exception) stop the box. Every exit stops the box first and waits until Vast confirms it."""
    if getattr(a, "args", None):               # the CLI requires it: the cap guard uses the cap the job was packed with
        set_cap(job_stage(json.loads(Path(a.args).read_text())), packed_cap(json.loads(Path(a.args).read_text())))
    t0 = time.time()
    stage = a.stage or job_stage(json.loads(Path(a.args).read_text()))
    key, changed, ever_running, failures = None, t0, False, 0
    while True:
        try:
            x = inst(a.id)
            now = time.time()
            if x is None:
                raise RuntimeError("status read failed")
            c = running_cost(x, now)
            if c["usd"] is None:
                raise RuntimeError("cost unreadable")
            state = x.get("actual_status")

            def out(code, tag, **extra):
                _exit(a.id, code, tag, stage, t0, now, c["usd"], state, **extra)
            margin = float(c["dph"]) * (a.poll + STOP_MARGIN_S) / 3600
            if over_stop(c["usd"] + margin, stage):
                out(3, "HARD-STOP")
            failures = 0
            ever_running = ever_running or state == "running"
            if state in STOPPED:                # ended (or stopped before this watch): pull it, never destroy first
                out(6, "INSTANCE-ENDED", note="pull it; destroy only after a passed pull")
            start = x.get("start_date")
            age = now - float(start) if start is not None else now - t0
            if state != "running" and not ever_running and age > START_MIN * 60:
                out(4, "NOT-RUNNING", note="destroy by exact id and try another host")
            limit = max(time_limit_min(c["dph"], stage), a.max_min or 0)
            if now - t0 > limit * 60:
                out(6, "TIMEOUT", limit_min=round(limit, 1))
            if state == "running":
                text = log_text(a.id)
                if text is not None:            # a failed fetch neither shows a mark nor moves the watchdog
                    marks = closing_marks(text.splitlines())
                    for tag, code, name in (("DONE", 0, "DONE"), ("FAIL", 2, "JOB-FAIL"), ("GATE", 8, "GATE")):
                        if marks[tag]:          # the export is written: stop now, so only storage bills during the pull
                            out(code, name, found=marks[tag][-1:])
                    k = progress_key(text)
                    if k != key:
                        key, changed = k, now
                    elif now - changed > WATCHDOG_MIN * 60:
                        out(5, "WATCHDOG", note="no new log line for 10 min")
        except SystemExit:
            raise
        except Exception as error:              # a failed read, an unreadable cost, anything else: three in a row stop it
            failures += 1
            print(json.dumps({"poll_failure": type(error).__name__, "msg": str(error)[:200], "in_a_row": failures}),
                  file=sys.stderr, flush=True)
            if failures >= 3:
                _exit(a.id, 7, "BLIND", stage, t0, time.time(), None, None, note="three failed polls in a row")
        time.sleep(a.poll)


def _exit(i, code, tag, stage, t0, now, usd, state, **extra):
    """Every waitlog exit stops the box first and waits until Vast confirms it (`stop_confirmed`)."""
    stopped = stop_confirmed(i)
    print(json.dumps({"exit": code, "event": tag, "usd": None if usd is None else round(usd, 4),
                      "hard_stop_usd": HARD_STOP[stage], "status": state, "waited_min": round((now - t0) / 60, 1),
                      "stopped": stopped, **extra}))
    raise SystemExit(code)

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


def inner_check(out):
    """Every runner MANIFEST.sha256 (out/1a and out/1b, inside the exported stage dirs) against the extracted files,
    checkpoints included. Returns (found, bad)."""
    found, bad = False, []
    for man in sorted(out.glob("*/MANIFEST.sha256")):
        found = True
        for line in man.read_text().splitlines():
            if not line.strip():
                continue
            digest, name = line.split(maxsplit=1)
            p = man.parent / name
            if not p.is_file() or sha(p.read_bytes()) != digest:
                bad.append(f"{man.parent.name}/{name}")
    return found, bad


def pull(a):
    """STATUS first (it is written last, so empty means the export is not whole: refused), then stop the instance and
    wait until Vast confirms it, then MANIFEST, PARTS and every base64 part of the export via execute + cat; join,
    decode, sha256 check, extract, then the runner's inner manifests. PULL_OK.json is written only if all passed."""
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / PULL_OK).unlink(missing_ok=True)
    raw = exec_cat(a.id, "/job/export/STATUS.txt")
    if raw is None:
        raise SystemExit(f"could not read /job/export/STATUS.txt of {a.id} (network); run pull again")
    job_status = raw.decode().strip()
    if not job_status:
        raise SystemExit(f"/job/export/STATUS.txt of {a.id} is empty: the job has not finished its export. Wait for "
                         "waitlog's closing mark (a stuck job is recovered by hand, never by a partial pull)")
    if (inst(a.id) or {}).get("actual_status") not in STOPPED:     # no GPU billing while the parts are read
        print(json.dumps({"stopped_before_pull": stop_confirmed(a.id)}), flush=True)
    man = (exec_cat(a.id, "/job/export/MANIFEST.sha256") or b"").decode()
    parts = (exec_cat(a.id, "/job/export/PARTS.txt") or b"").decode()
    (out / "MANIFEST.sha256").write_text(man)
    (out / "PARTS.txt").write_text(parts)
    (out / "STATUS.txt").write_text(job_status + "\n")
    want = dict(reversed(ln.split(None, 1)) for ln in man.splitlines() if ln.strip())
    if getattr(a, 'only', None):
        want = {k: v for k, v in want.items() if k in a.only.split(',')}
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
    tar_ok = bool(res) and "out.tar.gz" in res and all(v["sha_ok"] for v in res.values())
    inner_found, inner_bad = False, []
    if tar_ok:
        safe_extract(out / "out.tar.gz", out, "r:gz")
        if "ckpt.tar.gz" in res:
            safe_extract(out / "ckpt.tar.gz", out, "r:gz")
        inner_found, inner_bad = inner_check(out)
    job_done = job_status.startswith("DONE") and "dryrun=1" not in job_status     # a dry run has no out/ dirs
    missing = []
    inner_ok = not inner_bad
    ok = tar_ok and inner_ok and bool(job_status)
    print(json.dumps({"all_sha_ok": tar_ok, "inner_manifest_found": inner_found, "inner_bad": inner_bad,
                      "manifest_missing": missing, "job_status": job_status, "pull_ok": ok}))
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
    x = inst(a.id)
    if x is None:
        raise SystemExit(f"cannot read instance {a.id}; nothing deleted")
    label = x.get("label") or ""
    if not label.startswith(LABEL_PREFIX):
        raise SystemExit(f"refusing to destroy {a.id}: label {label!r} was not created by this thread "
                         f"(must start with {LABEL_PREFIX})")
    r = call("DELETE", f"/instances/{a.id}/")
    print(json.dumps({"destroy": r.get("success"), "msg": r.get("msg"), "abandon": a.abandon}))
    time.sleep(5)
    listing = call("GET", "/instances/")
    if not isinstance(listing.get("instances"), list):
        print(json.dumps({"still_listed": "unknown", "error": listing.get("error")}))
        raise SystemExit(1)
    gone = int(a.id) not in [i.get("id") for i in listing["instances"]]
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
    p.add_argument("--kind", choices=STAGES, required=True)
    p.add_argument("--dph", type=float, required=True, help="the offer's $/h (sets the run's deadline)")
    p.add_argument("--cap", type=float, required=True, help="this box's dollars")
    p.add_argument("--arm", choices=("floor", "full"), default=None)
    p.add_argument("--steps", type=int, default=12000)
    p.add_argument("--out", required=True)
    p = add("search", search)
    p.add_argument("--n", type=int, default=12)
    p.add_argument("--max-dph", type=float, default=0.8)
    p.add_argument("--gpu", default="RTX 4090")
    p.add_argument("--min-ram", type=int, default=23000)
    p = add("create", create)
    p.add_argument("--offer", required=True)
    p.add_argument("--args", required=True)
    p.add_argument("--label", default=None)
    p.add_argument("--disk", type=int, default=60)
    p.add_argument("--gpu", default="RTX 4090")
    p.add_argument("--min-ram", type=int, default=23000)
    p.add_argument("--dryrun", action="store_true")
    p.add_argument("--yes", action="store_true", help="actually send the request (rents the machine)")
    for name, fn in (("status", status), ("cost", cost), ("logs", logs), ("waitlog", waitlog), ("pull", pull),
                     ("stop", stop), ("destroy", destroy)):
        p = add(name, fn)
        p.add_argument("--id", required=True)
        if name in ("cost", "waitlog"):
            p.add_argument("--stage", choices=STAGES, default=None)
            p.add_argument("--args", required=True, help="the pack's args.json: the cap is read from it")
        if name == "logs":
            p.add_argument("--out", required=True)
            p.add_argument("--tail", type=int, default=2000)
            p.add_argument("--show", type=int, default=40)
        if name == "waitlog":
            p.add_argument("--max-min", type=float, default=None)
            p.add_argument("--poll", type=float, default=120)
        if name == "pull":
            p.add_argument("--out", required=True)
            p.add_argument("--only", default=None, help="comma list of export tarballs to read (e.g. out.tar.gz)")
        if name == "destroy":
            p.add_argument("--pulled", default=None)
            p.add_argument("--abandon", action="store_true")
    a = ap.parse_args(argv)
    a.fn(a)


def set_cap(stage, cap):
    if not 0 < cap <= 40.0:
        raise SystemExit(f"cap must be in (0, 40] dollars, got {cap}")
    HARD_STOP[stage] = float(cap)


if __name__ == "__main__":
    main()
