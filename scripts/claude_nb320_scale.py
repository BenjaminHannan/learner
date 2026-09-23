#!/usr/bin/env python3
"""nb-320 scale runner (report-only baseline).

Backend-pluggable: --factory module:attr names a callable taking a notebook
directory and returning an object with the contract API (declare_relation,
new_entity, assert_fact, retract, ask, current). Default open_baseline()
returns FixedIndexedLoopNotebook(root).nb. nb-321 reuses this file unchanged.

Subcommands (each runs in a FRESH process):
  write  replay a workload file into a fresh dir, track ground truth + statuses
  open   time the factory opening a finished dir (cold open)
  probe  open a finished dir, run 2000 one-hop + 1000 two-hop recall probes
  crash  20k-only crash test driver (spawns crashchild 30x, SIGKILLs, reopens)
  crashchild  write facts with an fsynced ack file (kill target)
  tamper 20k-only tamper test driver (20 copies, 1 byte flipped, reopen)
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import pickle
import random
import resource
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def open_baseline(root):
    """Default factory: the store model 292 uses."""
    from fable_fix220_restartindex import FixedIndexedLoopNotebook
    return FixedIndexedLoopNotebook(root).nb


def load_factory(spec: str | None):
    if not spec:
        return open_baseline
    mod_name, _, attr = spec.partition(":")
    if not attr:
        raise SystemExit("--factory must be module:attr")
    mod = importlib.import_module(mod_name)
    return getattr(mod, attr)


def read_workload(path: str):
    header = None
    ops = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            if row["type"] == "header":
                header = row
            else:
                ops.append(row)
    assert header is not None
    return header, ops


def cmd_write(args) -> int:
    factory = load_factory(args.factory)
    header, ops = read_workload(args.workload)
    names = header["names"]
    functional = set(header["functional"])
    outdir = Path(args.dir)
    if outdir.exists():
        raise SystemExit(f"refusing to reuse existing dir {outdir}")
    t0 = time.perf_counter()
    nb = factory(str(outdir))
    eid: dict[int, str] = {}
    for rel in sorted(set(functional) | set(header["multivalued"])):
        r = nb.declare_relation(f"nb320-rel-{rel}", rel, rel in functional)
        assert r.status == "SAVED", (rel, r.status)
    for i, name in enumerate(names):
        r = nb.new_entity(f"nb320-ent-{i:06d}", name)
        assert r.status == "SAVED", (name, r.status)
        eid[i] = r.detail["entity_id"]

    statuses: dict[str, dict[str, int]] = {}
    unexpected: list[dict] = []
    op2fid: dict[int, str] = {}
    # ground truth
    facts: dict[int, dict] = {}
    pair_corr: dict[tuple[int, str], bool] = {}

    def note(kind: str, status: str, op: dict):
        statuses.setdefault(kind, {}).setdefault(status, 0)
        statuses[kind][status] += 1
        if status != "SAVED":
            if len(unexpected) < 200:
                unexpected.append({"op": op["i"], "kind": kind,
                                   "status": status})

    for op in ops:
        subj = eid[op["subject"]]
        if op["kind"] == "teach":
            v = op["value"]
            val = {"entity": eid[v["entity"]]} if "entity" in v \
                else {"literal": v["literal"]}
            r = nb.assert_fact(op["event_id"], "listening", "taught",
                               subj, op["relation"], val,
                               correction=False, raw=op["raw"])
            note("teach", r.status, op)
            if r.status == "SAVED":
                fid = r.detail["fact_id"]
                op2fid[op["i"]] = fid
                facts[op["i"]] = {"fid": fid, "subj": op["subject"],
                                  "rel": op["relation"],
                                  "text": names[v["entity"]] if "entity" in v
                                  else v["literal"],
                                  "is_entity": "entity" in v,
                                  "val_ent": v.get("entity"),
                                  "active": True, "corr_child": False}
        elif op["kind"] == "correct":
            v = op["value"]
            val = {"entity": eid[v["entity"]]} if "entity" in v \
                else {"literal": v["literal"]}
            r = nb.assert_fact(op["event_id"], "listening", "taught",
                               subj, op["relation"], val,
                               correction=True, raw=op["raw"])
            note("correct", r.status, op)
            if r.status == "SAVED":
                fid = r.detail["fact_id"]
                op2fid[op["i"]] = fid
                old = facts.get(op["target"])
                if old is not None:
                    old["active"] = False
                facts[op["i"]] = {"fid": fid, "subj": op["subject"],
                                  "rel": op["relation"],
                                  "text": names[v["entity"]] if "entity" in v
                                  else v["literal"],
                                  "is_entity": "entity" in v,
                                  "val_ent": v.get("entity"),
                                  "active": True, "corr_child": True}
                pair_corr[(op["subject"], op["relation"])] = True
        elif op["kind"] == "forget":
            fid = op2fid[op["target"]]
            r = nb.retract(op["event_id"], "listening", fid, "nb320 forget")
            note("forget", r.status, op)
            if r.status == "SAVED" and op["target"] in facts:
                facts[op["target"]]["active"] = False
        else:
            raise SystemExit(f"bad op kind {op['kind']}")
    wall = time.perf_counter() - t0
    n_fact_writes = sum(1 for o in ops if o["kind"] in ("teach", "correct"))
    gt = {"names": names, "functional": sorted(functional),
          "eid": eid, "facts": facts,
          "pair_corr": {f"{s}\x00{r}": True for (s, r) in pair_corr},
          "n_ops": len(ops)}
    with open(args.gt, "wb") as fh:
        pickle.dump(gt, fh)
    out = {"wall_s": wall, "n_ops": len(ops),
           "n_fact_writes": n_fact_writes,
           "facts_per_s": n_fact_writes / wall if wall > 0 else 0.0,
           "n_events": len(nb.events), "statuses": statuses,
           "n_unexpected": sum(1 for u in unexpected),
           "unexpected": unexpected[:50]}
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "unexpected"}),
          flush=True)
    return 0


def cmd_open(args) -> int:
    factory = load_factory(args.factory)
    t0 = time.perf_counter()
    nb = factory(args.dir)
    dt = time.perf_counter() - t0
    Path(args.out).write_text(json.dumps({"open_s": dt,
                                          "n_events": len(nb.events)}),
                              encoding="utf-8")
    print(f"open_s={dt:.3f}", flush=True)
    return 0


def pair_answer(gt_facts, subj, rel):
    rows = [(oi, f) for oi, f in gt_facts.items()
            if f["active"] and f["subj"] == subj and f["rel"] == rel]
    rows.sort(key=lambda r: -r[0])
    return ", ".join(f["text"] for _, f in rows)


def cmd_probe(args) -> int:
    factory = load_factory(args.factory)
    with open(args.gt, "rb") as fh:
        gt = pickle.load(fh)
    names = gt["names"]
    facts = gt["facts"]
    pair_corr = set(tuple(k.split("\x00")) for k in gt["pair_corr"])
    pair_corr = {(int(s), r) for s, r in pair_corr}
    rng = random.Random(args.seed)
    t0 = time.perf_counter()
    nb = factory(args.dir)
    open_s = time.perf_counter() - t0

    plain = [oi for oi, f in facts.items()
             if f["active"] and not f["corr_child"]
             and (f["subj"], f["rel"]) not in pair_corr]
    corr = [oi for oi, f in facts.items()
            if f["active"] and f["corr_child"]]
    forg_all = [oi for oi, f in facts.items() if not f["active"]
                and "fid" in f]
    # forgotten whose pair has no other active facts
    active_pairs: dict[tuple[int, str], int] = {}
    for oi, f in facts.items():
        if f["active"]:
            active_pairs[(f["subj"], f["rel"])] = \
                active_pairs.get((f["subj"], f["rel"]), 0) + 1
    forg = [oi for oi in forg_all
            if active_pairs.get((facts[oi]["subj"], facts[oi]["rel"]), 0) == 0]
    assert len(plain) >= 1200, f"plain pool {len(plain)}"
    assert len(corr) >= 400, f"corr pool {len(corr)}"
    assert len(forg) >= 200, f"forg pool {len(forg)}"

    one = []
    for oi in rng.sample(plain, 1200):
        f = facts[oi]
        one.append((names[f["subj"]], [f["rel"]],
                    pair_answer(facts, f["subj"], f["rel"]), "plain"))
    for oi in rng.sample(corr, 400):
        f = facts[oi]
        one.append((names[f["subj"]], [f["rel"]],
                    pair_answer(facts, f["subj"], f["rel"]), "corrected"))
    for oi in rng.sample(forg, 200):
        f = facts[oi]
        one.append((names[f["subj"]], [f["rel"]], None, "forgotten"))
    ever = {(f["subj"], f["rel"]) for f in facts.values()}
    never = []
    while len(never) < 200:
        s = rng.randrange(len(names))
        r = rng.choice(list({f["rel"] for f in facts.values()}))
        if (s, r) not in ever:
            ever.add((s, r))
            never.append((names[s], [r], None, "never"))
    one.extend(never)

    ent_active = [oi for oi, f in facts.items()
                  if f["active"] and f["is_entity"] and f["val_ent"] is not None]
    two = []
    used = 0
    order = rng.sample(ent_active, len(ent_active))
    for oi in order:
        if len(two) >= 1000:
            break
        f1 = facts[oi]
        e = f1["val_ent"]
        cands = [(o2, f2) for o2, f2 in facts.items()
                 if f2["active"] and f2["subj"] == e]
        if not cands:
            continue
        cands.sort(key=lambda r: (r[1]["rel"] not in gt["functional"], r[0]))
        o2, f2 = cands[0]
        two.append((names[f1["subj"]], [f1["rel"], f2["rel"]],
                    pair_answer(facts, e, f2["rel"]), oi, o2))
        used += 1
    assert len(two) >= 1000, f"two-hop pool {len(two)}"

    def run(asks):
        lat, res = [], {"right": 0, "wrong": 0, "miss_should_answer": 0,
                        "answered_should_not": 0, "other": 0}
        wrong_rows = []
        for name, rels, exp, *extra in asks:
            t = time.perf_counter()
            r = nb.ask(name, rels)
            lat.append((time.perf_counter() - t) * 1000.0)
            if exp is None:
                if r.status == "MISSING_FACT":
                    res["right"] += 1
                elif r.status == "OK":
                    res["answered_should_not"] += 1
                    wrong_rows.append({"ask": [name, rels], "expected": None,
                                       "got": r.detail.get("answer"),
                                       "status": r.status})
                else:
                    res["other"] += 1
                    wrong_rows.append({"ask": [name, rels], "expected": None,
                                       "got": None, "status": r.status})
            else:
                if r.status == "OK" and r.detail.get("answer") == exp:
                    res["right"] += 1
                elif r.status == "OK":
                    res["wrong"] += 1
                    wrong_rows.append({"ask": [name, rels], "expected": exp,
                                       "got": r.detail.get("answer"),
                                       "status": r.status})
                elif r.status == "MISSING_FACT":
                    res["miss_should_answer"] += 1
                    wrong_rows.append({"ask": [name, rels], "expected": exp,
                                       "got": None, "status": r.status})
                else:
                    res["other"] += 1
                    wrong_rows.append({"ask": [name, rels], "expected": exp,
                                       "got": None, "status": r.status})
        lat.sort()
        n = len(lat)
        pct = lambda q: lat[min(n - 1, int(q * n))]
        return {"n": n, "p50_ms": pct(0.50), "p99_ms": pct(0.99),
                "max_ms": lat[-1], "score": res, "wrong_rows": wrong_rows}

    one_res = run(one)
    two_asks = [(a, b, c) for a, b, c, _, _ in two]
    two_res = run(two_asks)
    out = {"open_s": open_s, "one_hop": {k: v for k, v in one_res.items()
                                         if k != "wrong_rows"},
           "two_hop": {k: v for k, v in two_res.items() if k != "wrong_rows"},
           "wrong_rows": one_res["wrong_rows"] + [
               {**w, "two_hop": True} for w in two_res["wrong_rows"]],
           "maxrss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    Path(args.out).write_text(json.dumps(out), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "wrong_rows"}),
          flush=True)
    return 0


def cmd_crashchild(args) -> int:
    factory = load_factory(args.factory)
    rng = random.Random(args.seed)
    outdir = Path(args.dir)
    outdir.mkdir(parents=True, exist_ok=True)
    nb = factory(str(outdir))
    nb.declare_relation(f"crash-rel-{args.seed}", "pal", False)
    eids = []
    for i in range(20):
        r = nb.new_entity(f"crash-{args.seed}-e{i}",
                          f"Crashper{args.seed} Son{i}")
        eids.append(r.detail["entity_id"])
    ack = open(args.ack, "a", encoding="utf-8")
    for i in range(args.n):
        eid = eids[i % len(eids)]
        ev = f"crash-{args.seed}-{i:05d}"
        r = nb.assert_fact(ev, "listening", "taught", eid, "pal",
                           {"literal": f"Town{i}"}, raw=f"crash {i}")
        if r.status == "SAVED":
            ack.write(ev + "\n")
            ack.flush()
            os.fsync(ack.fileno())
    ack.close()
    return 0


def cmd_crash(args) -> int:
    factory = load_factory(args.factory)
    rng = random.Random(args.seed)
    work = Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)
    per_child = args.per_child
    ack_lost, dups, failed, torn = 0, 0, 0, 0
    clean_finish = 0
    details = []
    for j in range(args.children):
        d = work / f"crash-{j:02d}"
        if d.exists():
            shutil.rmtree(d)
        ack = work / f"ack-{j:02d}.txt"
        if ack.exists():
            ack.unlink()
        proc = subprocess.Popen(
            [sys.executable, "-B", __file__, "crashchild",
             "--factory", args.factory or "", "--dir", str(d),
             "--ack", str(ack), "--n", str(per_child),
             "--seed", str(args.seed + j)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Wait until the child is mid-write (first ack line fsynced), so the
        # random-moment SIGKILL below lands during writing, not during
        # interpreter startup. A child that exits first counts as clean.
        waited = 0.0
        while waited < 120.0:
            if proc.poll() is not None:
                break
            if ack.exists() and ack.stat().st_size > 0:
                break
            time.sleep(0.02)
            waited += 0.02
        time.sleep(rng.uniform(0.05, 2.0))
        killed = True
        if proc.poll() is None:
            proc.send_signal(signal.SIGKILL)
            proc.wait()
        else:
            killed = False
            clean_finish += 1
        acked = ack.read_text(encoding="utf-8").split() if ack.exists() else []
        try:
            nb = factory(str(d))
            opened = True
        except Exception as exc:  # noqa: BLE001
            failed += 1
            details.append({"child": j, "killed": killed,
                            "failed_open": type(exc).__name__})
            continue
        if getattr(nb, "torn_tail", False):
            torn += 1
            nb.repair_torn_tail()
            nb = factory(str(d))
        present = set(getattr(nb, "event_ids", set()))
        lost = [e for e in acked if e not in present]
        ack_lost += len(lost)
        seen: set[str] = set()
        nd = 0
        log = d / "events.jsonl"
        # A child killed before its first append leaves no log at all:
        # that is an empty store, not a duplicate.
        raw_lines = log.read_text(encoding="utf-8").split("\n") \
            if log.exists() else []
        for line in raw_lines:
            if not line.strip():
                continue
            try:
                ev = json.loads(line).get("event_id")
            except ValueError:
                continue
            if ev in seen:
                nd += 1
            seen.add(ev)
        dups += nd
        details.append({"child": j, "killed": killed, "acked": len(acked),
                        "lost": len(lost), "dup": nd,
                        "torn": bool(getattr(nb, "torn_tail", False))})
    out = {"children": args.children, "per_child": per_child,
           "clean_finish": clean_finish, "killed": args.children - clean_finish,
           "acked_but_lost": ack_lost, "duplicates": dups,
           "failed_opens": failed, "torn_tails": torn, "details": details}
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "details"}),
          flush=True)
    return 0


def cmd_tamper(args) -> int:
    factory = load_factory(args.factory)
    rng = random.Random(args.seed)
    work = Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)
    src = Path(args.dir) / "events.jsonl"
    lines = src.read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    caught, missed = 0, []
    for k in range(args.copies):
        d = work / f"tamper-{k:02d}"
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(args.dir, d)
        idx = rng.randrange(len(lines) - 1)  # never the final line
        raw = bytearray(lines[idx].encode("utf-8"))
        pos = rng.randrange(len(raw))
        raw[pos] = (raw[pos] + 1) % 256
        lines2 = list(lines)
        lines2[idx] = raw.decode("utf-8", errors="surrogateescape")
        (d / "events.jsonl").write_text("\n".join(lines2) + "\n",
                                        encoding="utf-8")
        try:
            factory(str(d))
            missed.append({"copy": k, "line": idx + 1, "offset": pos})
        except Exception:  # noqa: BLE001 LogCorrupt expected
            caught += 1
    out = {"copies": args.copies, "caught": caught, "missed": missed}
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({"copies": args.copies, "caught": caught,
                      "missed_n": len(missed)}), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="nb-320 scale runner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--factory", default=None)
        p.add_argument("--dir", required=True)
        p.add_argument("--out", required=True)

    p = sub.add_parser("write")
    common(p)
    p.add_argument("--workload", required=True)
    p.add_argument("--gt", required=True)

    p = sub.add_parser("open")
    common(p)

    p = sub.add_parser("probe")
    common(p)
    p.add_argument("--gt", required=True)
    p.add_argument("--seed", type=int, default=3200)

    p = sub.add_parser("crash")
    p.add_argument("--factory", default=None)
    p.add_argument("--workdir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--children", type=int, default=30)
    p.add_argument("--per-child", type=int, default=3000)
    p.add_argument("--seed", type=int, default=3200)

    p = sub.add_parser("crashchild")
    p.add_argument("--factory", default=None)
    p.add_argument("--dir", required=True)
    p.add_argument("--ack", required=True)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)

    p = sub.add_parser("tamper")
    p.add_argument("--factory", default=None)
    p.add_argument("--dir", required=True)
    p.add_argument("--workdir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--copies", type=int, default=20)
    p.add_argument("--seed", type=int, default=3201)

    args = parser.parse_args()
    if args.factory == "":
        args.factory = None
    return {"write": cmd_write, "open": cmd_open, "probe": cmd_probe,
            "crash": cmd_crash, "crashchild": cmd_crashchild,
            "tamper": cmd_tamper}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
