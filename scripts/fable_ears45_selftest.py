#!/usr/bin/env python3
"""Rung 1 of design 43 -- unit self-test, must pass before any training run.

1,000 generated sentences: tokenise -> encode -> feed the decoder ORACLE probabilities
built from the gold targets -> the decoded item must equal the gold item byte for byte,
and the unchanged validator must accept it.  This tests the tokeniser's char spans, the
pointer convention (BOS = absent), the pronoun table, the two-key relation rule and the
OPEN snake_case rule together.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_listening_english as LE          # noqa: E402
import fable_ears45_data as D                 # noqa: E402
import fable_ears45_score as S                # noqa: E402

N = 1000


def oracle(enc):
    t = enc["n"]
    P = {"act": torch.zeros(15), "items": torch.zeros(4), "flags": torch.zeros(6),
         "slot": torch.zeros(5, 2, t), "hs": torch.zeros(D.MAX_HOPS, t),
         "he": torch.zeros(D.MAX_HOPS, t), "stop": torch.zeros(D.MAX_HOPS),
         "key": torch.zeros(D.MAX_HOPS, D.N_RELKEY),
         "typ": torch.zeros(D.MAX_HOPS, 2), "n": t}
    P["act"][enc["act"]] = 1.0
    P["items"][enc["n_items"]] = 1.0
    P["flags"][:] = torch.tensor(enc["flags"], dtype=torch.float)
    for s in range(5):
        P["slot"][s, 0, enc["slot_ptr"][s][0]] = 1.0
        P["slot"][s, 1, enc["slot_ptr"][s][1]] = 1.0
    for j in range(D.MAX_HOPS):
        a, b = enc["hop_ptr"][j]
        P["hs"][j, a] = 1.0
        P["he"][j, b] = 1.0
        P["key"][j, enc["hop_key"][j]] = 1.0
        P["typ"][j, enc["hop_type"][j]] = 1.0
        P["stop"][j] = 1.0 if j >= enc["n_hops"] else 0.0
    return P


def main():
    split, pools, lex, gen = D.load_all()
    rng = random.Random(45999)
    rows = []
    for name in ("dev", "t_seen", "t_new", "t_far", "t_trap", "t_hard"):
        rows += D.make_panel(gen, name, N // 6 + 1)
    rows = rows[:N]
    bad_span, bad_item, bad_valid, dropped = [], [], [], 0
    for ex in rows:
        enc = D.encode(ex, lex, rng, False)
        if enc is None:
            dropped += 1
            continue
        toks = D.tokenise(ex["utterance"])
        for sl, sp in ex["slots"].items():
            i = D.SLOT_IDX[sl]
            a, b = enc["slot_ptr"][i]
            if S._span_text(ex["utterance"], toks, a, b) != ex["utterance"][sp[0]:sp[1]]:
                bad_span.append((ex["utterance"], sl))
        for j, sp in enumerate(ex["hops"]):
            a, b = enc["hop_ptr"][j]
            if S._span_text(ex["utterance"], toks, a, b) != ex["utterance"][sp[0]:sp[1]]:
                bad_span.append((ex["utterance"], f"hop{j}"))
        got = S.decode(ex, enc, oracle(enc))
        gold = ex["item"]
        if gold is None:
            if got["item"] is not None and got["act"] not in S.NO_ITEM_ACTS:
                bad_item.append((ex["utterance"], None, got["item"]))
        elif not S.same_item(got["item"], gold):
            bad_item.append((ex["utterance"], gold, got["item"]))
        if gold is not None:
            try:
                LE.validate_model_output(
                    {"items": [gold], "unsure": False, "unsure_reason": ""},
                    ex["utterance"], None)
            except Exception as exc:
                bad_valid.append((ex["utterance"], str(exc)))
    print(f"sentences {len(rows)}  dropped(>8 opaque) {dropped}")
    print(f"span round-trip failures : {len(bad_span)}")
    print(f"oracle-decode mismatches : {len(bad_item)}")
    print(f"validator rejections     : {len(bad_valid)}")
    for u, g, o in bad_item[:10]:
        print("  MISMATCH", repr(u))
        print("    gold", g)
        print("    got ", o)
    for u, s in bad_valid[:10]:
        print("  REJECT", repr(u), s)
    ok = not (bad_span or bad_item or bad_valid)
    print("SELFTEST", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
