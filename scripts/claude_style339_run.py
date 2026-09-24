#!/usr/bin/env python3
"""339 builders and scorer (month-end line). Marks: artifacts/claude-style339-20260924/PASSMARKS.md.
New file only; never prints panel text.

Runs go through the 336 harness (3 days, one sleep per day, kill + restart from the same state dir):
  python -B scripts/claude_e2e336_run.py --bank PANEL --arm claude_style339_run:build_P --name P \
      --model <lis-301 dir> --gen-model <MiniCPM5-1B dir> --out OUT
  python -B scripts/claude_e2e336_run.py --bank PANEL --arm claude_chat338_run:build_P --name B \
      --model <lis-301 dir> --gen-model <same> --out OUT
  python -B scripts/claude_e2e336_run.py --bank PANEL --arm twin --name T --model <same MiniCPM5-1B dir> --out OUT
  python -B scripts/claude_style339_run.py --panel PANEL --score OUT
P = 330a + 334 + 333 + 338 + 339; B = the same without 339; T = the plain twin.

Mechanical: a saved preference shows as its fixed acknowledgement (ACK339) in P's reply, so the
scorer reads P's rows only. Judge packets (blind, arm order shuffled with seed 339):
  judge_follow_P.jsonl  feedback lives: the preference in words + P's day-3 turns and replies
  judge_pair_B.jsonl / judge_pair_T.jsonl  feedback lives: day-3 of P and of the other arm, shuffled
                                           (keys in judge_key_B.json / judge_key_T.json)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PREF_WORDS = {
    "shorter": "The user asked for shorter replies.",
    "longer": "The user asked for longer, more detailed replies.",
    "no_nickname": "The user asked not to be called \"{d}\".",
    "no_emoji": "The user asked for no emoji.",
    "casual": "The user asked for a more casual, relaxed tone.",
    "formal": "The user asked for a more formal, polite tone.",
    "no_questions": "The user asked the assistant to stop ending every reply with a question.",
    "name": "The user asked to be called {d}.",
}
_GEN: dict = {}


def build_P(state_dir, args):
    import claude_chat338_agent as C
    import claude_e2e330_arms as A
    import claude_style339_agent as S
    loop = A.build_330a_cre(state_dir, args)
    share = A._gen(args.gen_model)
    if args.gen_model not in _GEN:
        _GEN[args.gen_model] = C.Gen338(share=share)
    C.install_chat338(loop, S.StyledGen339(_GEN[args.gen_model], loop))
    S.install_style339(loop)
    return loop


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def saved_labels(reply: str) -> list[tuple[str, str | None]]:
    import claude_style339_agent as S
    out = []
    for lab, ack in S.ACK339.items():
        pat = "^" + re.escape(ack).replace(re.escape("{d}"), r"([A-Za-z]+)")
        m = re.match(pat, reply)
        if m:
            out.append((lab, m.group(1) if m.groups() else None))
    return out


def score(a):
    panel, d = Path(a.panel), Path(a.score)
    lives = {x["life_id"]: x for x in load(panel / "lives.jsonl")}
    turns = {(t["life_id"], t["turn_index"]): t for t in load(panel / "turns.jsonl")}
    arms = {x: load(d / f"arm_{x}.jsonl") for x in ("P", "B", "T") if (d / f"arm_{x}.jsonl").exists()}
    P = [r for r in arms["P"] if r["kind"] == "user"]
    got: dict = {lid: [] for lid in lives}
    for r in P:
        got[r["life_id"]] += saved_labels(r["reply"])
    fb = [lid for lid, x in lives.items() if x["preference"]]
    ctl = [lid for lid, x in lives.items() if not x["preference"]]

    def right(lid):
        x = lives[lid]
        want = (x["preference"], (x["detail"].lower() if x["preference"] == "no_nickname" else x["detail"])
                if x["detail"] else None)
        return got[lid] == [want]

    summ = {
        "lives": len(lives), "feedback_lives": len(fb), "control_lives": len(ctl),
        "P339.1_feedback_lives_saved_exactly_right": sum(1 for lid in fb if right(lid)),
        "P339.2_control_lives_with_any_saved": sum(1 for lid in ctl if got[lid]),
        "feedback_lives_with_extra_or_wrong": sum(1 for lid in fb if got[lid] and not right(lid)),
        "feedback_lives_with_nothing_saved": sum(1 for lid in fb if not got[lid]),
        "saved_by_label": {lab: sum(1 for lid in lives for g in got[lid] if g[0] == lab)
                           for lab in PREF_WORDS},
    }

    def day3(x, lid):
        return [{"user": turns[(lid, r["turn_index"])]["user_text"], "assistant": r["reply"]}
                for r in arms[x] if r["life_id"] == lid and r["kind"] == "user" and r["day"] == 3]

    def pref_words(lid):
        x = lives[lid]
        return PREF_WORDS[x["preference"]].format(d=x["detail"])

    (d / "judge_follow_P.jsonl").write_text("".join(
        json.dumps({"life_id": lid, "preference": pref_words(lid), "day3": day3("P", lid)}, ensure_ascii=False)
        + "\n" for lid in sorted(fb)), encoding="utf-8")
    for other in ("B", "T"):
        if other not in arms:
            continue
        rng = random.Random(339)
        packets, key = [], {}
        for lid in sorted(fb):
            pair = [("P", day3("P", lid)), (other, day3(other, lid))]
            rng.shuffle(pair)
            key[lid] = [pair[0][0], pair[1][0]]
            packets.append({"life_id": lid, "preference": pref_words(lid),
                            "day3_1": pair[0][1], "day3_2": pair[1][1]})
        (d / f"judge_pair_{other}.jsonl").write_text(
            "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in packets), encoding="utf-8")
        (d / f"judge_key_{other}.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    (d / "summary.json").write_text(json.dumps(summ, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(summ, sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--score", required=True)
    score(ap.parse_args())


if __name__ == "__main__":
    main()
