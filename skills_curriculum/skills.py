"""Skill families, easy (level 1) to hard (level 8). Each returns prompt, answer, steps, slots, meta.

`slots` are strings that must appear verbatim in the prompt (the verifier checks the prompt really shows the facts
the answer was computed from). `steps` is the worked solution a calculator-using core could follow.
"""
import re
from .core import family, FAMILIES

ORD = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _a(word):
    return "an" if word[0] in "aeiou" else "a"


def _lst(xs):
    return ", ".join(str(x) for x in xs)


# =============================================================== LEVEL 1: look and copy
@family("copy_word", 1, ["plain", "echo", "distractor"], "copy a made-up word exactly")
def copy_word(c, v):
    w = c.madeup()
    if v == "plain":
        p = c.pick("plain", ["Repeat the word: {w}", "Say this word back: {w}", "Write the word {w} once more."]).format(w=w)
    elif v == "echo":
        p = c.pick("echo", ["Echo: {w}", "Copy exactly what follows the colon. {w}"]).format(w=w)
        p = p if ":" in p else "Copy this: " + w
    else:
        w2 = c.madeup()
        p = c.pick("dist", ["Ignore {w2}. Repeat {w}.", "Do not say {w2}; say {w}.", "Skip {w2} and give back {w}."]).format(w=w, w2=w2)
    return {"prompt": p, "answer": w, "slots": [w], "meta": {"word": w}, "steps": [f"copy {w}"]}


@family("list_index", 1, ["ordinal", "first_last", "after", "before", "position_of"], "pick an item from a list of words")
def list_index(c, v):
    k = c.rng.randint(4, 6 + c.diff)
    ws = c.words(k)
    L = ", ".join(ws)
    head = c.pick("head", ["Items: {L}.", "The list is {L}.", "Here are some words: {L}."]).format(L=L)
    if v == "ordinal":
        i = c.rng.randrange(k)
        q, a = f"What is the {ORD[i]} item?", ws[i]
    elif v == "first_last":
        i = c.rng.choice((0, k - 1))
        q, a = ("What is the first item?" if i == 0 else "What is the last item?"), ws[i]
    elif v == "after":
        i = c.rng.randrange(k - 1)
        q, a = f"Which word comes right after {ws[i]}?", ws[i + 1]
    elif v == "before":
        i = c.rng.randrange(1, k)
        q, a = f"Which word comes right before {ws[i]}?", ws[i - 1]
    else:
        i = c.rng.randrange(k)
        q, a = f"At which position is {ws[i]}? Count from 1.", i + 1
    return {"prompt": head + " " + q, "answer": a, "slots": ws, "meta": {"items": ws, "variant": v},
            "steps": [f"list = {ws}", f"answer {a}"]}


@family("letter_ops", 1, ["count", "length", "first", "last", "nth"], "letters of a word")
def letter_ops(c, v):
    w = c.madeup(c.rng.choice((2, 3, 3, 4)))
    if v == "count":
        ch = c.rng.choice(w)
        q, a = f"How many times does the letter {ch} appear in {w}?", w.count(ch)
    elif v == "length":
        q, a = f"How many letters are in the word {w}?", len(w)
    elif v == "first":
        q, a = f"What is the first letter of {w}?", w[0]
    elif v == "last":
        q, a = f"What is the last letter of {w}?", w[-1]
    else:
        i = c.rng.randrange(len(w))
        q, a = f"What is letter number {i + 1} of {w}?", w[i]
    return {"prompt": q, "answer": a, "slots": [w], "meta": {"word": w, "variant": v}, "steps": [f"word {w}"]}


