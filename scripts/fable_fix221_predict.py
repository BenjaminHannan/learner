#!/usr/bin/env python3
"""Exp 221 -- P3 PREDICTED MOVES, worked out before any agent run.

Pure function over the frozen suite INPUTS (rt136 cases, rt143 cases,
sessions152 sessions, the four bench splits) and the relation table. No
agent is built, no notebook is touched, no sealed output row is read.

A case is a PREDICTED MOVE CANDIDATE when one of its question turns Q
(text ending in "?") satisfies:

  (A) table reading: fable_fix221_tableask.unique_reading221(Q) is not
      None. The mixin can only change such a turn when the 138i base
      misses it (base_missed221), which this text-only rule cannot see, so
      (A) is a superset of the real (a)-moves.
  (B) key re-point: Q has a single-hop base shape the 138i ears parse as
      an ask on one key k ("Who/What/Where is X's R?", "... is my R?",
      "Who/What is the R of X?"), k is in a table group G, and some teach
      turn of the same case touches G through a different key (possessive
      / "my" surface of another key in G, or any table teach template of
      G or of a narrower relation). Superset of the real (b)-moves.

  (C) live reverse reply: fable_fix153_reverse.parse_reverse(Q) is not
      None and both spans pass 153's own _simple gate (the 153 answer gets the label; its "I don't know anyone
      whose" line may be widened through the table group).

After the run every moved case must be in this list (an unpredicted move
is a P3 FAIL); listed cases that do not move are reported, not failed.

Run: python3 -B scripts/fable_fix221_predict.py --out <json>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent

import fable_fix153_reverse as R153  # noqa: E402 (parser, read-only)
import fable_fix221_tableask as T  # noqa: E402

BENCH = [
    ("new_121_4hop", ROOT / "data/open/bench121/fable_edit121_4hop.jsonl"),
    ("old_s2fresh_4hop",
     ROOT / "data/open/bench103/fable_edit103_s2fresh_4hop.jsonl"),
    ("edit200", ROOT / "data/open/bench65/fable_edit_200.jsonl"),
    ("bench132_4hop", ROOT / "data/open/bench132/fable_edit132_4hop.jsonl"),
]

_Q_POSS = re.compile(r"^(?:who|what|where)(?: is|'s) ([^?']+?)'s ([a-z][a-z ]*?)\?$",
                     re.I)
_Q_MY = re.compile(r"^(?:who|what|where) is my ([a-z][a-z ]*?)\?$", re.I)
_Q_OF = re.compile(r"^(?:who|what) is the ([a-z][a-z ]*?) of ([^?']+?)\?$",
                   re.I)
_T_POSS = re.compile(r"'s ([a-z][a-z ]*?) (?:is|are) ", re.I)
_T_MY = re.compile(r"^my ([a-z][a-z ]*?) (?:is|are) ", re.I)


def _teach_patterns(tb: T.Table221) -> list[tuple[str, str, re.Pattern]]:
    """(relation, key, regex): generic-family teaches write the surface's
    own key; relation-specific (verb/bench) teaches -> key '*' (unknown)."""
    data = json.loads(tb.path.read_text(encoding="utf-8"))
    gen = data["generic_patterns"]
    out = []
    for r in data["relations"]:
        pats = []
        for fam in r["generic"]:
            pats += [(True, p) for p in gen[fam].get("teach", [])]
        pats += [(False, p) for p in r["teach"]]
        surfaces = [r["name"].replace("_", " ")] + list(r["aliases"])
        for is_gen, p in pats:
            t = p["t"]
            for s in (surfaces if "{R}" in t else [None]):
                c = t.replace("{R}", s) if s else t
                k = T.key221(s) if (is_gen and s) else "*"
                out.append((r["name"], k, T.compile_template221(c)))
    return out


def teach_touches(sent: str, tb: T.Table221, tpats) -> set[tuple[str, str]]:
    """(relation, key-or-'*') pairs a teach sentence could write."""
    s = " ".join(str(sent).split())
    out = set()
    for m in list(_T_POSS.finditer(s)) + list(_T_MY.finditer(s)):
        k = T.key221(m.group(1))
        rel = tb.key2rel.get(k) or tb.invkey2rel.get(k)
        if rel:
            out.add((rel, k))
    body = s.rstrip(" .?!")
    for rel, k, rx in tpats:
        if rx.fullmatch(body):
            out.add((rel, k))
    return out


def q_base_key(q: str) -> str | None:
    s = " ".join(str(q).split())
    for rx, gi, xi in ((_Q_POSS, 2, 1), (_Q_MY, 1, None), (_Q_OF, 1, 2)):
        m = rx.match(s)
        if m and (xi is None or T._slot_ok(m.group(xi))):
            return T.key221(m.group(gi))
    return None


def predict_case(qs: list[str], teaches: list[str], tb, tpats) -> list[dict]:
    touches = set()
    for t in teaches:
        touches |= teach_touches(t, tb, tpats)
    out = []
    for q in qs:
        rd = T.unique_reading221(q, tb)
        if rd is not None:
            out.append({"turn": q, "rule": "A", "reading": {
                k: rd[k] for k in ("rel", "kind", "X", "Y")}})
        pr = R153.parse_reverse(q)
        if pr is not None and R153._simple(pr[0]) and R153._simple(pr[1]):
            out.append({"turn": q, "rule": "C", "reverse153": list(pr)})
        k = q_base_key(q)
        if k is None:
            continue
        g = tb.key2rel.get(k) or tb.invkey2rel.get(k)
        if g is None:
            continue
        fk = set(tb.forward_keys(g))
        narrower = set(tb.rels[g].get("narrower", []))
        hit = [(r, kk) for r, kk in touches
               if (r == g or r in narrower or kk in fk)
               and (kk == "*" or kk != k)]
        if hit:
            out.append({"turn": q, "rule": "B", "base_key": k, "group": g,
                        "teach_touch": sorted(f"{r}:{kk}" for r, kk in hit)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    tb = T.get_table221()
    tpats = _teach_patterns(tb)
    pred: dict = {"rule": __doc__.split("After the run")[0].strip(),
                  "suites": {}}

    cases = json.loads((ROOT / "artifacts/fable-redteam136-20260922/"
                        "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    teaches = [c["text"] for c in cases if not c["text"].strip().endswith("?")]
    rows = []
    for c in cases:  # rt136: one fresh daemon per case (single turn)
        if c["text"].strip().endswith("?"):
            for p in predict_case([c["text"]], [], tb, tpats):
                rows.append({"id": c["id"], **p})
    pred["suites"]["rt136"] = rows

    s143 = json.loads((ROOT / "artifacts/fable-redteam143-20260922/"
                       "fable_redteam143_cases.json").read_text(
        encoding="utf-8"))
    rows = []
    for c in s143["cases"]:
        for p in predict_case([c["question"]], c.get("teaches", []), tb,
                              tpats):
            rows.append({"id": c["id"], **p})
    pred["suites"]["rt143"] = rows

    import fable_session152_sessions as S152  # noqa: E402 (data only)
    rows = []
    for s in S152.SESSIONS:
        texts = [t["text"] for t in s["turns"]]
        teaches = [t for t in texts if not t.strip().endswith("?")]
        for i, t in enumerate(texts):
            if t.strip().endswith("?"):
                for p in predict_case([t], teaches[:], tb, tpats):
                    rows.append({"id": f"{s['id']}#{i}", **p})
    pred["suites"]["sessions152"] = rows

    rows = []
    for stag, path in BENCH:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            teaches = [t["sentence_en"] for t in it["taught"]]
            for p in predict_case([it["question"]], teaches, tb, tpats):
                rows.append({"id": it["id"], "split": stag, **p})
    pred["suites"]["bench"] = rows
    pred["counts"] = {k: len({r["id"] for r in v})
                      for k, v in pred["suites"].items()}
    Path(args.out).write_text(json.dumps(pred, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(json.dumps(pred["counts"]))
    for k, v in pred["suites"].items():
        for r in v:
            print(k, r["id"], r["rule"], r["turn"][:90],
                  r.get("reading") or r.get("teach_touch")
                  or r.get("reverse153"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
