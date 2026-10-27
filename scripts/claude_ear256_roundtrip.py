#!/usr/bin/env python3
"""Exp 256 -- the round-trip table (brief 2c), built on the 138l BASE.

For every relation of relation_table_v1 x {named, first, named_chain, my_chain,
named_hop1, my_hop1}, in a fresh 138l work dir:
  named       teach "{S}'s {r} is {V}."  must store exactly (S, R, V) and nothing else;
              the canonical question must answer V.
  first       teach "My {r} is {V}."     must store exactly (USER, R, V); "What is my {r}?" -> V.
  named_chain setup "Tamsel's sister is Wenna Farrow." then the named teach for Wenna Farrow;
              "What is Tamsel's sister's {r}?" -> V.
  my_chain    setup "My sister is Wenna Farrow." then the named teach; "What is my sister's {r}?" -> V.
  named_hop1  (person relations only) "Tamsel's {r} is Wenna Farrow." + "Wenna Farrow's city is
              Dovecote." ; "What is Tamsel's {r}'s city?" -> Dovecote.
  my_hop1     (person relations only) "My {r} is Wenna Farrow." + the city teach;
              "What is my {r}'s city?" -> Dovecote.
Replies must not contain the raw key "USER". Template candidates are tried in order
(claude_ear256_route); the first that passes is recorded.

python claude_ear256_roundtrip.py --out artifacts/claude-earloop256-20260922/roundtrip.json --work DIR
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_ear256_route as R  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402
import fable_marks123_all as M  # noqa: E402

REPO = SCRIPTS.parent
BASE_AGENT = "scripts/claude_loop138l_agent.py"
BASE_CFG = "artifacts/claude-merge138l-20260922/loop138l-config.json"
TABLE = REPO / "artifacts/claude-relationtable-20260922/relation_table_v1.json"

VALUES = {"person": "Ivo Marr", "place": "Kellbridge", "organization": "Oakly Farms",
          "work": "Blue Rain", "date": "12 May", "number": "34", "language": "Norrish",
          "literal": "teal"}
SUBJ = "Tamsel"
MID = "Wenna Farrow"


class Runner:
    def __init__(self, work: Path):
        _, self.dcls, _, _ = M.load_agent(str(REPO / BASE_AGENT))
        self.cfg = M.load_base_cfg(str(REPO / BASE_CFG))
        self.work = work
        self.n = 0

    def dialog(self, turns):
        root = self.work / f"d{self.n:04d}"
        self.n += 1
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = M.make_daemon(self.dcls, copy.deepcopy(self.cfg), root)
        out = []
        for j, t in enumerate(turns):
            before = set(L90.notebook_triples(d.loop.nb))
            f = root / "inbox" / f"m{j:02d}.txt"
            f.write_text(t, encoding="utf-8")
            d.process_file(f)
            rep = (root / "outbox" / f"m{j:02d}.txt").read_text(encoding="utf-8").strip()
            after = set(L90.notebook_triples(d.loop.nb))
            out.append(dict(turn=t, reply=rep, new=sorted(after - before), gone=sorted(before - after)))
        shutil.rmtree(root, ignore_errors=True)
        return out


def answered(reply: str, v: str) -> bool:
    low = reply.lower()
    return v.lower() in low and not low.startswith(("i don't know", "i do not know")) \
        and "USER" not in reply


def stored_exactly(step, s, rel, v) -> bool:
    return step["new"] == [(s, rel, v)] and not step["gone"] and "USER" not in step["reply"]


def try_row(run, setup, teach_tpls, teach_fmt, expect, ask_tpls, ask_fmt, value):
    """setup: list of plain turns. teach candidates x ask candidates, first pass wins."""
    tried = []
    for tt in teach_tpls:
        teach = tt.format(**teach_fmt)
        for at in ask_tpls:
            ask = at.format(**ask_fmt)
            steps = run.dialog(setup + [teach, ask])
            st, sa = steps[-2], steps[-1]
            ok_s = stored_exactly(st, *expect)
            ok_a = answered(sa["reply"], value)
            rec = dict(teach=tt, ask=at, teach_text=teach, ask_text=ask,
                       stored=[list(x) for x in st["new"]], teach_reply=st["reply"],
                       ask_reply=sa["reply"], setup_replies=[x["reply"] for x in steps[:-2]],
                       ok_store=ok_s, ok_answer=ok_a, ok=ok_s and ok_a)
            tried.append(rec)
            if rec["ok"]:
                return dict(rec, n_tried=len(tried))
            if not ok_s:
                break  # the teach itself failed: other ask templates cannot help
    best = dict(tried[0], n_tried=len(tried), all_tried=[(t["teach"], t["ask"]) for t in tried])
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--only", default=None, help="comma list of relations (debug)")
    a = ap.parse_args()
    table = json.loads(TABLE.read_text())
    run = Runner(Path(a.work))
    rows = {}
    only = set(a.only.split(",")) if a.only else None
    for rel_entry in table["relations"]:
        rel = rel_entry["name"]
        if only and rel not in only:
            continue
        vk = rel_entry.get("value_kind", "literal")
        v = VALUES.get(vk, "teal")
        r = R.rel_words(rel)
        res = {}
        res["named"] = try_row(run, [], R.TEACH_NAMED, dict(S=SUBJ, r=r, V=v), (SUBJ, rel, v),
                               R.ASK_NAMED, dict(S=SUBJ, r=r), v)
        res["first"] = try_row(run, [], R.TEACH_FIRST, dict(r=r, V=v), ("USER", rel, v),
                               R.ASK_FIRST, dict(r=r), v)
        res["named_chain"] = try_row(run, [f"{SUBJ}'s sister is {MID}."], R.TEACH_NAMED,
                                     dict(S=MID, r=r, V=v), (MID, rel, v),
                                     R.ASK_CHAIN, dict(P=f"{SUBJ}'s sister's", r=r), v)
        res["my_chain"] = try_row(run, [f"My sister is {MID}."], R.TEACH_NAMED,
                                  dict(S=MID, r=r, V=v), (MID, rel, v),
                                  R.ASK_CHAIN, dict(P="my sister's", r=r), v)
        if vk == "person":
            res["named_hop1"] = try_row(run, [f"{SUBJ}'s {r} is {MID}."], R.TEACH_NAMED,
                                        dict(S=MID, r="city", V="Dovecote"), (MID, "city", "Dovecote"),
                                        R.ASK_CHAIN, dict(P=f"{SUBJ}'s {r}'s", r="city"), "Dovecote")
            res["my_hop1"] = try_row(run, [f"My {r} is {MID}."], R.TEACH_NAMED,
                                     dict(S=MID, r="city", V="Dovecote"), (MID, "city", "Dovecote"),
                                     R.ASK_CHAIN, dict(P=f"my {r}'s", r="city"), "Dovecote")
            # hop-1 rows also need the hop-1 fact itself to have been stored exactly
            for k, subj in (("named_hop1", SUBJ), ("my_hop1", "USER")):
                ok1 = res[k]["setup_replies"] and "Saved" in res[k]["setup_replies"][0]
                res[k]["ok_hop1_saved"] = bool(ok1)
                res[k]["ok"] = bool(res[k]["ok"] and ok1)
        rows[rel] = res
        print(rel, {k: int(x["ok"]) for k, x in res.items()}, flush=True)
    summ = {k: [sum(1 for x in rows.values() if k in x and x[k]["ok"]),
                sum(1 for x in rows.values() if k in x)] for k in R.KINDS}
    Path(a.out).write_text(json.dumps(dict(summary=summ, subject=SUBJ, mid=MID, values=VALUES,
                                           base_agent=BASE_AGENT, base_cfg=BASE_CFG,
                                           rows=rows), indent=1), encoding="utf-8")
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
