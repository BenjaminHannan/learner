#!/usr/bin/env python3
"""Director held-out probe of exp 263 (comma write guard). CPU only.

Drives BOTH arms exactly as artifacts/claude-commapanel263-20260923/run_base.py
drives an agent: a fresh agent + fresh temp state dir per dialog, turns sent in
order, stored triples read after each turn via fable_loop90_agent.notebook_triples.

Arms:
  260: scripts/claude_loop260_agent.build_agent260 +
       artifacts/claude-openers260-20260922/loop260-config.json
  263: scripts/claude_loop263_agent.build_agent263 +
       artifacts/claude-comma263-20260923/loop263-config.json

Writes arm260.json and arm263.json (rows: replies + stored triples after each turn).
Sequential, one process. Isolated temp state dirs; never touches repo-root notebook/.
"""
import copy
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent.parent  # artifacts/claude-verify-20260923/263 -> repo root
# Fallback: resolve by walking up to find scripts/
p = HERE
while not (p / "scripts").exists() and p != p.parent:
    p = p.parent
REPO = p
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import claude_loop260_agent as A260  # noqa: E402
import claude_loop263_agent as A263  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402

CONFIG260 = REPO / "artifacts" / "claude-openers260-20260922" / "loop260-config.json"
CONFIG263 = REPO / "artifacts" / "claude-comma263-20260923" / "loop263-config.json"

DIALOGS = {
    "D1": ["Dude, Orla's boss is Petra.", "Who is Orla's boss?"],
    "D2": ["Okay listen, Brin works at Halden Mill.", "Where does Brin work?"],
    "D3": ["Wow, Tamsin's sister is Juno.", "Who is Tamsin's sister?"],
    "D4": ["Anyway, Ilse lives in Carrow, Wend.", "Where does Ilse live?"],
    "D5": ["Crazy thing, Mabon speaks Welsh.", "What language does Mabon speak?"],
    "D6": ["Sadly, Rhys moved to Tolby.", "Where does Rhys live?"],
    "D7": ["Fenn's boss is Aldo.", "Who is Fenn's boss?"],
    "D8": ["Nell, my neighbour, works at Ashby Farm.", "Where does Nell work?"],
    "D9": ["Ok so like, Coral's brother is Dane.", "Who is Coral's brother?"],
    "D10": ["Btw, is Orla's boss Petra?"],
    "D11": ["Pip works at Stone, Hale and Webb.", "Where does Pip work?"],
    "D12": ["Hmm, Ada's city is Luton.", "What is Ada's city?"],
}


def fresh260():
    cfg = copy.deepcopy(json.loads(CONFIG260.read_text(encoding="utf-8")))
    td = tempfile.mkdtemp(prefix="v263_260_", dir="/tmp")
    cfg["state_dir"] = td
    return A260.build_agent260(cfg)


def fresh263():
    cfg = copy.deepcopy(json.loads(CONFIG263.read_text(encoding="utf-8")))
    td = tempfile.mkdtemp(prefix="v263_263_", dir="/tmp")
    cfg["state_dir"] = td
    return A263.build_agent263(cfg)


def triples(loop):
    return sorted([list(x) for x in L90.notebook_triples(loop.nb)])


def send(loop, text):
    return " ".join(loop.turn(text))


def run_arm(fresh, out_path):
    rows = []
    for did in sorted(DIALOGS, key=lambda d: int(d[1:])):
        turns = DIALOGS[did]
        loop = fresh()
        replies = []
        stored = []
        for t in turns:
            replies.append(send(loop, t))
            stored.append(triples(loop))
        rows.append({
            "dialog": did,
            "turns": turns,
            "replies": replies,
            "stored_after_each_turn": stored,
        })
        print(f"{did}: reply_last={replies[-1][:80]!r} stored_last={stored[-1]}", flush=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"wrote {out_path} ({len(rows)} rows)", flush=True)


def main():
    run_arm(fresh260, HERE / "arm260.json")
    run_arm(fresh263, HERE / "arm263.json")


if __name__ == "__main__":
    main()
