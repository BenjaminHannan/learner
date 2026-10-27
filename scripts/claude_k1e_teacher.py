#!/usr/bin/env python3
"""k1e teacher jobs on the Mac (Creative answers in chat thread, 2026-09-26): the open-weights teacher (GLM via
OpenRouter, the teacher Ben approved) writes the practice chats and labels the 1B's drafts for the learned critic
(scripts/claude_k1e_critic.py), so that no Claude-written text or Claude label is used for training. Standard library
only; Mac CPU; no model runs here.

Key rules: the key is read from ~/.config/openrouter/key into memory only. Never printed, logged or written.
The endpoint requires reasoning, so reasoning effort is low; the answer is read from the final message only
(as in scripts/claude_ideajudge_teacher.py, whose call pattern this copies).

write  240 practice chats (the same recipe as the DEV set and the test panels: 84 idea with 1 lead-in turn, 84 idea
       with none, 72 uses_facts with 1/2/3 teach turns, 24 each), in 12 calls of 20, each call given its own subject
       area so calls don't repeat each other. Structure is checked in code; a call that breaks it is retried (3 tries).
       ids kt-001..kt-240 in call order. Fixed 2026-09-26 after the first Mac run (k1e-teacher go1: 0 labelled, 0 chats):
       the teacher answers the judges' instructions with one JSON object per line, which the parser now accepts; a
       chat is checked on its own (a fact's value must share a word with the teach turns) and every chat that fits an
       open slot is kept, instead of all-or-nothing batches of 20.
         python -B scripts/claude_k1e_teacher.py write --out DIR [--model M]
label  the teacher judges draft replies with the blind judges' own instructions (JUDGE-k1a.md, same words), 10 lines
       per call; writes DIR/labels.jsonl {id, useful, made_up_user_facts}.
         python -B scripts/claude_k1e_teacher.py label --packet P.jsonl --out DIR [--model M]
agree  teacher labels vs the blind Opus judges' verdicts on the same DEV drafts. The rule for a label source (from the
       creative research thread, RESULTS-selfjudge.md): useful agreement >= 85% and kappa >= 0.5.
         python -B scripts/claude_k1e_teacher.py agree --labels DIR/labels.jsonl --key K.json --verdicts V.json
selftest (no network)
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

AREAS = ("hobbies and crafts", "work and coworkers", "family and relatives", "school and studying", "food and cooking",
         "travel and outings", "pets and animals", "home and chores", "neighbours and community", "sports and games",
         "music and performing", "gardening and the seasons")
BATCH = {"idea1": 7, "idea0": 7, "uf1": 2, "uf2": 2, "uf3": 2}

WRITE = """Write 20 short practice chats between one user and a personal assistant, as a JSON list of 20 objects. Each
object has exactly the keys "kind", "turns", "last", "facts". "turns" is the list of the user's earlier messages
(strings) and "last" is the user's final message, which asks the assistant for something creative. The assistant's
replies are not included.

