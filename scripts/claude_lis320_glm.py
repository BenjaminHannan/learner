#!/usr/bin/env python3
"""lis-320 pilot, step 2 of 3: GLM writes the wording for each dialog seed (one OpenRouter call per dialog).

Input: claude_lis320_seed.py output. For every turn GLM gets the intent (described in the abstract), the facts chosen by
code, the strings that MUST appear verbatim and the strings that must NOT appear. The instruction holds no example
sentences or phrasings: all wording comes from GLM. GLM returns JSON: per turn, the assistant's short reply just
before the user's message ("reply_before") and the user's message ("user").

Key rules (as claude_ideajudge_teacher.py): the key is read from ~/.config/openrouter/key into memory only. Never
printed, logged or written. If any model output contains "sk-or", nothing more is written and the run aborts.

python3 claude_lis320_glm.py --seeds seeds.jsonl --out raw.jsonl [--model z-ai/glm-5.3-flash] [--temperature 1.0]
        [--limit N]                  resumes: dialog ids already in --out are skipped
python3 claude_lis320_glm.py --seeds seeds.jsonl --dry-run [--dialog ID]   prints one prompt, no API call
python3 claude_lis320_glm.py --selftest                                     fake reply, no network
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

MODEL = "z-ai/glm-5.3-flash"
KEY_MARK = "sk-or"

HEAD = """You are writing training data: realistic text chats between a user and a personal assistant app. Below is the plan for ONE conversation. Code chose every fact; your job is only the wording.

For each numbered turn write two strings:
- "reply_before": what the assistant said just before this user message, reacting briefly to the user's previous message. At most about 15 words. It states no facts, guesses nothing, does not ask about anything the plan has not reached yet, and uses no name the user has not already typed. {opener}
- "user": the user's message for this turn, following the turn's plan.

How the user writes: like a real person texting on a phone. Casual, often all lowercase, sometimes run-on sentences or missing punctuation, occasional small typos in ordinary words, varied lengths (very short to a few sentences) and varied openings. Every message should sound different from the others. Do not greet in every message.

Hard rules (a message that breaks one is thrown away):
1. Each MUST INCLUDE string appears in that user message spelled exactly as given, letter for letter. Typing it all in lowercase is fine; nothing else may change: no typo, plural, hyphen, nickname or abbreviation inside it.
2. No MUST NOT INCLUDE string appears in that user message. Where the turn says "also not in reply_before", it must not appear in that turn's reply_before either.
3. A user message says only what its plan says: no other facts about anyone, the user included (no other jobs, places, pets, ages, relatives, likes or names). After the turn that introduced a person, do not say again how they are related to the user, unless the plan says to refer to them by their role.
4. "first person" means the user speaks about themself.
5. A relation's value is exactly the given value; do not add words inside it.

People in this conversation (name: relation to the user, gender). Only use a name in the turns whose MUST INCLUDE lists it:
{people}

Turns:
{turns}

