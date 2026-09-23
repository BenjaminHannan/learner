#!/usr/bin/env python3
"""Exp 265 -- strict loader for ourpanel265 (schema per
handoff/kit/briefs/ourpanel265-spec.txt: earpanel264 line format PLUS the new
boolean field "ask_whose"; folder artifacts/claude-ourpanel265-20260923/;
ids "o265-001".."o265-080"; families group_owner 30 / mixed 15 /
first_person 20 / named 15).

The panel sha is verified against the panel's own SEAL.sha256.txt (checked OK
from the repo root), never a hardcoded hash. Any schema deviation prints
SCHEMA-MISMATCH and exits 3 (nothing scored). A sha mismatch exits 4.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_panel as P7  # noqa: E402
import claude_smolear235b_panel as P5  # noqa: E402

LINE_KEYS_265 = {"id", "family", "turn", "gold", "clear", "notes", "ask_whose"}

FAMS_265 = {"group_owner": 30, "mixed": 15, "first_person": 20, "named": 15}

ID_RE = re.compile(r"^o265-(00[1-9]|0[1-9][0-9]|080)$")

DEV_ID_RE = re.compile(r"^d265-[0-9]{3}$")


def _expect_sha(panel_path, seal_path):
    lines = Path(seal_path).read_text().splitlines()
    for ln in lines:
        parts = ln.strip().split()
        if len(parts) == 2 and parts[1].endswith("panel.jsonl"):
            return parts[0]
    raise SystemExit(f"no panel.jsonl line in seal {seal_path}")


def check_265(lines, id_re, fams):
    """Strict per-line checks mirrored from the 257/264 loaders, adapted for
    the 265 line keys and families. Returns a list of error strings."""
    errs, ids, fam = [], set(), {}
    for n, d in enumerate(lines):
        where = f"line {n + 1}"
        if not isinstance(d, dict) or set(d) != LINE_KEYS_265:
            errs.append(f"{where}: keys {sorted(d) if isinstance(d, dict) else type(d)}")
            continue
        if d["id"] in ids:
            errs.append(f"{where}: duplicate id")
        ids.add(d["id"])
        if not (isinstance(d["id"], str) and id_re.match(d["id"])):
            errs.append(f"{where}: bad id {d['id']!r}")
        if d["family"] not in fams:
            errs.append(f"{where}: unknown family {d.get('family')!r}")
        fam[d["family"]] = fam.get(d["family"], 0) + 1
        if not isinstance(d["turn"], str) or not d["turn"].strip():
            errs.append(f"{where}: bad turn")
        if not isinstance(d["clear"], bool) or not isinstance(d["notes"], str):
            errs.append(f"{where}: bad clear/notes type")
        if not isinstance(d["ask_whose"], bool):
            errs.append(f"{where}: bad ask_whose type")
        if not isinstance(d["gold"], list):
            errs.append(f"{where}: gold not a list")
            continue
        for g in d["gold"]:
            act = g.get("act") if isinstance(g, dict) else None
            if act == "TEACH":
                if set(g) != P5.TEACH_KEYS:
                    errs.append(f"{where}: TEACH keys {sorted(g)}")
            elif act == "ASK":
                keys = set(g)
                if keys != (P5.ASK_KEYS | {"chain_aliases"}):
                    errs.append(f"{where}: ASK keys {sorted(keys)}")
            else:
                errs.append(f"{where}: bad act")
    if fam != fams:
        errs.append(f"family counts {fam} != {fams}")
    return errs


def to_items(lines):
    items = []
    for d in lines:
        gold = []
        for g in d["gold"]:
            al = [str(x) for x in g["relation_aliases"]]
            if g["act"] == "ASK" and g.get("chain"):
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
                          context=[], tags=tags, gold=gold,
                          ask_whose=bool(d["ask_whose"])))
    return items


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
    if len(lines) != 80:
        print(f"SCHEMA-MISMATCH:\n  expected 80 lines, got {len(lines)}", file=sys.stderr)
        sys.exit(3)
    errs = []
    for n, d in enumerate(lines):
        if not isinstance(d, dict) or set(d) != LINE_KEYS_265:
            errs.append(f"line {n + 1}: keys "
                        f"{sorted(d) if isinstance(d, dict) else type(d)}")
    good = [d for d in lines
            if isinstance(d, dict) and set(d) == LINE_KEYS_265]
    errs += check_265(good, ID_RE, FAMS_265)
    if errs:
        print("SCHEMA-MISMATCH:", *errs[:50], sep="\n  ", file=sys.stderr)
        sys.exit(3)
    return to_items(lines)


def load_dev(path):
    """Dev file in the same line format (ids d265-NNN, any family mix, no sha,
    no count bar). Same strictness otherwise."""
    lines = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines()
             if x.strip()]
    errs = []
    ids = set()
    for n, d in enumerate(lines):
        where = f"line {n + 1}"
        if not isinstance(d, dict) or set(d) != LINE_KEYS_265:
            errs.append(f"{where}: keys {sorted(d) if isinstance(d, dict) else type(d)}")
            continue
        if d["id"] in ids:
            errs.append(f"{where}: duplicate id")
        ids.add(d["id"])
        if not (isinstance(d["id"], str) and DEV_ID_RE.match(d["id"])):
            errs.append(f"{where}: bad id {d['id']!r}")
    good = [d for d in lines
            if isinstance(d, dict) and set(d) == LINE_KEYS_265]
    errs += [e for e in check_265(good, DEV_ID_RE,
                                  {f: sum(1 for x in good if x.get("family") == f)
                                   for f in FAMS_265})
             if not e.startswith("family counts")]
    for n, d in enumerate(lines):
        if isinstance(d, dict) and "family" in d and d["family"] not in FAMS_265:
            errs.append(f"line {n + 1}: unknown family {d.get('family')!r}")
    if errs:
        print("SCHEMA-MISMATCH:", *errs[:50], sep="\n  ", file=sys.stderr)
        sys.exit(3)
    return to_items(good)
