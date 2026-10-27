#!/usr/bin/env python3
"""mu-405: do stored facts in the talker's input make the plain 1B make things up about the user, and does giving
them as the user's own words help? ("Making things up about you", 2026-09-26). New file; DEV data only.
Marks: artifacts/claude-mu405-20260926/PASSMARKS.md (fixed before the run).

The talker is the plain MiniCPM5-1B exactly as the 336 plain twin b runs it (scripts/claude_e2e336_twinb.py: the
twin's system line, greedy, 160 new tokens, enable_thinking=False, <think> text cut). No reader, notebook, rules or
templates. Each panel chat has two sessions (artifacts/claude-mu405-20260926/panel/items.jsonl); code chose the 3
facts session 1 teaches (facts.jsonl). Only session 2 is judged. Arms differ only in what the system message adds
before session 2:
  N  nothing (session 2 only)
  K  the 3 facts as 0.2c's notebook line: " Facts the user has told you: " + claude_cre333_agent._sentence(triple)
  W  session 1's user turns in y1f's L1 form (0.2d's W input): claude_y1f_layout.L1_HEAD + 'User said, "<text>"'
     lines, oldest first
  H  report only: the plain twin with both sessions as real chat history (session 1 answered by the twin too), the
     way plain rivals see a whole chat
Facts come from the panel's labels, so K and W carry all 3 facts in every session-2 prompt by construction;
--count-prompts proves it at $0 (no model) before any spend.

  python -B scripts/claude_mu405_talk.py --count-prompts --panel P --facts F
  python -B scripts/claude_mu405_talk.py --panel P --facts F --model BASE --arm N|K|W|H --out OUT [--smoke]
  python -B scripts/claude_mu405_talk.py --selftest
Output OUT/talk_<arm>.jsonl: one row per session-2 turn (item_id, arm, turn_i, kind, user, reply, ms), and for H also
session-1 rows (session 1). Last printed line: JSON counts (rows, ask_right, ms_median).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_cre333_agent as C  # noqa: E402  (0.2c's fact sentence)
import claude_e2e336_twin as TW  # noqa: E402  (plain twin system line, MAX_NEW, loader)
import claude_y1f_layout as Y  # noqa: E402  (0.2d's W input header)

ARMS = ("N", "K", "W", "H")
THINK = re.compile(r"<think>.*?(</think>|$)", re.S)
KINDS2 = ("smalltalk", "feelings", "advice", "followup", "ask")


def load(panel: str, facts: str, smoke: bool) -> list[dict]:
    fx = {r["item_id"]: r for r in map(json.loads, Path(facts).read_text(encoding="utf-8").splitlines())}
    out = []
    for r in map(json.loads, Path(panel).read_text(encoding="utf-8").splitlines()):
        f = fx[r["item_id"]]
        if f["smoke"] != smoke:
            continue
        out.append({**r, "facts": f["facts"], "ask": f["facts"][f["ask_index"]]})
    return out


def system_for(arm: str, item: dict) -> str:
    if arm in ("N", "H"):
        return TW.SYSTEM
    if arm == "K":
        return TW.SYSTEM + " Facts the user has told you: " + " ".join(C._sentence(tuple(f["triple"]))
                                                                        for f in item["facts"])
    if arm == "W":
        return TW.SYSTEM + "\n\n" + Y.L1_HEAD + "".join('User said, "' + t["text"] + '"\n' for t in item["session1"])
    raise ValueError(arm)


def facts_in(text: str, item: dict) -> int:
    low = text.lower()
    return sum(1 for f in item["facts"] if f["value"].lower() in low)


def count_prompts(items: list[dict]) -> dict:
    res = {}
    for arm in ("N", "K", "W"):
        per = [facts_in(system_for(arm, it), it) for it in items for _ in it["session2"]]
        res[arm] = {"prompts": len(per), "with_all_3": sum(1 for x in per if x == 3),
                    "with_at_least_2": sum(1 for x in per if x >= 2), "min": min(per), "max": max(per)}
    return res


class Talker:
    def __init__(self, model_dir: str):
        self.tok, self.model, self.dev = TW._load(model_dir)

    def reply(self, system: str, history: list[dict]) -> str:
        import torch
        msgs = [{"role": "system", "content": system}] + history
        try:
            prompt = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                                  enable_thinking=False)
        except TypeError:
            prompt = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ids = self.tok(prompt, return_tensors="pt").to(self.dev)
        with torch.no_grad():
            out = self.model.generate(**ids, max_new_tokens=TW.MAX_NEW, do_sample=False,
                                      pad_token_id=self.tok.eos_token_id)
        text = self.tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
        return THINK.sub("", text.split("\nUser:")[0]).strip()


def run_arm(talker, arm: str, items: list[dict]) -> list[dict]:
    rows = []
    for n, it in enumerate(items, 1):
        system = system_for(arm, it)
        hist: list[dict] = []
        if arm == "H":
            for i, t in enumerate(it["session1"]):
                hist.append({"role": "user", "content": t["text"]})
                t0 = time.time()
                r = talker.reply(system, hist)
                hist.append({"role": "assistant", "content": r})
                rows.append({"item_id": it["item_id"], "arm": arm, "session": 1, "turn_i": i, "kind": "teach",
                             "user": t["text"], "reply": r, "ms": round((time.time() - t0) * 1000, 1)})
        for i, t in enumerate(it["session2"]):
            hist.append({"role": "user", "content": t["text"]})
            t0 = time.time()
            r = talker.reply(system, hist)
            hist.append({"role": "assistant", "content": r})
            rows.append({"item_id": it["item_id"], "arm": arm, "session": 2, "turn_i": i, "kind": t["kind"],
                         "user": t["text"], "reply": r, "ms": round((time.time() - t0) * 1000, 1)})
        print(f"[mu405/{arm}] {it['item_id']} ({n}/{len(items)})", flush=True)
    return rows


def ask_right(rows: list[dict], items: list[dict]) -> int:
    ask = {it["item_id"]: it["ask"]["value"].lower() for it in items}
    return sum(1 for r in rows if r["session"] == 2 and r["kind"] == "ask" and ask[r["item_id"]] in r["reply"].lower())


def selftest() -> None:
    ok = 0
    it = {"item_id": "x", "session1": [{"text": "my dog Biscuit is a menace"}, {"text": "I'm a welder lol"},
                                       {"text": "grew up in Duluth"}],
          "session2": [{"kind": k, "text": "hi"} for k in KINDS2],
          "facts": [{"triple": ["user", "dog_name", "Biscuit"], "value": "Biscuit"},
                    {"triple": ["user", "job", "welder"], "value": "welder"},
                    {"triple": ["user", "home_town", "Duluth"], "value": "Duluth"}],
          "ask": {"value": "Biscuit"}}
    assert system_for("N", it) == TW.SYSTEM; ok += 1
    assert facts_in(system_for("N", it), it) == 0; ok += 1
    assert system_for("K", it).endswith("The user's dog name is Biscuit. The user's job is welder. "
                                        "The user's home town is Duluth."); ok += 1
    w = system_for("W", it)
    assert Y.L1_HEAD in w and 'User said, "my dog Biscuit is a menace"\n' in w; ok += 1
    c = count_prompts([it])
    assert c["K"]["with_all_3"] == 5 and c["W"]["with_all_3"] == 5 and c["N"]["max"] == 0; ok += 1
    rows = [{"item_id": "x", "session": 2, "kind": "ask", "reply": "It's biscuit!"},
            {"item_id": "x", "session": 2, "kind": "feelings", "reply": "Biscuit"}]
    assert ask_right(rows, [it]) == 1; ok += 1
    print(f"mu405 selftest {ok}/6 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel")
    ap.add_argument("--facts")
    ap.add_argument("--model")
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--out")
    ap.add_argument("--smoke", action="store_true", help="run the smoke chats (never panel items)")
    ap.add_argument("--count-prompts", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    items = load(a.panel, a.facts, a.smoke)
    for it in items:
        if [t["kind"] for t in it["session2"]] != list(KINDS2):
            raise SystemExit(f"mu405: {it['item_id']} session 2 kinds wrong")
    if a.count_prompts:
        print(json.dumps({"items": len(items), "count_prompts": count_prompts(items)}))
        return
    rows = run_arm(Talker(a.model), a.arm, items)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"talk_{a.arm}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                             encoding="utf-8")
    s2 = [r for r in rows if r["session"] == 2]
    print(json.dumps({"arm": a.arm, "items": len(items), "rows_session2": len(s2), "rows_all": len(rows),
                      "ask_right": ask_right(rows, items),
                      "ms_median": round(statistics.median(r["ms"] for r in s2), 1)}))


if __name__ == "__main__":
    main()
