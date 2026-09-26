#!/usr/bin/env python3
"""k1g DEV check: does MiniCPM5-1B write more useful creative replies in its Think mode? (Creative answers in chat
thread, 2026-09-26, at the Thread manager's question "is it the model or the recipe?"). Readable DEV items only
(artifacts/claude-k1a-dev-20260926, 40 chats). Not a registered run; $0 (CPU).

The k1a writer already samples at temperature 0.7, top_p 0.9 with thinking off, close to the model card's No Think
recommendation (0.7 / 0.95). Untried: the card's Think mode (enable_thinking=True, temperature 0.9, top_p 0.95).

samples  For every DEV item, the k1a writer's W1 prompt (SYSTEM333D, the chat as messages with the lead turns
         answered greedily by twin b, as claude_k1c_pilot.py --form W1 does), rendered with enable_thinking=True.
         Draws one sample at a time (at most MAX_DRAWS, MAX_NEW new tokens each, seed*1000 + item index), cuts the
         think block, trims and guards as k1a does, and keeps the first passing draw (None = the fallback line).
packet   One blind line per distinct (item, reply) over two conditions: THINK (this file's reply) and NOTHINK (k1a's
         first passing draft from the k1c pilot's W1 samples, --w1). Shuffled with seed 4778, ids G0000.., so the
         judges see both conditions mixed. Judge words: artifacts/claude-k1c-20260926/JUDGE-k1c.md.
score    Useful per condition (a fallback counts as not useful), items only one side got, exact sign test.
Budget: 1280 new tokens (first set at 768; at 17:36 UTC, before any judging, the second DEV item's think block took
about 700 tokens and the cap cut its answer to one sentence, so the run was restarted from scratch at 1280).
Shards: --shard k --nshards n runs items with index % n == k into samples.s<k>.jsonl (same per-item seeds).
Marks (fixed 17:33 UTC 09-26 before any draw, sent to the Thread manager): THINK >= NOTHINK + 5 and >= 19 of 40 ->
the LFM swap is premature; THINK <= NOTHINK + 2 -> Think mode doesn't rescue MiniCPM5-1B; otherwise unclear.

  python -B scripts/claude_k1g_think_dev.py samples --items DEV/items.jsonl --model <MiniCPM5-1B> --out OUT
  python -B scripts/claude_k1g_think_dev.py packet --items DEV/items.jsonl --out OUT --w1 W1/samples.jsonl
  python -B scripts/claude_k1g_think_dev.py score --out OUT --judges J1,J2[,J3]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MAX_DRAWS, MAX_NEW, TEMP, TOP_P = 3, 1280, 0.9, 0.95
THINK_BLOCK = re.compile(r"^.*?</think>", re.S)


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def after_think(raw: str) -> tuple[str, bool]:
    """The answer after the think block; ("", False) when the block never closed."""
    if "</think>" in raw:
        return THINK_BLOCK.sub("", raw, count=1).strip(), True
    if "<think>" in raw:
        return "", False
    return raw.strip(), True


def run_samples(a):
    import torch
    import claude_chat338_agent as C38
    import claude_cre333b_agent as CB
    import claude_cre333d_agent as CD
    import claude_e2e336_twin as OLD
    import claude_e2e336_twinb as TB
    g = CB.Gen333b(a.model)
    OLD._CACHE[a.model] = (g.tok, g.model, g.dev)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"samples.s{a.shard}.jsonl"
    done = {r["item_id"] for r in load(path)} if path.exists() else set()
    with open(path, "a", encoding="utf-8") as fh:
        for i, it in enumerate(load(a.items)):
            if it["item_id"] in done or i % a.nshards != a.shard:
                continue
            t0 = time.time()
            text, hist = it["last"], []
            with tempfile.TemporaryDirectory() as d:
                tw = TB.Twin336b(d, a.model)
                for lead in it["turns"]:
                    hist += [{"role": "user", "content": lead}, {"role": "assistant", "content": tw.turn(lead)[0]}]
            known = C38._words([text, ""] + [m["content"] for m in hist])
            msgs = [{"role": "system", "content": CD.SYSTEM333D}] + hist + [{"role": "user", "content": text}]
            prompt = g.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=True)
            ids = g.tok(prompt, return_tensors="pt").to(g.dev)
            torch.manual_seed(a.seed * 1000 + i)
            draws, reply = [], None
            for _ in range(MAX_DRAWS):
                with torch.no_grad():
                    o = g.model.generate(**ids, max_new_tokens=MAX_NEW, do_sample=True, temperature=TEMP,
                                         top_p=TOP_P, pad_token_id=g.tok.eos_token_id)
                new = o[0][ids["input_ids"].shape[1]:]
                raw = g.tok.decode(new, skip_special_tokens=True)
                ans, closed = after_think(raw)
                tc = C38.trim(ans)
                gd = CD.guard333d(tc, text, known)
                draws.append({"raw": raw, "closed": closed, "tokens": int(new.shape[0]), "trimmed": tc, "guard": gd})
                if gd is None:
                    reply = tc
                    break
            fh.write(json.dumps({"item_id": it["item_id"], "draws": draws, "reply": reply}, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[k1g] {it['item_id']} draws {len(draws)} tokens {[d['tokens'] for d in draws]} "
                  f"{time.time() - t0:.0f}s", flush=True)


def packet(a):
    import claude_cre333_agent as C
    items = {it["item_id"]: it for it in load(a.items)}
    think = {r["item_id"]: (r["reply"] if r["reply"] is not None else C.FALLBACK)
             for f in sorted(Path(a.out).glob("samples.s*.jsonl")) for r in load(f)}
    nothink = {}
    for r in load(a.w1):
        ok = [s["trimmed"] for s in r["samples"] if s["guard"] is None]
        nothink[r["item_id"]] = ok[0] if ok else C.FALLBACK
    if set(think) != set(items) or set(nothink) != set(items):
        raise SystemExit("k1g: both conditions need every DEV item")
    groups = {}
    for cond, rep in (("THINK", think), ("NOTHINK", nothink)):
        for iid, t in rep.items():
            groups.setdefault((iid, t), []).append(cond)
    pool = sorted(groups)
    random.Random(4778).shuffle(pool)
    key, pk = {}, []
    for n, (iid, t) in enumerate(pool):
        cid = f"G{n:04d}"
        key[cid] = [{"cond": c, "item_id": iid} for c in groups[(iid, t)]]
        pk.append({"id": cid, "chat": list(items[iid]["turns"]), "request": items[iid]["last"], "reply": t})
    (Path(a.out) / "packet.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pk),
                                              encoding="utf-8")
    (Path(a.out) / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(json.dumps({"lines": len(pk), "shared": sum(len(v) > 1 for v in key.values())}))


def score(a):
    import claude_k1c_score as KC
    key = json.loads((Path(a.out) / "key.json").read_text(encoding="utf-8"))
    js = KC._judges(a.judges)
    j1, j2 = js[0], js[1]
    split = [c for c in key if KC.yes(j1[c]["useful"]) != KC.yes(j2[c]["useful"])]
    if len(js) < 3:
        (Path(a.out) / "splits.json").write_text(json.dumps(sorted(split)), encoding="utf-8")
        print(json.dumps({"lines": len(key), "useful_splits": len(split)}))
        return
    j3 = js[2]
    import claude_cre333_agent as C
    pk = {r["id"]: r for r in load(Path(a.out) / "packet.jsonl")}
    u = {}
    for c, who in key.items():
        v = KC.yes(j1[c]["useful"]) if c not in split else KC.yes(j3[c]["useful"])
        v = v and pk[c]["reply"] != C.FALLBACK
        for w in who:
            u[(w["cond"], w["item_id"])] = v
    ids = sorted({i for _, i in u})
    t = sum(u[("THINK", i)] for i in ids)
    n = sum(u[("NOTHINK", i)] for i in ids)
    b = sum(u[("THINK", i)] and not u[("NOTHINK", i)] for i in ids)
    c = sum(u[("NOTHINK", i)] and not u[("THINK", i)] for i in ids)
    verdict = ("premature" if t >= n + 5 and t >= 19 else "no rescue" if t <= n + 2 else "unclear")
    print(json.dumps({"items": len(ids), "THINK": t, "NOTHINK": n, "THINK_only": b, "NOTHINK_only": c,
                      "sign_p_one_sided": round(KC.sign_p(b, c), 4), "third_judged": len(split),
                      "reading": verdict}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["samples", "packet", "score"])
    ap.add_argument("--items", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--seed", type=int, default=4777)
    ap.add_argument("--w1", default="")
    ap.add_argument("--judges", default="")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()
    {"samples": run_samples, "packet": packet, "score": score}[a.mode](a)


if __name__ == "__main__":
    main()
