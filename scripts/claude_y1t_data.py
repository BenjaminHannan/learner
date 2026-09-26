#!/usr/bin/env python3
"""y1t: trained doubt, the practice data (Answering-from-memory thread, 2026-09-26). New file.

y1g (artifacts/claude-y1g-20260926/VERIFY-y1g.md) was NO-GO: the plain 1B's own tries carry a doubt signal, but a
hand-written agreement rule on 5 noisy tries threw away too many right answers. y1g's PLAN names the fallback: the 1B
learns when to say "I don't know" from its own graded drafts. Ben's 16:39 "Use GLM" (goals page 5f38f110e): nothing
trained on is written or judged by Claude. So:
- chats: Reading facts' lis-320 GLM dialogs. Code chose every fact (seeds.jsonl); GLM 5.3 Flash wrote the wording;
  lis-320's code check kept or dropped each turn (kept.jsonl). Only kept user turns are shown, in order.
- questions: the dialog's own "ask" turns (GLM wording). The gold is the latest ASSERT/CORRECT value that the seed's
  code frames give for (owner, rel) among the kept turns before the ask, counting a fact only when its value is typed
  in that user turn (a "yes" to the assistant's question does not put the value in the user's words). Never-told twin: the same ask with every
  kept earlier turn whose seed frame holds a fact on that (owner, rel) removed; gold "I don't know".
- drafts: the plain 1B answers each item in y1f's L1 layout (greedy + K samples, T 0.7 / top-p 0.9). Code grades
  every draft with the 336 scorer (score_ask) plus y1f's checks. An old, corrected value does not match the gold, so it
  is graded wrong (Wrong answers stated as fact asked for this, 16:15 UTC).
- targets: the greedy draft if it is graded right, else the first right sample (the 1B's own words); if no draft is
  right, or the ask is a never-told twin, the fixed "I don't know." (Y.FALLBACK). "I don't know" rows are capped at
  the number of answer rows (seeded subsample), so the practice does not teach refusing. A small set is repeated
  so about 1500 rows pass through training (each row at most 3 times; the trainer's recipe is 1 pass).
Output rows are bm-398r's trainer format ({"system", "user", "answer"}; dev rows add "kind" and "layout"), so the
sealed trainer (scripts/claude_bm398r_train.py: rank 16 LoRA on q/k/v/o, 1 epoch, lr 2e-4, batch 8, loss on the answer
tokens) is used unchanged, and the sealed y1g harness scores the merged model on DEV.

  python -B scripts/claude_y1t_data.py split-seeds --seeds SEEDS.jsonl [--parts 8]   -> SEEDS_0.jsonl .. SEEDS_7.jsonl
  python -B scripts/claude_y1t_data.py items --seeds SEEDS --kept KEPT --out DIR [--seed 4027] [--dev-share 0.15]
      -> DIR/items_train.jsonl, DIR/items_dev.jsonl (CPU; prints counts)
  python -B scripts/claude_y1t_data.py drafts --model BASE --dir DIR [--k 4] [--seed 4027] [--max-items 3000]
      -> DIR/drafts.jsonl, DIR/train.jsonl, DIR/dev.jsonl (GPU; prints counts)
  python -B scripts/claude_y1t_data.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_y1d_readchat as Y  # noqa: E402  (sealed: load, Gen, _seed, FALLBACK)
import claude_y1f_layout as F  # noqa: E402  (sealed: messages, checked)

CURRENT = ("ASSERT", "CORRECT")
K_SAMPLES = 4
MIN_ROW_PASSES, MAX_REPEAT = 1500, 3     # small practice sets: each row repeated so ~1500 rows pass (at most 3 times)
SEED = 4027


def load(p) -> list[dict]:
    return Y.load(p)


def _key(owner: str, rel: str) -> tuple[str, str]:
    return (str(owner).strip().lower(), str(rel).strip().lower())


def build_items(seeds: list[dict], kept: list[dict]) -> tuple[list[dict], Counter]:
    """Practice items from kept GLM turns and the seeds' code frames. Never reads anything but these two files."""
    import claude_e2e336_score as S
    text = {}
    for r in kept:
        did, k = r["id"].rsplit("-t", 1)
        text[(did.removeprefix("glm320-"), int(k))] = r["turn"]
    items, c = [], Counter()
    for d in seeds:
        shown = [t for t in d["turns"] if (d["dialog_id"], t["k"]) in text]
        for i, t in enumerate(shown):
            if t["intent"] != "ask":
                continue
            c["asks_kept"] += 1
            ask = t["gold"].get("ask") or {}
            key = _key(ask.get("owner", ""), ask.get("rel", ""))
            before = shown[:i]
            latest = None
            for u in before:
                for f in u["gold"].get("facts") or []:
                    # told = the value is typed in that kept user turn (a "yes" to the assistant's question is not)
                    if _key(f["owner"], f["rel"]) == key and S.vmatch(text[(d["dialog_id"], u["k"])], f["value"]):
                        latest = f
            if latest is None or latest.get("mode") not in CURRENT:
                c["skip_no_current_fact"] += 1
                continue
            q = text[(d["dialog_id"], t["k"])]
            rows = [{"id": u["k"], "text": text[(d["dialog_id"], u["k"])], "said_at": None} for u in before]
            base = {"dialog_id": d["dialog_id"], "k": t["k"], "question": q, "owner": key[0], "rel": key[1]}
            items.append(base | {"kind": "answerable", "rows": rows,
                                 "gold": {"type": "value", "values": [str(latest["value"])]},
                                 "corrected": latest.get("mode") == "CORRECT"})
            keep = [r for r, u in zip(rows, before)
                    if not any(_key(f["owner"], f["rel"]) == key for f in u["gold"].get("facts") or [])]
            items.append(base | {"kind": "never_told", "rows": keep, "gold": {"type": "idk", "values": []},
                                 "corrected": False})
            c["items_answerable"] += 1
            c["items_never_told"] += 1
            c["corrected"] += latest.get("mode") == "CORRECT"
    return items, c


