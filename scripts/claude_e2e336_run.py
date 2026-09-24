#!/usr/bin/env python3
"""336 end-to-end runner: 3-day lives with sleeps, restarts and a simulated user
for "is that right?" questions (month-end line; spec design/v3/30-modes/331-e2e-bank-spec.md,
plan design/v3/30-modes/330-month-end-plan.md section 4).

New file only. It never edits agent code. For every life:
  day 1 turns -> end of day (one forced sleep) -> kill + restart from the same state dir
  day 2 turns -> end of day -> kill + restart
  day 3 turns -> end of day
After each reply, if the reply asks the user to confirm something (CONFIRM_MARKERS),
the harness sends ONE mechanical "yes" or "no" taken from the life's truth sheet
(truth.jsonl, facts valid at that turn) and records it as its own row
(kind "confirm_answer"). That count is Ben's attention cost.

Arms are named by --arm "module:function". The function is called as
function(state_dir, args) and must return an object with .turn(text) -> list[str].
Optional hooks on that object:
  .e2e_end_day()      run the end-of-day sleep (default for AgentLoop-like objects:
                      sleep_threshold 0 for one step(), then restored)
  .nb                 a notebook; stored triples are then logged via fable_loop90_agent
Built-in arms: "292t" (292t alone), "twin" (claude_e2e336_twin:build).

Output: <out>/arm_<name>.jsonl, one row per user turn or confirm answer:
  life_id, day, turn_index, kind ("user" | "confirm_answer"), reply, ms,
  notebook_events (new events this row), stored_triples (after the row),
  confirm_asked (bool), confirm_answer ("yes" | "no" | null)
User text is never printed or copied into the output (the bank may be TEST-ONLY).

Usage (Mac or BensPC, builder-outbox scripts on the path):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_e2e336_run.py --bank DIR --arm 292t --out DIR
"""
from __future__ import annotations

import argparse
import copy
import gc
import importlib
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Lowercase substrings. A reply that contains one of these AND a "?" asks the user
# to confirm something. Fixed before any run; taken from agent wording
# (lis-310 "Just to check: ...?", lis-314 "I think you told me ..., is that right?").
CONFIRM_MARKERS = [
    "is that right?",
    "just to check",
    "did i get that right",
    "is that correct?",
    "am i right that",
]

BUILTIN_ARMS = {
    "292t": "claude_e2e336_run:build_292t",
    "twin": "claude_e2e336_twin:build",
}


def load(p: Path) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def build_292t(state_dir: str, args) -> object:
    import claude_loop292t_agent as T292
    cfg = copy.deepcopy(T292.DEFAULT_CONFIG292T)
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000     # no mid-day sleep; the harness sleeps once per day
    return T292.build_agent292t(cfg)


def resolve_arm(name: str):
    spec = BUILTIN_ARMS.get(name, name)
    mod, _, fn = spec.partition(":")
    if not fn:
        raise SystemExit(f"336: arm {name!r} must be 'module:function'")
    return getattr(importlib.import_module(mod), fn)


def end_day(agent) -> None:
    hook = getattr(agent, "e2e_end_day", None)
    if callable(hook):
        hook()
        return
    if hasattr(agent, "sleep_threshold") and hasattr(agent, "step"):
        old = agent.sleep_threshold
        agent.sleep_threshold = 0
        try:
            agent.step()               # sleep_due() is now true: one sleep tick
        finally:
            agent.sleep_threshold = old
            if hasattr(agent, "_save"):
                agent._save()


def is_confirm(reply: str) -> bool:
    low = reply.lower()
    return "?" in low and any(m in low for m in CONFIRM_MARKERS)


def _mentions(text_low: str, phrase: str) -> bool:
    phrase = phrase.strip().lower()
    if not phrase:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text_low) is not None


def confirm_answer(reply: str, truth: list[dict], turn_index: int) -> str:
    """'yes' iff some fact valid at turn_index has its value named in the reply and its
    owner named too (first name is enough; USER facts count when the reply says you/your/me/my)."""
    low = reply.lower()
    for f in truth:
        if f["taught_turn"] > turn_index:
            continue
        if f.get("valid_until_turn") is not None and f["valid_until_turn"] <= turn_index:
            continue
        if not _mentions(low, str(f["value"])):
            continue
        owner = str(f["owner"])
        if owner == "USER":
            if any(_mentions(low, w) for w in ("you", "your", "you're", "me", "my")):
                return "yes"
            continue
        if _mentions(low, owner) or _mentions(low, owner.split()[0]):
            return "yes"
    return "no"


