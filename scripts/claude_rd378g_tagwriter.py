#!/usr/bin/env python3
"""rd-378g: tag every practice dialog with the model that wrote it, and drop dialogs that carry service error text
(Trustworthy notes thread, 2026-09-27; rd-378g addendum I). New file.

The practice set mixes two writers: the dialogs already in --have were written by GLM 5.3 Flash through OpenRouter
(rd378g-teacher); every later dialog in --in was written by GPT-6 Luna through Codex (writeluna). The folder name does
not say this, so each row gets a "writer" field. A dialog is dropped when any turn or note text matches ERR
(case-insensitive); the script prints counts only, never text.

python -B scripts/claude_rd378g_tagwriter.py tag --have glm/notes_w1.jsonl --in glm2N/notes_w1.jsonl --out F.jsonl
python -B scripts/claude_rd378g_tagwriter.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ERR = re.compile(r"usage limit|limit exceeded|rate limit|quota", re.I)
GLM = "glm-5.3-flash (OpenRouter, rd378g-teacher)"
LUNA = "gpt-6-luna (Codex, writeluna)"


def rows(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def texts(d):
    for t in d["turns"]:
        yield t.get("text", "")
        for n in t.get("notes", []) or []:
            yield n.get("text", "")


def tag(have, items):
    old = {d["dialog"] for d in have}
    out, rep = [], {w: {"dialogs": 0, "dropped": 0} for w in (GLM, LUNA)}
    for d in items:
        w = GLM if d["dialog"] in old else LUNA
        rep[w]["dialogs"] += 1
        if any(ERR.search(x or "") for x in texts(d)):
            rep[w]["dropped"] += 1
            continue
        out.append(dict(d, writer=w))
    return out, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["tag", "selftest"])
    ap.add_argument("--have", default="")
    ap.add_argument("--in", dest="inp", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.mode == "selftest":
        mk = lambda i, s: {"dialog": i, "kind": "chat", "turns": [{"t": 1, "text": s, "notes": [{"text": "n"}]}]}
        have = [mk("kg-001", "hi")]
        out, rep = tag(have, have + [mk("kg-002", "fine"), mk("kg-003", "Error: Usage limit exceeded")])
        ok = ([d["writer"] for d in out] == [GLM, LUNA] and rep[GLM] == {"dialogs": 1, "dropped": 0}
              and rep[LUNA] == {"dialogs": 2, "dropped": 1})
        print("rd378g tagwriter selftest " + ("1/1 ok" if ok else "FAIL"))
        sys.exit(0 if ok else 1)
    out, rep = tag(rows(a.have), rows(a.inp))
    Path(a.out).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    print(json.dumps({"kept": len(out), "by_writer": rep}))


if __name__ == "__main__":
    main()
