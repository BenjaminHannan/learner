#!/usr/bin/env python3
"""gr-1U blind TEST panel maker (Plain-English puzzles thread, 2026-09-26; ADDENDUM-gr1-1). Prints counts only.

A blind writer that saw no code was told gr-1's 8 practice layouts and wrote 20 grid format recipes that are none of
them (/tmp/blind_gr1u/formats.json; the recipe keys are claude_gr1.RECIPE_KEYS). This script puts 3 fresh squares in
each format (claude_gr1.render_recipe) and places each inside one of gr-1's sealed blind wrappers
(artifacts/claude-panel-gr1-20260926/writings.json), giving 60 messages:
  unseen.jsonl  {"id", "text", "size", "grid", "broken", "format_id", "wrapper_id", "token_clash"}
  SEAL-panel.sha256.txt, formats.json, README.md
Squares: claude_rsn358b2_bridge.make_requests seeds 488004-488007 (sizes 4-7, 15 each; no other gr-1 seed), about 20%
broken as in 358b3. token_clash marks a message where two cells fall in one token of the 1B's tokenizer (in the echo
prompt), so a per-token reader cannot read it exactly; those are kept and counted.

  HF_HUB_OFFLINE=1 python -B scripts/claude_gr1u_make_panel.py --formats /tmp/blind_gr1u/formats.json \
      --wrappers artifacts/claude-panel-gr1-20260926/writings.json --model BASE --out artifacts/claude-panel-gr1u-20260926
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

SEED = 4880


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--formats", required=True)
    ap.add_argument("--wrappers", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from transformers import AutoTokenizer
    import claude_gr1 as G
    import claude_puzzle_reader as R
    import claude_rsn358b2_bridge as B
    import claude_rsn358b3_panel as P3
    fm = json.loads(Path(a.formats).read_text(encoding="utf-8"))
    fmts = fm["formats"]
    assert len(fmts) == 20 and all(set(G.RECIPE_KEYS) <= set(f) and f["sep"] for f in fmts)
    wr = json.loads(Path(a.wrappers).read_text(encoding="utf-8"))["wrappers"]
    assert len(wr) == 30
    tok = AutoTokenizer.from_pretrained(a.model)
    rng = random.Random(SEED)
    sq = []
    for s in (4, 5, 6, 7):
        for r in B.make_requests(SEED * 100 + s, 15, s, False):
            puz, broken = r["puz"], rng.random() < 0.2
            if broken:
                puz = P3._broken(rng, puz, s)
            sq.append((s, puz, broken))
    rng.shuffle(sq)
    rows, clash_n, code_read = [], 0, 0
    for i, (s, puz, broken) in enumerate(sq):
        fid, wid = i % 20, (i * 7) % 30
        grid_text, cells = G.render_recipe(puz, fmts[fid])
        pre, post = wr[wid].replace("{s}", str(s)).split("{rows}")
        text = pre + grid_text + post
        cells = [(c + len(pre), r, cc) for c, r, cc in cells]
        head = G.ECHO_HEAD.format(text=text)
        offs = tok(head + text, return_offsets_mapping=True)["offset_mapping"]
        start = len(head)
        spans = [(max(x, start) - start, y - start) for x, y in offs if y > start and y > x]
        clash = G.token_tags(spans, cells)[1] > 0
        clash_n += int(clash)
        code_read += int((R.read_latin(text) or {}).get("grid") == puz)
        rows.append({"id": "gr1u-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken, "format_id": fid,
                     "wrapper_id": wid, "token_clash": clash})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    p = out / "unseen.jsonl"
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    fj = out / "formats.json"
    fj.write_text(json.dumps(fm, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "SEAL-panel.sha256.txt").write_text(
        "".join(f"{hashlib.sha256(x.read_bytes()).hexdigest()}  {x.name}\n" for x in (p, fj)))
    info = {"messages": len(rows), "formats": len(fmts), "broken": sum(r["broken"] for r in rows),
            "by_size": {s: sum(r["size"] == s for r in rows) for s in (4, 5, 6, 7)},
            "token_clash_messages": clash_n, "formats_with_clash": len({r["format_id"] for r in rows if r["token_clash"]}),
            "code_standin_exact": code_read}
    (out / "README.md").write_text(
        "# gr-1U blind panel (TEST-ONLY: never trained, tuned, read or quoted)\n\nMade by scripts/claude_gr1u_make_panel.py"
        " from a blind writer's 20 format recipes and gr-1's sealed blind wrappers. Only scripts/claude_gr1.py run"
        " (--task unseen) and scoreu read it.\n\nCounts: " + json.dumps(info) + "\n")
    print(json.dumps(info))


if __name__ == "__main__":
    main()
