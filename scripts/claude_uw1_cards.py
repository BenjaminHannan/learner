#!/usr/bin/env python3
"""uw-1: does showing the old notes let the plain 1B catch corrections? (wrong-as-fact thread, 2026-09-26). New file.

The textbook fix for stale facts is to supersede on write: when a new message arrives, the writer sees the old note
and decides whether the message changes it (Mem0's UPDATE step; brain: reconsolidation, a reactivated memory that
meets a mismatch is rewritten). Our reader never sees the notebook (claude_lis319_common.py build_prompt_hist). This
card test asks one thing: with the SAME plain MiniCPM5-1B and the SAME prompt, does adding the current notes (arm B)
to the earlier user turns (arm A has only those) make it name corrections right without changing notes on
look-alike messages? No training. The notes are the true facts at that turn (oracle), so finding notes is not
tested, only using them.

Cards
  one per user turn: the life's earlier user turns (oldest first), the new user message, and for arm B the notes
  valid just before that turn. gold = CHANGE (owner, new value, old value) on a correction turn, else NONE.
  --dev   the lis-320 GLM pilot dialogs (readable DEV; code-seeded gold; builder-outbox) for format and timing only
  --bank  a 331-format bank (turns, truth, corrections, decoys); the sealed panel is read by code only
Output (one line): "CHANGE | whose fact | what | new value" or "NONE".
Grades (code): on a correction card RIGHT (owner matches, new value named, old value not named), WRONG_CHANGE,
MISSED (NONE) or UNPARSED; on any other card OK_NONE, FALSE_CHANGE or UNPARSED. Prints counts only.

  python -B scripts/claude_uw1_cards.py run --model DIR --arm A|B (--dev DIR | --bank DIR) --out ROWS.jsonl [--limit N]
  python -B scripts/claude_uw1_cards.py count ROWS_A.jsonl ROWS_B.jsonl
  python -B scripts/claude_uw1_cards.py --selftest
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

MAX_NEW = 40
USER = "USER"
USER_WORDS = {"user", "me", "i", "you", "the user", "myself", "me (the user)"}

SYSTEM = "You keep a notebook of facts about the user and the people and pets in the user's life."
QUESTION = ("Does the new message change one of the facts {where} to a new value, because the user corrects it or "
            "because it has changed?\n"
            "If yes, answer with exactly one line: CHANGE | whose fact | what | new value\n"
            "If not, answer with exactly one line: NONE")
WHERE = {"A": "the user told you before", "B": "in your notebook"}
# second DEV format (arm B only; added 20:17 UTC (date -u) after the first DEV run, before any sealed item exists): point at a note
QUESTION_NOTE = ("Does the new message change one of the notes in your notebook to a new value, because the user "
                 "corrects it or because it has changed?\n"
                 "If yes, answer with exactly one line: UPDATE note number | new value\n"
                 "If not, answer with exactly one line: NONE")


def ld(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


# ---------------------------------------------------------------- cards
def _owner_text(owner: str) -> str:
    return "me (the user)" if owner == USER else owner


def cards_bank(panel: Path) -> list[dict]:
    """331-format bank. Notes before turn i = facts taught before i and not closed before i."""
    turns = ld(panel / "turns.jsonl")
    truth = ld(panel / "truth.jsonl")
    fact = {f["fact_id"]: f for f in truth}
    corr = {(c["life_id"], c["turn_index"]): c for c in ld(panel / "corrections.jsonl")}
    decoy = {(d["life_id"], d["turn_index"]) for d in ld(panel / "decoys.jsonl")} \
        if (panel / "decoys.jsonl").exists() else set()
    lives = defaultdict(list)
    for t in turns:
        lives[t["life_id"]].append(t)
    by_life = defaultdict(list)
    for f in truth:
        by_life[f["life_id"]].append(f)
    cards = []
    for life_id in sorted(lives):
        life = sorted(lives[life_id], key=lambda t: t["turn_index"])
        for t in life:
            i = t["turn_index"]
            notes = [f for f in sorted(by_life[life_id], key=lambda f: (f["taught_turn"], f["fact_id"]))
                     if f["taught_turn"] < i and (f["valid_until_turn"] is None or f["valid_until_turn"] >= i)]
            c = corr.get((life_id, i))
            if c is not None:
                new, old = fact[c["new_fact"]], fact[c["old_fact"]]
                gold = {"type": "CHANGE", "owner": new["owner"], "value": str(new["value"]),
                        "old": str(old["value"]), "style": str(c["style"])}
                group = "correct"
            else:
                gold = {"type": "NONE"}
                group = "decoy" if (life_id, i) in decoy else t["kind"]
            cards.append({"card": f"{life_id}:{i}", "group": group, "gold": gold, "text": t["user_text"],
                          "earlier": [x["user_text"] for x in life if x["turn_index"] < i],
                          "notes": [(_owner_text(f["owner"]), str(f["relation"]).replace("_", " "), str(f["value"]))
                                    for f in notes]})
    return cards


def cards_dev320(root: Path) -> tuple[list[dict], Counter]:
    """lis-320 pilot dialogs (seeds.jsonl + kept.jsonl per pilot folder). Only kept turns are cards; notes come from
    the gold ASSERT/CORRECT facts of earlier kept turns (a CORRECT replaces the same owner and relation)."""
    cards, skipped = [], Counter()
    for pdir in sorted(p for p in root.iterdir() if (p / "seeds.jsonl").exists()):
        kept = {k["id"]: k for k in ld(pdir / "kept.jsonl")}
        for s in ld(pdir / "seeds.jsonl"):
            notes: dict = {}
            earlier = []
            for t in sorted(s["turns"], key=lambda t: t["k"]):
                kid = f"glm320-{s['dialog_id']}-t{t['k']}"
                row = kept.get(kid)
                facts = t["gold"]["facts"]
                owner = lambda f: USER if f["owner"] == "me" else f["owner"]  # noqa: E731
                if row is not None:
                    cor = [f for f in facts if f.get("mode") == "CORRECT"]
                    gold, group = {"type": "NONE"}, t["intent"]
                    if t["intent"] == "correct":
                        key = (owner(cor[0]), cor[0]["rel"]) if len(cor) == 1 else None
                        if key is None or key not in notes:
                            skipped["correct_old_not_in_notes"] += 1
                            gold = None
                        else:
                            gold = {"type": "CHANGE", "owner": key[0], "value": cor[0]["value"],
                                    "old": notes[key], "style": "dev"}
                    else:
                        for f in facts:
                            key = (owner(f), f["rel"])
                            if f.get("mode") == "ASSERT" and key in notes and notes[key].lower() != f["value"].lower():
                                skipped["implicit_change"] += 1
                                gold = None
                                break
                            if f.get("mode") == "FORMER" and notes.get(key, "").lower() == f["value"].lower():
                                skipped["former_of_current"] += 1
                                gold = None
                                break
                    if gold is not None:
                        cards.append({"card": kid, "group": group, "gold": gold, "text": row["turn"],
                                      "earlier": list(earlier),
                                      "notes": [(_owner_text(o), r, v) for (o, r), v in notes.items()]})
                    for f in facts:
                        if f.get("mode") in ("ASSERT", "CORRECT"):
                            notes[(owner(f), f["rel"])] = f["value"]
                    earlier.append(row["turn"])
                else:
                    skipped["turn_not_kept"] += 1
                    # a dropped turn's text is unknown to the card and its facts never become notes
    return cards, skipped


def messages(card: dict, arm: str, fmt: str = "owner") -> list[dict]:
    parts = []
    if arm == "B":
        lines = [f"{i}. {o} | {r} | {v}" for i, (o, r, v) in enumerate(card["notes"], 1)] or ["(empty)"]
        parts.append("Your notebook now:\n" + "\n".join(lines))
    parts.append("What the user told you before, oldest first:\n"
                 + ("\n".join(f"- {x}" for x in card["earlier"]) or "(nothing)"))
    parts.append(f"The user's new message:\n{card['text']}")
    parts.append(QUESTION_NOTE if fmt == "note" else QUESTION.format(where=WHERE[arm]))
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n\n".join(parts)}]


# ---------------------------------------------------------------- parse and grade
_CHANGE = re.compile(r"^\W*change\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*(.+?)\s*$", re.I)
_NONE = re.compile(r"^\W*none\W*$", re.I)
_UPDATE = re.compile(r"^\W*update\s*(?:note\s*)?#?(\d+)\s*\|\s*(.+?)\s*$", re.I)


def parse_note(out: str, notes: list) -> dict:
    """UPDATE N | value -> a CHANGE whose owner is note N's owner (code resolves the pointer)."""
    for line in str(out).splitlines():
        line = line.strip().strip("`*").strip()
        if not line:
            continue
        m = _UPDATE.match(line)
        if m:
            n = int(m.group(1))
            if not 1 <= n <= len(notes):
                return {"type": "UNPARSED"}
            o, r, v = notes[n - 1]
            return {"type": "CHANGE", "owner": o, "what": r, "value": m.group(2), "note_value": v}
        if _NONE.match(line):
            return {"type": "NONE"}
        return {"type": "UNPARSED"}
    return {"type": "UNPARSED"}


