"""own-O0a3 PERMISSION AUDIT: can a WRONG reading get through the write rules?

own-O0a/O0a2 asked "can every TRUE fact get through?" (coverage ceiling with a
perfect reader). This asks the other side: "can a WRONG reading get through?"
(audit of the same rules against misreadings). Coverage bought by loosening
safety (v0 -> v1 -> learned-licensed) must show up here.

Inputs (all read-only, never modified, never re-sealed):
  artifacts/claude-own-o0a-20260923/turns.jsonl + gold.jsonl   (dev set 1)
  artifacts/claude-own-o0a2-20260923/turns.jsonl + gold.jsonl  (dev set 2)
  artifacts/claude-smolear257-20260922/relation_table_v2.json  (relation table)
  scripts/claude_own_o0a_compiler.py   (v0 code, imported read-only)
  scripts/claude_own_o0a2_compiler.py  (v1 extras, imported read-only)

Mutations (one change each from the gold reading; every applicable one made):
  From every gold ASSERT/CORRECT/DENY fact:
    m1: owner swapped to another name span in the same turn
    m2: value swapped to another word span in the turn
    m3: owner and value reversed
    m4: relation swapped to another table relation whose (v0) cue IS in turn
    m5: relation swapped to a table relation whose cue is NOT in the turn
        (absent under BOTH v0 and v1 cue expressions; first 3 alphabetically)
    m6: owner ME<->WE, or a name owner -> ME  (subs: me2we / we2me / name2me)
    m7: value trimmed (multi-word: drop last word) or extended by one
        adjacent turn word (single-word)
  From every gold no-save fact (CHECK/SUPPOSE/PLAN/ASK/REPORTED):
    m8: mode flipped to ASSERT (spans and relation unchanged)

Each wrong reading is fed to three rules (v0 / v1 / learned-licensed) with the
WE policy of Ben's 2026-09-23 ruling (WE is never saved as the speaker; it
asks): i.e. we_allowed=False in every judge. Judges reuse the sealed
expressions read-only (v0 toks/has_span/cue expression; o0a2 plural/template
extras); the judge body is the same mode > OTHER > owner > value > WE > cue
ladder as scripts/claude_own_o0a2_compiler.py.

Outputs: <outdir>/mutations.jsonl (one row per wrong reading x rule verdicts
plus the gold fact's own verdicts) and <outdir>/summary.json (integer counts
per kind x rule: made / blocked / through, plus the "clean" subset: mutants
whose gold fact is itself writable under that rule).

CPU only, no model, no downloads, no randomness. Fictional names only (inputs
already are). Never opens any TEST-ONLY panel.

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_own_o0a3_mutate.py [outdir]
Default outdir: artifacts/claude-own-o0a3-20260923 (registered run only).
Pilot runs must pass a scratch dir (e.g. /tmp/o0a3pilot).
"""

import importlib.util
import json
import os
import re
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_A = os.path.join(REPO, "artifacts", "claude-own-o0a-20260923")
SRC_B = os.path.join(REPO, "artifacts", "claude-own-o0a2-20260923")
REL_TABLE = os.path.join(
    REPO, "artifacts", "claude-smolear257-20260922", "relation_table_v2.json")

WRITE_MODES = ("ASSERT", "CORRECT", "DENY")
RULES = ("v0", "v1", "licensed")
# Ben's 2026-09-23 ruling: WE is never saved as the speaker; it asks.
WE_ALLOWED = False

# Capitalized turn words whose lowercase form is here are NOT name spans
# (sentence starters, interrogatives, pronouns, determiners, verbs of asking).
STOP = frozenset((
    "i", "my", "our", "we", "us", "is", "are", "was", "were", "be", "been",
    "who", "what", "where", "when", "why", "how", "which", "whose",
    "does", "did", "do", "has", "have", "had", "can", "could", "will",
    "would", "should", "he", "she", "they", "him", "her", "them", "his",
    "their", "it", "its", "the", "this", "that", "these", "those",
    "no", "yes", "so", "if", "in", "at", "on", "to", "of", "for", "as",
    "a", "an", "and", "but", "or", "not", "there", "here", "then",
    "with", "let", "give", "tell", "say", "said", "suppose", "assume",
))


