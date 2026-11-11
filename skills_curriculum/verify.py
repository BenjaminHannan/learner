"""Independent checks. Nothing here calls a family's generator function.

1. slots: every fact the answer was built from really appears in the prompt text.
2. steps: every 'a op b = c' line in the worked steps is arithmetically true, and a final step that ends in the answer agrees with it.
3. parse re-solve: for the families in PARSERS the answer is recomputed from the PROMPT TEXT alone (layout undone first).
4. length: estimated tokens within the cap.
Family coverage of check 3 is reported, not assumed.
"""
import re
from .core import FAMILIES, undo_layout, MAX_TOKENS_EST

ORD = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"]


def _nums(s):
    return [int(x) for x in re.findall(r"-?\d+", s)]


def p_copy_word(p):
    for pat in (r"Repeat the word: (\w+)$", r"Say this word back: (\w+)$", r"Write the word (\w+) once more\.$", r"Echo: (\w+)$",
                r"Copy this: (\w+)$", r"Copy exactly what follows the colon\. (\w+)$", r"Repeat (\w+)\.$", r"; say (\w+)\.$", r"give back (\w+)\.$"):
        m = re.search(pat, p)
        if m:
            return m[1]


def p_list_index(p):
    m = re.match(r"(?:Items: |The list is |Here are some words: )(.*?)\. (.*)$", p)
    ws = m[1].split(", ")
    q = m[2]
    for i, o in enumerate(ORD):
        if q == f"What is the {o} item?":
            return ws[i]
    if q == "What is the last item?":
        return ws[-1]
    m2 = re.match(r"Which word comes right after (\w+)\?", q)
    if m2:
        return ws[ws.index(m2[1]) + 1]
    m2 = re.match(r"Which word comes right before (\w+)\?", q)
    if m2:
        return ws[ws.index(m2[1]) - 1]
    m2 = re.match(r"At which position is (\w+)\?", q)
    if m2:
        return ws.index(m2[1]) + 1


def p_letter_ops(p):
    m = re.match(r"How many times does the letter (\w) appear in (\w+)\?", p)
    if m:
        return m[2].count(m[1])
    m = re.match(r"How many letters are in the word (\w+)\?", p)
    if m:
        return len(m[1])
    m = re.match(r"What is the first letter of (\w+)\?", p)
    if m:
        return m[1][0]
    m = re.match(r"What is the last letter of (\w+)\?", p)
    if m:
        return m[1][-1]
    m = re.match(r"What is letter number (\d+) of (\w+)\?", p)
    if m:
        return m[2][int(m[1]) - 1]


