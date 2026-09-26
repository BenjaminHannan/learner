#!/usr/bin/env python3
"""rp1: the recall path against plain same-size models on memory questions (Answering-from-memory thread,
2026-09-26). New file. Registered test on bank E (TEST-ONLY); marks in artifacts/claude-rp1-20260926/PASSMARKS.md,
sealed before any bank E run.

Brain idea (hippocampus): keep every experience as a pointer to the raw episode, and handle doubt at recall. The
recall path R = every earlier user turn kept raw, read by the plain MiniCPM5-1B in y1f's L1 layout (bm-390's LoCoMo
reading layout), one greedy answer through y1f's checks, then y1g's winning doubt step (claude_y1g_doubt.DOUBT_RP1 is
fixed in PASSMARKS.md; here --doubt). Rivals get the same messages, greedy, thinking off, 200 new tokens, the same trim:
  R   MiniCPM5-1B + checks + doubt step              M   plain MiniCPM5-1B (R's first answer, unchecked)
  Q   plain Qwen3.5-2B                               L   plain LFM2.5-1.2B-Instruct
  Mi, Qi, Li  the same three in y1f's L1i layout (L1 plus 'If the conversations do not say, answer "I don't know."')
  report only: M1 = R without the doubt step; Mb = plain MiniCPM5-1B through bm-390's loader (harness check)
Every arm's reply is scored by the 336 scorer (score_ask). Replies the scorer calls WRONG_CANDIDATE go to blind judges
(as 0.2c H1): identical (ask, reply) pairs are judged once, arms mixed under neutral ids (seed 4032), two judges in
private folders, a fresh third on splits. marks applies PASSMARKS.md by script (K1 is ADDENDUM-15's win-row bar:
ahead of every rival at <= 5% one-sided chance for an equal build, by a life-level sign-flip test).

  python -B scripts/claude_rp1_recall.py run --bank BANK --minicpm DIR --qwen DIR --lfm DIR --doubt C3 --out OUT
      [--seed 4025] [--limit N]            OUT/rp1_rows.jsonl (never printed), OUT/rp1_summary.json,
                                           OUT/score/judge_asks_<arm>.jsonl; prints counts only
  python -B scripts/claude_rp1_recall.py prep --bank BANK --score OUT/score --out JUDGEDIR   key at JUDGEDIR/../rp1_key.json
  python -B scripts/claude_rp1_recall.py splits --out JUDGEDIR
  python -B scripts/claude_rp1_recall.py score --key KEY --out JUDGEDIR       -> JUDGEDIR/../rp1_judged.json
  python -B scripts/claude_rp1_recall.py marks --rows OUT/rp1_rows.jsonl --judged JUDGED   prints marks, counts only
  python -B scripts/claude_rp1_recall.py --selftest
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_y1d_readchat as Y  # noqa: E402  (sealed: load, all_rows, Gen, _seed, FALLBACK, ANSWERABLE)
import claude_y1f_layout as F  # noqa: E402  (sealed: messages)
import claude_y1g_doubt as G  # noqa: E402  (sealed: answer_all)

JUDGED_ARMS = ("R", "M", "Q", "L", "Mi", "Qi", "Li")
REPORT_ARMS = ("M1", "Mb")
RIVALS = ("M", "Q", "L")
SEED_JUDGE = 4032
FLIPS = 20000
MAX_NEW = Y.MAX_NEW_GREEDY
# PASSMARKS.md (fixed before any bank E run)
K1_P = 0.05             # net(R) ahead of the rival's better prompt at <= 5% one-sided chance for an equal build
                        # (ADDENDUM-15's win-row bar): life-level sign-flip test, p_equal()
K2_SLACK = 2            # never-told "don't know": R >= rival's better prompt - this
K3_SHARE = 0.5          # right(R) >= this x right(M): the doubt step keeps at least half the plain 1B's right answers

INSTRUCTIONS = """# Judging: is this a wrong answer stated as fact?

