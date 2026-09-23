#!/usr/bin/env python3
"""Exp 102 pre-build collision scan (design validation, NOT a registered run).

Applies the planned Loop102 pre-filter regexes to every English turn in the
sealed corpora (redteam98 64 cases, turns84 60 turns, bench200 sentences,
redteam81 SEQS) and reports every hit outside the 16 known BUG turns.
Pure text scan: no agent is built or run.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fable_bench73_english_arm as B73  # noqa: E402 (read-only patterns)

HEARSAY_RES = [
    re.compile(r",[^,.\n]{1,40}?\bsaid\s*\.?\s*$", re.I),
    re.compile(r"\baccording\s+to\b", re.I),
    re.compile(r"\bread\s+online\b", re.I),
    re.compile(r"\bi\s+read\s+that\b", re.I),
    re.compile(r"\bi\s+heard\b", re.I),
    re.compile(r"\bapparently\b", re.I),
    re.compile(r"\breportedly\b", re.I),
    re.compile(r"^quote[\s:]", re.I),
    re.compile(r"\bthe\s+web\s+says\b", re.I),
]
PREFIX_RE = re.compile(
    r"^(actually\s*,|actually\s+|no\s*,|correction\s*:|sorry\s*,?\s*i\s+meant\s*,?)\s+(.+)$",
    re.I | re.S)
FORGET_VERB_RE = re.compile(r"^(please\s+)?forget(\s|$)", re.I)
QUAL_RES = [
    re.compile(r"\s+from\s+\d{4}\s+to\s+\d{4}\s*\.?\s*$", re.I),
    re.compile(r"\s+as\s+of\s+\d{4}\s*\.?\s*$", re.I),
    re.compile(r"\s+(in|since|until)\s+\d{4}\s*\.?\s*$", re.I),
]


def norm(t):
    return " ".join(str(t).split())


def cap1(t):
    return t[:1].upper() + t[1:] if t else t


def strip_qual(t):
    for rx in QUAL_RES:
        if rx.search(t):
            return rx.sub("", t).strip()
    return t


def hits(text):
    t = norm(text)
    out = []
    if any(r.search(t) for r in HEARSAY_RES):
        out.append("hearsay")
    m = PREFIX_RE.match(t)
    if m and B73.hear_teach_template(cap1(m.group(2).strip())):
        out.append("corrprefix")
    if FORGET_VERB_RE.match(t) and not t.rstrip().endswith("?"):
        out.append("forgetverb")
    if not t.rstrip().endswith("?") and strip_qual(t) != t:
        out.append("qualstrip")
    tr = B73.hear_teach_template(t)
    if tr is not None and tr[0][:1].islower():
        out.append("lowersubj")
    return out


def collect():
    rows = []
    sys.path.insert(0, str(ROOT / "scripts"))
    import fable_redteam98_cases as RC
    for c in RC.CASES:
        for i, st in enumerate(c["steps"]):
            if st["op"] == "send":
                rows.append((f"rt98-{c['id']}", i, st["text"]))
    for line in (ROOT / "data/open/turns84/turns.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows.append((f"turns84-{r['n']}", 0, r["turn"]))
    for line in (ROOT / "data/open/bench65/fable_edit_200.jsonl").read_text().splitlines():
        if line.strip():
            it = json.loads(line)
            for k, s in enumerate(s["sentence_en"] for s in it["taught"]):
                rows.append((f"bench200-{it['id']}-t{k}", 0, s))
            rows.append((f"bench200-{it['id']}-q", 0, it["question"]))
    import fable_redteam81_probe as P81
    for seq_id, _d, steps in P81.SEQS:
        for i, st in enumerate(steps):
            if isinstance(st, dict) and st.get("turn", "").strip() and st["turn"] != "__SETUP_SECOND_MIRA__":
                rows.append((f"rt81-{seq_id}-{i}", 0, st["turn"]))
    # P4 innocents
    p4 = json.loads((ROOT / "artifacts/fable-loop102-20260921/p4-innocent-30.json").read_text())
    for s in p4["sentences"]:
        rows.append((s["id"], 0, s["text"]))
        for u in s.get("setup", []):
            rows.append((s["id"] + "-setup", 0, u))
    return rows


KNOWN = {  # BUG-turn hits the filters are *supposed* to catch
    ("rt98-A2", 1), ("rt98-A3", 1), ("rt98-A5", 1), ("rt98-A6", 1),
    ("rt98-A8", 2), ("rt98-B5", 2), ("rt98-D2", 0), ("rt98-D7", 0),
    ("rt98-C1", 2), ("rt98-C2", 2), ("rt98-C3", 1), ("rt98-C4", 1),
    ("rt98-C5", 2), ("rt98-C7", 1), ("rt98-C7", 2),
    ("rt98-A1", 1),  # leading-quote clarify (already clarifies today)
    ("rt98-B4", 2),  # Actually-possessive falls through to FakeEars (no corrprefix hit expected)
    ("rt98-G1", 2),  # forget-verb hit expected; ambiguity guard clarifies
    ("rt98-C6", 1), ("rt98-C8", 1),
}

rows = collect()
print(f"scanned {len(rows)} turns")
n_hit = 0
for cid, i, text in rows:
    h = hits(text)
    if not h:
        continue
    n_hit += 1
    flag = "" if (cid, i) in KNOWN else "  <-- UNEXPECTED"
    print(f"{cid}[{i}] {h} :: {text[:100]!r}{flag}")
print(f"total hits: {n_hit}")
