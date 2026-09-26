#!/usr/bin/env python3
"""rd-378g teacher job on the Mac (Trustworthy notes thread, 2026-09-26): the GLM teacher writes practice dialogs WITH
memory notes, so a note writer can be trained from the plain 1B with no Claude-written or Claude-judged row (Ben 16:39
"Use GLM"; Thread manager ruling 16:53: the rd-378 writer, trained on Opus-written notes, stays out of every build).
The recipe is rd-378's (artifacts/claude-rd378-20260925/data/WRITER_NOTES.md) with GLM in place of the Opus writers;
the teacher then grades its own notes with claude_rd378k_teacher.py label, and scripts/claude_rd378_data.py keeps a
turn only if every note is "ok" and nothing was missed, exactly as for rd-378. Standard library only.

writenotes  240 dialogs in 40 calls of 6 (3 chat + 3 overheard, 10-14 turns, notes on every non-assistant turn), each
            call with its own subject area and name letters. Structure and note form checked in code (cites in [-6, 0],
            never before turn 1, a "when" must appear in a cited turn); a call that breaks them is retried (3 tries).
            Output DIR/notes_w1.jsonl in the rd-378 notes format (ids kg-001.., t from 1; assistant turns carry no
            "notes" key, so the grader skips them).
              python -B scripts/claude_rd378g_teacher.py writenotes --out DIR [--model M]
split       python -B scripts/claude_rd378g_teacher.py split --file F --parts N   (F.0 .. F.N-1, round robin; counts only)
selftest    (no network)
Key rules as claude_rd378k_teacher.py: the key is read from ~/.config/openrouter/key into memory only, never printed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_rd378k_teacher import MONTHS, call, json_list  # noqa: E402

AREAS = ("a new pet", "moving to a new town", "a job change", "a school project", "a family trip", "a wedding",
         "a sports season", "learning an instrument", "a garden", "a house renovation", "a new friend", "a breakup",
         "a birthday party", "a hiking trip", "cooking for guests", "a work deadline", "a volunteering day",
         "a holiday abroad", "a sick relative", "buying a car", "a book club (invented titles)", "a new baby in the family",
         "a band rehearsal", "a road trip", "starting a small business", "exam season", "a neighbourhood fair",
         "a camping weekend", "a job interview", "a craft market", "a fishing trip", "a dance class", "a move abroad",
         "a surprise gift", "a lost item", "a new apartment", "a charity run", "a family reunion", "an art class",
         "a long commute")
LETTERS = "ABCDEFGHIJKLMNOPRSTVWYZ"

WRITE = """Write 6 realistic conversations with memory notes, as a JSON list of 6 objects. Each object has exactly the
keys "kind", "speakers", "date", "turns".
- 3 with kind "chat": a user talks with a personal assistant. speakers = ["user", "assistant"]. Turns alternate, starting
  with the user. The assistant's turns are short natural replies.
- 3 with kind "overheard": two friends, relatives or coworkers talk. speakers = their two first names. Turns alternate,
  starting with the first name.
- date: the day the conversation happens, like "8 May 2023", a different day for each, between 2021 and 2025.
- turns: 10 to 14 objects {"speaker", "text", "notes"}. "notes" is [] on every assistant turn.
Notes are short MEMORY NOTES about the turn they sit on: plain sentences worth remembering later (what happened, what is
planned, when, who said it, what someone likes or thinks, people and pets in their lives, changes over time). Each note
is {"text": ..., "cites": [...], "when": ... or null}:
- text: ONE plain sentence, third person, names not pronouns ("the user" for the user in chat dialogs), true to the cited
  turns only, nothing guessed. Plans stay plans ("Kai plans to ..."), hopes stay hopes, jokes, sarcasm and "what if" talk
  give no note, a claim about someone else stays a claim ("Mira said Tal quit his job"), a correction gives the corrected
  fact only.