def triples(agent) -> list | None:
    nb = getattr(agent, "nb", None)
    if nb is None:
        return None
    import fable_loop90_agent as L90
    return sorted([s, r, v] for (s, r, v) in L90.notebook_triples(nb))


def events_len(agent) -> int:
    nb = getattr(agent, "nb", None)
    return len(nb.events) if nb is not None else 0


def one(agent, text: str) -> tuple[str, float, list]:
    ev0 = events_len(agent)
    t0 = time.time()
    parts = agent.turn(text)
    ms = (time.time() - t0) * 1000
    reply = " ".join(p for p in (parts or []) if p)
    nb = getattr(agent, "nb", None)
    new = [dict(e) for e in list(nb.events)[ev0:]] if nb is not None else []
    return reply, ms, new


def run_life(builder, args, life: str, turns: list[dict], truth: list[dict], rows: list) -> None:
    tmp = tempfile.mkdtemp(prefix=f"e2e336-{life}-")
    agent = builder(tmp, args)
    try:
        days = sorted({t["day"] for t in turns})
        for di, day in enumerate(days):
            for t in [x for x in turns if x["day"] == day]:
                text = t.get("user_text")
                if not isinstance(text, str) or not text.strip():
                    raise SystemExit(f"336: empty text at {life} {t.get('turn_index')}")
                reply, ms, new = one(agent, text)
                asked = is_confirm(reply)
                rows.append({"life_id": life, "day": day, "turn_index": t["turn_index"],
                             "kind": "user", "reply": reply, "ms": round(ms, 1),
                             "notebook_events": new, "stored_triples": triples(agent),
                             "confirm_asked": asked, "confirm_answer": None})
                if asked:
                    ans = confirm_answer(reply, truth, t["turn_index"])
                    reply2, ms2, new2 = one(agent, ans)
                    rows.append({"life_id": life, "day": day, "turn_index": t["turn_index"],
                                 "kind": "confirm_answer", "reply": reply2, "ms": round(ms2, 1),
                                 "notebook_events": new2, "stored_triples": triples(agent),
                                 "confirm_asked": is_confirm(reply2), "confirm_answer": ans})
            end_day(agent)
            if di < len(days) - 1:          # kill + restart from the same state dir
                del agent
                gc.collect()
                agent = builder(tmp, args)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True, help="dir with turns.jsonl and truth.jsonl")
    ap.add_argument("--arm", required=True)
    ap.add_argument("--name", default=None, help="output arm name (default: --arm)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lives", default="", help="comma-separated life ids (default all)")
    ap.add_argument("--model", default="", help="model dir for arms that need one (reader / twin)")
    ap.add_argument("--gen-model", default="", help="base MiniCPM5-1B dir for creative (333)")
    ap.add_argument("--mouth-model", default="", help="mouth model dir (own line)")
    args = ap.parse_args()

    bank = Path(args.bank)
    turns = load(bank / "turns.jsonl")
    truth = load(bank / "truth.jsonl")
    want = {x for x in args.lives.split(",") if x}
    order: list[str] = []
    by: dict[str, list[dict]] = {}
    for t in turns:
        lid = t["life_id"]
        if want and lid not in want:
            continue
        if lid not in by:
            by[lid] = []
            order.append(lid)
        by[lid].append(t)
    for lid in order:
        by[lid].sort(key=lambda x: x["turn_index"])
    truth_by: dict[str, list[dict]] = {}
    for f in truth:
        truth_by.setdefault(f["life_id"], []).append(f)

    builder = resolve_arm(args.arm)
    name = args.name or args.arm.replace(":", "_").replace("/", "_")
    rows: list[dict] = []
    for lid in order:
        run_life(builder, args, lid, by[lid], truth_by.get(lid, []), rows)
        print(f"[336/{name}] {lid} turns={len(by[lid])}", flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"arm_{name}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote arm_{name}.jsonl rows={len(rows)} lives={len(order)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
