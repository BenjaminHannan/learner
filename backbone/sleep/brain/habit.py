"""Habit spotter (PREREG-habit1.md): a nightly pass that looks ACROSS days of the diary for repeats.

A routine in the week is never stated as a habit: Sam mentions one occasion at a time ("grabbing coffee with Vresaglom at Relozal
tonight") on 3 or 4 different days. The day tagger reads one message at a time, so it can only see one-off events; on Qwen3.6 it turned
1 of the 20 routines into a person-place item (addendum 12, routine 30). The spotter counts, over the diary so far, the pairs of candidate
names that come up together in one user turn on >= HABIT_MIN_DAYS different days and that no item links yet, shows the model one message
per day, and asks whether it is a habit. A yes ("Sam usually ... A ... B.") becomes an item whose fact is that sentence; the rest of the
night (refresh, dreams, gist dreams, training) treats it like any other item.

--habit ctrl is the equal-question control: the same prompt and the same number of questions a night, asked about pairs that came up
together on ONE day only (no repetition to spot). Pure Python, no torch: habit_probe.py imports it too."""
import itertools
import random
import re
from collections import defaultdict

HABIT_MIN_DAYS = 2  # distinct days a pair must share before it is asked about
HABIT_CAP = 40  # questions a night (not scaled by the work scale)
HABIT_CTX_DAYS = 6  # messages shown: the latest turn of each of the pair's most recent days
HABIT_SYS = "You are a careful assistant that studies facts."


def pair_days(diary, d, vocab, pat):
    """{(norm a, norm b) sorted: [turn index, ...]} over user turns of days <= d; names = vocab {norm: display}; pat(norm) -> compiled
    whole-word pattern (sleepb.pat). A turn counts each unordered pair once."""
    pats = {n: pat(n) for n in vocab}
    out = defaultdict(list)
    for t in diary.turns:
        if t["day"] > d:
            continue
        low = diary.low[t["i"]]
        hits = sorted({n for n, p in pats.items() if p.search(low)})
        for a, b in itertools.combinations(hits, 2):
            out[(a, b)].append(t["i"])
    return out


def linked(items, a, b):
    return any(k in items and not items[k].dead for k in ((a, b), (b, a)))


def candidates(diary, pt, items, dropped, asked, min_days=HABIT_MIN_DAYS, cap=HABIT_CAP):
    """Spot: pairs on >= min_days distinct days, unlinked, not dropped, and seen on more days than when last asked; most days first,
    then earliest first turn. Returns [(pair, [turn idx of the latest turn per day, chronological])]."""
    out = []
    for p, idx in pt.items():
        days = sorted({diary.turns[i]["day"] for i in idx})
        if len(days) < min_days or linked(items, *p) or p in dropped or p[::-1] in dropped or asked.get(p, 0) >= len(days):
            continue
        last = {diary.turns[i]["day"]: i for i in sorted(idx)}
        out.append((p, [last[x] for x in days][-HABIT_CTX_DAYS:], len(days), min(idx)))
    out.sort(key=lambda c: (-c[2], c[3], c[0]))
    return [(p, ctx) for p, ctx, _, _ in out[:cap]]


def control(diary, pt, items, dropped, asked, n, rng):
    """Control: n pairs that came up together on exactly ONE day (unlinked, not dropped, not asked before), drawn with rng."""
    pool = sorted(p for p, idx in pt.items() if len({diary.turns[i]["day"] for i in idx}) == 1 and not linked(items, *p)
                  and p not in dropped and p[::-1] not in dropped and p not in asked)
    pick = rng.sample(pool, min(n, len(pool)))
    return [(p, [max(pt[p])]) for p in pick]


def habit_user(ctx, a, b, n):
    """The question (user text). ctx: the labelled messages; n: distinct days."""
    days = f"{n} different days" if n > 1 else "1 day"
    return (f"Messages Sam sent in chat on {days}:\n{ctx}\n\n\"{a}\" and \"{b}\" come up together in these messages. Is this a habit of Sam's, "
            f"something Sam keeps doing again and again that involves both of them? If yes, reply with one sentence that starts with \"Sam usually\" and names both \"{a}\" and \"{b}\". If not, reply only: no")


def parse_habit(txt, a, b):
    """The reply -> the habit sentence, or None (a no, or a sentence without "usually" or without both names as whole words)."""
    lines = [x.strip(" \t*\"'`") for x in str(txt or "").strip().splitlines() if x.strip(" \t*\"'`")]
    if not lines or re.match(r"(?:no|none|nope|not)(?:$|[^\w])", lines[0].lower()):
        return None
    s = lines[0][:240]
    low = s.lower()
    if "usually" not in low or not all(re.search(r"(?<!\w)" + re.escape(x.lower()) + r"(?!\w)", low) for x in (a, b)):
        return None
    return s if s.endswith(".") else s + "."


def order(sentence, a, b):
    """(first, second) of a and b by where they appear in the sentence."""
    low = sentence.lower()
    return (a, b) if low.find(a.lower()) <= low.find(b.lower()) else (b, a)


def new_rng(seed):
    return random.Random(seed + 41)
