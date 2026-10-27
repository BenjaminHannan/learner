#!/usr/bin/env python3
"""k1e teacher, label fix (Creative answers in chat thread, 2026-09-26). New file; claude_k1e_teacher.py is unchanged.

Why: phase 1 (artifacts/claude-k1e-20260926/VERIFY-teacher-dev.md) failed the label rule fixed before it ran
(>= 85% useful agreement with the blind judges AND kappa >= 0.5): GLM 5.3 Flash agreed on 121 of 157 DEV drafts
(77%), kappa 0.537, and called 76 drafts useful where the judges called 56 (28 of the 36 disagreements were GLM
"yes", judges "no"). The judges' words, the packet and the parser stay; only how GLM is asked changes.

Two candidate labellers (each ONE change from phase 1's labeller: JUDGE-k1a.md words + JUDGE_TAIL, 10 lines per
call, temperature 0, reasoning effort low):
  high   reasoning effort "high" instead of "low".
  vote3  three labels per line at temperature 0.7 (reasoning low), the majority kept (useful yes if >= 2 of 3;
         made_up_user_facts = the median of the three).
DEV is split by chat (DEV item ids sorted, shuffled with seed 4556, the first 20 chats = half A, the other 20 =
half B). Both candidates label half A; the one with more agreement on A (ties: higher kappa, then "high") is chosen,
and only the chosen one labels half B, where the phase-1 rule is applied once. PASS on B -> the chosen labeller
labels the critic's training drafts (phase 2). FAIL -> no GLM labels are trained on; the thread reports and asks.
Written before any candidate label was seen.

  python -B scripts/claude_k1e_teacher_c.py split --packet DEV/packet_dev.jsonl --key DEV/key_dev.json --out DIR
  python -B scripts/claude_k1e_teacher_c.py label --packet DIR/packet_A.jsonl --how high|vote3 --out DIR/A_<how>
  python -B scripts/claude_k1e_teacher_c.py choose --dir DIR --key DEV/key_dev.json --verdicts DEV/verdicts_dev.json
  python -B scripts/claude_k1e_teacher_c.py label --packet DIR/packet_B.jsonl --how <chosen> --out DIR/B_<chosen>
  python -B scripts/claude_k1e_teacher_c.py check --dir DIR --key DEV/key_dev.json --verdicts DEV/verdicts_dev.json
  python -B scripts/claude_k1e_teacher_c.py selftest      (no network)
Key rules as in claude_k1e_teacher.py: the key is read from ~/.config/openrouter/key into memory only.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_k1e_teacher as T  # noqa: E402

SPLIT_SEED, HALF = 4556, 20
HOW = {"high": {"effort": "high", "temperature": 0, "votes": 1},
       "vote3": {"effort": "low", "temperature": 0.7, "votes": 3}}


def call(key, model, text, temperature, effort, tries=4):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": text}], "temperature": temperature,
                       "max_tokens": 16000, "reasoning": {"effort": effort}}).encode()
    for i in range(tries):
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body, headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read().decode())
            return d["choices"][0]["message"]["content"] or "", d.get("usage", {})
        except Exception as e:                        # the message of an HTTP error never carries the key
            print(f"[k1e-teacher-c] try {i + 1} failed: {type(e).__name__} {str(e)[:120]}", flush=True)
            time.sleep(2 ** (i + 1))
    return "", {}


def split(a) -> None:
    lines = T.load(a.packet)
    key = json.loads(Path(a.key).read_text(encoding="utf-8"))
    chats = sorted({key[x["id"]]["item_id"] for x in lines})
    random.Random(SPLIT_SEED).shuffle(chats)
    half_a = set(chats[:HALF])
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, keep in (("A", lambda i: i in half_a), ("B", lambda i: i not in half_a)):
        sel = [x for x in lines if keep(key[x["id"]]["item_id"])]
        (out / f"packet_{name}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in sel),
                                                  encoding="utf-8")
    na = sum(key[x["id"]]["item_id"] in half_a for x in lines)
    print(json.dumps({"chats": len(chats), "chats_A": len(half_a), "lines_A": na, "lines_B": len(lines) - na}))


def label(a, key, caller=None) -> None:
    caller = caller or call
    h = HOW[a.how]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lines = T.load(a.packet)
    rows, usage, failed = [], [], []
    for s in range(0, len(lines), 10):
        chunk = [{k: x[k] for k in ("id", "chat", "request", "reply")} for x in lines[s:s + 10]]
        want = [x["id"] for x in chunk]
        text = T.JUDGE + T.JUDGE_TAIL + "\n".join(json.dumps(x, ensure_ascii=False) for x in chunk)
        votes = []
        for _ in range(h["votes"]):
            got = None
            for _ in range(3):
                txt, u = caller(key, a.model, text, h["temperature"], h["effort"])
                usage.append(u)
                v = T.json_list(txt)
                if v and [str(r.get("id")) for r in v if isinstance(r, dict)] == want:
                    got = v
                    break
            if got is None:
                break
            votes.append(got)
        if len(votes) < h["votes"]:
            failed += want
            print(f"[k1e-teacher-c] lines {s}-{s + len(chunk) - 1} unparsed", flush=True)
            continue
        for n, cid in enumerate(want):
            ys = [str(v[n].get("useful")).strip().lower() == "yes" for v in votes]
            mu = [int(v[n].get("made_up_user_facts") or 0) for v in votes]
            rows.append({"id": cid, "useful": "yes" if 2 * sum(ys) > len(ys) else "no",
                         "made_up_user_facts": int(statistics.median(mu)), "votes_yes": sum(ys)})
        print(f"[k1e-teacher-c] lines {s}-{s + len(chunk) - 1} ok", flush=True)
    (out / "labels.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    cost = sum(float(u.get("cost", 0) or 0) for u in usage)
    print(json.dumps({"how": a.how, "lines": len(lines), "labelled": len(rows), "unparsed": len(failed),
                      "calls": len(usage), "useful_yes": sum(r["useful"] == "yes" for r in rows),
                      "cost_usd": round(cost, 4)}))


def _agree(labels, key, verdicts) -> dict:
    ns = argparse.Namespace(labels=labels, key=key, verdicts=verdicts)
    return T.agree(ns)


def choose(a) -> str:
    d = Path(a.dir)
    reps = {}
    for how in ("high", "vote3"):
        p = d / f"A_{how}" / "labels.jsonl"
        if not p.exists():
            raise SystemExit(f"k1e-teacher-c: {p} missing")
        reps[how] = _agree(str(p), a.key, a.verdicts)
        if reps[how]["compared"] != len(T.load(d / "packet_A.jsonl")):
            raise SystemExit(f"k1e-teacher-c: {how} did not label every half-A line")
    best = max(("high", "vote3"), key=lambda h: (reps[h]["agree"], reps[h]["kappa"], h == "high"))
    (d / "chosen.txt").write_text(best + "\n", encoding="utf-8")
    print(json.dumps({"chosen": best, **{f"A_{h}": r for h, r in reps.items()}}))
    return best


def check(a) -> dict:
    d = Path(a.dir)
    best = (d / "chosen.txt").read_text(encoding="utf-8").strip()
    rep = _agree(str(d / f"B_{best}" / "labels.jsonl"), a.key, a.verdicts)
    n_b = len(T.load(d / "packet_B.jsonl"))
    rep = {"chosen": best, "lines_B": n_b, **rep,
           "verdict": "PASS" if rep["passes_label_rule"] and rep["compared"] == n_b else "FAIL"}
    print(json.dumps(rep))
    return rep


def selftest() -> None:
    ok = 0
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        lines, key, ver = [], {}, {}
        for c in range(40):
            for k in range(4 if c % 3 else 3):
                cid = f"E{len(lines):04d}"
                rep = f"r{c}-{k}"
                lines.append({"id": cid, "chat": [], "request": "q", "reply": rep, "extra": 1})
                key[cid] = {"item_id": f"k1dev-{c + 1:02d}", "reply": rep}
                ver[f"k1dev-{c + 1:02d}\t{rep}"] = k == 0
        (t / "p.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")
        (t / "k.json").write_text(json.dumps(key), encoding="utf-8")
        (t / "v.json").write_text(json.dumps(ver), encoding="utf-8")
        ns = argparse.Namespace(packet=str(t / "p.jsonl"), key=str(t / "k.json"), out=str(t / "d"))
        split(ns)
        pa, pb = T.load(t / "d" / "packet_A.jsonl"), T.load(t / "d" / "packet_B.jsonl")
        ca = {key[x["id"]]["item_id"] for x in pa}
        cb = {key[x["id"]]["item_id"] for x in pb}
        assert len(ca) == 20 and len(cb) == 20 and not ca & cb and len(pa) + len(pb) == len(lines)
        ok += 1

        def fake(right_rate, how):
            calls = {"n": 0}

            def caller(k, model, text, temperature, effort):
                assert effort == HOW[how]["effort"] and temperature == HOW[how]["temperature"]
                calls["n"] += 1
                chunk = [json.loads(x) for x in text.split("Packet:\n", 1)[1].splitlines()]
                out = []
                for x in chunk:
                    truth = x["reply"].endswith("-0")
                    wrong = (hash((x["id"], calls["n"])) % 100) < 100 * (1 - right_rate)
                    out.append({"id": x["id"], "useful": "yes" if truth != wrong else "no", "made_up_user_facts": 0})
                return "\n".join(json.dumps(o) for o in out), {"cost": 0.001}
            return caller
        for how, rate in (("high", 1.0), ("vote3", 0.8)):
            label(argparse.Namespace(packet=str(t / "d" / "packet_A.jsonl"), how=how, out=str(t / "d" / f"A_{how}"),
                                     model="m"), "KEY", fake(rate, how))
        rows = T.load(t / "d" / "A_vote3" / "labels.jsonl")
        assert all(r["votes_yes"] in (0, 1, 2, 3) for r in rows) and len(rows) == len(pa)
        ok += 1
        c = choose(argparse.Namespace(dir=str(t / "d"), key=str(t / "k.json"), verdicts=str(t / "v.json")))
        assert c == "high"
        label(argparse.Namespace(packet=str(t / "d" / "packet_B.jsonl"), how="high", out=str(t / "d" / "B_high"),
                                 model="m"), "KEY", fake(1.0, "high"))
        r = check(argparse.Namespace(dir=str(t / "d"), key=str(t / "k.json"), verdicts=str(t / "v.json")))
        assert r["verdict"] == "PASS" and r["agree"] == len(pb)
        ok += 1
    print(f"k1e teacher-c selftest {ok}/3 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["split", "label", "choose", "check", "selftest"])
    ap.add_argument("--packet", default="")
    ap.add_argument("--key", default="")
    ap.add_argument("--verdicts", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--dir", default="")
    ap.add_argument("--how", choices=sorted(HOW), default="high")
    ap.add_argument("--model", default="z-ai/glm-5.3-flash")
    a = ap.parse_args()
    if a.mode == "selftest":
        selftest()
    elif a.mode == "split":
        split(a)
    elif a.mode == "label":
        key = (Path.home() / ".config" / "openrouter" / "key").read_text(encoding="utf-8").strip()
        label(a, key)
    elif a.mode == "choose":
        choose(a)
    else:
        check(a)


if __name__ == "__main__":
    main()
