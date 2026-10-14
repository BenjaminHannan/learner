"""Independent reader for the LT-1 logic prompts (does NOT import logicgen).

parse_prompt(text) -> Parsed(facts, rules, query, ids, ok, err)
  literal   = (neg:bool, pred:str, ent:str)
  rule      = (lhs: tuple[(neg,pred)], rhs: (neg,pred), ent: str|None)   ent None = universal
  ids       = template ids "<kind>:<idx>" inferred from the TEXT, in sentence order (last = question)

Semantics engines:
  fwd(...)        documented semantics: forward chaining on literals, no modus tollens, no closed world
  min_depth(...)  exact minimum proof size (fewest distinct derived atoms) and minimum proof height (rounds)
  classical(...)  textbook entailment (DPLL over per-entity propositional atoms, ~ = classical negation):
                  contrapositives, case splits and inconsistency all count
"""
import re
from itertools import combinations

E = r"(?P<e>[A-Z][a-z]+)"
P = r"(?P<p>[a-z]+)"
Q_ = r"(?P<q>[a-z]+)"
C = r"(?P<c>(?:not )?[a-z]+)"          # possibly negated conclusion phrase
A_ = r"(?P<a>(?:not )?[a-z]+)"
B_ = r"(?P<b>(?:not )?[a-z]+)"
N = r"(?P<n>not )?"

# ----- sentence inventory, written from reading the rendered corpus + template file ---------------------------------
_R1 = ["Every {P} is {Q}.", "All {P} are {Q}.", "Any {P} is {Q}.", "{P} things are {Q}.", "Each {P} is {Q}.",
       "If it is {P}, it is {Q}.", "What is {P} is {Q}.", "Those {P} are {Q}.", "A {P} thing is {Q}.",
       "Anything {P} is {Q}.", "Being {P} means {Q}.", "All {P} ones are {Q}.", "If {P} then {Q}.",
       "Every {P} thing is {Q}."]
_R2 = ["No {P} is {Q}.", "No {P} thing is {Q}.", "None {P} is {Q}.", "{P} things are never {Q}.",
       "Any {P} is not {Q}.", "Each {P} is not {Q}.", "All {P} are not {Q}.", "If it is {P}, it is not {Q}.",
       "What is {P} is not {Q}.", "Those {P} are not {Q}.", "A {P} thing is not {Q}.", "Nothing {P} is {Q}.",
       "If {P} then not {Q}.", "Every {P} is not {Q}."]
_R3 = ["{P} and {Q} things are {C}.", "Any {P} and {Q} is {C}.", "All {P} and {Q} are {C}.",
       "If {P} and {Q}, then {C}.", "If it is {P} and {Q}, it is {C}.", "Each {P}, {Q} one is {C}.",
       "What is {P} and {Q} is {C}.", "Every {P} and {Q} is {C}.", "A {P} {Q} thing is {C}.",
       "Those {P} and {Q} are {C}.", "{P} plus {Q} gives {C}.", "Being {P} and {Q} means {C}.",
       "Anything {P} and {Q} is {C}.", "Both {P} and {Q} means {C}."]
_R4 = ["Any non-{P} is {Q}.", "Not {P} things are {Q}.", "If not {P}, then {Q}.", "If it is not {P}, it is {Q}.",
       "What is not {P} is {Q}.", "Every non-{P} is {Q}.", "All non-{P} are {Q}.", "Each non-{P} is {Q}.",
       "Those not {P} are {Q}.", "Anything not {P} is {Q}.", "Not {P} means {Q}.", "A non-{P} thing is {Q}.",
       "Non-{P} things are {Q}.", "If not {P} then {Q}."]
_R5 = ["If {E} is {A}, {E} is {B}.", "{E} is {B} if {E} is {A}.", "When {E} is {A}, {E} is {B}.",
       "If {E} is {A}, then {B}.", "Should {E} be {A}, {E} is {B}.", "{E} is {B} when {E} is {A}.",
       "Whenever {E} is {A}, {E} is {B}.", "If {E} is {A}, {E} must be {B}.", "Given {E} is {A}, {E} is {B}.",
       "{E} being {A} makes {E} {B}.", "Once {E} is {A}, {E} is {B}.", "If {E} is {A}, {E} is then {B}.",
       "Provided {E} is {A}, {E} is {B}.", "If {E} is {A}, {E} is {B} too."]
