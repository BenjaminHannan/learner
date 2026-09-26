#!/usr/bin/env python3
"""sf-401 diagnosis (report only, $0; written before the seal so a FAIL is explained without a rerun). New file only.
Prints counts only, never words.

  python3 scripts/claude_sf401_diag.py BANK RUN JUDGE_OUT J1 J2 [J3]

BANK = the sealed panel dir; RUN = the run dir with arm_A.jsonl, arm_B.jsonl and sf401_events_B.jsonl (SF401_EVENTS);
JUDGE_OUT, J1, J2, J3 as for claude_sf401_judges.py marks (the final verdict is judge 1 and 2 when they agree, else 3).

Joins B's per-turn guard events to the panel by life (the runner's temp dir name holds it) and sha1 of the user's
words, in turn order. Then:
  corrections: per correction style, correction turns the reader framed (act not None) and turns that raised a doubt;
  B's judged-wrong edit asks, each in exactly one class:
    W1 no live doubt at the ask, no doubt ever raised in that life before it   (the reader never saw the change)
    W2 no live doubt at the ask, but one was raised earlier and cleared         (repeat or "no")
    W3 a live doubt, the reply names none of them                               (wrong value came from elsewhere)
    W4 the reply names a doubted value, the guard did not fire                  (explained_skip, or reply was a question)
    W5 the guard fired (confirm or hedge) and the reply was still judged wrong
    W0 no event row matched the ask (join failure; reported, never guessed)
  the same classes for A's judged-wrong edit asks at the same (life, turn), using B's events (what the guard saw);
  B's control asks where the guard fired, split by the mechanical class A got there (harm surface).
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SEED401 = 4011
ld = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]  # noqa: E731


def sha(text: str) -> str:
    return hashlib.sha1(str(text).encode("utf-8")).hexdigest()[:16]


def final_verdicts(score: Path, out: Path, j1: Path, j2: Path, j3: Path | None) -> dict:
    """(arm, life, turn) -> "wrong" | "ok", in the same prep order as claude_sf401_judges.py."""
    v = [{r["id"]: r["verdict"] for r in ld(p)} for p in (j1, j2)]
    v3 = {r["id"]: r["verdict"] for r in ld(j3)} if j3 else {}
    key = json.loads((out / "key_asks.json").read_text(encoding="utf-8"))
    rows = []
    for arm in ("A", "B"):
        for p in ld(score / f"judge_asks_{arm}.jsonl"):
            rows.append((arm, p["life_id"], p["turn_index"]))
    random.Random(SEED401).shuffle(rows)
    res = {}
    for i, (arm, life, ti) in enumerate(rows):
        pid = f"Q{i:04d}"
        assert key[pid] == arm, "prep order mismatch"
        a, b = v[0].get(pid), v[1].get(pid)
        res[(arm, life, ti)] = a if a == b else v3.get(pid, "missing")
    return res


def life_of(d: str, lives: list) -> str | None:
    m = re.search(r"e2e336-(.+?)-[^-/\\]*$", Path(d).name)
    if m and m.group(1) in lives:
        return m.group(1)
    hits = [x for x in lives if f"e2e336-{x}-" in d]
    return hits[0] if len(hits) == 1 else None


def join(turns: list, events: list) -> dict:
    """(life, turn_index) -> event row, matching each life's events to its panel turns in order by sha."""
    by_life = defaultdict(list)
    for t in sorted(turns, key=lambda t: (t["life_id"], t["turn_index"])):
        by_life[t["life_id"]].append(t)
    ev_life = defaultdict(list)
    lives = list(by_life)
    unmatched = 0
    for e in events:
        life = life_of(e.get("dir", ""), lives)
        if life is None:
            unmatched += 1
            continue
        ev_life[life].append(e)
    out = {}
    for life, ts in by_life.items():
        i = 0
        for e in ev_life.get(life, []):
            j = i
            while j < len(ts) and sha(ts[j]["user_text"]) != e["sha"]:
                j += 1
            if j == len(ts):
                continue                      # a confirm answer ("yes"/"no") the runner sent: not a panel turn
            out[(life, ts[j]["turn_index"])] = e
            i = j + 1
    out["_unmatched_dirs"] = unmatched
    return out


