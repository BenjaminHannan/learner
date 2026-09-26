#!/usr/bin/env python3
"""mu-403 pilot (report only, DEV data; "Making things up about you" thread, 2026-09-26). New file only.

Question before registering mu-403: does the 1B's own yes/no self-check (claude_mu403_ground.GroundScorer) rank its
chat samples by how much they make up about the user? And, as the fallback idea, does a plainer system line make it
assume less?

For up to --turns feelings/advice/followup turns of the mu-402 dev panel, rebuild chat 338's prompt exactly
(SYSTEM338, no notebook facts, the last 12 messages of arm B's own mu-402 transcript, the user's turn), then draw 4
samples with SYSTEM338 (variant S0) and 4 with SYSTEM338 + VARIANT_LINE (variant S1), same seed per turn, trimmed and
guarded as 338 does. Every S0 sample also gets its self-check margin. Output: one JSON line per sample (tid, variant,
k, reply, guard, margin). Blind Opus judges then flag each sample with mu-402's JUDGE-claims.md rules.

  python -B scripts/claude_mu403_pilot.py --panel-dir artifacts/claude-mu402-20260926/devchat \
      --transcript artifacts/claude-mu402-20260926/run/chat_B.jsonl --gen-model BASE --out OUT [--turns 40]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import zlib
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

VARIANT_LINE = (" Only say things about the user that they actually told you in this chat. Do not guess their "
                "feelings, plans, situation or past; if something matters and you don't know it, ask.")
KINDS = ("feelings", "advice", "followup")
N = 4


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def pick_turns(items, rows, k):
    by = {}
    for r in rows:
        by.setdefault(r["item_id"], {})[r["turn_i"]] = r["reply"]
    cands = [(it["item_id"], i) for it in items for i, t in enumerate(it["turns"]) if t["kind"] in KINDS
             and it["item_id"] in by and all(j in by[it["item_id"]] for j in range(i))]
    random.Random(4030).shuffle(cands)
    return sorted(cands[:k]), by


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel-dir", required=True)
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--gen-model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--turns", type=int, default=40)
    a = ap.parse_args()
    import torch
    import claude_chat338_agent as C38
    import claude_cre333b_agent as C333B
    import claude_mu403_ground as G
    items = {it["item_id"]: it for it in load(Path(a.panel_dir) / "items.jsonl")}
    turns, by = pick_turns(list(items.values()), load(a.transcript), a.turns)
    one_b = C333B.Gen333b(a.gen_model)
    gen = C38.Gen338(share=one_b)
    sc = G.GroundScorer(one_b)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for iid, ti in turns:
        it = items[iid]
        hist = []
        for j in range(ti):
            hist += [{"role": "user", "content": it["turns"][j]["text"]},
                     {"role": "assistant", "content": by[iid][j]}]
        hist = hist[-C38.HISTORY338:]
        text = it["turns"][ti]["text"]
        known = C38._words([text] + [h["content"] for h in hist])
        seed = (zlib.crc32(f"{iid}|{ti}".encode()) ^ 403) & 0x7FFFFFFF
        for var, system in (("S0", C38.SYSTEM338), ("S1", C38.SYSTEM338 + VARIANT_LINE)):
            msgs = [{"role": "system", "content": system}] + hist + [{"role": "user", "content": text}]
            random.seed(seed)
            torch.manual_seed(seed)
            cands = [C38.trim(c) for c in gen.sample_chat(msgs, N)]
            margins = sc.margins(msgs, cands) if var == "S0" else [None] * len(cands)
            for k, (c, m) in enumerate(zip(cands, margins)):
                rows.append({"tid": f"{iid}#{ti}", "kind": it["turns"][ti]["kind"], "variant": var, "k": k,
                             "reply": c, "guard": C38.guard(c, text, known), "margin": m})
        print(f"[mu403-pilot] {iid}#{ti}", flush=True)
        (out / "pilot_samples.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                                 encoding="utf-8")


if __name__ == "__main__":
    main()