def _load_module(fname, modname):
    path = os.path.join(REPO, "scripts", fname)
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # read-only reuse; main() never executed
    return mod


V0 = _load_module("claude_own_o0a_compiler.py", "claude_own_o0a_compiler")
O0A2 = _load_module("claude_own_o0a2_compiler.py", "claude_own_o0a2_compiler")
toks = V0.toks
has_span = V0.has_span


def words_orig(turn):
    """Original-case alphanumeric words of the turn, in order."""
    return re.findall(r"[A-Za-z0-9]+", turn)


def build_cues():
    with open(REL_TABLE) as f:
        table = json.load(f)["relations"]
    cue_of = {}
    for r in table:
        cues = {r["name"].lower()} | {a.lower() for a in r.get("aliases", [])}
        cue_of[r["name"]] = [toks(c) for c in cues]
    extra_of = {}
    for r in table:
        extra = []
        for c in cue_of[r["name"]]:
            extra.extend(O0A2.plural_variants(c))
        for x in r.get("teach", []):
            extra.extend(O0A2.template_fixed_tokens(x.get("t", "")))
        seen = {tuple(c) for c in cue_of[r["name"]]}
        uniq = []
        for e in extra:
            if e and tuple(e) not in seen:
                seen.add(tuple(e))
                uniq.append(e)
        extra_of[r["name"]] = uniq
    return cue_of, extra_of


CUE_OF, EXTRA_OF = build_cues()
VALID_RELATIONS = set(CUE_OF)


def cue_hit_v0(tt, rel):
    return any(
        any(tt[i:i + len(c)] == c for i in range(len(tt) - len(c) + 1))
        for c in CUE_OF[rel] if c)


def cue_hit_v1(tt, rel):
    return any(
        any(tt[i:i + len(c)] == c for i in range(len(tt) - len(c) + 1))
        for c in (CUE_OF[rel] + EXTRA_OF[rel]) if c)


def judge(turn_text, fact, rule):
    """Same ladder as the o0a2 compiler; WE never allowed (Ben's ruling)."""
    tt = toks(turn_text)
    if fact["mode"] not in WRITE_MODES:
        return False, "no-save-mode"
    rel = fact["relation"]
    if rel.startswith("OTHER:"):
        return False, "relation-OTHER"
    assert rel in VALID_RELATIONS, "unknown relation: %r" % rel
    owner = fact["owner"]
    if owner == "ME":
        pass
    elif owner == "WE":
        return False, "WE-owner"  # WE_ALLOWED is False, always
    else:
        if not has_span(tt, owner):
            return False, "owner-not-span"
    if not has_span(tt, fact["value"]):
        if fact.get("typo"):
            return False, "typo"
        return False, "value-not-span"
    if rule == "v0":
        if not cue_hit_v0(tt, rel):
            return False, "no-relation-cue"
    elif rule == "v1":
        if not cue_hit_v1(tt, rel):
            return False, "no-relation-cue"
    elif rule == "licensed":
        pass
    else:
        raise AssertionError(rule)
    return True, "writable"


def name_spans(turn):
    """Distinct capitalized non-stop words of the turn (original case)."""
    seen = set()
    out = []
    for w in words_orig(turn):
        if len(w) >= 2 and w[0].isupper() and w.lower() not in STOP:
            if w.lower() not in seen:
                seen.add(w.lower())
                out.append(w)
    return out


def distinct_words(turn):
    """Distinct turn words len>=2, not stopwords: (original, lower)."""
    seen = set()
    out = []
    for w in words_orig(turn):
        lw = w.lower()
        if len(w) >= 2 and lw not in STOP and lw not in seen:
            seen.add(lw)
            out.append((w, lw))
    return out


def copy_fact(fact):
    return {"owner": fact["owner"], "relation": fact["relation"],
            "value": fact["value"], "mode": fact["mode"]}