_FP = ["{E} is {P}.", "{E} is {P}, yes.", "We know {E} is {P}.", "Note: {E} is {P}.", "{E} is surely {P}.",
       "{E} was {P}.", "{E} is quite {P}.", "Fact: {E} is {P}.", "{E} is truly {P}.", "It is true {E} is {P}."]
_FN = ["{E} is not {P}.", "{E} isn't {P}.", "We know {E} is not {P}.", "Note: {E} is not {P}.",
       "{E} is surely not {P}.", "{E} was not {P}.", "{E} is never {P}.", "Fact: {E} is not {P}.",
       "{E} is truly not {P}.", "It is true {E} is not {P}."]
_QS = ["Is {E} {N}{P}?", "Can we tell {E} is {N}{P}?", "True or false or unknown: {E} is {N}{P}.",
       "Does it follow that {E} is {N}{P}?", "Is it true that {E} is {N}{P}?", "Then is {E} {N}{P}?",
       "Claim: {E} is {N}{P}.", "Is {E} {N}{P}, then?", "So, is {E} {N}{P}?", "Check: {E} is {N}{P}.",
       "{E} is {N}{P}: true, false or unknown?", "Decide: {E} is {N}{P}."]

_SUBS = {"{P}": P, "{Q}": Q_, "{C}": C, "{A}": A_, "{B}": B_, "{N}": N}


def _compile(tpl, ent_group_count=1):
    s = re.escape(tpl)
    if tpl.startswith("{P}"):          # sentence-initial predicate word is capitalised by the renderer
        s = s.replace(re.escape("{P}"), r"(?P<p>[A-Z][a-z]+)", 1)
    # escaped placeholders look like \{P\}
    first = True
    for k in ("E",):
        while "\\{E\\}" in s:
            s = s.replace("\\{E\\}", E if first else r"(?P=e)", 1)
            first = False
    for k, v in _SUBS.items():
        s = s.replace(re.escape(k), v)
    return re.compile("^" + s + "$")


SENT = []   # (kind, idx, regex)
for kind, lst in (("R1", _R1), ("R2", _R2), ("R3", _R3), ("R4", _R4), ("R5", _R5), ("FP", _FP), ("FN", _FN)):
    for i, t in enumerate(lst):
        SENT.append((kind, i, _compile(t)))
QSENT = [("Q", i, _compile(t)) for i, t in enumerate(_QS)]

_SUFFIX = re.compile(r" \((true|false|unknown)/(true|false|unknown)/(true|false|unknown)\)$")


def split_options(prompt):
    m = _SUFFIX.search(prompt)
    if not m:
        return prompt, None
    ws = m.groups()
    return prompt[:m.start()], ws if len(set(ws)) == 3 else None


def sentences(body):
    return re.split(r"(?<=[.?])\s+", body.strip())


def _phrase(s):
    s = s.strip()
    return (True, s[4:]) if s.startswith("not ") else (False, s)


class Parsed:
    __slots__ = ("facts", "rules", "query", "ids", "ok", "err", "nsent", "rule_ids")

    def __init__(self):
        self.facts, self.rules, self.query, self.ids, self.ok, self.err, self.nsent, self.rule_ids = [], [], None, [], False, None, 0, []


