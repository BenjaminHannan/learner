#!/usr/bin/env python3
"""rd-378k cut-only training rows (Trustworthy notes, 09-26): the rd-378 note writer's OWN notes with every note the
blind judges did not mark "ok" deleted (Ben, 12:02 UTC 09-26: "Cut only", corrections may only delete untrue parts).

Inputs (rd-371b, all judged before this script existed):
  --dialogs  artifacts/claude-rd371b-20260926/data/train_dialogs.jsonl   (120 fresh training dialogs, not a panel)
  --drafts   train_drafts.jsonl (origin/builder-outbox:artifacts/claude-rd371b-20260926/): the writer's greedy draft and
             one temperature-0.8 sample per turn, {"dialog","t","draft","notes","raw","ms"}
  --judged   artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl: one verdict per DISTINCT note of the turn
             (both drafts, first-seen order, text compared lower-cased with spaces collapsed, as tools/judge_build.py
             built the judge input) and "missed" = memorable things no note of the turn covers.
Target per turn = the turn's distinct notes judged "ok", in first-seen order, each exactly as the writer wrote it
(text, cites, when). Nothing is added or reworded: the only edit is deletion.
A turn whose target is empty is kept only if the judge found nothing missed (teaching "no note" there is right); an
empty target with missed > 0 is dropped (it would teach leaving out something memorable).
10% of dialogs (by id hash, as claude_rd378_data.py) go to dev. Rows: {"id","prompt","target","src","family"}, prompt =
claude_rd378_common.build_nprompt exactly as the writer is prompted, target = notes_text(...). Prints counts only.

python claude_rd378k_data.py judgein --dialogs D --drafts R --out JUDGE_IN   (the graders' input; same union order)
python claude_rd378k_data.py --dialogs D --drafts R --judged J --out OUT [--repeat 3]
python claude_rd378k_data.py selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_rd378_common import build_nprompt, notes_text  # noqa: E402


def norm(text):
    return " ".join(text.split()).lower()


def read_jsonl(p):
    return [json.loads(line) for line in Path(p).read_text(encoding="utf-8").splitlines() if line.strip()]


def union_notes(drafts):
    """(dialog, t) -> the turn's distinct notes over all drafts, first-seen order (as tools/judge_build.py)."""
    union = {}
    for r in drafts:
        lst = union.setdefault((r["dialog"], int(r["t"])), [])
        for n in r.get("notes") or []:
            if norm(n["text"]) not in {norm(x["text"]) for x in lst}:
                lst.append(n)
    return union


def judge_input(dialogs, drafts):
    """Dialogs with each drafted turn's distinct notes: the judge's input, verdicts line up with union_notes."""
    union, out = union_notes(drafts), []
    for d in dialogs:
        turns = []
        for t in d["turns"]:
            t = {k: v for k, v in t.items() if k != "notes"}
            key = (d["dialog"], int(t["t"]))
            if key in union:
                t["notes"] = [{"text": n["text"], "cites": n.get("cites") or [0], "when": n.get("when")}
                              for n in union[key]]
            turns.append(t)
        out.append(dict(d, turns=turns))
    return out


def build(dialogs, drafts, judged, repeat=3):
    union = union_notes(drafts)
    verdict = {(j["dialog"], int(j["t"])): j for j in judged}
    c = Counter()
    train, dev = [], []
    for d in dialogs:
        is_dev = int(hashlib.sha256(d["dialog"].encode()).hexdigest(), 16) % 10 == 0
        turns = d["turns"]
        for k, t in enumerate(turns):
            if d["kind"] == "chat" and t["speaker"] == "assistant":
                continue
            key = (d["dialog"], int(t["t"]))
            if key not in verdict:
                c["no_verdict"] += 1
                continue
            notes, j = union.get(key, []), verdict[key]
            if len(j["verdicts"]) != len(notes):
                raise SystemExit(f"verdicts do not line up with the distinct notes at {key}")
            kept = [n for n, v in zip(notes, j["verdicts"]) if v == "ok"]
            c["turns"] += 1
            c["notes_in"] += len(notes)
            c["notes_cut"] += len(notes) - len(kept)
            if not kept and j.get("missed", 0):
                c["dropped_empty_missed"] += 1
                continue
            row = {"id": f"{d['dialog']}-t{t['t']}", "src": "cut378k_dev" if is_dev else "cut378k",
                   "family": d["kind"] + (":empty" if not kept else ""),
                   "prompt": build_nprompt(d["kind"], d.get("date", ""), turns[:k], t),
                   "target": notes_text([{"text": n["text"], "cites": n.get("cites") or [0], "when": n.get("when")}
                                         for n in kept])}
            if is_dev:
                dev.append(row)
            else:
                train += [row] * repeat
            c["kept_dev" if is_dev else "kept_train"] += 1
            c["kept_empty"] += not kept
            c["notes_kept"] += len(kept)
    c["train_rows"], c["dev_rows"] = len(train), len(dev)
    return train, dev, dict(sorted(c.items()))


