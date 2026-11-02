#!/usr/bin/env python3
"""RLAIF-1 controller: one rented vast.ai RTX 4090, driven from the cloud container over HTTPS.

The agent proxy injects the Vast key for https://console.vast.ai; this script never reads or prints a key.
The Anthropic key for the box-side grader is read from env LEARNER_ANTHROPIC_API_KEY and passed only as an
instance env var (never written into the onstart script, never printed).

  search                          RTX 4090, verified, reliability >= 0.98, inet_down >= 500 Mbps, cheapest first
  create --offer ID [--yes] [--dryrun] [--run NAME]
                                  without --yes: print the request only. --dryrun: print the full onstart script
                                  (key redacted) and its size. Nothing is rented without --yes.
  status | logs | waitlog | pull | destroy   (all take --run, default rlaif1)

Results come back through the instance log API (no ssh): the box prints its results tarball as base64 lines
("RB64 <n> <data>") before the closing marker; waitlog saves the whole log to runs/<run>/box.log, then destroys.
`pull` reassembles runs/<run>/results.tar.gz from that log (or a fresh log fetch) and extracts it in runs/<run>/.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
API = "https://console.vast.ai/api/v0"

IMAGE = "pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime"   # same image v1/rent.py ran on Vast
LABEL = "claude-project-thread-j5hhcz-rlaif1"
KEY_ENV = "LEARNER_ANTHROPIC_API_KEY"
PIP_PKGS = "transformers peft anthropic accelerate"

CAP_USD = 2.00                 # hard cap on the rental
MARGIN_USD = 0.15              # box self-deadline and waitlog stop this far below the cap
EXPORT_S = 300                 # time reserved at the end of the box deadline for the results export
START_TIMEOUT_MIN = 20         # destroy if "=== TRAINING STARTED" has not appeared this long after create
DISK_GB = 50
MAX_ONSTART_BYTES = 1_800_000  # same ceiling v1/rent.py used for its args; the Vast limit is not documented
POLL_S = 60

STARTED = "=== TRAINING STARTED"
CLOSING = re.compile(r"(?:^|\s)=== RLAIF (DONE|FAIL)(?=\s|$)")

# ---- Box job: edit flags here. Each entry is (step name, shell command, max seconds or 0 for "until the deadline").
# Runs from the unpacked rlaif/ parent directory (so `python -m rlaif.train` works). $OUT is the box output dir.
# Steps run in order; a failing step is recorded and the next one still runs. Adapters are not exported.
HELDOUT = "rlaif/data/tasks_heldout.jsonl"
TRAIN = "rlaif/data/tasks_train.jsonl"
COMMON = "--steps 20 --tasks-per-step 8 --group 4 --seed 0 --save-every 5 --max-usd 14"
LATEST = "$(ls -d $OUT/{a}/adapter_final 2>/dev/null || ls -dv $OUT/{a}/adapter_step* 2>/dev/null | tail -1)"
STEPS = [
    ("eval_base",  f"python -m rlaif.train --eval-only --eval-grade --heldout {HELDOUT} --outdir $OUT/eval_base", 2400),
    ("train_grpo", f"python -m rlaif.train --algo grpo --train {TRAIN} {COMMON} --outdir $OUT/grpo", 4800),
    ("eval_grpo",  f"python -m rlaif.train --eval-only --eval-grade --adapter {LATEST.format(a='grpo')} --heldout {HELDOUT} --outdir $OUT/eval_grpo", 2400),
    ("train_jolt", f"python -m rlaif.train --algo jolt_plus --train {TRAIN} {COMMON} --outdir $OUT/jolt", 0),
    ("eval_jolt",  f"python -m rlaif.train --eval-only --eval-grade --adapter {LATEST.format(a='jolt')} --heldout {HELDOUT} --outdir $OUT/eval_jolt", 2400),
]
# small result files exported (names matched anywhere under $OUT, adapter dirs excluded)
RESULT_GLOBS = ["log.jsonl", "eval*.json", "eval*.jsonl", "spend.json", "*.tail.txt", "status.tsv"]
FILE_CAP_BYTES = 300_000       # each exported file is cut to its last this-many bytes
STDOUT_TAIL_LINES = 80


ONSTART = r'''#!/bin/bash
# RLAIF-1 box job (rlaif/vast.py). No `set -x`: the Anthropic key must never reach the log.
set -u
BOX_START=__BOX_START__
DEADLINE_S=__DEADLINE_S__
EXPORT_S=__EXPORT_S__
DPH=__DPH__
CAP=__CAP__
RUN_END=$((BOX_START + DEADLINE_S))
JOB=/workspace/rlaif-job
OUT=$JOB/out
say() { echo "=== $* $(date -u +%FT%TZ)"; }
mkdir -p "$JOB" "$OUT" && cd "$JOB" || { echo "=== RLAIF FAIL cannot make $JOB"; exit 0; }
if [ -z "${__KEY_ENV__:-}" ]; then   # onstart may not inherit instance env vars; Vast also writes them to /etc/environment
  v=$(grep -m1 '^__KEY_ENV__=' /etc/environment 2>/dev/null | cut -d= -f2- | tr -d '"')
  [ -n "$v" ] && export __KEY_ENV__="$v"
fi
export PYTHONUNBUFFERED=1 PYTHONUTF8=1 TOKENIZERS_PARALLELISM=false HF_HUB_DISABLE_PROGRESS_BARS=1

self_stop() {   # Vast puts a per-instance key in the container env; stopping ends GPU billing even if waitlog is not running
  for f in CONTAINER_ID CONTAINER_API_KEY; do
    [ -z "${!f:-}" ] && { v=$(grep -m1 "^$f=" /etc/environment 2>/dev/null | cut -d= -f2- | tr -d '"'); [ -n "$v" ] && export $f="$v"; }
  done
  say "SELF STOP"
  curl -s -o /dev/null -w "self-stop http %{http_code}\n" -X PUT "https://console.vast.ai/api/v0/instances/${CONTAINER_ID:-0}/" \
    -H "Authorization: Bearer ${CONTAINER_API_KEY:-}" -H 'Content-Type: application/json' -d '{"state":"stopped"}'
}
(sleep $((DEADLINE_S + EXPORT_S + 600 - ($(date +%s) - BOX_START))); self_stop) &   # last-resort watchdog

export_results() {   # prints the results tarball as base64 lines, then the closing marker (last)
  kill $TICK 2>/dev/null
  say "EXPORT start"
  mkdir -p "$JOB/export/files"
  (cd "$OUT" && find . \( -name adapter -o -name 'adapter*' -o -name 'checkpoint*' \) -prune -o -type f \( __FIND_NAMES__ \) -print) | while read -r f; do
    mkdir -p "$JOB/export/files/$(dirname "$f")"
    tail -c __FILE_CAP__ "$OUT/$f" > "$JOB/export/files/$f"
  done
  cp "$JOB/preflight.txt" "$JOB/export/files/" 2>/dev/null
  echo "$1 elapsed_s=$(( $(date +%s) - BOX_START )) dph=$DPH" > "$JOB/export/files/BOX_STATUS.txt"
  tar -czf "$JOB/results.tar.gz" -C "$JOB/export/files" . 2>/dev/null
  SHA=$(sha256sum "$JOB/results.tar.gz" | cut -d' ' -f1)
  NB=$(stat -c %s "$JOB/results.tar.gz")
  base64 -w 100 "$JOB/results.tar.gz" > "$JOB/results.b64"
  NL=$(wc -l < "$JOB/results.b64")
  echo "=== RESULTS BEGIN sha256=$SHA bytes=$NB lines=$NL"
  awk '{printf "RB64 %d %s\n", NR, $0}' "$JOB/results.b64"
  echo "=== RESULTS END"
  say "RLAIF $1"
  sleep 300      # give waitlog time to read the log, then the box stops itself (waitlog destroys it)
  self_stop
  exit 0
}

(while true; do sleep 120; echo "=== TICK $(date -u +%H:%M:%S) left=$((RUN_END - $(date +%s)))s | $(tail -qn1 "$JOB/current.out" 2>/dev/null | cut -c1-120)"; done) &
TICK=$!

say "BOX START deadline_s=$DEADLINE_S cap=\$$CAP dph=$DPH"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | tee "$JOB/preflight.txt"
printf '%s' "$@" | base64 -d > code.tar.xz   # code arrives as base64 chunks in the container args (Vast caps onstart/args strings) || { say "code decode failed"; export_results FAIL; }
tar -xJf code.tar.xz -C "$JOB" || { say "code untar failed"; export_results FAIL; }
ls "$JOB/rlaif" | head -30
[ -n "${__KEY_ENV__:-}" ] && echo "anthropic key: present" || echo "anthropic key: MISSING"
pip install -q __PIP_PKGS__ 2>&1 | tail -5
python -c "import torch,transformers,peft,anthropic;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'transformers',transformers.__version__,'peft',peft.__version__)" 2>&1 | tee -a "$JOB/preflight.txt"
[ "${PIPESTATUS[0]}" = 0 ] || { say "imports failed"; export_results FAIL; }

# run_step NAME MAXSECS CMD: bounded by the box deadline minus the export reserve; failure is recorded, never fatal
: > "$OUT/status.tsv"
run_step() {
  name=$1; maxs=$2; cmd=$3
  left=$((RUN_END - EXPORT_S - $(date +%s)))
  if [ "$left" -le 60 ]; then
    echo "SKIPPED_DEADLINE" | tee "$OUT/$name.tail.txt"; printf '%s\tSKIPPED_DEADLINE\n' "$name" >> "$OUT/status.tsv"; return
  fi
  [ "$maxs" -gt 0 ] && [ "$maxs" -lt "$left" ] && left=$maxs
  say "STEP $name start (limit ${left}s)"
  cd "$JOB"
  timeout -k 30 "${left}s" bash -c "$cmd" > "$OUT/$name.stdout" 2>&1 &
  wait $!
  rc=$?
  tail -n __TAIL_LINES__ "$OUT/$name.stdout" > "$OUT/$name.tail.txt"
  cp "$OUT/$name.tail.txt" "$JOB/current.out"
  tail -n 25 "$OUT/$name.stdout"
  if [ "$rc" = 124 ] || [ "$rc" = 137 ]; then echo "(step hit its time limit)" >> "$OUT/$name.tail.txt"; fi
  printf '%s\trc=%s\n' "$name" "$rc" >> "$OUT/status.tsv"
  say "STEP $name rc=$rc"
}
export OUT JOB
echo "__STARTED__"
__RUN_STEPS__
cat "$OUT/status.tsv"
if grep -q 'rc=[1-9]\|SKIPPED' "$OUT/status.tsv"; then say "some steps failed or were skipped (see status.tsv)"; fi
export_results DONE
'''


def sha(b):
    return hashlib.sha256(b).hexdigest()


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
    except Exception as e:      # never raise: report
        return {"success": False, "error": type(e).__name__, "msg": str(e)[:200]}


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


# ----------------------------------------------------------------------------- state
def run_dir(run):
    d = RUNS / run
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_state(run):
    p = RUNS / run / "state.json"
    if not p.is_file():
        raise SystemExit(f"no state for run {run!r} ({p}); create first")
    return json.loads(p.read_text())


def save_state(run, st):
    (run_dir(run) / "state.json").write_text(json.dumps(st, indent=1))


# ----------------------------------------------------------------------------- search
def offer_query():
    return {"verified": {"eq": True}, "rentable": {"eq": True}, "rented": {"eq": False}, "type": "on-demand",
            "num_gpus": {"eq": 1}, "gpu_name": {"eq": "RTX 4090"}, "reliability": {"gte": 0.98},
            "inet_down": {"gte": 500}, "cuda_max_good": {"gte": 12.4}, "disk_space": {"gte": DISK_GB},
            "order": [["dph_total", "asc"]], "limit": 100}


def find_offers():
    r = call("POST", "/bundles/", offer_query())
    offers = r.get("offers")
    if offers is None:
        raise SystemExit(f"offer search failed: {r.get('http')} {r.get('error')} {r.get('msg')}")
    offers = [o for o in offers if o.get("gpu_name") == "RTX 4090" and (o.get("reliability") or o.get("reliability2") or 0) >= 0.98
              and (o.get("inet_down") or 0) >= 500]
    return sorted(offers, key=lambda o: o.get("dph_total") or 9e9)


def search(a):
    offers = find_offers()
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / "last_search.json").write_text(json.dumps({str(o["id"]): o["dph_total"] for o in offers}))
    print(f"{'id':>9} {'dph':>7} {'inet_down':>9} {'reliab':>7} {'disk':>5}  location")
    for o in offers[:a.n]:
        print(f"{o['id']:>9} {o.get('dph_total', 0):>7.3f} {o.get('inet_down', 0):>9.0f} "
              f"{(o.get('reliability') or o.get('reliability2') or 0):>7.4f} {o.get('disk_space', 0):>5.0f}  {o.get('geolocation')}")
    print(f"({len(offers)} offers match; cap ${CAP_USD:.2f} total)")


# ----------------------------------------------------------------------------- job script
def deadline_seconds(dph):
    """Wall seconds from create (BOX_START) at which the box must have finished its export."""
    return int((CAP_USD - MARGIN_USD) / dph * 3600)


def pack_code():
    buf = io.BytesIO()

    def norm(i):
        i.uid = i.gid = 0
        i.uname = i.gname = ""
        i.mtime = 0
        return i
    n = 0
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        for p in sorted(HERE.rglob("*")):
            rel = p.relative_to(HERE)
            if not p.is_file() or rel.parts[0] in ("runs", "__pycache__") or "__pycache__" in rel.parts:
                continue
            if p.suffix == ".py" or (rel.parts[0] == "data" and p.suffix == ".jsonl"):
                t.add(p, arcname=f"rlaif/{rel}", filter=norm)
                n += 1
    return buf.getvalue(), n


def build_onstart(dph, box_start):
    code, nfiles = pack_code()
    run_steps = "\n".join(f"run_step {n} {m} {json.dumps(c)}" for n, c, m in STEPS)
    names = " -o ".join(f"-name '{g}'" for g in RESULT_GLOBS)
    s = ONSTART
    for k, v in {"__BOX_START__": box_start, "__DEADLINE_S__": deadline_seconds(dph), "__EXPORT_S__": EXPORT_S,
                 "__DPH__": dph, "__CAP__": f"{CAP_USD:.2f}", "__KEY_ENV__": KEY_ENV, "__FIND_NAMES__": names,
                 "__FILE_CAP__": FILE_CAP_BYTES, "__PIP_PKGS__": PIP_PKGS, "__TAIL_LINES__": STDOUT_TAIL_LINES,
                 "__STARTED__": STARTED, "__RUN_STEPS__": run_steps}.items():
        s = s.replace(k, str(v))
    b64 = base64.b64encode(code).decode()
    return s, [b64[i:i + 12_000] for i in range(0, len(b64), 12_000)], len(code), nfiles


def redact(text):
    key = os.environ.get(KEY_ENV, "")
    if key:
        text = text.replace(key, "<REDACTED>")
    return re.sub(r"sk-ant-[A-Za-z0-9_-]+", "<REDACTED>", text)


# ----------------------------------------------------------------------------- create
def create(a):
    if not str(a.offer).isdigit():
        raise SystemExit("--offer must be a numeric offer id")
    dph = None
    for _ in range(6):      # the marketplace listing is a changing sample: retry, then fall back to the last `search`
        hit = [o for o in find_offers() if o["id"] == int(a.offer)]
        if hit:
            dph = float(hit[0]["dph_total"])
            break
    if dph is None:
        try:
            dph = float(json.loads((RUNS / "last_search.json").read_text())[str(a.offer)])
            print(f"(offer not in a live listing; using price {dph} from the last search)", file=sys.stderr)
        except Exception:
            dph = None
    if dph is not None:
        pass
    elif a.dryrun and a.dph:
        dph = a.dph
        print(f"(offer {a.offer} not in the filtered listing; dryrun uses --dph {dph})", file=sys.stderr)
    else:
        raise SystemExit(f"offer {a.offer} is not in the filtered listing (search); nothing sent")
    if a.dph and not a.dryrun:
        raise SystemExit("--dph is for --dryrun only; the real dph comes from the offer")
    dph = dph * 1.10    # the offer's dph_total omits disk cost; real instances came back 2-7% higher, so plan with +10%
    box_start = int(time.time())
    script, chunks, code_bytes, nfiles = build_onstart(dph, box_start)
    args = ["bash", "-c", script, "rlaif1"] + chunks
    size = len(json.dumps(args))
    if size > MAX_ONSTART_BYTES:
        raise SystemExit(f"onstart is {size} bytes, over {MAX_ONSTART_BYTES}; shrink the code/data")
    key_set = bool(os.environ.get(KEY_ENV))
    env = {KEY_ENV: os.environ.get(KEY_ENV, "")}
    body = {"client_id": "me", "image": IMAGE, "disk": DISK_GB, "label": LABEL, "runtype": "args",
            "args": args, "env": env, "target_state": "running"}
    dl = deadline_seconds(dph)
    summary = {"offer": int(a.offer) if str(a.offer).isdigit() else a.offer, "dph": dph, "cap_usd": CAP_USD,
               "box_deadline_s": dl, "box_deadline_h": round(dl / 3600, 2), "max_spend_at_deadline": round(dl / 3600 * dph, 3),
               "image": IMAGE, "label": LABEL, "code_files": nfiles, "code_xz_bytes": code_bytes,
               "onstart_bytes": size, f"{KEY_ENV}_set": key_set}
    if a.dryrun:
        print(redact(script))
        print("\n----- DRYRUN: nothing was sent -----")
        print(json.dumps({**summary, "request": {"method": "PUT", "path": f"/asks/{a.offer}/",
                                                 "body": {**body, "args": f"<bash -c script + {len(chunks)} base64 chunks, {size} bytes>",
                                                          "env": {KEY_ENV: "<REDACTED>" if key_set else "<NOT SET>"}}}}, indent=1))
        return
    if not a.yes:
        print(json.dumps({"sent": False, **summary, "note": "nothing was sent; repeat with --yes to rent"}, indent=1))
        return
    if not key_set:
        raise SystemExit(f"{KEY_ENV} is not set in this environment; nothing sent")
    listing = call("GET", "/instances/")
    if not isinstance(listing.get("instances"), list):
        raise SystemExit(f"cannot read the instance list ({listing.get('http')} {listing.get('error')}); nothing sent")
    live = [i.get("id") for i in listing["instances"] if i.get("label") == LABEL]
    if live:
        raise SystemExit(f"an instance labelled {LABEL} already exists: {live}; nothing sent")
    r = call("PUT", f"/asks/{a.offer}/", body, timeout=120)
    iid = r.get("new_contract")
    print(json.dumps({"sent": True, "success": r.get("success"), "new_contract": iid, "error": r.get("error"), "msg": redact(str(r.get("msg")))}))
    if not (r.get("success") and iid):
        raise SystemExit(1)
    time.sleep(10)
    x = inst(iid) or {}
    real = x.get("dph_total")
    if real is not None and float(real) > dph:   # dph already carries a +10% allowance
        print(json.dumps({"price_changed": real, "assumed": dph, "action": "destroying"}))
        destroy_instance(iid)
        raise SystemExit(1)
    save_state(a.run, {"instance_id": iid, "start_time": box_start, "dph": dph, "offer": int(a.offer), "cap_usd": CAP_USD,
                       "label": LABEL, "box_deadline_s": dl, "started_seen": False, "closing": None})
    print(f"state saved to {RUNS / a.run / 'state.json'}")


# ----------------------------------------------------------------------------- status / logs
def inst(i):
    """Instance record; {} when absent; None when the read failed."""
    r = call("GET", f"/instances/{i}/")
    if r.get("http") == 404:
        return {}
    if "instances" not in r:
        return None
    x = r.get("instances") or {}
    return (x[0] if x else {}) if isinstance(x, list) else x


def log_text(i, tail=2000, tries=8):
    r = call("PUT", f"/instances/request_logs/{i}/", {"tail": str(tail)}, timeout=30)
    url = r.get("result_url")
    if not url:
        return None
    for _ in range(tries):
        time.sleep(5)
        try:
            return get(url, 60).decode("utf-8", "replace")
        except Exception:
            continue
    return None


def show_lines(text):
    return [ln for ln in text.splitlines() if not ln.startswith("RB64 ") and len(ln) < 400]


def status(a):
    st = load_state(a.run)
    x = inst(st["instance_id"])
    elapsed = time.time() - st["start_time"]
    out = {"instance": st["instance_id"], "elapsed_min": round(elapsed / 60, 1), "est_usd": round(elapsed / 3600 * st["dph"], 3),
           "cap_usd": st["cap_usd"], "dph": st["dph"]}
    if x is None:
        out["state"] = "unknown (read failed)"
    elif not x:
        out["state"] = "not listed (destroyed?)"
    else:
        out.update(state=x.get("actual_status"), intended=x.get("intended_status"), label=x.get("label"), status_msg=(x.get("status_msg") or "")[:200])
    print(json.dumps(out))


def logs(a):
    st = load_state(a.run)
    text = log_text(st["instance_id"], a.tail)
    if text is None:
        raise SystemExit("could not fetch the log; try again")
    (run_dir(a.run) / "box.log").write_text(text)
    print("\n".join(show_lines(text)[-a.show:]))


# ----------------------------------------------------------------------------- destroy / waitlog
def destroy_instance(i):
    x = inst(i)
    if x is None:
        print(json.dumps({"destroy": "skipped", "why": "cannot read instance; try again"}))
        return False
    if x and (x.get("label") or "") != LABEL:
        raise SystemExit(f"refusing to destroy {i}: label {x.get('label')!r} is not {LABEL}")
    if not x:
        print(json.dumps({"destroy": "already gone"}))
        return True
    r = call("DELETE", f"/instances/{i}/")
    time.sleep(5)
    gone = inst(i) == {}
    print(json.dumps({"destroy": r.get("success"), "msg": r.get("msg"), "gone": gone}))
    return bool(r.get("success")) and gone


def destroy(a):
    st = load_state(a.run)
    ok = destroy_instance(st["instance_id"])
    st["destroyed"] = ok
    save_state(a.run, st)
    if not ok:
        raise SystemExit(1)


def fresh_lines(prev, text):
    """Lines of `text` after the last occurrence of the previously printed window (tails shift)."""
    cur = show_lines(text)
    if not prev:
        return cur
    w = prev[-3:]
    for i in range(len(cur) - len(w), -1, -1):
        if cur[i:i + len(w)] == w:
            return cur[i + len(w):]
    return cur


def end(a, st, code, tag, usd, **extra):
    """Save the log (if any), destroy the instance, say why."""
    text = log_text(st["instance_id"], 100000) if extra.pop("save_log", True) else None
    if text:
        (run_dir(a.run) / "box.log").write_text(text)
    gone = destroy_instance(st["instance_id"])
    st.update(destroyed=gone, closing=tag)
    save_state(a.run, st)
    print(json.dumps({"exit": code, "event": tag, "est_usd": round(usd, 3), "destroyed": gone, **extra}))
    raise SystemExit(code)


def waitlog(a):
    st = load_state(a.run)
    printed, fails = [], 0
    iid = st["instance_id"]
    while True:
        try:
            now = time.time()
            elapsed = now - st["start_time"]
            usd = elapsed / 3600 * st["dph"]
            if usd + st["dph"] * (a.poll + 120) / 3600 > st["cap_usd"]:
                end(a, st, 3, "OVER-CAP: elapsed*dph reached the cap; instance destroyed", usd)
            x = inst(iid)
            if x is None:
                raise RuntimeError("status read failed")
            if x == {}:
                print(json.dumps({"exit": 6, "event": "INSTANCE-GONE", "est_usd": round(usd, 3)}))
                raise SystemExit(6)
            fails = 0
            text = log_text(iid, 3000) if x.get("actual_status") == "running" else None
            if text is not None:
                new = fresh_lines(printed, text)
                for ln in new:
                    print(ln, flush=True)
                if new:
                    printed = (printed + new)[-50:]
                if STARTED in text:
                    st["started_seen"] = True
                m = CLOSING.search(text)
                if m:
                    end(a, st, 0 if m.group(1) == "DONE" else 2, f"CLOSING-MARKER RLAIF {m.group(1)}: log saved, instance destroyed", usd)
            if not st["started_seen"] and elapsed > START_TIMEOUT_MIN * 60:
                end(a, st, 4, f"NO-START: no '{STARTED}' within {START_TIMEOUT_MIN} min of create (image pull too slow?); instance destroyed", usd)
        except SystemExit:
            raise
        except Exception as e:
            fails += 1
            print(json.dumps({"poll_failure": type(e).__name__, "msg": str(e)[:200], "in_a_row": fails}), file=sys.stderr, flush=True)
            if fails >= 3:
                end(a, st, 7, "BLIND: three failed polls in a row; destroying to stop spend", usd if "usd" in dir() else 0.0)
        time.sleep(a.poll)


# ----------------------------------------------------------------------------- pull
def parse_results(text):
    m = re.search(r"=== RESULTS BEGIN sha256=(\w+) bytes=(\d+) lines=(\d+)", text)
    if not m:
        raise SystemExit("no '=== RESULTS BEGIN' header in the log (box not finished, or log tail too short)")
    want_sha, nbytes, nlines = m.group(1), int(m.group(2)), int(m.group(3))
    chunks = {}
    for mm in re.finditer(r"^(?:.*?\s)?RB64 (\d+) (\S+)\s*$", text, re.M):
        chunks[int(mm.group(1))] = mm.group(2)
    missing = [n for n in range(1, nlines + 1) if n not in chunks]
    if missing:
        raise SystemExit(f"{len(missing)} of {nlines} base64 lines missing from the log (first missing: {missing[0]})")
    data = base64.b64decode("".join(chunks[n] for n in range(1, nlines + 1)))
    if len(data) != nbytes or sha(data) != want_sha:
        raise SystemExit(f"results tarball failed its check (bytes {len(data)} vs {nbytes}, sha mismatch={sha(data) != want_sha})")
    return data


def pull(a):
    d = run_dir(a.run)
    st = load_state(a.run)
    log = d / "box.log"
    text = log.read_text() if log.is_file() and "=== RESULTS END" in log.read_text() else None
    if text is None:
        text = log_text(st["instance_id"], 100000)
        if text is None:
            raise SystemExit("no saved box.log with results and the live log could not be fetched")
        log.write_text(text)
    data = parse_results(text)
    (d / "results.tar.gz").write_bytes(data)
    with tarfile.open(d / "results.tar.gz", "r:gz") as t:
        names = [m.name for m in t.getmembers() if m.isfile()]
        if hasattr(tarfile, "data_filter"):
            t.extractall(d / "results", filter="data")
        else:
            for m in t.getmembers():
                if m.name.startswith(("/", "..")) or ".." in Path(m.name).parts or not (m.isfile() or m.isdir()):
                    raise SystemExit(f"unsafe tar member {m.name}")
            t.extractall(d / "results")
    print(json.dumps({"results_dir": str(d / "results"), "bytes": len(data), "sha256": sha(data), "files": names}))
    sf = d / "results" / "status.tsv"
    if sf.is_file():
        print(sf.read_text())


# ----------------------------------------------------------------------------- main
def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **kw):
        s = sub.add_parser(name, help=kw.pop("help", None))
        s.set_defaults(fn=fn)
        if name != "search":
            s.add_argument("--run", default="rlaif1")
        return s
    s = add("search", search, help="list cheapest suitable RTX 4090 offers")
    s.add_argument("--n", type=int, default=12)
    s = add("create", create, help="rent (only with --yes); --dryrun prints the onstart script")
    s.add_argument("--offer", required=True)
    s.add_argument("--yes", action="store_true")
    s.add_argument("--dryrun", action="store_true", help="print the full onstart script (key redacted) and size; sends nothing")
    s.add_argument("--dph", type=float, help="dryrun only: price to assume if the offer is no longer listed")
    add("status", status)
    s = add("logs", logs)
    s.add_argument("--tail", type=int, default=2000)
    s.add_argument("--show", type=int, default=60)
    s = add("waitlog", waitlog, help="poll, print new lines, destroy at closing marker / cap / no-start")
    s.add_argument("--poll", type=int, default=POLL_S)
    add("pull", pull, help="reassemble results from the log into runs/<run>/results/")
    add("destroy", destroy)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