Each line of batch.jsonl is one moment in a chat between a user and an assistant. The user asked a question about
things they had told the assistant earlier. You get:
- "question": what the user asked;
- "facts_true_now": every fact the user had told the assistant by then that was still true (owner, relation, value);
- "gold": the right answer ("values" to name; "type" yes / no for a yes-no question; "idk" when the user never told
  the assistant, so the right reply is to say it doesn't know; "partial" when only the first step is known);
- "reply": what the assistant said.

Label each item:
- WRONG if the reply states as fact an answer to the question that the facts do not support: a wrong value, a wrong
  person, the wrong yes/no, or any made-up answer to a question the user never answered ("idk" gold). A confident
  guess counts as stated as fact.
- OK otherwise: the right answer in other words or spelling; a reply that says it doesn't know or isn't sure; a
  question back to the user that asserts nothing wrong; or a reply that does not answer the question and asserts
  nothing false about the user's life.

Judge only from the item itself. Do not look at any other file or folder, and do not discuss items with anyone.
Write labels/batch.jsonl in this folder: one JSON line per item, {"item": "<id>", "label": "WRONG" or "OK"}, every
item exactly once.
"""


def load(p) -> list[dict]:
    return Y.load(p)


# ---------------------------------------------------------------- run

class Rival:
    """A plain model through bm-390's loader: greedy, thinking off, the same system and user text as R."""

    def __init__(self, model_dir: str):
        self.dir = model_dir

    def greedy_chat(self, msgs: list[dict]) -> str:
        import claude_bm390 as B
        return B.generate(self.dir, msgs[0]["content"], msgs[1]["content"], MAX_NEW)[0]


def replies(gen, rivals: dict, text: str, rows: list[dict], doubt: str) -> tuple[dict, dict]:
    """Every arm's reply for one ask. gen = MiniCPM5-1B (Y.Gen); rivals = {"Q": .., "L": .., "Mb": ..}."""
    import claude_chat338_agent as C38
    a = G.answer_all(gen, text, rows)
    rep = {"R": a[doubt], "M": a["A0"] if rows else C38.trim(gen.greedy_chat(F.messages("L1", text, rows))),
           "M1": a["A1"]}
    l1, l1i = F.messages("L1", text, rows), F.messages("L1i", text, rows)
    rep["Mi"] = C38.trim(gen.greedy_chat(l1i))
    for k in ("Q", "L"):
        rep[k] = C38.trim(rivals[k].greedy_chat(l1))
        rep[k + "i"] = C38.trim(rivals[k].greedy_chat(l1i))
    rep["Mb"] = C38.trim(rivals["Mb"].greedy_chat(l1))
    return rep, {"agree": a["agree"], "verify": a["verify"], "fail_a1": a["fail_a1"]}


def run(gen, rivals: dict, bank: str, doubt: str, seed: int, out: Path, limit: int = 0, log=print) -> dict:
    import claude_e2e336_score as S
    if doubt not in ("C3", "C4", "V"):
        raise SystemExit("--doubt must be C3, C4 or V")
    turns = load(Path(bank) / "turns.jsonl")
    lives = defaultdict(list)
    for t in turns:
        lives[t["life_id"]].append(t)
    n_asks = sum(t["kind"] == "ask" for t in turns)
    out.mkdir(parents=True, exist_ok=True)
    (out / "score").mkdir(exist_ok=True)
    rows_path = out / "rp1_rows.jsonl"
    rows_path.write_text("", encoding="utf-8")
    judge = {arm: [] for arm in JUDGED_ARMS}
    k_ask, no_rows, t_all = 0, 0, time.time()
    for life_id in sorted(lives):
        life = sorted(lives[life_id], key=lambda t: t["turn_index"])
        for t in life:
            if t["kind"] != "ask" or (limit and k_ask >= limit):
                continue
            k_ask += 1
            rows = Y.all_rows(t, life)
            no_rows += not rows
            Y._seed(seed + 100 * k_ask)
            t0 = time.time()
            rep, info = replies(gen, rivals, t["user_text"], rows, doubt)
            labels = {arm: S.score_ask(t, {"reply": rep[arm]}, None) for arm in JUDGED_ARMS + REPORT_ARMS}
            row = {"life_id": life_id, "turn_index": t["turn_index"], "ask_type": t["ask_type"],
                   "gold_type": t["gold"]["type"], "n_rows": len(rows), "seed": seed + 100 * k_ask,
                   "ms": int(1000 * (time.time() - t0)), "reply": rep, "label": labels, **info}
            with rows_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            for arm in JUDGED_ARMS:
                if labels[arm] == "WRONG_CANDIDATE":
                    judge[arm].append({"life_id": life_id, "turn_index": t["turn_index"], "ask_type": t["ask_type"],
                                       "gold": t["gold"], "reply": rep[arm]})
            log(f"[rp1] {k_ask}/{n_asks}")
    for arm, items in judge.items():
        (out / "score" / f"judge_asks_{arm}.jsonl").write_text(
            "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items), encoding="utf-8")
    summ = counts(load(rows_path))
    summ |= {"bank": bank, "doubt": doubt, "seed": seed, "asks": k_ask, "asks_without_rows": no_rows,
             "minutes": round((time.time() - t_all) / 60, 1)}
    (out / "rp1_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    return summ


def counts(rows: list[dict]) -> dict:
    """Scorer counts per arm (no judging): answerable right, never-told "don't know", wrong-candidates."""
    arms = JUDGED_ARMS + REPORT_ARMS
    right = {a: sum(r["gold_type"] in Y.ANSWERABLE and r["label"][a] in ("RIGHT", "RIGHT_CONFIRM") for r in rows)
             for a in arms}
    nt = {a: sum(r["gold_type"] == "idk" and r["label"][a] == "RIGHT" for r in rows) for a in arms}
    wc = {a: sum(r["label"][a] == "WRONG_CANDIDATE" for r in rows) for a in arms}
    same = sum(r["reply"]["M"] == r["reply"]["Mb"] for r in rows)
    return {"answerable": sum(r["gold_type"] in Y.ANSWERABLE for r in rows),
            "never_told": sum(r["gold_type"] == "idk" for r in rows),
            "answerable_right": right, "never_told_idk": nt, "wrong_candidates": wc, "M_equals_Mb": same,
            "R_kept": sum(r["reply"]["R"] != Y.FALLBACK for r in rows),
            "M1_answered": sum(r["reply"]["M1"] != Y.FALLBACK for r in rows)}


# ---------------------------------------------------------------- blind judging

def _write(folder: Path, items: list[dict]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "batch.jsonl").write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items),
                                        encoding="utf-8")
    (folder / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")


def prep(bank: str, score: str, out: str) -> dict:
    """One packet per distinct (life, turn, reply) over every judged arm's wrong-candidates; the key maps it back."""
    turns = {(t["life_id"], t["turn_index"]): t for t in load(Path(bank) / "turns.jsonl")}
    truth = load(Path(bank) / "truth.jsonl")
    uniq: dict[tuple, dict] = {}
    for arm in JUDGED_ARMS:
        for p in load(Path(score) / f"judge_asks_{arm}.jsonl"):
            k = (p["life_id"], p["turn_index"], p["reply"])
            uniq.setdefault(k, {"p": p, "arms": []})["arms"].append(arm)
    order = sorted(uniq, key=lambda k: (k[0], k[1], k[2]))
    random.Random(SEED_JUDGE).shuffle(order)
    key, items = {}, []
    for i, k in enumerate(order):
        p, iid = uniq[k]["p"], f"Q{i:04d}"
        key[iid] = {"arms": uniq[k]["arms"], "life_id": p["life_id"], "turn_index": p["turn_index"],
                    "ask_type": p["ask_type"]}
        t = turns[(p["life_id"], p["turn_index"])]
        now = [{f: x[f] for f in ("owner", "relation", "value")} for x in truth
               if x["life_id"] == p["life_id"] and x["taught_turn"] <= p["turn_index"]
               and (x.get("valid_until_turn") is None or x["valid_until_turn"] > p["turn_index"])]
        items.append({"item": iid, "question": t["user_text"], "facts_true_now": now,
                      "gold": {"type": p["gold"]["type"], "values": p["gold"]["values"]}, "reply": p["reply"]})
    o = Path(out)
    for j in ("a", "b"):
        _write(o / f"judge_{j}", items)
    (o.parent / "rp1_key.json").write_text(json.dumps(key, indent=0), encoding="utf-8")
    res = {"items": len(items), "by_arm": {a: sum(a in k["arms"] for k in key.values()) for a in JUDGED_ARMS}}
    print(json.dumps(res))
    return res


def _labels(folder: Path) -> dict:
    p = folder / "labels" / "batch.jsonl"
    return {x["item"]: x["label"] for x in load(p)} if p.exists() else {}


def splits(out: str) -> int:
    o = Path(out)
    a, b = _labels(o / "judge_a"), _labels(o / "judge_b")
    items = load(o / "judge_a" / "batch.jsonl")
    if any(it["item"] not in a or it["item"] not in b for it in items):
        raise SystemExit("unlabelled items")
    bad = {v for v in list(a.values()) + list(b.values())} - {"WRONG", "OK"}
    if bad:
        raise SystemExit(f"labels must be WRONG or OK, got {sorted(bad)}")
    sp = [it for it in items if a[it["item"]] != b[it["item"]]]
    if sp:
        _write(o / "judge_c", sp)
    print(json.dumps({"items": len(items), "splits": len(sp)}))
    return len(sp)


def score(key_path: str, out: str) -> dict:
    """Final label per packet -> JUDGEDIR/../rp1_judged.json: {"<life>|<turn>|<arm>": "WRONG" | "OK"}."""
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    o = Path(out)
    a, b, c = (_labels(o / f"judge_{j}") for j in ("a", "b", "c"))
    judged, agree, nsplit = {}, 0, 0
    for iid, k in key.items():
        if iid not in a or iid not in b:
            raise SystemExit(f"{iid} unlabelled")
        if a[iid] == b[iid]:
            agree, lab = agree + 1, a[iid]
        else:
            nsplit += 1
            if iid not in c:
                raise SystemExit(f"split {iid} needs the third judge")
            lab = c[iid]
        for arm in k["arms"]:
            judged[f"{k['life_id']}|{k['turn_index']}|{arm}"] = lab
    (o.parent / "rp1_judged.json").write_text(json.dumps(judged, indent=0), encoding="utf-8")
    wrong = Counter(key.split("|")[2] for key, lab in judged.items() if lab == "WRONG")
    res = {"packets": len(key), "agree": agree, "splits": nsplit,
           "wrong_as_fact": {arm: wrong.get(arm, 0) for arm in JUDGED_ARMS}}
    print(json.dumps(res))
    return res


# ---------------------------------------------------------------- marks

def per_ask(rows: list[dict], judged: dict, arm: str) -> list[tuple[str, int]]:
    """(life, s) per ask: +1 answerable right, -1 judged wrong-as-fact, else 0."""
    out = []
    for r in rows:
        lab = r["label"][arm]
        if r["gold_type"] in Y.ANSWERABLE and lab in ("RIGHT", "RIGHT_CONFIRM"):
            s = 1
        elif lab == "WRONG_CANDIDATE":
            k = f"{r['life_id']}|{r['turn_index']}|{arm}"
            if k not in judged:
                raise SystemExit(f"{k} not judged")
            s = -1 if judged[k] == "WRONG" else 0
        else:
            s = 0
        out.append((r["life_id"], s))
    return out


def p_equal(a: list[tuple[str, int]], b: list[tuple[str, int]], seed: int = SEED_JUDGE) -> float:
    """One-sided chance that an equal build is this far ahead: each life's net(a) - net(b) gets a random sign
    (lives are the unit; asks in one life share a chat), p = (1 + flips with sum >= observed) / (1 + FLIPS)."""
    d = defaultdict(int)
    for (life, x), (_, y) in zip(a, b):
        d[life] += x - y
    v = [d[k] for k in sorted(d)]
    obs = sum(v)
    rng = random.Random(seed)
    hit = sum(sum(x if rng.random() < 0.5 else -x for x in v) >= obs for _ in range(FLIPS))
    return round((1 + hit) / (1 + FLIPS), 5)


def marks(rows: list[dict], judged: dict) -> dict:
    c = counts(rows)
    s = {arm: per_ask(rows, judged, arm) for arm in JUDGED_ARMS}
    net = {arm: sum(x for _, x in s[arm]) for arm in JUDGED_ARMS}
    waf = {arm: sum(x == -1 for _, x in s[arm]) for arm in JUDGED_ARMS}
    nt = c["never_told_idk"]
    res = {"net": net, "wrong_as_fact": waf, "answerable_right": {a: c["answerable_right"][a] for a in JUDGED_ARMS},
           "never_told_idk": {a: nt[a] for a in JUDGED_ARMS}, "rivals": {}}
    ok = True
    for x in RIVALS:
        best = x if net[x] >= net[x + "i"] else x + "i"
        p = p_equal(s["R"], s[best])
        k1 = net["R"] > net[best] and p <= K1_P
        k2 = nt["R"] >= nt[best] - K2_SLACK
        res["rivals"][x] = {"better_prompt": best, "net_gap": net["R"] - net[best], "p_equal": p, "K1": k1,
                            "K2": k2}
        ok &= k1 and k2
    k3 = c["answerable_right"]["R"] >= K3_SHARE * c["answerable_right"]["M"]
    res["K3"] = k3
    res["verdict"] = "PASS" if ok and k3 else "FAIL"
    split = Counter()
    for r in rows:
        for arm in JUDGED_ARMS:
            if judged.get(f"{r['life_id']}|{r['turn_index']}|{arm}") == "WRONG":
                split[f"{arm}|{'edit' if r['ask_type'] == 'edit' else 'rest'}"] += 1
    res["wrong_as_fact_edit_vs_rest"] = dict(sorted(split.items()))
    by_type = Counter()
    for r in rows:
        for arm in ("R", "M", "Q", "L"):
            if r["gold_type"] in Y.ANSWERABLE and r["label"][arm] in ("RIGHT", "RIGHT_CONFIRM"):
                by_type[f"{arm}|{r['ask_type']}"] += 1
    res["right_by_type"] = dict(sorted(by_type.items()))
    res["M_equals_Mb"] = c["M_equals_Mb"]
    return res


# ---------------------------------------------------------------- selftest

class _FakeRival:
    """Answers the first capitalised word of the last 'User said' line; 'bold' also answers never-told questions."""

    def __init__(self, bold: bool):
        self.bold = bold

    def greedy_chat(self, msgs):
        import re
        u = msgs[-1]["content"]
        if "I don't know" in u and not self.bold:
            return "I don't know."
        lines = re.findall(r'User said, "(.*)"', u)
        caps = re.findall(r"\b([A-Z][a-z]+)\b", lines[-1]) if lines else []
        return (caps[0] + ".") if caps else "Pim."


def selftest() -> None:
    bank = SCRIPTS.parent / Y.BANK
    riv = {"Q": _FakeRival(True), "L": _FakeRival(False), "Mb": _FakeRival(True)}
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        summ = run(G._FakeGen(), riv, str(bank), "C3", 4025, d / "out", log=lambda s: None)
        rows = load(d / "out/rp1_rows.jsonl")
        assert summ["asks"] == 71 == len(rows) and summ["answerable"] == 56 and summ["never_told"] == 10, summ
        assert all(set(r["reply"]) == set(JUDGED_ARMS + REPORT_ARMS) for r in rows)
        assert all(r["reply"]["R"] in (r["reply"]["M1"], Y.FALLBACK) for r in rows)
        n_wc = {a: len(load(d / f"out/score/judge_asks_{a}.jsonl")) for a in JUDGED_ARMS}
        assert all(n_wc[a] == summ["wrong_candidates"][a] for a in JUDGED_ARMS), (n_wc, summ)
        res = prep(str(bank), str(d / "out/score"), str(d / "j/judges"))
        items = load(d / "j/judges/judge_a/batch.jsonl")
        key = json.loads((d / "j/rp1_key.json").read_text())
        assert len(items) == len(key) == res["items"] <= sum(n_wc.values())
        assert all(set(it) == {"item", "question", "facts_true_now", "gold", "reply"} for it in items)
        assert not any('"arms"' in json.dumps(it) or "life_id" in json.dumps(it) for it in items)
        # judges: a says WRONG to all; b says OK to packets that R shares; c sides with a
        for j, f in (("a", lambda k: "WRONG"), ("b", lambda k: "OK" if "R" in k["arms"] else "WRONG")):
            (d / f"j/judges/judge_{j}/labels").mkdir(parents=True)
            (d / f"j/judges/judge_{j}/labels/batch.jsonl").write_text(
                "".join(json.dumps({"item": it["item"], "label": f(key[it["item"]])}) + "\n" for it in items))
        nsp = splits(str(d / "j/judges"))
        assert nsp == sum("R" in k["arms"] for k in key.values())
        if nsp:
            (d / "j/judges/judge_c/labels").mkdir(parents=True)
            (d / "j/judges/judge_c/labels/batch.jsonl").write_text("".join(
                json.dumps({"item": it["item"], "label": "WRONG"}) + "\n"
                for it in load(d / "j/judges/judge_c/batch.jsonl")))
        sc = score(str(d / "j/rp1_key.json"), str(d / "j/judges"))
        assert all(sc["wrong_as_fact"][a] == summ["wrong_candidates"][a] for a in JUDGED_ARMS), sc
        judged = json.loads((d / "j/rp1_judged.json").read_text())
        m = marks(rows, judged)
        assert set(m["rivals"]) == set(RIVALS) and m["verdict"] in ("PASS", "FAIL")
        for a in JUDGED_ARMS:
            assert m["net"][a] == m["answerable_right"][a] - m["wrong_as_fact"][a], (a, m)
    # marks on hand-made rows: R answers 30 right, 0 wrong; M 40 right, 40 wrong
    rows, judged = [], {}
    for i in range(80):
        life = f"L{i % 20}"
        lab = {a: "ABSTAIN" for a in JUDGED_ARMS + REPORT_ARMS}
        rep = {a: "x" for a in JUDGED_ARMS + REPORT_ARMS}
        if i < 30:
            lab["R"] = "RIGHT"
        for a in ("M", "Q", "L", "Mi", "Qi", "Li"):
            lab[a] = "RIGHT" if i % 2 == 0 else "WRONG_CANDIDATE"
            if lab[a] == "WRONG_CANDIDATE":
                judged[f"{life}|{i}|{a}"] = "WRONG"
        rows.append({"life_id": life, "turn_index": i, "ask_type": "edit" if i < 10 else "one_hop",
                     "gold_type": "value", "label": lab, "reply": rep})
    m = marks(rows, judged)
    assert m["net"]["R"] == 30 and m["net"]["M"] == 0 and m["rivals"]["M"]["better_prompt"] == "M", m
    assert m["K3"]                                                 # 30 >= 0.5 x 40
    for x in RIVALS:
        v = m["rivals"][x]
        assert v["K1"] == (v["net_gap"] > 0 and v["p_equal"] <= K1_P) and v["K2"]
    assert m["verdict"] == ("PASS" if all(m["rivals"][x]["K1"] for x in RIVALS) else "FAIL")
    assert m["wrong_as_fact_edit_vs_rest"]["M|edit"] == 5 and m["wrong_as_fact_edit_vs_rest"]["M|rest"] == 35
    assert p_equal([("a", 1), ("b", 0)], [("a", 0), ("b", 1)]) > 0.5      # gap 0: most flips tie or beat it
    assert p_equal([(f"l{i}", 1) for i in range(20)], [(f"l{i}", 0) for i in range(20)]) < 0.001
    assert 0.3 < p_equal([(f"l{i}", 1 if i < 11 else 0) for i in range(20)],
                         [(f"l{i}", 0 if i < 11 else 1) for i in range(20)]) < 0.6
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    for k in ("--bank", "--minicpm", "--qwen", "--lfm", "--doubt", "--out"):
        r.add_argument(k, required=True)
    r.add_argument("--seed", type=int, default=4025)
    r.add_argument("--limit", type=int, default=0)
    p = sub.add_parser("prep")
    for k in ("--bank", "--score", "--out"):
        p.add_argument(k, required=True)
    s = sub.add_parser("splits")
    s.add_argument("--out", required=True)
    k = sub.add_parser("score")
    k.add_argument("--key", required=True)
    k.add_argument("--out", required=True)
    m = sub.add_parser("marks")
    m.add_argument("--rows", required=True)
    m.add_argument("--judged", required=True)
    a = ap.parse_args()
    if a.cmd == "run":
        riv = {"Q": Rival(a.qwen), "L": Rival(a.lfm), "Mb": Rival(a.minicpm)}
        summ = run(Y.Gen(a.minicpm), riv, a.bank, a.doubt, a.seed, Path(a.out), a.limit,
                   log=lambda s: print(s, flush=True))
        print(json.dumps({k: summ[k] for k in ("asks", "answerable", "never_told", "answerable_right",
                                                "never_told_idk", "wrong_candidates", "M_equals_Mb", "R_kept",
                                                "minutes")}, sort_keys=True), flush=True)
    elif a.cmd == "prep":
        prep(a.bank, a.score, a.out)
    elif a.cmd == "splits":
        splits(a.out)
    elif a.cmd == "score":
        score(a.key, a.out)
    else:
        print(json.dumps(marks(load(a.rows), json.loads(Path(a.judged).read_text(encoding="utf-8"))),
                         sort_keys=True))


if __name__ == "__main__":
    main()
