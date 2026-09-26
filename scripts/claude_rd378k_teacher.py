#!/usr/bin/env python3
"""rd-378k teacher jobs on the Mac (Trustworthy notes thread, 2026-09-26): the open-weights teacher (GLM via OpenRouter,
the teacher Ben approved; goals page 5f38f110e: nothing a model trains on is written or judged by Claude) writes the
practice dialogs the note writer drafts over, and grades the writer's own notes, so the cut-only rows
(scripts/claude_rd378k_data.py) hold no Claude-written or Claude-judged text. Standard library only; no model runs here.

Key rules: the key is read from ~/.config/openrouter/key into memory only. Never printed, logged or written.
Call pattern copied from scripts/claude_k1e_teacher.py (reasoning effort low, answer read from the final message).

write  160 practice dialogs in 20 calls of 8 (4 chat with an assistant + 4 overheard between two named people,
       12-16 turns), each call with its own subject area. Structure checked in code; a call that breaks it is retried
       (3 tries). ids kd-001..kd-160 in call order; t counts from 1.
         python -B scripts/claude_rd378k_teacher.py write --out DIR [--model M]
label  the teacher grades every note of a judge-input file (claude_rd378k_data.py judgein) with the judge brief's own
       verdict words (artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md), one dialog per call, temperature 0;
       writes DIR/labels.jsonl {dialog, t, verdicts, missed} (the judge-output format). [--only-hash K: only dialogs
       whose sha256(id) % K == 0.]
         python -B scripts/claude_rd378k_teacher.py label --judge-in J.jsonl --out DIR [--only-hash K] [--model M]
agree  teacher verdicts vs the blind judges' verdicts on the same notes, ok vs not ok. Label rule fixed before any
       teacher label exists (the creative thread's rule for a label source, k1e): agreement >= 85% and kappa >= 0.5.
         python -B scripts/claude_rd378k_teacher.py agree --labels L.jsonl --verdicts V.jsonl
selftest (no network)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path

AREAS = ("hobbies and crafts", "work and coworkers", "family visits", "school and exams", "food and cooking",
         "travel and trips", "pets", "moving house", "neighbours and community", "sports and fitness",
         "music and concerts", "gardening", "health and appointments", "money and shopping", "weddings and parties",
         "cars and commuting", "books and films (invented titles only)", "volunteering", "holidays and seasons",
         "new jobs and interviews")
VERDICTS = ("ok", "unsupported", "bad_cite", "bad_when", "bad_form")
MONTHS = ("January February March April May June July August September October November December").split()

WRITE = """Write 8 realistic conversations as a JSON list of 8 objects. Each object has exactly the keys "kind",
"speakers", "date", "turns".
- 4 with kind "chat": a user talks with a personal assistant. speakers = ["user", "assistant"]. Turns alternate,
  starting with the user. The user tells the assistant about their life; the assistant's turns are short natural replies.
- 4 with kind "overheard": two friends, relatives or coworkers talk. speakers = their two first names. Turns alternate,
  starting with the first name.
