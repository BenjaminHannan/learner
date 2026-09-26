#!/usr/bin/env python3
"""lis-320 seeds plus a correction whose owner was named only earlier (reading thread, 2026-09-26; ADDENDUM-5).
New file; claude_lis320_seed.py is sealed by y1t and stays unchanged (its seeds are byte-identical without this file).

Gap found by the Wrong answers thread (20:28 UTC): claude_lis320_seed.correct() always puts the owner's name in the
correction turn (:345), so lis-320 never practised the owner_not_span case, 14 of lis-319f's 60 correction misses
(claude-lis319k VERIFY.md:17-21). New intent correct_ref = correct() + backref(): a CORRECT fact about a person named in
the last HIST_TURNS turns, referred to only by pronoun (when that person is the only one of that gender named in view)
or by role word, never by name; the old value is named about half the time. One fact per turn. Weight 1.5.
Everything else (world, names, other intents and weights, ask-back) is claude_lis320_seed's.

python -B scripts/claude_lis320_seed_cr.py --seed 324 --n 6000 --ask-back --avoid-names F --avoid-hashes H --out S.jsonl
python -B scripts/claude_lis320_seed_cr.py --selftest
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis320_seed as S  # noqa: E402

CR_W = {"correct_ref": 1.5}
S.INTENT_GLOSS["correct_ref"] = ("the user corrects something said earlier about a person they named earlier: the new "
                                 "value replaces the old one; the user refers to that person only in the way given "
                                 "(never by name)")


class DialogCR(S.Dialog):
    def correct_ref(self):
        r = self.rng
        vis = self.visible_named()
        opts = []
        for n in sorted(vis):
            p = self.by[n]
            if not any((n, rel) in self.stored and rel in S.CORRECT_RELS and (n, rel) not in self.corrected
                       for rel in S.CORRECT_RELS):
                continue
            if len([m for m in vis if self.by[m]["gender"] == p["gender"]]) == 1:
                opts.append((n, "pronoun"))
            if n in self.intro and self.intro[n] >= self.k() - S.HIST_TURNS:
                opts.append((n, "role"))
        if not opts:
            return False
        n, kind = r.choice(opts)
        p = self.by[n]
        rel = r.choice(sorted(rel for rel in S.CORRECT_RELS if (n, rel) in self.stored and (n, rel) not in self.corrected))
        old = self.stored[(n, rel)]
        new = S.value_for(rel, self.W, self.taken)
        name_old = r.random() < 0.5
        f = S.fact(n, rel, new, "CORRECT", old if name_old else None)
        self.stored[(n, rel)] = new
        self.corrected.add((n, rel))
        if kind == "pronoun":
            ref = {"kind": "pronoun", "gender": p["gender"],
                   "words": ["she", "her", "hers"] if p["gender"] == "f" else ["he", "him", "his"]}
            how = "only by a " + ("she/her" if p["gender"] == "f" else "he/him/his") + " pronoun"
        else:
            ref = {"kind": "role", "role": p["role"], "words": [S.role_word(p["role"])]}
            how = f"only by the role word \"{S.role_word(p['role'])}\" (as the user's {S.role_word(p['role'])})"
        lines = [self.fact_line(f, subject=f"{n}, referred to {how}"),
                 f"old value said earlier: \"{old}\" ("
                 + ("the message must name the old value too)" if name_old else "the message must NOT name it)"),
                 r.choice(["why: the old value was true before and has changed since (moved, new job, renamed, "
                           "and so on); the user updates it",
                           "why: the old value was said by mistake; the user fixes it"])]
        self.add("correct_ref", S.frame("CORRECT", [f]), [new] + ([old] if name_old else []), lines,
                 must_not=[n] + ([] if name_old else [old]), reply_must_not=[n], ref=ref)
        return True

    def run(self, n_turns):
        r = self.rng
        self.teach()
        W = S.WEIGHTS | (S.ASK_BACK_W if self.ask_back else {}) | CR_W
        while len(self.turns) < n_turns:
            ks = list(W)
            kind = r.choices(ks, [W[x] for x in ks])[0]
            fn = getattr(self, kind, None)
            ok = fn() if fn else self.lookalike(kind)
            if not ok:
                self.teach() or self.smalltalk()
        return {"dialog_id": self.id, "people": self.people, "opener": r.random() < 0.5,
                "proper_values": sorted(v for v in self.taken if v[:1].isupper()),
                "turns": self.turns}


def make_seeds(seed, n, avoid=frozenset(), ask_back=False):
    out = []
    for i in range(n):
        rng = random.Random(f"lis320cr-{seed}-{i}")
        d = DialogCR(f"s320cr-{seed}-{i:05d}", rng, set(avoid))
        d.ask_back = ask_back
        out.append(d.run(rng.randint(6, 8)))
    return out


def selftest():
    a = make_seeds(5, 400, ask_back=True)
    c = Counter(t["intent"] for d in a for t in d["turns"])
    assert c["correct_ref"] >= 40 and c["correct"] > 0 and c["backref"] > 0, c
    for d in a:
        names = [p["name"] for p in d["people"]]
        for t in d["turns"]:
            if t["intent"] != "correct_ref":
                continue
            f = t["gold"]["facts"][0]
            o = f["owner"]
            assert len(t["gold"]["facts"]) == 1 and f["mode"] == "CORRECT" and o != "me"
            assert o not in t["must"] and o in t["must_not"] and o in t["reply_must_not"]
            assert ("old" in f) == (f.get("old") in t["must"])
            vis_turns = d["turns"][max(0, t["k"] - 1 - S.HIST_TURNS): t["k"] - 1]
            assert any(o in u["must"] for u in vis_turns), "owner not named in view"
            if t["ref"]["kind"] == "pronoun":
                g = next(p["gender"] for p in d["people"] if p["name"] == o)
                vis = {n for u in vis_turns for n in u["must"] if n in names}
                assert [n for n in vis if next(p["gender"] for p in d["people"] if p["name"] == n) == g] == [o]
    b = S.make_seeds(321, 60, ask_back=True)       # the sealed seeder is untouched by importing this file
    assert not any(t["intent"] == "correct_ref" for d in b for t in d["turns"])
    print("seed_cr selftest OK:", len(a), "dialogs;", {k: c[k] for k in ("correct_ref", "correct", "backref")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=323)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--out")
    ap.add_argument("--avoid-names")
    ap.add_argument("--avoid-hashes")
    ap.add_argument("--ask-back", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    avoid = set()
    if a.avoid_names:
        avoid = {x.strip().lower() for x in Path(a.avoid_names).read_text().splitlines() if x.strip()}
    if a.avoid_hashes:
        S.AVOID_HASHES.update(x.strip() for x in Path(a.avoid_hashes).read_text().splitlines() if x.strip())
    seeds = make_seeds(a.seed, a.n, avoid, ask_back=a.ask_back)
    Path(a.out).write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in seeds), encoding="utf-8")
    c = Counter(t["intent"] for d in seeds for t in d["turns"])
    print(json.dumps({"dialogs": len(seeds), "turns": sum(c.values()), "intents": dict(sorted(c.items()))}))


if __name__ == "__main__":
    sys.exit(main())
