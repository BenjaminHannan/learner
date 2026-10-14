"""English templates. Each kind's list is split deterministically: index % 3 == 2 -> HELDOUT (1/3),
otherwise TRAIN (2/3). Template id = "<kind>:<index>".

Slots: {p} {q} predicate words, {c}/{a}/{b} literal phrases ("big" or "not big"), {e} capitalised entity,
{n} "not " or "" (questions)."""

TEMPLATES = {
    # R1: every P is Q
    "R1": ["Every {p} is {q}.", "All {p} are {q}.", "Any {p} is {q}.", "{p} things are {q}.",
           "Each {p} is {q}.", "If it is {p}, it is {q}.", "What is {p} is {q}.", "Those {p} are {q}.",
           "A {p} thing is {q}.", "Anything {p} is {q}.", "Being {p} means {q}.", "All {p} ones are {q}.",
           "If {p} then {q}.", "Every {p} thing is {q}."],
    # R2: no P is Q
    "R2": ["No {p} is {q}.", "No {p} thing is {q}.", "None {p} is {q}.", "{p} things are never {q}.",
           "Any {p} is not {q}.", "Each {p} is not {q}.", "All {p} are not {q}.",
           "If it is {p}, it is not {q}.", "What is {p} is not {q}.", "Those {p} are not {q}.",
           "A {p} thing is not {q}.", "Nothing {p} is {q}.", "If {p} then not {q}.", "Every {p} is not {q}."],
    # R3: conjunction; {c} is the conclusion phrase (possibly negated)
    "R3": ["{p} and {q} things are {c}.", "Any {p} and {q} is {c}.", "All {p} and {q} are {c}.",
           "If {p} and {q}, then {c}.", "If it is {p} and {q}, it is {c}.", "Each {p}, {q} one is {c}.",
           "What is {p} and {q} is {c}.", "Every {p} and {q} is {c}.", "A {p} {q} thing is {c}.",
           "Those {p} and {q} are {c}.", "{p} plus {q} gives {c}.", "Being {p} and {q} means {c}.",
           "Anything {p} and {q} is {c}.", "Both {p} and {q} means {c}."],
    # R4: negated premise
    "R4": ["Any non-{p} is {q}.", "Not {p} things are {q}.", "If not {p}, then {q}.",
           "If it is not {p}, it is {q}.", "What is not {p} is {q}.", "Every non-{p} is {q}.",
           "All non-{p} are {q}.", "Each non-{p} is {q}.", "Those not {p} are {q}.",
           "Anything not {p} is {q}.", "Not {p} means {q}.", "A non-{p} thing is {q}.",
           "Non-{p} things are {q}.", "If not {p} then {q}."],
    # R5: entity-specific; {a} premise phrase, {b} conclusion phrase
    "R5": ["If {e} is {a}, {e} is {b}.", "{e} is {b} if {e} is {a}.", "When {e} is {a}, {e} is {b}.",
           "If {e} is {a}, then {b}.", "Should {e} be {a}, {e} is {b}.", "{e} is {b} when {e} is {a}.",
           "Whenever {e} is {a}, {e} is {b}.", "If {e} is {a}, {e} must be {b}.",
           "Given {e} is {a}, {e} is {b}.", "{e} being {a} makes {e} {b}.", "Once {e} is {a}, {e} is {b}.",
           "If {e} is {a}, {e} is then {b}.", "Provided {e} is {a}, {e} is {b}.", "If {e} is {a}, {e} is {b} too."],
    "FP": ["{e} is {p}.", "{e} is {p}, yes.", "We know {e} is {p}.", "Note: {e} is {p}.",
           "{e} is surely {p}.", "{e} was {p}.", "{e} is quite {p}.", "Fact: {e} is {p}.",
           "{e} is truly {p}.", "It is true {e} is {p}."],
    "FN": ["{e} is not {p}.", "{e} isn't {p}.", "We know {e} is not {p}.", "Note: {e} is not {p}.",
           "{e} is surely not {p}.", "{e} was not {p}.", "{e} is never {p}.", "Fact: {e} is not {p}.",
           "{e} is truly not {p}.", "It is true {e} is not {p}."],
    "Q": ["Is {e} {n}{p}?", "Can we tell {e} is {n}{p}?", "True or false or unknown: {e} is {n}{p}.",
          "Does it follow that {e} is {n}{p}?", "Is it true that {e} is {n}{p}?", "Then is {e} {n}{p}?",
          "Claim: {e} is {n}{p}.", "Is {e} {n}{p}, then?", "So, is {e} {n}{p}?", "Check: {e} is {n}{p}.",
          "{e} is {n}{p}: true, false or unknown?", "Decide: {e} is {n}{p}."],
}


def heldout_ids(kind):
    return [i for i in range(len(TEMPLATES[kind])) if i % 3 == 2]


def train_ids(kind):
    return [i for i in range(len(TEMPLATES[kind])) if i % 3 != 2]


def pick(rng, kind, tset):
    """Random template of `kind` from the 'train' or 'heldout' set -> (id string, template text)."""
    i = rng.choice(train_ids(kind) if tset == "train" else heldout_ids(kind))
    return f"{kind}:{i}", TEMPLATES[kind][i]


def phrase(neg, pred):
    return ("not " if neg else "") + pred


def rule_kind(r):
    """R1..R5 by shape; ValueError for shapes without a template (never generated)."""
    if r.ent:
        return "R5"
    if len(r.lhs) == 2:
        if r.lhs[0][0] or r.lhs[1][0]:
            raise ValueError("negated conjunct not renderable")
        return "R3"
    (ln, _), (rn, _) = r.lhs[0], r.rhs
    if not ln and not rn:
        return "R1"
    if not ln and rn:
        return "R2"
    if ln and not rn:
        return "R4"
    raise ValueError("rule not renderable")


def cap(s):
    return s[:1].upper() + s[1:]


def render_rule(rng, r, tset):
    kind = rule_kind(r)
    tid, t = pick(rng, kind, tset)
    if kind == "R5":
        s = t.format(e=cap(r.ent), a=phrase(*r.lhs[0]), b=phrase(*r.rhs))
    elif kind == "R3":
        s = t.format(p=r.lhs[0][1], q=r.lhs[1][1], c=phrase(*r.rhs))
    else:
        s = t.format(p=r.lhs[0][1], q=r.rhs[1])
    return tid, cap(s)


def render_fact(rng, lit, tset):
    tid, t = pick(rng, "FN" if lit[0] else "FP", tset)
    return tid, cap(t.format(e=cap(lit[2]), p=lit[1]))


def render_question(rng, lit, tset, kind="Q"):
    tid, t = pick(rng, kind, tset)
    return tid, cap(t.format(e=cap(lit[2]), p=lit[1], n="not " if lit[0] else ""))


def atom_sentence(lit):
    return f"{cap(lit[2])} is {phrase(lit[0], lit[1])}."
