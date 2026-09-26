#!/usr/bin/env python3
"""k1d DEV pilot (Creative answers in chat thread, written 2026-09-26 16:31 UTC): the fallback if k1c FAILs. Readable
DEV items only (artifacts/claude-k1a-dev-20260926). Not a registered run.

Question: can the writer's own 1B, reading each of its 4 drafts the way the user would, tell which one does what was
asked? Brain picture (Ben 16:05; textbook-level, not checked here): a speaker hears their own planned sentence through
their comprehension system before saying it (Levelt's "perceptual loop" for self-monitoring) and changes course when it
doesn't fit. Here the listener is the same 1B, asked one question about each draft. No training, no hand-written
rules; the only hand-written text is the question below, which is a prompt, like the writer's system line.

Fixed before any listener score was computed (one wording, no variants tried):
  Y   the 1B's log p("Yes") - log p("No") for the first answer token, after this chat (the writer's template,
      thinking off):
        system: LISTEN_SYSTEM
        user:   LISTEN_USER filled with the user's earlier messages, the request and the draft
      Highest Y wins among the drafts that passed the guards; ties keep draw order.
Reads the k1c pilot's samples.jsonl (the k1a writer's 4 drafts per DEV item, same seeds) and writes listen.jsonl.
  python -B scripts/claude_k1d_pilot.py listen --items DEV/items.jsonl --model <MiniCPM5-1B> --out OUT
  python -B scripts/claude_k1d_pilot.py score --items DEV/items.jsonl --out OUT --verdicts V.json
score reports first / oracle / P (k1c, from OUT/pmi.jsonl) / Y, and how often Y and P pick the same draft.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_k1c_pilot as PL  # noqa: E402

load = PL.load
LISTEN_SYSTEM = "You read an assistant's draft reply before it is sent and say whether it should be sent."
LISTEN_USER = ("{chat}The user's latest message: {request}\n\nDraft reply:\n{draft}\n\n"
               "Does this draft do what the user asked, in the form they asked for, fitting what they said earlier, "
               "without inventing facts about them? Answer with one word: Yes or No.")


def listen_msgs(turns: list[str], request: str, draft: str) -> list[dict]:
    said = [t.strip() for t in turns if t and t.strip()]
    chat = ("The user's earlier messages:\n" + "\n".join(f"- {t}" for t in said) + "\n\n") if said else ""
    return [{"role": "system", "content": LISTEN_SYSTEM},
            {"role": "user", "content": LISTEN_USER.format(chat=chat, request=request, draft=draft)}]


def yes_no_ids(tok) -> tuple[int, int]:
    y = tok("Yes", add_special_tokens=False)["input_ids"]
    n = tok("No", add_special_tokens=False)["input_ids"]
    return y[0], n[0]


def listen_score(g, gen, msgs: list[dict], yn: tuple[int, int]) -> float:
    torch = g.torch
    ids = g.tok(gen._render(msgs), return_tensors="pt")["input_ids"].to(g.dev)
    with torch.no_grad():
        lp = torch.log_softmax(g.model(input_ids=ids).logits[0, -1].float(), -1)
    return float(lp[yn[0]] - lp[yn[1]])


def run_listen(a):
    import claude_chat338_agent as C38
    import claude_cre333b_agent as CB
    g = CB.Gen333b(a.model)
    gen = C38.Gen338(share=g)
    yn = yes_no_ids(g.tok)
    items = {it["item_id"]: it for it in load(a.items)}
    path = Path(a.out) / "listen.jsonl"
    done = {r["item_id"] for r in load(path)} if path.exists() else set()
    with open(path, "a", encoding="utf-8") as fh:
        for r in load(Path(a.out) / "samples.jsonl"):
            if r["item_id"] in done:
                continue
            t0 = time.time()
            it = items[r["item_id"]]
            ys = [listen_score(g, gen, listen_msgs(it["turns"], it["last"], s["trimmed"]), yn)
                  if s["guard"] is None else None for s in r["samples"]]
            fh.write(json.dumps({"item_id": r["item_id"], "Y": ys}) + "\n")
            fh.flush()
            print(f"[k1d-listen] {r['item_id']} {time.time() - t0:.0f}s", flush=True)


def score(a):
    verdict = json.loads(Path(a.verdicts).read_text(encoding="utf-8"))   # {"item\ttext": true/false}
    pm = {r["item_id"]: r["pmi"] for r in load(Path(a.out) / "pmi.jsonl")}
    ls = {r["item_id"]: r["Y"] for r in load(Path(a.out) / "listen.jsonl")}
    res = {"items": 0, "no_passing": 0, "unjudged": 0, "first": 0, "oracle": 0, "P": 0, "Y": 0,
           "Y_gained_vs_first": 0, "Y_lost_vs_first": 0, "Y_same_pick_as_P": 0, "Y_picked_not_first": 0}
    for r in load(Path(a.out) / "samples.jsonl"):
        res["items"] += 1
        ok = [k for k, s in enumerate(r["samples"]) if s["guard"] is None]
        if not ok:
            res["no_passing"] += 1
            continue
        v = [verdict.get(f"{r['item_id']}\t{r['samples'][k]['trimmed']}") for k in ok]
        if any(x is None for x in v):
            res["unjudged"] += 1
            continue
        p = [pm[r["item_id"]][k] for k in ok]
        y = [ls[r["item_id"]][k] for k in ok]
        jp = min(range(len(ok)), key=lambda i: (-p[i], i))
        jy = min(range(len(ok)), key=lambda i: (-y[i], i))
        res["first"] += bool(v[0])
        res["oracle"] += any(v)
        res["P"] += bool(v[jp])
        res["Y"] += bool(v[jy])
        res["Y_gained_vs_first"] += bool(v[jy]) and not v[0]
        res["Y_lost_vs_first"] += bool(v[0]) and not v[jy]
        res["Y_same_pick_as_P"] += jy == jp
        res["Y_picked_not_first"] += jy != 0
    print(json.dumps(res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["listen", "score"])
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--verdicts", default="")
    a = ap.parse_args()
    {"listen": run_listen, "score": score}[a.mode](a)


if __name__ == "__main__":
    main()
