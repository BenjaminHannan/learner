#!/usr/bin/env python3
"""y1t data gate, part 2: never-told twins whose answer is a person (Answering-from-memory thread, 2026-09-26). New file.
Rule: artifacts/claude-y1t-20260926/GATE-ADDENDUM-1.md, where F1 is registered as G1b (the sealed G1 FAILED as
written and stays on the record). claude_y1t_gate.py stays as sealed.

Before the combined GLM set existed, the sealed G1 check (a twin fails when any turn it keeps contains the gold value)
was run on the first run's items: 64 of 283 training twins failed it. Counted by code (no item read for this count),
every one of the 64 asks "who is my <role>?" (the answer is a person's name, 134 of 283 items), and the person is
named elsewhere in the chat (their cat, their job, a look-alike turn). A twin that names the landlord's cat without
saying who the landlord is still does not tell the answer, so G1 counts the wrong thing for these questions.

  F1 (code, every twin, filters the data): keep a twin when no turn it keeps contains the gold value; for a role
     question ("me", a lis-320 role relation), also keep it when no kept turn with the name also has the role word
     ("name only"); drop every other twin ("role word with the name", or "value present" for other questions).
     Answerable items are never dropped.
  G4 (blind, decides whether "name only" twins stay): a seeded sample of up to 60 name-only twins; two blind judges,
     a fresh third on disagreements, say whether the earlier messages say that this person is the user's <role>.
     Pass: "yes" on at most 10% of the sample (6 of 60). Fail: every name-only twin is dropped too.
The judges' labels only pass or stop the data; nothing trained on is labelled by them (Ben 16:39).

  python -B scripts/claude_y1t_gate2.py filter --items ITEMS --out FILTERED     (F1; counts only)
  python -B scripts/claude_y1t_gate2.py sample --items FILTERED --out JUDGEDIR [--n 60] [--seed 4036]
  python -B scripts/claude_y1t_gate2.py splits --out JUDGEDIR
  python -B scripts/claude_y1t_gate2.py score --out JUDGEDIR                   -> JUDGEDIR/../g4_result.json
  python -B scripts/claude_y1t_gate2.py drop-name-only --items FILTERED --out OUT   (only if G4 fails)
  python -B scripts/claude_y1t_gate2.py --selftest
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_y1d_readchat as Y  # noqa: E402  (sealed: load)

N_SAMPLE, SEED = 60, 4036
G4_MAX_YES = 0.10

INSTRUCTIONS = """# Checking practice chats

Each line of batch.jsonl is one chat. A user wrote the messages to an assistant.
You get:
- "earlier_messages": what the user wrote earlier in the chat, in order;
- "last_message": the user's latest message;
- "person": a name, and "role": a relation to the user (for example "landlord" or "best friend").

Answer one question for each item, from the text only:
- "stated": do the earlier messages say that this person is the user's <role> (in any words, now or at some point)?
  "yes" or "no". It is "yes" if a reader of the earlier messages could tell that this person is the user's <role>.
  It is "no" if the person is mentioned but the messages never say they are the user's <role>.

