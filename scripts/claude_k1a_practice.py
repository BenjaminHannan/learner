#!/usr/bin/env python3
"""k1a practice check (Creative answers in chat thread, 2026-09-26): the creative writer with and without the chat,
next to the plain 1B, on readable DEV items only (artifacts/claude-k1a-dev-20260926). Not a registered run.

Per item (fresh state each):
  T   twin b (claude_e2e336_twinb.Twin336b: whole chat, greedy, 160 new tokens) answers every lead-in turn and the
      request.
  W0  cre333d's writer exactly (claude_k1a_cre.write_k1a with hist=[]): system line + request only.
  W1  the k1a writer: the same, plus the chat so far = the lead-in turns and T's replies to them (a stand-in for the
      agent's own replies; the real agent's come from chat338 or its reader).
  W0 and W1 use the same sampling seed per item, so with no lead-in their prompts and replies are identical.
  No reader and no notebook here, so the writer's "facts" are empty in both W arms (0.2c's reader saved on 5 of 32
  lead turns). No sleep adapter (not on this machine). Any item is written by the writer, routed or not; the row
  says whether is_creative333c would have routed it.

  python -B scripts/claude_k1a_practice.py run --items DEV/items.jsonl --model <MiniCPM5-1B dir> --out OUT [--limit N]
  python -B scripts/claude_k1a_practice.py packets --items DEV/items.jsonl --out OUT     (blind packets + key)
  python -B scripts/claude_k1a_practice.py score --items DEV/items.jsonl --out OUT --judges J1.jsonl,J2.jsonl[,J3]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ARMS = ("T", "W0", "W1", "W2", "W3")


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def run(a):
    import torch
    import claude_chat338_agent as C38
    import claude_cre333_agent as C
    import claude_cre333b_agent as CB
    import claude_e2e336_twin as OLD
    import claude_e2e336_twinb as TB
    import claude_k1a_cre as K
    g = CB.Gen333b(a.model)
    gen = C38.Gen338(share=g)
    OLD._CACHE[a.model] = (g.tok, g.model, g.dev)          # the twin shares the loaded weights
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "rows.jsonl"
    done = {(r["item_id"], r["arm"]) for r in load(path)} if path.exists() else set()
    items = load(a.items)[: a.limit] if a.limit else load(a.items)
    with open(path, "a", encoding="utf-8") as fh:
        for i, it in enumerate(items):
            if all((it["item_id"], x) in done for x in ARMS):
                continue
            t0 = time.time()
            with tempfile.TemporaryDirectory() as d:
                tw = TB.Twin336b(d, a.model)
                hist = []
                for lead in it["turns"]:
                    r = tw.turn(lead)[0]
                    hist += [{"role": "user", "content": lead}, {"role": "assistant", "content": r}]
                rt = tw.turn(it["last"])[0]
            rows = [{"item_id": it["item_id"], "arm": "T", "reply": rt, "fallback": False}]
            for arm, h in (("W0", []), ("W1", hist)):
                torch.manual_seed(a.seed * 1000 + i)
                stats: dict = {}
                r = K.write_k1a(gen, it["last"], "", h, stats)
                rows.append({"item_id": it["item_id"], "arm": arm, "reply": r if r is not None else C.FALLBACK,
                             "fallback": r is None, "guards": stats, "hist_msgs": len(h)})
            for r in rows:
                r["routed"] = CB.is_creative333c(it["last"])
                r["lead"] = len(it["turns"])
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[k1a-practice] {it['item_id']} {time.time() - t0:.0f}s", flush=True)


def run_w2(a):
    """W2 (added after the 333e E.2 precedent, before any judging): the writer gets only the user's earlier messages,
    quoted inside its system line, not the chat as messages (so it can't copy an earlier reply). W3 = k1b
    (scripts/claude_k1b_cre.py): W0's samples, but a reply that ended on its own is not trimmed. Same seed as W0/W1."""
    import torch
    import claude_chat338_agent as C38
    import claude_cre333_agent as C
    import claude_cre333b_agent as CB
    import claude_k1a_cre as K
    g = CB.Gen333b(a.model)
    gen = C38.Gen338(share=g)
    path = Path(a.out) / "rows.jsonl"
    done = {(r["item_id"], r["arm"]) for r in load(path)}
    items = load(a.items)[: a.limit] if a.limit else load(a.items)
    with open(path, "a", encoding="utf-8") as fh:
        for i, it in enumerate(items):
            t0 = time.time()
            for arm in ("W2", "W3"):
                if (it["item_id"], arm) in done:
                    continue
                torch.manual_seed(a.seed * 1000 + i)
                stats: dict = {}
                if arm == "W2":
                    r = K.write_k1a_said(gen, it["last"], "", list(it["turns"]), stats)
                else:                        # W3 = k1b: W0's exact samples, a finished reply kept whole
                    import claude_k1b_cre as KB
                    r = KB.write_k1b(gen, it["last"], "", stats)
                row = {"item_id": it["item_id"], "arm": arm, "reply": r if r is not None else C.FALLBACK,
                       "fallback": r is None, "guards": stats, "hist_msgs": len(it["turns"]) if arm == "W2" else 0,
                       "routed": CB.is_creative333c(it["last"]), "lead": len(it["turns"])}
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                fh.flush()
            print(f"[k1a-practice-w2] {it['item_id']} {time.time() - t0:.0f}s", flush=True)


def packets(a):
    items = {it["item_id"]: it for it in load(a.items)}
    rows = load(Path(a.out) / "rows.jsonl")
    random.Random(a.seed + 7).shuffle(rows)
    key, pk = {}, []
    for n, r in enumerate(rows):
        cid = f"P{n:04d}"
        key[cid] = {"arm": r["arm"], "item_id": r["item_id"]}
        it = items[r["item_id"]]
        pk.append({"id": cid, "chat": it["turns"], "request": it["last"], "reply": r["reply"]})
    (Path(a.out) / "packet.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pk),
                                              encoding="utf-8")
    (Path(a.out) / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(json.dumps({"packets": len(pk)}))


def yes(v) -> bool:
    return str(v).strip().lower() in ("yes", "true", "1", "useful")


def score(a):
    key = json.loads((Path(a.out) / "key.json").read_text(encoding="utf-8"))
    items = {it["item_id"]: it for it in load(a.items)}
    rows = {(r["item_id"], r["arm"]): r for r in load(Path(a.out) / "rows.jsonl")}
    js = [{j["id"]: j for j in load(p)} for p in a.judges.split(",")]
    c, made, agree, split = Counter(), Counter(), 0, 0
    for cid, k in key.items():
        v = [yes(j[cid]["useful"]) for j in js[:2]]
        if v[0] == v[1]:
            agree += 1
            u = v[0]
        else:
            split += 1
            u = yes(js[2][cid]["useful"]) if len(js) > 2 else False
        it = items[k["item_id"]]
        grp = ("lead" if it["turns"] else "nolead")
        arm = k["arm"]
        for g in ("all", grp, it["kind"], "routed" if rows[(k["item_id"], arm)]["routed"] else "not_routed"):
            c[(arm, g, "n")] += 1
            c[(arm, g, "useful")] += u
        made[arm] += max(int(j[cid].get("made_up_user_facts", 0)) for j in js[:2])
        c[(arm, "all", "fallback")] += rows[(k["item_id"], arm)].get("fallback", False)
    out = {"judge_agreement": agree, "judge_splits": split, "made_up_max_of_2": dict(made)}
    for arm in ARMS:
        out[arm] = {g: f"{c[(arm, g, 'useful')]}/{c[(arm, g, 'n')]}"
                    for g in ("all", "lead", "nolead", "idea", "uses_facts", "routed", "not_routed")}
        out[arm]["fallbacks"] = c[(arm, "all", "fallback")]
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "run_w2", "packets", "score"])
    ap.add_argument("--items", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=4111)
    ap.add_argument("--judges", default="")
    a = ap.parse_args()
    {"run": run, "run_w2": run_w2, "packets": packets, "score": score}[a.mode](a)


if __name__ == "__main__":
    main()
