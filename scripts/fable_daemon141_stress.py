"""Exp 141 harnesses (new, prefix-owned): stress / empty / killburst.

stress:     boots a daemon subprocess for --agent/--config, then WRITES EVERY
            INBOX MESSAGE NON-ATOMICALLY ON PURPOSE (create empty file, sleep
            uniform(0, 300 ms), write full text, sometimes in two chunks with
            a second sleep) from --writers threads, while the daemon polls.
            Verifies every message is answered exactly once with the right
            content; counts "didn't catch anything" replies on non-empty
            messages, lost, wrong, dupes; records per-message latency
            (write-complete -> outbox visible).
empty:      writes --n genuinely-empty 0-byte files; each must get exactly
            one "I didn't catch anything." reply.
killburst:  exp-108 G2-style aimed kill-9 burst against the COMBINED
            108+141 daemon (boot with --combined): per aimed turn, a writer
            thread starts a non-atomic write, the driver sleeps a random
            0-400 ms then SIGKILLs the daemon, reboots, and awaits the reply
            (no resend -- the reply must already be durable or the reboot
            must serve it). Verifies 0 dup / 0 lost / 0 wrong.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_daemon141_stress.py stress --agent ... --config ... \\
    --out DIR --n 3000 --seed 141
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path

EMPTY_REPLY = "I didn't catch anything."
OUTBOX_POLL_S = 0.005


def _boot(agent: str, config: str, root: Path, combined: bool,
          idle_seconds: float = 3600.0) -> subprocess.Popen:
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    cmd = [sys.executable, "-B", agent, "--daemon", "--dir", str(root),
           "--config", config, "--idle-seconds", str(idle_seconds)]
    if "fable_daemon141_settle" in agent and combined:
        cmd.append("--combined")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, env=env)
    deadline = time.time() + 240.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("daemon exited during boot")
        if (root / "daemon_status.json").exists():
            return proc
        time.sleep(0.01)
    proc.terminate()
    raise RuntimeError("daemon boot timeout")


def _stop(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=30)


def _nonatomic_write(path: Path, text: str, rng: random.Random) -> None:
    """Create-then-write with a race window, sometimes in two chunks."""
    with open(path, "w", encoding="utf-8"):
        pass  # create empty, close
    time.sleep(rng.uniform(0.0, 0.300))
    if text and rng.random() < 0.30:
        cut = rng.randint(1, max(1, len(text) - 1))
        with open(path, "w", encoding="utf-8") as h:
            h.write(text[:cut])
            h.flush()
        time.sleep(rng.uniform(0.0, 0.100))
    with open(path, "w", encoding="utf-8") as h:
        h.write(text)
        h.flush()


def _await_all(root: Path, names: list[str], timeout: float,
               done: dict[str, float], t_complete: dict[str, float],
               lat: dict[str, float]) -> None:
    deadline = time.time() + timeout
    pending = set(names)
    while pending and time.time() < deadline:
        for name in list(pending):
            if (root / "outbox" / name).exists():
                t = time.time()
                done[name] = t
                if name in t_complete:
                    lat[name] = t - t_complete[name]
                pending.discard(name)
        if pending:
            time.sleep(OUTBOX_POLL_S)


def _turn_counts(root: Path) -> Counter:
    cnt: Counter = Counter()
    try:
        for line in (root / "daemon.log.jsonl").read_text(
                encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("event") == "turn" and rec.get("file"):
                cnt[rec["file"]] += 1
    except OSError:
        pass
    return cnt


def _plan(n: int) -> tuple[list[tuple[str, str, str | None]],
                           dict[str, str]]:
    """[(name, text, want_or_None_for_teach)]. First 10% teaches, then asks
    cycling the taught people with a rewrite every 9th turn."""
    n_teach = max(1, n // 10)
    msgs: list[tuple[str, str, str | None]] = []
    truth: dict[str, str] = {}
    for i in range(n_teach):
        p, v = f"FixP{i:04d}", f"FixV{i:04d}"
        truth[p] = v
        msgs.append((f"m{i:05d}.txt", f"{p}'s city is {v}.", None))
    i = n_teach
    k = 0
    while len(msgs) < n:
        p = f"FixP{k % n_teach:04d}"
        if k % 9 == 8:
            v = f"FixW{k:05d}"
            truth[p] = v
            msgs.append((f"m{i:05d}.txt",
                         f"Actually, {p}'s city is {v}.", None))
        else:
            msgs.append((f"m{i:05d}.txt", f"What is {p}'s city?",
                         truth[p]))
        i += 1
        k += 1
    return msgs, truth


def cmd_stress(args) -> int:
    t0 = time.time()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    root = out / "daemon"
    (root / "inbox").mkdir(parents=True)
    msgs, _ = _plan(args.n)
    by_name = {name: (text, want) for name, text, want in msgs}
    names = [m[0] for m in msgs]
    proc = _boot(args.agent, args.config, root, combined=False)
    t_complete: dict[str, float] = {}
    done: dict[str, float] = {}
    lat: dict[str, float] = {}
    lock = threading.Lock()
    try:
        shards = [msgs[i::args.writers] for i in range(args.writers)]

        def writer(shard, wid):
            rng = random.Random(args.seed + wid)
            for name, text, _ in shard:
                _nonatomic_write(root / "inbox" / name, text, rng)
                with lock:
                    t_complete[name] = time.time()

        threads = [threading.Thread(target=writer, args=(s, w))
                   for w, s in enumerate(shards)]
        for t in threads:
            t.start()
        _await_all(root, names, timeout=args.timeout, done=done,
                   t_complete=t_complete, lat=lat)
        for t in threads:
            t.join(timeout=60)
        # one more sweep: files written after the await deadline
        _await_all(root, names, timeout=120.0, done=done,
                   t_complete=t_complete, lat=lat)
        # sequential low-load probe (atomic tmp+replace writes, one at a
        # time): isolates per-turn daemon latency from queueing, for the
        # R3 p50-added gate.
        seq_lat: list[float] = []
        for j in range(args.seq_probe):
            sname = f"q{j:05d}.txt"
            stext = f"ProbeP{j:03d}'s city is ProbeV{j:03d}."
            tmp = root / "inbox" / (sname + f".tmp{os.getpid()}")
            tmp.write_text(stext, encoding="utf-8")
            t_start = time.time()
            os.replace(tmp, root / "inbox" / sname)
            got2: dict[str, float] = {}
            _await_all(root, [sname], timeout=120.0, done=got2,
                       t_complete={}, lat={})
            if sname in got2:
                seq_lat.append(got2[sname] - t_start)
        seq_lat.sort()
    finally:
        _stop(proc)
    lost, wrong, bad_empty, ok = 0, 0, 0, 0
    wrong_detail: list = []
    for name in names:
        text, want = by_name[name]
        try:
            reply = (root / "outbox" / name).read_text(encoding="utf-8")
        except OSError:
            lost += 1
            continue
        s = reply.strip()
        if want is None:
            good = s.startswith("Saved:") or s == "I already have that."
        else:
            good = want in s
        if good:
            ok += 1
        else:
            wrong += 1
            if s == EMPTY_REPLY:
                bad_empty += 1
            if len(wrong_detail) < 20:
                wrong_detail.append({"file": name, "text": text[:120],
                                     "want": want, "reply": s[:120]})
    cnt = _turn_counts(root)
    dupes = sum(1 for n_ in names if cnt.get(n_, 0) > 1)
    unlogged = sum(1 for n_ in names
                   if (root / "outbox" / n_).exists() and cnt.get(n_, 0) == 0)
    lats = sorted(lat.values())
    def pct(q):
        return round(lats[min(len(lats) - 1, int(q * len(lats)))]
                     if lats else -1.0, 4)
    seq_p50 = round(seq_lat[len(seq_lat) // 2], 4) if seq_lat else -1.0
    rep = {"mark": "R1-STRESS", "agent": args.agent, "n": args.n,
           "seed": args.seed, "writers": args.writers,
           "completed": len(done), "ok": ok, "lost": lost, "wrong": wrong,
           "bad_empty_on_nonempty": bad_empty, "dupes": dupes,
           "replied_but_unlogged": unlogged,
           "latency_s": {"n": len(lats), "p50": pct(0.50),
                         "p90": pct(0.90), "max": pct(1.0)},
           "latency_seq_s": {"n": len(seq_lat), "p50": seq_p50},
           "wrong_detail": wrong_detail,
           "pass": lost == 0 and wrong == 0 and dupes == 0,
           "seconds": round(time.time() - t0, 1)}
    (out / "stress-report.json").write_text(json.dumps(rep, indent=1),
                                            encoding="utf-8")
    print(json.dumps({k: rep[k] for k in
                      ("n", "completed", "ok", "lost", "wrong",
                       "bad_empty_on_nonempty", "dupes",
                       "replied_but_unlogged", "pass", "seconds")},
                     indent=1), flush=True)
    print(f"latency p50={rep['latency_s']['p50']} "
          f"p90={rep['latency_s']['p90']} max={rep['latency_s']['max']} "
          f"seq_p50={rep['latency_seq_s']['p50']}",
          flush=True)
    return 0 if rep["pass"] else 1


def cmd_empty(args) -> int:
    t0 = time.time()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    root = out / "daemon"
    (root / "inbox").mkdir(parents=True)
    names = [f"e{i:03d}.txt" for i in range(args.n)]
    proc = _boot(args.agent, args.config, root, combined=False)
    try:
        for name in names:
            with open(root / "inbox" / name, "w", encoding="utf-8"):
                pass  # genuinely empty, stays empty
        done: dict[str, float] = {}
        _await_all(root, names, timeout=args.timeout, done=done,
                   t_complete={}, lat={})
    finally:
        _stop(proc)
    lost, wrong = 0, 0
    for name in names:
        try:
            s = (root / "outbox" / name).read_text(encoding="utf-8").strip()
        except OSError:
            lost += 1
            continue
        if s != EMPTY_REPLY:
            wrong += 1
    cnt = _turn_counts(root)
    dupes = sum(1 for n_ in names if cnt.get(n_, 0) > 1)
    unlogged = sum(1 for n_ in names
                   if (root / "outbox" / n_).exists() and cnt.get(n_, 0) == 0)
    rep = {"mark": "R2-EMPTY", "n": args.n, "replied": len(done),
           "lost": lost, "wrong_content": wrong, "dupes": dupes,
           "replied_but_unlogged": unlogged,
           "pass": lost == 0 and wrong == 0 and dupes == 0,
           "seconds": round(time.time() - t0, 1)}
    (out / "empty-report.json").write_text(json.dumps(rep, indent=1),
                                           encoding="utf-8")
    print(json.dumps(rep, indent=1), flush=True)
    return 0 if rep["pass"] else 1


def cmd_killburst(args) -> int:
    t0 = time.time()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    root = out / "daemon"
    (root / "inbox").mkdir(parents=True)
    rng = random.Random(args.seed)
    proc = _boot(args.agent, args.config, root, combined=True)
    truth: dict[str, str] = {}
    records: list[dict] = []
    lost = wrong = dup_total = 0
    try:
        # atomic teaches first (no race here; establish ground truth)
        for i in range(60):
            p, v = f"KillP{i:02d}", f"KillV{i:02d}"
            truth[p] = v
            name = f"t{i:04d}.txt"
            (root / "inbox" / name).write_text(f"{p}'s city is {v}.",
                                               encoding="utf-8")
        _await_all(root, [f"t{i:04d}.txt" for i in range(60)],
                   timeout=300.0, done={}, t_complete={}, lat={})
        for k in range(args.kills):
            p = f"KillP{rng.randrange(60):02d}"
            text: str
            want: str | None
            if rng.random() < 0.4:
                v = f"KillW{k:03d}"
                truth[p] = v
                text, want = (f"Actually, {p}'s city is {v}.", None)
            else:
                text, want = f"What is {p}'s city?", truth[p]
            name = f"k{k:04d}.txt"
            started = threading.Event()

            def writer():
                r2 = random.Random(args.seed * 1000 + k)
                # exp-135 race shape: create, scheduling gap, ONE complete
                # write (single-open writers cannot recreate a served file,
                # so any dupe/wrong here is the daemon's, not the writer's).
                started.set()
                p = root / "inbox" / name
                with open(p, "w", encoding="utf-8"):
                    pass
                time.sleep(r2.uniform(0.0, 0.300))
                with open(p, "w", encoding="utf-8") as h:
                    h.write(text)
                    h.flush()

            th = threading.Thread(target=writer)
            th.start()
            started.wait()
            time.sleep(rng.uniform(0.0, 0.400))
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=60)
            th.join(timeout=60)
            proc = _boot(args.agent, args.config, root, combined=True)
            got: dict[str, float] = {}
            _await_all(root, [name], timeout=180.0, done=got,
                       t_complete={}, lat={})
            rec = {"file": name, "text": text[:120], "want": want,
                   "replied": name in got}
            if name not in got:
                lost += 1
            else:
                s = (root / "outbox" / name).read_text(
                    encoding="utf-8").strip()
                rec["reply"] = s[:120]
                good = (s.startswith("Saved:")
                        or s == "I already have that.") if want is None \
                    else (want in s)
                if not good:
                    wrong += 1
                    rec["BAD"] = True
            records.append(rec)
    finally:
        _stop(proc)
    cnt = _turn_counts(root)
    for rec in records:
        c = cnt.get(rec["file"], 0)
        rec["turn_events"] = c
        if c > 1:
            dup_total += 1
    # every aimed file must also exist exactly once in outbox
    outbox_names = [p.name for p in (root / "outbox").glob("k*.txt")]
    rep = {"mark": "R4-KILLBURST", "kills": args.kills, "seed": args.seed,
           "lost": lost, "wrong": wrong, "dup_files": dup_total,
           "aimed_outbox_files": len(outbox_names),
           "pass": lost == 0 and wrong == 0 and dup_total == 0
           and len(outbox_names) == args.kills,
           "seconds": round(time.time() - t0, 1), "records": records}
    (out / "killburst-report.json").write_text(json.dumps(rep, indent=1),
                                               encoding="utf-8")
    print(json.dumps({k: rep[k] for k in
                      ("kills", "lost", "wrong", "dup_files",
                       "aimed_outbox_files", "pass", "seconds")},
                     indent=1), flush=True)
    return 0 if rep["pass"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 141 harnesses")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("stress", "empty", "killburst"):
        s = sub.add_parser(name)
        s.add_argument("--agent", required=True)
        s.add_argument("--config", required=True)
        s.add_argument("--out", required=True)
        s.add_argument("--seed", type=int, default=141)
        s.add_argument("--timeout", type=float, default=900.0)
        if name == "stress":
            s.add_argument("--n", type=int, default=3000)
            s.add_argument("--writers", type=int, default=6)
            s.add_argument("--seq-probe", type=int, default=50)
        elif name == "empty":
            s.add_argument("--n", type=int, default=24)
        else:
            s.add_argument("--kills", type=int, default=12)
    args = ap.parse_args(argv)
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    if args.cmd == "stress":
        return cmd_stress(args)
    if args.cmd == "empty":
        return cmd_empty(args)
    return cmd_killburst(args)


if __name__ == "__main__":
    sys.exit(main())
