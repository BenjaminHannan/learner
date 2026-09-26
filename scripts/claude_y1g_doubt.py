#!/usr/bin/env python3
"""y1g: doubt at recall. Can the plain 1B tell when it doesn't know? (Answering-from-memory thread, 2026-09-26). New
file. DEV data only (artifacts/claude-e2e331-dev-20260924, readable). Diagnosis and selection, not a change.

y1f (artifacts/claude-y1f-20260926): in bm-390's LoCoMo layout (y1f's L1) the plain MiniCPM5-1B reads well, 27 of 56
answerable asks from only the right lines and 25 of 56 from every earlier line, but it never doubts. It said "don't
know" to 2 of 10 never-told asks and gave 24 wrong answers. One added "say I don't know" line flips it to refusing
almost everything (3 of 56). Ben (16:05 UTC): when something isn't working, ask how the brain does it. The brain
trusts a recalled detail when recollection is stable: the same episode comes back each time it is cued. y1g tests
doubt signals from the model itself, on top of the same reading (L1, every earlier user turn in time order, the
question as the QA prompt's question):
  A0  one greedy answer, unchecked (the plain 1B; control)
  A1  A0 through y1f's checks (338 strict guard + G5; an abstaining answer counts as "I don't know.")
  C3  A1, kept only if at least 3 of 5 sampled answers (T 0.7 / top-p 0.9) agree with it, else "I don't know."
  C4  the same with at least 4 of 5
  V   A1, kept only if the 1B's own yes/no check in the same layout ("is the answer below correct?") says yes
Agreement: for a yes/no answer, the sample's first yes/no word matches; otherwise every content word of the answer
(lowercase, not a stop word, not in the question) is in the sample, and the sample does not abstain. An answer with
no content word never agrees. All configs come from the same generations per ask (seed 4024 + 100 x ask number).
Scored by the 336 scorer's score_ask.

  python -B scripts/claude_y1g_doubt.py --model BASE --out OUT [--seed 4024]    (always the DEV bank; no --bank)
  python -B scripts/claude_y1g_doubt.py --selftest
Outputs: OUT/y1g_rows.jsonl (one line per ask), OUT/y1g_summary.json. Last two printed lines: {"pick": ...} and the
counts per config with the doubt-signal test (signal()).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_y1d_readchat as Y  # noqa: E402  (sealed: load, all_rows, Gen, _seed, FALLBACK, ANSWERABLE, BANK)
import claude_y1f_layout as F  # noqa: E402  (sealed: messages, checked, L1_HEAD)

CONFIGS = ("A0", "A1", "C3", "C4", "V")
N_SAMPLES = 5
V_PROMPT = ("\nBased on the above conversations, is the answer below correct? Answer only yes or no.\n\n"
            "Question: {q}\nAnswer: {a}\n")
STOP = set("""a an the is are was were be been being am to of in on at and or but my your his her their our its i
you he she it they we me him them us that this these those with for as by from so do does did has have had not no
yes just like really also then there here what who whom which where when why how name named called s""".split())
YN = re.compile(r"\b(yes|no)\b", re.I)


def words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", s.lower())


def key_words(answer: str, question: str) -> set[str]:
    q = set(words(question))
    return {w.strip("'") for w in words(answer) if w not in STOP and w not in q and w.strip("'")}


def first_yn(s: str) -> str | None:
    m = YN.search(s)
    return m.group(1).lower() if m else None


def agrees(answer: str, sample: str, question: str) -> bool:
    import claude_e2e382 as E
    if E.abstains(sample):
        return False
    a = answer.strip().lower()
    if a.startswith(("yes", "no")) and first_yn(a) is not None:
        return first_yn(sample) == first_yn(a)
    k = key_words(answer, question)
    return bool(k) and k <= {w.strip("'") for w in words(sample)}


def verify_messages(question: str, answer: str, rows: list[dict]) -> list[dict]:
    import claude_bm390 as B
    body = "".join('User said, "' + r["text"] + '"\n' for r in rows)
    return [{"role": "system", "content": B.LOCOMO_SYSTEM},
            {"role": "user", "content": F.L1_HEAD + body + V_PROMPT.format(q=question, a=answer)}]


def answer_all(gen, text: str, rows: list[dict], n: int = N_SAMPLES) -> dict:
    """Every config's reply for one ask, from one greedy answer, n samples and (if A1 passes) one yes/no check."""
    import claude_chat338_agent as C38
    if not rows:
        return {c: Y.FALLBACK for c in CONFIGS} | {"samples": [], "agree": 0, "verify": None, "fail_a1": "no_rows"}
    msgs = F.messages("L1", text, rows)
    raw = C38.trim(gen.greedy_chat(msgs))
    known = C38._words([text] + [r["text"] for r in rows])
    f = F.checked(raw, text, known)
    a1 = raw if f is None else Y.FALLBACK
    samples = [C38.trim(s) for s in gen.sample_chat(msgs, n)]
    agree = sum(agrees(raw, s, text) for s in samples) if f is None else 0
    ver = first_yn(gen.greedy_chat(verify_messages(text, raw, rows))) if f is None else None
    return {"A0": raw, "A1": a1, "C3": a1 if agree >= 3 else Y.FALLBACK, "C4": a1 if agree >= 4 else Y.FALLBACK,
            "V": a1 if ver == "yes" else Y.FALLBACK, "samples": samples, "agree": agree, "verify": ver,
            "fail_a1": f}


