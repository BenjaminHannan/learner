#!/usr/bin/env python3
"""Exp 221c runner + ONE sealed scorer (dev set and blind panel).

Every item runs in a fresh work dir per arm (setup turns, then the scored
question), arms interleaved per item. Per arm and item it records every
reply, the stored triples after setup and after the question, and the
wall time of the question turn.

Scorer (same for every arm; decided before the panel was opened):
  norm(s)   lower-case, ' for U+2019, spaces collapsed.
  has(r, v) v appears in r as whole words (no letter/digit either side).
  gold kind: "yes"/"no" -> yesno; "abstain"/"unknown"/"none"/"i don't
    know"/"" -> abstain; a label in LABELS -> label (not scored right/
    wrong, only listed); otherwise values = gold split on ";" (ALL needed).
  stored values = values of the arm's own stored triples after setup,
    plus the item's stored_after_setup values when the item has them.
  other values = stored values that are not a gold value, not inside a
    gold value, do not contain a gold value, and do not appear in the
    question text.
  abstain-like = reply contains one of ABSTAIN_MARKS.
  RIGHT  value: every gold value in reply and no other value.
         yesno: norm(reply) starts with the gold word.
         abstain: abstain-like and no stored value in the reply.
  WRONG  value: not right, not abstain-like, an other value in reply and
                no gold value in reply.
         yesno: reply starts with the opposite word.
         abstain: not abstain-like and some stored value in reply.
  QUESTION WRITE = triples after the question != triples after setup,
    counted only when the scored turn is question-shaped (ends in "?", or
    starts with a question word and has no final . or !).

Panel loader: id; family; setup (list, or a string split on newlines);
question; gold (string, or list joined with "; "); optional
stored_after_setup (triples). Field fallbacks: turns/teach/context for
setup, q/ask for question, answer/expected for gold.

Run:
  python -B scripts/claude_qnorm221c_run.py --items FILE --out DIR \\
    --arm 138i=scripts/fable_loop138i_agent.py,artifacts/fable-agent138i-20260922/loop138i-config.json \\
    --arm 221=... --arm 221c=... [--limit N]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_marks123_all as M  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)

ABSTAIN_MARKS = ("i don't know", "i do not know", "don't know",
                 "never taught me", "no record", "not sure",
                 "i don't have", "i do not have", "haven't been told",
                 "didn't understand")
ABSTAIN_GOLDS = ("abstain", "unknown", "none", "i don't know", "")
LABELS = ("self", "clarify", "statement", "current path", "no_relation")


def norm(s) -> str:
    return " ".join(str(s).replace("’", "'").lower().split())


def has(reply: str, v: str) -> bool:
    v = norm(v).rstrip(".")
    if not v:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])",
                     norm(reply)) is not None


def abstain_like(reply: str) -> bool:
    r = norm(reply)
    return any(m in r for m in ABSTAIN_MARKS)


_QW = ("who", "what", "where", "when", "which", "whose", "how", "why")


def question_shaped(turn: str) -> bool:
    """Ends in "?", or starts with a question word (after an optional
    "so,"/"um,"/"hey,") and has no final . or !."""
    t = " ".join(str(turn).split())
    t = re.sub(r"^(so|um|hey)\s*,\s*", "", t, flags=re.I)
    if not t:
        return False
    if t.endswith("?"):
        return True
    if t[-1] in ".!":
        return False
    return re.split(r"[\s'\u2019,]", t, maxsplit=1)[0].lower() in _QW


def gold_kind(gold: str) -> tuple[str, list[str]]:
    g = norm(gold).rstrip(".")
    if g in ("yes", "no"):
        return "yesno", [g]
    if g in ABSTAIN_GOLDS:
        return "abstain", []
    if g in LABELS:
        return "label", [g]
    return "value", [x.strip() for x in str(gold).split(";") if x.strip()]


def score(item: dict, arm_row: dict) -> dict:
    reply = arm_row["reply"]
    kind, gold = gold_kind(item["gold"])
    stored = [t[2] for t in arm_row["triples_setup"]]
    stored += [t[2] for t in item.get("stored_after_setup") or []
               if isinstance(t, (list, tuple)) and len(t) >= 3]
    stored = list(dict.fromkeys(str(v) for v in stored))
    q = item["question"]
    gn = [norm(g) for g in gold]
    other = [v for v in stored
             if norm(v) not in gn
             and not any(norm(v) in g or g in norm(v) for g in gn)
             and not has(q, v) and has(reply, v)]
    abst = abstain_like(reply)
    right = wrong = False
    if kind == "value":
        all_g = all(has(reply, g) for g in gold)
        any_g = any(has(reply, g) for g in gold)
        right = all_g and not other
        wrong = (not right) and (not abst) and bool(other) and not any_g
    elif kind == "yesno":
        r = norm(reply)
        right = r.startswith(gold[0])
        wrong = r.startswith("no" if gold[0] == "yes" else "yes")
    elif kind == "abstain":
        in_reply = [v for v in stored if has(reply, v) and not has(q, v)]
        right = abst and not in_reply
        wrong = (not abst) and bool(in_reply)
        other = in_reply
    wrote = sorted(map(tuple, arm_row["triples_after"])) != \
        sorted(map(tuple, arm_row["triples_setup"]))
    return {"kind": kind, "right": right, "wrong": wrong,
            "abstain_like": abst, "other_values": other,
            "question_shaped": question_shaped(q),
            "question_wrote": wrote and question_shaped(q),
            "turn_wrote": wrote}


def load_items(path: Path) -> list[dict]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        it = json.loads(line)
        setup = it.get("setup", it.get("turns", it.get("teach",
                                                        it.get("context"))))
        if setup is None:
            setup = []
        if isinstance(setup, str):
            setup = [s for s in setup.splitlines() if s.strip()]
        q = it.get("question", it.get("q", it.get("ask")))
        gold = it.get("gold", it.get("answer", it.get("expected")))
        if isinstance(gold, list):
            gold = "; ".join(str(g) for g in gold)
        items.append({"id": it.get("id"), "family": it.get("family", "?"),
                      "setup": [str(s) for s in setup], "question": str(q),
                      "gold": "" if gold is None else str(gold),
                      "expect": it.get("expect"),
                      "stored_after_setup": it.get("stored_after_setup")})
    return items


def triples(d) -> list[list[str]]:
    nb = d.loop.nb
    return sorted([list(map(str, t)) for t in L90.notebook_triples(nb)])


def run_item(dcls, cfg, root: Path, item: dict) -> dict:
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    d = M.make_daemon(dcls, cfg, root)
    replies = []
    n = 0

    def send(text: str) -> tuple[str, float]:
        nonlocal n
        f = root / "inbox" / f"m{n:02d}.txt"
        f.write_text(text, encoding="utf-8")
        t0 = time.perf_counter()
        d.process_file(f)
        dt = (time.perf_counter() - t0) * 1000.0
        rep = (root / "outbox" / f"m{n:02d}.txt").read_text(
            encoding="utf-8").strip()
        n += 1
        return rep, dt

    for s in item["setup"]:
        replies.append(send(s)[0])
    t_setup = triples(d)
    rep, ms = send(item["question"])
    t_after = triples(d)
    qn = getattr(d.loop.ears, "last_qnorm221c", None)
    shutil.rmtree(root, ignore_errors=True)
    return {"setup_replies": replies, "reply": rep, "ms": ms,
            "triples_setup": t_setup, "triples_after": t_after,
            "qnorm221c": qn}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arm", action="append", required=True,
                    help="label=agent.py,config.json")
    ap.add_argument("--work", default=None)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work) if args.work else out / "_work"
    items = load_items(Path(args.items))
    if args.limit:
        items = items[:args.limit]
    arms = []
    for spec in args.arm:
        label, rest = spec.split("=", 1)
        agent, cfgp = rest.split(",", 1)
        _mod, dcls, _b, _c = M.load_agent(agent)
        arms.append((label, dcls, M.load_base_cfg(cfgp)))
    rows = []
    t0 = time.time()
    with (out / "rows.jsonl").open("w", encoding="utf-8") as fh:
        for i, it in enumerate(items):
            row = {"id": it["id"], "family": it["family"],
                   "question": it["question"], "gold": it["gold"],
                   "expect": it.get("expect"), "arms": {}}
            for label, dcls, cfg in arms:
                r = run_item(dcls, cfg, work / label, it)
                r["score"] = score(it, r)
                row["arms"][label] = r
            rows.append(row)
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if (i + 1) % 10 == 0:
                print(f"{i + 1}/{len(items)} items, {time.time() - t0:.0f}s",
                      flush=True)
    shutil.rmtree(work, ignore_errors=True)
    labels = [a[0] for a in arms]
    summ: dict = {"n_items": len(rows), "seconds": round(time.time() - t0, 1),
                  "arms": {}}
    fams = sorted({r["family"] for r in rows})
    for lab in labels:
        sc = [r["arms"][lab]["score"] for r in rows]
        summ["arms"][lab] = {
            "right": sum(s["right"] for s in sc),
            "wrong": sum(s["wrong"] for s in sc),
            "question_writes": sum(s["question_wrote"] for s in sc),
            "labels_unscored": sum(s["kind"] == "label" for s in sc),
            "by_family": {f: {"n": sum(r["family"] == f for r in rows),
                              "right": sum(r["arms"][lab]["score"]["right"]
                                           for r in rows
                                           if r["family"] == f)}
                          for f in fams},
            "median_question_ms": round(statistics.median(
                r["arms"][lab]["ms"] for r in rows), 2) if rows else None,
            "rewrites_used": sum(bool(r["arms"][lab].get("qnorm221c"))
                                 for r in rows)}
    if "221" in labels and "221c" in labels:
        summ["right_221_not_221c"] = [
            r["id"] for r in rows if r["arms"]["221"]["score"]["right"]
            and not r["arms"]["221c"]["score"]["right"]]
        summ["right_221c_not_221"] = [
            r["id"] for r in rows if r["arms"]["221c"]["score"]["right"]
            and not r["arms"]["221"]["score"]["right"]]
        summ["median_added_ms_221c_vs_221"] = round(statistics.median(
            r["arms"]["221c"]["ms"] - r["arms"]["221"]["ms"] for r in rows),
            2) if rows else None
        diff = []
        for r in rows:
            a, b = r["arms"]["221"], r["arms"]["221c"]
            if (a["reply"], a["triples_after"], a["setup_replies"]) != \
                    (b["reply"], b["triples_after"], b["setup_replies"]):
                diff.append(r["id"])
        summ["items_differing_221_vs_221c"] = diff
        stm = [r for r in rows if r["family"] == "statement"]
        summ["statements_byte_identical"] = (
            f"{sum(r['id'] not in diff for r in stm)}/{len(stm)}")
    (out / "summary.json").write_text(json.dumps(summ, indent=1),
                                      encoding="utf-8")
    # human table
    lines = ["| id | family | question | gold | " + " | ".join(
        f"{lab} reply | {lab}" for lab in labels) + " |",
        "|" + "---|" * (4 + 2 * len(labels))]
    for r in rows:
        cells = [r["id"], r["family"], r["question"].replace("|", "/"),
                 r["gold"]]
        for lab in labels:
            a = r["arms"][lab]
            s = a["score"]
            g = "RIGHT" if s["right"] else ("WRONG" if s["wrong"] else "miss")
            if s["kind"] == "label":
                g = "label"
            if s["question_wrote"]:
                g += "+WRITE"
            cells += [a["reply"].replace("|", "/"), g]
        lines.append("| " + " | ".join(cells) + " |")
    (out / "cases.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summ, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
