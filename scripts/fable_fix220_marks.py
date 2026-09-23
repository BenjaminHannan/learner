#!/usr/bin/env python3
"""Exp 220 -- R1/R2/R3/R6 driver (scorer only; agent code read-only).

In-process loop.turn() drives (the same turn path the daemon calls) with
an isolated scratch state dir per arm. Restart = rebuild the agent object
on the same state dir (notebook _load from disk, the restart path under
test). NEVER touches the repo-root notebook/.

  python -B scripts/fable_fix220_marks.py --mode r1|r2|r3|r6 \\
    --agent base|fixed --cases <cases220.json> --out <dir> [--limit N]
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_agent(which: str):
    if which == "base":
        import fable_loop138i_agent as M
        return M, M.DEFAULT_CONFIG138I, M.build_agent138i
    if which == "fixed":
        import fable_loop220_agent as M
        return M, M.DEFAULT_CONFIG220, M.build_agent220
    raise ValueError(which)


def fresh_cfg(default_cfg: dict, workdir: Path) -> dict:
    cfg = copy.deepcopy(default_cfg)
    cfg["state_dir"] = str(workdir)
    cfg["sleep_threshold"] = 100000
    return cfg


def drive(loop, turns: list[str]) -> list[str]:
    out = []
    for t in turns:
        out.append(" ".join(loop.turn(t)))
    return out


def inner_of(loop):
    return loop.nb.nb


def run_r1(which: str, cases: dict, out: Path, limit: int | None) -> dict:
    from fable_fix220_restartindex import index_state
    _, default_cfg, build = load_agent(which)
    rows = []
    for h in cases["histories"][:limit]:
        snaps = {}
        for tag, nres in (("r0a", 0), ("r0b", 0), ("r1", 1), ("r2", 2)):
            d = out / "work" / which / h["id"] / tag
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)
            turns = h["turns"]
            chunks = split(turns, nres + 1)
            loop = build(fresh_cfg(default_cfg, d))
            for i, ch in enumerate(chunks):
                drive(loop, ch)
                if i < nres:
                    loop = build(fresh_cfg(default_cfg, d))
            snaps[tag] = index_state(inner_of(loop))
        c = {"det": snaps["r0a"] == snaps["r0b"],
             "r1": snaps["r0a"] == snaps["r1"],
             "r2": snaps["r0a"] == snaps["r2"]}
        rows.append({"id": h["id"], **{k: bool(v) for k, v in c.items()}})
    n_eq = sum(sum(1 for k in ("det", "r1", "r2") if r[k]) for r in rows)
    # R1 counts 3 comparisons per history (determinism + 1 + 2 restarts).
    rep = {"mode": "r1", "agent": which, "n_histories": len(rows),
           "comparisons": 3 * len(rows), "equal": n_eq, "rows": rows}
    (out / f"r1-{which}.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"R1 {which}: {n_eq}/{3 * len(rows)} equal", flush=True)
    return rep


def split(turns: list[str], k: int) -> list[list[str]]:
    n = len(turns)
    return [turns[(i * n) // k:((i + 1) * n) // k] for i in range(k)]


def ghost_run(which: str, g: dict, root: Path):
    import fable_loop90_agent as L90
    _, default_cfg, build = load_agent(which)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    loop = build(fresh_cfg(default_cfg, root))
    teaches = [f"{g['A']}'s boss is {g['B']}.", f"{g['B']}'s city is {g['V']}."]
    if g.get("C"):
        teaches.append(f"{g['C']}'s boss is {g['A']}.")
    drive(loop, teaches)
    loop = build(fresh_cfg(default_cfg, root))  # restart
    forget_reply = drive(loop, [f"Forget {g['B']}'s city."])[0]
    rev = drive(loop, [f"Whose city is {g['V']}?"])[0]
    fwd = drive(loop, [f"What is {g['B']}'s city?"])[0]
    chn = drive(loop, [f"What is {g['A']}'s boss's city?"])[0]
    triples = L90.notebook_triples(loop.nb)
    inner = inner_of(loop)
    cur = inner.current(
        inner.resolve(g["B"]).detail["entity_id"]
        if inner.resolve(g["B"]).status == "OK" else "E0000", "city")
    leak_replies = [r for r in (rev, fwd, chn) if g["V"] in r]
    leak_triples = [t for t in triples if tuple(t) == (g["B"], "city", g["V"])]
    abstains = [("don't know" in r or "do not know" in r or "never told me" in r)
                for r in (rev, fwd, chn)]
    return {
        "id": g["id"], "forget_reply": forget_reply,
        "reverse": rev, "forward": fwd, "chain": chn,
        "triples": [list(t) for t in triples],
        "current_after_forget": [
            {"fact_id": r["fact_id"], "source": r["source"]} for r in cur],
        "value_in_replies": [r for r in (rev, fwd, chn) if g["V"] in r],
        "value_in_triples": [list(t) for t in leak_triples],
        "all_abstain": all(abstains),
        # PASS = every probe abstains (no positive answer naming the
        # forgotten link) AND the triple is gone. (Abstain templates echo
        # the question's value, e.g. "I don't know anyone whose city is
        # Oslo." -- that echo is correct behaviour, not a leak.)
        "pass": all(abstains) and not leak_triples,
    }


def run_r2(which: str, cases: dict, out: Path, limit: int | None) -> dict:
    rows = [ghost_run(which, g, out / "work" / which / g["id"])
            for g in cases["ghosts"][:limit]]
    n_pass = sum(1 for r in rows if r["pass"])
    rep = {"mode": "r2", "agent": which, "n_cases": len(rows),
           "pass": n_pass, "rows": rows}
    (out / f"r2-{which}.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"R2 {which}: {n_pass}/{len(rows)} clean", flush=True)
    return rep


def run_r3(which: str, cases: dict, out: Path, limit: int | None) -> dict:
    _, default_cfg, build = load_agent(which)
    rows = []
    for h in cases["histories"][:limit]:
        arms = {}
        for nres in (0, 1, 2):
            d = out / "work" / f"{which}-q" / h["id"] / f"r{nres}"
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)
            chunks = split(h["turns"], nres + 1)
            loop = build(fresh_cfg(default_cfg, d))
            for i, ch in enumerate(chunks):
                drive(loop, ch)
                if i < nres:
                    loop = build(fresh_cfg(default_cfg, d))
            arms[nres] = drive(loop, h["questions"])
        ok = arms[0] == arms[1] == arms[2]
        rows.append({"id": h["id"], "identical": ok,
                     "replies": arms[0] if not ok else None,
                     "r1": None if ok else arms[1],
                     "r2": None if ok else arms[2]})
    n_ok = sum(1 for r in rows if r["identical"])
    n_q = sum(len(h["questions"]) for h in cases["histories"][:limit])
    rep = {"mode": "r3", "agent": which, "n_histories": len(rows),
           "n_questions_each": 10, "n_replies": n_q * 3,
           "histories_identical": n_ok, "rows": rows}
    (out / f"r3-{which}.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"R3 {which}: {n_ok}/{len(rows)} histories byte-identical "
          f"({n_q} questions x3 arms)", flush=True)
    return rep


def build_log_5k(nbdir: Path, n_fact: int = 5000) -> None:
    import fable_notebook_contract as C
    if nbdir.exists():
        shutil.rmtree(nbdir)
    nb = C.Notebook(nbdir)
    nb.declare_relation("rel-boss", "boss", True)
    nb.declare_relation("rel-city", "city", True)
    eids = [nb.new_entity(f"ent-{i:05d}", f"Resident{i:05d}").detail["entity_id"]
            for i in range(3200)]
    boss_k = 0
    for i in range(n_fact):
        s = eids[i % 600]
        if i % 2 == 0:
            boss_k += 1
            nb.assert_fact(f"ev-b-{i:06d}", "listening", "taught", s, "boss",
                           {"entity": eids[600 + boss_k]})
        else:
            nb.assert_fact(f"ev-c-{i:06d}", "listening", "taught", s, "city",
                           {"literal": f"Town{i:06d}"}, correction=True)
    assert len(nb.events) >= n_fact, len(nb.events)


def run_r6(which: str, out: Path) -> dict:
    import fable_perf128_index as P128
    from fable_fix220_restartindex import FixedIndexedLoopNotebook
    classes = {"fixed": FixedIndexedLoopNotebook,
               "base": P128.IndexedLoopNotebook}
    base = out / "work" / "loadlogs"
    if base.exists():
        shutil.rmtree(base)
    src = base / "src"
    build_log_5k(src)
    n_events = sum(1 for _ in (src / "events.jsonl").read_text(
        encoding="utf-8").splitlines() if _.strip())
    order = ["fixed", "base"] if which == "both" else [which]
    if which == "both":
        # Warmup (discarded): settle the file cache before timing.
        for name in ("base", "fixed"):
            dst = base / f"warm-{name}"
            shutil.copytree(src, dst)
            classes[name](dst)
            shutil.rmtree(dst)
    reps: dict = {name: {"wall_s": [], "process_s": []} for name in order}
    for rep in range(5 if which == "both" else 3):
        for name in (list(reversed(order)) if rep % 2 else order):
            dst = base / f"{name}-{rep}"
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            t0 = time.process_time()
            w0 = time.time()
            nb = classes[name](dst)
            w1 = time.time()
            p1 = time.process_time()
            assert len(nb.events) == n_events
            assert len(nb.nb.events) == n_events
            reps[name]["wall_s"].append(round(w1 - w0, 3))
            reps[name]["process_s"].append(round(p1 - t0, 3))
    rep = {"mode": "r6", "agent": which, "n_events": n_events,
           "arms": reps}
    if which != "both":
        rep.update({"wall_s": reps[which]["wall_s"],
                    "process_s": reps[which]["process_s"]})
    (out / f"r6-{which}.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    print(f"R6 {which}: events={n_events} " +
          " ".join(f"{k} wall={v['wall_s']} proc={v['process_s']}"
                    for k, v in reps.items()), flush=True)
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 220 marks driver")
    ap.add_argument("--mode", required=True, choices=["r1", "r2", "r3", "r6"])
    ap.add_argument("--agent", required=True, choices=["base", "fixed", "both"])
    ap.add_argument("--cases", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = (json.loads(Path(args.cases).read_text(encoding="utf-8"))
             if args.cases else {"histories": [], "ghosts": []})
    t0 = time.time()
    if args.mode == "r1":
        run_r1(args.agent, cases, out, args.limit)
    elif args.mode == "r2":
        run_r2(args.agent, cases, out, args.limit)
    elif args.mode == "r3":
        run_r3(args.agent, cases, out, args.limit)
    elif args.mode == "r6":
        run_r6(args.agent, out)
    print(f"done {args.mode}-{args.agent} in {round(time.time() - t0, 1)}s",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
