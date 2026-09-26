#!/usr/bin/env python3
"""y1v: a trained yes/no judge on the plain 1B's own answers (Answering-from-memory thread, 2026-09-26). New file.
y1t's FAIL fallback (artifacts/claude-y1v-20260926/PLAN.md): it runs only if y1t (trained doubt) is NO-GO.

One change to y1g's V config. In V the plain MiniCPM5-1B answers in y1f's L1 layout (A1: one greedy answer through
y1f's checks), then a yes/no check with y1g's V_PROMPT keeps or drops that answer. In y1g the plain 1B judged itself
and said "no" to 15 of its 26 right answers. Here the check is done by a LoRA-trained copy of the plain 1B (the
judge). The answers stay the plain model's own, so the judge can only keep or drop them.

Brain idea (a guess): people judge "do I really know this?" with a monitoring step that is partly separate from
recall itself (feeling-of-knowing / source monitoring), and that monitor is tuned by feedback on past recalls.

Judge practice data, no new model text: the plain 1B's own drafts from y1t's run (drafts.jsonl: greedy + 4 samples on
GLM-written practice chats, artifacts/claude-y1t-20260926/run/) joined to y1t's items (items_train.jsonl). Each draft
that y1f's checks would let through (not an abstention, guards pass, some earlier turns) becomes one judge row: y1g's
verify_messages for (question, draft, earlier user turns), target "Yes." if y1t's grade() calls the draft right (336
scorer + y1f's checks; an old corrected value is wrong; any answer to a never-told twin is wrong), else "No.".
Identical drafts of one item count once. The larger class is cut to the size of the smaller (seeded; at most 2000
each), so the judge does not learn to always agree; small sets are repeated so about 1500 rows pass through training
(at most 3 times each). 15% of dialogs are held out as judge practice-dev (seed 4033; report only). Code chose every
fact, GLM wrote every word, code graded every draft: nothing here is written or judged by Claude.

Training: scripts/claude_bm398r_train.py unchanged (rank 16 LoRA on q/k/v/o, 1 epoch, lr 2e-4, batch 8, loss on the
answer tokens, seed 3992), merged copy saved. DEV check: y1g's run() unchanged on the DEV bank with a routed model:
V's yes/no prompt goes to the judge, everything else (greedy answer, samples) to the plain 1B. So A0, A1, C3, C4 are
the plain 1B's own and V is the one change.

  python -B scripts/claude_y1v_judge.py data --items ITEMS_TRAIN --drafts DRAFTS --out DIR
      -> DIR/train.jsonl, DIR/dev.jsonl (bm-398r trainer format), DIR/judge_summary.json; prints counts only
  python -B scripts/claude_y1v_judge.py eval --answerer BASE --judge JUDGE_DIR --out OUT   (DEV bank, seed 4024)
      -> OUT/y1g_rows.jsonl, OUT/y1g_summary.json (y1g's files); prints the summary's counts
  python -B scripts/claude_y1v_judge.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_y1d_readchat as Y  # noqa: E402  (sealed: load, Gen, BANK, FALLBACK)
import claude_y1f_layout as F  # noqa: E402  (sealed: checked)
import claude_y1g_doubt as G  # noqa: E402  (sealed: V_PROMPT, verify_messages, run)
import claude_y1t_data as T  # noqa: E402  (sealed: grade, MIN_ROW_PASSES, MAX_REPEAT)

SEED = 4033
DEV_SHARE = 0.15
DEV_CAP = 300
MAX_PER_CLASS = 2000                      # bounds training time: at most 4000 distinct rows
EVAL_SEED = 4024                          # y1g's seed
YES, NO = "Yes.", "No."
V_MARK = G.V_PROMPT.split("{q}")[0]       # the fixed text of y1g's yes/no prompt, up to the question


def judge_rows(items: list[dict], drafts: list[dict]) -> tuple[list[dict], Counter]:
    """One row per distinct draft that y1f's checks let through, labelled by y1t's grade()."""
    import claude_chat338_agent as C38
    by = {}
    for it in items:
        key = (it["dialog_id"], it["k"], it["kind"])
        assert key not in by, f"duplicate item {key}"
        by[key] = it
    rows, c = [], Counter()
    for d in drafts:
        it = by[(d["dialog_id"], d["k"], d["kind"])]
        if not it["rows"]:                      # y1g never asks the yes/no check without earlier turns
            c["not_judged_no_rows"] += 1
            continue
        known = C38._words([it["question"]] + [r["text"] for r in it["rows"]])
        seen = set()
        for i, a in enumerate([d["greedy"]] + list(d["samples"])):
            src = "greedy" if i == 0 else "sample"
            if a in seen:
                c["duplicate_draft"] += 1
                continue
            seen.add(a)
            f = F.checked(a, it["question"], known)
            if f is not None:
                c["not_judged_" + ("abstained" if f == "abstained" else "guard")] += 1
                continue
            ok = T.grade(it, a)
            m = G.verify_messages(it["question"], a, it["rows"])
            rows.append({"dialog_id": it["dialog_id"], "system": m[0]["content"], "user": m[1]["content"],
                         "answer": YES if ok else NO})
            c[f"{it['kind']}_{src}_{'yes' if ok else 'no'}"] += 1
    return rows, c


def balance(rows: list[dict], seed: int) -> tuple[list[dict], dict]:
    """Cut the larger class to the smaller one's size (seeded), then repeat so ~MIN_ROW_PASSES rows pass."""
    rng = random.Random(seed)
    yes = [r for r in rows if r["answer"] == YES]
    no = [r for r in rows if r["answer"] == NO]
    rng.shuffle(yes)
    rng.shuffle(no)
    n = min(len(yes), len(no), MAX_PER_CLASS)
    base = yes[:n] + no[:n]
    repeat = min(T.MAX_REPEAT, max(1, math.ceil(T.MIN_ROW_PASSES / max(1, len(base)))))
    train = base * repeat
    rng.shuffle(train)
    return train, {"yes_all": len(yes), "no_all": len(no), "per_class": n, "repeat": repeat}