# =============================================================== LEVEL 2: numbers
def _pn(r, d):
    return r.randint(10 ** d // 10 if d > 1 else 1, 10 ** d - 1)


@family("arith_bare", 2, ["symbol", "verbal", "missing", "subtract_word"], "one-step arithmetic with no story")
def arith_bare(c, v):
    d = 2 + (c.diff >= 2)
    op = c.rng.choice(["+", "-", "*"])
    if v == "subtract_word":
        op = "-"
    if op == "*":
        x, y = c.rng.randint(2, 12 + 20 * c.diff), c.rng.randint(2, 19)
    else:
        x, y = c.difficulty_int(10, 10 ** d - 1), c.difficulty_int(10, 10 ** d - 1)
        if op == "-" and x < y:
            x, y = y, x
    r = {"+": x + y, "-": x - y, "*": x * y}[op]
    word = {"+": "plus", "-": "minus", "*": "times"}[op]
    if v == "symbol":
        p = c.pick("sym", ["{x} {o} {y} =", "Compute {x} {o} {y}.", "{x} {o} {y} = ?"]).format(x=x, y=y, o=op)
        a, slots = r, [x, y]
    elif v == "verbal":
        p = c.pick("verb", ["What is {x} {w} {y}?", "Work out {x} {w} {y}.", "Give the value of {x} {w} {y}."]).format(x=x, y=y, w=word)
        a, slots = r, [x, y]
    elif v == "missing":
        p, a, slots = f"{x} {op} ? = {r}", y, [x, r]
    else:
        p = c.pick("sw", ["Take {y} away from {x}.", "Subtract {y} from {x}."]).format(x=x, y=y)
        a, slots = r, [x, y]
    return {"prompt": p, "answer": a, "slots": slots, "meta": {"x": x, "y": y, "op": op, "variant": v}, "steps": [f"{x} {op} {y} = {r}"]}


@family("div_exact", 2, ["bare", "share", "groups"], "exact division")
def div_exact(c, v):
    y = c.rng.randint(2, 9 + 3 * c.diff)
    q = c.rng.randint(2, 12 + 15 * c.diff)
    x = y * q
    if v == "bare":
        p = f"{x} / {y} = ?"
    elif v == "share":
        n, nn = c.name(), c.noun()
        p = c.pick("sh", ["{n} shares {x} {nn} equally among {y} friends. How many does each friend get?",
                          "{x} {nn} are split evenly into {y} piles. How many are in each pile?"]).format(n=n, x=x, nn=nn, y=y)
    else:
        nn = c.noun()
        p = c.pick("gr", ["Packs hold {y} {nn} each. How many packs are needed for {x} {nn}?",
                          "How many sets of {y} can be made from {x} {nn}?"]).format(nn=nn, x=x, y=y)
    return {"prompt": p, "answer": q, "slots": [x, y], "meta": {"x": x, "y": y}, "steps": [f"{x} / {y} = {q}"]}


CONTEXTS = [("counted", "on Monday", "on Tuesday"), ("sold", "at the market", "at the fair"),
            ("collected", "in spring", "in autumn"), ("stacked", "in the attic", "in the cellar"),
            ("delivered", "to the school", "to the clinic"), ("found", "under the bed", "behind the couch"),
            ("received", "in June", "in July"), ("sorted", "before lunch", "after dinner")]


@family("story_addsub", 2, ["total", "difference", "gain", "loss"], "one-step story problems, composed wording", layout=True)
def story_addsub(c, v):
    n, nn = c.name(), c.noun()
    x = c.difficulty_int(10, 99 + 400 * (c.diff > 0))
    y = c.difficulty_int(10, 99 + 400 * (c.diff > 0))
    if v in ("total", "difference"):
        if v == "difference" and x < y:
            x, y = y, x
        pv, A, B = c.pick("ctx", CONTEXTS)
        intro = c.pick("intro", ["{n} {pv} {x} {nn} {A} and {y} {nn} {B}.", "{x} {nn} were {pv} {A}, and {y} {nn} were {pv} {B}."])
        intro = intro.format(n=n, pv=pv, x=x, y=y, nn=nn, A=A, B=B)
        if v == "total":
            q = c.pick("qt", ["How many {nn} are there altogether?", "How many {nn} are there in all?", "Find the sum of the {nn} from both places."]).format(nn=nn)
            a, st = x + y, f"{x} + {y} = {x + y}"
        else:
            q = c.pick("qd", ["How many more {nn} were {pv} {A} than {B}?", "By how many do the {nn} {A} outnumber those {B}?"]).format(nn=nn, pv=pv, A=A, B=B)
            a, st = x - y, f"{x} - {y} = {x - y}"
        return {"prompt": intro + " " + q, "answer": a, "slots": [x, y], "meta": {"x": x, "y": y, "op": "add" if v == "total" else "sub"}, "steps": [st]}
    if v == "gain":
        g = c.pick("g", ["received", "was given", "picked up"])
        p = f"{n} started with {x} {nn}. Later, {n} {g} {y} more. " + c.pick("q", ["How many {nn} does {n} end up with?", "How many {nn} does {n} have at the end?"]).format(nn=nn, n=n)
        a = x + y
        return {"prompt": p, "answer": a, "slots": [x, y], "meta": {"x": x, "y": y, "op": "add"}, "steps": [f"{x} + {y} = {a}"]}
    y = min(y, x - 1) if y >= x else y
    g = c.pick("l", ["gave away", "lost", "used up"])
    p = f"At first {n} owned {x} {nn}. Then {n} {g} {y} of them. " + c.pick("ql", ["How many {nn} are left with {n} now?", "How many {nn} does {n} have now?"]).format(nn=nn, n=n)
    a = x - y
    return {"prompt": p, "answer": a, "slots": [x, y], "meta": {"x": x, "y": y, "op": "sub"}, "steps": [f"{x} - {y} = {a}"]}


@family("compare_numbers", 2, ["larger", "smaller", "largest_of", "smallest_of", "count_above"], "compare numbers")
def compare_numbers(c, v):
    hi = 99 + 900 * (c.diff > 0)
    if v in ("larger", "smaller"):
        x, y = c.rng.sample(range(10, hi), 2)
        a = max(x, y) if v == "larger" else min(x, y)
        p = c.pick("p", ["Which is {w}, {x} or {y}?", "Between {x} and {y}, which number is {w}?"]).format(w=v, x=x, y=y)
        return {"prompt": p, "answer": a, "slots": [x, y], "meta": {"xs": [x, y], "variant": v}, "steps": [f"compare {x} {y}"]}
    k = c.rng.randint(4, 5 + c.diff)
    xs = c.rng.sample(range(10, hi), k)
    if v == "count_above":
        t = c.rng.randint(20, hi - 20)
        a = sum(1 for z in xs if z > t)
        p = f"Numbers: {_lst(xs)}. How many are greater than {t}?"
        return {"prompt": p, "answer": a, "slots": xs + [t], "meta": {"xs": xs, "t": t, "variant": v}, "steps": [f"count > {t}"]}
    a = max(xs) if v == "largest_of" else min(xs)
    w = "largest" if v == "largest_of" else "smallest"
    p = f"Numbers: {_lst(xs)}. Which is the {w}?"
    return {"prompt": p, "answer": a, "slots": xs, "meta": {"xs": xs, "variant": v}, "steps": [f"{w} of {xs}"]}


@family("list_stats", 2, ["sum", "range", "count_even", "second_largest"], "small statistics of a number list")
def list_stats(c, v):
    k = c.rng.randint(3, 4 + c.diff)
    xs = [c.difficulty_int(2, 99) for _ in range(k)]
    if v == "second_largest":
        xs = c.rng.sample(range(2, 100), k)
    if v == "sum":
        a, q = sum(xs), "What is the sum of the numbers?"
    elif v == "range":
        a, q = max(xs) - min(xs), "What is the largest minus the smallest?"
    elif v == "count_even":
        a, q = sum(1 for z in xs if z % 2 == 0), "How many of the numbers are even?"
    else:
        a, q = sorted(xs)[-2], "What is the second largest number?"
    return {"prompt": f"Numbers: {_lst(xs)}. {q}", "answer": a, "slots": xs, "meta": {"xs": xs, "variant": v}, "steps": [f"{v} of {xs}"]}


@family("digits_parity", 2, ["parity", "digit_sum", "tens_digit", "num_digits"], "digits and odd/even")
def digits_parity(c, v):
    n = c.difficulty_int(10, 99 + 9900 * (c.diff > 0))
    if v == "parity":
        a, q = ("even" if n % 2 == 0 else "odd"), f"Is {n} odd or even?"
    elif v == "digit_sum":
        a, q = sum(int(d) for d in str(n)), f"What is the sum of the digits of {n}?"
    elif v == "tens_digit":
        n = max(n, 10)
        a, q = (n // 10) % 10, f"What is the tens digit of {n}?"
    else:
        a, q = len(str(n)), f"How many digits does {n} have?"
    return {"prompt": q, "answer": a, "slots": [n], "meta": {"n": n, "variant": v}, "steps": [f"n = {n}"]}


# =============================================================== LEVEL 3: sequences
@family("seq_next", 3, ["arith", "geom", "growing_step", "alternating", "fib_like"], "continue a number sequence")
def seq_next(c, v):
    k = 5 if c.diff else 4
    if v == "arith":
        a0, d = c.rng.randint(1, 40), c.rng.randint(2, 15) * c.rng.choice((1, 1, -1))
        s = [a0 + d * i for i in range(k + 2)]
    elif v == "geom":
        a0, r = c.rng.randint(1, 6), c.rng.choice((2, 3, 4))
        s = [a0 * r ** i for i in range(k + 2)]
    elif v == "growing_step":
        a0, d0, e = c.rng.randint(1, 20), c.rng.randint(1, 4), c.rng.randint(1, 3)
        s, cur, d = [], a0, d0
        for _ in range(k + 2):
            s.append(cur)
            cur += d
            d += e
    elif v == "alternating":
        a0, p, q = c.rng.randint(5, 40), c.rng.randint(3, 12), c.rng.randint(1, 8)
        s, cur = [], a0
        for i in range(k + 2):
            s.append(cur)
            cur += p if i % 2 == 0 else -q
    else:
        a, b = c.rng.randint(1, 6), c.rng.randint(1, 6)
        s = [a, b]
        while len(s) < k + 2:
            s.append(s[-1] + s[-2])
    shown, nxt = s[:k], s[k]
    p = c.pick("p", ["{L}, ... What number comes next?", "Continue the pattern: {L}, ?", "Sequence: {L}. What is the next number?"]).format(L=_lst(shown))
    return {"prompt": p, "answer": nxt, "slots": shown, "meta": {"shown": shown, "variant": v}, "steps": [f"rule {v}", f"next = {nxt}"]}


@family("seq_cycle", 3, ["next_letter", "kth_letter", "kth_number"], "repeating patterns")
def seq_cycle(c, v):
    m = c.rng.randint(2, 4 + (c.diff > 0))
    if v == "kth_number":
        pat = c.rng.sample(range(1, 10), m)
    else:
        pat = c.rng.sample("abcdefghijklmnopqrstuvwxyz", m)
    P = " ".join(str(z) for z in pat)
    if v == "next_letter":
        reps = c.rng.randint(2, 3)
        n_shown = m * reps + c.rng.randint(1, m - 1)
        shown = [pat[i % m] for i in range(n_shown)]
        return {"prompt": f"{' '.join(shown)} ? What comes next?", "answer": pat[n_shown % m], "slots": shown,
                "meta": {"pat": pat, "n": n_shown}, "steps": [f"cycle length {m}"]}
    k = c.rng.randint(m + 1, 12 + 15 * c.diff)
    return {"prompt": f"The pattern {P} repeats forever. What is item number {k}?", "answer": pat[(k - 1) % m],
            "slots": pat + [k], "meta": {"pat": pat, "k": k}, "steps": [f"({k}-1) mod {m} = {(k - 1) % m}"]}


@family("odd_one_out", 3, ["multiples", "parity", "digit_count"], "find the number that breaks the rule")
def odd_one_out(c, v):
    k = c.rng.randint(4, 5 + c.diff)
    if v == "multiples":
        m = c.rng.randint(3, 9)
        good = [m * c.rng.randint(2, 15) for _ in range(k - 1)]
        bad = c.rng.randint(10, 120)
        while bad % m == 0:
            bad += 1
        good = list(dict.fromkeys(good))
    elif v == "parity":
        par = c.rng.choice((0, 1))
        good = [2 * c.rng.randint(5, 49) + par for _ in range(k - 1)]
        bad = 2 * c.rng.randint(5, 49) + (1 - par)
    else:
        nd = c.rng.choice((2, 3))
        good = [c.rng.randint(10 ** (nd - 1), 10 ** nd - 1) for _ in range(k - 1)]
        bad = c.rng.randint(10 ** (nd), 10 ** (nd + 1) - 1)
    good = [g for g in good if g != bad]
    xs = good + [bad]
    c.rng.shuffle(xs)
    if len(set(xs)) != len(xs) or len(xs) < 4:
        xs = list(dict.fromkeys(xs))
    return {"prompt": f"Which number does not belong with the others: {_lst(xs)}?", "answer": bad, "slots": xs,
            "meta": {"xs": xs, "variant": v}, "steps": [f"rule {v}"]}


# =============================================================== LEVEL 4: binding and tracking
@family("var_chain", 4, ["forward", "reassign", "distractor", "two_vars"], "follow variable assignments", layout=True)
def var_chain(c, v):
    names = c.rng.sample("abcdefghkmnpqrstuwxyz", 6)
    steps_n = 1 + c.diff + (c.rng.random() < 0.4)
    val = {}
    lines, tr = [], []
    first = names[0]
    val[first] = c.rng.randint(2, 30)
    lines.append(f"{first} = {val[first]}.")
    cur = first
    for i in range(steps_n):
        o = c.rng.choice("+-*")
        n = c.rng.randint(2, 9)
        nv = {"+": val[cur] + n, "-": val[cur] - n, "*": val[cur] * n}[o]
        nxt = names[i + 1] if v != "reassign" else cur
        lines.append(f"{nxt} = {cur} {o} {n}.")
        tr.append(f"{nxt} = {val[cur]} {o} {n} = {nv}")
        val[nxt] = nv
        cur = nxt
    if v == "distractor":
        dn = names[5]
        lines.insert(c.rng.randrange(1, len(lines) + 1), f"{dn} = {c.rng.randint(2, 40)}.")
    if v == "two_vars":
        other = names[5]
        ov = c.rng.randint(2, 30)
        lines.append(f"{other} = {ov}.")
        a, q = val[cur] + ov, f"What is {cur} + {other}?"
        tr.append(f"{val[cur]} + {ov} = {a}")
    else:
        a, q = val[cur], f"What is {cur}?"
    return {"prompt": " ".join(lines) + " " + q, "answer": a, "slots": [], "meta": {"lines": lines, "q": q, "variant": v}, "steps": tr}


@family("order_chain", 4, ["tallest", "shortest", "yes_no", "middle"], "order from pairwise comparisons", layout=True)
def order_chain(c, v):
    k = c.rng.randint(3, 4 + (c.diff > 0))
    es = c.names(k)
    parts = [p for p in c.pick("adj2", ["taller|tallest|shortest", "older|oldest|youngest", "faster|fastest|slowest", "heavier|heaviest|lightest"]).split("|")]
    cmp_w, top, bot = parts
    pairs = [(es[i], es[i + 1]) for i in range(k - 1)]  # es[0] is the top
    stm = [f"{a} is {cmp_w} than {b}." for a, b in pairs]
    c.rng.shuffle(stm)
    body = " ".join(stm)
    if v == "tallest":
        q, a = f"Who is the {top}?", es[0]
    elif v == "shortest":
        q, a = f"Who is the {bot}?", es[-1]
    elif v == "yes_no":
        i, j = c.rng.sample(range(k), 2)
        q, a = f"Is {es[i]} {cmp_w} than {es[j]}?", "yes" if i < j else "no"
    else:
        if k % 2 == 0:
            q, a = f"Who is the {top}?", es[0]
        else:
            q, a = f"Who is neither the {top} nor the {bot}? Name the one in the middle.", es[k // 2] if k == 3 else es[1]
            if k == 5:
                q, a = f"Who is second from the top?", es[1]
    return {"prompt": body + " " + q, "answer": a, "slots": es, "meta": {"order_top_to_bottom": es, "cmp": cmp_w, "q": q, "variant": v}, "steps": [f"order {es}"]}


@family("object_track", 4, ["handoff", "move_place", "swap"], "follow who has / where something is")
def object_track(c, v):
    k = 2 + c.diff
    if v == "handoff":
        ps = c.names(k + 1)
        obj = c.word()
        s = [f"{ps[0]} has the {obj}."] + [f"{ps[i]} gives it to {ps[i + 1]}." for i in range(k)]
        return {"prompt": " ".join(s) + f" Who has the {obj} now?", "answer": ps[-1], "slots": ps, "meta": {"holders": ps}, "steps": [f"holders {ps}"]}
    if v == "move_place":
        pl = []
        while len(pl) < k + 1:
            p_ = c.place()
            if p_ not in pl:
                pl.append(p_)
        obj = c.word()
        s = [f"The {obj} is in the {pl[0]}."] + [f"Then it is moved to the {pl[i + 1]}." for i in range(k)]
        return {"prompt": " ".join(s) + f" Where is the {obj} now?", "answer": pl[-1], "slots": pl, "meta": {"places": pl}, "steps": [f"places {pl}"]}
    a, b = c.names(2)
    o1, o2 = c.words(2)
    s = f"{a} holds the {o1}. {b} holds the {o2}. {a} and {b} swap what they hold."
    if c.diff:
        s += " Then they swap again."
    final_a = o1 if c.diff else o2
    who = c.rng.choice((a, b))
    ans = final_a if who == a else (o2 if c.diff else o1)
    return {"prompt": s + f" What does {who} hold now?", "answer": ans, "slots": [a, b, o1, o2], "meta": {"a": a, "b": b, "swaps": 1 + int(bool(c.diff)), "o": [o1, o2], "who": who}, "steps": ["swap"]}


@family("table_lookup", 4, ["lookup", "sum_two", "most", "difference"], "read facts from a small table in text", layout=True)
def table_lookup(c, v):
    k = c.rng.randint(3, 4 + c.diff)
    ks = c.words(k)
    vals = c.rng.sample(range(2, 60), k)
    tab = "; ".join(f"{a}: {b}" for a, b in zip(ks, vals))
    i, j = c.rng.sample(range(k), 2)
    if v == "lookup":
        q, a = f"What is the number for {ks[i]}?", vals[i]
    elif v == "sum_two":
        q, a = f"What is {ks[i]} plus {ks[j]}?", vals[i] + vals[j]
    elif v == "most":
        q, a = "Which word has the largest number?", ks[vals.index(max(vals))]
    else:
        a = abs(vals[i] - vals[j])
        q = f"How much bigger is the larger of {ks[i]} and {ks[j]} than the smaller?"
    return {"prompt": f"Table - {tab}. {q}", "answer": a, "slots": ks + vals, "meta": {"keys": ks, "vals": vals, "i": i, "j": j, "variant": v}, "steps": ["read table"]}


@family("state_update", 4, ["add_remove", "two_containers"], "keep a running count through events", layout=True)
def state_update(c, v):
    nn = c.noun()
    start = c.rng.randint(5, 40)
    cur, ev, tr = start, [], []
    for _ in range(2 + c.diff):
        n = c.rng.randint(1, 9)
        if c.rng.random() < 0.5 or cur - n < 0:
            ev.append(f"{n} are added.")
            cur += n
            tr.append(f"+{n} -> {cur}")
        else:
            ev.append(f"{n} are removed.")
            cur -= n
            tr.append(f"-{n} -> {cur}")
    if v == "add_remove":
        p = f"A jar holds {start} {nn}. " + " ".join(ev) + f" How many {nn} are in the jar now?"
        return {"prompt": p, "answer": cur, "slots": [start], "meta": {"start": start, "events": ev}, "steps": tr}
    s2 = c.rng.randint(5, 40)
    p = f"Jar A holds {start} {nn}. Jar B holds {s2}. For jar A: " + " ".join(ev) + " How many are in both jars together now?"
    return {"prompt": p, "answer": cur + s2, "slots": [start, s2], "meta": {"start": start, "events": ev, "other": s2}, "steps": tr + [f"{cur} + {s2}"]}


# =============================================================== LEVEL 5: logic
@family("syllogism", 5, ["all", "none", "unknown", "chain", "distractor"], "reasoning over invented categories", answer_open=False)
def syllogism(c, v):
    a, b, d = c.catword(), c.catword(), c.catword()
    while b == a:
        b = c.catword()
    while d in (a, b):
        d = c.catword()
    x = c.madeup().capitalize()
    if v == "all":
        p, ans = f"All {a}s are {b}s. {x} is a {a}. Is {x} a {b}?", "yes"
    elif v == "none":
        p, ans = f"No {a}s are {b}s. {x} is a {a}. Is {x} a {b}?", "no"
    elif v == "unknown":
        p, ans = f"All {a}s are {b}s. {x} is a {b}. Is {x} a {a}?", "unknown"
    elif v == "chain":
        p, ans = f"All {a}s are {b}s. All {b}s are {d}s. {x} is a {a}. Is {x} a {d}?", "yes"
    else:
        p, ans = f"All {a}s are {b}s. All {d}s are {a}s. {x} is a {d}. Is {x} a {b}?", "yes"
    return {"prompt": p, "answer": ans, "slots": [a, b, x], "meta": {"variant": v}, "steps": [v]}


@family("prop_eval", 5, ["and_or", "not", "nested", "implies"], "evaluate true/false statements", answer_open=False)
def prop_eval(c, v):
    names = c.rng.sample("PQRS", 3)
    val = {n: c.rng.random() < 0.5 for n in names}
    P, Q, R = names
    if v == "and_or":
        e = c.rng.choice([f"{P} and {Q}", f"{P} or {Q}"])
        ans = (val[P] and val[Q]) if " and " in e else (val[P] or val[Q])
    elif v == "not":
        e = c.rng.choice([f"not {P}", f"{P} and not {Q}", f"not {P} or {Q}"])
        ans = eval(e.replace(P, str(val[P])).replace(Q, str(val[Q])))
    elif v == "nested":
        e = c.rng.choice([f"({P} or {Q}) and {R}", f"{P} and ({Q} or not {R})", f"not ({P} and {Q}) or {R}"])
        ex = e
        for n in names:
            ex = re.sub(rf"\b{n}\b", str(val[n]), ex)
        ans = eval(ex)
    else:
        e = f"if {P} then {Q}"
        ans = (not val[P]) or val[Q]
    facts = " ".join(f"{n} is {'true' if val[n] else 'false'}." for n in names)
    return {"prompt": f"{facts} Is this statement true or false: {e}?", "answer": "true" if ans else "false", "slots": names,
            "meta": {"expr": e, "val": val, "variant": v}, "steps": [e]}


@family("rule_apply", 5, ["number_rule", "lookup_rule", "threshold"], "apply a rule stated in the prompt")
def rule_apply(c, v):
    if v == "number_rule":
        a_, b_ = c.rng.randint(2, 5), c.rng.randint(1, 9)
        n = c.rng.randint(5, 60)
        a = n // 2 if n % 2 == 0 else n * a_ + b_
        p = f"Rule: if a number is even, halve it; if odd, multiply it by {a_} and add {b_}. Apply the rule once to {n}."
        return {"prompt": p, "answer": a, "slots": [n, a_, b_], "meta": {"n": n, "a": a_, "b": b_}, "steps": [f"{n} is {'even' if n % 2 == 0 else 'odd'}"]}
    if v == "lookup_rule":
        ks = []
        while len(ks) < 3:
            col = c.color()
            if col not in ks:
                ks.append(col)
        acts = c.rng.sample(["stop", "go", "wait", "turn", "jump", "hide", "sing"], 3)
        i = c.rng.randrange(3)
        p = "Rules: " + " ".join(f"If the light is {k}, {a}." for k, a in zip(ks, acts)) + f" The light is {ks[i]}. What do you do?"
        return {"prompt": p, "answer": acts[i], "slots": ks + acts, "meta": {"ks": ks, "acts": acts, "i": i}, "steps": [f"{ks[i]} -> {acts[i]}"]}
    t, x = c.rng.randint(10, 60), c.rng.randint(1, 90)
    n1, n2 = c.rng.randint(2, 9), c.rng.randint(2, 9)
    a = x + n1 if x >= t else x - n2 if x >= n2 else n2 - x
    p = f"Rule: if a number is at least {t}, add {n1}; otherwise subtract {n2}. Apply it to {x}."
    if x < t and x < n2:
        a = x - n2
    return {"prompt": p, "answer": a, "slots": [t, n1, n2, x], "meta": {"t": t, "n1": n1, "n2": n2, "x": x}, "steps": ["threshold"]}


@family("verify_claim", 5, ["add", "sub", "mul", "sorted"], "check whether a stated fact is correct", answer_open=False)
def verify_claim(c, v):
    ok = c.rng.random() < 0.5
    if v == "sorted":
        xs = sorted(c.rng.sample(range(1, 90), 5))
        if not ok:
            i = c.rng.randrange(4)
            xs[i], xs[i + 1] = xs[i + 1], xs[i]
        return {"prompt": f"Is this list in increasing order: {_lst(xs)}?", "answer": "yes" if ok else "no", "slots": xs, "meta": {"xs": xs}, "steps": ["scan"]}
    x, y = c.difficulty_int(10, 99), c.difficulty_int(10, 99)
    if v == "mul":
        x, y = c.rng.randint(3, 15), c.rng.randint(3, 15)
    if v == "sub" and x < y:
        x, y = y, x
    r = {"add": x + y, "sub": x - y, "mul": x * y}[v]
    shown = r if ok else r + c.rng.choice((-10, -2, -1, 1, 2, 10))
    if shown < 0 or (not ok and shown == r):
        shown = r + 1
    o = {"add": "+", "sub": "-", "mul": "*"}[v]
    return {"prompt": f"Is this correct: {x} {o} {y} = {shown}?", "answer": "yes" if shown == r else "no", "slots": [x, y, shown],
            "meta": {"x": x, "y": y, "op": o, "shown": shown}, "steps": [f"{x} {o} {y} = {r}"]}


# =============================================================== LEVEL 6: multi-step
@family("chain_story2", 6, ["add_sub", "sub_add", "mul_add", "mul_sub", "distractor"], "two chained calculator steps in a story", layout=True)
def chain_story2(c, v):
    n, nn = c.name(), c.noun()
    x = c.rng.randint(10, 60 + 200 * (c.diff > 0))
    y = c.rng.randint(2, 40)
    z = c.rng.randint(2, 40)
    if v in ("add_sub", "distractor"):
        r1 = x + y
        z = min(z, r1 - 1)
        a = r1 - z
        p = f"{n} had {x} {nn}. Then {n} got {y} more. After that, {n} lost {z} of them."
        st = [f"{x} + {y} = {r1}", f"{r1} - {z} = {a}"]
    elif v == "sub_add":
        y = min(y, x - 1)
        r1 = x - y
        a = r1 + z
        p = f"{n} had {x} {nn}. Then {n} gave away {y}. After that, {n} found {z} more."
        st = [f"{x} - {y} = {r1}", f"{r1} + {z} = {a}"]
    elif v == "mul_add":
        x, y = c.rng.randint(2, 12), c.rng.randint(2, 15)
        r1 = x * y
        a = r1 + z
        p = f"{n} has {x} boxes with {y} {nn} in each. Then {n} gets {z} loose ones."
        st = [f"{x} * {y} = {r1}", f"{r1} + {z} = {a}"]
    else:
        x, y = c.rng.randint(2, 12), c.rng.randint(2, 15)
        r1 = x * y
        z = min(z, r1 - 1)
        a = r1 - z
        p = f"{n} has {x} boxes with {y} {nn} in each. Then {n} gives away {z} of the {nn}."
        st = [f"{x} * {y} = {r1}", f"{r1} - {z} = {a}"]
    if v == "distractor":
        other = c.noun()
        while other == nn:
            other = c.noun()
        p += f" The shop also has {c.rng.randint(20, 90)} {other}."
    return {"prompt": p + f" How many {nn} does {n} have now?", "answer": a, "slots": [x, y, z], "meta": {"x": x, "y": y, "z": z, "variant": v}, "steps": st}


@family("unit_convert", 6, ["single", "inverse", "two_hop"], "use conversion facts given in the prompt", heldout_family=True, layout=True)
def unit_convert(c, v):
    u1, u2, u3 = c.madeup(), c.madeup(), c.madeup()
    f1, f2 = c.rng.randint(2, 9), c.rng.randint(2, 9)
    if v == "single":
        n = c.rng.randint(2, 20)
        return {"prompt": f"1 {u1} equals {f1} {u2}. How many {u2} are in {n} {u1}?", "answer": n * f1, "slots": [u1, u2, f1, n], "meta": {"f1": f1, "n": n}, "steps": [f"{n} * {f1}"]}
    if v == "inverse":
        n = f1 * c.rng.randint(2, 15)
        return {"prompt": f"1 {u1} equals {f1} {u2}. How many {u1} are in {n} {u2}?", "answer": n // f1, "slots": [u1, u2, f1, n], "meta": {"f1": f1, "n": n}, "steps": [f"{n} / {f1}"]}
    n = c.rng.randint(2, 12)
    return {"prompt": f"1 {u1} equals {f1} {u2}. 1 {u2} equals {f2} {u3}. How many {u3} are in {n} {u1}?", "answer": n * f1 * f2,
            "slots": [u1, u2, u3, f1, f2, n], "meta": {"f1": f1, "f2": f2, "n": n}, "steps": [f"{n} * {f1} = {n * f1}", f"{n * f1} * {f2}"]}


@family("clock_date", 6, ["minutes_later", "minutes_earlier", "weekday_ahead", "weekday_back"], "clock and weekday arithmetic", heldout_family=True)
def clock_date(c, v):
    if v.startswith("minutes"):
        h, m = c.rng.randint(1, 12), c.rng.randint(0, 59)
        d = c.rng.randint(5, 170)
        t = h * 60 + m + (d if v == "minutes_later" else -d)
        t %= 12 * 60
        hh, mm = divmod(t, 60)
        hh = 12 if hh == 0 else hh
        word = "later" if v == "minutes_later" else "earlier"
        return {"prompt": f"It is {h}:{m:02d} on a 12-hour clock. What time is it {d} minutes {word}? Answer as h:mm.", "answer": f"{hh}:{mm:02d}",
                "slots": [f"{h}:{m:02d}", d], "meta": {"h": h, "m": m, "d": d, "v": v}, "steps": [f"minutes {h * 60 + m} +/- {d} mod 720"]}
    i, d = c.rng.randrange(7), c.rng.randint(2, 40)
    j = (i + d) % 7 if v == "weekday_ahead" else (i - d) % 7
    q = f"What day of the week will it be in {d} days?" if v == "weekday_ahead" else f"What day of the week was it {d} days ago?"
    return {"prompt": f"Today is {DAYS[i]}. {q}", "answer": DAYS[j], "slots": [DAYS[i], d],
            "meta": {"i": i, "d": d, "v": v}, "steps": [f"{d} mod 7 = {d % 7}"]}


@family("percent_rate", 6, ["percent", "times_as_many", "rate_total", "rate_each"], "percentages, multiples and rates", layout=True)
def percent_rate(c, v):
    nn = c.noun()
    if v == "percent":
        p_ = c.rng.choice((10, 20, 25, 50, 75))
        base = c.rng.choice([b for b in range(20, 400, 20) if (b * p_) % 100 == 0])
        return {"prompt": f"What is {p_}% of {base}?", "answer": base * p_ // 100, "slots": [p_, base], "meta": {"p": p_, "base": base}, "steps": [f"{base} * {p_} / 100"]}
    if v == "times_as_many":
        b, k = c.rng.randint(3, 30), c.rng.randint(2, 9)
        a, bn = c.names(2)
        return {"prompt": f"{b} {nn} belong to {bn}. {a} has {k} times as many {nn} as {bn}. How many does {a} have?", "answer": b * k, "slots": [b, k], "meta": {"b": b, "k": k}, "steps": [f"{b} * {k}"]}
    bags, per = c.rng.randint(2, 9), c.rng.randint(2, 15)
    if v == "rate_total":
        more = c.rng.randint(2, 9)
        return {"prompt": f"{bags} bags hold {bags * per} {nn} in all, the same number in each. How many {nn} are in {more} bags?", "answer": per * more,
                "slots": [bags, bags * per, more], "meta": {"bags": bags, "per": per, "more": more}, "steps": [f"{bags * per} / {bags} = {per}", f"{per} * {more}"]}
    return {"prompt": f"{bags} bags hold {bags * per} {nn} in all, the same number in each. How many {nn} are in one bag?", "answer": per,
            "slots": [bags, bags * per], "meta": {"bags": bags, "per": per}, "steps": [f"{bags * per} / {bags}"]}


@family("backward_solve", 6, ["sum_diff_larger", "sum_diff_smaller", "think_of_number"], "work backwards from a result", layout=True)
def backward_solve(c, v):
    if v.startswith("sum_diff"):
        s_, d_ = c.rng.randint(10, 100), c.rng.randint(2, 30)
        if (s_ + d_) % 2:
            s_ += 1
        big, small = (s_ + d_) // 2, (s_ - d_) // 2
        w = "larger" if v.endswith("larger") else "smaller"
        return {"prompt": f"Two numbers add up to {s_} and differ by {d_}. What is the {w} number?", "answer": big if w == "larger" else small,
                "slots": [s_, d_], "meta": {"s": s_, "d": d_, "w": w}, "steps": [f"({s_} {'+' if w == 'larger' else '-'} {d_}) / 2"]}
    n = c.rng.randint(2, 30)
    a_, m_ = c.rng.randint(2, 15), c.rng.randint(2, 6)
    res = (n + a_) * m_
    return {"prompt": f"I think of a number, add {a_}, then multiply by {m_}, and get {res}. What was my number?", "answer": n, "slots": [a_, m_, res],
            "meta": {"n": n, "a": a_, "m": m_}, "steps": [f"{res} / {m_} = {res // m_}", f"{res // m_} - {a_} = {n}"]}


# =============================================================== LEVEL 7: learn from examples in the prompt
@family("fewshot_number_rule", 7, ["add", "mult", "affine", "pair_sum", "pair_diff"], "infer a number rule from examples, then apply it")
def fewshot_number_rule(c, v):
    k = 3 if c.diff else 2
    if v.startswith("pair"):
        pairs = [(c.rng.randint(5, 50), c.rng.randint(2, 40)) for _ in range(k + 1)]
        f = (lambda a, b: a + b) if v == "pair_sum" else (lambda a, b: abs(a - b))
        ex = "; ".join(f"({a}, {b}) -> {f(a, b)}" for a, b in pairs[:k])
        a, b = pairs[k]
        return {"prompt": f"Examples: {ex}. Now ({a}, {b}) -> ?", "answer": f(a, b), "slots": [a, b], "meta": {"pairs": pairs, "v": v}, "steps": ["infer pair rule"]}
    if v == "add":
        A, B = 1, c.rng.randint(2, 30) * c.rng.choice((1, -1))
    elif v == "mult":
        A, B = c.rng.randint(2, 9), 0
    else:
        A, B = c.rng.randint(2, 6), c.rng.randint(1, 15)
    xs = c.rng.sample(range(2, 30), k + 1)
    f = lambda x: A * x + B
    ex = "; ".join(f"{x} -> {f(x)}" for x in xs[:k])
    return {"prompt": f"Examples: {ex}. Now {xs[k]} -> ?", "answer": f(xs[k]), "slots": xs[:k] + [xs[k]], "meta": {"A": A, "B": B, "xs": xs}, "steps": [f"rule x*{A}+{B}"]}


@family("string_transform", 7, ["reverse", "first_last", "sort", "drop_first", "double"], "infer a word rule from examples", heldout_family=True)
def string_transform(c, v):
    rules = {"reverse": lambda w: w[::-1], "first_last": lambda w: w[0] + w[-1], "sort": lambda w: "".join(sorted(w)),
             "drop_first": lambda w: w[1:], "double": lambda w: w + w}
    f = rules[v]
    ws = [c.madeup() for _ in range(3)]
    ex = "; ".join(f"{w} -> {f(w)}" for w in ws[:2])
    return {"prompt": f"Examples: {ex}. Now {ws[2]} -> ?", "answer": f(ws[2]), "slots": ws, "meta": {"rule": v, "ws": ws}, "steps": [f"rule {v}"]}


@family("cipher_map", 7, ["encode", "decode"], "use a small code table given in the prompt")
def cipher_map(c, v):
    letters = c.rng.sample("abcdefgh", 4)
    nums = c.rng.sample(range(1, 10), 4)
    tab = ", ".join(f"{a}={b}" for a, b in zip(letters, nums))
    L = 3
    if v == "encode":
        w = [c.rng.choice(letters) for _ in range(L)]
        return {"prompt": f"Code: {tab}. Write {''.join(w)} as numbers.", "answer": " ".join(str(nums[letters.index(x)]) for x in w),
                "slots": [''.join(w)], "meta": {"letters": letters, "nums": nums, "w": w}, "steps": ["look up each letter"]}
    n = [c.rng.choice(nums) for _ in range(L)]
    return {"prompt": f"Code: {tab}. Decode the numbers {' '.join(map(str, n))} into letters.", "answer": "".join(letters[nums.index(x)] for x in n),
            "slots": n, "meta": {"letters": letters, "nums": nums, "n": n}, "steps": ["look up each number"]}


@family("op_define", 7, ["linear", "maxmin", "product_minus", "nested"], "learn a made-up operation from its definition", heldout_family=True)
def op_define(c, v):
    sym = c.rng.choice(["#", "@", "&", "$"])
    a, b = c.rng.randint(2, 15), c.rng.randint(2, 15)
    if v == "linear":
        m_, n_ = c.rng.randint(2, 4), c.rng.randint(1, 3)
        d, f = f"x {sym} y means x*{m_} + y*{n_}", (lambda x, y: x * m_ + y * n_)
    elif v == "maxmin":
        d, f = f"x {sym} y means the larger of x and y minus the smaller", (lambda x, y: abs(x - y))
    elif v == "product_minus":
        d, f = f"x {sym} y means x*y - x", (lambda x, y: x * y - x)
    else:
        m_ = c.rng.randint(2, 4)
        d, f = f"x {sym} y means x*{m_} + y", (lambda x, y: x * m_ + y)
        z = c.rng.randint(2, 10)
        return {"prompt": f"Define: {d}. What is ({a} {sym} {b}) {sym} {z}?", "answer": f(f(a, b), z), "slots": [a, b, z], "meta": {"def": d, "a": a, "b": b, "z": z},
                "steps": [f"{a} {sym} {b} = {f(a, b)}", f"{f(a, b)} {sym} {z} = {f(f(a, b), z)}"]}
    return {"prompt": f"Define: {d}. What is {a} {sym} {b}?", "answer": f(a, b), "slots": [a, b], "meta": {"def": d, "a": a, "b": b}, "steps": [f"{a} {sym} {b} = {f(a, b)}"]}


@family("group_induct", 7, ["multiple", "parity", "threshold"], "guess which group a new number belongs to", answer_open=False)
def group_induct(c, v):
    if v == "multiple":
        m = c.rng.randint(3, 7)
        inA = lambda x: x % m == 0
    elif v == "parity":
        inA = lambda x: x % 2 == 0
    else:
        t = c.rng.randint(30, 60)
        inA = lambda x: x >= t
    pool = list(range(4, 90))
    c.rng.shuffle(pool)
    A = [x for x in pool if inA(x)][:3]
    B = [x for x in pool if not inA(x)][:3]
    q = c.rng.choice([x for x in pool if x not in A + B])
    return {"prompt": f"Group A: {_lst(A)}. Group B: {_lst(B)}. Which group does {q} belong to?", "answer": "A" if inA(q) else "B", "slots": A + B + [q],
            "meta": {"A": A, "B": B, "q": q, "v": v}, "steps": ["infer rule"]}


# =============================================================== LEVEL 8: reading and composition
@family("passage_qa", 8, ["color", "owner", "count_total", "place"], "short passage with distractors", layout=True)
def passage_qa(c, v):
    a, b = c.names(2)
    o1, o2 = c.words(2)
    c1, c2 = c.color(), c.color()
    while c2 == c1:
        c2 = c.color()
    n1, n2 = c.rng.randint(2, 20), c.rng.randint(2, 20)
    p1, p2 = c.place(), c.place()
    if v == "color":
        s = f"{a} owns {_a(c1)} {c1} {o1}. {b} owns {_a(c2)} {c2} {o2}. What color is the {o2}?"
        ans = c2
    elif v == "owner":
        s = f"{a} owns {_a(c1)} {c1} {o1}. {b} owns {_a(c2)} {c2} {o2}. Who owns the {c1} one?"
        ans = a
    elif v == "count_total":
        s = f"{a} has {n1} {o1}s. {b} has {n2} {o1}s. {a} also has {_a(c1)} {c1} {o2}. How many {o1}s do they have together?"
        ans = n1 + n2
    else:
        s = f"{a} put the {o1} in the {p1}. {b} put the {o2} in the {p2}. Where did {b} put the {o2}?"
        ans = p2
    return {"prompt": s, "answer": ans, "slots": [a, b], "meta": {"v": v}, "steps": ["read passage"]}


@family("word_filter", 8, ["start_letter", "longer_than", "contains"], "count words in a list that meet a test")
def word_filter(c, v):
    ws = c.words(c.rng.randint(5, 7))
    if v == "start_letter":
        ch = c.rng.choice([w[0] for w in ws])
        a, q = sum(1 for w in ws if w[0] == ch), f"How many words start with the letter {ch}?"
    elif v == "longer_than":
        k = c.rng.randint(4, 7)
        a, q = sum(1 for w in ws if len(w) > k), f"How many words have more than {k} letters?"
    else:
        ch = c.rng.choice("aeiourst")
        a, q = sum(1 for w in ws if ch in w), f"How many words contain the letter {ch}?"
    return {"prompt": f"Words: {', '.join(ws)}. {q}", "answer": a, "slots": ws, "meta": {"ws": ws, "q": q}, "steps": ["scan list"]}


@family("kin_chain", 8, ["grandparent", "child_of_child", "yes_no_older"], "compose two relations", layout=True)
def kin_chain(c, v):
    a, b, d = c.names(3)
    if v == "grandparent":
        return {"prompt": f"{a} is the parent of {b}. {b} is the parent of {d}. Who is {d}'s grandparent?", "answer": a, "slots": [a, b, d], "meta": {"chain": [a, b, d]}, "steps": ["compose"]}
    if v == "child_of_child":
        return {"prompt": f"{d} is the child of {b}. {b} is the child of {a}. Who is {a}'s grandchild?", "answer": d, "slots": [a, b, d], "meta": {"chain": [a, b, d]}, "steps": ["compose"]}
    x, y = c.rng.sample([a, b, d], 2)
    order = [a, b, d]
    return {"prompt": f"{a} is the parent of {b}. {b} is the parent of {d}. Is {x} older than {y}?", "answer": "yes" if order.index(x) < order.index(y) else "no",
            "slots": [a, b, d], "meta": {"chain": order, "x": x, "y": y}, "steps": ["parents are older"]}


@family("story_chain3", 8, ["three_step", "compare_after"], "three chained steps with a question at the end", layout=True)
def story_chain3(c, v):
    n, nn = c.name(), c.noun()
    x, y, z, w = c.rng.randint(20, 90), c.rng.randint(2, 20), c.rng.randint(2, 15), c.rng.randint(2, 9)
    r1 = x + y
    r2 = r1 - z
    if v == "three_step":
        a = r2 * w
        p = f"{n} had {x} {nn}, got {y} more, then lost {z}. Then {n} bought {w} times as many as were left. How many {nn} did {n} buy?"
        return {"prompt": p, "answer": a, "slots": [x, y, z, w], "meta": {"x": x, "y": y, "z": z, "w": w}, "steps": [f"{x}+{y}={r1}", f"{r1}-{z}={r2}", f"{r2}*{w}={a}"]}
    other = c.rng.randint(10, 150)
    p = f"{n} had {x} {nn}, got {y} more, then lost {z}. A friend has {other}. Who has more now, {n} or the friend?"
    return {"prompt": p, "answer": n if r2 > other else ("friend" if r2 < other else "same"), "slots": [x, y, z, other],
            "meta": {"x": x, "y": y, "z": z, "other": other, "n": n}, "steps": [f"{x}+{y}-{z}={r2}", f"compare {r2} {other}"],
            "accepted": [n if r2 > other else ("friend" if r2 < other else "same")]}


# =============================================================== added after PR #29 structure findings
OPS = ["add", "sub", "mul", "div"]
OPSYM = {"add": "+", "sub": "-", "mul": "*", "div": "/"}


def _step_phrase(c, op, k, nn):
    return {"add": c.pick("add", ["gets {k} more", "is given {k} more", "picks up {k} more"]),
            "sub": c.pick("sub", ["gives away {k}", "loses {k}", "uses up {k}"]),
            "mul": c.pick("mul", ["ends up with {k} times as many", "multiplies the amount by {k}"]),
            "div": c.pick("div", ["splits them into {k} equal groups and keeps one", "keeps one of {k} equal shares"])}[op].format(k=k)


@family("chain_ops", 6, ["two_step", "three_step", "sub_second", "sub_first"], "chained steps: every operation in every position", layout=True)
def chain_ops(c, v):
    n, nn = c.name(), c.noun()
    n_steps = 3 if v == "three_step" else 2
    while True:
        ops = [c.rng.choice(OPS) for _ in range(n_steps)]
        if v == "sub_second":
            ops[1] = "sub"
        if v == "sub_first":
            ops[0] = "sub"
        cur = c.rng.randint(8, 60 + 120 * (c.diff > 0))
        x0, tr, ks, ok = cur, [], [], True
        for op in ops:
            if op == "div":
                divs = [d for d in range(2, 9) if cur % d == 0 and cur // d >= 2]
                if not divs:
                    ok = False
                    break
                k = c.rng.choice(divs)
            elif op == "mul":
                k = c.rng.randint(2, 6)
            elif op == "sub":
                if cur <= 3:
                    ok = False
                    break
                k = c.rng.randint(1, min(40, cur - 1))
            else:
                k = c.rng.randint(2, 40)
            new = {"add": cur + k, "sub": cur - k, "mul": cur * k, "div": cur // k}[op]
            tr.append(f"{cur} {OPSYM[op]} {k} = {new}")
            ks.append(k)
            cur = new
        if ok and cur <= 5000:
            break
    parts = [f"{n} has {x0} {nn}."]
    for op, k in zip(ops, ks):
        parts.append(f"Then {n} {_step_phrase(c, op, k, nn)}.")
    p = " ".join(parts) + f" How many {nn} does {n} have at the end?"
    return {"prompt": p, "answer": cur, "slots": [x0] + ks, "meta": {"x0": x0, "ops": ops, "ks": ks}, "steps": tr}


@family("distance_units", 6, ["distance", "speed", "time"], "speed, distance and time with units written out", layout=True)
def distance_units(c, v):
    unit, tu = c.rng.choice([("km", "hours"), ("miles", "hours"), ("meters", "minutes")])
    sp, t = c.rng.randint(2, 12) * (10 if unit != "meters" else 5), c.rng.randint(2, 9)
    d = sp * t
    who = c.name()
    if v == "distance":
        return {"prompt": f"{who} moves at a steady {sp} {unit} per {tu[:-1]}. How far does {who} go in {t} {tu}?", "answer": d, "slots": [sp, t], "meta": {"sp": sp, "t": t}, "steps": [f"{sp} * {t} = {d}"]}
    if v == "speed":
        return {"prompt": f"{who} covers {d} {unit} in {t} {tu} at a steady pace. How many {unit} per {tu[:-1]} is that?", "answer": sp, "slots": [d, t], "meta": {"d": d, "t": t}, "steps": [f"{d} / {t} = {sp}"]}
    return {"prompt": f"{who} moves at a steady {sp} {unit} per {tu[:-1]}. How many {tu} does {who} need to go {d} {unit}?", "answer": t, "slots": [sp, d], "meta": {"sp": sp, "d": d}, "steps": [f"{d} / {sp} = {t}"]}


@family("table_calc", 6, ["row_total", "column_sum", "cost"], "read a small table laid out in rows", layout=False)
def table_calc(c, v):
    k = 3
    ks = c.words(k)
    qty = [c.rng.randint(2, 9) for _ in range(k)]
    price = [c.rng.randint(2, 12) for _ in range(k)]
    rows = " ".join(f"Row {w}: qty {q}, price {p}." for w, q, p in zip(ks, qty, price))
    i = c.rng.randrange(k)
    if v == "row_total":
        return {"prompt": f"{rows} What is the total cost of row {ks[i]}?", "answer": qty[i] * price[i], "slots": ks + qty + price, "meta": {"ks": ks, "qty": qty, "price": price, "i": i, "v": v}, "steps": [f"{qty[i]} * {price[i]}"]}
    if v == "column_sum":
        return {"prompt": f"{rows} What is the total qty over all rows?", "answer": sum(qty), "slots": ks + qty + price, "meta": {"ks": ks, "qty": qty, "price": price, "v": v}, "steps": [f"sum {qty}"]}
    return {"prompt": f"{rows} What is the total cost of all rows?", "answer": sum(a * b for a, b in zip(qty, price)), "slots": ks + qty + price, "meta": {"ks": ks, "qty": qty, "price": price, "v": v}, "steps": ["sum of qty*price"]}
