#!/usr/bin/env python3
"""Exp 241 M4 pairwise sampler (sealed seed).

1. Builds fictional dialogs from PAIRS_SEED (teach / duplicate / conflict +
   "no" / list / yes-no / reverse / abstain / unknown name / broken chain /
   forget one / forget all / not-had / user facts / self questions).
2. Runs them through the 241 daemon (Loop241Daemon, 228 config) in fresh
   state dirs. Mouth241Mixin logs every reply line (MOUTH241_LOG): "in" is
   the base's own line (the mixin runs after the whole base turn and cannot
   write; M2(c) checks that), "out" is the 241 line.
3. Keeps lines A changed (route A, out != in), draws 120 stratified by act
   (equal share per act, leftovers to the largest strata), puts base and 241
   in random order as X / Y.

Outputs (artifacts/claude-mouth241-20260922/):
  pairs.jsonl      {pair_id, user_turn, X, Y, facts}  -> the judge
  pairs-key.jsonl  {pair_id, act, X, Y ("base"/"241"), dialog, turn}
  pairs-log.jsonl  every logged line (for M2(b) / counts; not for the judge)
Run: uv ... python -B scripts/claude_mouth241_pairs.py [--pilot-seed N]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_mouth241_sweep as SW  # noqa: E402 (name pool only)

REPO = SCRIPTS.parent
ART = REPO / "artifacts/claude-mouth241-20260922"
AGENT = SCRIPTS / "claude_loop241_agent.py"
CONFIG = REPO / "artifacts/claude-determinism228-20260922/loop228-config.json"
PAIRS_SEED = 241_0922_31  # sealed
N_PAIRS = 120
N_DIALOGS = 24

SINGLE_PERSON = ["mother", "boss", "teacher", "coach", "spouse", "father"]
MULTI_PERSON = ["friend", "sister", "brother", "cousin", "neighbour"]
PLACE = ["city", "hometown"]
ORG = ["employer", "school"]


def _name(pool, r):
    return pool.person(r.choice(SW.CLASSES[:3]))


def dialog(pool: SW.Pool, r: random.Random) -> list[str]:
    A, B, Z, Q = (_name(pool, r) for _ in range(4))
    C = [_name(pool, r) for _ in range(3)]
    if r.random() < 0.25:  # the user types a one-word name in lower case
        A = pool.word().lower()
    p1 = pool.entity("place", r.choice(SW.CLASSES))
    p2 = pool.entity("place", "plain")
    p3 = pool.entity("place", "plain")
    org = pool.entity("organization", r.choice(SW.CLASSES))
    sp = r.choice(SINGLE_PERSON)
    mp = r.choice(MULTI_PERSON)
    pl = r.choice(PLACE)
    og = r.choice(ORG)
    job = pool.entity("literal", r.choice(("plain", "vowel")), "occupation")
    turns = [
        f"{A}'s {pl} is {p1}.",
        f"{A}'s {sp} is {B}.",
        f"{A}'s {mp} is {C[0]}.",
        f"{A}'s {mp} is {C[1]}.",
        f"{A}'s {mp} is {C[2]}.",
        f"{A}'s job is {job}.",
        f"{B}'s {og} is {org}.",
        f"Who is {A}'s {mp}?",
        f"Is {C[0]} {A}'s {mp}?",
        f"Is {A}'s {mp} {Z}?",
        f"Is {A}'s {sp} {Z}?",
        f"What is {A}'s {pl}?",
        f"What is {A}'s job?",
        f"What is {A}'s {sp}'s {og}?",
        f"Who is {A}'s {pl}'s {sp}?",
        f"{A}'s {pl} is {p2}.",
        "no",
        f"{A}'s {sp} is {B}.",
        f"Who is {A}'s {r.choice(['boss', 'teacher', 'coach', 'doctor'])}?",
        f"Who is {Q}'s {sp}?",
        f"Whose {sp} is {B}?",
        f"Forget {A}'s {mp} {C[1]}.",
        f"Forget {A}'s {mp} {Z}.",
        f"Forget {A}'s {pl}.",
        f"What is {A}'s {pl}?",
        f"My {pl} is {p3}.",
        f"What is my {pl}?",
        f"Who is my {sp}?",
        "How many people do you know?",
        "How many facts do you know?",
        "Have you slept?",
        "How many turns have we had?",
        "How many questions have you answered?",
    ]
    return turns


def run_dialogs(dialogs, work: Path, log_path: Path):
    import fable_marks123_all as MK
    mod, dcls, _, _ = MK.load_agent(str(AGENT))
    base = MK.load_base_cfg(str(CONFIG))
    os.environ["MOUTH241_LOG"] = str(log_path)
    if log_path.exists():
        log_path.unlink()
    rows = []
    for i, msgs in enumerate(dialogs):
        root = work / f"d{i:02d}"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = MK.make_daemon(dcls, base, root)
        ctx = []
        for j, t in enumerate(msgs):
            before = _count_lines(log_path)
            f = root / "inbox" / f"m{j:02d}.txt"
            f.write_text(t, encoding="utf-8")
            d.process_file(f)
            new = _read_from(log_path, before)
            for e in new:
                e.update({"dialog": i, "turn_ix": j, "context": list(ctx[-4:])})
                rows.append(e)
            rep = (root / "outbox" / f"m{j:02d}.txt").read_text(
                encoding="utf-8").strip()
            ctx.append({"user": t, "reply": rep})
    return rows


def _count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    with open(p, encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def _read_from(p: Path, n: int) -> list[dict]:
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as fh:
        return [json.loads(x) for k, x in enumerate(fh) if k >= n]


def facts(fr: dict | None) -> list[str]:
    if not fr:
        return []
    out = [f"reply type: {fr['act']}"]
    s = fr.get("subject") or {}
    if s.get("role") == "user":
        out.append("about: the user")
    elif s.get("text"):
        out.append(f"about: {s['text']}")
    if fr.get("path"):
        out.append("relation: " + " -> ".join(fr["path"]))
    if fr.get("values"):
        out.append("value(s): " + "; ".join(fr["values"]))
    for k, lab in (("also_have", "also stored"), ("subjects", "subjects"),
                   ("choices", "choices")):
        if fr.get(k):
            out.append(f"{lab}: " + "; ".join(fr[k]))
    if fr.get("old_value"):
        out.append(f"stored value: {fr['old_value']}; new value offered: "
                   f"{fr['new_value']}")
    if fr.get("count") is not None:
        out.append(f"count: {fr['count']}")
    if fr.get("count2") is not None:
        out.append(f"second count: {fr['count2']}")
    if fr.get("names"):
        out.append("names: " + "; ".join("the user" if n == "USER" else n
                                         for n in fr["names"]))
    return out


def sample(rows, r: random.Random, n=N_PAIRS):
    by = defaultdict(list)
    for e in rows:
        if e["route"] == "A" and e["out"] != e["in"]:
            by[e["act"]].append(e)
    for v in by.values():
        r.shuffle(v)
    acts = sorted(by)
    take = {a: 0 for a in acts}
    left = n
    while left > 0 and any(take[a] < len(by[a]) for a in acts):
        for a in acts:
            if left and take[a] < len(by[a]):
                take[a] += 1
                left -= 1
    chosen = [e for a in acts for e in by[a][:take[a]]]
    r.shuffle(chosen)
    return chosen, {a: (take[a], len(by[a])) for a in acts}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot-seed", type=int, default=None)
    ap.add_argument("--dialogs", type=int, default=N_DIALOGS)
    ap.add_argument("--out", default=str(ART))
    ap.add_argument("--work", required=True, help="scratch state dirs")
    a = ap.parse_args(argv)
    seed = PAIRS_SEED if a.pilot_seed is None else a.pilot_seed
    r = random.Random(seed)
    pool = SW.Pool(seed + 1)
    dialogs = [dialog(pool, r) for _ in range(a.dialogs)]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows = run_dialogs(dialogs, Path(a.work), Path(a.work) / "mouth241.log")
    chosen, strata = sample(rows, r)
    print(f"dialogs {len(dialogs)} lines {len(rows)} wall {time.time()-t0:.0f}s")
    print("strata (taken, available):", strata)
    with open(out / "pairs-log.jsonl", "w", encoding="utf-8") as fh:
        for e in rows:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(out / "pairs.jsonl", "w", encoding="utf-8") as fp, \
            open(out / "pairs-key.jsonl", "w", encoding="utf-8") as fk:
        for k, e in enumerate(chosen):
            pid = f"p{k + 1:03d}"
            base_first = r.random() < 0.5
            X, Y = (e["in"], e["out"]) if base_first else (e["out"], e["in"])
            # no dialog context: earlier replies are 241 text and would
            # tell the judge which side is which
            fp.write(json.dumps({"pair_id": pid, "user_turn": e["turn"],
                                 "X": X, "Y": Y,
                                 "facts": facts(e.get("frame"))},
                                ensure_ascii=False) + "\n")
            fk.write(json.dumps({"pair_id": pid, "act": e["act"],
                                 "X": "base" if base_first else "241",
                                 "Y": "241" if base_first else "base",
                                 "dialog": e["dialog"],
                                 "turn": e["turn_ix"]}) + "\n")
    print("wrote pairs.jsonl / pairs-key.jsonl / pairs-log.jsonl in", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
