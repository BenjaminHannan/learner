"""Forward-chaining checker and the outside "logic tool".

SEMANTICS (kept deliberately simple so labels are well defined)
  * Atoms are literals: pred(ent) or ~pred(ent). Rules are Horn-like: conjunction of literals -> literal.
  * Forward chaining only. Contrapositive reasoning (modus tollens) is NOT part of the semantics:
    from "P -> Q" and "not Q" nothing follows about P.
  * No closed-world assumption: an atom that is neither given nor derived is unknown.
  * Label of query literal L: TRUE if L is derivable, FALSE if the complement of L is derivable,
    UNKNOWN otherwise. A knowledge base that derives both p(e) and ~p(e) is a contradiction;
    run_program reports "error" for it (the generator never emits such problems).
  * Proof / depth: the shortest proof is the smallest set of derived atoms (one rule application each)
    needed for the target, found by iterated relaxation over union-of-premise-proofs (exact on
    tree-shaped proofs, which is all the generator makes). depth = its size; 0 if L is a given fact.

PROGRAM GRAMMAR (items separated by ";", spaces ignored, identifiers [a-z][a-z0-9_]*)
  F <lit>            fact,               e.g.  F wumpus(max)   F ~big(sam)
  R <xlit>[&<xlit>]>(<xlit>)             universal rule over variable x,
                                         e.g.  R wumpus(x)>tarvle(x)   R tarvle(x)&cold(x)>~big(x)   R ~red(x)>cold(x)
  R <ent>: <plit> > <plit>               entity-specific rule, plit = [~]pred,   e.g.  R max: wumpus>~cold
  Q <lit>            the query (exactly one required)
"""
import re
from typing import NamedTuple

_ID = r"[a-z][a-z0-9_]*"
_LIT = re.compile(rf"^(~?)({_ID})\(({_ID})\)$")
_XLIT = re.compile(rf"^(~?)({_ID})\(x\)$")
_PLIT = re.compile(rf"^(~?)({_ID})$")


class ParseError(ValueError):
    pass


class Rule(NamedTuple):
    lhs: tuple          # tuple of (neg, pred)
    rhs: tuple          # (neg, pred)
    ent: object = None  # entity name for entity-specific rules, else None (universal)


class Result(NamedTuple):
    label: object       # "true" | "false" | "unknown" (None when no query)
    depth: object       # int, or None for unknown
    proof: tuple        # derived literals of the shortest proof, in order (empty at depth 0)
    target: object      # the literal that was proved (query or its complement), else None
    contradictions: tuple
    closure: frozenset
    used_rules: frozenset
    used_facts: frozenset


def neg_lit(l):
    return (not l[0], l[1], l[2])


def fmt_lit(l):
    return ("~" if l[0] else "") + f"{l[1]}({l[2]})"


def _pl(p):
    return ("~" if p[0] else "") + p[1]


def fmt_rule(r):
    if r.ent:
        return f"R {r.ent}: {_pl(r.lhs[0])}>{_pl(r.rhs)}"
    return "R " + "&".join(_pl(p) + "(x)" for p in r.lhs) + ">" + _pl(r.rhs) + "(x)"


def parse_lit(s):
    m = _LIT.match(s.replace(" ", ""))
    if not m:
        raise ParseError(f"bad literal {s!r}")
    return (m.group(1) == "~", m.group(2), m.group(3))


def parse_program(prog, need_query=True):
    """Return (facts, rules, query). Raises ParseError on any deviation from the grammar."""
    facts, rules, query = [], [], None
    for item in prog.split(";"):
        item = item.strip()
        if not item:
            continue
        tag, body = item[:1], item[1:]
        if tag not in "FRQ" or not body[:1].isspace():
            raise ParseError(f"bad item {item!r}")
        body = body.replace(" ", "")
        if tag == "F":
            facts.append(parse_lit(body))
        elif tag == "Q":
            if query is not None:
                raise ParseError("two queries")
            query = parse_lit(body)
        else:
            ent = None
            if ":" in body:
                ent, body = body.split(":", 1)
                if not re.fullmatch(_ID, ent):
                    raise ParseError(f"bad entity {ent!r}")
            if body.count(">") != 1:
                raise ParseError(f"bad rule {item!r}")
            l, r = body.split(">")
            if ent:
                ms = [_PLIT.match(l)]
                mr = _PLIT.match(r)
            else:
                ms = [_XLIT.match(t) for t in l.split("&")]
                mr = _XLIT.match(r)
            if not all(ms) or not mr:
                raise ParseError(f"bad rule {item!r}")
            rules.append(Rule(tuple((m.group(1) == "~", m.group(2)) for m in ms),
                              (mr.group(1) == "~", mr.group(2)), ent))
    if need_query and query is None:
        raise ParseError("no query")
    return facts, rules, query


def solve(facts, rules, query=None):
    facts = list(dict.fromkeys(facts))
    ents = {f[2] for f in facts} | {r.ent for r in rules if r.ent} | ({query[2]} if query else set())
    ground = []  # (premise literals, conclusion literal, rule index)
    for ri, r in enumerate(rules):
        for e in ([r.ent] if r.ent else sorted(ents)):
            ground.append((tuple((n, p, e) for n, p in r.lhs), (r.rhs[0], r.rhs[1], e), ri))
    best = {f: () for f in facts}  # literal -> ordered tuple of (derived literal, rule index)
    changed = True
    while changed:
        changed = False
        for prem, concl, ri in ground:
            if concl in best and not best[concl]:
                continue  # given fact: cost 0
            if not all(p in best for p in prem):
                continue
            merged = []
            for p in prem:
                for st in best[p]:
                    if st not in merged:
                        merged.append(st)
            if any(s[0] == concl for s in merged):
                continue
            cand = tuple(merged) + ((concl, ri),)
            if concl not in best or len(cand) < len(best[concl]):
                best[concl] = cand
                changed = True
    closure = frozenset(best)
    contra = tuple(sorted((p, e) for (n, p, e) in closure if not n and (True, p, e) in closure))
    label = depth = target = None
    steps = ()
    if query is not None:
        if query in best:
            label, target = "true", query
        elif neg_lit(query) in best:
            label, target = "false", neg_lit(query)
        else:
            label = "unknown"
        if target is not None:
            steps = best[target]
            depth = len(steps)
    used_r, used_f = set(), set()
    for lit, ri in steps:
        used_r.add(ri)
        for n, p in rules[ri].lhs:
            if (n, p, lit[2]) in facts:
                used_f.add((n, p, lit[2]))
    if target is not None and depth == 0:
        used_f.add(target)
    return Result(label, depth, tuple(s[0] for s in steps), target, contra, closure,
                  frozenset(used_r), frozenset(used_f))


def run_program(program_str):
    """The outside logic tool: 'true' | 'false' | 'unknown' | 'error' (parse error or contradiction)."""
    try:
        facts, rules, query = parse_program(program_str)
        res = solve(facts, rules, query)
    except Exception:
        return "error"
    return "error" if res.contradictions else res.label
