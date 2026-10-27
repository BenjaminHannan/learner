#!/usr/bin/env python3
"""gr-8 dev post hoc, report only (written after the count): on the fresh unseen set, where are the wrong reads? By the
format's cell separator, and by whether any cell shares a tokenizer token with a neighbouring character (a "token clash",
as the panel makers define it with claude_gr1.token_tags). Practice data and the tokenizer only; no model is run.
  HF_HUB_OFFLINE=1 python3 -B artifacts/claude-gr8d-20260927/posthoc/why.py
"""
import glob
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_gr1 as G  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

D = Path(__file__).resolve().parents[1]
tok = AutoTokenizer.from_pretrained(glob.glob("/root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c*")[0])


def load(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def clash(text, cells):
    head = G.ECHO_HEAD.format(text=text)
    offs = tok(head + text, return_offsets_mapping=True)["offset_mapping"]
    st = len(head)
    spans = [(max(x, st) - st, y - st) for x, y in offs if y > st and y > x]
    return G.token_tags(spans, [tuple(c) for c in cells])[1] > 0


fm = {f["id"]: f for f in json.loads((D / "practice/formats.json").read_text())}
truth = {r["id"]: r for r in load(D / "practice/unseen.jsonl")}
st = Counter()
for r in load(D / "run/L8_unseen.jsonl"):
    t = truth[r["id"]]
    f = fm[t["format_id"]]
    c = "clash" if clash(t["text"], t["cells"]) else "noclash"
    sep = repr(f["sep"].strip() or f["sep"])
    for arm in ("greedy", "pick"):
        g = r[arm]
        res = "exact" if g == t["grid"] else ("none" if g is None else "wrong")
        st[f"{arm}_{c}_{res}"] += 1
        st[f"{arm}_sep{sep}_{res}"] += 1
        if res == "wrong" and len(g) == len(t["grid"]):
            st[f"{arm}_{c}_wrong_right_size"] += 1
            st[f"{arm}_right_size_cells_differing"] += sum(a != b for x, y in zip(g, t["grid"]) for a, b in zip(x, y))
    st[f"items_{c}"] += 1
for k, v in sorted(st.items()):
    print(k, v)


# second pass (added after reading three wrong picks): in the right-size wrong picks, what is wrong with each row that
# differs from the truth row at the same place?
def kind(row, trow, grid):
    if row in grid:
        return "another_true_row"
    d, e = [v for v in row if v], [v for v in trow if v]
    if d == e:
        return "same_digits_moved"
    if len(d) != len(e):
        return "digit_dropped_or_added"
    return "digit_changed"


st2 = Counter()
for r in load(D / "run/L8_unseen.jsonl"):
    t = truth[r["id"]]
    g = r["pick"]
    if g is None or g == t["grid"] or len(g) != len(t["grid"]):
        continue
    st2["right_size_wrong_picks"] += 1
    for row, trow in zip(g, t["grid"]):
        if row != trow:
            st2["rows_differing"] += 1
            st2["row_" + kind(row, trow, t["grid"])] += 1
print("# second pass")
for k, v in sorted(st2.items()):
    print(k, v)
