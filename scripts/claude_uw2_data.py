#!/usr/bin/env python3
"""uw-2 training cards and data gate (artifacts/claude-uw2-20260926/PASSMARKS-uw2.md). Wrong-as-fact thread,
2026-09-26, written before any training row exists. New file. Prints counts only.

Cards follow claude_uw1_cards.cards_dev320's rules (notes = gold ASSERT/CORRECT facts of earlier kept turns; dropped
turns skipped; implicit changes and "former of a current note" left out and counted), with the PASSMARKS target rule:
a `correct` OR `correct_ref` turn whose single CORRECT fact's (owner, rel) is note N gets "UPDATE N | v", where v is
the new value exactly as typed in the message (case-insensitive whole-word span; no span = dropped and counted).
Every other kept turn gets "NONE". The prompt is claude_uw1_cards.messages(card, "B", "note"), byte for byte.

Mix (PASSMARKS): every correction card and every look-alike card; the other NONE cards are sampled with seed 4052
so that NONE cards total 4 per correction card (or all, if fewer). Minimum to train: 300 correction cards, at least
80 of them correct_ref.

  build   LIS320_DIR OUT         OUT/train.jsonl (bm398r rows: system, user, answer, kind, layout) + OUT/build.json
  devrows UW1_DEV_DIR OUT        OUT/dev.jsonl: the trainer's report-only dev rows from the uw-1 DEV pilots
  gateprep OUT GATE              60 cards (seed 4053: 30 corrections with 15 correct_ref, 30 look-alike NONE) as
                                 judge packets GATE/packets.jsonl (notes, earlier turns, message; no label) and
                                 GATE/key.json (builder-only)
  gatecmp GATE J1 J2 [J3]        judges' {"id", "note", "new_value"} (note 0 = no change) vs the code labels;
                                 final = J1 if J1 and J2 agree, else J3; PASS if >= 54 of 60 agree
  --selftest                     on the uw-1 DEV pilots with a relabelled copy (readable DEV; temp files only)
"""
from __future__ import annotations

import json
import random
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_uw1_cards as U  # noqa: E402

CORRECT_INTENTS = ("correct", "correct_ref")
LOOKALIKE = ("former", "plan", "hypothetical", "someone_else", "question", "doubt", "confirm", "negation_only",
             "ambiguous_pronoun")
SEED_MIX, SEED_GATE = 4052, 4053
MIN_CORR, MIN_REF, GATE_PASS = 300, 80, 54


