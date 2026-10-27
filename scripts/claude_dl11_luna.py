#!/usr/bin/env python3
"""dl-11 Luna stage (Mac, CPU): GPT-6 Luna writes the two kinds of text dl-11 needs, and code checks every row.
(Fix-sleep thread, 2026-09-27; marks: artifacts/claude-dl11-20260927/PASSMARKS.md.) Ben 03:47 09-27 "Allow Luna".

1. Q frames: candidate one-sentence instructions for "work out this arithmetic expression, reply with the number
   only", with the placeholder {EXPR}. dl-11 uses the first valid one to practise; the others are its rewording row.
2. Look-alikes: short everyday questions that contain a number in digits (prices, ages, dates, sizes, scores ...) but
   are NOT arithmetic and not puzzles. They are the router's "leave it to the base" examples from night 1. They are
   never answered and never trained into any adapter.

Code filters (not Luna) decide what is kept:
- Q frame: exactly one {EXPR}, no other braces, no digits, 20-220 characters.
- Look-alike: 8-160 characters, ends with "?", has a digit, no arithmetic between digits, none of the BANNED words (the
  panel's two number templates and their synonyms), not equal to any panel question, no repeats.
Stops with STOP-LUNA (exit 2, no output file) if fewer than MIN_FRAMES frames or MIN_LOOK look-alikes survive.
Luna is called through scripts/claude_luna_effort.py (the Director's claude_luna_codex.py helper with effort "low" and
a 600 s limit per try), one call at a time; this script handles no key and prints counts only, never reply text.
Standard library only.

  python3 scripts/claude_dl11_luna.py --selftest        (filters only; no Luna call)
  python3 scripts/claude_dl11_luna.py --out artifacts/claude-dl11-20260927/luna
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

N_FRAMES, MIN_FRAMES = 5, 3
N_LOOK, MIN_LOOK, PER_CALL, MAX_CALLS = 600, 400, 25, 48
SEED = 2993
EFFORT, TIMEOUT = "low", 600         # rd-378g's writer pilot timed out 9 of 9 at the default effort and 300 s
TOPICS = ["prices and shopping", "ages and birthdays", "years and history dates", "sizes and heights",
          "distances and travel", "sports scores and results", "recipes and cooking times", "clock times and schedules",
          "temperatures and weather", "phones, batteries and gadgets", "books, pages and chapters", "rooms, floors and "
          "addresses", "school grades and classes", "money, tips and bills", "speed limits and driving",
          "pets and animals", "music, songs and albums", "films and TV episodes"]
FRAME_PROMPT = (
    "Write {n} different one-sentence instructions that ask someone to work out the value of an arithmetic "
    "expression and to reply with only the resulting number. Each instruction must contain the placeholder {{EXPR}} "
    "exactly once, where the expression will be inserted. Do not include any example numbers. Vary the wording. "
    "Output only the {n} instructions, one per line, with no numbering and no other text.")
LOOK_PROMPT = (
    "Write {n} short, different everyday questions about {topic}. Each question must contain at least one number "
    "written in digits. The questions must not be arithmetic problems or puzzles, must not ask to calculate anything, "
    "must not ask which number is bigger or smaller or compare amounts, and must not start with \"How many\". Keep each under 20 words "
    "and end each with a question mark. Output only the questions, one per line, with no numbering and no other "
    "text.")
ARITH = re.compile(r"\d\s*[-+*/x×÷^=]\s*\d")
# The panel's two number templates ("Which number is bigger ...", "How many ...") and their synonyms (Thread manager
# review 12:29 UTC), so the template cannot leak back into the router's look-alikes.
BANNED = (" bigger ", " larger ", " smaller ", " how many ", " greater ", " higher ", " more than ", " less ",
          " fewer ", " lower ", " most ", " least ")


def panel_questions() -> set:
    import claude_dl1_nights as D1
    return {it["q"].strip().lower() for it in D1.harm_panel()}


def lines(reply: str) -> list[str]:
    out = []
    for t in reply.splitlines():
        t = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", t).strip().strip('"').strip()
        if t:
            out.append(t)
    return out


def ok_frame(t: str) -> bool:
    return (t.count("{EXPR}") == 1 and t.replace("{EXPR}", "").count("{") == 0 and "}" not in t.replace("{EXPR}", "")
            and not re.search(r"\d", t) and 20 <= len(t) <= 220)


def ok_look(t: str, panel: set) -> bool:
    low = " " + re.sub(r"[^a-z0-9' ]", " ", t.lower()) + " "
    return (8 <= len(t) <= 160 and t.endswith("?") and bool(re.search(r"\d", t)) and not ARITH.search(t)
            and not any(b in low for b in BANNED) and t.strip().lower() not in panel)


def run(a) -> None:
    import claude_luna_effort as L          # the Codex helper with a set effort and time limit (rd-378g's fix)
    L.EFFORT, L.TIMEOUT = EFFORT, TIMEOUT
    out = Path(a.out)
    panel = panel_questions()
    res = {"what": "dl-11 Luna stage", "model": L.MODEL, "effort": EFFORT, "timeout": TIMEOUT, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prompts": {"frame": FRAME_PROMPT, "look": LOOK_PROMPT}, "calls": [], "q_frames": [], "lookalikes": []}
    try:
        reply = L.call(FRAME_PROMPT.format(n=N_FRAMES))
    except RuntimeError as e:
        reply = ""
        res["calls"].append({"kind": "frame", "error": str(e)[:200]})
    cand = lines(reply)
    res["q_frame_candidates"] = cand
    res["q_frames"] = [t for t in dict.fromkeys(cand) if ok_frame(t)][:N_FRAMES]
    res["calls"].append({"kind": "frame", "lines": len(cand), "kept": len(res["q_frames"])})
    print(f"[dl11-luna] frames kept {len(res['q_frames'])} of {len(cand)}", flush=True)
    seen, kept, dropped = set(), [], 0
    rng = random.Random(SEED)
    for c in range(MAX_CALLS):
        if len(kept) >= N_LOOK:
            break
        topic = TOPICS[c % len(TOPICS)] if c < len(TOPICS) else rng.choice(TOPICS)
        try:
            got = lines(L.call(LOOK_PROMPT.format(n=PER_CALL, topic=topic)))
        except RuntimeError as e:
            res["calls"].append({"kind": "look", "topic": topic, "error": str(e)[:200]})
            continue
        k0 = len(kept)
        for t in got:
            if ok_look(t, panel) and t.lower() not in seen:
                seen.add(t.lower())
                kept.append(t)
            else:
                dropped += 1
        res["calls"].append({"kind": "look", "topic": topic, "lines": len(got), "kept": len(kept) - k0})
        print(f"[dl11-luna] call {c + 1} {topic}: kept {len(kept) - k0} of {len(got)} (total {len(kept)})", flush=True)
    res["lookalikes"] = kept[:N_LOOK]
    res["dropped_lines"] = dropped
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if len(res["q_frames"]) < MIN_FRAMES or len(res["lookalikes"]) < MIN_LOOK:
        print(f"STOP-LUNA: frames {len(res['q_frames'])} (need {MIN_FRAMES}), look-alikes {len(res['lookalikes'])} "
              f"(need {MIN_LOOK})", flush=True)
        (out.parent / "luna-stop.json").parent.mkdir(parents=True, exist_ok=True)
        (out.parent / "luna-stop.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        sys.exit(2)
    out.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(res, indent=1, ensure_ascii=False).encode("utf-8")
    (out / "luna_texts.json").write_bytes(raw)
    print(f"[dl11-luna] wrote {out / 'luna_texts.json'} sha256 {hashlib.sha256(raw).hexdigest()} "
          f"frames {len(res['q_frames'])} look-alikes {len(res['lookalikes'])}", flush=True)


def selftest() -> None:
    panel = panel_questions()
    assert ok_frame("Work out {EXPR} and reply with only the number.")
    assert not ok_frame("Work out {EXPR} = {EXPR}.") and not ok_frame("Compute {EXPR} for 3 cases, number only.")
    assert not ok_frame("Work out the value.")
    assert ok_look("Is a ticket for 12 dollars a good deal for a 2 hour film?", panel)
    assert not ok_look("What is 12 + 7?", panel) and not ok_look("What is 3x4?", panel)
    assert not ok_look("Which number is bigger, 12 or 21? Reply with the number only.", panel)
    assert not ok_look("How many 5 cent coins fit in a jar?", panel)
    assert not ok_look("What is the capital of France? Reply with the city name only.", panel)
    assert not ok_look("Is it warm today?", panel)
    assert not ok_look("Is 30 degrees greater than room temperature?", panel)
    assert not ok_look("Do 3 cats need more than 1 litter box?", panel)
    assert not ok_look("Which of the 4 seasons has the least rain?", panel)
    assert lines("1. First?\n- Second?\n\n3) Third?") == ["First?", "Second?", "Third?"]
    assert "{EXPR}" in FRAME_PROMPT.format(n=5) and "prices" in LOOK_PROMPT.format(n=3, topic="prices")
    # run() end to end with a fake Luna (no network): frames and look-alikes pass the filters, the file is written
    import tempfile
    import types
    fake = types.ModuleType("claude_luna_effort")
    fake.MODEL, fake.EFFORT, fake.TIMEOUT = "fake", None, 0
    k = [0]

    def fake_call(text):
        k[0] += 1
        if "{EXPR}" in text:
            return "\n".join(f"Say what {{EXPR}} comes to, number only, version {w}." for w in "abcde")
        return "\n".join(f"Is a {k[0]}{i} minute bus ride long for a trip number {i}?" for i in range(PER_CALL))
    fake.call = fake_call
    sys.modules["claude_luna_effort"] = fake
    with tempfile.TemporaryDirectory() as td:
        run(argparse.Namespace(out=str(Path(td) / "luna")))
        d = json.loads((Path(td) / "luna" / "luna_texts.json").read_text(encoding="utf-8"))
        assert len(d["q_frames"]) == 5 and len(d["lookalikes"]) == N_LOOK and d["effort"] == EFFORT, d["calls"][:2]
    del sys.modules["claude_luna_effort"]
    print("dl11 luna selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/claude-dl11-20260927/luna")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    run(a)


if __name__ == "__main__":
    main()
