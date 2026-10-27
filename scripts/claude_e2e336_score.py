#!/usr/bin/env python3
"""336 mechanical scorer (month-end line). Marks: artifacts/claude-e2e336-20260924/PASSMARKS.md.

New file only. Reads the bank (turns.jsonl, truth.jsonl) and one or more runner outputs
(arm_<name>.jsonl from scripts/claude_e2e336_run.py). Prints and writes counts only; never
prints user text. It also writes the packets the blind graders need:
  judge_saves_<arm>.jsonl    every NEW stored triple, with the turn's truth facts, for the
                             blind wrong-save judges (M1)
  judge_asks_<arm>.jsonl     every ask the mechanical rules call wrong, for the blind
                             wrong-answer judges (M2)
  grammar_<arm>.jsonl        every distinct reply, for the two grammar graders (M7)
Mechanical rules (fixed before any run):
  - A reply ABSTAINS if it contains any ABSTAIN_MARKERS entry (lowercase substring).
  - A reply CLARIFIES if it contains any CLARIFY_MARKERS entry.
  - A reply CONFIRMS if the runner flagged confirm_asked.
  - Value match = case-insensitive, word-boundary match of the gold value.
  - ask type value/two_hop/reversal/edit/one_hop: RIGHT if every gold value matches and the
    reply does not abstain; RIGHT_CONFIRM if the reply is a confirm question naming every gold
    value and the harness answered yes; ABSTAIN if it abstains or clarifies; CONFIRM_OTHER if a
    confirm question that is not RIGHT_CONFIRM; else WRONG_CANDIDATE.
  - ask type idk (never_told): RIGHT if it abstains; else WRONG_CANDIDATE.
  - ask type partial: RIGHT if it abstains and names the known middle value; ABSTAIN if it only
    abstains; else WRONG_CANDIDATE.
  - ask type yes/no: RIGHT if the reply's first yes/no word equals the gold; ABSTAIN if it
    abstains; else WRONG_CANDIDATE.
  - A taught fact is SAVED if, at some row at or after its turn and before its correction,
    a stored triple has the same owner (USER <-> USER/me/i; else case-insensitive full name or
    first name) and value (case-insensitive). Relation is left to the blind judges.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ABSTAIN_MARKERS = [
    "don't know", "do not know", "dont know", "not sure", "haven't told me", "have not told me",
    "haven't mentioned", "didn't tell me", "did not tell me", "never told me", "no record",
    "not told", "i don't have", "i do not have", "can't find", "cannot find", "won't guess",
    "will not guess", "no idea", "not in my notes", "not in my notebook", "don't remember",
    "do not remember", "i'm not aware", "unknown",
]
CLARIFY_MARKERS = [
    "didn't understand", "don't know that shape", "well enough to save", "don't know that yet",
    "do not know that from what you taught me", "couldn't save that as a fact",
    "couldn't read that message", "please say it like", "do not understand that question",
    "did not understand", "not sure what you mean", "could you rephrase", "can you rephrase",
]
USER_OWNERS = {"user", "me", "i", "you", "ben"}


def load(p: Path) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def has(low: str, markers: list[str]) -> bool:
    return any(m in low for m in markers)


def vmatch(text: str, value: str) -> bool:
    v = str(value).strip().lower()
    if not v:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", text.lower()) is not None


def owner_match(stored: str, truth_owner: str) -> bool:
    s = str(stored).strip().lower()
    t = str(truth_owner).strip().lower()
    if t == "user":
        return s in USER_OWNERS
    return s == t or s == t.split()[0]


def first_yesno(text: str) -> str | None:
    m = re.search(r"(?<![a-z])(yes|yeah|yep|no|nope)(?![a-z])", text.lower())
    if not m:
        return None
    return "yes" if m.group(1) in ("yes", "yeah", "yep") else "no"


def score_ask(t: dict, row: dict, conf: dict | None) -> str:
    reply = row["reply"]
    low = reply.lower()
    g = t["gold"] or {}
    typ = g.get("type", "value")
    vals = [str(v) for v in g.get("values", [])]
    ab = has(low, ABSTAIN_MARKERS) or has(low, CLARIFY_MARKERS)
    if row.get("confirm_asked"):
        if typ in ("value",) and vals and all(vmatch(reply, v) for v in vals) \
                and conf is not None and conf.get("confirm_answer") == "yes":
            return "RIGHT_CONFIRM"
        return "CONFIRM_OTHER"
    if typ == "idk":
        return "RIGHT" if ab else "WRONG_CANDIDATE"
    if typ == "partial":
        if ab and vals and all(vmatch(reply, v) for v in vals):
            return "RIGHT"
        return "ABSTAIN" if ab else "WRONG_CANDIDATE"
    if typ in ("yes", "no"):
        if ab:
            return "ABSTAIN"
        return "RIGHT" if first_yesno(reply) == typ else "WRONG_CANDIDATE"
    if ab:
        return "ABSTAIN"
    if vals and all(vmatch(reply, v) for v in vals):
        return "RIGHT"
    return "WRONG_CANDIDATE"


def score_arm(name: str, turns: list[dict], truth: list[dict], rows: list[dict], out: Path) -> dict:
    tkey = {(t["life_id"], t["turn_index"]): t for t in turns}
    lives_run = {r["life_id"] for r in rows}
    truth_by = defaultdict(list)
    for f in truth:
        if f["life_id"] in lives_run:          # score only the lives this arm ran
            truth_by[f["life_id"]].append(f)
    user_rows = [r for r in rows if r["kind"] == "user"]
    conf_rows = {(r["life_id"], r["turn_index"]): r for r in rows if r["kind"] == "confirm_answer"}
    res: dict = {"arm": name, "user_rows": len(user_rows), "confirm_rows": len(conf_rows)}

    # asks
    by_type = defaultdict(Counter)
    wrong_packets = []
    for r in user_rows:
        t = tkey.get((r["life_id"], r["turn_index"]))
        if t is None:
            res["join_miss"] = res.get("join_miss", 0) + 1
            continue
        if t["kind"] != "ask":
            continue
        c = score_ask(t, r, conf_rows.get((r["life_id"], r["turn_index"])))
        by_type[t.get("ask_type") or "?"][c] += 1
        by_type["ALL"][c] += 1
        if c == "WRONG_CANDIDATE":
            wrong_packets.append({"life_id": r["life_id"], "turn_index": r["turn_index"],
                                  "ask_type": t.get("ask_type"), "gold": t["gold"], "reply": r["reply"]})
    res["asks"] = {k: dict(v) for k, v in by_type.items()}

    # saves: new triples per row, and recall per taught fact
    save_packets = []
    prev: dict[str, set] = defaultdict(set)
    stored_seen: dict[str, list] = defaultdict(list)   # life -> [(turn_index, set_of_triples)]
    nosave_rows_with_writes = 0
    for r in rows:
        st = r.get("stored_triples")
        if st is None:
            continue
        cur = {tuple(x) for x in st}
        new = cur - prev[r["life_id"]]
        prev[r["life_id"]] = cur
        stored_seen[r["life_id"]].append((r["turn_index"], cur))
        t = tkey.get((r["life_id"], r["turn_index"]))
        if new and t is not None and t["kind"] == "nosave" and r["kind"] == "user":
            nosave_rows_with_writes += 1
        for tr in sorted(new):
            valid = [f for f in truth_by[r["life_id"]] if f["taught_turn"] <= r["turn_index"]
                     and (f.get("valid_until_turn") is None or f["valid_until_turn"] > r["turn_index"])]
            auto = any(owner_match(tr[0], f["owner"]) and str(tr[2]).lower() == str(f["value"]).lower()
                       for f in valid)
            save_packets.append({"life_id": r["life_id"], "turn_index": r["turn_index"],
                                 "row_kind": r["kind"], "turn_kind": t["kind"] if t else None,
                                 "triple": list(tr), "owner_value_supported": auto,
                                 "truth_valid_now": [{k: f[k] for k in ("owner", "relation", "value")}
                                                     for f in valid]})
    res["new_triples"] = len(save_packets)
    res["new_triples_owner_value_unsupported"] = sum(1 for p in save_packets if not p["owner_value_supported"])
    res["nosave_turns_with_writes"] = nosave_rows_with_writes

    saved = total = 0
    day1_kept = day1_total = 0
    tday = {(t["life_id"], t["turn_index"]): t["day"] for t in turns}
    for life, facts in truth_by.items():
        seen = stored_seen.get(life, [])
        for f in facts:
            total += 1
            end = f.get("valid_until_turn")
            hit = any(ti >= f["taught_turn"] and (end is None or ti < end)
                      and any(owner_match(a, f["owner"]) and str(v).lower() == str(f["value"]).lower()
                              for (a, _r, v) in s)
                      for ti, s in seen)
            saved += hit
            if hit and end is None and tday.get((life, f["taught_turn"])) == 1 and seen:
                day1_total += 1
                last = seen[-1][1]
                day1_kept += any(owner_match(a, f["owner"]) and str(v).lower() == str(f["value"]).lower()
                                 for (a, _r, v) in last)
    res["facts_total"] = total
    res["facts_saved"] = saved
    res["day1_saved_facts"] = day1_total
    res["day1_saved_facts_kept_at_end"] = day1_kept

    replies = [r["reply"] for r in user_rows]
    cnt = Counter(replies)
    res["most_common_reply_count"] = cnt.most_common(1)[0][1] if cnt else 0
    res["distinct_replies"] = len(cnt)
    res["clarify_replies"] = sum(1 for x in replies if has(x.lower(), CLARIFY_MARKERS))
    ms = [r["ms"] for r in user_rows]
    res["ms_median"] = round(statistics.median(ms), 1) if ms else None
    res["ms_p90"] = round(sorted(ms)[int(0.9 * (len(ms) - 1))], 1) if ms else None
    creative = [r for r in user_rows if tkey.get((r["life_id"], r["turn_index"]), {}).get("kind") == "creative"]
    res["creative_turns"] = len(creative)
    res["creative_turns_with_writes"] = sum(1 for r in creative if r["notebook_events"])

    out.mkdir(parents=True, exist_ok=True)
    for fn, data in ((f"judge_saves_{name}.jsonl", save_packets),
                     (f"judge_asks_{name}.jsonl", wrong_packets),
                     (f"grammar_{name}.jsonl", [{"reply": x} for x in sorted(set(
                         [r["reply"] for r in rows if r["reply"]]))])):
        (out / fn).write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in data),
                              encoding="utf-8")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--runs", required=True, nargs="+", help="arm_<name>.jsonl files")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    turns = load(Path(a.bank) / "turns.jsonl")
    truth = load(Path(a.bank) / "truth.jsonl")
    out = Path(a.out)
    results = []
    for p in a.runs:
        name = Path(p).stem.removeprefix("arm_")
        results.append(score_arm(name, turns, truth, load(Path(p)), out))
    (out / "mechanical.json").write_text(json.dumps(results, indent=1, sort_keys=True), encoding="utf-8")
    for r in results:
        print(json.dumps(r, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
