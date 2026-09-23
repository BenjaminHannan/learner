"""own-O0a2: v1 write compiler + three ceilings on FRESH dev turns.

v1 rule (the ONE change vs own-O0a v0): a relation cue also counts when a
whole-word span of the turn is
  (a) a plural or possessive form of the relation's name or alias
      (base + s / es / 's / s'), or
  (b) the fixed words of one of that relation's own "teach" templates in
      relation_table_v2.json (template text with {X} and {Y} removed,
      alternations (a|b) expanded, contiguous whole-word span match).
Everything else is v0-unchanged: mode in ASSERT/CORRECT/DENY; owner ME or an
exact whole-word span (WE counted both ways); value an exact whole-word span
(typos still need asking); OTHER never writable.

Three ceilings per fact x WE allowed/not allowed: v0 (same code as own-O0a,
imported read-only), v1, learned-licensed (relation needs no cue in the turn,
only the table name; spans and modes unchanged).

CPU only, no model, no downloads. Reads (read-only):
  artifacts/claude-smolear257-20260922/relation_table_v2.json,
  artifacts/claude-own-o0a2-20260923/turns.jsonl + gold.jsonl.
Writes: artifacts/claude-own-o0a2-20260923/oracle_coverage_o0a2.json.
"""
import importlib.util
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(REPO, "artifacts", "claude-own-o0a2-20260923")
REL_TABLE = os.path.join(
    REPO, "artifacts", "claude-smolear257-20260922", "relation_table_v2.json")

WRITE_MODES = ("ASSERT", "CORRECT", "DENY")


def _load_v0():
    # Read-only reuse of own-O0a code: import the module, never its main().
    path = os.path.join(REPO, "scripts", "claude_own_o0a_compiler.py")
    spec = importlib.util.spec_from_file_location("claude_own_o0a_compiler",
                                                  path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V0 = _load_v0()
toks = V0.toks          # same tokenizer as own-O0a
has_span = V0.has_span  # same span check as own-O0a


def expand_alternations(s):
    """Expand (a|b) groups into a list of strings (one per alternative)."""
    m = re.search(r"\(([^()|]+(?:\|[^()|]+)+)\)", s)
    if not m:
        return [s]
    opts = m.group(1).split("|")
    out = []
    for o in opts:
        out.extend(expand_alternations(s[:m.start()] + o + s[m.end():]))
    return out


def template_fixed_tokens(t):
    """Fixed-word token lists of one teach template, {X}/{Y} removed."""
    t = t.replace("{X}", " ").replace("{Y}", " ")
    t = t.replace("{R}", " ").replace("{WH}", " ")
    seqs = []
    for variant in expand_alternations(t):
        variant = re.sub(r"\[([^\]]*)\]", r"\1", variant)  # [optional] kept
        tt = toks(variant)
        if tt:
            seqs.append(tt)
    return seqs


def plural_variants(cue_tokens):
    """cue + s/es on the last word (possessive cue+'s is already covered:
    v0 matches the bare name inside 'name's')."""
    if not cue_tokens:
        return []
    out = []
    for suf in ("s", "es"):
        v = list(cue_tokens)
        v[-1] = v[-1] + suf
        out.append(v)
    return out


def main():
    with open(REL_TABLE) as f:
        table = json.load(f)["relations"]
    # v0 cues: same expression as own-O0a source (name + aliases).
    cue_of = {}
    for r in table:
        cues = {r["name"].lower()} | {a.lower() for a in r.get("aliases", [])}
        cue_of[r["name"]] = [toks(c) for c in cues]
    valid_relations = set(cue_of)
    # v1 extras per relation: plural variants + own teach-template fixed words.
    extra_of = {}
    for r in table:
        extra = []
        for c in cue_of[r["name"]]:
            extra.extend(plural_variants(c))
        for x in r.get("teach", []):
            extra.extend(template_fixed_tokens(x.get("t", "")))
        # de-duplicate, drop empties and cues v0 already covers
        seen = {tuple(c) for c in cue_of[r["name"]]}
        uniq = []
        for e in extra:
            if e and tuple(e) not in seen:
                seen.add(tuple(e))
                uniq.append(e)
        extra_of[r["name"]] = uniq

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

    def cue_hit(tt, rel, v1):
        seqs = cue_of[rel]
        if v1:
            seqs = seqs + extra_of[rel]
        return any(
            any(tt[i:i + len(c)] == c for i in range(len(tt) - len(c) + 1))
            for c in seqs if c)

    def judge(turn_text, fact, we_allowed, rule):
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
        if rule in ("v0", "v1"):
            if not cue_hit(tt, rel, v1=(rule == "v1")):
                return False, "no-relation-cue"
        elif rule == "licensed":
            pass
        else:
            raise AssertionError(rule)
        return True, "writable"

    out = {"rules": {}}
    for rule in ("v0", "v1", "licensed"):
        out["rules"][rule] = {}
        for we_allowed in (False, True):
            rows = []
            for tid, turn_text, fact in gold:
                ok, reason = judge(turn_text, fact, we_allowed, rule)
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
            out["rules"][rule][key] = {
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
    with open(os.path.join(ART, "oracle_coverage_o0a2.json"), "w") as f:
        json.dump(out, f, indent=1)
    for rule in ("v0", "v1", "licensed"):
        for key in ("we_not_allowed", "we_allowed"):
            o = out["rules"][rule][key]
            print("%s %s: ACD %d/%d = %.1f%%; nosave-writable %d/%d; "
                  "reasons %s" % (
                      rule, key, o["acd_writable"], o["acd_total"],
                      o["acd_pct"], o["nosave_writable"], o["nosave_total"],
                      json.dumps(o["nonwritable_by_reason"], sort_keys=True)))


if __name__ == "__main__":
    main()