- date: the day the conversation happens, like "8 May 2023", a different day for each, between 2021 and 2025.
- turns: 12 to 16 objects {"speaker": one of the speakers, "text": the message}.
What the talk should contain, mixed naturally: things that happened, plans, preferences and opinions, times said in the
chat ("last May", "next Friday", "two weeks ago", "in 2019"), changes (moved, new job, got a pet, broke up), things one
person says about someone else, the odd joke, sarcasm or "what if", a correction of something said earlier ("wait, it
was Tuesday"), pronouns pointing back to earlier messages, and some small talk with nothing to remember.
Style: real texting, some typos in ordinary words (never in names), run-ons, mixed lengths (3 to 60 words).
Subject area for all 8: {area}. Fictional names only: invented first names from many cultures and made-up places; no
real public figures, brands, or book, film or game titles.

Reply with ONLY the JSON list, no other text."""

JUDGE = """You are checking memory notes that a small model wrote about a conversation. Below is one conversation as JSON:
{"dialog","kind","speakers","date","turns":[{"t","speaker","text","notes":[{"text","cites","when"}]}]}.
cites are offsets from the note's own turn (0 = that turn, -1 = the turn before, ...).

For EVERY note, read the dialog up to and including the note's turn and give one verdict:
- ok: one plain sentence, third person with names (or "the user"), and everything in it is stated by the cited turns
  (reading the earlier turns only to know who "she"/"that" is); plans stay plans, claims about others stay claims.
- unsupported: it says something the cited turns do not state (a guess, an inference, a wrong detail, wrong person).
- bad_cite: true to the dialog but a turn it needs is not cited, or a cited turn is not needed.
- bad_when: "when" is wrong (not the time the turns give for this note, or missing when the turn gives one).
- bad_form: pronoun instead of a name, first/second person, more than one sentence, a joke or hypothetical turned into a fact.
For EVERY turn that has a "notes" list (even an empty one), also say "missed": the number of clearly memorable things in
that turn (an event, plan, preference, change, time, person or pet fact) that no note of that turn covers (0 if none).

Reply with ONLY a JSON list with one object per turn that has a "notes" list, in order:
{"t": <the turn's t>, "verdicts": [one verdict word per note, in order], "missed": <integer>}.

Conversation:
"""


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def call(key, model, text, temperature, tries=4):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": text}], "temperature": temperature,
                       "max_tokens": 16000, "reasoning": {"effort": "low"}}).encode()
    for i in range(tries):
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body, headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.loads(r.read().decode())
            return d["choices"][0]["message"]["content"] or "", d.get("usage", {})
        except Exception as e:                        # the message of an HTTP error never carries the key
            print(f"[rd378k-teacher] try {i + 1} failed: {type(e).__name__} {str(e)[:120]}", flush=True)
            time.sleep(2 ** (i + 1))
    return "", {}


def json_list(txt):
    m = re.search(r"\[.*\]", txt, re.S)
    if not m:
        return None
    try:
        v = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return v if isinstance(v, list) else None


def check_dialog(r) -> str | None:
    if not isinstance(r, dict) or set(r) != {"kind", "speakers", "date", "turns"}:
        return "keys"
    sp = r["speakers"]
    if r["kind"] == "chat":
        if sp != ["user", "assistant"]:
            return "chat speakers"
    elif r["kind"] == "overheard":
        if not (isinstance(sp, list) and len(sp) == 2 and all(isinstance(s, str) and re.fullmatch(r"[A-Z][\w'-]+", s)
                                                               for s in sp) and sp[0] != sp[1]):
            return "overheard speakers"
    else:
        return "kind"
    m = re.fullmatch(r"(\d{1,2}) ([A-Z][a-z]+) (20\d\d)", str(r["date"]))
    if not m or m.group(2) not in MONTHS or not 2021 <= int(m.group(3)) <= 2025 or not 1 <= int(m.group(1)) <= 31:
        return "date"
    ts = r["turns"]
    if not isinstance(ts, list) or not 12 <= len(ts) <= 16:
        return "turn count"
    for i, t in enumerate(ts):
        if not isinstance(t, dict) or set(t) != {"speaker", "text"} or not isinstance(t["text"], str) or \
                not t["text"].strip():
            return "turn keys"
        if t["speaker"] != sp[i % 2]:
            return "speakers do not alternate"
    return None


def check_batch(rows) -> str | None:
    if not rows or len(rows) != 8:
        return "not 8 dialogs"
    for r in rows:
        bad = check_dialog(r)
        if bad:
            return bad
    kinds = sorted(r["kind"] for r in rows)
    return None if kinds == ["chat"] * 4 + ["overheard"] * 4 else "not 4 chat + 4 overheard"


def write(a, key):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    items, usage, seen = [], [], set()
    for b, area in enumerate(AREAS):
        rows = None
        for t in range(3):
            txt, u = call(key, a.model, WRITE.replace("{area}", area), 0.9)
            usage.append(u)
            rows = json_list(txt)
            bad = check_batch(rows)
            firsts = None if bad else {r["turns"][0]["text"].strip().lower() for r in rows}
            if bad is None and not firsts & seen:
                break
            print(f"[rd378k-teacher] batch {b} try {t + 1}: {bad or 'repeats an earlier dialog'}", flush=True)
            rows = None
        if rows is None:
            raise SystemExit(f"rd378k-teacher: batch {b} failed 3 times")
        for r in rows:
            seen.add(r["turns"][0]["text"].strip().lower())
            items.append({"dialog": f"kd-{len(items) + 1:03d}", "kind": r["kind"], "speakers": r["speakers"],
                          "date": r["date"], "turns": [{"t": i + 1, "speaker": t["speaker"], "text": t["text"]}
                                                       for i, t in enumerate(r["turns"])]})
        print(f"[rd378k-teacher] batch {b} ok ({len(items)} dialogs)", flush=True)
    (out / "dialogs.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items),
                                       encoding="utf-8")
    cost = sum(float(u.get("cost", 0) or 0) for u in usage)
    print(json.dumps({"dialogs": len(items), "turns": sum(len(x["turns"]) for x in items), "calls": len(usage),
                      "cost_usd": round(cost, 4)}))


def check_labels(d, v) -> list | None:
    want = [(int(t["t"]), len(t["notes"])) for t in d["turns"] if "notes" in t]
    if not v or len(v) != len(want):
        return None
    rows = []
    for (t, n), r in zip(want, v):
        if not isinstance(r, dict) or r.get("t") != t or not isinstance(r.get("verdicts"), list) or \
                len(r["verdicts"]) != n or any(x not in VERDICTS for x in r["verdicts"]):
            return None
        try:
            m = int(r.get("missed") or 0)
        except (TypeError, ValueError):
            return None
        rows.append({"dialog": d["dialog"], "t": t, "verdicts": r["verdicts"], "missed": max(0, m)})
    return rows


def picked(dialog_id, k):
    return k <= 1 or int(hashlib.sha256(dialog_id.encode()).hexdigest(), 16) % k == 0


def label(a, key):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dialogs = [d for d in load(a.judge_in) if picked(d["dialog"], a.only_hash)]
    rows, usage, failed = [], [], []
    for d in dialogs:
        got = None
        for _ in range(3):
            txt, u = call(key, a.model, JUDGE + json.dumps(d, ensure_ascii=False), 0)
            usage.append(u)
            got = check_labels(d, json_list(txt))
            if got is not None:
                break
        if got is None:
            failed.append(d["dialog"])
            print(f"[rd378k-teacher] {d['dialog']} unparsed", flush=True)
            continue
        rows += got
        print(f"[rd378k-teacher] {d['dialog']} ok", flush=True)
    (out / "labels.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    cost = sum(float(u.get("cost", 0) or 0) for u in usage)
    verdicts = [x for r in rows for x in r["verdicts"]]
    print(json.dumps({"dialogs": len(dialogs), "labelled": len(dialogs) - len(failed), "unparsed": len(failed),
                      "calls": len(usage), "notes": len(verdicts), **{v: verdicts.count(v) for v in VERDICTS},
                      "cost_usd": round(cost, 4)}))


def agree(a):
    lab = {(r["dialog"], int(r["t"])): r["verdicts"] for r in load(a.labels)}
    ver = {(r["dialog"], int(r["t"])): r["verdicts"] for r in load(a.verdicts)}
    pairs = []
    for k, vs in lab.items():
        if k in ver and len(ver[k]) == len(vs):
            pairs += [(x == "ok", y == "ok", y) for x, y in zip(vs, ver[k])]
    n = len(pairs)
    ag = sum(t == o for t, o, _ in pairs)
    pt, po = sum(t for t, _, _ in pairs) / max(1, n), sum(o for _, o, _ in pairs) / max(1, n)
    pe = pt * po + (1 - pt) * (1 - po)
    kappa = (ag / max(1, n) - pe) / (1 - pe) if pe < 1 else 0.0
    rep = {"compared": n, "teacher_ok": sum(t for t, _, _ in pairs), "judges_ok": sum(o for _, o, _ in pairs),
           "both_ok": sum(t and o for t, o, _ in pairs), "agree": ag, "kappa": round(kappa, 3),
           "judges_unsupported_teacher_ok": sum(t and y == "unsupported" for t, _, y in pairs),
           "judges_unsupported": sum(y == "unsupported" for _, _, y in pairs),
           "passes_label_rule": n > 0 and ag >= 0.85 * n and kappa >= 0.5}
    print(json.dumps(rep))
    return rep


def selftest():
    ok = 0
    chat = {"kind": "chat", "speakers": ["user", "assistant"], "date": "8 May 2023",
            "turns": [{"speaker": ["user", "assistant"][i % 2], "text": "hi"} for i in range(12)]}
    over = {"kind": "overheard", "speakers": ["Wren", "Tobin"], "date": "14 June 2022",
            "turns": [{"speaker": ["Wren", "Tobin"][i % 2], "text": "hey"} for i in range(13)]}
    assert check_batch([chat] * 4 + [over] * 4) is None
    assert check_batch([chat] * 5 + [over] * 3) == "not 4 chat + 4 overheard"
    assert check_dialog(dict(over, date="2023-05-08")) == "date"
    assert check_dialog(dict(chat, turns=chat["turns"][1:] + chat["turns"][:1])) == "speakers do not alternate"
    assert check_dialog(dict(over, turns=over["turns"][:11])) == "turn count"
    ok += 1
    d = {"dialog": "x", "turns": [{"t": 1, "speaker": "user", "text": "a", "notes": [{"text": "n"}, {"text": "m"}]},
                                  {"t": 2, "speaker": "assistant", "text": "b"},
                                  {"t": 3, "speaker": "user", "text": "c", "notes": []}]}
    good = [{"t": 1, "verdicts": ["ok", "unsupported"], "missed": 0}, {"t": 3, "verdicts": [], "missed": "1"}]
    assert check_labels(d, good) == [{"dialog": "x", "t": 1, "verdicts": ["ok", "unsupported"], "missed": 0},
                                     {"dialog": "x", "t": 3, "verdicts": [], "missed": 1}]
    assert check_labels(d, good[:1]) is None
    assert check_labels(d, [dict(good[0], verdicts=["ok"]), good[1]]) is None
    assert check_labels(d, [dict(good[0], verdicts=["ok", "maybe"]), good[1]]) is None
    assert json_list('text [{"a": 1}] more') == [{"a": 1}] and json_list("no list") is None
    ok += 1
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        L, V = Path(t) / "l.jsonl", Path(t) / "v.jsonl"
        L.write_text(json.dumps({"dialog": "x", "t": 1, "verdicts": ["ok", "ok", "unsupported", "bad_cite"]}) + "\n")
        V.write_text(json.dumps({"dialog": "x", "t": 1, "verdicts": ["ok", "unsupported", "unsupported", "ok"]}) + "\n")
        r = agree(argparse.Namespace(labels=str(L), verdicts=str(V)))
        assert r["compared"] == 4 and r["agree"] == 2 and r["judges_unsupported_teacher_ok"] == 1
        assert r["passes_label_rule"] is False
    ok += 1
    print(f"rd378k teacher selftest {ok}/3 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["write", "label", "agree", "selftest"])
    ap.add_argument("--out", default="")
    ap.add_argument("--judge-in", default="")
    ap.add_argument("--only-hash", type=int, default=1)
    ap.add_argument("--labels", default="")
    ap.add_argument("--verdicts", default="")
    ap.add_argument("--model", default="z-ai/glm-5.3-flash")
    a = ap.parse_args()
    if a.mode == "selftest":
        selftest()
        return
    if a.mode == "agree":
        agree(a)
        return
    key = (Path.home() / ".config" / "openrouter" / "key").read_text().strip()
    try:
        (write if a.mode == "write" else label)(a, key)
    finally:
        del key


if __name__ == "__main__":
    main()
