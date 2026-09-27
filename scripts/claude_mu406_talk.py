#!/usr/bin/env python3
"""mu-406 talk: the plain 1B and the mu-406 LoRA (merged copy) on the test panel ("Making things up about you",
2026-09-27). New file; reuses claude_mu405_talk.Talker and claude_mu407_talk's frames, block and latest unchanged.
Plan: artifacts/claude-mu406-20260926/PLAN-draft-3.md (draft; the sealed plan decides).

Arms (all greedy, mu-405's talk settings, mu-407's Luna frames; earlier session-2 turns stay plain history):
  P   plain 1B, U0 (memory block + blank line + the turn, in the latest user message)       registered
  T   the LoRA (merged copy), U0                                                             registered
  N   plain 1B, no memory                                                                    report only
  PW  plain 1B, W: the Luna system line, a blank line, then the memory block; the turn as written   report only
  TW  the LoRA (merged copy), W                                                              report only
P, N and PW take --model BASE; T and TW take --model MERGED (claude_mu406_train.py merge). The script refuses a
T arm on a model folder without the merge note, and a P arm on one with it.

  python -B scripts/claude_mu406_talk.py --panel P --frames FR --model DIR --arm P --out OUT [--smoke]
  python -B scripts/claude_mu406_talk.py --selftest
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
import claude_mu407_talk as M7  # noqa: E402

FORM = {"P": "U0", "T": "U0", "N": "N", "PW": "W", "TW": "W"}
TRAINED = {"T", "TW"}
MERGE_NOTE = "mu406_merged.json"


def system_for(arm: str, fr: dict, item: dict) -> str:
    return fr["system"] + "\n\n" + M7.block(fr, item) if FORM[arm] == "W" else fr["system"]


def latest_for(arm: str, fr: dict, item: dict, text: str) -> str:
    return text if FORM[arm] == "W" else M7.latest(FORM[arm], fr, item, text)


def run(talker, arm: str, fr: dict, items: list[dict]) -> list[dict]:
    rows = []
    for n, it in enumerate(items, 1):
        system, hist = system_for(arm, fr, it), []
        for i, t in enumerate(it["session2"]):
            t0 = time.time()
            r = talker.reply(system, hist + [{"role": "user", "content": latest_for(arm, fr, it, t["text"])}])
            hist += [{"role": "user", "content": t["text"]}, {"role": "assistant", "content": r}]
            rows.append({"item_id": it["item_id"], "arm": arm, "session": 2, "turn_i": i, "kind": t["kind"],
                         "user": t["text"], "reply": r, "ms": round((time.time() - t0) * 1000, 1)})
        print(f"[mu406/{arm}] {it['item_id']} ({n}/{len(items)})", flush=True)
    return rows


def check_model(arm: str, model_dir: str) -> None:
    merged = (Path(model_dir) / MERGE_NOTE).exists()
    if (arm in TRAINED) != merged:
        raise SystemExit(f"mu406 talk: arm {arm} needs {'the merged LoRA' if arm in TRAINED else 'the plain 1B'}")


def selftest() -> None:
    ok = 0
    fr = {"system": "SYS", "memory_header": "Earlier:", "line_prefix": "They said", "current_label": "Now:"}
    it = {"item_id": "x", "session1": [{"text": "my dog Pim"}, {"text": "welder"}, {"text": "Boise"}],
          "session2": [{"kind": k, "text": f"hi {k}"} for k in T.KINDS2]}

    class Fake:
        def __init__(self):
            self.seen = []

        def reply(self, system, msgs):
            self.seen.append((system, msgs))
            return f"r{len(self.seen)}"
    for arm, form in (("P", "U0"), ("T", "U0"), ("N", "N")):
        a, b = Fake(), Fake()
        run(a, arm, fr, [it])
        M7.run(b, form, fr, [it])
        assert a.seen == b.seen
    ok += 1
    w = Fake()
    rows = run(w, "PW", fr, [it])
    assert w.seen[0][0] == 'SYS\n\nEarlier:\nThey said "my dog Pim"\nThey said "welder"\nThey said "Boise"\n'; ok += 1
    assert w.seen[4][1][-1] == {"role": "user", "content": "hi ask"} and len(w.seen[4][1]) == 9; ok += 1
    assert [r["arm"] for r in rows] == ["PW"] * 5 and rows[4]["kind"] == "ask"; ok += 1
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        check_model("P", td)
        try:
            check_model("T", td)
            raise AssertionError("T ran on a plain folder")
        except SystemExit:
            pass
        (Path(td) / MERGE_NOTE).write_text("{}", encoding="utf-8")
        check_model("TW", td)
        try:
            check_model("PW", td)
            raise AssertionError("PW ran on a merged folder")
        except SystemExit:
            pass
    ok += 1
    print(f"mu406 talk selftest {ok}/5 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel")
    ap.add_argument("--frames")
    ap.add_argument("--model")
    ap.add_argument("--arm", choices=sorted(FORM))
    ap.add_argument("--out")
    ap.add_argument("--smoke", action="store_true", help="run the smoke chats (never panel items)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    check_model(a.arm, a.model)
    fr = M7.load_frames(a.frames)
    items = [json.loads(x) for x in Path(a.panel).read_text(encoding="utf-8").splitlines() if x.strip()]
    items = [it for it in items if ("-s" in it["item_id"]) == a.smoke]
    rows = run(T.Talker(a.model), a.arm, fr, items)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"talk_{a.arm}{'_smoke' if a.smoke else ''}.jsonl"
    (out / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"arm": a.arm, "items": len(items), "rows": len(rows),
                      "ms_median": round(statistics.median(r["ms"] for r in rows), 1)}))


if __name__ == "__main__":
    main()
