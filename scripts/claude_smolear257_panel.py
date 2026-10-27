#!/usr/bin/env python3
"""Exp 257 -- strict loader for ear panel 257 (schema from briefs/earpanel257-spec.txt).

= the 235b loader's schema (claude_smolear235b_panel: line keys, 150 lines, family counts,
  TEACH keys) + ASK frames carry `chain_aliases`:
    ASK = exactly {act, subject, relation, chain, relation_aliases, chain_aliases}
    chain null  <=> chain_aliases null
    chain = [hop1, hop2] with hop2 == relation; chain_aliases = [list, list] of strings and
    chain_aliases[1] == relation_aliases
Any deviation prints SCHEMA-MISMATCH and exits 3 (nothing scored). The panel file's sha256
must equal the director's SEAL line (else exit 4).
Scoring input: a two-hop ASK is scored on the hops in `chain`, with chain_aliases on EVERY hop;
one hop uses relation_aliases. Tags: R-tags (R1, R1rel, R2tag, ...) and lower/typo/noq/correction
from `notes`. `clear` is read for the schema only, never used for scoring.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235b_panel as P5  # noqa: E402

PANEL_SHA = "1d1b5588b787866bf986e6ea8500be70200b980dfe5734622a85b90e7d942fd3"
ASK_KEYS = P5.ASK_KEYS | {"chain_aliases"}
EXTRA_TAGS = {"lower", "typo", "noq", "correction"}


def _strlist(x):
    return isinstance(x, list) and all(isinstance(y, str) for y in x)


def check(lines):
    errs, ids, fam = [], set(), {}
    for n, d in enumerate(lines):
        where = f"line {n + 1}"
        if not isinstance(d, dict) or set(d) != P5.LINE_KEYS:
            errs.append(f"{where}: keys {sorted(d) if isinstance(d, dict) else type(d)}")
            continue
        if d["id"] in ids:
            errs.append(f"{where}: duplicate id")
        ids.add(d["id"])
        if d["family"] not in P5.COUNTS:
            errs.append(f"{where}: unknown family")
        fam[d["family"]] = fam.get(d["family"], 0) + 1
        if not isinstance(d["turn"], str) or not d["turn"].strip():
            errs.append(f"{where}: bad turn")
        if not isinstance(d["clear"], bool) or not isinstance(d["notes"], str):
            errs.append(f"{where}: bad clear/notes type")
        if not isinstance(d["gold"], list):
            errs.append(f"{where}: gold not a list")
            continue
        for g in d["gold"]:
            act = g.get("act") if isinstance(g, dict) else None
            if act == "TEACH":
                if set(g) != P5.TEACH_KEYS:
                    errs.append(f"{where}: TEACH keys {sorted(g)}")
            elif act == "ASK":
                if set(g) != ASK_KEYS:
                    errs.append(f"{where}: ASK keys {sorted(g)}")
                    continue
                ch, ca = g["chain"], g["chain_aliases"]
                if ch is None:
                    if ca is not None:
                        errs.append(f"{where}: chain null but chain_aliases set")
                elif not (isinstance(ch, list) and len(ch) == 2 and ch[-1] == g["relation"]):
                    errs.append(f"{where}: bad chain")
                elif not (isinstance(ca, list) and len(ca) == 2 and all(_strlist(x) for x in ca)):
                    errs.append(f"{where}: bad chain_aliases")
                elif ca[1] != g["relation_aliases"]:
                    errs.append(f"{where}: chain_aliases[1] != relation_aliases")
            else:
                errs.append(f"{where}: bad act")
            if isinstance(g, dict) and not _strlist(g.get("relation_aliases")):
                errs.append(f"{where}: relation_aliases not a list of strings")
    if len(lines) != 150:
        errs.append(f"{len(lines)} lines, expected 150")
    if fam != P5.COUNTS:
        errs.append(f"family counts {fam}")
    return errs


def load_panel(path, check_sha=True):
    raw = Path(path).read_bytes()
    if check_sha and hashlib.sha256(raw).hexdigest() != PANEL_SHA:
        print("PANEL-SHA-MISMATCH", file=sys.stderr)
        sys.exit(4)
    lines = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    errs = check(lines)
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
        tags = sorted({t for t in toks if re.fullmatch(r"R\d\w*", t)} | (set(toks) & EXTRA_TAGS))
        items.append(dict(id=d["id"], family=d["family"], turn=d["turn"], context=[], tags=tags, gold=gold))
    return items
