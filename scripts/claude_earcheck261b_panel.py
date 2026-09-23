#!/usr/bin/env python3
"""Exp 261b -- strict loader for ear panel 261b (schema exactly as panel 257,
per handoff/kit/briefs/earpanel261b-spec.txt: same line keys, 150 lines, same
family counts; notes carry risk tags R1..R14 plus lower/typo/noq).

Same adaptation as the 261 loader, only the id prefix differs:
- ids "e261b-001".."e261b-150";
- the panel sha is verified against the panel's own SEAL.sha256.txt
  (checked OK from the repo root), not a hardcoded hash.
Any schema deviation prints SCHEMA-MISMATCH and exits 3 (nothing scored).
A sha mismatch exits 4.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235b_panel as P5  # noqa: E402
import claude_smolear257_panel as P7  # noqa: E402

ID_RE = re.compile(r"^e261b-(00[1-9]|0[1-9][0-9]|1[0-4][0-9]|150)$")


def _expect_sha(panel_path, seal_path):
    lines = Path(seal_path).read_text().splitlines()
    for ln in lines:
        parts = ln.strip().split()
        if len(parts) == 2 and parts[1].endswith("panel.jsonl"):
            return parts[0]
    raise SystemExit(f"no panel.jsonl line in seal {seal_path}")


def load_panel(path, seal=None, check_sha=True):
    raw = Path(path).read_bytes()
    if check_sha:
        if seal is None:
            seal = str(Path(path).parent / "SEAL.sha256.txt")
        want = _expect_sha(path, seal)
        if hashlib.sha256(raw).hexdigest() != want:
            print("PANEL-SHA-MISMATCH", file=sys.stderr)
            sys.exit(4)
    lines = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    errs = P7.check(lines)
    for n, d in enumerate(lines):
        if not (isinstance(d.get("id"), str) and d["id"].startswith("e261b-")
                and len(d["id"]) == 9 and ID_RE.match(d["id"])):
            errs.append(f"line {n + 1}: bad id {d.get('id')!r}")
    if errs:
        print("SCHEMA-MISMATCH:", *errs[:50], sep="\n  ", file=sys.stderr)
        sys.exit(3)
    items = []
    for d in lines:
        gold = []
        for g in d["gold"]:
            al = [str(x) for x in g["relation_aliases"]]
            if g["act"] == "ASK" and g["chain"]:
                hops = [str(x).strip() for x in g["chain"]]
                aliases = [[str(y) for y in x] for x in g["chain_aliases"]]
            else:
                hops, aliases = [str(g["relation"]).strip()], [al]
            fr = dict(act=g["act"], subject=str(g["subject"]), relation=hops, aliases=aliases)
            if g["act"] == "TEACH":
                fr["value"] = str(g["value"])
            gold.append(fr)
        toks = d["notes"].split()
        tags = sorted({t for t in toks if re.fullmatch(r"R\d\w*", t)}
                      | (set(toks) & P7.EXTRA_TAGS))
        items.append(dict(id=d["id"], family=d["family"], turn=d["turn"],
                          context=[], tags=tags, gold=gold))
    return items
