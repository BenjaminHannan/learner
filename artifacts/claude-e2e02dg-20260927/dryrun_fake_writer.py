#!/usr/bin/env python3
"""Harness dry run before the rental (no model): checks.py's w1, compare, w2 and timing with a FAKE writer whose one
note is the whole prompt it was given (so "notes equal" = "prompts equal") and a fake talker. It tests the runner code
and shows that the build's turn path hands G the same prompt text as claude_rd378_write.py does. It says nothing about
G itself. Usage: python -B dryrun_fake_writer.py OUT_DIR"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import checks as C  # noqa: E402
import claude_e2e02d as B  # noqa: E402
import claude_e2e02d_g as G  # noqa: E402
from claude_rd378_common import build_nprompt  # noqa: E402


class Fake:
    dev = "fake (no model)"

    def write(self, kind, date, earlier, latest):
        p = build_nprompt(kind, date, earlier, latest)
        return [{"text": p, "cites": [0], "when": None}], "raw", 1.0


class FakeTalker:
    hit_max = 0

    def __init__(self, d):
        pass

    def reply(self, s, m, n):
        return "fake reply"


G.writer_for = lambda d, want=None: Fake()
B.Talker = FakeTalker
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
D = str(ROOT / "artifacts/claude-rd378g-20260926/g5/dialogs.jsonl")
rows, w = [], Fake()
for d in C.dialogs(D):                         # claude_rd378_write.main's loop, same fake writer
    for k, t in enumerate(d["turns"]):
        if d["kind"] == "chat" and t["speaker"] == "assistant":
            continue
        notes, raw, ms = w.write(d["kind"], d.get("date", ""), d["turns"][:k], t)
        rows.append({"dialog": d["dialog"], "t": t["t"], "notes": notes, "raw": raw, "ms": round(ms, 1)})
C._write_notes_file(out / "cli.jsonl", rows)
C.cmd_w1(argparse.Namespace(dialogs=D, out=str(out / "build.jsonl"), want_sha=""))
C.cmd_compare(argparse.Namespace(dialogs=D, cli=str(out / "cli.jsonl"), build=str(out / "build.jsonl"),
                                 rental=str(ROOT / "artifacts/claude-rd378g-20260926/vast/g5/notes_G.jsonl"),
                                 out=str(out / "w1.json")))
C.cmd_w2(argparse.Namespace(dialogs=D, cli=str(out / "cli.jsonl"), out=str(out / "w2.json"), want_sha=""))
C.cmd_timing(argparse.Namespace(dialogs=D, talker="x", out=str(out / "timing.json"), want_sha="", dialogs_n=2, turns=4))
