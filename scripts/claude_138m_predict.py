#!/usr/bin/env python3
"""Merge 138m -- build the M1 section of predicted_moves138m.json from a
PILOT run of claude_138m_l1.py (own/head/l/m rows in one dir).

Every case whose 138m record differs from its line head's record becomes a
predicted move, keyed by id, with the exact 138m record expected
(expect_m = claude_138m_l1._cmp of the pilot's m row) and a category that
says which layer wins the turn and why:

  224_glue        the head gave the glued decline (HONEST_DECLINE +
                  DECLINE_SUFFIX); 224/224c (outermost) swap it for their
                  one sentence.
  224_on_base     138l's base gates (212 statement gate / 216 cue gate)
                  send the turn to the glued decline where the head (on
                  138i) answered from the D8 route; 224 then swaps the
                  glue. The name line (219) never sees D8 on these turns.
  base138l        138m == 138l on the turn: the head's older base (138i)
                  and 138l differ (212/216 gates, 138j 188 statement
                  fallback beats 224's S1, 138j unknown-name reply, 154f
                  negation handling, 138j USER-key wording).
  nameline        the 219/230/230b/230c name line answers a D8 user-name
                  turn from the notebook on another line's case (the head
                  of that line has no 219); the name line wins.
  identity        the 227/227b/227c identity gate (ahead of 187 and the
                  138i/138l self routes) answers an identity turn on a
                  234 case; the identity line wins.
  smalltalk234    234's fixed reply wins on a non-234 case.
usage: claude_138m_predict.py --pilot DIR --out predicted_moves138m.json
       [--merge EXISTING.json]   (keeps the other sections of EXISTING)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_138m_l1 as L1  # noqa: E402
import claude_identity227c as C227C  # noqa: E402 (sheet texts, read-only)
import claude_loop234_agent as A234  # noqa: E402 (fixed reply, read-only)
import fable_decline224 as DEC  # noqa: E402 (224 sentences, read-only)
import fable_loop138_agent as L138  # noqa: E402 (DECLINE_SUFFIX)
import fable_self105 as S105  # noqa: E402 (HONEST_DECLINE)

GLUE = S105.HONEST_DECLINE + L138.DECLINE_SUFFIX
S224 = set(DEC.NEW_SENTENCES224.values())
F234 = {A234.FIXED_234, A234.GREET_PREFIX_234 + A234.FIXED_234}
SHEET = set(C227C.SHEET_227C.values()) | {"My name is Premonition."}
NAME_PREFIXES = ("Yes. Your name is ", "Your name is ", "No. Your name is ")


def _cat(h: str, m: str, l_: str) -> str:
    if m in F234 and h not in F234:
        return "smalltalk234"
    if m in S224 and h == GLUE:
        return "224_glue"
    if m in S224 and l_ == GLUE:
        return "224_on_base"
    if m == l_:
        return "base138l"
    if m.startswith(NAME_PREFIXES):
        return "nameline"
    if any(x in m for x in SHEET):
        return "identity"
    return "UNCLASSIFIED"


def _as_text(r) -> str:
    return r if isinstance(r, str) else " ".join(r)


def build_m1(d: Path) -> dict:
    out: dict = {}
    for piece in L1.PIECES:
        hf = d / f"{piece}-head.json"
        if not hf.exists():
            hf = d / f"{piece}-own.json"
        H = {r["id"]: r for r in json.loads(hf.read_text())}
        M = {r["id"]: r for r in json.loads((d / f"{piece}-m.json")
                                            .read_text())}
        Lr = {r["id"]: r for r in json.loads((d / f"{piece}-l.json")
                                             .read_text())}
        pp = {}
        for cid, h in H.items():
            m, l_ = M[cid], Lr[cid]
            if L1._cmp(piece, h) == L1._cmp(piece, m):
                continue
            if piece in ("224c", "233"):
                cats = [_cat(_as_text(h["reply"]), _as_text(m["reply"]),
                             _as_text(l_["reply"]))]
                turns = [cid]
            else:
                cats, turns = [], []
                for i, t in enumerate(h["turns"]):
                    if (h["lines"][i] != m["lines"][i]
                            or h["writes"][i] != m["writes"][i]):
                        cats.append(_cat(" ".join(h["lines"][i]),
                                         " ".join(m["lines"][i]),
                                         " ".join(l_["lines"][i])))
                        turns.append(f"t{i}")
            pp[cid] = {"category": sorted(set(cats)), "turns": turns,
                       "expect_m": L1._cmp(piece, m)}
        out[piece] = pp
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--merge", default=None)
    a = ap.parse_args(argv)
    base = (json.loads(Path(a.merge).read_text()) if a.merge
            and Path(a.merge).exists() else {})
    m1 = build_m1(Path(a.pilot))
    base["m1"] = m1
    tally: dict = {}
    for piece, pp in m1.items():
        for cid, v in pp.items():
            for c in v["category"]:
                tally[f"{piece}:{c}"] = tally.get(f"{piece}:{c}", 0) + 1
    base["m1_tally"] = tally
    Path(a.out).write_text(json.dumps(base, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    n = sum(len(v) for v in m1.values())
    print(f"m1 predicted moves: {n}")
    print(json.dumps(tally, indent=1))
    bad = [k for k in tally if k.endswith("UNCLASSIFIED")]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