def parse(out: str) -> dict:
    for line in str(out).splitlines():
        line = line.strip().strip("`*").strip()
        if not line:
            continue
        m = _CHANGE.match(line)
        if m:
            return {"type": "CHANGE", "owner": m.group(1), "what": m.group(2), "value": m.group(3)}
        if _NONE.match(line):
            return {"type": "NONE"}
        return {"type": "UNPARSED"}
    return {"type": "UNPARSED"}


def _vmatch(text: str, value: str) -> bool:
    v = str(value).strip().lower()
    return bool(v) and re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", str(text).lower()) is not None


def owner_ok(said: str, gold_owner: str) -> bool:
    s = re.sub(r"\(.*?\)", "", str(said)).strip().strip(".'\"").lower()
    s = re.sub(r"'s$", "", s)
    if gold_owner == USER:
        return s in USER_WORDS or str(said).strip().lower() in USER_WORDS
    g = str(gold_owner).strip().lower()
    return s == g or s == g.split()[0]


def grade(card: dict, p: dict) -> str:
    g = card["gold"]
    if p["type"] == "UNPARSED":
        return "UNPARSED"
    if g["type"] == "NONE":
        return "OK_NONE" if p["type"] == "NONE" else "FALSE_CHANGE"
    if p["type"] == "NONE":
        return "MISSED"
    if "note_value" in p and str(p["note_value"]).lower() != g["old"].lower():
        return "WRONG_CHANGE"  # pointed at a note other than the one being corrected
    right = owner_ok(p["owner"], g["owner"]) and _vmatch(p["value"], g["value"]) \
        and not (g["old"].lower() != g["value"].lower() and _vmatch(p["value"], g["old"]))
    return "RIGHT" if right else "WRONG_CHANGE"