def split(items: list[dict], seed: int, dev_share: float) -> tuple[list[dict], list[dict]]:
    dialogs = sorted({it["dialog_id"] for it in items})
    random.Random(seed).shuffle(dialogs)
    dev = set(dialogs[:round(dev_share * len(dialogs))])
    return [it for it in items if it["dialog_id"] not in dev], [it for it in items if it["dialog_id"] in dev]


def grade(it: dict, draft: str) -> bool:
    """Right = the 336 scorer says RIGHT and y1f's checks pass (never-told: the draft abstains)."""
    import claude_chat338_agent as C38
    import claude_e2e336_score as S
    lab = S.score_ask({"gold": it["gold"]}, {"reply": draft}, None)
    if it["gold"]["type"] == "idk":
        return lab == "RIGHT"
    known = C38._words([it["question"]] + [r["text"] for r in it["rows"]])
    return lab in ("RIGHT", "RIGHT_CONFIRM") and F.checked(draft, it["question"], known) is None


def draft_item(gen, it: dict, k: int) -> dict:
    import claude_chat338_agent as C38
    msgs = F.messages("L1", it["question"], it["rows"])
    g = C38.trim(gen.greedy_chat(msgs))
    ss = [C38.trim(s) for s in gen.sample_chat(msgs, k)]
    ok_g, ok_s = grade(it, g), [grade(it, s) for s in ss]
    if it["kind"] == "never_told":
        target, src = Y.FALLBACK, "idk_never_told"
    elif ok_g:
        target, src = g, "own_greedy"
    elif any(ok_s):
        target, src = ss[ok_s.index(True)], "own_sample"
    else:
        target, src = Y.FALLBACK, "idk_all_wrong"
    return {"greedy": g, "samples": ss, "greedy_right": ok_g, "samples_right": sum(ok_s), "target": target,
            "src": src}


def trainer_row(it: dict, answer: str) -> dict:
    m = F.messages("L1", it["question"], it["rows"])
    return {"system": m[0]["content"], "user": m[1]["content"], "answer": answer}