Judge only from the item itself. Do not look at any other file or folder, and do not discuss items with anyone.
Write labels/batch.jsonl in this folder: one JSON line per item, {"item": "<id>", "stated": "yes" or "no"}, every
item exactly once.
"""


def roles() -> set[str]:
    import claude_lis320_seed as L
    return set(L.FEMALE_ROLES + L.MALE_ROLES + L.NEUTRAL_ROLES)


def _has_word(text: str, word: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(word.lower()), text.lower()) is not None


def classify(twin: dict, gold: str, role_rels: set[str]) -> str:
    import claude_e2e336_score as S
    hits = [r for r in twin["rows"] if S.vmatch(r["text"], gold)]
    if not hits:
        return "clean"
    if twin["owner"] == "me" and twin["rel"] in role_rels:
        word = twin["rel"].replace("_", " ")
        return "role_word_with_name" if any(_has_word(r["text"], word) for r in hits) else "name_only"
    return "value_present"


def f1(items: list[dict]) -> tuple[list[dict], dict]:
    role_rels = roles()
    gold = {(it["dialog_id"], it["k"]): it["gold"]["values"][0] for it in items if it["kind"] == "answerable"}
    out, c = [], Counter()
    for it in items:
        if it["kind"] != "never_told":
            out.append(it)
            continue
        cls = classify(it, gold[(it["dialog_id"], it["k"])], role_rels)
        c[cls] += 1
        if cls in ("clean", "name_only"):
            out.append(it | {"f1": cls})
    return out, {"answerable": sum(it["kind"] == "answerable" for it in items), "twins": sum(c.values()),
                 **dict(sorted(c.items())), "twins_kept": c["clean"] + c["name_only"]}


def _write(folder: Path, items: list[dict]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")
    (folder / "batch.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items),
                                        encoding="utf-8")


def sample(items: list[dict], out: Path, n: int = N_SAMPLE, seed: int = SEED) -> dict:
    gold = {(it["dialog_id"], it["k"]): it["gold"]["values"][0] for it in items if it["kind"] == "answerable"}
    pool = sorted((it for it in items if it.get("f1") == "name_only"), key=lambda it: (it["dialog_id"], it["k"]))
    pick = random.Random(seed).sample(pool, min(n, len(pool)))
    batch, key = [], {}
    for i, it in enumerate(pick, 1):
        iid = f"h{i:03d}"
        key[iid] = {"dialog_id": it["dialog_id"], "k": it["k"]}
        batch.append({"item": iid, "earlier_messages": [r["text"] for r in it["rows"]], "last_message": it["question"],
                      "person": gold[(it["dialog_id"], it["k"])], "role": it["rel"].replace("_", " ")})
    for j in ("a", "b"):
        _write(out / f"judge_{j}", batch)
    (out.parent / "g4_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    return {"pool": len(pool), "items": len(batch)}


def _labels(folder: Path) -> dict:
    p = folder / "labels" / "batch.jsonl"
    out = {}
    for r in Y.load(p):
        assert r["item"] not in out, f"{p}: {r['item']} twice"
        assert r["stated"] in ("yes", "no"), f"{p}: bad label for {r['item']}"
        out[r["item"]] = r["stated"]
    return out


def splits(out: Path) -> int:
    batch = Y.load(out / "judge_a" / "batch.jsonl")
    a, b = _labels(out / "judge_a"), _labels(out / "judge_b")
    assert set(a) == set(b) == {x["item"] for x in batch}, "judges did not label every item exactly once"
    split = [x for x in batch if a[x["item"]] != b[x["item"]]]
    if split:
        _write(out / "judge_c", split)
    return len(split)


def score(out: Path) -> dict:
    batch = Y.load(out / "judge_a" / "batch.jsonl")
    a, b = _labels(out / "judge_a"), _labels(out / "judge_b")
    c = _labels(out / "judge_c") if (out / "judge_c").exists() else {}
    need = {x["item"] for x in batch if a[x["item"]] != b[x["item"]]}
    assert need == set(c), "the third judge must label exactly the split items"
    yes = sum((a[i] if a[i] == b[i] else c[i]) == "yes" for i in (x["item"] for x in batch))
    res = {"items": len(batch), "stated_yes": yes, "judges_agree": len(batch) - len(need), "splits": len(need),
           "max_yes": int(G4_MAX_YES * len(batch)), "G4": len(batch) > 0 and yes <= int(G4_MAX_YES * len(batch))}
    (out.parent / "g4_result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def drop_name_only(items: list[dict]) -> tuple[list[dict], dict]:
    out = [it for it in items if it.get("f1") != "name_only"]
    return out, {"dropped_name_only": len(items) - len(out), "items": len(out)}


def selftest() -> None:
    import claude_y1t_data as T
    fr = lambda act, facts=(), ask=None: {"act": act, "facts": list(facts), "ask": ask}  # noqa: E731
    fa = lambda o, rel, v, mode="ASSERT": {"owner": o, "rel": rel, "value": v, "mode": mode}  # noqa: E731
    seeds, kept = [], []
    # d0 clean pet twin; d1 pet value still present; d2 landlord named only by name; d3 name with the role word
    later = {"d0": "long day honestly", "d1": "tansy is such a cute name", "d2": "saorn's cat is called Fipip",
             "d3": "my landlord saorn got a cat"}
    for d, (owner, rel, val, intro, ask) in {
            "d0": ("Mira", "dog", "Tansy", "mira's dog is Tansy", "what's mira's dog called?"),
            "d1": ("Mira", "dog", "Tansy", "mira's dog is Tansy", "what's mira's dog called?"),
            "d2": ("me", "landlord", "Saorn", "my landlord is Saorn", "who's my landlord again?"),
            "d3": ("me", "landlord", "Saorn", "my landlord is Saorn", "who's my landlord again?")}.items():
        seeds.append({"dialog_id": d, "turns": [
            {"k": 1, "intent": "teach", "gold": fr("TELL", [fa(owner, rel, val)])},
            {"k": 2, "intent": "smalltalk", "gold": fr("CHAT")},
            {"k": 3, "intent": "ask", "gold": fr("ASK", [], {"owner": owner, "rel": rel, "inverse": False})}]})
        kept += [{"id": f"glm320-{d}-t1", "turn": intro}, {"id": f"glm320-{d}-t2", "turn": later[d]},
                 {"id": f"glm320-{d}-t3", "turn": ask}]
    items = T.build_items(seeds, kept)[0]
    out, c = f1(items)
    assert c == {"answerable": 4, "twins": 4, "clean": 1, "name_only": 1, "role_word_with_name": 1,
                 "value_present": 1, "twins_kept": 2}, c
    kinds = {(it["dialog_id"], it["kind"]): it.get("f1") for it in out}
    assert kinds == {("d0", "answerable"): None, ("d0", "never_told"): "clean", ("d1", "answerable"): None,
                     ("d2", "answerable"): None, ("d2", "never_told"): "name_only", ("d3", "answerable"): None}, kinds
    assert not _has_word("my landlords", "lord") and _has_word("my landlord's cat", "landlord")
    many = []
    for i in range(70):
        many += [dict(it, dialog_id=f"{it['dialog_id']}x{i}") for it in out if it["dialog_id"] == "d2"]
    with tempfile.TemporaryDirectory() as d:
        jd = Path(d) / "g4"
        assert sample(many, jd) == {"pool": 70, "items": 60}
        batch = Y.load(jd / "judge_a" / "batch.jsonl")
        assert all(set(x) == {"item", "earlier_messages", "last_message", "person", "role"} for x in batch)
        assert batch[0]["person"] == "Saorn" and batch[0]["role"] == "landlord" and "dialog_id" not in json.dumps(batch)
        for j, f in (("a", lambda n: "no"), ("b", lambda n: "yes" if n < 9 else "no")):
            (jd / f"judge_{j}" / "labels").mkdir()
            (jd / f"judge_{j}" / "labels" / "batch.jsonl").write_text("".join(
                json.dumps({"item": x["item"], "stated": f(n)}) + "\n" for n, x in enumerate(batch)))
        assert splits(jd) == 9
        cb = Y.load(jd / "judge_c" / "batch.jsonl")
        (jd / "judge_c" / "labels").mkdir()
        (jd / "judge_c" / "labels" / "batch.jsonl").write_text("".join(
            json.dumps({"item": x["item"], "stated": "yes" if n < 7 else "no"}) + "\n" for n, x in enumerate(cb)))
        res = score(jd)
        assert res["stated_yes"] == 7 and res["max_yes"] == 6 and not res["G4"], res
        (jd / "judge_c" / "labels" / "batch.jsonl").write_text("".join(
            json.dumps({"item": x["item"], "stated": "yes" if n < 6 else "no"}) + "\n" for n, x in enumerate(cb)))
        assert score(jd)["G4"]
    assert drop_name_only(out)[1] == {"dropped_name_only": 1, "items": 5}
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("filter", "drop-name-only"):
        p = sub.add_parser(name)
        p.add_argument("--items", required=True)
        p.add_argument("--out", required=True)
    sm = sub.add_parser("sample")
    sm.add_argument("--items", required=True)
    sm.add_argument("--out", required=True)
    sm.add_argument("--n", type=int, default=N_SAMPLE)
    sm.add_argument("--seed", type=int, default=SEED)
    for name in ("splits", "score"):
        sub.add_parser(name).add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd in ("filter", "drop-name-only"):
        rows, c = (f1 if a.cmd == "filter" else drop_name_only)(Y.load(a.items))
        Path(a.out).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
        print(json.dumps(c))
    elif a.cmd == "sample":
        print(json.dumps(sample(Y.load(a.items), Path(a.out), a.n, a.seed)))
    elif a.cmd == "splits":
        print(json.dumps({"splits": splits(Path(a.out))}))
    else:
        print(json.dumps(score(Path(a.out))))


if __name__ == "__main__":
    main()