def data(items_path: str, drafts_path: str, out: Path, seed: int = SEED) -> dict:
    rows, c = judge_rows(Y.load(items_path), Y.load(drafts_path))
    dialogs = sorted({r["dialog_id"] for r in rows})
    random.Random(seed).shuffle(dialogs)
    dev_ids = set(dialogs[:round(DEV_SHARE * len(dialogs))])
    tr = [r for r in rows if r["dialog_id"] not in dev_ids]
    dv = [r for r in rows if r["dialog_id"] in dev_ids]
    train, info = balance(tr, seed)
    random.Random(seed + 1).shuffle(dv)
    dev = [{"system": r["system"], "user": r["user"], "answer": r["answer"], "kind": "value", "layout": "V"}
           for r in dv[:DEV_CAP]]
    train = [{"system": r["system"], "user": r["user"], "answer": r["answer"]} for r in train]
    out.mkdir(parents=True, exist_ok=True)
    for name, rs in (("train.jsonl", train), ("dev.jsonl", dev)):
        (out / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs), encoding="utf-8")
    res = {"judge_rows": len(rows), "dialogs": len(dialogs), "dev_dialogs": len(dev_ids), "train_rows": len(train),
           "dev_rows": len(dev), "dev_yes": sum(r["answer"] == YES for r in dev), **info,
           "counts": dict(sorted(c.items()))}
    (out / "judge_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


class Routed:
    """The plain 1B answers and samples; only y1g's yes/no prompt goes to the judge."""

    def __init__(self, answerer, judge):
        self.answerer, self.judge = answerer, judge
        self.judged = 0

    def greedy_chat(self, msgs):
        if V_MARK in msgs[-1]["content"]:
            self.judged += 1
            return self.judge.greedy_chat(msgs)
        return self.answerer.greedy_chat(msgs)

    def sample_chat(self, msgs, n):
        assert V_MARK not in msgs[-1]["content"]
        return self.answerer.sample_chat(msgs, n)


def evaluate(gen: Routed, out: Path, log=print) -> dict:
    summ = G.run(gen, str(SCRIPTS.parent / Y.BANK), EVAL_SEED, out, log=log)
    summ["judge_calls"] = gen.judged
    (out / "y1g_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    return summ


def decide(summ: dict) -> dict:
    """PLAN.md's rule, fixed before the run: GO if V has answerable right >= 22 of 56, answerable wrong <= 8 and
    never-told "don't know" >= 8 of 10."""
    r, w, nt = (summ[k]["V"] for k in ("answerable_right", "answerable_wrong", "never_told_idk"))
    return {"right": r, "wrong": w, "never_told_idk": nt, "go": r >= 22 and w <= 8 and nt >= 8}


# ---------------------------------------------------------------- selftest

class _Judge:
    """Says no when the answer is 'Pim.', else yes."""

    def greedy_chat(self, msgs):
        assert V_MARK in msgs[-1]["content"]
        return "No." if "Answer: Pim." in msgs[-1]["content"] else "Yes."


def selftest() -> None:
    fr = lambda act, facts=(), ask=None: {"act": act, "facts": list(facts), "ask": ask}  # noqa: E731
    fa = lambda o, rel, v, mode="ASSERT", **kw: {"owner": o, "rel": rel, "value": v, "mode": mode, **kw}  # noqa: E731
    seeds = [{"dialog_id": f"d{i}", "turns": [
        {"k": 1, "intent": "smalltalk", "gold": fr("CHAT")},
        {"k": 2, "intent": "teach", "gold": fr("TELL", [fa("me", "sister", "Mira"), fa("Mira", "dog", "Rolo")])},
        {"k": 3, "intent": "correct", "gold": fr("TELL", [fa("Mira", "dog", "Tansy", "CORRECT", old="Rolo")])},
        {"k": 4, "intent": "ask", "gold": fr("ASK", [], {"owner": "Mira", "rel": "dog", "inverse": False})}]}
        for i in range(10)]
    kept = [x for i in range(10) for x in (
        {"id": f"glm320-d{i}-t1", "turn": f"long day at the shop number {i} lol"},
        {"id": f"glm320-d{i}-t2", "turn": "my sister Mira got a dog called Rolo"},
        {"id": f"glm320-d{i}-t3", "turn": "wait no mira's dog is Tansy not rolo"},
        {"id": f"glm320-d{i}-t4", "turn": "whats mira's dog called again"})]
    items, _ = T.build_items(seeds, kept)
    assert len(items) == 20
    drafts = []
    for it in items:
        if it["kind"] == "answerable":
            g, ss = "Tansy.", ["Tansy.", "Rolo.", "I don't know.", "Tansy."]
        else:                                   # the twin keeps only the small-talk turn
            g, ss = "Shop.", ["I don't know.", "Shop.", "Shop.", "Shop."]
        drafts.append({"dialog_id": it["dialog_id"], "k": it["k"], "kind": it["kind"], "greedy": g, "samples": ss})
    rows, c = judge_rows(items, drafts)
    # answerable: Tansy (yes), Rolo (no; the old corrected value); never-told: Shop (no); "I don't know." not judged
    assert len(rows) == 30 and c["answerable_greedy_yes"] == 10 and c["answerable_sample_no"] == 10, c
    assert c["never_told_greedy_no"] == 10 and c["not_judged_abstained"] == 20 and c["duplicate_draft"] == 50, c
    nr, cn = judge_rows([items[1] | {"rows": []}], [drafts[1]])
    assert not nr and cn["not_judged_no_rows"] == 1
    r0 = rows[0]
    assert r0["user"].endswith("Question: whats mira's dog called again\nAnswer: Tansy.\n") and r0["answer"] == YES
    assert r0["system"] == G.verify_messages("q", "a", [])[0]["content"]
    tr, info = balance(rows, SEED)
    assert info["per_class"] == 10 and info["repeat"] == 3 and len(tr) == 60, info
    assert sum(r["answer"] == YES for r in tr) == 30
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "items.jsonl").write_text("".join(json.dumps(x) + "\n" for x in items))
        (d / "drafts.jsonl").write_text("".join(json.dumps(x) + "\n" for x in drafts))
        res = data(str(d / "items.jsonl"), str(d / "drafts.jsonl"), d / "out")
        tr, dv = Y.load(d / "out" / "train.jsonl"), Y.load(d / "out" / "dev.jsonl")
        assert res["dialogs"] == 10 and res["dev_dialogs"] == 2 and len(dv) == 6 and res["dev_yes"] == 2, res
        assert all(set(r) == {"system", "user", "answer"} for r in tr) and len(tr) == res["train_rows"]
        assert all(r["kind"] == "value" and r["layout"] == "V" for r in dv)
        assert res["train_rows"] == 2 * 8 * 3        # 8 train dialogs: 8 yes, 16 no -> 8 per class, x3
        assert not {r["user"] for r in dv} & {r["user"] for r in tr}
        gen = Routed(G._FakeGen(), _Judge())
        summ = evaluate(gen, d / "eval", log=lambda s: None)
        plain = G.run(G._FakeGen(), str(SCRIPTS.parent / Y.BANK), EVAL_SEED, d / "plain", log=lambda s: None)
    assert summ["asks"] == 71 and gen.judged > 0 and summ["judge_calls"] == gen.judged
    for k in ("answerable_right", "answerable_wrong", "never_told_idk"):
        assert all(summ[k][c] == plain[k][c] for c in ("A0", "A1", "C3", "C4")), k   # only V may differ
    dc = decide({"answerable_right": {"V": 22}, "answerable_wrong": {"V": 8}, "never_told_idk": {"V": 8}})
    assert dc["go"]
    assert not decide({"answerable_right": {"V": 21}, "answerable_wrong": {"V": 0}, "never_told_idk": {"V": 10}})["go"]
    assert not decide({"answerable_right": {"V": 26}, "answerable_wrong": {"V": 9}, "never_told_idk": {"V": 10}})["go"]
    assert not decide({"answerable_right": {"V": 26}, "answerable_wrong": {"V": 0}, "never_told_idk": {"V": 7}})["go"]
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("data")
    for k in ("--items", "--drafts", "--out"):
        d.add_argument(k, required=True)
    e = sub.add_parser("eval")
    for k in ("--answerer", "--judge", "--out"):
        e.add_argument(k, required=True)
    a = ap.parse_args()
    if a.cmd == "data":
        print(json.dumps(data(a.items, a.drafts, Path(a.out))), flush=True)
    else:
        summ = evaluate(Routed(Y.Gen(a.answerer), Y.Gen(a.judge)), Path(a.out),
                        log=lambda s: print(s, flush=True))
        print(json.dumps({k: summ[k] for k in ("asks", "answerable_right", "answerable_wrong", "never_told_idk",
                                                "kept", "judge_calls")}), flush=True)
        print(json.dumps({"decide": decide(summ)}), flush=True)


if __name__ == "__main__":
    main()
