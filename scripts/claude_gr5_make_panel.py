#!/usr/bin/env python3
"""gr-5 blind TEST panel maker (gr-3's maker with new seeds and ids) (Plain-English puzzles thread, 2026-09-26). Prints counts only, never panel text.

A blind writer that saw no code and no earlier panel wrote /tmp/blind_gr5/writings.json: 30 wrappers ({rows}, some {s}),
60 lookalikes (numbers in rows, not a request to fill a Latin square), and 20 grid format recipes that are none of
gr-1's 8 practice layouts (keys = claude_gr1.RECIPE_KEYS). This script writes artifacts/claude-panel-gr5-20260926:
  squares.jsonl     100 {"id", "text", "size", "grid", "broken", "layout", "wrapper_id"}: seeds 497004-497007 (sizes
                    4-7, 25 each), about 20% broken as in 358b3, layouts "Row k:" and bare alternating (358b3's).
  lookalikes.jsonl  60 {"id", "text", "square"}: square = what claude_puzzle_reader.read_latin reads (usually null).
  unseen.jsonl      60 {"id", "text", "size", "grid", "broken", "format_id", "wrapper_id", "token_clash"}: seeds
                    498004-498007 (15 per size), 3 per format, inside the same wrappers.
  writings.json, SEAL-panel.sha256.txt, README.md
Seeds used nowhere else: gr-1 485004-7 / 486000-486359 / 487004-7 / 488004-7 / 489003-8 / 489103-7; gr-2 491004-7 / 492004-7; gr-3 selftest 489203-9; gr-3 panel 493004-7 / 494004-7; Sleep research
35900-36000, 47311, 47399.

  HF_HUB_OFFLINE=1 python -B scripts/claude_gr5_make_panel.py --writings /tmp/blind_gr5/writings.json --model BASE \
      --out artifacts/claude-panel-gr5-20260926
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SEED_SQ, SEED_UN = 4970, 4980


def squares_for(B, P3, seed, per_size):
    rng = random.Random(seed)
    out = []
    for s in (4, 5, 6, 7):
        for r in B.make_requests(seed * 100 + s, per_size, s, False):
            puz, broken = r["puz"], rng.random() < 0.2
            if broken:
                puz = P3._broken(rng, puz, s)
            out.append((s, puz, broken))
    rng.shuffle(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--writings", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from transformers import AutoTokenizer
    import claude_gr1 as G
    import claude_gr1_make_panel as M1
    import claude_puzzle_reader as R
    import claude_rsn358b2_bridge as B
    import claude_rsn358b3_panel as P3
    w = json.loads(Path(a.writings).read_text(encoding="utf-8"))
    wr, lk, fm = w["wrappers"], w["lookalikes"], w["formats"]
    assert len(wr) == 30 and len(lk) == 60 and len(fm) == 20
    assert all(x.count("{rows}") == 1 and not any(ch.isdigit() for ch in x) for x in wr)
    assert all(set(G.RECIPE_KEYS) <= set(f) and f["sep"] for f in fm)
    tok = AutoTokenizer.from_pretrained(a.model)

    def clash(text, cells):
        head = G.ECHO_HEAD.format(text=text)
        offs = tok(head + text, return_offsets_mapping=True)["offset_mapping"]
        st = len(head)
        spans = [(max(x, st) - st, y - st) for x, y in offs if y > st and y > x]
        return G.token_tags(spans, cells)[1] > 0

    squares, mism = [], 0
    for i, (s, puz, broken) in enumerate(squares_for(B, P3, SEED_SQ, 25)):
        layout, wid = ("row" if i % 2 == 0 else "bare"), i % 30
        text = wr[wid].replace("{s}", str(s)).replace("{rows}", M1.rows_text(puz, layout))
        mism += int((R.read_latin(text) or {}).get("grid") != puz)
        squares.append({"id": "gr5-sq-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken,
                        "layout": layout, "wrapper_id": wid})
    looks = []
    for i, t in enumerate(lk):
        g = R.read_latin(t)
        looks.append({"id": "gr5-lk-%03d" % i, "text": t, "square": None if g is None else g["grid"]})
    unseen, n_clash, code_un = [], 0, 0
    for i, (s, puz, broken) in enumerate(squares_for(B, P3, SEED_UN, 15)):
        fid, wid = i % 20, (i * 7) % 30
        gt, cells = G.render_recipe(puz, fm[fid])
        pre, post = wr[wid].replace("{s}", str(s)).split("{rows}")
        text = pre + gt + post
        c = clash(text, [(x + len(pre), r, cc) for x, r, cc in cells])
        n_clash += int(c)
        code_un += int((R.read_latin(text) or {}).get("grid") == puz)
        unseen.append({"id": "gr5-un-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken, "format_id": fid,
                       "wrapper_id": wid, "token_clash": c})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seal = []
    for name, rows in (("squares.jsonl", squares), ("lookalikes.jsonl", looks), ("unseen.jsonl", unseen)):
        p = out / name
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        seal.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
    wj = out / "writings.json"
    wj.write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    seal.append(f"{hashlib.sha256(wj.read_bytes()).hexdigest()}  writings.json")
    (out / "SEAL-panel.sha256.txt").write_text("\n".join(seal) + "\n")
    info = {"squares": len(squares), "squares_broken": sum(r["broken"] for r in squares),
            "squares_code_mismatch": mism, "lookalikes": len(looks),
            "lookalikes_with_square": sum(r["square"] is not None for r in looks),
            "unseen": len(unseen), "unseen_broken": sum(r["broken"] for r in unseen), "unseen_token_clash": n_clash,
            "unseen_formats_with_clash": len({r["format_id"] for r in unseen if r["token_clash"]}),
            "unseen_code_standin_exact": code_un}
    (out / "README.md").write_text(
        "# gr-5 blind panel (TEST-ONLY: never trained, tuned, read or quoted)\n\nMade by scripts/claude_gr5_make_panel.py"
        " from a blind writer's wrappers, lookalikes and format recipes. Only scripts/claude_gr5.py run and score read"
        " it.\n\nCounts: " + json.dumps(info) + "\n")
    print(json.dumps(info))


if __name__ == "__main__":
    main()