Answer with ONLY this JSON and no other text:
{{"turns": [{{"n": 1, "reply_before": "...", "user": "..."}}, ... one object per turn, n = 1 to {n}]}}
"""

OPENER_YES = ('For turn 1, reply_before is a short opening line from the assistant (no names, no questions about '
              'people).')
OPENER_NO = 'For turn 1, reply_before is "" (the user starts the chat).'


def q(s):
    return json.dumps(s, ensure_ascii=False)


def turn_block(t) -> str:
    lines = [f"Turn {t['k']}. intent: {t['intent']}. {t['gloss']}."]
    lines += [f"  {x}" for x in t["lines"]]
    inc = [q(s) for s in t["must"]]
    if t.get("first_person"):
        inc.append("first person")
    for alts in t.get("role_words") or []:
        inc.append("a word that makes the role clear: " + " / ".join(alts))
    if t.get("ref"):
        if t["ref"]["kind"] == "pronoun":
            inc.append("a " + ("she/her" if t["ref"]["gender"] == "f" else "he/him/his") + " pronoun for that person")
        else:
            inc.append("the role word " + q(t["ref"]["words"][0]))
    lines.append("  MUST INCLUDE: " + (", ".join(inc) if inc else "(nothing)"))
    nots = [q(s) for s in t.get("must_not") or []]
    if nots:
        also = [s for s in t.get("must_not") or [] if s in (t.get("reply_must_not") or [])]
        lines.append("  MUST NOT INCLUDE: " + ", ".join(nots) + (" (also not in reply_before)" if also else ""))
    return "\n".join(lines)


def build_prompt(d) -> str:
    people = "\n".join(f"- {p['name']}: the user's {p['role'].replace('_', ' ')}, "
                       f"{'female' if p['gender'] == 'f' else 'male'}" for p in d["people"])
    return HEAD.format(opener=OPENER_YES if d.get("opener") else OPENER_NO, people=people,
                       turns="\n".join(turn_block(t) for t in d["turns"]), n=len(d["turns"]))


def parse(txt, n):
    m = re.search(r"\{.*\}", txt or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    ts = d.get("turns") if isinstance(d, dict) else None
    if not isinstance(ts, list) or len(ts) != n:
        return None
    out = []
    for i, t in enumerate(ts):
        if not isinstance(t, dict) or not isinstance(t.get("user"), str) or not t["user"].strip():
            return None
        rb = t.get("reply_before", "")
        out.append({"n": i + 1, "reply_before": rb if isinstance(rb, str) else "", "user": t["user"]})
    return {"turns": out}


class KeyLeak(Exception):
    pass


def guard(*texts):
    if any(KEY_MARK in str(x) for x in texts):
        raise KeyLeak("model output contains the key marker; aborting, nothing written for this dialog")


def call(key, model, text, temperature, tries=4):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": text}], "temperature": temperature,
                       "max_tokens": 8000, "reasoning": {"effort": "low"}}).encode()
    for i in range(tries):
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body, headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode())
            return d["choices"][0]["message"]["content"] or "", d.get("usage", {})
        except Exception as e:                        # the message of an HTTP error never carries the key
            print(f"[glm320] try {i + 1} failed: {type(e).__name__} {str(e)[:120]}", flush=True)
            time.sleep(2 ** (i + 1))
    return "", {}


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def run(seeds, out_path, caller, model, temperature):
    """caller(prompt) -> (text, usage). Appends one JSON line per dialog to out_path."""
    out = Path(out_path)
    done = {r["dialog_id"] for r in load(out)} if out.exists() else set()
    tot = {"calls": 0, "parsed": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "skipped": 0}
    with out.open("a", encoding="utf-8") as fh:
        for d in seeds:
            if d["dialog_id"] in done:
                tot["skipped"] += 1
                continue
            prompt = build_prompt(d)
            txt, u = caller(prompt)
            guard(txt, json.dumps(u))
            got = parse(txt, len(d["turns"]))
            tot["calls"] += 1
            tot["parsed"] += got is not None
            tot["prompt_tokens"] += int(u.get("prompt_tokens", 0) or 0)
            tot["completion_tokens"] += int(u.get("completion_tokens", 0) or 0)
            tot["cost_usd"] += float(u.get("cost", 0) or 0)
            fh.write(json.dumps({"dialog_id": d["dialog_id"], "model": model, "temperature": temperature,
                                 "prompt_chars": len(prompt), "parsed": got, "raw": txt, "usage": u},
                                ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[glm320] {d['dialog_id']} {'ok' if got else 'unparsed'}", flush=True)
    tot["cost_usd"] = round(tot["cost_usd"], 5)
    return tot


def selftest():
    import tempfile
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from claude_lis320_seed import make_seeds
    d = make_seeds(1, 1)[0]
    p = build_prompt(d)
    for t in d["turns"]:
        for s in t["must"] + t["must_not"]:
            assert q(s) in p, s
    assert "used to" not in p.lower() and KEY_MARK not in p
    n = len(d["turns"])
    fake = json.dumps({"turns": [{"n": i + 1, "reply_before": "" if i == 0 else "ok", "user": f"msg {i}"}
                                 for i in range(n)]})
    assert parse("sure! " + fake, n)["turns"][2]["user"] == "msg 2"
    assert parse(fake, n + 1) is None and parse("no json", n) is None
    try:
        guard("here you go sk-or-v1-xxxx")
        raise AssertionError("guard missed the key marker")
    except KeyLeak:
        pass
    with tempfile.TemporaryDirectory() as td:
        outp = Path(td) / "raw.jsonl"
        tot = run([d], outp, lambda _p: (fake, {"prompt_tokens": 1000, "completion_tokens": 400, "cost": 0.001}),
                  MODEL, 1.0)
        assert tot["calls"] == 1 and tot["parsed"] == 1 and tot["completion_tokens"] == 400, tot
        tot2 = run([d], outp, lambda _p: ("", {}), MODEL, 1.0)
        assert tot2["skipped"] == 1 and tot2["calls"] == 0
        try:
            run([make_seeds(1, 2)[1]], outp, lambda _p: ("leak sk-or-abc", {}), MODEL, 1.0)
            raise AssertionError("leak not caught")
        except KeyLeak:
            pass
        assert len(load(outp)) == 1
    print(f"glm selftest OK: prompt {len(p)} chars for {n} turns; parse, resume and key guard checked")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds")
    ap.add_argument("--out")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dialog")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    seeds = load(a.seeds)
    if a.dry_run:
        d = next(x for x in seeds if x["dialog_id"] == a.dialog) if a.dialog else seeds[0]
        print(build_prompt(d))
        return
    if a.limit:
        seeds = seeds[: a.limit]
    key = (Path.home() / ".config" / "openrouter" / "key").read_text().strip()
    try:
        tot = run(seeds, a.out, lambda p: call(key, a.model, p, a.temperature), a.model, a.temperature)
    except KeyLeak as e:
        del key
        raise SystemExit(f"[glm320] ABORT: {e}")
    del key
    print(json.dumps(tot))


if __name__ == "__main__":
    sys.exit(main())
