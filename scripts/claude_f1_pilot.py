#!/usr/bin/env python3
"""Exp F1 dev pilot: 292t vs F1 on the builder's own dev turns.

New file only. Fictional names, everyday wording; dev material only, never
the blind panels. Both arms run read-only (imports only).

Per dev case, one fresh agent per arm; turns run in order on both arms.
Compares per turn: reply text (changed lines listed with route/act/why),
notebook events grown, stored triples. Prints integer counts:
  turns, changed lines, route counts (A/legacy/passthrough), sev-1 count,
  store-diff turns (must be 0), crash turns (must be 0).

Usage:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_f1_pilot.py \
    artifacts/claude-f1-20260923/devcasesf1.json \
    artifacts/claude-f1-20260923/pilot/pilot.json
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def triples_of(loop) -> list:
    import fable_loop90_agent as L90
    try:
        t = [[s, r, v] for (s, r, v) in L90.notebook_triples(loop.nb)]
    except Exception:  # noqa: BLE001
        return ["<unreadable>"]
    t.sort()
    return t


def events_of(loop) -> int:
    try:
        return len(loop.nb.events)
    except Exception:  # noqa: BLE001
        return -1


def run_case(arm_mod, cfg, turns):
    import tempfile as _tf
    c = copy.deepcopy(cfg)
    tmp = _tf.mkdtemp(prefix="f1pilot-")
    c["state_dir"] = tmp
    c["sleep_threshold"] = 100000
    loop = arm_mod.build_agent292t(c) if hasattr(arm_mod, "build_agent292t") \
        else arm_mod.build_agentf1(c)
    rows = []
    try:
        for t in turns:
            e0 = events_of(loop)
            try:
                rep = loop.turn(t)
                crash = None
            except Exception as e:  # noqa: BLE001
                rep, crash = [], f"{type(e).__name__}: {e}"
            e1 = events_of(loop)
            rows.append({"turn": t, "reply": list(rep or []), "crash": crash,
                         "ev_grown": (e1 - e0) if e0 >= 0 else -999,
                         "triples": triples_of(loop)})
        stats = dict(getattr(loop, "mouth241b_stats", {}) or {})
        log = list(getattr(loop, "mouth241b_log", []) or [])
    finally:
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            del loop
        except Exception:  # noqa: BLE001
            pass
    return rows, stats, log


def main() -> int:
    import claude_loop292t_agent as T292T
    import claude_loopf1_agent as F1

    src, dst = sys.argv[1], sys.argv[2]
    cases = json.load(open(src))["cases"]
    base_cfg = copy.deepcopy(T292T.DEFAULT_CONFIG292T)

    n_turns = n_changed = n_store_diff = n_crash = 0
    route_counts: dict[str, int] = {}
    changed = []
    case_rows = []
    agg_stats: dict[str, int] = {}
    for case in cases:
        turns = case["turns"]
        r292, _s292, _l292 = run_case(T292T, base_cfg, turns)
        rf1, sf1, lf1 = run_case(F1, base_cfg, turns)
        for k, v in sf1.items():
            agg_stats[k] = agg_stats.get(k, 0) + int(v)
        rows = []
        log_by_in = {}
        for e in lf1:
            log_by_in.setdefault(e["in"], []).append(e)
        for i, (a, b) in enumerate(zip(r292, rf1)):
            n_turns += 1
            ra = " ".join(a["reply"]) if a["reply"] else ""
            rb = " ".join(b["reply"]) if b["reply"] else ""
            if a["crash"] or b["crash"]:
                n_crash += 1
            same_store = (a["triples"] == b["triples"]
                          and a["ev_grown"] == b["ev_grown"])
            if not same_store:
                n_store_diff += 1
            entry = {"case": case["id"], "idx": i, "turn": a["turn"],
                     "reply292t": ra, "replyf1": rb,
                     "changed": ra != rb,
                     "ev292t": a["ev_grown"], "evf1": b["ev_grown"],
                     "store_same": same_store}
            if ra != rb:
                n_changed += 1
                routes = [e["route"] for e in log_by_in.get(a["reply"][0]
                          if a["reply"] else "", [])] or \
                    [e["route"] for e in lf1 if e["turn"] == a["turn"]]
                entry["routes"] = routes
                for e in lf1:
                    if e["turn"] == a["turn"] and e["in"] != e["out"]:
                        entry.setdefault("rewrites", []).append(
                            {"in": e["in"], "out": e["out"],
                             "route": e["route"], "act": e["act"],
                             "why": e.get("why")})
                        route_counts[e["route"]] = \
                            route_counts.get(e["route"], 0) + 1
                changed.append(entry)
            rows.append(entry)
        case_rows.append({"id": case["id"], "n": len(turns), "rows": rows})

    sev1 = agg_stats.get("sev1", 0)
    legacy = agg_stats.get("legacy", 0)
    out = {"n_turns": n_turns, "n_changed_turns": n_changed,
           "route_counts_changed": route_counts,
           "mouth_stats_f1": agg_stats, "sev1": sev1, "legacy": legacy,
           "n_store_diff_turns": n_store_diff, "n_crash_turns": n_crash,
           "cases": case_rows}
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                         encoding="utf-8")
    print(f"turns={n_turns} changed_turns={n_changed} "
          f"routes={route_counts} stats={agg_stats} "
          f"store_diff={n_store_diff} crash={n_crash}")
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