def selftest():
    dialogs = [{"dialog": "x1", "kind": "overheard", "speakers": ["Wren", "Tobin"], "date": "8 May 2023", "turns": [
        {"t": 1, "speaker": "Wren", "text": "I moved to Oakvale in May."},
        {"t": 2, "speaker": "Tobin", "text": "Cool."},
        {"t": 3, "speaker": "Wren", "text": "The library hired me and I start Monday."}]}]
    drafts = [{"dialog": "x1", "t": 1, "draft": "greedy", "notes": [{"text": "Wren moved to Oakvale.", "cites": [0],
                                                                      "when": "in May"}]},
              {"dialog": "x1", "t": 1, "draft": "s1", "notes": [{"text": "wren  moved to Oakvale.", "cites": [0]},
                                                                  {"text": "Wren hates Oakvale.", "cites": [0]}]},
              {"dialog": "x1", "t": 2, "draft": "greedy", "notes": []},
              {"dialog": "x1", "t": 2, "draft": "s1", "notes": [{"text": "Tobin is cool.", "cites": [0]}]},
              {"dialog": "x1", "t": 3, "draft": "greedy", "notes": [{"text": "Wren was fired.", "cites": [0]}]},
              {"dialog": "x1", "t": 3, "draft": "s1", "notes": None}]
    judged = [{"dialog": "x1", "t": 1, "verdicts": ["ok", "unsupported"], "missed": 0},
              {"dialog": "x1", "t": 2, "verdicts": ["unsupported"], "missed": 0},
              {"dialog": "x1", "t": 3, "verdicts": ["unsupported"], "missed": 1}]
    train, dev, c = build(dialogs, drafts, judged, repeat=1)
    rows = train + dev
    ok = {}
    t1 = [r for r in rows if r["id"] == "x1-t1"]
    ok["deletes the untrue note, keeps the true one word for word"] = len(t1) == 1 and json.loads(
        t1[0]["target"].split("\n<END>")[0])["notes"] == [{"text": "Wren moved to Oakvale.", "cites": [0],
                                                           "when": "in May"}]
    ok["duplicate across drafts counted once"] = c["notes_in"] == 4
    t2 = [r for r in rows if r["id"] == "x1-t2"]
    ok["empty target kept when nothing missed"] = len(t2) == 1 and '"notes": []' in t2[0]["target"]
    ok["empty target dropped when something missed"] = not [r for r in rows if r["id"] == "x1-t3"] and \
        c["dropped_empty_missed"] == 1
    ok["prompt is the writer's prompt"] = t1[0]["prompt"] == build_nprompt("overheard", "8 May 2023", [],
                                                                           dialogs[0]["turns"][0])
    jin = judge_input(dialogs, drafts)
    ok["judge input: one note per distinct text, lines up with verdicts"] = \
        [len(t["notes"]) for t in jin[0]["turns"]] == [2, 1, 1] and jin[0]["turns"][0]["notes"][1]["text"] == \
        "Wren hates Oakvale."
    try:
        build(dialogs, drafts, [dict(judged[0], verdicts=["ok"])] + judged[1:])
        ok["misaligned verdicts stop"] = False
    except SystemExit:
        ok["misaligned verdicts stop"] = True
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("RD378K-DATA-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


def main():
    if sys.argv[1:] == ["selftest"]:
        return selftest()
    if sys.argv[1:2] == ["judgein"]:
        ap = argparse.ArgumentParser()
        ap.add_argument("mode")
        ap.add_argument("--dialogs", required=True)
        ap.add_argument("--drafts", required=True)
        ap.add_argument("--out", required=True)
        a = ap.parse_args()
        jin = judge_input(read_jsonl(a.dialogs), read_jsonl(a.drafts))
        Path(a.out).write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in jin), encoding="utf-8")
        print(json.dumps({"dialogs": len(jin), "turns_with_notes_list": sum("notes" in t for d in jin for t in d["turns"]),
                          "notes": sum(len(t.get("notes", [])) for d in jin for t in d["turns"])}))
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("--dialogs", required=True)
    ap.add_argument("--drafts", required=True)
    ap.add_argument("--judged", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repeat", type=int, default=3)
    a = ap.parse_args()
    train, dev, c = build(read_jsonl(a.dialogs), read_jsonl(a.drafts), read_jsonl(a.judged), a.repeat)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("dev", dev)):
        (out / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                           encoding="utf-8")
    print(json.dumps(c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
