#!/usr/bin/env python3
"""y1t data gate (Answering-from-memory thread, 2026-09-26). New file. Marks in
artifacts/claude-y1t-20260926/GATE-data.md, fixed before the GLM practice chats exist.

The Thread manager's test-hygiene rule 2 (design/v3/30-modes/test-hygiene-2026-09-26.md): a label taken from what a
writer was asked to write is not a label of what the text does. y1t's items take two labels from the seed (what GLM
was asked to write): that an "ask" turn asks for one stored fact, and that a never-told twin, with the turns carrying
that fact removed, no longer says the answer. The value itself is already checked from the text (build_items counts a
fact only if its value is typed in the kept user turn). Before any training this gate checks:
  G1 (code, every twin): the gold value does not appear in any turn the twin keeps (336's vmatch);
  G2, G3 (blind sample): two blind judges, a fresh third on disagreements, read a seeded sample of answerable items
  and say whether the last message asks for the named fact (G2) and whether the earlier messages state that value as
  the current answer (G3).
The judges' labels are never trained on; they only pass or stop the data (Ben 16:39: nothing trained on is judged by
Claude). If the gate fails, the fix labels from the text itself (code or GLM) under a new seal.

  python -B scripts/claude_y1t_gate.py audit --items ITEMS_TRAIN            (code check G1; counts only)
  python -B scripts/claude_y1t_gate.py sample --items ITEMS_TRAIN --out JUDGEDIR [--n 60] [--seed 4034]
  python -B scripts/claude_y1t_gate.py splits --out JUDGEDIR
  python -B scripts/claude_y1t_gate.py score --out JUDGEDIR               -> JUDGEDIR/../gate_result.json
  python -B scripts/claude_y1t_gate.py --selftest
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_y1d_readchat as Y  # noqa: E402  (sealed: load)

N_SAMPLE, SEED = 60, 4034
G1_MAX_SHARE = 0.05       # twins that still carry the gold value
G2_MIN = G3_MIN = 54      # of 60 sampled answerable items
QS = ("asks", "stated")

INSTRUCTIONS = """# Checking practice questions