def drafts(gen, d: Path, k: int, seed: int, max_items: int, log=print) -> dict:
    items = load(d / "items_train.jsonl")
    if max_items and len(items) > max_items:
        pairs = sorted({(it["dialog_id"], it["k"]) for it in items})
        random.Random(seed).shuffle(pairs)
        keep = set(pairs[:max_items // 2])
        items = [it for it in items if (it["dialog_id"], it["k"]) in keep]
    out = d / "drafts.jsonl"
    out.write_text("", encoding="utf-8")
    c = Counter()
    rows_ans, rows_idk = [], []
    for n, it in enumerate(items, 1):
        Y._seed(seed + n)
        r = draft_item(gen, it, k)
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"dialog_id": it["dialog_id"], "k": it["k"], "kind": it["kind"],
                                 "corrected": it["corrected"], **r}, ensure_ascii=False) + "\n")
        c[r["src"]] += 1
        c[f"{it['kind']}_greedy_right"] += r["greedy_right"]
        c[f"{it['kind']}_n"] += 1
        c["corrected_greedy_right"] += it["corrected"] and r["greedy_right"]
        c["corrected_n"] += it["corrected"]
        (rows_ans if r["target"] != Y.FALLBACK else rows_idk).append(trainer_row(it, r["target"]))
        if n % 100 == 0:
            log(f"[y1t] drafts {n}/{len(items)}")
    rng = random.Random(seed)
    rng.shuffle(rows_idk)
    rows_idk = rows_idk[:len(rows_ans)]
    base = rows_ans + rows_idk
    repeat = min(MAX_REPEAT, max(1, math.ceil(MIN_ROW_PASSES / max(1, len(base)))))
    train = base * repeat
    rng.shuffle(train)
    (d / "train.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in train), encoding="utf-8")
    dev = []
    for it in load(d / "items_dev.jsonl"):
        r = trainer_row(it, it["gold"]["values"][0] if it["gold"]["values"] else "")
        dev.append(r | {"kind": "missing" if it["kind"] == "never_told" else "value", "layout": "L1"})
    (d / "dev.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in dev), encoding="utf-8")
    res = {"items": len(items), "train_rows": len(train), "repeat": repeat, "answer_rows": len(rows_ans),
           "idk_rows": len(rows_idk),
           "dev_rows": len(dev), "counts": dict(sorted(c.items()))}
    (d / "drafts_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


# ---------------------------------------------------------------- selftest

class _Fake:
    """Greedy answers the last capitalised word of the last line; samples: that, then 'Pim.'."""

    def greedy_chat(self, msgs):
        import re
        lines = re.findall(r'User said, "(.*)"', msgs[-1]["content"])
        caps = re.findall(r"\b([A-Z][a-z]+)\b", lines[-1]) if lines else []
        return (caps[-1] + ".") if caps else "I don't know."

    def sample_chat(self, msgs, n):
        return [self.greedy_chat(msgs)] + ["Pim."] * (n - 1)


def selftest() -> None:
    fr = lambda act, facts=(), ask=None: {"act": act, "facts": list(facts), "ask": ask}  # noqa: E731
    fa = lambda o, rel, v, mode="ASSERT", **kw: {"owner": o, "rel": rel, "value": v, "mode": mode, **kw}  # noqa: E731
    seeds = [{"dialog_id": "d1", "turns": [
        {"k": 1, "intent": "teach", "gold": fr("TELL", [fa("me", "sister", "Mira"), fa("Mira", "dog", "Rolo")])},
        {"k": 2, "intent": "smalltalk", "gold": fr("CHAT")},
        {"k": 3, "intent": "correct", "gold": fr("TELL", [fa("Mira", "dog", "Tansy", "CORRECT", old="Rolo")])},
        {"k": 4, "intent": "ask", "gold": fr("ASK", [], {"owner": "Mira", "rel": "dog", "inverse": False})},
        {"k": 5, "intent": "hypothetical", "gold": fr("SUPPOSE", [fa("me", "cat", "Opal", "SUPPOSE")])},
        {"k": 6, "intent": "ask", "gold": fr("ASK", [], {"owner": "me", "rel": "cat", "inverse": False})}]},
        {"dialog_id": "d2", "turns": [
            {"k": 1, "intent": "teach", "gold": fr("TELL", [fa("me", "city", "Varno")])},
            {"k": 2, "intent": "ask", "gold": fr("ASK", [], {"owner": "me", "rel": "city", "inverse": False})}]},
        {"dialog_id": "d3", "turns": [
            {"k": 1, "intent": "yes_after_ask", "gold": fr("TELL", [fa("me", "pet", "Nib")])},
            {"k": 2, "intent": "ask", "gold": fr("ASK", [], {"owner": "me", "rel": "pet", "inverse": False})}]}]
    kept = [{"id": "glm320-d1-t1", "turn": "my sister Mira got a dog called Rolo"},
            {"id": "glm320-d1-t2", "turn": "long day lol"},
            {"id": "glm320-d1-t3", "turn": "wait no mira's dog is Tansy not rolo"},
            {"id": "glm320-d1-t4", "turn": "whats mira's dog called again"},
            {"id": "glm320-d1-t6", "turn": "did i get a cat?"},
            {"id": "glm320-d2-t2", "turn": "where do i live"},              # d2's teach turn was dropped
            {"id": "glm320-d3-t1", "turn": "yep that's right"}, {"id": "glm320-d3-t2", "turn": "what's my pet?"}]
    items, c = build_items(seeds, kept)
    assert c["asks_kept"] == 4 and c["items_answerable"] == 1 and c["skip_no_current_fact"] == 3, c
    a, nt = items
    assert a["gold"]["values"] == ["Tansy"] and a["corrected"] and len(a["rows"]) == 3
    assert nt["gold"]["type"] == "idk" and [r["id"] for r in nt["rows"]] == [2]   # both turns on (mira, dog) removed
    assert grade(a, "Tansy.") and not grade(a, "Rolo.") and not grade(a, "I don't know.")
    assert grade(nt, "I don't know.") and not grade(nt, "Tansy.")
    tr, dv = split(items * 1, 4027, 0.0)
    assert len(tr) == 2 and not dv
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "items_train.jsonl").write_text("".join(json.dumps(x) + "\n" for x in items))
        (d / "items_dev.jsonl").write_text("".join(json.dumps(x) + "\n" for x in items))
        res = drafts(_Fake(), d, 4, 4027, 0, log=lambda s: None)
        assert res["items"] == 2 and res["answer_rows"] == 1 and res["idk_rows"] == 1 and res["repeat"] == 3, res
        tr = load(d / "train.jsonl")
        assert len(tr) == 6
        tr = tr[:2] if tr[0]["answer"] != tr[1]["answer"] else [tr[0], next(r for r in tr if r["answer"] != tr[0]["answer"])]
        assert {r["answer"] for r in tr} == {"Tansy.", Y.FALLBACK}
        assert all(set(r) == {"system", "user", "answer"} for r in tr) and "Question: whats mira" in tr[0]["user"] + \
            tr[1]["user"]
        dv = load(d / "dev.jsonl")
        assert [r["kind"] for r in dv] == ["value", "missing"] and dv[0]["answer"] == "Tansy"
        dr = load(d / "drafts.jsonl")
        assert dr[0]["src"] == "own_greedy" and dr[1]["src"] == "idk_never_told"
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("items")
    for k in ("--seeds", "--kept", "--out"):
        i.add_argument(k, required=True)
    i.add_argument("--seed", type=int, default=SEED)
    i.add_argument("--dev-share", type=float, default=0.15)
    sp = sub.add_parser("split-seeds")
    sp.add_argument("--seeds", required=True)
    sp.add_argument("--parts", type=int, default=8)
    g = sub.add_parser("drafts")
    g.add_argument("--model", required=True)
    g.add_argument("--dir", required=True)
    g.add_argument("--k", type=int, default=K_SAMPLES)
    g.add_argument("--seed", type=int, default=SEED)
    g.add_argument("--max-items", type=int, default=3000)
    a = ap.parse_args()
    if a.cmd == "split-seeds":
        lines = [x for x in Path(a.seeds).read_text(encoding="utf-8").splitlines() if x.strip()]
        for i in range(a.parts):
            Path(f"{a.seeds[:-len('.jsonl')]}_{i}.jsonl").write_text(
                "".join(x + "\n" for x in lines[i::a.parts]), encoding="utf-8")
        print(json.dumps({"dialogs": len(lines), "parts": a.parts}))
    elif a.cmd == "items":
        items, c = build_items(load(a.seeds), load(a.kept))
        tr, dv = split(items, a.seed, a.dev_share)
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        for name, rows in (("items_train.jsonl", tr), ("items_dev.jsonl", dv)):
            (out / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(json.dumps({"counts": dict(sorted(c.items())), "train_items": len(tr), "dev_items": len(dv)}))
    else:
        t0 = time.time()
        res = drafts(Y.Gen(a.model), Path(a.dir), a.k, a.seed, a.max_items, log=lambda s: print(s, flush=True))
        print(json.dumps(res | {"minutes": round((time.time() - t0) / 60, 1)}), flush=True)


if __name__ == "__main__":
    main()
