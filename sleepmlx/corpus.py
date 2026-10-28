"""Text helpers and the Diary index (port of sleepb.py's Diary: word-boundary lookup and a small BM25)."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Dict, List

STOP = set("the a an of in is to and where who does what which for at on by with was are do did live lives name s".split())


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^0-9a-z]+", " ", str(s).lower().replace("’", "'").replace("'s", "")).split())


def pat(s: str):
    return re.compile(r"(?<!\w)" + re.escape(s.lower()) + r"(?!\w)")


def tokens(s: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", s.lower().replace("’", "'").replace("'s", ""))


def has_ans(target: str, ans: str) -> bool:
    return target.lower() in ans.lower()


class Diary:
    """User turns of the whole diary. Callers filter by day number."""

    def __init__(s, week: dict, who: str = ""):
        s.who = who.lower()   # every turn here is this person's (helper runs are kept apart in week["helper_runs"]): occurs(who) is all of them
        s.turns = [dict(t, i=i) for i, t in enumerate(x for x in week["diary"] if x["role"] == "user")]
        s.low = [t["text"].lower() for t in s.turns]
        s.occ_cache: Dict[str, frozenset] = {}
        s.tf: List[Counter] = []
        s.post = defaultdict(list)
        s.sc: dict = {}
        for i, t in enumerate(s.turns):
            c = Counter(w for w in tokens(t["text"]) if w not in STOP)
            s.tf.append(c)
            for w in c:
                s.post[w].append(i)
        s.dl = [sum(c.values()) for c in s.tf]
        s.avg = max(sum(s.dl) / max(len(s.dl), 1), 1e-9)

    def occurs(s, string: str) -> frozenset:
        k = string.lower()
        if k == s.who and k not in s.occ_cache:
            s.occ_cache[k] = frozenset(range(len(s.turns)))
        if k not in s.occ_cache:
            p = pat(k)
            s.occ_cache[k] = frozenset(i for i, x in enumerate(s.low) if p.search(x))
        return s.occ_cache[k]

    def containing(s, a: str, b: str, upto: int = 10 ** 6) -> List[int]:
        return sorted(i for i in s.occurs(a) & s.occurs(b) if s.turns[i]["day"] <= upto)

    def label(s, idxs, maxc: int = 500) -> str:
        return "\n".join("[Day %s] %s" % (s.turns[i]["day"], s.turns[i]["text"][:maxc]) for i in idxs)

    def search(s, q: str, k: int = 8, upto=None) -> List[int]:
        key = (q, k, upto)
        if upto is not None and key in s.sc:
            return s.sc[key]
        ok = (lambda i: True) if upto is None else (lambda i: s.turns[i]["day"] <= upto)
        n, scores = sum(1 for i in range(len(s.turns)) if ok(i)), defaultdict(float)
        for w in set(tokens(q)) - STOP:
            ps = [i for i in s.post.get(w, ()) if ok(i)]
            df = len(ps)
            if not df:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for i in ps:
                tf = s.tf[i][w]
                scores[i] += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * s.dl[i] / s.avg))
        top = sorted(scores, key=lambda i: (-scores[i], i))[:k]
        if upto is not None:
            s.sc[key] = sorted(top)
        return sorted(top)