def parse_prompt(text):
    body, opts = split_options(text)
    out = Parsed()
    if opts is None:
        out.err = "no_options_suffix"
        return out
    ss = sentences(body)
    out.nsent = len(ss)
    for si, s in enumerate(ss):
        last = si == len(ss) - 1
        if last:
            hit = None
            for kind, i, rx in QSENT:
                m = rx.match(s)
                if m:
                    hit = (kind, i, m)
                    break
            if not hit:
                out.err = f"unparsed_query:{s}"
                return out
            kind, i, m = hit
            out.query = (bool(m.group("n")), m.group("p"), m.group("e").lower())
            out.ids.append(f"Q:{i}")
            continue
        hits = []
        for kind, i, rx in SENT:
            m = rx.match(s)
            if m:
                hits.append((kind, i, m))
        if not hits:
            out.err = f"unparsed_sentence:{s}"
            return out
        # an ambiguous sentence (two templates, different logic) is reported, not silently resolved
        kind, i, m = hits[0]
        g = m.groupdict()
        if kind == "FP":
            lit = (False, g["p"].lower(), g["e"].lower())
            out.facts.append(lit)
        elif kind == "FN":
            lit = (True, g["p"].lower(), g["e"].lower())
            out.facts.append(lit)
        elif kind == "R1":
            out.rules.append((((False, g["p"].lower()),), (False, g["q"]), None))
        elif kind == "R2":
            out.rules.append((((False, g["p"].lower()),), (True, g["q"]), None))
        elif kind == "R3":
            out.rules.append((((False, g["p"].lower()), (False, g["q"])), _phrase(g["c"]), None))
        elif kind == "R4":
            out.rules.append((((True, g["p"].lower()),), (False, g["q"]), None))
        elif kind == "R5":
            out.rules.append(((_phrase(g["a"]),), _phrase(g["b"]), g["e"].lower()))
        out.ids.append(f"{kind}:{i}")
        if kind.startswith("R"):
            out.rule_ids.append(f"{kind}:{i}")
        if len(hits) > 1:
            sigs = set()
            for k2, i2, m2 in hits:
                sigs.add((k2, tuple(sorted(m2.groupdict().items()))))
            if len(sigs) > 1:
                out.err = f"ambiguous_sentence:{s}"
                return out
    out.ok = True
    return out


# ------------------------------------------------------------------ semantics ---------------------------------------
def neg(l):
    return (not l[0], l[1], l[2])


def entities(facts, rules, query):
    es = {f[2] for f in facts} | {r[2] for r in rules if r[2]}
    if query:
        es.add(query[2])
    return sorted(es)


def ground(facts, rules, query):
    es = entities(facts, rules, query)
    gr = []
    for lhs, rhs, ent in rules:
        for e in ([ent] if ent else es):
            gr.append((tuple((n, p, e) for n, p in lhs), (rhs[0], rhs[1], e)))
    return gr


def closure_rounds(facts, grules):
    """-> (dict literal->round first derived (0 = given), list of derived in order)."""
    rd = {f: 0 for f in facts}
    r = 0
    while True:
        r += 1
        new = {}
        for prem, concl in grules:
            if concl not in rd and concl not in new and all(p in rd for p in prem):
                new[concl] = r
        if not new:
            break
        rd.update(new)
    return rd


def fwd(facts, rules, query):
    """documented semantics -> (label, contradiction:bool, closure round map)."""
    gr = ground(facts, rules, query)
    rd = closure_rounds(facts, gr)
    contra = any((not l[0]) and (True, l[1], l[2]) in rd for l in rd)
    if query in rd:
        lab = "true"
    elif neg(query) in rd:
        lab = "false"
    else:
        lab = "unknown"
    return lab, contra, rd, gr


def min_depth(facts, rules, query):
    """Exact minimum proof size = fewest distinct derived atoms needed (try all subsets of the derivable atoms, smallest
    first), and minimum proof height = round of first derivation. For label unknown: (None, None)."""
    lab, contra, rd, gr = fwd(facts, rules, query)
    if lab == "unknown":
        return lab, None, None
    tgt = query if lab == "true" else neg(query)
    height = rd[tgt]
    if height == 0:
        return lab, 0, 0
    derived = sorted(l for l in rd if rd[l] > 0)
    if len(derived) > 18:
        return lab, None, height          # too many to enumerate; caller counts these
    fs = set(facts)
    byc = {}
    for prem, concl in gr:
        byc.setdefault(concl, []).append(prem)
    for k in range(1, len(derived) + 1):
        for sub in combinations(derived, k):
            if tgt not in sub:
                continue
            allowed = fs | set(sub)
            got = set(fs)
            ch = True
            while ch:
                ch = False
                for l in sub:
                    if l not in got and any(all(p in got for p in prem) for prem in byc.get(l, ())):
                        got.add(l)
                        ch = True
            if tgt in got:
                return lab, k, height
    return lab, None, height