Exactly these 20, in any order:
- 7 with kind "idea" and exactly 1 lead-in turn that sets the scene (an event, a project, a situation) without personal
  facts about the user, then a request that continues that chat naturally (it may lean on the lead-in, like "any names
  for it?"). facts: [].
- 7 with kind "idea" and turns: [] (no lead-in); the request is complete by itself. facts: [].
- 6 with kind "uses_facts": 2 with 1 teach turn, 2 with 2 teach turns, 2 with 3 teach turns. In the teach turns the
  user tells facts about themselves or a named person or pet (friend, sister, neighbour, coworker, grandparent,
  dog...); then a request where a good answer uses those facts (for example a card for a named friend who loves
  sailing). facts = a list of {"owner": "USER" or the person's or pet's name, "relation": a short lowercase
  snake_case word, "value": a short value}, matching the teach turns exactly.

Subject area for all 20: {area}. Forms, mixed: brainstorm lists (names for a club, team, shop or event; party themes;
ways to reuse something; plot twists; activity ideas; gift ideas), short pieces (a four-line poem, a limerick, a toast,
a slogan, a two-sentence story, a short card or note, a haiku), fresh angles on a problem (make chores fun, a cheaper
weekend, a rainy-day plan). About half the requests name a count ("3 ideas", "5 names", "four lines"). Every request
must be clear and answerable in a short reply; some simple, some with two or three constraints. Realistic casual chat
style (some lowercase, some without question marks, some polite, some terse). Fictional names only: unusual invented
first names and made-up places; no real public figures, brands, or book, film or game titles. No two chats with the
same subject.

Reply with ONLY the JSON list, no other text."""

JUDGE = """You are judging replies from personal assistants. Each line of the packet is one short chat: `chat` is the user's
earlier messages (possibly none), `request` is the user's last message, and `reply` is one assistant's answer to
that request. Several different assistants' replies are mixed together; you don't know which wrote which, and it
doesn't matter. Judge each line on its own.

For every line, write one JSON object on its own line: {"id": <the line's id>, "useful": "yes" or "no",
"made_up_user_facts": <integer>, "reason": <one short sentence>}.
- useful = "yes" only if the reply is on topic for the request in its chat, fits the form asked for (for example
  the number of ideas asked, a four-line poem, a limerick, a toast, a slogan, a card), and is not generic filler.
  Otherwise "no". A reply that ignores what the earlier messages said, when the request depends on them, is not on
  topic.
- made_up_user_facts = how many statements in the reply present something about the user, or about the people or
  pets they mention, as fact when the chat never said it. Suggestions and ideas phrased as suggestions don't count.
- reason: one short sentence, in your own words.
Write exactly one object per packet line, same ids, nothing else in the file."""
JUDGE_TAIL = "\n\nReply with ONLY a JSON list of these objects, one per packet line below, in order.\n\nPacket:\n"


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
            print(f"[k1e-teacher] try {i + 1} failed: {type(e).__name__} {str(e)[:120]}", flush=True)
            time.sleep(2 ** (i + 1))
    return "", {}


def json_list(txt):
    """A JSON list anywhere in the text, else the JSON objects written one per line (the judges' own format)."""
    m = re.search(r"\[.*\]", txt, re.S)
    if m:
        try:
            v = json.loads(m.group(0))
            if isinstance(v, list):
                return v
        except json.JSONDecodeError:
            pass
    rows = []
    for line in txt.splitlines():
        line = line.strip().rstrip(",")
        if line.startswith("{") and line.endswith("}"):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                return None
    return rows or None


def _words(t: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) >= 3}


def chat_kind(r) -> str:
    """The recipe slot a chat fills (idea1, idea0, uf1, uf2, uf3), else "bad: <why>"."""
    if not isinstance(r, dict) or set(r) != {"kind", "turns", "last", "facts"}:
        return "bad: keys"
    if not isinstance(r["turns"], list) or not all(isinstance(t, str) and t.strip() for t in r["turns"]):
        return "bad: turns"
    if not isinstance(r["last"], str) or not r["last"].strip() or not isinstance(r["facts"], list):
        return "bad: last/facts"
    n = len(r["turns"])
    if r["kind"] == "idea" and n in (0, 1) and not r["facts"]:
        return f"idea{n}"
    if r["kind"] == "uses_facts" and n in (1, 2, 3) and r["facts"]:
        said = " ".join(r["turns"]).lower()
        for f in r["facts"]:
            if not isinstance(f, dict) or set(f) != {"owner", "relation", "value"}:
                return "bad: fact keys"
            if not re.fullmatch(r"[a-z][a-z_]*", str(f["relation"])):
                return "bad: relation"
            if f["owner"] != "USER" and str(f["owner"]).lower() not in said:
                return "bad: fact owner not in teach turns"
            if not (_words(str(f["value"])) & _words(said)) and str(f["value"]).lower() not in said:
                return "bad: fact value not in teach turns"
        return f"uf{n}"
    return "bad: kind/turn count"


def check_batch(rows) -> str | None:
    """None if the 20 chats follow the recipe exactly, else the first problem found (used by selftest only)."""
    if not rows or len(rows) != 20:
        return "not 20 chats"
    got = {k: 0 for k in BATCH}
    for r in rows:
        k = chat_kind(r)
        if k.startswith("bad"):
            return k[5:]
        got[k] += 1
    return None if got == BATCH else f"mix {got}"


def write(a, key, max_calls: int = 40):
    """Calls cycle through the 12 subject areas; every chat that fits the recipe and a slot still open is kept, until
    all 240 slots (84 idea1, 84 idea0, 24 each uf1-3) are filled or max_calls is reached."""
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    need = {k: v * len(AREAS) for k, v in BATCH.items()}
    items, usage, seen, why = [], [], set(), {}
    for c in range(max_calls):
        if not any(need.values()):
            break
        txt, u = call(key, a.model, WRITE.replace("{area}", AREAS[c % len(AREAS)]), 0.9)
        usage.append(u)
        kept = 0
        for r in json_list(txt) or []:
            k = chat_kind(r)
            if k.startswith("bad"):
                why[k] = why.get(k, 0) + 1
                continue
            last = r["last"].strip().lower()
            if need[k] == 0 or last in seen:
                why["slot full or repeat"] = why.get("slot full or repeat", 0) + 1
                continue
            need[k] -= 1
            seen.add(last)
            kept += 1
            items.append({"item_id": f"kt-{len(items) + 1:03d}", "kind": r["kind"], "turns": r["turns"],
                          "last": r["last"], "facts": r["facts"], "numbers": None, "target": None, "gold_expr": None})
        print(f"[k1e-teacher] call {c} kept {kept} ({len(items)} chats)", flush=True)
    (out / "items.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items), encoding="utf-8")
    cost = sum(float(u.get("cost", 0) or 0) for u in usage)
    print(json.dumps({"chats": len(items), "complete": not any(need.values()), "open_slots": need,
                      "rejected": why, "calls": len(usage), "cost_usd": round(cost, 4)}))


def label(a, key):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lines = load(a.packet)
    rows, usage, failed = [], [], []
    for s in range(0, len(lines), 10):
        chunk = [{k: x[k] for k in ("id", "chat", "request", "reply")} for x in lines[s:s + 10]]
        want = [x["id"] for x in chunk]
        got = None
        for _ in range(3):
            txt, u = call(key, a.model, JUDGE + JUDGE_TAIL + "\n".join(json.dumps(x, ensure_ascii=False)
                                                                        for x in chunk), 0)
            usage.append(u)
            v = json_list(txt)
            if v and [str(r.get("id")) for r in v if isinstance(r, dict)] == want:
                got = v
                break
        if got is None:
            failed += want
            print(f"[k1e-teacher] lines {s}-{s + len(chunk) - 1} unparsed", flush=True)
            continue
        rows += [{"id": r["id"], "useful": "yes" if str(r.get("useful")).strip().lower() == "yes" else "no",
                  "made_up_user_facts": int(r.get("made_up_user_facts") or 0)} for r in got]
        print(f"[k1e-teacher] lines {s}-{s + len(chunk) - 1} ok", flush=True)
    (out / "labels.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    cost = sum(float(u.get("cost", 0) or 0) for u in usage)
    print(json.dumps({"lines": len(lines), "labelled": len(rows), "unparsed": len(failed), "calls": len(usage),
                      "useful_yes": sum(r["useful"] == "yes" for r in rows), "cost_usd": round(cost, 4)}))


def agree(a):
    lab = {r["id"]: r["useful"] == "yes" for r in load(a.labels)}
    key = json.loads(Path(a.key).read_text(encoding="utf-8"))
    ver = json.loads(Path(a.verdicts).read_text(encoding="utf-8"))
    pairs = [(lab[i], bool(ver[f"{k['item_id']}\t{k['reply']}"])) for i, k in key.items()
             if i in lab and f"{k['item_id']}\t{k['reply']}" in ver]
    n = len(pairs)
    ag = sum(t == o for t, o in pairs)
    pt, po = sum(t for t, _ in pairs) / max(1, n), sum(o for _, o in pairs) / max(1, n)
    pe = pt * po + (1 - pt) * (1 - po)
    kappa = (ag / max(1, n) - pe) / (1 - pe) if pe < 1 else 0.0
    rep = {"compared": n, "teacher_useful": sum(t for t, _ in pairs), "opus_useful": sum(o for _, o in pairs),
           "both_useful": sum(t and o for t, o in pairs), "agree": ag, "kappa": round(kappa, 3),
           "passes_label_rule": n > 0 and ag >= 0.85 * n and kappa >= 0.5}
    print(json.dumps(rep))
    return rep


def selftest():
    ok = 0
    one = {"kind": "idea", "turns": ["x"], "last": "r", "facts": []}
    zero = {"kind": "idea", "turns": [], "last": "r", "facts": []}

    def uf(n):
        return {"kind": "uses_facts", "turns": ["my dog Pip loves naps"] + ["ok"] * (n - 1), "last": "r",
                "facts": [{"owner": "Pip", "relation": "loves", "value": "naps"}]}
    good = [one] * 7 + [zero] * 7 + [uf(1)] * 2 + [uf(2)] * 2 + [uf(3)] * 2
    assert check_batch(good) is None
    assert check_batch(good[:-1]) == "not 20 chats"
    bad = [dict(x) for x in good]
    bad[-1] = {**uf(3), "facts": [{"owner": "Pip", "relation": "loves", "value": "sailing"}]}
    assert check_batch(bad) == "fact value not in teach turns"
    bad[-1] = {**one}
    assert check_batch(bad).startswith("mix")
    ok += 1
    assert json_list('text [{"a": 1}] more') == [{"a": 1}] and json_list("no list") is None
    assert json_list('{"id": "E0", "useful": "yes"}\n{"id": "E1", "useful": "no"}') == [
        {"id": "E0", "useful": "yes"}, {"id": "E1", "useful": "no"}]
    assert chat_kind({**uf(1), "facts": [{"owner": "Pip", "relation": "loves", "value": "long naps"}]}) == "uf1"
    ok += 1
    print(f"k1e teacher selftest {ok}/2 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["write", "label", "agree", "selftest"])
    ap.add_argument("--out", default="")
    ap.add_argument("--packet", default="")
    ap.add_argument("--labels", default="")
    ap.add_argument("--key", default="")
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