def report_extra(card: dict, p: dict) -> str | None:
    """Report-only reason for a WRONG_CHANGE: value right but owner not matched, or other."""
    if card["gold"]["type"] != "CHANGE" or p["type"] != "CHANGE":
        return None
    if _vmatch(p["value"], card["gold"]["value"]) and not owner_ok(p["owner"], card["gold"]["owner"]):
        return "value_right_owner_not_matched"
    return None


# ---------------------------------------------------------------- run
class Gen:
    """Greedy chat on the plain MiniCPM5-1B, thinking off (the 338 render), MAX_NEW new tokens."""

    def __init__(self, model_dir: str):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if self.dev == "cuda" else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=dtype,
                                                          trust_remote_code=True).to(self.dev).eval()

    def greedy_chat(self, msgs) -> str:
        text = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        ids = self.tok(text, return_tensors="pt").to(self.dev)
        with self.torch.no_grad():
            out = self.model.generate(**ids, max_new_tokens=MAX_NEW, do_sample=False,
                                      pad_token_id=self.tok.eos_token_id)
        return self.tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def run(gen, cards: list[dict], arm: str, out: Path, log=print, fmt: str = "owner") -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("", encoding="utf-8")
    c, t0 = Counter(), time.time()
    for k, card in enumerate(cards, 1):
        raw = gen.greedy_chat(messages(card, arm, fmt))
        p = parse_note(raw, card["notes"]) if fmt == "note" else parse(raw)
        g = grade(card, p)
        c[(card["group"], g)] += 1
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"card": card["card"], "arm": arm, "group": card["group"], "raw": raw,
                                 "parsed": p, "grade": g, "extra": report_extra(card, p)},
                                ensure_ascii=False) + "\n")
        if k % 25 == 0:
            log(f"[uw1] {arm} {k}/{len(cards)} {round((time.time() - t0) / k, 1)} s/card")
    return {"arm": arm, "cards": len(cards), "minutes": round((time.time() - t0) / 60, 1),
            "by_group_grade": {f"{a}|{b}": n for (a, b), n in sorted(c.items())}}