def _dpll(clauses, assign):
    # clauses: list of frozenset of (var, sign); assign: dict var->bool
    while True:
        unit = None
        newc = []
        for c in clauses:
            sat = False
            rest = []
            for v, s in c:
                if v in assign:
                    if assign[v] == s:
                        sat = True
                        break
                else:
                    rest.append((v, s))
            if sat:
                continue
            if not rest:
                return False
            if len(rest) == 1 and unit is None:
                unit = rest[0]
            newc.append(rest)
        clauses = newc
        if unit is None:
            break
        assign = dict(assign)
        assign[unit[0]] = unit[1]
    if not clauses:
        return True
    v = clauses[0][0][0]
    for val in (True, False):
        a = dict(assign)
        a[v] = val
        if _dpll(clauses, a):
            return True
    return False


def classical(facts, rules, query):
    """Textbook entailment. -> 'inconsistent' | 'true' | 'false' | 'unknown'."""
    gr = ground(facts, rules, query)
    cl = []
    lit = lambda l: ((l[1], l[2]), not l[0])        # (var, sign): ~p(e) is the classical negation of p(e)
    for f in facts:
        cl.append([lit(f)])
    for prem, concl in gr:
        cl.append([(lit(p)[0], not lit(p)[1]) for p in prem] + [lit(concl)])
    sat = lambda extra: _dpll([c for c in cl] + [[x] for x in extra], {})
    if not sat([]):
        return "inconsistent"
    qv, qs = lit(query)
    if not sat([(qv, not qs)]):
        return "true"
    if not sat([(qv, qs)]):
        return "false"
    return "unknown"


# ------------------------------------------------------------------ program-string (generator's own text form) -------
def read_program(prog):
    """Tiny independent reader of the stored 'program' string -> (facts set, rules set, query)."""
    facts, rules, query = set(), set(), None
    for item in prog.split(";"):
        item = item.strip().replace(" ", "")
        if not item:
            continue
        tag, body = item[0], item[1:]
        if tag == "F":
            m = re.fullmatch(r"(~?)(\w+)\((\w+)\)", body)
            facts.add((m.group(1) == "~", m.group(2), m.group(3)))
        elif tag == "Q":
            m = re.fullmatch(r"(~?)(\w+)\((\w+)\)", body)
            query = (m.group(1) == "~", m.group(2), m.group(3))
        else:
            ent = None
            if ":" in body:
                ent, body = body.split(":", 1)
            lhs, rhs = body.split(">")
            if ent:
                lh = [(lhs.startswith("~"), lhs.lstrip("~"))]
                rh = (rhs.startswith("~"), rhs.lstrip("~"))
            else:
                lh = []
                for t in lhs.split("&"):
                    m = re.fullmatch(r"(~?)(\w+)\(x\)", t)
                    lh.append((m.group(1) == "~", m.group(2)))
                m = re.fullmatch(r"(~?)(\w+)\(x\)", rhs)
                rh = (m.group(1) == "~", m.group(2))
            rules.add((tuple(sorted(lh)), rh, ent))
    return facts, rules, query


def norm_rules(rules):
    return {(tuple(sorted(l)), r, e) for l, r, e in rules}


# ------------------------------------------------------------------ alternative readings ----------------------------
def contrapositive_rules(rules):
    """rules + their contrapositives (modus tollens made available to forward chaining)."""
    out = list(rules)
    for lhs, rhs, ent in rules:
        nr = (not rhs[0], rhs[1])
        for j in range(len(lhs)):
            others = tuple(x for k, x in enumerate(lhs) if k != j)
            out.append(((nr,) + others, (not lhs[j][0], lhs[j][1]), ent))
    return out


def distribute(rules, rule_ids, dist_ids):
    """Read the listed R3 templates as 'p -> c' and 'q -> c' (distributive 'All p and q are c')."""
    out = []
    for r, rid in zip(rules, rule_ids):
        if rid in dist_ids:
            out.append(((r[0][0],), r[1], r[2]))
            out.append(((r[0][1],), r[1], r[2]))
        else:
            out.append(r)
    return out


def drop_rules(rules, rule_ids, drop_ids):
    return [r for r, rid in zip(rules, rule_ids) if rid not in drop_ids]
