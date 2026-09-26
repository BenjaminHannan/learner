#!/usr/bin/env python3
"""q-404: math asked with "you" reaches the thinking step (month-end line, 2026-09-26; problem #3). New file only.

Marks: artifacts/claude-q404-20260926/PASSMARKS-q404.md (registered before this code and before the blind panel).
Written on DEV wordings only; the TEST panel artifacts/claude-panel-q404-20260926 is read only by run and score.

What: claude_think299_agent.is_reasoning() refuses every turn containing you/your/yourself (SELF). q-404 narrows
that one test for arm Q: a turn with you/your is refused only when it asks about the assistant itself or asks it
to recall what the user said (ABOUT). Every other is_reasoning condition is unchanged. The patch is keyed on the
loop (loop.q404 = True), so arm B in the same process is untouched.

  B      = claude_q404:build_b      (build_02c; ROUTE02C per Q404_ROUTE=1 iff 383 is a verified PASS)
  Q      = claude_q404:build_q      (B + q-404)

  python -B scripts/claude_q404.py --selftest                     (no model; the gate on dev cases)
  python -B scripts/claude_readersha_wrap.py scripts/claude_twinb_wrap.py scripts/claude_q404.py run \
      --task math|self --arm claude_q404:build_b|claude_q404:build_q --name B|Q --model READER319 \
      --gen-model BASE --panel-dir PD --out OUT
  python -B scripts/claude_q404.py score --out OUT --panel-dir PD --score SCOREDIR
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_think299_agent as A  # noqa: E402

TURN_SEED = 404_026
ABOUT = re.compile("|".join([
    r"\b(?:who|what) are you\b",
    r"\byour (?:own )?(?:name|age|opinions?|favou?rites?|feelings?|memory|memories|mood|job|purpose|creators?|"
    r"thoughts?|views?|preferences?|abilities|ability|limits?|limitations?|training|mind|notes?|notebook|brain|"
    r"personality|day|life|family|friends?|hobbies|hobby|dreams?|goals?)\b",
    r"\b(?:do|did|can|could|will|would|are|have|were) you (?:still )?(?:remember|recall|like|love|hate|think|feel|"
    r"know|believe|prefer|enjoy|want|wish|mind|dream|sleep|forget|learn|store|save|keep|get tired|get bored|"
    r"have feelings|understand me|agree)\b",
    r"\byourself\b",
    r"\b(?:i|we) (?:told|tell|gave|showed|mentioned|said|asked|taught)\b[^.?!]*\byou\b",
    r"\b(?:i|we)(?:'ve| have) (?:told|given|shown|mentioned|said)\b",
    r"\byou (?:said|told me|mentioned|remembered|promised|asked me|saved|learned|noted|wrote down|know about me)\b",
    r"\b(?:how many|how much)\b[^.?!]*\b(?:do|can|did|could) you (?:remember|know|store|keep|recall|hold)\b",
    r"\b(?:about|of) you\b(?! (?:buy|pay|have|get|spend|need|use|make|walk|drive|run|save))",
    r"\bare you\b",
    r"\b(?:would|do|did) you (?:rather|prefer)\b",
]), re.I)
_orig_is_reasoning = A.is_reasoning


def about_assistant(text: str) -> bool:
    return bool(ABOUT.search(text or ""))


def is_reasoning_q404(text: str, loop=None) -> bool:
    if loop is None or not getattr(loop, "q404", False):
        return _orig_is_reasoning(text, loop)
    t = (text or "").strip()
    if A.SELF.search(t):
        if about_assistant(t):
            return False
        return _orig_is_reasoning(A.SELF.sub("they", t), loop)   # every other condition exactly as before
    return _orig_is_reasoning(text, loop)


A.is_reasoning = is_reasoning_q404        # identical to the original for any loop without .q404


def build_b(state_dir, args):
    import claude_e2e02c as E02C
    if os.environ.get("Q404_ROUTE", "") == "1":
        E02C.ROUTE02C = True                  # only if 383 is a verified PASS (PASSMARKS-q404 "Arms")
    loop = E02C.build_02c(state_dir, args)
    loop.q404 = False
    return loop


def build_q(state_dir, args):
    loop = build_b(state_dir, args)
    loop.q404 = True
    loop.layers330c = list(getattr(loop, "layers330c", []) or []) + ["q404"]
    return loop


# ------------------------------------------------------------------ runner
def _load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def run(a) -> None:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    import torch
    torch.use_deterministic_algorithms(True, warn_only=True)
    mod, fn = a.arm.split(":")
    build = getattr(importlib.import_module(mod), fn)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{a.task}_{a.name}.jsonl"
    if path.exists():
        raise SystemExit(f"q404: {path} exists (each run is launched once)")
    if a.task == "dev":
        items = [{"id": f"dev-{i:03d}", "text": t} for i, (t, _) in enumerate(DEV_MATH + DEV_SELF)]
    else:
        items = _load(Path(a.panel_dir) / {"math": "math.jsonl", "self": "self.jsonl"}[a.task])
    rows = []
    for it in items:
        tmp = tempfile.mkdtemp(prefix=f"q404-{a.name}-")
        try:
            agent = build(tmp, a)
            torch.manual_seed(TURN_SEED)
            gate = A.is_reasoning(it["text"], agent)
            t0 = time.time()
            parts = agent.turn(it["text"])
            rows.append({"id": it["id"], "reply": " ".join(x for x in (parts or []) if x), "think_gate": gate,
                         "ms": round((time.time() - t0) * 1000, 1)})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"task": a.task, "name": a.name, "rows": len(rows),
                      "think_gate": sum(r["think_gate"] for r in rows)}), flush=True)


# ------------------------------------------------------------------ score (counts only)
UNSURE = re.compile(r"^\s*(?:I'm not sure|I am not sure|I don't know|I can't|I cannot|Sorry)", re.I)
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def stated_answer(reply: str):
    """The number the reply gives as its answer, or None. Same rule for every arm, fixed before the run."""
    if not reply or UNSURE.search(reply):
        return None
    head = reply.split("How I worked it out:")[0] if "How I worked it out:" in reply else None
    nums = NUM.findall(head if head is not None else reply)
    if not nums:
        return None
    s = (nums[0] if head is not None else nums[-1]).replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return None
    return int(v) if v == int(v) else v


def score(a) -> None:
    out = Path(a.out)
    pd = Path(a.panel_dir)
    math = {r["id"]: r for r in _load(pd / "math.jsonl")}
    res = {}
    for name in ("B", "Q"):
        f = out / f"math_{name}.jsonl"
        if not f.exists():
            continue
        rows = _load(f)
        right = wrong = right_you = 0
        for r in rows:
            gold, ans = math[r["id"]]["answer"], stated_answer(r["reply"])
            ok = ans is not None and ans == gold
            right += ok
            right_you += ok and math[r["id"]]["you"]
            wrong += ans is not None and not ok
        res[name] = {"right": right, "right_you": right_you, "wrong_stated": wrong,
                     "think_gate": sum(r["think_gate"] for r in rows),
                     "think_gate_you": sum(r["think_gate"] for r in rows if math[r["id"]]["you"])}
    b, q = res.get("B"), res.get("Q")
    same_noyou = None
    if b and q:
        rb = {r["id"]: r["reply"] for r in _load(out / "math_B.jsonl")}
        same_noyou = sum(1 for r in _load(out / "math_Q.jsonl")
                         if not math[r["id"]]["you"] and rb.get(r["id"]) == r["reply"])
    fq = out / "self_Q.jsonl"
    self_fires = sum(r["think_gate"] for r in _load(fq)) if fq.exists() else None
    marks = {
        "M1": None if not (b and q) else q["right"] - b["right"] >= 10,
        "M2": None if not (b and q) else q["right_you"] - b["right_you"] >= 8,
        "M3": None if self_fires is None else self_fires <= 3,
        "M4": None if same_noyou is None else same_noyou == sum(1 for r in math.values() if not r["you"]),
        "M5": None if not (b and q) else q["wrong_stated"] - b["wrong_stated"] <= 5}
    out_json = {"arms": res, "same_noyou": same_noyou, "self_fires": self_fires, "marks": marks,
                "pass": all(v is True for v in marks.values())}
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "q404_score.json").write_text(json.dumps(out_json, indent=1), encoding="utf-8")
    print(json.dumps(out_json))


# ------------------------------------------------------------------ dev cases (mine; never the TEST panel)
DEV_MATH = [(t, True) for t in [
    "Can you work out how much 4 notebooks cost at 3 dollars each?",
    "If you drive 60 miles an hour for 3 hours, how far do you go?",
    "How many cookies do you get if you bake 5 trays with 12 on each?",
    "If you have 20 dollars and spend 7, how much do you have left?",
    "Could you tell me what 15 percent of 80 is?",
    "If your train leaves at 9 and the trip takes 2 hours, when do you arrive?",
    "What do you pay for 3 tickets at 12 dollars each plus a 5 dollar fee?",
    "If you split 36 apples among 4 friends, how many does each get?",
    "Can you add up 14, 27 and 9 for me?",
    "How many minutes do you need to read 90 pages at 3 pages a minute?",
    "If you save 15 dollars a week, how much do you have after 8 weeks?",
    "What is your total if you buy 2 shirts at 18 and 1 hat at 11?",
]]
DEV_SELF = [(t, False) for t in [
    "What are you able to remember from the 2 chats we had yesterday, out of 5 total?",
    "Do you remember the 3 books I told you about last week, and which was 2nd?",
    "I told you my 2 dogs are 4 and 7, how old is the older one?",
    "How many of the 3 goals I mentioned did I say I finished?",
    "Are you able to do 2 things at once, like 10 tasks?",
    "What is your favourite number between 1 and 10?",
    "Do you like 3 or 4 day weekends better?",
    "How many facts can you remember about me, 10 or 20?",
    "What did I say my 2 kids were called when I told you on day 3?",
    "Tell me about yourself in 2 or 3 sentences?",
    "Have I told you how many of my 4 cousins live in 2 cities?",
    "Would you rather have 2 or 5 hours of rest?",
]]


def selftest() -> None:
    import types
    loop = types.SimpleNamespace(q404=True)
    off = types.SimpleNamespace(q404=False)
    bad = 0
    for t, want in DEV_MATH + DEV_SELF:
        got = A.is_reasoning(t, loop)
        if got != want:
            bad += 1
            print("MISMATCH", want, got, "|", t)
        assert A.is_reasoning(t, off) == _orig_is_reasoning(t, off)            # arm B unchanged
    assert stated_answer("12. How I worked it out: 4 * 3 = 12") == 12
    assert stated_answer("I'm not sure. I worked it out a few times") is None
    assert stated_answer("You'd have 1,200 left.") == 1200
    n = len(DEV_MATH) + len(DEV_SELF)
    print(f"q404 selftest {n - bad}/{n} dev cases")
    if bad:
        raise SystemExit(1)


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score"])
    ap.add_argument("--task", default="")
    ap.add_argument("--arm", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--gen-model", default="")
    ap.add_argument("--mouth-model", default="")
    ap.add_argument("--panel-dir", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--score", default="")
    a = ap.parse_args()
    run(a) if a.cmd == "run" else score(a)


if __name__ == "__main__":
    main()