def ld(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def span(text: str, value: str) -> str | None:
    m = re.search(r"(?<![a-z0-9])" + re.escape(str(value).lower()) + r"(?![a-z0-9])", str(text).lower())
    return text[m.start():m.end()] if m else None


def cards(root: Path) -> tuple[list[dict], Counter]:
    """Every folder under root holding seeds.jsonl + kept.jsonl (lis-320 layout)."""
    out, skipped = [], Counter()
    dirs = [root] if (root / "seeds.jsonl").exists() else sorted(p for p in root.iterdir() if (p / "seeds.jsonl").exists())
    for pdir in dirs:
        kept = {k["id"]: k for k in ld(pdir / "kept.jsonl")}
        pref = {}                                  # dialog_id -> kept-id prefix ("glm320-s320-321-00000")
        for k in kept:
            head = k.rsplit("-t", 1)[0]
            pref.setdefault(head.split("-", 1)[1] if "-" in head else head, head)
        for s in ld(pdir / "seeds.jsonl"):
            notes: dict = {}
            earlier = []
            prefix = pref.get(s["dialog_id"])
            for t in sorted(s["turns"], key=lambda t: t["k"]):
                row = kept.get(f"{prefix}-t{t['k']}") if prefix else None
                facts = t["gold"]["facts"]
                owner = lambda f: U.USER if f["owner"] == "me" else f["owner"]  # noqa: E731
                if row is None:
                    skipped["turn_not_kept"] += 1
                    continue
                gold, group = {"type": "NONE"}, t["intent"]
                if t["intent"] in CORRECT_INTENTS:
                    cor = [f for f in facts if f.get("mode") == "CORRECT"]
                    key = (owner(cor[0]), cor[0]["rel"]) if len(cor) == 1 else None
                    if key is None or key not in notes:
                        skipped["correct_old_not_in_notes"] += 1
                        gold = None
                    else:
                        v = span(row["turn"], cor[0]["value"])
                        if v is None:
                            skipped["value_not_span"] += 1
                            gold = None
                        else:
                            gold = {"type": "CHANGE", "owner": key[0], "value": v, "old": notes[key],
                                    "note": list(notes).index(key) + 1, "style": t["intent"]}
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
                    out.append({"card": row["id"], "group": group, "gold": gold, "text": row["turn"],
                                "earlier": list(earlier),
                                "notes": [(U._owner_text(o), r, v) for (o, r), v in notes.items()]})
                for f in facts:
                    if f.get("mode") in ("ASSERT", "CORRECT"):
                        notes[(owner(f), f["rel"])] = f["value"]   # a corrected note keeps its place and number
                earlier.append(row["turn"])
    return out, skipped


def target(card: dict) -> str:
    g = card["gold"]
    return f"UPDATE {g['note']} | {g['value']}" if g["type"] == "CHANGE" else "NONE"


def row(card: dict) -> dict:
    m = U.messages(card, "B", "note")
    return {"system": m[0]["content"], "user": m[1]["content"], "answer": target(card),
            "kind": "change" if card["gold"]["type"] == "CHANGE" else "none", "layout": "uw2", "card": card["card"],
            "group": card["group"]}


def mix(cs: list[dict]) -> list[dict]:
    corr = [c for c in cs if c["gold"]["type"] == "CHANGE"]
    look = [c for c in cs if c["gold"]["type"] == "NONE" and c["group"] in LOOKALIKE]
    other = [c for c in cs if c["gold"]["type"] == "NONE" and c["group"] not in LOOKALIKE]
    need = max(0, 4 * len(corr) - len(look))
    rng = random.Random(SEED_MIX)
    pick = rng.sample(other, min(need, len(other)))
    out = corr + look + pick
    rng.shuffle(out)
    return out


def build(src: Path, out: Path) -> dict:
    cs, skipped = cards(src)
    m = mix(cs)
    corr = [c for c in m if c["gold"]["type"] == "CHANGE"]
    n_ref = sum(c["group"] == "correct_ref" for c in corr)
    out.mkdir(parents=True, exist_ok=True)
    (out / "train.jsonl").write_text("".join(json.dumps(row(c), ensure_ascii=False) + "\n" for c in m),
                                     encoding="utf-8")
    (out / "cards.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in m), encoding="utf-8")
    rep = {"cards_all": len(cs), "train_cards": len(m), "corrections": len(corr), "correct_ref": n_ref,
           "none": len(m) - len(corr), "by_group": dict(Counter(c["group"] for c in m)), "skipped": dict(skipped),
           "enough": len(corr) >= MIN_CORR and n_ref >= MIN_REF}
    (out / "build.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep))
    return rep


def devrows(dev: Path, out: Path) -> None:
    cs, _ = U.cards_dev320(dev)
    rows = []
    for c in cs:
        g = c["gold"]
        if g["type"] == "CHANGE":
            keys = [(o, r) for (o, r, v) in c["notes"]]
            idx = next(i for i, (o, r, v) in enumerate(c["notes"], 1) if v == g["old"])
            v = span(c["text"], g["value"]) or g["value"]
            c = dict(c, gold=dict(g, note=idx, value=v))
            assert len(keys) == len(c["notes"])
        rows.append(row(c))
    out.mkdir(parents=True, exist_ok=True)
    (out / "dev.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"dev_rows": len(rows), "change": sum(r["kind"] == "change" for r in rows)}))


def gateprep(out: Path, gate: Path) -> None:
    cs = ld(out / "cards.jsonl")
    rng = random.Random(SEED_GATE)
    ref = [c for c in cs if c["group"] == "correct_ref"]
    plain = [c for c in cs if c["group"] == "correct"]
    look = [c for c in cs if c["gold"]["type"] == "NONE" and c["group"] in LOOKALIKE]
    pick = rng.sample(ref, min(15, len(ref)))
    pick += rng.sample(plain, min(30 - len(pick), len(plain)))
    pick += rng.sample(look, min(30, len(look)))
    rng.shuffle(pick)
    gate.mkdir(parents=True, exist_ok=True)
    packets, key = [], {}
    for i, c in enumerate(pick):
        pid = f"G{i:03d}"
        packets.append({"id": pid, "notes": [f"{j}. {o} | {r} | {v}" for j, (o, r, v) in enumerate(c["notes"], 1)],
                        "earlier_user_turns": c["earlier"], "new_message": c["text"]})
        key[pid] = c["gold"]
    (gate / "packets.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in packets),
                                        encoding="utf-8")
    (gate / "key.json").write_text(json.dumps(key, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"packets": len(packets), "change": sum(g["type"] == "CHANGE" for g in key.values())}))


def _agree(g: dict, a: dict) -> bool:
    n = int(a.get("note") or 0)
    if g["type"] == "NONE":
        return n == 0
    return n == g["note"] and U._vmatch(str(a.get("new_value", "")), g["value"])


def gatecmp(gate: Path, j1: Path, j2: Path, j3: Path | None = None) -> dict:
    key = json.loads((gate / "key.json").read_text(encoding="utf-8"))
    v1 = {a["id"]: a for a in ld(j1)}
    v2 = {a["id"]: a for a in ld(j2)}
    v3 = {a["id"]: a for a in ld(j3)} if j3 else {}
    same = lambda a, b: int(a.get("note") or 0) == int(b.get("note") or 0) and (  # noqa: E731
        int(a.get("note") or 0) == 0 or str(a.get("new_value", "")).strip().lower()
        == str(b.get("new_value", "")).strip().lower())
    split = [i for i in key if not same(v1[i], v2[i])]
    if split and not v3:
        (gate / "split_ids.json").write_text(json.dumps(split), encoding="utf-8")
        print(json.dumps({"splits": len(split), "need_third": True}))
        return {"splits": len(split)}
    final = {i: (v1[i] if i not in split else v3[i]) for i in key}
    agree = sum(_agree(key[i], final[i]) for i in key)
    res = {"packets": len(key), "splits": len(split), "agree": agree,
           "agree_change": sum(_agree(key[i], final[i]) for i in key if key[i]["type"] == "CHANGE"),
           "agree_none": sum(_agree(key[i], final[i]) for i in key if key[i]["type"] == "NONE"),
           "verdict": "PASS" if agree >= GATE_PASS else "FAIL"}
    print(json.dumps(res))
    return res


def selftest() -> None:
    dev = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    assert span("wait, it's Rusk Tools now", "rusk tools") == "Rusk Tools" and span("x", "y") is None
    if dev is None:
        print("selftest ok (unit only; pass the uw-1 DEV pilots folder for the full selftest)")
        return
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        # a relabelled copy of pilot2: every other `correct` turn becomes `correct_ref`, so both paths run
        src = d / "src" / "p"
        src.mkdir(parents=True)
        seeds = ld(dev / "pilot2" / "seeds.jsonl")
        flip = 0
        for s in seeds:
            for t in s["turns"]:
                if t["intent"] == "correct":
                    flip += 1
                    if flip % 2 == 0:
                        t["intent"] = "correct_ref"
        (src / "seeds.jsonl").write_text("".join(json.dumps(s) + "\n" for s in seeds), encoding="utf-8")
        (src / "kept.jsonl").write_text((dev / "pilot2" / "kept.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
        rep = build(d / "src", d / "out")
        assert rep["correct_ref"] > 0 and rep["corrections"] > rep["correct_ref"] and not rep["enough"]
        assert rep["none"] <= 4 * rep["corrections"] and rep["train_cards"] == rep["corrections"] + rep["none"]
        tr = ld(d / "out" / "train.jsonl")
        for r in tr:
            assert r["answer"] == "NONE" or re.fullmatch(r"UPDATE \d+ \| .+", r["answer"]), r["answer"]
        cs = ld(d / "out" / "cards.jsonl")
        for c in cs:
            g = c["gold"]
            if g["type"] == "CHANGE":
                o, _r, v = c["notes"][g["note"] - 1]
                assert v.lower() == g["old"].lower() and g["value"] in c["text"]
                p = U.parse_note(target(c), c["notes"])
                assert U.grade(c, p) == "RIGHT", (target(c), g)
            assert U.messages(c, "B", "note")[1]["content"] == next(r for r in tr if r["card"] == c["card"])["user"]
        gateprep(d / "out", d / "gate")
        key = json.loads((d / "gate" / "key.json").read_text())
        pk = ld(d / "gate" / "packets.jsonl")
        assert all(set(p) == {"id", "notes", "earlier_user_turns", "new_message"} for p in pk)
        perfect = [{"id": i, "note": g.get("note", 0), "new_value": g.get("value", "")} for i, g in key.items()]
        (d / "j1.jsonl").write_text("".join(json.dumps(a) + "\n" for a in perfect))
        (d / "j2.jsonl").write_text("".join(json.dumps(a) + "\n" for a in perfect))
        res = gatecmp(d / "gate", d / "j1.jsonl", d / "j2.jsonl")
        assert res["agree"] == len(key) and res["splits"] == 0
        devrows(dev, d / "dev")
        assert len(ld(d / "dev" / "dev.jsonl")) == len(U.cards_dev320(dev)[0])
    print(f"selftest ok: relabelled DEV copy gives {rep['corrections']} corrections ({rep['correct_ref']} correct_ref), "
          f"every target grades RIGHT under the sealed grader; gate plumbing ok")


def main() -> int:
    cmd = sys.argv[1]
    if cmd == "--selftest":
        selftest()
    elif cmd == "build":
        build(Path(sys.argv[2]), Path(sys.argv[3]))
    elif cmd == "devrows":
        devrows(Path(sys.argv[2]), Path(sys.argv[3]))
    elif cmd == "gateprep":
        gateprep(Path(sys.argv[2]), Path(sys.argv[3]))
    elif cmd == "gatecmp":
        gatecmp(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]) if len(sys.argv) > 5 else None)
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
