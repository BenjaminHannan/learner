#!/usr/bin/env python3
"""gr-6 blind TEST panel maker (gr-5's maker with new seeds, gr6- ids and the sealed same-format check) (Plain-English
puzzles thread, 2026-09-27; PASSMARKS-gr6.md). Prints counts only, never panel text.

A fresh blind writer that saw no code, no earlier panel and no training layout wrote writings.json: 30 wrappers
({rows}, some {s}), 60 lookalikes and 40 grid format recipes (keys = claude_gr1.RECIPE_KEYS). Its file is sealed
(SEAL-writings in artifacts/claude-gr6-20260927) before this maker reads it; the maker refuses a file whose sha256 is
not the sealed one. The unseen formats are the first 20 writer formats, in the writer's order, that are complete, have
a non-empty separator, and write a row differently (claude_gr6.signature) from every one of the 48 training and dev
layouts (gr-1's 8 with their variants and the 40 drawn) and from every writer format kept before them. If fewer than
20 pass, --more (a second sealed writings file with 20 more formats) is read after the first.
  squares.jsonl     100 {"id", "text", "size", "grid", "broken", "layout", "wrapper_id"}: seeds 501004-501007 (sizes
                    4-7, 25 each), about 20% broken as in 358b3, layouts "Row k:" and bare alternating (358b3's).
  lookalikes.jsonl  60 {"id", "text", "square"}: square = what claude_puzzle_reader.read_latin reads (usually null).
  unseen.jsonl      60 {"id", "text", "size", "grid", "broken", "format_id", "wrapper_id", "token_clash", "sep_seen"}:
                    seeds 502004-502007 (15 per size), 3 per kept format; sep_seen = its cell separator is used by a
                    training layout (report only).
  writings.json, formats-kept.json, SEAL-panel.sha256.txt, README.md
Seeds used nowhere else: see claude_gr5_make_panel.py; gr-5 497004-7 / 498004-7; gr-6 training squares 503000-503319.

  HF_HUB_OFFLINE=1 python -B scripts/claude_gr6_make_panel.py --writings W.json [--more W2.json] --model BASE \
      --out artifacts/claude-panel-gr6-20260927
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_gr5_make_panel as M5  # noqa: E402
import claude_gr6 as G6  # noqa: E402

SEED_SQ, SEED_UN = 5010, 5020
SEAL_W = G6.ROOT / "artifacts/claude-gr6-20260927/SEAL-writings.sha256.txt"
N_FORMATS = 20


def _sealed(path: Path) -> None:
    want = {ln.split()[1]: ln.split()[0] for ln in SEAL_W.read_text().splitlines() if ln.strip()}
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if want.get(path.name) != got:
        raise SystemExit(f"gr6 maker: {path.name} is not the sealed writings file")


def keep_formats(fm, lay):
    import claude_gr1 as G
    taken = G6.gr1_signatures() | {G6.signature(r) for r in lay}
    kept, reasons = [], {"incomplete": 0, "same_as_training_or_dev": 0, "same_as_kept": 0}
    kept_sigs = set()
    for f in fm:
        if not (set(G.RECIPE_KEYS) <= set(f) and f["sep"] and f["header"] in ("none", "numbers", "letters")):
            reasons["incomplete"] += 1
            continue
        sg = G6.signature(f)
        if sg in taken:
            reasons["same_as_training_or_dev"] += 1
            continue
        if sg in kept_sigs:
            reasons["same_as_kept"] += 1
            continue
        kept_sigs.add(sg)
        kept.append(f)
        if len(kept) == N_FORMATS:
            break
    return kept, reasons


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--writings", required=True)
    ap.add_argument("--more", default="")
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from transformers import AutoTokenizer
    import claude_gr1 as G
    import claude_gr1_make_panel as M1
    import claude_puzzle_reader as R
    import claude_rsn358b2_bridge as B
    import claude_rsn358b3_panel as P3
    _sealed(Path(a.writings))
    w = json.loads(Path(a.writings).read_text(encoding="utf-8"))
    wr, lk, fm = w["wrappers"], w["lookalikes"], list(w["formats"])
    assert len(wr) == 30 and len(lk) == 60 and len(fm) == 40
    assert all(x.count("{rows}") == 1 and not any(ch.isdigit() for ch in x) for x in wr)
    if a.more:
        _sealed(Path(a.more))
        fm += json.loads(Path(a.more).read_text(encoding="utf-8"))["formats"]
    lay = G6.draw_layouts()
    kept, reasons = keep_formats(fm, lay)
    if len(kept) < N_FORMATS:
        print(json.dumps({"formats_written": len(fm), "formats_kept": len(kept), **reasons, "stop": "too few"}))
        raise SystemExit(4)
    seps = G6.training_seps(lay)
    tok = AutoTokenizer.from_pretrained(a.model)

    def clash(text, cells):
        head = G.ECHO_HEAD.format(text=text)
        offs = tok(head + text, return_offsets_mapping=True)["offset_mapping"]
        st = len(head)
        spans = [(max(x, st) - st, y - st) for x, y in offs if y > st and y > x]
        return G.token_tags(spans, cells)[1] > 0

    squares, mism = [], 0
    for i, (s, puz, broken) in enumerate(M5.squares_for(B, P3, SEED_SQ, 25)):
        layout, wid = ("row" if i % 2 == 0 else "bare"), i % 30
        text = wr[wid].replace("{s}", str(s)).replace("{rows}", M1.rows_text(puz, layout))
        mism += int((R.read_latin(text) or {}).get("grid") != puz)
        squares.append({"id": "gr6-sq-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken,
                        "layout": layout, "wrapper_id": wid})
    looks = []
    for i, t in enumerate(lk):
        g = R.read_latin(t)
        looks.append({"id": "gr6-lk-%03d" % i, "text": t, "square": None if g is None else g["grid"]})
    unseen, n_clash, code_un = [], 0, 0
    for i, (s, puz, broken) in enumerate(M5.squares_for(B, P3, SEED_UN, 15)):
        fid, wid = i % N_FORMATS, (i * 7) % 30
        gt, cells = G.render_recipe(puz, kept[fid])
        pre, post = wr[wid].replace("{s}", str(s)).split("{rows}")
        text = pre + gt + post
        c = clash(text, [(x + len(pre), r, cc) for x, r, cc in cells])
        n_clash += int(c)
        code_un += int((R.read_latin(text) or {}).get("grid") == puz)
        unseen.append({"id": "gr6-un-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken, "format_id": fid,
                       "wrapper_id": wid, "token_clash": c, "sep_seen": G6._norm(kept[fid]["sep"]) in seps})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seal = []
    for name, rows in (("squares.jsonl", squares), ("lookalikes.jsonl", looks), ("unseen.jsonl", unseen)):
        p = out / name
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        seal.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
    for name, obj in (("writings.json", w), ("formats-kept.json", kept)):
        p = out / name
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        seal.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
    (out / "SEAL-panel.sha256.txt").write_text("\n".join(seal) + "\n")
    info = {"squares": len(squares), "squares_broken": sum(r["broken"] for r in squares),
            "squares_code_mismatch": mism, "lookalikes": len(looks),
            "lookalikes_truth_none_R2_denominator": sum(r["square"] is None for r in looks),
            "lookalikes_with_square": sum(r["square"] is not None for r in looks),
            "formats_written": len(fm), "formats_kept": len(kept), **reasons,
            "unseen": len(unseen), "unseen_broken": sum(r["broken"] for r in unseen), "unseen_token_clash": n_clash,
            "unseen_formats_with_clash": len({r["format_id"] for r in unseen if r["token_clash"]}),
            "unseen_formats_sep_seen": len({r["format_id"] for r in unseen if r["sep_seen"]}),
            "unseen_code_standin_exact": code_un}
    (out / "README.md").write_text(
        "# gr-6 blind panel (TEST-ONLY: never trained, tuned, read or quoted)\n\nMade by scripts/claude_gr6_make_panel.py"
        " from a fresh blind writer's wrappers, lookalikes and format recipes (sealed before this maker read them). Only"
        " scripts/claude_gr6.py run and score read it.\n\nCounts: " + json.dumps(info) + "\n")
    print(json.dumps(info))


if __name__ == "__main__":
    main()
