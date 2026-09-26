#!/usr/bin/env python3
"""y1d: where are memory answers lost, finding or reading? (Answering-from-memory thread, 2026-09-26). New file.

DEV data only (artifacts/claude-e2e331-dev-20260924, readable). No reader weights, no notebook: only the plain
MiniCPM5-1B (thinking off) and, for condition k20, the ep-382 store (MiniLM + BM25). Diagnosis, not a change.

Every ask in the dev bank is answered by ep-382's own answer step (scripts/claude_e2e382.py: SYSTEM382, the rows
block, N382 = 4 samples at 338's temperature, 338's strict guard + G5, abstaining samples skipped, first pass wins,
else the answer counts as "I don't know."), fed three different row sets:
  gold  only the user turns that taught the facts the ask cites (truth.jsonl taught_turn); reading alone
  all   every earlier user turn of the life, in order (a bank life is short, so finding is free)
  k20   the ep-382 store v2's recall(query_of(text), k=20) over every earlier user turn (what 382b's E arm sees)
Each condition is also answered once greedily with no guard (reading ceiling). Replies are scored by the 336
scorer's score_ask (the registered rules). never_told asks have no gold rows, so gold skips them.

  python -B scripts/claude_y1d_readchat.py --model BASE --out OUT [--conds gold,all,k20] [--seed 4021]
  python -B scripts/claude_y1d_readchat.py --selftest
Outputs: OUT/y1d_rows.jsonl (one line per ask x condition: replies, labels, guard fails), OUT/y1d_summary.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

BANK = "artifacts/claude-e2e331-dev-20260924"
ANSWERABLE = ("value", "yes", "no")
FALLBACK = "I don't know."
MAX_NEW_GREEDY = 200


def load(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def gold_rows(ask: dict, life_turns: dict, facts: dict) -> list[dict]:
    """The user turns that taught the facts this ask cites, oldest first."""
    idx = sorted({facts[f]["taught_turn"] for f in ask["gold"]["uses_facts"]})
    return [{"id": i, "text": life_turns[i]["user_text"], "said_at": None} for i in idx]


def all_rows(ask: dict, life: list[dict]) -> list[dict]:
    return [{"id": t["turn_index"], "text": t["user_text"], "said_at": None}
            for t in life if t["turn_index"] < ask["turn_index"]]


def answer382(gen, text: str, rows: list[dict], n: int) -> tuple[str, list[str], str | None]:
    """ep-382's answer step on the given rows: (reply, guard fails, picked sample or None)."""
    import claude_chat338_agent as C38
    import claude_e2e382 as E
    if not rows:
        return FALLBACK, ["no_rows"], None
    known = C38._words([text] + [r["text"] for r in rows] + [r.get("said_at") or "" for r in rows])
    msgs = [{"role": "system", "content": E.SYSTEM382 + "\n\n" + E._rows_block(rows)},
            {"role": "user", "content": text}]
    fails = []
    for c in gen.sample_chat(msgs, n):
        c = C38.trim(c)
        g = C38.guard(c, text, known, strict=True) or ("G5" if E.g5_unsupported(c, known) else None)
        if g is not None:
            fails.append(g)
            continue
        if E.abstains(c):
            fails.append("abstained")
            continue
        return c, fails, c
    return FALLBACK, fails, None


def greedy(gen, text: str, rows: list[dict]) -> str:
    import claude_chat338_agent as C38
    import claude_e2e382 as E
    if not rows:
        return FALLBACK
    msgs = [{"role": "system", "content": E.SYSTEM382 + "\n\n" + E._rows_block(rows)},
            {"role": "user", "content": text}]
    return C38.trim(gen.greedy_chat(msgs))