def run(gen, bank: str, seed: int, out: Path, log=print) -> dict:
    import claude_e2e336_score as S
    turns = Y.load(Path(bank) / "turns.jsonl")
    lives = defaultdict(list)
    for t in turns:
        lives[t["life_id"]].append(t)
    out.mkdir(parents=True, exist_ok=True)
    rows_path = out / "y1g_rows.jsonl"
    rows_path.write_text("", encoding="utf-8")
    tab = defaultdict(Counter)
    sep = defaultdict(Counter)
    k_ask = 0
    for life_id in sorted(lives):
        life = sorted(lives[life_id], key=lambda t: t["turn_index"])
        for t in life:
            if t["kind"] != "ask":
                continue
            k_ask += 1
            rows = Y.all_rows(t, life)
            Y._seed(seed + 100 * k_ask)
            t0 = time.time()
            a = answer_all(gen, t["user_text"], rows)
            row = {"life_id": life_id, "turn_index": t["turn_index"], "ask_type": t["ask_type"], "n_rows": len(rows),
                   "seed": seed + 100 * k_ask, "ms": int(1000 * (time.time() - t0)), **a}
            for c in CONFIGS:
                lab = S.score_ask(t, {"reply": a[c]}, None)
                row["label_" + c] = lab
                tab[(c, t["ask_type"])][lab] += 1
                if t["gold"]["type"] in Y.ANSWERABLE:
                    tab[(c, "ANSWERABLE")][lab] += 1
            if a["A1"] != Y.FALLBACK and t["gold"]["type"] in Y.ANSWERABLE + ("idk",):
                kind = "right" if row["label_A1"] in ("RIGHT", "RIGHT_CONFIRM") else "wrong"
                for c in ("C3", "C4", "V"):
                    sep[c][kind] += 1
                    sep[c][kind + "_kept"] += a[c] != Y.FALLBACK
            with rows_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            log(f"[y1g] {life_id} t{t['turn_index']} {t['ask_type']}")
    summ = {"bank": bank, "seed": seed, "asks": k_ask, "configs": list(CONFIGS),
            "counts": {f"{c}|{a}": dict(v) for (c, a), v in sorted(tab.items())}}
    summ["answerable_right"] = {c: tab[(c, "ANSWERABLE")].get("RIGHT", 0) + tab[(c, "ANSWERABLE")].get("RIGHT_CONFIRM", 0)
                                for c in CONFIGS}
    summ["answerable_wrong"] = {c: tab[(c, "ANSWERABLE")].get("WRONG_CANDIDATE", 0) for c in CONFIGS}
    summ["never_told_idk"] = {c: tab[(c, "never_told")].get("RIGHT", 0) for c in CONFIGS}
    summ["kept"] = {c: {k: sep[c].get(k, 0) for k in ("right", "right_kept", "wrong", "wrong_kept")}
                    for c in ("C3", "C4", "V")}
    summ["signal"] = signal(summ["kept"])
    (out / "y1g_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    return summ


def signal(kept: dict) -> dict:
    """PLAN.md's proved-wrong test, over asks A1 answers (answerable or never-told): a config carries a doubt signal
    if the share of A1's right answers it keeps is at least twice the share of A1's wrong answers it keeps (a
    never-told ask that A1 answers counts as wrong)."""
    out = {}
    for c, k in kept.items():
        r = k["right_kept"] / k["right"] if k["right"] else 0.0
        w = k["wrong_kept"] / k["wrong"] if k["wrong"] else 0.0
        out[c] = {"right_share": round(r, 3), "wrong_share": round(w, 3), "signal": r > 0 and r >= 2 * w}
    out["any"] = any(v["signal"] for v in out.values())
    return out


def pick(summ: dict) -> dict:
    """PLAN.md's pre-set choice: eligible = never_told "don't know" >= 8 of 10 and answerable wrong-candidates <= 8
    (a third of y1f's L1 g1, 24); winner = most answerable right, then fewer wrong, then more never_told "don't know",
    then the order C3, C4, V, A1. GO if the winner keeps >= 18 of 56 right."""
    cand = []
    for i, c in enumerate(("C3", "C4", "V", "A1")):
        r, w, nt = summ["answerable_right"][c], summ["answerable_wrong"][c], summ["never_told_idk"][c]
        cand.append({"config": c, "right": r, "wrong": w, "never_told_idk": nt, "eligible": nt >= 8 and w <= 8,
                     "rank": (-r, w, -nt, i)})
    ok = sorted((x for x in cand if x["eligible"]), key=lambda x: x["rank"])
    win = ok[0] if ok else None
    return {"candidates": [{k: v for k, v in x.items() if k != "rank"} for x in cand],
            "winner": win and win["config"], "go": bool(win and win["right"] >= 18)}


class _FakeGen:
    """CPU stand-in. Greedy answers the first capitalised word of the last 'User said' line; samples echo it except
    when the question contains 'shaky' (then they scatter); the yes/no check says yes unless the question has 'doubt'."""

    def greedy_chat(self, msgs):
        u = msgs[-1]["content"]
        if "is the answer below correct?" in u:
            return "No." if "doubt" in u else "Yes."
        return self._ans(u)

    def _ans(self, u):
        lines = re.findall(r'User said, "(.*)"', u)
        caps = re.findall(r"\b([A-Z][a-z]+)\b", lines[-1]) if lines else []
        return (caps[0] + ".") if caps else "I don't know."

    def sample_chat(self, msgs, n):
        u = msgs[-1]["content"]
        a = self._ans(u)
        if "shaky" in u:
            return [a, "Quill.", "Oslo.", "Pim.", "Moss."][:n]
        return [a] * n


def selftest() -> None:
    import claude_e2e336_score as S
    assert key_words("Sten and Viggo.", "what were ulla's boys called?") == {"sten", "viggo"}
    assert agrees("Sten and Viggo.", "Twin boys, Sten and Viggo.", "what were ulla's boys called?")
    assert not agrees("Sten and Viggo.", "Sten.", "what were ulla's boys called?")
    assert not agrees("Sten.", "I don't know.", "q?")
    assert agrees("Yes, Ziggy is a beagle.", "yes he is", "ziggy's a beagle, right?")
    assert not agrees("Yes.", "No, he's a pug.", "ziggy's a beagle, right?")
    assert not agrees("Ulla.", "Ulla.", "who is ulla?")                    # no content word: never agrees
    rows = [{"id": 0, "text": "my dog is Rex", "said_at": None}]
    a = answer_all(_FakeGen(), "what's my dog called?", rows)
    assert a["A0"] == a["A1"] == a["C3"] == a["C4"] == a["V"] == "Rex." and a["agree"] == 5, a
    a = answer_all(_FakeGen(), "what's my dog called, shaky?", rows)
    assert a["A1"] == "Rex." and a["C3"] == a["C4"] == Y.FALLBACK and a["V"] == "Rex." and a["agree"] == 1, a
    a = answer_all(_FakeGen(), "what's my dog called, doubt?", rows)
    assert a["C3"] == "Rex." and a["V"] == Y.FALLBACK and a["verify"] == "no", a
    a = answer_all(_FakeGen(), "what's my dog called?", [{"id": 0, "text": "we met Zanzibar", "said_at": None}])
    assert a["A0"] == "Zanzibar." and a["fail_a1"] is None
    a = answer_all(_FakeGen(), "q?", [])
    assert all(a[c] == Y.FALLBACK for c in CONFIGS)
    vm = verify_messages("q?", "Rex.", rows)
    assert vm[1]["content"].endswith("Question: q?\nAnswer: Rex.\n") and 'User said, "my dog is Rex"' in vm[1]["content"]
    assert S.score_ask({"gold": {"type": "idk", "values": []}}, {"reply": Y.FALLBACK}, None) == "RIGHT"
    bank = SCRIPTS.parent / Y.BANK
    with tempfile.TemporaryDirectory() as d:
        summ = run(_FakeGen(), str(bank), 4024, Path(d), log=lambda s: None)
        out = Y.load(Path(d) / "y1g_rows.jsonl")
    assert summ["asks"] == 71 and len(out) == 71 and all(r["n_rows"] == r["turn_index"] for r in out)
    p = pick(summ)
    assert len(p["candidates"]) == 4 and isinstance(p["go"], bool)
    assert set(summ["kept"]) == {"C3", "C4", "V"} and isinstance(summ["signal"]["any"], bool)
    sg = signal({"C3": {"right": 20, "right_kept": 16, "wrong": 30, "wrong_kept": 12},
                 "C4": {"right": 20, "right_kept": 10, "wrong": 30, "wrong_kept": 15},
                 "V": {"right": 0, "right_kept": 0, "wrong": 5, "wrong_kept": 0}})
    assert sg["C3"]["signal"] and not sg["C4"]["signal"] and not sg["V"]["signal"] and sg["any"], sg
    fake = {"answerable_right": {"C3": 20, "C4": 18, "V": 20, "A1": 25},
            "answerable_wrong": {"C3": 6, "C4": 3, "V": 5, "A1": 24},
            "never_told_idk": {"C3": 8, "C4": 9, "V": 8, "A1": 2}}
    p = pick(fake)
    assert p["winner"] == "V" and p["go"], p                   # tie on right: fewer wrong wins
    fake["answerable_wrong"]["V"] = 9
    assert pick(fake)["winner"] == "C3"
    fake["answerable_right"] = {"C3": 17, "C4": 15, "V": 17, "A1": 25}
    assert pick(fake)["winner"] == "C3" and not pick(fake)["go"]
    print("selftest ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--seed", type=int, default=4024)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not (a.model and a.out):
        raise SystemExit("--model and --out are required")
    summ = run(Y.Gen(a.model), Y.BANK, a.seed, Path(a.out), log=lambda s: print(s, flush=True))
    print(json.dumps({"pick": pick(summ)}), flush=True)
    print(json.dumps({"answerable_right": summ["answerable_right"], "answerable_wrong": summ["answerable_wrong"],
                      "never_told_idk": summ["never_told_idk"], "signal": summ["signal"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