def p_arith_bare(p):
    m = re.search(r"(\d+) ([+\-*]) \? = (\d+)", p)
    if m:
        x, o, r = int(m[1]), m[2], int(m[3])
        return {"+": r - x, "-": x - r, "*": r // x}[o]
    m = re.search(r"(\d+) (plus|minus|times|[+\-*]) (\d+)", p)
    if m:
        x, o, y = int(m[1]), m[2], int(m[3])
        return {"+": x + y, "plus": x + y, "-": x - y, "minus": x - y, "*": x * y, "times": x * y}[o]
    m = re.search(r"Take (\d+) away from (\d+)", p) or re.search(r"Subtract (\d+) from (\d+)", p)
    if m:
        return abs(int(m[2]) - int(m[1]))


def p_div_exact(p):
    m = re.match(r"(\d+) / (\d+) = \?", p)
    if m:
        return int(m[1]) // int(m[2])
    ns = _nums(p)
    return max(ns) // min(ns) if len(ns) == 2 else None


def p_compare_numbers(p):
    m = re.match(r"(?:Which is|Between) (?:(larger|smaller), (\d+) or (\d+)\?|(\d+) and (\d+), which number is (larger|smaller)\?)", p)
    if m:
        a, b, w = (int(m[2]), int(m[3]), m[1]) if m[1] else (int(m[4]), int(m[5]), m[6])
        return max(a, b) if w == "larger" else min(a, b)
    m = re.match(r"Numbers: ([\d, ]+)\. (.*)", p)
    xs = [int(t) for t in m[1].split(",")]
    q = m[2]
    if "largest" in q:
        return max(xs)
    if "smallest" in q:
        return min(xs)
    t = int(re.search(r"greater than (\d+)", q)[1])
    return sum(1 for z in xs if z > t)


def p_list_stats(p):
    m = re.match(r"Numbers: ([\d, ]+)\. (.*)", p)
    xs = [int(t) for t in m[1].split(",")]
    q = m[2]
    if "sum" in q:
        return sum(xs)
    if "minus" in q:
        return max(xs) - min(xs)
    if "even" in q:
        return sum(1 for z in xs if z % 2 == 0)
    if "second largest" in q:
        return sorted(xs)[-2]


def p_digits_parity(p):
    m = re.match(r"Is (\d+) odd or even\?", p)
    if m:
        return "even" if int(m[1]) % 2 == 0 else "odd"
    m = re.match(r"What is the sum of the digits of (\d+)\?", p)
    if m:
        return sum(int(d) for d in m[1])
    m = re.match(r"What is the tens digit of (\d+)\?", p)
    if m:
        return int(m[1][-2])
    m = re.match(r"How many digits does (\d+) have\?", p)
    if m:
        return len(m[1])


def p_var_chain(p):
    m = re.match(r"(.*?) What is (.*)\?$", p)
    env = {}
    for stmt in re.findall(r"([a-z]) = ([^.]+)\.", m[1]):
        env[stmt[0]] = eval(re.sub(r"\b([a-z])\b", lambda mm: str(env[mm[1]]), stmt[1]))
    return eval(re.sub(r"\b([a-z])\b", lambda mm: str(env[mm[1]]), m[2]))


def p_prop_eval(p):
    m = re.match(r"(.*?) Is this statement true or false: (.*)\?$", p)
    val = {k: v == "true" for k, v in re.findall(r"([PQRS]) is (true|false)\.", m[1])}
    e = m[2]
    mm = re.match(r"if (\w) then (\w)$", e)
    if mm:
        return "true" if (not val[mm[1]]) or val[mm[2]] else "false"
    for k, v in val.items():
        e = re.sub(rf"\b{k}\b", str(v), e)
    return "true" if eval(e) else "false"


def p_cipher_map(p):
    m = re.match(r"Code: (.*?)\. (.*)$", p)
    tab = dict(t.split("=") for t in m[1].split(", "))
    q = m[2]
    mm = re.match(r"Write (\w+) as numbers\.", q)
    if mm:
        return " ".join(tab[ch] for ch in mm[1])
    mm = re.match(r"Decode the numbers ([\d ]+) into letters\.", q)
    inv = {v: k for k, v in tab.items()}
    return "".join(inv[x] for x in mm[1].split())


def p_word_filter(p):
    m = re.match(r"Words: (.*?)\. (.*)$", p)
    ws = m[1].split(", ")
    q = m[2]
    mm = re.match(r"How many words start with the letter (\w)\?", q)
    if mm:
        return sum(1 for w in ws if w[0] == mm[1])
    mm = re.match(r"How many words have more than (\d+) letters\?", q)
    if mm:
        return sum(1 for w in ws if len(w) > int(mm[1]))
    mm = re.match(r"How many words contain the letter (\w)\?", q)
    return sum(1 for w in ws if mm[1] in w)


def p_verify_claim(p):
    m = re.match(r"Is this correct: (\d+) ([+\-*]) (\d+) = (\d+)\?", p)
    if m:
        x, o, y, z = int(m[1]), m[2], int(m[3]), int(m[4])
        return "yes" if {"+": x + y, "-": x - y, "*": x * y}[o] == z else "no"
    m = re.match(r"Is this list in increasing order: ([\d, ]+)\?", p)
    xs = [int(t) for t in m[1].split(",")]
    return "yes" if xs == sorted(xs) else "no"


def p_table_lookup(p):
    m = re.match(r"Table - (.*?)\. (.*)$", p)
    tab = {k: int(v) for k, v in (e.split(": ") for e in m[1].split("; "))}
    q = m[2]
    mm = re.match(r"What is the number for (\w+)\?", q)
    if mm:
        return tab[mm[1]]
    mm = re.match(r"What is (\w+) plus (\w+)\?", q)
    if mm:
        return tab[mm[1]] + tab[mm[2]]
    if q.startswith("Which word has the largest"):
        return max(tab, key=tab.get)
    mm = re.match(r"How much bigger is the larger of (\w+) and (\w+) than the smaller\?", q)
    return abs(tab[mm[1]] - tab[mm[2]])


def p_unit_convert(p):
    ns = _nums(p)
    if "equals" in p and p.count("equals") == 2:
        f1, f2, n = ns[1], ns[3], ns[-1]
        return n * f1 * f2
    m = re.match(r"1 (\w+) equals (\d+) (\w+)\. How many (\w+) are in (\d+) (\w+)\?", p)
    u1, f, u2, ask, n, have = m.groups()
    return int(n) * int(f) if have == u1 else int(n) // int(f)


def p_seq_cycle(p):
    m = re.match(r"The pattern (.*?) repeats forever\. What is item number (\d+)\?", p)
    if m:
        pat = m[1].split()
        return pat[(int(m[2]) - 1) % len(pat)]
    m = re.match(r"(.*?) \? What comes next\?", p)
    shown = m[1].split()
    for L in range(1, len(shown)):
        if all(shown[i] == shown[i % L] for i in range(len(shown))):
            return shown[len(shown) % L]


def p_syllogism(p):
    if p.startswith("No "):
        return "no"
    sents = re.findall(r"All (\w+?)s are (\w+?)s\.", p)
    m = re.search(r"(\w+) is a (\w+)\. Is \1 a (\w+)\?$", p)
    start, goal = m[2], m[3]
    reach, ch = {start}, True
    while ch:
        ch = False
        for a, b in sents:
            if a in reach and b not in reach:
                reach.add(b)
                ch = True
    return "yes" if goal in reach else "unknown"


def p_fewshot_number_rule(p):
    m = re.match(r"Examples: (.*)\. Now (.*?) -> \?$", p)
    ex = m[1].split("; ")
    if ex[0].startswith("("):
        prs = [tuple(map(int, re.findall(r"-?\d+", e))) for e in ex]
        q = tuple(map(int, re.findall(r"-?\d+", m[2])))
        if all(a + b == r for a, b, r in prs):
            return q[0] + q[1]
        if all(abs(a - b) == r for a, b, r in prs):
            return abs(q[0] - q[1])
        return None
    pts = [tuple(map(int, e.split(" -> "))) for e in ex]
    x = int(m[2])
    # find integer A,B consistent with all points
    for A in range(0, 12):
        for B in range(-40, 41):
            if all(A * a + B == r for a, r in pts):
                cands = {A * x + B}
                return cands.pop()


def p_string_transform(p):
    m = re.match(r"Examples: (.*)\. Now (\w+) -> \?$", p)
    pts = [e.split(" -> ") for e in m[1].split("; ")]
    w = m[2]
    rules = {"reverse": lambda s: s[::-1], "first_last": lambda s: s[0] + s[-1], "sort": lambda s: "".join(sorted(s)),
             "drop_first": lambda s: s[1:], "double": lambda s: s + s}
    ok = [f for f in rules.values() if all(f(a) == b for a, b in pts)]
    outs = {f(w) for f in ok}
    return outs.pop() if len(outs) == 1 else None


PARSERS = {k[2:]: v for k, v in globals().items() if k.startswith("p_") and callable(v)}


def check_item(it):
    """Return a list of problems (empty = ok)."""
    bad = []
    fam = FAMILIES[it["family"]]
    prompt, ans = it["prompt"], it["answer"]
    core_text = prompt
    w = it.get("wrap", {"pre": "", "post": ""})
    if w["pre"]:
        core_text = core_text[len(w["pre"]) + 1:]
    if w["post"]:
        core_text = core_text[:-(len(w["post"]) + 1)]
    canon = undo_layout(core_text, it.get("layout", "facts_first"))
    for s in it["slots"]:
        if str(s) not in prompt:
            bad.append(f"slot {s!r} not in prompt")
    for st in it["steps"]:
        m = re.fullmatch(r"(-?\d+) ([+\-*/]) (-?\d+) = (-?\d+)", st)
        if m:
            a, o, b, r = int(m[1]), m[2], int(m[3]), int(m[4])
            val = {"+": a + b, "-": a - b, "*": a * b, "/": a // b if b and a % b == 0 else None}[o]
            if val != r:
                bad.append(f"step wrong: {st}")
    if it["steps"]:
        m = re.fullmatch(r".*= (-?\d+)", it["steps"][-1])
        if m and fam["answer_open"] and it["family"] in ("chain_ops", "chain_story2", "arith_bare", "div_exact", "story_addsub") and m[1] != ans:
            if it["family"] != "arith_bare" or it["variant"] != "missing":
                bad.append(f"last step {m[1]} != answer {ans}")
    if it["family"] in PARSERS:
        try:
            got = PARSERS[it["family"]](canon)
        except Exception as e:  # parser failure is a finding, not a skip
            got, bad = None, bad + [f"parser error {type(e).__name__}: {e}"]
        if got is None:
            bad.append("parser returned None")
        elif str(got) not in [str(a) for a in it["accepted"]]:
            bad.append(f"parser says {got!r}, item says {ans!r}")
    if it["est_tokens"] > MAX_TOKENS_EST:
        bad.append(f"too long: {it['est_tokens']}")
    if it["family"] in AMBIG and AMBIG[it["family"]](canon):
        bad.append("more than one simple rule fits the examples")
    return bad


# ---------------------------------------------------------------- unique-rule check for induction families
def _fit_seq(shown):
    """All next-values predicted by every simple sequence rule that fits `shown`."""
    s, out = shown, set()
    d = [b - a for a, b in zip(s, s[1:])]
    if len(set(d)) == 1:
        out.add(s[-1] + d[0])
    if all(x != 0 for x in s[:-1]) and all(b % a == 0 for a, b in zip(s, s[1:])):
        r = [b // a for a, b in zip(s, s[1:])]
        if len(set(r)) == 1:
            out.add(s[-1] * r[0])
    if len(d) >= 3:
        e = [b - a for a, b in zip(d, d[1:])]
        if len(set(e)) == 1:
            out.add(s[-1] + d[-1] + e[0])
        if all(d[i] == d[i % 2] for i in range(len(d))):
            out.add(s[-1] + d[len(d) % 2])
    if len(s) >= 3 and all(s[i] == s[i - 1] + s[i - 2] for i in range(2, len(s))):
        out.add(s[-1] + s[-2])
    return out


def amb_seq_next(p):
    m = re.search(r"(-?\d+(?:, -?\d+)+)", p)
    shown = [int(t) for t in m[1].split(",")]
    return len(_fit_seq(shown)) != 1


def amb_odd_one_out(p):
    xs = [int(t) for t in re.search(r": ([\d, ]+)\?", p)[1].split(",")]
    odd = set()
    rules = [lambda x, m=m: x % m == 0 for m in range(2, 10)] + [lambda x: x % 2 == 1, lambda x: len(str(x)) == 2, lambda x: len(str(x)) == 3]
    for f in rules:
        bad = [x for x in xs if not f(x)]
        if len(bad) == 1 and len(xs) - 1 >= 3:
            odd.add(bad[0])
    return len(odd) != 1


def amb_fewshot_number_rule(p):
    m = re.match(r"Examples: (.*)\. Now (.*?) -> \?$", p)
    ex = m[1].split("; ")
    outs = set()
    if ex[0].startswith("("):
        prs = [tuple(map(int, re.findall(r"-?\d+", e))) for e in ex]
        q = tuple(map(int, re.findall(r"-?\d+", m[2])))
        hyp = [lambda a, b: a + b, lambda a, b: abs(a - b), lambda a, b: a - b, lambda a, b: a * b, lambda a, b: max(a, b), lambda a, b: min(a, b)]
        for f in hyp:
            if all(f(a, b) == r for a, b, r in prs):
                outs.add(f(*q))
        return len(outs) != 1
    pts = [tuple(map(int, e.split(" -> "))) for e in ex]
    x = int(m[2])
    for A in range(0, 13):
        for B in range(-60, 61):
            if all(A * a + B == r for a, r in pts):
                outs.add(A * x + B)
    # also squares / digit-sum style rules would be exotic; the affine class is what the generator uses
    return len(outs) != 1


STR_RULES = {"reverse": lambda s: s[::-1], "first_last": lambda s: s[0] + s[-1], "sort": lambda s: "".join(sorted(s)),
             "drop_first": lambda s: s[1:], "double": lambda s: s + s, "drop_last": lambda s: s[:-1], "last_first": lambda s: s[-1] + s[0],
             "first_only": lambda s: s[0], "last_only": lambda s: s[-1], "rot": lambda s: s[1:] + s[0]}


def amb_string_transform(p):
    m = re.match(r"Examples: (.*)\. Now (\w+) -> \?$", p)
    pts = [e.split(" -> ") for e in m[1].split("; ")]
    outs = {f(m[2]) for f in STR_RULES.values() if all(f(a) == b for a, b in pts)}
    return len(outs) != 1


def amb_group_induct(p):
    m = re.match(r"Group A: ([\d, ]+)\. Group B: ([\d, ]+)\. Which group does (\d+) belong to\?", p)
    A = [int(t) for t in m[1].split(",")]
    B = [int(t) for t in m[2].split(",")]
    q = int(m[3])
    preds = set()
    rules = []
    for k in range(2, 10):
        rules += [lambda x, k=k: x % k == 0, lambda x, k=k: x % k != 0]
    for t in range(5, 95):
        rules += [lambda x, t=t: x >= t, lambda x, t=t: x < t]
    for f in rules:
        if all(f(a) for a in A) and not any(f(b) for b in B):
            preds.add("A" if f(q) else "B")
    return len(preds) != 1


AMBIG = {k[4:]: v for k, v in globals().items() if k.startswith("amb_")}
