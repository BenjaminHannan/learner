#!/usr/bin/env python3
"""y1f: which prompt layout lets the plain 1B read the user's own words? (Answering-from-memory thread, 2026-09-26).
New file. DEV data only (artifacts/claude-e2e331-dev-20260924, readable). Diagnosis and selection, not a change.

y1d (artifacts/claude-y1d-20260926) gave the plain MiniCPM5-1B the exact lines that hold each answer and it answered
3 of 56 (greedy 0 of 56: "I don't have information about ..."), with every earlier line 13 of 56. Benchmarks' bm-398d
gave the same model LoCoMo's right lines in bm-390's layout and it answered 137 of 297. y1d used ep-382's layout (the
lines in the system message, the user's turn as the user message). y1f keeps y1d's asks, rows, model, guard and scorer
and changes only the layout:

  L0   ep-382 as is: SYSTEM382 + numbered rows in the system message, the user's turn as the user message (control)
  L1   bm-390's LoCoMo layout: LOCOMO_SYSTEM; the user message is a header, a "CONVERSATION:" block of
       'User said, "<text>"' lines in time order, then bm-390's QA_PROMPT with the user's turn as the question
  L1i  L1 plus one last line in the user message: If the conversations do not say, answer "I don't know."
  L2   the rows as earlier chat: a short system line, each row as a user message answered "Okay.", then the turn

Conditions: gold (only the turns that taught the cited facts) and all (every earlier user turn, in time order). y1d's
k20 is left out: on bank-sized lives the store's top 20 is every earlier turn (y1d: 71 of 71 asks, same set as all),
only in rank order. Decodings, both through the same checks as y1d's answer step (338 strict guard + G5, abstaining
answers skipped, else "I don't know."): p382 = 4 samples at T 0.7 / top-p 0.9, first pass wins; g1 = one greedy
answer. The raw greedy answer is also kept (report only, no guard). Scored by the 336 scorer's score_ask.

  python -B scripts/claude_y1f_layout.py --model BASE --out OUT [--layouts L0,L1,L1i,L2] [--seed 4023]
  python -B scripts/claude_y1f_layout.py --selftest
Outputs: OUT/y1f_rows.jsonl (one line per ask x condition x layout), OUT/y1f_summary.json. Last printed line: JSON with
answerable_right, never_told_idk and answerable_wrong per layout|cond|mode.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_y1d_readchat as Y  # noqa: E402  (sealed: load, gold_rows, all_rows, Gen, _seed, FALLBACK)

LAYOUTS = ("L0", "L1", "L1i", "L2")
CONDS = ("gold", "all")
L1_HEAD = "Below is what the user said to you in earlier conversations, in time order.\n\nCONVERSATION:\n"
L1I_LINE = '\nIf the conversations do not say, answer "I don\'t know."\n'
L2_SYSTEM = "You are a helpful and honest assistant. Answer briefly and directly."
L2_ACK = "Okay."


def messages(layout: str, text: str, rows: list[dict]) -> list[dict]:
    """The chat messages for one layout. rows are in time order."""
    import claude_bm390 as B
    import claude_e2e382 as E
    if layout == "L0":
        return [{"role": "system", "content": E.SYSTEM382 + "\n\n" + E._rows_block(rows)},
                {"role": "user", "content": text}]
    if layout in ("L1", "L1i"):
        body = "".join('User said, "' + r["text"] + '"\n' for r in rows)
        user = L1_HEAD + body + "\n" + B.QA_PROMPT.format(text)
        if layout == "L1i":
            user += L1I_LINE
        return [{"role": "system", "content": B.LOCOMO_SYSTEM}, {"role": "user", "content": user}]
    if layout == "L2":
        msgs = [{"role": "system", "content": L2_SYSTEM}]
        for r in rows:
            msgs += [{"role": "user", "content": r["text"]}, {"role": "assistant", "content": L2_ACK}]
        return msgs + [{"role": "user", "content": text}]
    raise ValueError(layout)


def checked(c: str, text: str, known: set[str]) -> str | None:
    """y1d's answer-step checks on one answer: the failed check's name, "abstained", or None if it passes."""
    import claude_chat338_agent as C38
    import claude_e2e382 as E
    g = C38.guard(c, text, known, strict=True) or ("G5" if E.g5_unsupported(c, known) else None)
    if g is not None:
        return g
    return "abstained" if E.abstains(c) else None


def answer(gen, layout: str, text: str, rows: list[dict], n: int) -> dict:
    """Both decodings for one ask: {"p382", "fails382", "g1", "fail_g1", "raw"}."""
    import claude_chat338_agent as C38
    if not rows:
        return {"p382": Y.FALLBACK, "fails382": ["no_rows"], "g1": Y.FALLBACK, "fail_g1": "no_rows",
                "raw": Y.FALLBACK}
    known = C38._words([text] + [r["text"] for r in rows] + [r.get("said_at") or "" for r in rows])
    msgs = messages(layout, text, rows)
    rep, fails = Y.FALLBACK, []
    for c in gen.sample_chat(msgs, n):
        c = C38.trim(c)
        f = checked(c, text, known)
        if f is None:
            rep = c
            break
        fails.append(f)
    raw = C38.trim(gen.greedy_chat(msgs))
    fg = checked(raw, text, known)
    return {"p382": rep, "fails382": fails, "g1": raw if fg is None else Y.FALLBACK, "fail_g1": fg, "raw": raw}


def run(gen, bank: str, layouts: list[str], n: int, seed: int, out: Path, log=print) -> dict:
    import claude_e2e336_score as S
    turns = Y.load(Path(bank) / "turns.jsonl")
    facts = {f["fact_id"]: f for f in Y.load(Path(bank) / "truth.jsonl")}
    lives = defaultdict(list)
    for t in turns:
        lives[t["life_id"]].append(t)
    out.mkdir(parents=True, exist_ok=True)
    rows_path = out / "y1f_rows.jsonl"
    rows_path.write_text("", encoding="utf-8")
    tab = defaultdict(Counter)            # (layout, cond, mode, ask_type) -> outcome counts
    k_ask = 0
    for life_id in sorted(lives):
        life = sorted(lives[life_id], key=lambda t: t["turn_index"])
        by_i = {t["turn_index"]: t for t in life}
        for t in life:
            if t["kind"] != "ask":
                continue
            k_ask += 1
            typ = t["gold"]["type"]
            for ci, cond in enumerate(CONDS):
                if cond == "gold" and typ == "idk":
                    continue
                rows = Y.gold_rows(t, by_i, facts) if cond == "gold" else Y.all_rows(t, life)
                for li, lay in enumerate(layouts):
                    gen_seed = seed + 100 * k_ask + 10 * ci + li
                    Y._seed(gen_seed)
                    a = answer(gen, lay, t["user_text"], rows, n)
                    row = {"life_id": life_id, "turn_index": t["turn_index"], "ask_type": t["ask_type"],
                           "cond": cond, "layout": lay, "n_rows": len(rows), "row_turns": [r["id"] for r in rows],
                           "seed": gen_seed, **a}
                    for mode in ("p382", "g1", "raw"):
                        lab = S.score_ask(t, {"reply": a[mode]}, None)
                        row["label_" + mode] = lab
                        tab[(lay, cond, mode, t["ask_type"])][lab] += 1
                        if typ in Y.ANSWERABLE:
                            tab[(lay, cond, mode, "ANSWERABLE")][lab] += 1
                    with rows_path.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            log(f"[y1f] {life_id} t{t['turn_index']} {t['ask_type']}")
    summ = {"bank": bank, "layouts": layouts, "conds": list(CONDS), "n": n, "seed": seed, "asks": k_ask,
            "counts": {"|".join(k): dict(v) for k, v in sorted(tab.items())}}
    right = lambda v: v.get("RIGHT", 0) + v.get("RIGHT_CONFIRM", 0)  # noqa: E731
    summ["answerable_right"] = {f"{l}|{c}|{m}": right(v) for (l, c, m, a), v in tab.items() if a == "ANSWERABLE"}
    summ["answerable_wrong"] = {f"{l}|{c}|{m}": v.get("WRONG_CANDIDATE", 0)
                                for (l, c, m, a), v in tab.items() if a == "ANSWERABLE"}
    summ["never_told_idk"] = {f"{l}|{c}|{m}": v.get("RIGHT", 0)
                              for (l, c, m, a), v in tab.items() if a == "never_told"}
    (out / "y1f_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    return summ


def pick(summ: dict, layouts=LAYOUTS) -> dict:
    """PLAN.md's pre-set choice over condition all: eligible = never_told "don't know" >= 8 of 10 and answerable
    wrong-candidates <= 11 (y1d's L0 p382 had 11); winner = most answerable right, then fewer wrong-candidates, then
    more never_told "don't know", then the order L1i, L1, L2, L0 and g1 before p382. Go if the winner has >= 25."""
    order = [(l, m) for l in ("L1i", "L1", "L2", "L0") if l in layouts for m in ("g1", "p382")]
    cand = []
    for i, (l, m) in enumerate(order):
        k = f"{l}|all|{m}"
        r, w, nt = summ["answerable_right"].get(k, 0), summ["answerable_wrong"].get(k, 0), summ["never_told_idk"].get(k, 0)
        cand.append({"config": f"{l}|{m}", "right": r, "wrong": w, "never_told_idk": nt,
                     "eligible": nt >= 8 and w <= 11, "rank": (-r, w, -nt, i)})
    ok = sorted((c for c in cand if c["eligible"]), key=lambda c: c["rank"])
    win = ok[0] if ok else None
    return {"candidates": [{k: v for k, v in c.items() if k != "rank"} for c in cand],
            "winner": win and win["config"], "go": bool(win and win["right"] >= 25)}


class _FakeGen:
    """CPU stand-in: answers with the first capitalised word of the first row it finds in the messages."""

    def _ans(self, msgs):
        import re
        if msgs[0]["content"].startswith("You are a helpful and honest assistant. Below"):
            m = re.search(r"\b\d+\. (.*)", msgs[0]["content"])
            src = m.group(1) if m else ""
        elif len(msgs) == 2:
            m = re.search(r'User said, "(.*)"', msgs[1]["content"])
            src = m.group(1) if m else ""
        else:
            src = msgs[1]["content"]
        caps = re.findall(r"\b([A-Z][a-z]+)\b", src)
        return (caps[0] + ".") if caps else "I don't know."

    def sample_chat(self, msgs, n):
        return [self._ans(msgs)] * n

    def greedy_chat(self, msgs):
        return self._ans(msgs)


def selftest() -> None:
    import claude_bm390 as B
    import claude_e2e336_score as S
    import claude_e2e382 as E
    rows = [{"id": 0, "text": "my dog is Rex", "said_at": None}, {"id": 3, "text": "I live in Oslo", "said_at": None}]
    m0 = messages("L0", "q?", rows)
    assert m0[0]["content"] == E.SYSTEM382 + "\n\n1. my dog is Rex\n2. I live in Oslo" and m0[1]["content"] == "q?"
    m1 = messages("L1", "q?", rows)
    assert m1[0]["content"] == B.LOCOMO_SYSTEM and len(m1) == 2
    assert m1[1]["content"] == (L1_HEAD + 'User said, "my dog is Rex"\nUser said, "I live in Oslo"\n\n'
                                + B.QA_PROMPT.format("q?")), m1[1]["content"]
    assert messages("L1i", "q?", rows)[1]["content"] == m1[1]["content"] + L1I_LINE
    m2 = messages("L2", "q?", rows)
    assert [x["role"] for x in m2] == ["system", "user", "assistant", "user", "assistant", "user"]
    assert m2[1]["content"] == "my dog is Rex" and m2[-1]["content"] == "q?" and m2[2]["content"] == L2_ACK
    for lay in LAYOUTS:
        a = answer(_FakeGen(), lay, "what's my dog called?", rows, 4)
        assert a["p382"] == "Rex." and a["g1"] == "Rex." and a["fails382"] == [], (lay, a)
    a = answer(_FakeGen(), "L1", "who?", [], 4)
    assert a["p382"] == a["g1"] == Y.FALLBACK and a["fails382"] == ["no_rows"]
    a = answer(_FakeGen(), "L1", "who?", [{"id": 0, "text": "we met Quill", "said_at": None}], 4)
    assert a["p382"] == "Quill." and a["g1"] == "Quill."
    # an unsupported name fails G5 and falls back
    assert checked("Zanzibar.", "who?", {"who", "we", "met", "quill"}) == "G5"
    assert checked("I don't know.", "who?", {"who"}) == "abstained"
    assert S.score_ask({"gold": {"type": "value", "values": ["Rex"]}}, {"reply": "Rex."}, None) == "RIGHT"
    bank = SCRIPTS.parent / Y.BANK
    turns = Y.load(bank / "turns.jsonl")
    with tempfile.TemporaryDirectory() as d:
        summ = run(_FakeGen(), str(bank), list(LAYOUTS), 4, 4023, Path(d), log=lambda s: None)
        out = Y.load(Path(d) / "y1f_rows.jsonl")
    n_ask = sum(1 for t in turns if t["kind"] == "ask")
    n_idk = sum(1 for t in turns if t["kind"] == "ask" and t["gold"]["type"] == "idk")
    assert summ["asks"] == n_ask == 71 and len(out) == 4 * (2 * n_ask - n_idk), len(out)
    assert all(r["row_turns"] == sorted(r["row_turns"]) and max(r["row_turns"] or [-1]) < r["turn_index"] for r in out)
    assert all(r["row_turns"] == list(range(r["turn_index"])) for r in out if r["cond"] == "all")
    p = pick(summ)
    assert len(p["candidates"]) == 8 and isinstance(p["go"], bool)
    fake = {"answerable_right": {"L1|all|g1": 30, "L1i|all|g1": 30, "L2|all|p382": 40},
            "answerable_wrong": {"L1|all|g1": 5, "L1i|all|g1": 5, "L2|all|p382": 12},
            "never_told_idk": {"L1|all|g1": 9, "L1i|all|g1": 9, "L2|all|p382": 10}}
    p = pick(fake)
    assert p["winner"] == "L1i|g1" and p["go"], p
    fake["answerable_right"]["L1|all|g1"] = 31
    assert pick(fake)["winner"] == "L1|g1"
    fake = {"answerable_right": {"L1|all|g1": 24}, "answerable_wrong": {"L1|all|g1": 0},
            "never_told_idk": {"L1|all|g1": 10}}
    p = pick(fake)
    assert p["winner"] == "L1|g1" and not p["go"], p
    print("selftest ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--bank", default=Y.BANK)
    ap.add_argument("--out", default="")
    ap.add_argument("--layouts", default=",".join(LAYOUTS))
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--seed", type=int, default=4023)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not (a.model and a.out):
        raise SystemExit("--model and --out are required")
    if "TEST" in a.bank.upper() or "bank" in Path(a.bank).name.lower():
        raise SystemExit("y1f reads the DEV bank only")
    layouts = [x for x in a.layouts.split(",") if x]
    summ = run(Y.Gen(a.model), a.bank, layouts, a.n, a.seed, Path(a.out), log=lambda s: print(s, flush=True))
    print(json.dumps({"pick": pick(summ, layouts)}), flush=True)
    print(json.dumps({"answerable_right": summ["answerable_right"], "never_told_idk": summ["never_told_idk"],
                      "answerable_wrong": summ["answerable_wrong"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
