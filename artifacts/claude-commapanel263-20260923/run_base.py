#!/usr/bin/env python3
"""Run commapanel263 on the base260 arm (scripts/claude_loop260_agent.py +
artifacts/claude-openers260-20260922/loop260-config.json).

Method (same as openpanel260 on 138m): one fresh agent per item, turns
sent in order (setup, turn, followup), stored triples read after each
turn. plain_reply comes from a second fresh agent with the same setup
plus plain_turn. One process, sequential. Isolated temp state dirs;
never touches repo-root notebook/.

Writes base260.jsonl (60 rows, 10 fields) and appends the base outcome
marker to each panel.jsonl note (" | base: RIGHT" / " | base: WRONG" /
" | base: WRONG+JUNK"). Deterministic: re-runs are byte-identical.
"""
import copy
import json
import string
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PANEL = HERE / "panel.jsonl"
OUT = HERE / "base260.jsonl"
SCRIPTS = HERE.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import claude_loop260_agent as A260  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402

CONFIG = HERE.parent / "claude-openers260-20260922" / "loop260-config.json"


def norm(s):
    return str(s).lower().strip(string.punctuation + " ")


def fresh():
    cfg = copy.deepcopy(json.loads(CONFIG.read_text(encoding="utf-8")))
    td = tempfile.mkdtemp(prefix="c263base_", dir="/tmp")
    cfg["state_dir"] = td
    return A260.build_agent260(cfg)


def triples(loop):
    return sorted([list(x) for x in L90.notebook_triples(loop.nb)])


def send(loop, text):
    return " ".join(loop.turn(text))


TEACH_FAMS = {"unlisted_opener_teach", "appositive_subject",
              "comma_value_ok"}


def judge(item, setup_stored, turn_stored, foll_stored,
          turn_reply, foll_reply):
    fam = item["family"]
    gold = item["gold"]
    expect = [tuple(t) for t in item["expect_store"]]
    setup = {tuple(t) for t in setup_stored}
    after_turn = {tuple(t) for t in turn_stored}
    after_foll = {tuple(t) for t in foll_stored}
    extra = (after_turn | after_foll) - setup - set(expect)
    junk = len(extra) > 0
    store_ok = set(expect) <= after_turn and not (
        after_turn - setup - set(expect))
    is_teach = fam in TEACH_FAMS or item["followup"] != ""
    if fam == "question" or (fam == "control" and item["followup"] == ""):
        is_teach = False
    scored = foll_reply if is_teach else turn_reply
    reply_ok = (gold == "" or norm(gold) in norm(scored))
    if fam == "question":
        qwrite = (after_turn != setup)
    else:
        qwrite = (after_foll != after_turn) if item["followup"] else False
    comma_subj = any("," in t[0] for t in (after_turn | after_foll))
    if fam in ("unlisted_opener_teach", "comma_value_ok"):
        right = store_ok and reply_ok and not junk and not qwrite
    elif fam == "appositive_subject":
        right = (not comma_subj and store_ok and reply_ok
                 and not junk and not qwrite)
    elif fam == "question":
        right = reply_ok and not junk and not qwrite
    elif fam == "control":
        right = (store_ok and reply_ok and not junk and not qwrite) \
            if is_teach else (reply_ok and not junk and not qwrite)
    else:
        raise ValueError(fam)
    return right, comma_subj


def main():
    items = [json.loads(l) for l in PANEL.read_text(
        encoding="utf-8").splitlines()]
    assert len(items) == 60
    rows = []
    for it in items:
        loop = fresh()
        setup_replies = [send(loop, t) for t in it["setup"]]
        setup_stored = triples(loop)
        turn_reply = send(loop, it["turn"])
        turn_stored = triples(loop)
        if it["followup"]:
            foll_reply = send(loop, it["followup"])
            foll_stored = triples(loop)
        else:
            foll_reply = ""
            foll_stored = turn_stored
        if it["plain_turn"]:
            ploop = fresh()
            for t in it["setup"]:
                send(ploop, t)
            plain_reply = send(ploop, it["plain_turn"])
        else:
            plain_reply = ""
        right, junk = judge(it, setup_stored, turn_stored, foll_stored,
                            turn_reply, foll_reply)
        marker = (" | base: RIGHT" if right
                  else " | base: WRONG+JUNK" if junk
                  else " | base: WRONG")
        it["note"] = it["note"] + marker
        rows.append({
            "id": it["id"],
            "setup_replies": setup_replies,
            "stored_after_setup": setup_stored,
            "turn_reply": turn_reply,
            "stored_after_turn": turn_stored,
            "followup_reply": foll_reply,
            "stored_after_followup": foll_stored,
            "plain_reply": plain_reply,
            "base_right": right,
            "base_junk": junk,
        })
    with open(PANEL, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} ({len(rows)} rows); notes marked in panel")


if __name__ == "__main__":
    main()