Each line of batch.jsonl is one practice item made from a chat. A user wrote the messages to an assistant.
You get:
- "earlier_messages": what the user wrote earlier in the chat, in order;
- "last_message": the user's latest message;
- "fact": one fact about the user's life: "about" is who it is about ("me" means the user), "relation" is what it
  is (for example "dog" means the name of that person's dog), "value" is the answer.

Answer two questions for each item, from the text only:
- "asks": does the last message ask the assistant for this fact (the value for that person and relation)? "yes" or
  "no". It still counts if it is casual, misspelled or indirect ("remind me what mira's dog is called"). It is "no"
  if the message asks for something else, asks nothing, or states the fact instead of asking.
- "stated": do the earlier messages say that this value is the answer, and is it still the answer by the end of them
  (not replaced by a later correction)? "yes" or "no".

Judge only from the item itself. Do not look at any other file or folder, and do not discuss items with anyone.
Write labels/batch.jsonl in this folder: one JSON line per item, {"item": "<id>", "asks": "yes" or "no",
"stated": "yes" or "no"}, every item exactly once.
"""


def audit(items: list[dict]) -> dict:
    import claude_e2e336_score as S
    twins = [it for it in items if it["kind"] == "never_told"]
    ans = [it for it in items if it["kind"] == "answerable"]
    gold = {(it["dialog_id"], it["k"]): it["gold"]["values"][0] for it in ans}
    leak = sum(any(S.vmatch(r["text"], gold[(it["dialog_id"], it["k"])]) for r in it["rows"]) for it in twins)
    return {"answerable": len(ans), "never_told": len(twins), "twins_with_value": leak,
            "G1": leak <= G1_MAX_SHARE * len(twins)}


def _write(folder: Path, items: list[dict]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")
    (folder / "batch.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items),
                                        encoding="utf-8")


def sample(items: list[dict], out: Path, n: int = N_SAMPLE, seed: int = SEED) -> dict:
    ans = sorted((it for it in items if it["kind"] == "answerable"), key=lambda it: (it["dialog_id"], it["k"]))
    pick = random.Random(seed).sample(ans, min(n, len(ans)))
    batch, key = [], {}
    for i, it in enumerate(pick, 1):
        iid = f"g{i:03d}"
        key[iid] = {"dialog_id": it["dialog_id"], "k": it["k"]}
        batch.append({"item": iid, "earlier_messages": [r["text"] for r in it["rows"]], "last_message": it["question"],
                      "fact": {"about": it["owner"], "relation": it["rel"], "value": it["gold"]["values"][0]}})
    for j in ("a", "b"):
        _write(out / f"judge_{j}", batch)
    (out.parent / "gate_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    return {"items": len(batch)}


def _labels(folder: Path) -> dict:
    p = folder / "labels" / "batch.jsonl"
    out = {}
    for r in Y.load(p):
        assert r["item"] not in out, f"{p}: {r['item']} twice"
        assert all(r[q] in ("yes", "no") for q in QS), f"{p}: bad label for {r['item']}"
        out[r["item"]] = {q: r[q] for q in QS}
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
    yes, agree = Counter(), Counter()
    for x in batch:
        i = x["item"]
        for q in QS:
            lab = a[i][q] if a[i][q] == b[i][q] else c[i][q]
            yes[q] += lab == "yes"
            agree[q] += a[i][q] == b[i][q]
    res = {"items": len(batch), "asks_yes": yes["asks"], "stated_yes": yes["stated"],
           "judges_agree": dict(agree), "splits": len(need),
           "G2": yes["asks"] >= G2_MIN, "G3": yes["stated"] >= G3_MIN}
    (out.parent / "gate_result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def selftest() -> None:
    import claude_y1t_data as T
    fr = lambda act, facts=(), ask=None: {"act": act, "facts": list(facts), "ask": ask}  # noqa: E731
    fa = lambda o, rel, v, mode="ASSERT": {"owner": o, "rel": rel, "value": v, "mode": mode}  # noqa: E731

    def build(n_leak: int) -> list[dict]:
        seeds, kept = [], []
        for i in range(70):
            seeds.append({"dialog_id": f"d{i}", "turns": [
                {"k": 1, "intent": "smalltalk", "gold": fr("CHAT")},
                {"k": 2, "intent": "teach", "gold": fr("TELL", [fa("Mira", "dog", "Tansy")])},
                {"k": 3, "intent": "ask", "gold": fr("ASK", [], {"owner": "Mira", "rel": "dog", "inverse": False})}]})
            small = "tansy is such a cute name" if i < n_leak else f"long day number {i}"   # the twin keeps this
            kept += [{"id": f"glm320-d{i}-t1", "turn": small},
                     {"id": f"glm320-d{i}-t2", "turn": "mira's dog is Tansy"},
                     {"id": f"glm320-d{i}-t3", "turn": "what's mira's dog called?"}]
        return T.build_items(seeds, kept)[0]

    items = build(3)
    au = audit(items)
    assert au == {"answerable": 70, "never_told": 70, "twins_with_value": 3, "G1": True}, au
    au = audit(build(4))
    assert au["twins_with_value"] == 4 and not au["G1"], au          # 4 > 5% of 70
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "judges"
        assert sample(items, out)["items"] == 60
        batch = Y.load(out / "judge_a" / "batch.jsonl")
        assert batch == Y.load(out / "judge_b" / "batch.jsonl") and len({x["item"] for x in batch}) == 60
        assert all(set(x) == {"item", "earlier_messages", "last_message", "fact"} for x in batch)
        assert not any("dialog_id" in json.dumps(x) or "never_told" in json.dumps(x) for x in batch)
        key = json.loads((Path(d) / "gate_key.json").read_text())
        assert len(key) == 60
        for j, f in (("a", lambda n: ("yes", "yes")), ("b", lambda n: ("no", "yes") if n < 8 else ("yes", "yes"))):
            (out / f"judge_{j}" / "labels").mkdir()
            (out / f"judge_{j}" / "labels" / "batch.jsonl").write_text("".join(
                json.dumps({"item": x["item"], "asks": f(n)[0], "stated": f(n)[1]}) + "\n"
                for n, x in enumerate(batch)))
        assert splits(out) == 8
        (out / "judge_c" / "labels").mkdir()
        (out / "judge_c" / "labels" / "batch.jsonl").write_text("".join(
            json.dumps({"item": x["item"], "asks": "no", "stated": "yes"}) + "\n"
            for x in Y.load(out / "judge_c" / "batch.jsonl")))
        res = score(out)
        assert res["asks_yes"] == 52 and res["stated_yes"] == 60 and res["splits"] == 8, res
        assert not res["G2"] and res["G3"] and res["judges_agree"] == {"asks": 52, "stated": 60}
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    au = sub.add_parser("audit")
    au.add_argument("--items", required=True)
    sm = sub.add_parser("sample")
    sm.add_argument("--items", required=True)
    sm.add_argument("--out", required=True)
    sm.add_argument("--n", type=int, default=N_SAMPLE)
    sm.add_argument("--seed", type=int, default=SEED)
    for name in ("splits", "score"):
        sub.add_parser(name).add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "audit":
        print(json.dumps(audit(Y.load(a.items))))
    elif a.cmd == "sample":
        print(json.dumps(sample(Y.load(a.items), Path(a.out), a.n, a.seed)))
    elif a.cmd == "splits":
        print(json.dumps({"splits": splits(Path(a.out))}))
    else:
        print(json.dumps(score(Path(a.out))))


if __name__ == "__main__":
    main()
