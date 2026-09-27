#!/usr/bin/env python3
"""mu-407 talk: the plain 1B with a current-message label vs without ("Making things up about you", 2026-09-27).
New file; reuses claude_mu405_talk (Talker, load, KINDS2, ask_right) unchanged. Marks:
artifacts/claude-mu407-20260927/PASSMARKS.md (fixed before any reply exists).

Every piece of text around the chat comes from GLM (prep/frames.json: system, memory_header, line_prefix,
current_label). All arms use the GLM system line. Earlier session-2 turns stay plain history; only the latest user
message differs:
  N   the user's turn as written (no memory; report and validity only)
  U0  memory_header, one line per session-1 message (line_prefix + the message in double quotes), a blank line,
      then the user's turn
  U1  U0 with one change: current_label on its own line between that blank line and the user's turn

  python -B scripts/claude_mu407_talk.py --panel P --facts F --frames FR --model BASE --arm U0 --out OUT [--smoke]
  python -B scripts/claude_mu407_talk.py --show --panel P --facts F --frames FR   (prints one U1 message, smoke chat)
  python -B scripts/claude_mu407_talk.py --selftest
Output OUT/talk_<ARM>.jsonl in mu-405's row shape; last printed line: JSON counts.
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

import claude_mu405_talk as T  # noqa: E402

ARMS = ("N", "U0", "U1")
FRAME_KEYS = ("system", "memory_header", "line_prefix", "current_label")


def load_frames(path: str) -> dict:
    fr = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [k for k in FRAME_KEYS if not str(fr.get(k, "")).strip()]
    if missing:
        raise SystemExit(f"mu407: frames missing {missing}")
    return {k: str(fr[k]).strip() for k in FRAME_KEYS}


def block(fr: dict, item: dict) -> str:
    return fr["memory_header"] + "\n" + "".join(fr["line_prefix"] + ' "' + t["text"] + '"\n' for t in item["session1"])


def latest(arm: str, fr: dict, item: dict, text: str) -> str:
    if arm == "N":
        return text
    if arm == "U0":
        return block(fr, item) + "\n" + text
    if arm == "U1":
        return block(fr, item) + "\n" + fr["current_label"] + "\n" + text
    raise ValueError(arm)


def run(talker, arm: str, fr: dict, items: list[dict]) -> list[dict]:
    rows = []
    for n, it in enumerate(items, 1):
        hist: list[dict] = []
        for i, t in enumerate(it["session2"]):
            t0 = time.time()
            r = talker.reply(fr["system"], hist + [{"role": "user", "content": latest(arm, fr, it, t["text"])}])
            hist += [{"role": "user", "content": t["text"]}, {"role": "assistant", "content": r}]
            rows.append({"item_id": it["item_id"], "arm": arm, "session": 2, "turn_i": i, "kind": t["kind"],
                         "user": t["text"], "reply": r, "ms": round((time.time() - t0) * 1000, 1)})
        print(f"[mu407/{arm}] {it['item_id']} ({n}/{len(items)})", flush=True)
    return rows


def selftest() -> None:
    ok = 0
    fr = {"system": "SYS", "memory_header": "Earlier, the user wrote:", "line_prefix": "They said",
          "current_label": "Reply to this now:"}
    it = {"item_id": "x", "session1": [{"text": "my dog Biscuit is a menace"}, {"text": "I'm a welder lol"},
                                       {"text": "grew up in Duluth"}],
          "session2": [{"kind": k, "text": f"hi {k}"} for k in T.KINDS2], "ask": {"value": "Biscuit"}}
    b = 'Earlier, the user wrote:\nThey said "my dog Biscuit is a menace"\nThey said "I\'m a welder lol"\n' \
        'They said "grew up in Duluth"\n'
    assert latest("N", fr, it, "yo") == "yo"; ok += 1
    assert latest("U0", fr, it, "yo") == b + "\nyo"; ok += 1
    assert latest("U1", fr, it, "yo") == b + "\nReply to this now:\nyo"; ok += 1
    assert latest("U1", fr, it, "yo").replace("Reply to this now:\n", "") == latest("U0", fr, it, "yo"); ok += 1

    class Fake:
        def __init__(self):
            self.seen = []

        def reply(self, system, msgs):
            self.seen.append((system, msgs))
            return "It's Biscuit." if "ask" in msgs[-1]["content"] else "ok"
    f = Fake()
    rows = run(f, "U1", fr, [it])
    assert len(rows) == 5 and all(s == "SYS" for s, _ in f.seen) and len(f.seen[4][1]) == 9; ok += 1
    assert f.seen[4][1][0] == {"role": "user", "content": "hi smalltalk"} and "Reply to this now:" in f.seen[4][1][-1][
        "content"]; ok += 1
    assert T.ask_right(rows, [it]) == 1; ok += 1
    print(f"mu407 talk selftest {ok}/7 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel")
    ap.add_argument("--facts")
    ap.add_argument("--frames")
    ap.add_argument("--model")
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--out")
    ap.add_argument("--smoke", action="store_true", help="run the smoke chats (never panel items)")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    fr = load_frames(a.frames)
    items = T.load(a.panel, a.facts, a.smoke or a.show)
    for it in items:
        if [t["kind"] for t in it["session2"]] != list(T.KINDS2):
            raise SystemExit(f"mu407: {it['item_id']} session 2 kinds wrong")
    if a.show:
        print(latest("U1", fr, items[0], items[0]["session2"][0]["text"]))
        return
    rows = run(T.Talker(a.model), a.arm, fr, items)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"talk_{a.arm}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                             encoding="utf-8")
    print(json.dumps({"arm": a.arm, "items": len(items), "rows": len(rows), "ask_substring": T.ask_right(rows, items),
                      "ms_median": round(statistics.median(r["ms"] for r in rows), 1)}))


if __name__ == "__main__":
    main()
