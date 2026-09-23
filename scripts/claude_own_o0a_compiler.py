"""own-O0a: v0 write compiler of plan 01-own-ear-mouth-plan.md section 4.1,
fed the ORACLE (gold) readings. CPU only, no model, no downloads.

A gold fact is AUTO-WRITABLE only if ALL hold:
  mode is ASSERT, CORRECT or DENY;
  owner is ME, or a whole-word span of the turn equal to the gold owner string
    (case-insensitive, possessive 's splits off in tokenisation);
  value is a whole-word span of the turn equal to the gold value string
    (a typo'd value is NOT writable automatically);
  relation is in relation table v2 (not OTHER) and some whole-word span of the
    turn is one of that relation's names or aliases (the relation cue; strict
    exact-word match, case-insensitive);
  WE owners counted both ways (WE->ME allowed / not allowed).

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_own_o0a_compiler.py
Reads: artifacts/claude-smolear257-20260922/relation_table_v2.json (read-only),
  artifacts/claude-own-o0a-20260923/turns.jsonl + gold.jsonl (read-only).
Writes: artifacts/claude-own-o0a-20260923/oracle_coverage.json (counts + lists).
Prints: integer counts for RESULTS.md / ledger.
"""
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(REPO, "artifacts", "claude-own-o0a-20260923")
REL_TABLE = os.path.join(
    REPO, "artifacts", "claude-smolear257-20260922", "relation_table_v2.json")

WRITE_MODES = ("ASSERT", "CORRECT", "DENY")


def toks(s):
    """Lowercase alphanumeric word tokens. 'Mira's' -> ['mira','s'] etc."""
    return re.findall(r"[a-z0-9]+", s.lower())


def has_span(turn_toks, phrase):
    """True if phrase's tokens form a contiguous subsequence of the turn."""
    pt = toks(phrase)
    if not pt:
        return False
    n = len(pt)
    return any(turn_toks[i:i + n] == pt for i in range(len(turn_toks) - n + 1))


def main():
    with open(REL_TABLE) as f:
        table = json.load(f)["relations"]
    cue_of = {}
    for r in table:
        cues = {r["name"].lower()} | {a.lower() for a in r.get("aliases", [])}
        cue_of[r["name"]] = [toks(c) for c in cues]
    valid_relations = set(cue_of)

    turns = {}
    with open(os.path.join(ART, "turns.jsonl")) as f:
        for line in f:
            d = json.loads(line)
            turns[d["id"]] = d["turn"]
    gold = []
    with open(os.path.join(ART, "gold.jsonl")) as f:
        for line in f:
            d = json.loads(line)
            for fact in d["facts"]:
                gold.append((d["id"], turns[d["id"]], fact))

    def judge(turn_text, fact, we_allowed):
        tt = toks(turn_text)
        if fact["mode"] not in WRITE_MODES:
            return False, "no-save-mode"
        rel = fact["relation"]
        if rel.startswith("OTHER:"):
            return False, "relation-OTHER"
        assert rel in valid_relations, "unknown relation: %r" % rel
        owner = fact["owner"]
        if owner == "ME":
            pass
        elif owner == "WE":
            if not we_allowed:
                return False, "WE-owner"
        else:
            if not has_span(tt, owner):
                return False, "owner-not-span"
        if not has_span(tt, fact["value"]):
            if fact.get("typo"):
                return False, "typo"
            return False, "value-not-span"
        if not any(
                any(tt[i:i + len(c)] == c for i in range(len(tt) - len(c) + 1))
                for c in cue_of[rel] if c):
            return False, "no-relation-cue"
        return True, "writable"

    out = {}
    for we_allowed in (False, True):
        rows = []
        for tid, turn_text, fact in gold:
            ok, reason = judge(turn_text, fact, we_allowed)
            rows.append({"id": tid, "turn": turn_text, "fact": fact,
                         "writable": ok, "reason": reason})
        acd = [r for r in rows if r["fact"]["mode"] in WRITE_MODES]
        nsv = [r for r in rows if r["fact"]["mode"] not in WRITE_MODES]
        w_acd = [r for r in acd if r["writable"]]
        w_nsv = [r for r in nsv if r["writable"]]
        by_reason = {}
        for r in acd:
            if not r["writable"]:
                by_reason[r["reason"]] = by_reason.get(r["reason"], 0) + 1
        key = "we_not_allowed" if not we_allowed else "we_allowed"
        out[key] = {
            "acd_total": len(acd),
            "acd_writable": len(w_acd),
            "acd_pct": (100.0 * len(w_acd) / len(acd)) if acd else 0.0,
            "nosave_total": len(nsv),
            "nosave_writable": len(w_nsv),
            "nonwritable_by_reason": by_reason,
            "nonwritable": [
                {"id": r["id"], "turn": r["turn"], "fact": r["fact"],
                 "reason": r["reason"]} for r in acd if not r["writable"]],
        }
    with open(os.path.join(ART, "oracle_coverage.json"), "w") as f:
        json.dump(out, f, indent=1)
    for key in ("we_not_allowed", "we_allowed"):
        o = out[key]
        print("%s: ACD %d/%d = %.1f%%; nosave-writable %d/%d; reasons %s" % (
            key, o["acd_writable"], o["acd_total"], o["acd_pct"],
            o["nosave_writable"], o["nosave_total"],
            json.dumps(o["nonwritable_by_reason"], sort_keys=True)))


if __name__ == "__main__":
    main()
