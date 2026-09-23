"""Exp 108 -- SOAK test of the exactly-once daemon (one-change follow-up to exp 93).

Drives a REAL daemon108 subprocess (scripts/fable_daemon108_run.py, new file;
sealed daemon74/loop102/agent-loop/notebook/listening modules unedited) through
its mailbox. Plan/schedule/checks are the exp-93 driver verbatim (same seed 93
=> same 20,000-turn plan, same 5 kill-9 + 3 graceful restart points); only the
daemon target differs, plus two measurement-only additions reported in
RESULTS.md as deviations: (a) --aim-midturn for the G2 seed-931 run (kill -9s
aimed deliberately mid-turn: the victim turn is submitted solo on a drained
pipeline and state.json is polled until loop.inbox is nonempty -- inbox write
done, reply not yet written -- then kill -9 at once); (b) exactly-once
evidence (doubled-sentence scan over every reply + receipts.jsonl single-
processing counts). Extra spawn flag --loop102 for the UNREGISTERED scale step
only (points daemon108 at the wrapped loop102 agent).

Turn language is restricted to the template sentences the FakeEars parser accepts:
  teach:   "Person0042's city is City00007."
  correct: "Actually, Person0042's city is City00007r1."
  ask 1-3 hops: "What is Person0042's city?" / "Who is Person0042's mother?"
                "What is Person0042's mother's city?" (up to 3 hops)

World: synthetic population of 2,000 people (one-word names Person0000..Person1999;
FakeEars rejects multi-word names) x 6 relations (mother/father/friend are person
pointers; city/color/food are literals with globally unique values).

The driver keeps a ground-truth model of the world and checks EVERY answer:
  ask     -> reply must contain "is <expected>." else wrong/unanswered (FAIL)
  teach/correct -> reply must be "Saved: ..." or "I already have that."
                   (DUPLICATE_OK after a kill-9 reprocess) else a wrong write (FAIL)
Teach-before-ask is guaranteed by construction: asks/corrections only reference
already-committed (person, relation) pairs; each pair is taught once (a second
plain teach of a new value would return CONFLICT by contract, so later changes go
through "Actually, ..." corrections, which supersede).

After EVERY restart the driver audits the raw notebook log (events.jsonl):
exactly one ENTITY per name; per (entity, relation) exactly as many taught FACT
events as committed teaches/corrections, with the current value equal to ground
truth. Any loss or duplication among facts whose reply was written is a FAIL.

Metrics recorded every 1,000 completed turns: daemon RSS, notebook file size,
window turns/s, per-turn reply latency p50/p99 (submit->reply under a sustained
pipeline of DEPTH=8 in-flight turns; turns straddling a restart excluded),
last boot time, last chain verify time. Restarts: with the pipeline in flight,
after reboot all pending outbox replies are awaited and reconciled in order.

First failure stops the run and writes a reproducer (the plan is deterministic
in --seed, so the point reproduces).

Stdlib only. Mac CPU. Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_soak108_run.py --turns 20000
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

RUN = SCRIPTS / "fable_daemon108_run.py"

PERSON_RELS = ("mother", "father", "friend")
LITERAL_RELS = ("city", "color", "food")
ALL_RELS = PERSON_RELS + LITERAL_RELS
N_PEOPLE = 2000
BURST = 24
WAIT_S = 180.0
# Pipeline depth: up to DEPTH turns submitted but unreconciled. The daemon drains
# at ~165 turns/s (dev: 500 teaches in 3.0 s on an empty notebook) while one
# submit->reply round trip costs a ~50 ms poll quantum; strict sequential driving
# would take ~70 ms/turn (~24 min for 20k, no margin). DEPTH=3 keeps a file
# waiting so the daemon never idles in its poll sleep, and throughput approaches
# the drain rate. DEPTH is deliberately small: reported reply latency is
# submit->reply under this sustained load with queueing <= 3 drains, so the K4
# growth ratio is not inflated by pipeline queueing. Turns straddling a restart
# are excluded from latency stats (they include the kill/STOP downtime).
DEPTH = 3


# ---------------------------------------------------------------- plan
def build_plan(n_turns: int, seed: int) -> tuple[list[dict], dict]:
    """Deterministic turn plan. Returns (turns, meta). Ground-truth simulation
    runs in plan order, which equals commit order at runtime."""
    rng = random.Random(seed)
    people = [f"Person{i:04d}" for i in range(N_PEOPLE)]
    lit_counter = [0]

    def fresh_literal(rel: str) -> str:
        lit_counter[0] += 1
        return f"{rel.capitalize()}{lit_counter[0]:05d}"

    pool: list[tuple[str, str, tuple]] = []
    for person in people:
        for rel in PERSON_RELS:
            target = rng.choice(people)
            while target == person:
                target = rng.choice(people)
            pool.append((person, rel, ("E", target)))
        for rel in LITERAL_RELS:
            pool.append((person, rel, ("L", fresh_literal(rel))))
    rng.shuffle(pool)

    gt: dict[tuple[str, str], tuple] = {}
    taught_order: list[tuple[str, str]] = []
    literal_pairs: list[tuple[str, str]] = []
    turns: list[dict] = []
    correct_seq = [0]

    def make_ask() -> dict | None:
        start = rng.choice(people)
        depth = 1 + rng.randrange(3)
        node = start
        rels: list[str] = []
        ok = True
        for hop in range(depth):
            if hop < depth - 1:
                links = [r for r in PERSON_RELS if (node, r) in gt]
                if not links:
                    ok = False
                    break
                rel = rng.choice(links)
                rels.append(rel)
                val = gt[(node, rel)]
                assert val[0] == "E"
                node = val[1]
            else:
                cands = [r for r in ALL_RELS if (node, r) in gt]
                if not cands:
                    cands = [r for r in ALL_RELS if (start, r) in gt]
                    node = start
                    rels = []
                    if not cands:
                        return None
                rel = rng.choice(cands)
                rels.append(rel)
        if not ok or not rels:
            cands = [r for r in ALL_RELS if (start, r) in gt]
            if not cands:
                return None
            rels = [rng.choice(cands)]
            node = start
        val = gt[(node, rels[-1])]
        if val[0] == "E":
            expected = val[1]
            what = "Who"
        else:
            expected = val[1]
            what = "What"
        chain = "'s ".join([start] + [r.replace("_", " ") for r in rels])
        return {"kind": "ask", "text": f"{what} is {chain}?",
                "expected": expected, "rels": list(rels)}

    while len(turns) < n_turns:
        r = rng.random()
        if pool and (r < 0.52 or len(taught_order) < 60):
            person, rel, val = pool.pop()
            gt[(person, rel)] = val
            taught_order.append((person, rel))
            if rel in LITERAL_RELS:
                literal_pairs.append((person, rel))
            vtext = val[1]
            turns.append({"kind": "teach", "text": f"{person}'s {rel} is {vtext}.",
                          "name": person, "rel": rel, "val": val})
        elif r < 0.86 and taught_order:
            ask = make_ask()
            if ask is None:
                person, rel, val = pool.pop()
                gt[(person, rel)] = val
                taught_order.append((person, rel))
                if rel in LITERAL_RELS:
                    literal_pairs.append((person, rel))
                turns.append({"kind": "teach",
                              "text": f"{person}'s {rel} is {val[1]}.",
                              "name": person, "rel": rel, "val": val})
            else:
                turns.append(ask)
        elif literal_pairs:
            person, rel = rng.choice(literal_pairs)
            correct_seq[0] += 1
            base = gt[(person, rel)][1]
            newv = ("L", f"{base}r{correct_seq[0]}")
            gt[(person, rel)] = newv
            turns.append({"kind": "correct",
                          "text": f"Actually, {person}'s {rel} is {newv[1]}.",
                          "name": person, "rel": rel, "val": newv})
        elif pool:
            person, rel, val = pool.pop()
            gt[(person, rel)] = val
            taught_order.append((person, rel))
            if rel in LITERAL_RELS:
                literal_pairs.append((person, rel))
            turns.append({"kind": "teach", "text": f"{person}'s {rel} is {val[1]}.",
                          "name": person, "rel": rel, "val": val})
        else:
            ask = make_ask()
            if ask is None:
                raise RuntimeError("plan starved: no taught facts for asks")
            turns.append(ask)
    kinds = {}
    for t in turns:
        kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
    meta = {"seed": seed, "kinds": kinds, "people": N_PEOPLE,
            "relations": list(ALL_RELS)}
    return turns, meta


# ---------------------------------------------------------------- daemon control
class Driver:
    def __init__(self, args) -> None:
        self.args = args
        self.dart = Path(args.artifact_dir)
        self.ddir = self.dart / "daemon"
        # Fresh dir per invocation: stale mailbox/notebook state from an
        # earlier run would alias filenames and facts (dev finding 2026-09-22:
        # reusing the dir replays old outbox replies and double-counts facts).
        import shutil
        if self.ddir.exists():
            shutil.rmtree(self.ddir)
        self.ddir.mkdir(parents=True, exist_ok=True)
        self.proc: subprocess.Popen | None = None
        self.log_handle = open(self.dart / "daemon.stdout.log", "a", encoding="utf-8")
        self.boot_s = -1.0
        self.verify_s = -1.0

    # -- mailbox io
    def submit(self, seq: int, text: str) -> None:
        name = f"t{seq:06d}"
        tmp = self.ddir / "inbox" / f"{name}.tmp{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as h:
            h.write(text if text.endswith("\n") else text + "\n")
            h.flush()
            os.fsync(h.fileno())
        os.replace(tmp, self.ddir / "inbox" / f"{name}.txt")

    def read_reply(self, seq: int) -> str | None:
        p = self.ddir / "outbox" / f"t{seq:06d}.txt"
        if p.exists():
            return p.read_text(encoding="utf-8")
        return None

    def wait_reply(self, seq: int, timeout: float = WAIT_S) -> tuple[str, float]:
        t0 = time.time()
        while time.time() - t0 < timeout:
            r = self.read_reply(seq)
            if r is not None:
                return r, time.time() - t0
            time.sleep(0.005)
        raise RuntimeError(f"no outbox reply for t{seq:06d} within {timeout}s")

    def wait_many(self, seqs: list[int], timeout: float = WAIT_S) -> None:
        t0 = time.time()
        missing = [s for s in seqs if self.read_reply(s) is None]
        while missing and time.time() - t0 < timeout:
            if self.proc is not None and self.proc.poll() is not None:
                raise RuntimeError(
                    f"daemon died (exit {self.proc.poll()}) after restart; "
                    f"missing {[f't{s:06d}' for s in missing[:5]]}; "
                    f"log tail: {self.log_tail(3)}")
            time.sleep(0.01)
            missing = [s for s in seqs if self.read_reply(s) is None]
        if missing:
            raise RuntimeError(f"missing outbox replies after restart: "
                               f"{[f't{s:06d}' for s in missing[:10]]} ...")

    def log_tail(self, n: int = 3) -> str:
        try:
            lines = (self.ddir / "daemon.log.jsonl").read_text(
                encoding="utf-8").strip().split("\n")
            return " | ".join(line[:160] for line in lines[-n:])
        except Exception as exc:
            return f"<no log: {exc}>"

    # -- process
    def spawn(self) -> float:
        (self.ddir / "STOP").unlink(missing_ok=True)
        (self.ddir / "heartbeat.json").unlink(missing_ok=True)
        (self.ddir / "daemon_status.json").unlink(missing_ok=True)
        t0 = time.time()
        cmd = [sys.executable, "-B", str(RUN), "--dir", str(self.ddir),
               "--idle-seconds", "3600"]
        if getattr(self.args, "loop102", False):
            cmd.append("--loop102")
        self.proc = subprocess.Popen(
            cmd, stdout=self.log_handle, stderr=subprocess.STDOUT)
        deadline = t0 + WAIT_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"daemon exited early code {self.proc.poll()}")
            if (self.ddir / "heartbeat.json").exists() and \
               (self.ddir / "daemon_status.json").exists():
                self.boot_s = time.time() - t0
                return self.boot_s
            time.sleep(0.02)
        self.proc.kill()
        raise RuntimeError("daemon did not write heartbeat/status in time")

    def stop_graceful(self, timeout: float = 10.0) -> float:
        assert self.proc is not None
        t0 = time.time()
        (self.ddir / "STOP").write_text("stop\n", encoding="utf-8")
        while time.time() - t0 < timeout:
            if self.proc.poll() is not None:
                break
            time.sleep(0.02)
        dt = time.time() - t0
        if self.proc.poll() is None:
            self.proc.kill()
            raise RuntimeError("daemon did not STOP gracefully within 10s")
        if self.proc.poll() != 0:
            raise RuntimeError(f"daemon STOP exit code {self.proc.poll()}, want 0")
        self.proc = None
        return dt

    def kill9(self) -> None:
        assert self.proc is not None
        self.proc.kill()
        self.proc.wait()
        self.proc = None

    def rss_kb(self) -> int:
        if self.proc is None:
            return -1
        try:
            out = subprocess.run(["ps", "-o", "rss=", "-p", str(self.proc.pid)],
                                 capture_output=True, text=True, timeout=10)
            return int(out.stdout.strip())
        except Exception:
            return -1

    def nb_bytes(self) -> int:
        p = self.ddir / "notebook" / "events.jsonl"
        return p.stat().st_size if p.exists() else -1

    def verify_chain(self) -> float:
        """Time a fresh read of the notebook dir (hash chain verification)."""
        import fable_notebook_contract as C
        t0 = time.time()
        nb = C.Notebook(self.ddir / "notebook")
        assert not nb.torn_tail, "torn tail present while daemon stopped"
        self.verify_s = time.time() - t0
        return self.verify_s

    # -- audit: every committed teach present exactly once, current value == gt
    def audit(self, committed: list[dict], gt: dict) -> dict:
        ent: dict[str, str] = {}
        facts: dict[tuple[str, str], list[tuple[str, str]]] = {}
        n_events = 0
        with open(self.ddir / "notebook" / "events.jsonl", encoding="utf-8") as h:
            for line in h:
                line = line.strip()
                if not line:
                    continue
                n_events += 1
                ev = json.loads(line)
                if ev.get("kind") == "ENTITY":
                    ent[ev["entity_id"]] = ev.get("name", "")
                elif ev.get("kind") == "FACT" and ev.get("source") == "taught":
                    v = ev["value"]
                    rep = ("E", ent.get(v["entity"], "?")) if "entity" in v \
                        else ("L", str(v.get("literal", "")))
                    facts.setdefault((ev["subject"], ev["relation"]), []).append(rep)
        name2id: dict[str, list[str]] = {}
        for eid, nm in ent.items():
            name2id.setdefault(nm, []).append(eid)
        dupe_entities = {n: ids for n, ids in name2id.items() if len(ids) != 1}
        want_counts: dict[tuple[str, str], int] = {}
        for c in committed:
            key = (c["name"], c["rel"])
            want_counts[key] = want_counts.get(key, 0) + 1
        id_of = {n: ids[0] for n, ids in name2id.items() if len(ids) == 1}
        lost, dupes, wrongval = [], [], []
        for (name, rel), want_n in want_counts.items():
            eid = id_of.get(name)
            got = facts.get((eid, rel), []) if eid else []
            if len(got) < want_n:
                lost.append((name, rel, want_n, len(got)))
            elif len(got) > want_n:
                dupes.append((name, rel, want_n, len(got)))
            if eid:
                want_v = gt.get((name, rel))
                if want_v is not None and got and got[-1] != want_v:
                    wrongval.append((name, rel, want_v, got[-1]))
        return {"events": n_events, "entities": len(ent),
                "dupe_entities": dupe_entities, "lost": lost, "dupes": dupes,
                "wrongval": wrongval,
                "ok": not dupe_entities and not lost and not dupes and not wrongval}


# ---------------------------------------------------------------- classification
def check_turn(turn: dict, reply: str) -> tuple[bool, str]:
    if turn["kind"] == "ask":
        if f"is {turn['expected']}." in reply:
            return True, "correct"
        return False, "wrong-or-unanswered"
    if reply.startswith("Saved:") or reply.strip() == "I already have that.":
        return True, "write-ok"
    return False, "wrong-write"


def has_doubled_sentence(reply: str) -> bool:
    """Exp-108 evidence scan: True if any sentence occurs twice in one reply
    (the exp-93 ghost signature: 'I already have that. I already have that.').
    Single-sentence replies are never doubled."""
    parts = [p.strip() for p in reply.replace("?", ".").split(".") if p.strip()]
    return len(parts) > 1 and len(set(parts)) != len(parts)


def read_state_inbox(daemon_dir) -> list:
    """What state.json currently holds in loop.inbox (crash-artefact probe)."""
    try:
        state = json.loads((Path(daemon_dir) / "state.json").read_text(
            encoding="utf-8"))
    except Exception:
        return []
    inbox = state.get("inbox", [])
    return list(inbox) if isinstance(inbox, list) else []


# ---------------------------------------------------------------- main
def percentile(xs: list[float], q: float) -> float:
    if not xs:
        return -1.0
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(q * len(s))))
    return s[i]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 108 daemon soak driver")
    ap.add_argument("--turns", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=93)
    ap.add_argument("--artifact-dir", default="artifacts/fable-soak108-20260921")
    ap.add_argument("--kills", type=int, default=5)
    ap.add_argument("--graceful", type=int, default=3)
    ap.add_argument("--budget-s", type=float, default=1500.0)
    ap.add_argument("--aim-midturn", action="store_true",
                    help="G2 mode: each kill -9 is aimed deliberately mid-turn "
                         "(victim submitted solo on a drained pipeline; "
                         "state.json polled until loop.inbox is nonempty, "
                         "then kill at once). Unused in the seed-93 run.")
    ap.add_argument("--loop102", action="store_true",
                    help="UNREGISTERED scale step only: point daemon108 at "
                         "the wrapped loop102 agent.")
    args = ap.parse_args(argv)

    t_start = time.time()
    turns, meta = build_plan(args.turns, args.seed)
    rng = random.Random(args.seed * 7 + 1)
    n_restart = args.kills + args.graceful
    lo = min(1500, max(50, args.turns // 10))
    hi = max(lo + n_restart, args.turns - 50)
    points = sorted(rng.sample(range(lo, hi), n_restart))
    kinds = (["kill"] * args.kills + ["graceful"] * args.graceful)
    rng.shuffle(kinds)
    schedule = sorted(zip(points, kinds))
    print(f"plan: {len(turns)} turns {meta['kinds']}", flush=True)
    print(f"restarts: {[(p, k) for p, k in schedule]}", flush=True)

    drv = Driver(args)
    ckpt_path = drv.dart / "checkpoints.csv"
    ckpt = open(ckpt_path, "w", newline="", encoding="utf-8")
    cw = csv.writer(ckpt)
    cw.writerow(["turns_done", "wall_s", "window_turns_per_s", "rss_kb",
                 "nb_bytes", "p50_ms", "p99_ms", "restarts_done",
                 "last_boot_s", "last_verify_s", "last_restart_kind"])
    rest_log = open(drv.dart / "restarts.csv", "w", newline="", encoding="utf-8")
    rw = csv.writer(rest_log)
    rw.writerow(["at_turn", "kind", "stop_s", "verify_s", "boot_s",
                 "lost", "dupes", "wrongval", "dupe_entities"])

    gt: dict[tuple[str, str], tuple] = {}
    committed: list[dict] = []
    lat: list[float] = []
    doubled_hits: list[int] = []  # exp-108 evidence: seqs whose reply holds
    done = 0                      # a twice-occurring sentence (ghost scan)
    rest_done = 0
    sched_i = 0
    fail: dict | None = None
    status = "PASS"

    def checkpoint() -> None:
        win = lat[-1000:]
        nb = drv.nb_bytes()
        cw.writerow([done, round(time.time() - t_start, 1),
                     round(1000.0 / max(1e-9, sum(win)), 2) if len(win) == 1000
                     else round(done / max(1e-9, time.time() - t_start), 2),
                     drv.rss_kb(), nb,
                     round(percentile(win, 0.50) * 1000, 2),
                     round(percentile(win, 0.99) * 1000, 2),
                     rest_done, round(drv.boot_s, 3), round(drv.verify_s, 3),
                     schedule[rest_done - 1][1] if rest_done else ""])
        ckpt.flush()
        print(f"ckpt {done}: " + ",".join(str(x) for x in
              [round(time.time() - t_start), drv.rss_kb(), nb,
               round(percentile(win, 0.50) * 1000, 1),
               round(percentile(win, 0.99) * 1000, 1)]), flush=True)

    def process_reply(seq: int, turn: dict, reply: str) -> tuple[bool, str]:
        ok, why = check_turn(turn, reply)
        if has_doubled_sentence(reply):
            doubled_hits.append(seq)
        if not ok:
            return False, why
        if turn["kind"] in ("teach", "correct"):
            gt[(turn["name"], turn["rel"])] = turn["val"]
            committed.append(turn)
        return True, why

    def reproducer(seq: int, turn: dict, reply: str, why: str) -> None:
        with open(drv.dart / "REPRODUCER.md", "w", encoding="utf-8") as h:
            h.write(f"# Exp 108 first failing point\n\nseed={args.seed} seq={seq} "
                    f"kind={turn['kind']} verdict={why}\n\nturn text:\n"
                    f"{turn['text']}\n\nexpected: {turn.get('expected', turn.get('val'))}\n\n"
                    f"reply:\n{reply}\n\nreplay: the plan is deterministic in "
                    f"--seed {args.seed}; re-run this script with --turns {seq + 1} "
                    f"to reach the same point.\n")

    try:
        drv.spawn()
        next_sub = 0
        next_wait = 0
        pending: list[int] = []  # submitted, unreconciled, in plan order
        submit_t: dict[int, float] = {}
        submit_epoch: dict[int, int] = {}
        epoch = 0

        def fill() -> None:
            nonlocal next_sub
            while len(pending) < DEPTH and next_sub < len(turns):
                drv.submit(next_sub, turns[next_sub]["text"])
                submit_t[next_sub] = time.time()
                submit_epoch[next_sub] = epoch
                pending.append(next_sub)
                next_sub += 1

        def wait_seq(s: int) -> str:
            deadline = submit_t[s] + WAIT_S
            while time.time() < deadline:
                r = drv.read_reply(s)
                if r is not None:
                    return r
                if drv.proc is not None and drv.proc.poll() is not None:
                    raise RuntimeError(
                        f"daemon died (exit {drv.proc.poll()}) while "
                        f"t{s:06d} was in flight; log tail: "
                        f"{drv.log_tail(3)}")
                time.sleep(0.005)
            raise RuntimeError(f"no outbox reply for t{s:06d} within {WAIT_S}s")

        def reconcile(s: int, reply: str, record_lat: bool) -> tuple[bool, str]:
            if record_lat:
                lat.append(time.time() - submit_t[s])
            return process_reply(s, turns[s], reply)

        while next_wait < len(turns):
            if time.time() - t_start > args.budget_s:
                status = "FAIL"
                fail = {"mark": "K5", "detail": f"budget {args.budget_s}s exceeded"}
                break
            if sched_i < len(schedule) and done == schedule[sched_i][0]:
                kind = schedule[sched_i][1]
                epoch += 1
                aim_info: dict | None = None
                if kind == "kill" and args.aim_midturn:
                    # G2: drain the pipeline normally, then aim one victim
                    # turn deliberately mid-turn (inbox write observed in
                    # state.json, reply not yet written) and kill -9 at once.
                    drain_bad = None
                    while pending:
                        s0 = next_wait
                        reply0 = wait_seq(s0)
                        ok0, why0 = reconcile(
                            s0, reply0, submit_epoch[s0] == epoch)
                        pending.remove(s0)
                        if not ok0:
                            drain_bad = (s0, turns[s0], reply0, why0)
                            break
                        done += 1
                        next_wait += 1
                    if drain_bad is not None:
                        s, t, r, why = drain_bad
                        reproducer(s, t, r, why)
                        status = "FAIL"
                        fail = {"mark": "K1", "seq": s, "kind": t["kind"],
                                "why": why}
                        break
                    victim: int | None = None
                    inbox_seen = False
                    outbox_before = False
                    attempts = 0
                    while next_sub < len(turns) and attempts < 50:
                        v = next_sub
                        drv.submit(v, turns[v]["text"])
                        submit_t[v] = time.time()
                        submit_epoch[v] = epoch
                        next_sub += 1
                        attempts += 1
                        seen, beat = False, False
                        t0p = time.time()
                        while time.time() - t0p < 10.0:
                            if read_state_inbox(drv.ddir):
                                seen = True
                                break
                            if drv.read_reply(v) is not None:
                                beat = True
                                break
                            time.sleep(0.0005)
                        if seen:
                            victim, inbox_seen = v, True
                            outbox_before = \
                                drv.read_reply(v) is not None
                            break
                        replyv = wait_seq(v)  # tick beat the polls: normal
                        okv, whyv = reconcile(v, replyv, True)
                        if not okv:
                            reproducer(v, turns[v], replyv, whyv)
                            status = "FAIL"
                            fail = {"mark": "K1", "seq": v,
                                    "kind": turns[v]["kind"], "why": whyv}
                            break
                        done += 1
                        next_wait += 1
                    if status == "FAIL":
                        break
                    if victim is None:  # fallback: un-aimed kill (reported)
                        victim = next_sub
                        drv.submit(victim, turns[victim]["text"])
                        submit_t[victim] = time.time()
                        submit_epoch[victim] = epoch
                        next_sub += 1
                        attempts += 1
                    drv.kill9()
                    stop_s = -1.0
                    pending.append(victim)
                    aim_info = {"victim": victim, "aimed": inbox_seen,
                                "outbox_before_kill": outbox_before,
                                "attempts": attempts}
                    with open(drv.dart / "aims.jsonl", "a",
                              encoding="utf-8") as ah:
                        ah.write(json.dumps(
                            {"at_turn": done, **aim_info}) + "\n")
                else:
                    for s in range(next_sub, min(len(turns), next_sub + BURST)):
                        drv.submit(s, turns[s]["text"])
                        submit_t[s] = time.time()
                        submit_epoch[s] = epoch
                        pending.append(s)
                        next_sub += 1
                    if kind == "kill":
                        time.sleep(0.25)
                        drv.kill9()
                        stop_s = -1.0
                    else:
                        time.sleep(0.15)
                        stop_s = drv.stop_graceful()
                drv.verify_chain()
                drv.spawn()
                drv.wait_many(list(pending))
                bad = None
                for s in list(pending):
                    reply = drv.read_reply(s)
                    assert reply is not None
                    ok, why = process_reply(s, turns[s], reply)
                    pending.remove(s)
                    if not ok:
                        bad = (s, turns[s], reply, why)
                        break
                    done += 1
                    next_wait += 1
                rest_done += 1
                aud = drv.audit(committed, gt)
                rw.writerow([done, kind, round(stop_s, 3),
                             round(drv.verify_s, 3), round(drv.boot_s, 3),
                             len(aud["lost"]), len(aud["dupes"]),
                             len(aud["wrongval"]), len(aud["dupe_entities"])])
                rest_log.flush()
                print(f"restart {rest_done}/{n_restart} {kind} at turn {done}: "
                      f"stop={stop_s:.2f}s verify={drv.verify_s:.2f}s "
                      f"boot={drv.boot_s:.2f}s audit_ok={aud['ok']}"
                      + (f" aim={aim_info}" if aim_info else ""), flush=True)
                if bad is not None:
                    s, t, r, why = bad
                    reproducer(s, t, r, why)
                    status = "FAIL"
                    fail = {"mark": "K1", "seq": s, "kind": t["kind"], "why": why}
                    break
                if not aud["ok"]:
                    with open(drv.dart / "AUDIT_FAIL.json", "w",
                              encoding="utf-8") as h:
                        json.dump({k: v for k, v in aud.items() if k != "ok"},
                                  h, indent=1, default=str)
                    status = "FAIL"
                    fail = {"mark": "K2", "at_turn": done, "kind": kind}
                    break
                sched_i += 1
                if done % 1000 == 0:
                    checkpoint()
                continue
            fill()
            s = next_wait
            reply = wait_seq(s)
            ok, why = reconcile(s, reply, submit_epoch[s] == epoch)
            pending.remove(s)
            if not ok:
                reproducer(s, turns[s], reply, why)
                status = "FAIL"
                fail = {"mark": "K1", "seq": s, "kind": turns[s]["kind"],
                        "why": why}
                break
            done += 1
            next_wait += 1
            if done % 1000 == 0:
                checkpoint()
    except Exception as exc:  # a crash is a failed mark, not a crashed script
        status = "FAIL"
        fail = {"mark": "EXCEPTION", "detail": f"{type(exc).__name__}: {exc}"}
    finally:
        try:
            if drv.proc is not None and drv.proc.poll() is None:
                try:
                    final_stop = drv.stop_graceful()
                except Exception:
                    drv.kill9()
                    final_stop = -1.0
            else:
                final_stop = -1.0
        except Exception:
            final_stop = -1.0
        ckpt.close()
        rest_log.close()

    wall = time.time() - t_start
    try:
        final_verify = drv.verify_chain()
    except Exception as exc:
        final_verify = -1.0
        if status == "PASS":
            status = "FAIL"
            fail = {"mark": "K3", "detail": f"final verify failed: {exc}"}
    final_boot = drv.boot_s

    lat_ms = sorted(x * 1000 for x in lat)
    p50_1k = percentile([x / 1000 for x in lat_ms[:1000]], 0.50) * 1000 \
        if len(lat_ms) >= 1000 else -1.0
    p99_1k = percentile([x / 1000 for x in lat_ms[:1000]], 0.99) * 1000 \
        if len(lat_ms) >= 1000 else -1.0
    p99_end = percentile([x / 1000 for x in lat_ms[-1000:]], 0.99) * 1000 \
        if len(lat_ms) >= 1000 else -1.0

    k4_data_ok = p99_1k > 0 and p99_end > 0
    marks = {
        "K1": {"desc": "0 wrong answers and 0 wrong writes over "
                       f"{args.turns} turns",
               "pass": status == "PASS",
               "wrong": 0 if status == "PASS" else 1},
        "K2": {"desc": "no replied taught fact lost/duplicated over "
                       f"{n_restart} restarts",
               "pass": status == "PASS" and (fail or {}).get("mark") != "K2"},
        "K3": {"desc": "final boot+verify < 10 s",
               "pass": 0 < final_boot + final_verify < 10.0,
               "boot_s": round(final_boot, 3), "verify_s": round(final_verify, 3)},
        "K4": {"desc": "p99 at end < 10x p99 at 1,000 turns",
               "pass": (p99_end < 10 * p99_1k) if k4_data_ok else args.turns < 2000,
               "p99_1k_ms": round(p99_1k, 2), "p99_end_ms": round(p99_end, 2)},
        "K5": {"desc": "whole soak < 25 min Mac CPU",
               "pass": wall < 1500.0 and done == args.turns,
               "wall_s": round(wall, 1), "turns_done": done},
    }
    if status == "PASS" and not all(m["pass"] for m in marks.values()):
        status = "FAIL"
        for k, m in marks.items():
            if not m["pass"]:
                fail = {"mark": k}
                break
    # Exp-108 exactly-once evidence (measurement only; K-marks unchanged):
    # every outbox reply scanned for doubled sentences, and receipts.jsonl
    # must show each processed id exactly once (no re-execution, no loss).
    receipts_path = drv.dart / "daemon" / "receipts.jsonl"
    receipt_counts: dict[str, int] = {}
    try:
        with open(receipts_path, encoding="utf-8") as rh:
            for line in rh:
                line = line.strip()
                if not line:
                    continue
                try:
                    name = json.loads(line)["file"]
                except (ValueError, KeyError):
                    continue
                receipt_counts[name] = receipt_counts.get(name, 0) + 1
    except OSError:
        pass
    dup_receipts = {f: c for f, c in receipt_counts.items() if c != 1}
    exactly_once = {"replies_checked": done,
                    "doubled_sentence_replies": len(doubled_hits),
                    "doubled_seqs": list(doubled_hits),
                    "receipt_ids": len(receipt_counts),
                    "receipts_not_exactly_once": dup_receipts}
    summary = {"status": ("PASS" if status == "PASS" else "FAIL"),
                "seed": args.seed, "turns_done": done,
                "turns_planned": args.turns, "wall_s": round(wall, 1),
                "plan_kinds": meta["kinds"], "restarts": schedule,
                "marks": marks, "fail": fail, "final_stop_s": final_stop,
                "exactly_once": exactly_once}
    with open(drv.dart / "summary.json", "w", encoding="utf-8") as h:
        json.dump(summary, h, indent=1)
    print(json.dumps(summary, indent=1), flush=True)
    print("SOAK108", summary["status"], flush=True)
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