def mutate_acd(src, tid, turn, fact):
    """Yield (kind, sub, mutant_fact, note) for one gold ACD fact."""
    owner, rel, val = fact["owner"], fact["relation"], fact["value"]
    names = name_spans(turn)
    # m1: owner -> another name span in the same turn
    if owner not in ("ME", "WE"):
        cands = [n for n in names if n.lower() != owner.lower()]
    else:
        cands = [n for n in names if n.lower() not in ("me", "we")]
    for n in sorted(set(cands), key=str.lower):
        m = copy_fact(fact)
        m["owner"] = n
        yield ("m1", "", m, "owner %s -> name span %s" % (owner, n))
    # m2: value -> another word span in the turn
    vt = toks(val)
    for w_orig, w_low in sorted(distinct_words(turn), key=lambda p: p[1]):
        if vt == [w_low]:
            continue
        m = copy_fact(fact)
        m["value"] = w_orig
        yield ("m2", "", m, "value %s -> word span %s" % (val, w_orig))
    # m3: owner and value reversed (name owners only, nonempty value)
    if owner not in ("ME", "WE") and val and val.lower() != owner.lower():
        m = copy_fact(fact)
        m["owner"] = val
        m["value"] = owner
        yield ("m3", "", m, "owner/value reversed")
    # m4: relation -> another table relation whose v0 cue IS in the turn
    tt = toks(turn)
    for other in sorted(VALID_RELATIONS):
        if other == rel:
            continue
        if cue_hit_v0(tt, other):
            m = copy_fact(fact)
            m["relation"] = other
            yield ("m4", "", m, "relation %s -> cued %s" % (rel, other))
    # m5: relation -> table relation whose cue is NOT in the turn
    # (absent under both v0 and v1 expressions; first 3 alphabetically)
    absent = [o for o in sorted(VALID_RELATIONS)
              if o != rel and not cue_hit_v0(tt, o)
              and not cue_hit_v1(tt, o)]
    for other in absent[:3]:
        m = copy_fact(fact)
        m["relation"] = other
        yield ("m5", "", m, "relation %s -> uncued %s" % (rel, other))
    # m6: ME<->WE, or name -> ME
    m = copy_fact(fact)
    if owner == "ME":
        m["owner"] = "WE"
        yield ("m6", "me2we", m, "owner ME -> WE")
    elif owner == "WE":
        m["owner"] = "ME"
        yield ("m6", "we2me", m, "owner WE -> ME")
    else:
        m["owner"] = "ME"
        yield ("m6", "name2me", m, "owner %s -> ME" % owner)
    # m7: value trimmed or extended by one word
    if len(vt) >= 2:
        m = copy_fact(fact)
        m["value"] = " ".join(val.split()[:-1])
        yield ("m7", "trim", m, "value trimmed to %s" % m["value"])
    elif len(vt) == 1:
        low = [w.lower() for w in words_orig(turn)]
        idx = None
        for i in range(len(low) - len(vt) + 1):
            if low[i:i + len(vt)] == vt:
                idx = i
                break
        if idx is not None:
            ow = words_orig(turn)
            if idx + len(vt) < len(ow):
                m = copy_fact(fact)
                m["value"] = val + " " + ow[idx + len(vt)]
                yield ("m7", "extend-next", m,
                       "value extended to %s" % m["value"])
            elif idx > 0:
                m = copy_fact(fact)
                m["value"] = ow[idx - 1] + " " + val
                yield ("m7", "extend-prev", m,
                       "value extended to %s" % m["value"])


def mutate_nosave(src, tid, turn, fact):
    """m8: flip a no-save gold fact's mode to ASSERT."""
    m = copy_fact(fact)
    m["mode"] = "ASSERT"
    yield ("m8", "", m, "mode %s -> ASSERT" % fact["mode"])


def load_inputs():
    items = []  # (src, tid, turn, fact)
    for src, art in (("o0a", SRC_A), ("o0a2", SRC_B)):
        turns = {}
        with open(os.path.join(art, "turns.jsonl")) as f:
            for line in f:
                d = json.loads(line)
                turns[d["id"]] = d["turn"]
        with open(os.path.join(art, "gold.jsonl")) as f:
            for line in f:
                d = json.loads(line)
                for fact in d["facts"]:
                    items.append((src, d["id"], turns[d["id"]], fact))
    return items


