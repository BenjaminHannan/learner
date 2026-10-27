#!/usr/bin/env python3
"""mu-405b: does the plain 1B use the user's own words when they sit in the user message instead of the system
message? ("Making things up about you", 2026-09-26). New file; DEV data only; reuses claude_mu405_talk unchanged.
Marks: artifacts/claude-mu405b-20260926/PASSMARKS.md (fixed before the run).

mu-405 (VERIFY-V405b.md) put session 1's 'User said, "..."' block in the SYSTEM message (its arm W, the way 0.2d's
talker builds its W input, scripts/claude_e2e02d.py:224-228) and the talker answered 4 of 60 stored-fact asks (none 0).
y1f's L1 layout puts the block in the USER message (scripts/claude_y1f_layout.py:59-63). One change against mu-405's W:
  U  system message = the twin's system line only (as N); every session-2 turn's latest user message is
     claude_y1f_layout.L1_HEAD + the 'User said, "<text>"' lines of session 1, oldest first, then a blank line, then
     the user's turn as written. Earlier session-2 turns stay in the history as plain text (the block rides only on
     the latest message, as a talker that rebuilds its input every turn would send it).
Talker, decoding, panel, facts and output rows are mu-405's (claude_mu405_talk: Talker, load, ask_right).

  python -B scripts/claude_mu405b_talk.py --count-prompts --panel P --facts F
  python -B scripts/claude_mu405b_talk.py --panel P --facts F --model BASE --out OUT [--smoke]
  python -B scripts/claude_mu405b_talk.py --selftest
Output OUT/talk_U.jsonl (mu-405's row shape, arm "U"); last printed line: JSON counts.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_e2e336_twin as TW  # noqa: E402
import claude_mu405_talk as T  # noqa: E402
import claude_y1f_layout as Y  # noqa: E402

ARM = "U"


def block(item: dict) -> str:
    return Y.L1_HEAD + "".join('User said, "' + t["text"] + '"\n' for t in item["session1"])


def latest(item: dict, text: str) -> str:
    return block(item) + "\n" + text


def messages(item: dict, hist: list[dict], text: str) -> list[dict]:
    """hist: earlier session-2 turns as plain {role, content}; the latest user message carries the block."""
    return hist + [{"role": "user", "content": latest(item, text)}]


def count_prompts(items: list[dict]) -> dict:
    per = [T.facts_in(latest(it, t["text"]), it) for it in items for t in it["session2"]]
    sys_facts = sum(T.facts_in(TW.SYSTEM, it) for it in items)
    return {"prompts": len(per), "with_all_3": sum(1 for x in per if x == 3), "min": min(per), "max": max(per),
            "facts_in_system_line": sys_facts}


def run_u(talker, items: list[dict]) -> list[dict]:
    rows = []
    for n, it in enumerate(items, 1):
        hist: list[dict] = []
        for i, t in enumerate(it["session2"]):
            t0 = time.time()
            r = talker.reply(TW.SYSTEM, messages(it, hist, t["text"]))
            hist += [{"role": "user", "content": t["text"]}, {"role": "assistant", "content": r}]
            rows.append({"item_id": it["item_id"], "arm": ARM, "session": 2, "turn_i": i, "kind": t["kind"],
                         "user": t["text"], "reply": r, "ms": round((time.time() - t0) * 1000, 1)})
        print(f"[mu405b/{ARM}] {it['item_id']} ({n}/{len(items)})", flush=True)
    return rows


def selftest() -> None:
    ok = 0
    it = {"item_id": "x", "session1": [{"text": "my dog Biscuit is a menace"}, {"text": "I'm a welder lol"},
                                       {"text": "grew up in Duluth"}],
          "session2": [{"kind": k, "text": f"hi {k}"} for k in T.KINDS2],
          "facts": [{"triple": ["user", "dog_name", "Biscuit"], "value": "Biscuit"},
                    {"triple": ["user", "job", "welder"], "value": "welder"},
                    {"triple": ["user", "home_town", "Duluth"], "value": "Duluth"}],
          "ask": {"value": "Biscuit"}}
    m = messages(it, [{"role": "user", "content": "hi smalltalk"}, {"role": "assistant", "content": "hello"}],
                 "hi feelings")
    assert [x["role"] for x in m] == ["user", "assistant", "user"]; ok += 1
    assert m[0]["content"] == "hi smalltalk" and Y.L1_HEAD not in m[0]["content"]; ok += 1
    assert m[-1]["content"] == (Y.L1_HEAD + 'User said, "my dog Biscuit is a menace"\nUser said, "I\'m a welder lol"\n'
                                'User said, "grew up in Duluth"\n\nhi feelings'); ok += 1
    c = count_prompts([it])
    assert c["with_all_3"] == 5 and c["facts_in_system_line"] == 0; ok += 1

    class Fake:
        def __init__(self):
            self.seen = []

        def reply(self, system, msgs):
            self.seen.append((system, msgs))
            return "It's Biscuit." if "ask" in msgs[-1]["content"] else "ok"
    f = Fake()
    it2 = dict(it, session2=[{"kind": k, "text": f"hi {k}"} for k in T.KINDS2])
    rows = run_u(f, [it2])
    assert len(rows) == 5 and f.seen[0][0] == TW.SYSTEM and len(f.seen[4][1]) == 9; ok += 1
    assert T.ask_right(rows, [it2]) == 1; ok += 1
    print(f"mu405b selftest {ok}/6 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel")
    ap.add_argument("--facts")
    ap.add_argument("--model")
    ap.add_argument("--out")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--count-prompts", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    items = T.load(a.panel, a.facts, a.smoke)
    for it in items:
        if [t["kind"] for t in it["session2"]] != list(T.KINDS2):
            raise SystemExit(f"mu405b: {it['item_id']} session 2 kinds wrong")
    if a.count_prompts:
        print(json.dumps({"items": len(items), "count_prompts_U": count_prompts(items)}))
        return
    rows = run_u(T.Talker(a.model), items)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"talk_{ARM}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                           encoding="utf-8")
    print(json.dumps({"arm": ARM, "items": len(items), "rows_session2": len(rows), "rows_all": len(rows),
                      "ask_right": T.ask_right(rows, items),
                      "ms_median": round(statistics.median(r["ms"] for r in rows), 1)}))


if __name__ == "__main__":
    main()
