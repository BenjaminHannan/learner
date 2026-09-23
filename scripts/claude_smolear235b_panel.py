#!/usr/bin/env python3
"""Exp 235b -- strict loader for ear panel 235b (schema from S/briefs/earpanel235b-spec.txt).

SCHEMA-MISMATCH check: any deviation from the spec below prints every problem and
exits with code 3 (nothing is scored).
  line  = exactly {id, family, turn, gold, clear, notes}; 150 lines; ids unique
  family counts: plain_teach 25, varied_teach 30, full_names 15, questions 25,
                 chain_questions 15, no_save 25, corrections 15
  TEACH = exactly {act, subject, relation, relation_aliases, value}
  ASK   = exactly {act, subject, relation, chain, relation_aliases};
          chain null (one hop) or [hop1, hop2] with hop2 == relation
The 235 chain-gold fix is built in: a two-hop ASK is scored on the hops in `chain`;
relation_aliases apply to the LAST hop only. Tags R1/R2/R3 come from `notes`.
The `clear` flag is read (schema) but never used for scoring.
Output items: {id, family, turn, context: [], tags, gold: [{act, subject,
relation: [hops], value?, aliases: [[...] per hop]}]}.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

COUNTS = {"plain_teach": 25, "varied_teach": 30, "full_names": 15, "questions": 25,
          "chain_questions": 15, "no_save": 25, "corrections": 15}
LINE_KEYS = {"id", "family", "turn", "gold", "clear", "notes"}
TEACH_KEYS = {"act", "subject", "relation", "relation_aliases", "value"}
ASK_KEYS = {"act", "subject", "relation", "chain", "relation_aliases"}


def check(lines):
    errs, ids, fam = [], set(), {}
    for n, d in enumerate(lines):
        where = f"line {n + 1}"
        if not isinstance(d, dict) or set(d) != LINE_KEYS:
            errs.append(f"{where}: keys {sorted(d) if isinstance(d, dict) else type(d)}")
            continue
        if d["id"] in ids:
            errs.append(f"{where}: duplicate id")
        ids.add(d["id"])
        if d["family"] not in COUNTS:
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
                if set(g) != TEACH_KEYS:
                    errs.append(f"{where}: TEACH keys {sorted(g)}")
            elif act == "ASK":
                if set(g) != ASK_KEYS:
                    errs.append(f"{where}: ASK keys {sorted(g)}")
                elif g["chain"] is not None and not (
                        isinstance(g["chain"], list) and len(g["chain"]) == 2
                        and g["chain"][-1] == g["relation"]):
                    errs.append(f"{where}: bad chain")
            else:
                errs.append(f"{where}: bad act")
            if isinstance(g, dict) and not isinstance(g.get("relation_aliases"), list):
                errs.append(f"{where}: relation_aliases not a list")
    if len(lines) != 150:
        errs.append(f"{len(lines)} lines, expected 150")
    if fam != COUNTS:
        errs.append(f"family counts {fam}")
    return errs


def load_panel(path):
    lines = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
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
                aliases = [[] for _ in hops[:-1]] + [al]
            else:
                hops, aliases = [str(g["relation"]).strip()], [al]
            fr = dict(act=g["act"], subject=str(g["subject"]), relation=hops, aliases=aliases)
            if g["act"] == "TEACH":
                fr["value"] = str(g["value"])
            gold.append(fr)
        tags = sorted(set(re.findall(r"\bR[123]\b", d["notes"])))
        items.append(dict(id=d["id"], family=d["family"], turn=d["turn"], context=[], tags=tags, gold=gold))
    return items