def main() -> int:
    bank, run, jout = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    j1, j2 = Path(sys.argv[4]), Path(sys.argv[5])
    j3 = Path(sys.argv[6]) if len(sys.argv) > 6 else None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import claude_e2e336_score as SC
    turns = ld(bank / "turns.jsonl")
    tk = {(t["life_id"], t["turn_index"]): t for t in turns}
    corr = ld(bank / "corrections.jsonl")
    ev = join(turns, ld(run / "sf401_events_B.jsonl"))
    final = final_verdicts(run.parent / "score", jout, j1, j2, j3)
    unmatched = ev.pop("_unmatched_dirs")
    report = {"events_matched": len(ev), "event_dirs_unmatched": unmatched, "panel_turns": len(turns)}
    # corrections
    cs = defaultdict(Counter)
    raised_at = defaultdict(list)             # life -> turn indexes where a doubt was raised
    for (life, ti), e in ev.items():
        if any(k.startswith("doubt_") for k in e.get("delta", {})):
            raised_at[life].append(ti)
    for c in corr:
        e = ev.get((c["life_id"], c["turn_index"]))
        s = str(c.get("style"))
        cs[s]["turns"] += 1
        cs[s]["no_event"] += e is None
        cs[s]["framed"] += bool(e and e.get("act"))
        cs[s]["doubt_raised"] += bool(e and any(k.startswith("doubt_") for k in e.get("delta", {})))
    report["corrections_by_style"] = {k: dict(v) for k, v in sorted(cs.items())}
    # classes
    arms = {a: ld(run / f"arm_{a}.jsonl") for a in ("A", "B")}
    confs = {a: {(r["life_id"], r["turn_index"]): r for r in rows if r["kind"] == "confirm_answer"}
             for a, rows in arms.items()}
    mech = {a: {} for a in arms}
    for a, rows in arms.items():
        for r in rows:
            t = tk.get((r["life_id"], r["turn_index"]))
            if r["kind"] == "user" and t is not None and t["kind"] == "ask":
                mech[a][(r["life_id"], r["turn_index"])] = SC.score_ask(t, r, confs[a].get((r["life_id"],
                                                                                          r["turn_index"])))

    def cls(life, ti):
        e = ev.get((life, ti))
        if e is None:
            return "W0"
        d = e.get("delta", {})
        if d.get("fired"):
            return "W5"
        if e.get("live_named"):
            return "W4"
        if e.get("live"):
            return "W3"
        return "W2" if any(x < ti for x in raised_at.get(life, [])) else "W1"

    for a in ("A", "B"):
        c = Counter()
        for (arm, life, ti), v in final.items():
            if arm == a and v == "wrong" and tk[(life, ti)]["ask_type"] == "edit":
                c[cls(life, ti)] += 1
        report[f"wrong_edit_{a}_by_class"] = dict(sorted(c.items()))
    harm = Counter()
    for (life, ti), e in ev.items():
        t = tk.get((life, ti))
        if t is None or t["kind"] != "ask" or t["ask_type"] == "edit" or not e.get("delta", {}).get("fired"):
            continue
        harm[f'{t["ask_type"]}:A_{mech["A"].get((life, ti), "none")}'] += 1
    report["guard_fired_on_non_edit_asks"] = dict(sorted(harm.items()))
    fired_edit = Counter(mech["A"].get((life, ti), "none") for (life, ti), e in ev.items()
                         if tk.get((life, ti), {}).get("ask_type") == "edit" and e.get("delta", {}).get("fired"))
    report["guard_fired_on_edit_asks_by_A_class"] = dict(sorted(fired_edit.items()))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