def main():
    outdir = (sys.argv[1] if len(sys.argv) > 1
              else os.path.join(REPO, "artifacts", "claude-own-o0a3-20260923"))
    os.makedirs(outdir, exist_ok=True)
    items = load_inputs()
    acd = [(s, i, t, f) for (s, i, t, f) in items
           if f["mode"] in WRITE_MODES]
    nsv = [(s, i, t, f) for (s, i, t, f) in items
           if f["mode"] not in WRITE_MODES]

    rows = []
    for (src, tid, turn, fact) in acd:
        for (kind, sub, m, note) in mutate_acd(src, tid, turn, fact):
            verdicts = {}
            for rule in RULES:
                ok, reason = judge(turn, m, rule)
                verdicts[rule] = {"writable": ok, "reason": reason}
            gold_v = {}
            for rule in RULES:
                ok, reason = judge(turn, fact, rule)
                gold_v[rule] = {"writable": ok, "reason": reason}
            rows.append({"src": src, "id": tid, "turn": turn,
                         "kind": kind, "sub": sub, "note": note,
                         "gold": fact, "mutant": m,
                         "verdicts": verdicts, "gold_verdicts": gold_v})
    for (src, tid, turn, fact) in nsv:
        for (kind, sub, m, note) in mutate_nosave(src, tid, turn, fact):
            verdicts = {}
            for rule in RULES:
                ok, reason = judge(turn, m, rule)
                verdicts[rule] = {"writable": ok, "reason": reason}
            gold_v = {}
            for rule in RULES:
                ok, reason = judge(turn, fact, rule)
                gold_v[rule] = {"writable": ok, "reason": reason}
            rows.append({"src": src, "id": tid, "turn": turn,
                         "kind": kind, "sub": sub, "note": note,
                         "gold": fact, "mutant": m,
                         "verdicts": verdicts, "gold_verdicts": gold_v})

    with open(os.path.join(outdir, "mutations.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    # Summary: per (kind, sub, rule): made / blocked / through (+ clean).
    summary = {"n_gold_acd": len(acd), "n_gold_nosave": len(nsv),
               "n_mutants": len(rows), "we_allowed": WE_ALLOWED,
               "cells": {}}
    kinds = sorted(set((r["kind"], r["sub"]) for r in rows))
    for (kind, sub) in kinds:
        key = kind if not sub else kind + ":" + sub
        summary["cells"][key] = {}
        sel = [r for r in rows if r["kind"] == kind and r["sub"] == sub]
        for rule in RULES:
            blocked = sum(1 for r in sel if not r["verdicts"][rule]["writable"])
            through = sum(1 for r in sel if r["verdicts"][rule]["writable"])
            assert blocked + through == len(sel)
            clean = [r for r in sel if r["gold_verdicts"][rule]["writable"]]
            c_blocked = sum(1 for r in clean
                            if not r["verdicts"][rule]["writable"])
            c_through = sum(1 for r in clean
                            if r["verdicts"][rule]["writable"])
            reasons = dict(Counter(r["verdicts"][rule]["reason"] for r in sel))
            summary["cells"][key][rule] = {
                "made": len(sel), "blocked": blocked, "through": through,
                "clean_made": len(clean), "clean_blocked": c_blocked,
                "clean_through": c_through, "reasons": reasons}
    with open(os.path.join(outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)

    print("gold ACD %d, gold nosave %d, wrong readings %d"
          % (len(acd), len(nsv), len(rows)))
    for (kind, sub) in kinds:
        key = kind if not sub else kind + ":" + sub
        parts = []
        for rule in RULES:
            c = summary["cells"][key][rule]
            parts.append("%s made=%d blocked=%d through=%d "
                         "clean=%d/%d/%d" % (
                             rule, c["made"], c["blocked"], c["through"],
                             c["clean_made"], c["clean_blocked"],
                             c["clean_through"]))
        print(key + ": " + " | ".join(parts))


if __name__ == "__main__":
    main()