- cites: offsets from the current turn: 0 = this turn, -1 = the previous turn, ... (never below -6, never before the
  first turn), listing every turn the note needs (a pronoun or "that" pointing back, an answer to a question).
- when: a time the chat itself gives for this note, copied exactly as typed ("last May", "next Friday", "in 2019",
  "yesterday"), else null. Never turn it into a calendar date.
- Turns with nothing worth remembering (greetings, small talk, reactions) have "notes": []. About 30% of non-assistant
  turns have no note.
Across the 6 conversations: many events, plans and preferences, several notes with a "when", several with a cite other
than 0, some changes over time; at most a quarter of the notes about who is related to whom.
Style of the messages: real texting, some typos in ordinary words (never in names), run-ons, mixed lengths (3 to 60
words). Topic for all 6: {area}. Fictional names only: invented first names from many cultures starting with the letters
{letters}, and made-up places; no real public figures, brands, or book, film or game titles.

Reply with ONLY the JSON list, no other text."""


def check_note(n, k, turns) -> str | None:
    if not isinstance(n, dict) or set(n) != {"text", "cites", "when"}:
        return "note keys"
    if not isinstance(n["text"], str) or not n["text"].strip():
        return "note text"
    c = n["cites"]
    if not isinstance(c, list) or not c or not all(isinstance(x, int) and -6 <= x <= 0 and k + x >= 0 for x in c):
        return "cites"
    w = n["when"]
    if w is not None:
        if not isinstance(w, str) or not w.strip():
            return "when"
        if not any(w.strip().lower() in turns[k + x]["text"].lower() for x in c):
            return "when not in a cited turn"
    return None


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
    if not isinstance(ts, list) or not 10 <= len(ts) <= 14:
        return "turn count"
    n_notes = 0
    for k, t in enumerate(ts):
        if not isinstance(t, dict) or set(t) != {"speaker", "text", "notes"} or not isinstance(t["text"], str) or \
                not t["text"].strip() or not isinstance(t["notes"], list):
            return "turn keys"
        if t["speaker"] != sp[k % 2]:
            return "speakers do not alternate"
        if r["kind"] == "chat" and t["speaker"] == "assistant" and t["notes"]:
            return "assistant turn has notes"
        for n in t["notes"]:
            bad = check_note(n, k, ts)
            if bad:
                return bad
        n_notes += len(t["notes"])
    return None if n_notes else "no notes"


def check_batch(rows) -> str | None:
    if not rows or len(rows) != 6:
        return "not 6 dialogs"
    for r in rows:
        bad = check_dialog(r)
        if bad:
            return bad
    kinds = sorted(r["kind"] for r in rows)
    return None if kinds == ["chat"] * 3 + ["overheard"] * 3 else "not 3 chat + 3 overheard"


def to_rows(rows, start):
    out = []
    for i, r in enumerate(rows):
        turns = []
        for k, t in enumerate(r["turns"]):
            row = {"t": k + 1, "speaker": t["speaker"], "text": t["text"]}
            if not (r["kind"] == "chat" and t["speaker"] == "assistant"):
                row["notes"] = [{"text": n["text"], "cites": n["cites"], "when": n["when"]} for n in t["notes"]]
            turns.append(row)
        out.append({"dialog": f"kg-{start + i + 1:03d}", "kind": r["kind"], "speakers": r["speakers"],
                    "date": r["date"], "turns": turns})
    return out


def writenotes(a, key):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    items, usage, seen = [], [], set()
    for b, area in enumerate(AREAS):
        letters = ", ".join(LETTERS[(3 * b + j) % len(LETTERS)] for j in range(3))
        rows = None
        for t in range(3):
            txt, u = call(key, a.model, WRITE.replace("{area}", area).replace("{letters}", letters), 0.9)
            usage.append(u)
            rows = json_list(txt)
            bad = check_batch(rows)
            firsts = None if bad else {r["turns"][0]["text"].strip().lower() for r in rows}
            if bad is None and not firsts & seen:
                break
            print(f"[rd378g-teacher] batch {b} try {t + 1}: {bad or 'repeats an earlier dialog'}", flush=True)
            rows = None
        if rows is None:
            print(f"[rd378g-teacher] batch {b} skipped after 3 tries", flush=True)
            continue
        seen |= {r["turns"][0]["text"].strip().lower() for r in rows}
        items += to_rows(rows, len(items))
        print(f"[rd378g-teacher] batch {b} ok ({len(items)} dialogs)", flush=True)
    (out / "notes_w1.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items),
                                        encoding="utf-8")
    cost = sum(float(u.get("cost", 0) or 0) for u in usage)
    tn = [t for x in items for t in x["turns"] if "notes" in t]
    print(json.dumps({"dialogs": len(items), "batches_skipped": len(AREAS) - len(items) // 6, "turns": len(tn),
                      "notes": sum(len(t["notes"]) for t in tn), "empty_turns": sum(not t["notes"] for t in tn),
                      "calls": len(usage), "cost_usd": round(cost, 4)}))


def split(a):
    lines = [x for x in Path(a.file).read_text(encoding="utf-8").splitlines() if x.strip()]
    for i in range(a.parts):
        Path(f"{a.file}.{i}").write_text("".join(x + "\n" for x in lines[i::a.parts]), encoding="utf-8")
    print(json.dumps({"lines": len(lines), "parts": [len(lines[i::a.parts]) for i in range(a.parts)]}))


def selftest():
    def turns(kind, sp, n):
        return [{"speaker": sp[k % 2], "text": "we got a dog last May" if k == 0 else "ok",
                 "notes": [] if (kind == "chat" and k % 2) else ([{"text": "The user got a dog.", "cites": [0],
                                                                   "when": "last May"}] if k == 0 else [])}
                for k in range(n)]
    chat = {"kind": "chat", "speakers": ["user", "assistant"], "date": "8 May 2023",
            "turns": turns("chat", ["user", "assistant"], 10)}
    over = {"kind": "overheard", "speakers": ["Wren", "Tobin"], "date": "14 June 2022",
            "turns": turns("overheard", ["Wren", "Tobin"], 12)}
    assert check_batch([chat] * 3 + [over] * 3) is None
    assert check_batch([chat] * 4 + [over] * 2) == "not 3 chat + 3 overheard"
    bad = json.loads(json.dumps(chat))
    bad["turns"][2]["notes"] = [{"text": "x", "cites": [-3], "when": None}]
    assert check_dialog(bad) == "cites"
    bad["turns"][2]["notes"] = [{"text": "x", "cites": [0], "when": "next week"}]
    assert check_dialog(bad) == "when not in a cited turn"
    bad["turns"][2]["notes"] = [{"text": "x", "cites": [-2], "when": "last may"}]
    assert check_dialog(bad) is None
    bad["turns"][1]["notes"] = [{"text": "x", "cites": [0], "when": None}]
    assert check_dialog(bad) == "assistant turn has notes"
    rows = to_rows([chat, over], 0)
    assert rows[0]["dialog"] == "kg-001" and "notes" not in rows[0]["turns"][1] and rows[0]["turns"][0]["t"] == 1
    assert rows[1]["turns"][1]["notes"] == []
    print("rd378g teacher selftest 1/1 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["writenotes", "split", "selftest"])
    ap.add_argument("--out", default="")
    ap.add_argument("--file", default="")
    ap.add_argument("--parts", type=int, default=4)
    ap.add_argument("--model", default="z-ai/glm-5.3-flash")
    a = ap.parse_args()
    if a.mode == "selftest":
        selftest()
        return
    if a.mode == "split":
        split(a)
        return
    key = (Path.home() / ".config" / "openrouter" / "key").read_text().strip()
    try:
        writenotes(a, key)
    finally:
        del key


if __name__ == "__main__":
    main()