class Gen:
    """338's chat sampling (Gen338 over Gen333: T 0.7, top-p 0.9, 200 new tokens, thinking off) plus greedy."""

    def __init__(self, model_dir: str):
        import claude_chat338_agent as C38
        self.g338 = C38.Gen338(model_dir)
        self.g = self.g338.g

    def sample_chat(self, msgs, n):
        return self.g338.sample_chat(msgs, n)

    def greedy_chat(self, msgs) -> str:
        g = self.g
        ids = g.tok(self.g338._render(msgs), return_tensors="pt").to(g.dev)
        with g.torch.no_grad():
            out = g.model.generate(**ids, max_new_tokens=MAX_NEW_GREEDY, do_sample=False,
                                   pad_token_id=g.tok.eos_token_id)
        return g.tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def run(gen, bank: str, conds: list[str], n: int, seed: int, out: Path, store_mod=None, log=print) -> dict:
    import claude_e2e336_score as S
    import claude_e2e382 as E
    turns = load(Path(bank) / "turns.jsonl")
    facts = {f["fact_id"]: f for f in load(Path(bank) / "truth.jsonl")}
    lives = defaultdict(list)
    for t in turns:
        lives[t["life_id"]].append(t)
    out.mkdir(parents=True, exist_ok=True)
    rows_path = out / "y1d_rows.jsonl"
    rows_path.write_text("", encoding="utf-8")
    tab = defaultdict(Counter)            # (cond, mode, ask_type) -> outcome counts
    k_ask = 0
    for life_id in sorted(lives):
        life = sorted(lives[life_id], key=lambda t: t["turn_index"])
        by_i = {t["turn_index"]: t for t in life}
        store, tmp = None, None
        if "k20" in conds:
            tmp = tempfile.mkdtemp(prefix="y1d_")
            store = store_mod.MemoryStore(tmp)
        for t in life:
            if t["kind"] == "ask":
                k_ask += 1
                typ = t["gold"]["type"]
                for ci, cond in enumerate(conds):
                    if cond == "gold":
                        if typ == "idk":
                            continue
                        rows = gold_rows(t, by_i, facts)
                    elif cond == "all":
                        rows = all_rows(t, life)
                    else:
                        rows = store.recall(E.query_of(t["user_text"]), k=20)
                    gen_seed = seed + 100 * k_ask + ci
                    _seed(gen_seed)
                    rep, fails, _ = answer382(gen, t["user_text"], rows, n)
                    grd = greedy(gen, t["user_text"], rows)
                    row_turns = [r["turn_ids"][0] if r.get("turn_ids") else r.get("id") for r in rows]
                    gold_t = sorted({facts[f]["taught_turn"] for f in t["gold"]["uses_facts"]})
                    row = {"life_id": life_id, "turn_index": t["turn_index"], "ask_type": t["ask_type"],
                           "cond": cond, "n_rows": len(rows), "row_turns": row_turns, "gold_turns": gold_t,
                           "gold_in_rows": all(g in row_turns for g in gold_t),
                           "seed": gen_seed, "reply382": rep, "fails382": fails, "greedy": grd}
                    for mode, reply in (("p382", rep), ("greedy", grd)):
                        lab = S.score_ask(t, {"reply": reply}, None)
                        row["label_" + mode] = lab
                        tab[(cond, mode, t["ask_type"])][lab] += 1
                        tab[(cond, mode, "ALL")][lab] += 1
                        if typ in ANSWERABLE:
                            tab[(cond, mode, "ANSWERABLE")][lab] += 1
                    with rows_path.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                log(f"[y1d] {life_id} t{t['turn_index']} {t['ask_type']} " +
                    " ".join(f"{c}" for c in conds))
            if store is not None:              # heard382 writes a turn after it is answered
                store.remember(t["user_text"], source="heard", speaker="user", turn_ids=[t["turn_index"]],
                               said_at=None, logged_at="2026-09-26T00:00:00+00:00")
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
    summ = {"bank": bank, "conds": conds, "n": n, "seed": seed, "asks": k_ask,
            "counts": {f"{c}|{m}|{a}": dict(v) for (c, m, a), v in sorted(tab.items())}}
    summ["answerable_right"] = {f"{c}|{m}": v.get("RIGHT", 0) + v.get("RIGHT_CONFIRM", 0)
                                for (c, m, a), v in tab.items() if a == "ANSWERABLE"}
    summ["never_told_idk"] = {f"{c}|{m}": v.get("RIGHT", 0)
                              for (c, m, a), v in tab.items() if a == "never_told"}
    (out / "y1d_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    return summ


def _seed(s: int) -> None:
    try:
        import torch
        torch.manual_seed(s)
    except ImportError:
        pass


class _FakeGen:
    """CPU stand-in for the selftest: answers with the first capitalised word of the rows' first mention."""

    def __init__(self):
        self.calls = 0

    def _ans(self, msgs):
        import re
        self.calls += 1
        sysm, q = msgs[0]["content"], msgs[1]["content"]
        m = re.search(r"\b(\d+)\. (.*)", sysm)
        if m is None:
            return "I don't know."
        caps = re.findall(r"\b([A-Z][a-z]+)\b", m.group(2))
        return (caps[0] + ".") if caps else "I don't know."

    def sample_chat(self, msgs, n):
        return [self._ans(msgs)] * n

    def greedy_chat(self, msgs):
        return self._ans(msgs)


class _FakeStore:
    def __init__(self, d):
        self.rows = []

    def remember(self, text, **kw):
        self.rows.append({"id": "h%07d" % len(self.rows), "text": text, "said_at": None,
                          "turn_ids": kw["turn_ids"]})

    def recall(self, q, k=10):
        return self.rows[-k:]


def selftest() -> None:
    import claude_e2e336_score as S
    bank = SCRIPTS.parent / BANK
    turns = load(bank / "turns.jsonl")
    facts = {f["fact_id"]: f for f in load(bank / "truth.jsonl")}
    life = sorted([t for t in turns if t["life_id"] == "e2e-dev-01"], key=lambda t: t["turn_index"])
    by_i = {t["turn_index"]: t for t in life}
    edit = next(t for t in life if t["ask_type"] == "edit")
    g = gold_rows(edit, by_i, facts)
    assert [r["id"] for r in g] == sorted({facts[f]["taught_turn"] for f in edit["gold"]["uses_facts"]}), g
    assert all(r["id"] < edit["turn_index"] for r in g)
    a = all_rows(edit, life)
    assert [r["id"] for r in a] == list(range(edit["turn_index"])), [r["id"] for r in a]
    # answer step: a guard failure falls back, a pass is taken
    rep, fails, pick = answer382(_FakeGen(), "who?", [], 4)
    assert rep == FALLBACK and fails == ["no_rows"] and pick is None
    rep, fails, pick = answer382(_FakeGen(), "what's my name?", [{"id": 0, "text": "I am Zed.", "said_at": None}], 4)
    assert pick == "Zed." and fails == [], (rep, fails)
    # 336 scoring is applied unchanged
    assert S.score_ask({"gold": {"type": "value", "values": ["Zed"]}}, {"reply": "Zed."}, None) == "RIGHT"
    assert S.score_ask({"gold": {"type": "idk", "values": []}}, {"reply": FALLBACK}, None) == "RIGHT"
    # whole run on the dev bank with fakes (CPU, seconds)
    with tempfile.TemporaryDirectory() as d:
        store_mod = type("M", (), {"MemoryStore": _FakeStore})
        summ = run(_FakeGen(), str(bank), ["gold", "all", "k20"], 4, 4021, Path(d), store_mod, log=lambda s: None)
        rows = load(Path(d) / "y1d_rows.jsonl")
    n_ask = sum(1 for t in turns if t["kind"] == "ask")
    n_idk = sum(1 for t in turns if t["kind"] == "ask" and t["gold"]["type"] == "idk")
    assert summ["asks"] == n_ask == 71, summ["asks"]
    assert len(rows) == 3 * n_ask - n_idk, len(rows)
    assert all(r["n_rows"] <= 20 for r in rows if r["cond"] == "k20")
    assert all(max(r["row_turns"] or [-1]) < r["turn_index"] for r in rows)
    assert all(r["gold_in_rows"] for r in rows if r["cond"] in ("gold", "all"))
    print("selftest ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--bank", default=BANK)
    ap.add_argument("--out", default="")
    ap.add_argument("--conds", default="gold,all,k20")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--seed", type=int, default=4021)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not (a.model and a.out):
        raise SystemExit("--model and --out are required")
    if "TEST" in a.bank.upper() or "bank" in Path(a.bank).name.lower():
        raise SystemExit("y1d reads the DEV bank only")
    conds = [c for c in a.conds.split(",") if c]
    store_mod = None
    if "k20" in conds:
        import importlib
        store_mod = importlib.import_module("claude_ep382_store_v2")
    summ = run(Gen(a.model), a.bank, conds, a.n, a.seed, Path(a.out), store_mod,
               log=lambda s: print(s, flush=True))
    print(json.dumps({"answerable_right": summ["answerable_right"], "never_told_idk": summ["never_told_idk"]}),
          flush=True)


if __name__ == "__main__":
    main()