def count(rows: list[dict]) -> dict:
    c = Counter()
    for r in rows:
        c[r["grade"]] += 1
        c[f"{r['group']}|{r['grade']}"] += 1
        if r.get("extra"):
            c[f"extra|{r['extra']}"] += 1
    return dict(sorted(c.items()))


# ---------------------------------------------------------------- selftest
class _FakeGen:
    """Says CHANGE with the gold owner and value on correction cards when it sees notes, else NONE."""

    def greedy_chat(self, msgs):
        u = msgs[-1]["content"]
        m = re.search(r"CORR:(\S+):(\S+)", u)
        if m and "Your notebook now" in u:
            return f"CHANGE | {m.group(1)} | x | {m.group(2)}"
        return "NONE"


def selftest() -> None:
    assert parse("CHANGE | Nulinim | city | Bralindale") == {"type": "CHANGE", "owner": "Nulinim", "what": "city",
                                                             "value": "Bralindale"}
    assert parse("  NONE.") == {"type": "NONE"} and parse("Sure! NONE")["type"] == "UNPARSED"
    assert parse("**CHANGE | me (the user) | job | welder**")["owner"] == "me (the user)"
    card = {"gold": {"type": "CHANGE", "owner": "Nulinim", "value": "Bralindale", "old": "Galyaford"}}
    assert grade(card, parse("CHANGE | Nulinim (husband) | city | bralindale")) == "RIGHT"
    assert grade(card, parse("CHANGE | nulinim | city | Bralindale, not Galyaford")) == "WRONG_CHANGE"
    assert grade(card, parse("CHANGE | my husband | city | Bralindale")) == "WRONG_CHANGE"
    assert report_extra(card, parse("CHANGE | my husband | city | Bralindale")) == "value_right_owner_not_matched"
    assert grade(card, parse("NONE")) == "MISSED" and grade(card, parse("hmm")) == "UNPARSED"
    ucard = {"gold": {"type": "CHANGE", "owner": USER, "value": "39", "old": "36"}}
    assert grade(ucard, parse("CHANGE | me (the user) | age | 39")) == "RIGHT"
    assert grade({"gold": {"type": "NONE"}}, parse("CHANGE | a | b | c")) == "FALSE_CHANGE"
    notes = [("me (the user)", "husband", "Nulinim"), ("Nulinim", "city", "Galyaford")]
    assert grade(card, parse_note("UPDATE 2 | Bralindale", notes)) == "RIGHT"
    assert grade(card, parse_note("UPDATE note 1 | Bralindale", notes)) == "WRONG_CHANGE"
    assert parse_note("UPDATE 3 | x", notes)["type"] == "UNPARSED" and parse_note("NONE", notes)["type"] == "NONE"
    # bank cards on the readable DEV bank (331 format; 10 corrections)
    dev = SCRIPTS.parent / "artifacts/claude-e2e331-dev-20260924"
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for f in ("turns.jsonl", "truth.jsonl"):
            (d / f).write_text((dev / f).read_text(encoding="utf-8"), encoding="utf-8")
        turns, truth = ld(dev / "turns.jsonl"), ld(dev / "truth.jsonl")
        closed = {f["fact_id"]: f for f in truth if f["valid_until_turn"] is not None}
        corr = []
        for t in turns:
            if t["kind"] == "correct":
                new = [f for f in truth if f["life_id"] == t["life_id"] and f["taught_turn"] == t["turn_index"]]
                old = [f for f in closed.values() if f["life_id"] == t["life_id"]
                       and f["valid_until_turn"] == t["turn_index"]]
                if len(new) == 1 and len(old) == 1:
                    corr.append({"life_id": t["life_id"], "turn_index": t["turn_index"], "old_fact": old[0]["fact_id"],
                                 "new_fact": new[0]["fact_id"], "style": 0})
        (d / "corrections.jsonl").write_text("".join(json.dumps(c) + "\n" for c in corr), encoding="utf-8")
        cards = cards_bank(d)
        assert len(cards) == len(turns)
        cc = [c for c in cards if c["gold"]["type"] == "CHANGE"]
        assert len(cc) == len(corr) > 0
        fact = {f["fact_id"]: f for f in truth}
        for c in cc:  # the old value is a note just before its correction; the new one is not yet
            life, i = c["card"].split(":")
            k = next(x for x in corr if x["life_id"] == life and x["turn_index"] == int(i))
            assert any(v == str(fact[k["old_fact"]]["value"]) for (_o, _r, v) in c["notes"])
            assert not any(v == str(fact[k["new_fact"]]["value"]) and v != str(fact[k["old_fact"]]["value"])
                           for (_o, _r, v) in c["notes"])
            c["text"] = f"CORR:{c['gold']['owner'] if c['gold']['owner'] != USER else 'me'}:{c['gold']['value']}"
        assert "Your notebook now" in messages(cards[5], "B")[1]["content"]
        assert "Your notebook now" not in messages(cards[5], "A")[1]["content"]
        simple = [c for c in cards if " " not in c["gold"].get("value", "x")]
        ra = run(_FakeGen(), simple, "A", d / "a.jsonl", log=lambda s: None)
        rb = run(_FakeGen(), simple, "B", d / "b.jsonl", log=lambda s: None)
        ca, cb = count(ld(d / "a.jsonl")), count(ld(d / "b.jsonl"))
        n_corr = sum(c["gold"]["type"] == "CHANGE" for c in simple)
        assert ca.get("RIGHT", 0) == 0 and cb.get("RIGHT", 0) == n_corr > 0, (ca, cb)
        assert cb.get("FALSE_CHANGE", 0) == 0 and ra["cards"] == rb["cards"] == len(simple)
    print(f"selftest ok: {len(cards)} DEV-bank cards, {len(cc)} corrections; fake note-reader right {n_corr} of "
          f"{n_corr} with notes, 0 without")


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "count", "cards"])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--model")
    ap.add_argument("--arm", choices=["A", "B"])
    ap.add_argument("--dev")
    ap.add_argument("--bank")
    ap.add_argument("--out")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--fmt", choices=["owner", "note"], default="owner")
    ap.add_argument("--sample", type=int, default=0, help="DEV only: all corrections + this many other cards (seed 4051)")
    a = ap.parse_args()
    if a.cmd == "count":
        for f in a.files:
            print(json.dumps({"file": Path(f).name, **count(ld(f))}))
        return 0
    if a.dev:
        cards, skipped = cards_dev320(Path(a.dev))
    else:
        cards, skipped = cards_bank(Path(a.bank)), Counter()
    print(json.dumps({"cards": len(cards), "by_group": dict(Counter(c["group"] for c in cards)),
                      "corrections": sum(c["gold"]["type"] == "CHANGE" for c in cards), "skipped": dict(skipped)}))
    if a.cmd == "cards":
        return 0
    if a.limit:
        cards = cards[:a.limit]
    if a.sample:
        import random
        other = [c for c in cards if c["gold"]["type"] == "NONE"]
        keep = {c["card"] for c in random.Random(4051).sample(other, min(a.sample, len(other)))}
        cards = [c for c in cards if c["gold"]["type"] == "CHANGE" or c["card"] in keep]
    assert a.fmt == "owner" or a.arm == "B", "the note format needs the notes (arm B)"
    res = run(Gen(a.model), cards, a.arm, Path(a.out), fmt=a.fmt)
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
