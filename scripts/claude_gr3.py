#!/usr/bin/env python3
"""gr-3: a learned glance says the grid's size, or "no square", before the cells are read (Plain-English puzzles,
2026-09-26).

gr-2 (registered FAIL on R2 and U2, artifacts/claude-gr2-20260926/VERIFY-gr2.md) read 100 of 100 squares and 50 of 60 in
new formats by searching every size 3-9 for the most probable square. It also found squares in 3 of 55 lookalikes and
read 7 new-format squares at the wrong size. Nothing learned said how big the block is, or whether it is a square.
Brain first: a person takes in the block at a glance ("a 5 by 5 grid", "a price list") and then reads the cells in that
frame. The one change: a small learned head (multinomial logistic regression on the mean hidden state of the echoed
message's second copy, one layer) says none or a size 3-9. When it says none, the reading is none. When it says s, the
same search as gr-2 (disclosed hand-written scaffolding, ADDENDUM-gr2-1) runs at that size only, still against the
tagging with no cells. The per-token head is gr-1's sealed head, unchanged.

Training for the glance: gr-1's 860 practice messages (code labels) and the 1B's own number-table messages
(claude_gr3_drafts.py; label = the size read_latin finds, usually none). The layer and L2 are picked by 5-fold CV
accuracy of the size label.

  python -B scripts/claude_gr3.py --selftest
  python -B scripts/claude_gr3.py feats --model BASE --tables TABLES.jsonl --gr1-feats FEATS.pt --out G3FEATS.pt
  python -B scripts/claude_gr3.py fit --feats G3FEATS.pt --head SIZEHEAD.pt
  python -B scripts/claude_gr3.py dev --model BASE --head SIZEHEAD.pt          (dev data only; report)
  python -B scripts/claude_gr3.py run --task squares|lookalikes|unseen|general --model BASE --head SIZEHEAD.pt --panel-dir PD --out OUT
  python -B scripts/claude_gr3.py score --out OUT --panel-dir PD --score SCOREDIR
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_gr1 as G1  # noqa: E402
import claude_gr2 as G2  # noqa: E402

ROOT = SCRIPTS.parent
TOK_HEAD = ROOT / "artifacts/claude-gr1-20260926/head.pt"     # gr-1's sealed per-token head (d5bf293ce)
CLASSES = [None, 3, 4, 5, 6, 7, 8, 9]
NEG = float("-inf")


def label_of(grid):
    return 0 if grid is None else CLASSES.index(len(grid))


def pooled(H):
    """[n_tokens, n_layers, d] -> [n_layers, d]: the mean hidden state of the second copy at each layer"""
    return H.float().mean(0)


def decode_at(text, spans, logp, s):
    """gr-2's search (claude_gr2.joint_decode) at one size s: the most probable s x s tagging, or None when the tagging
    with no cells is more probable. Same code as gr-2 restricted to one s (disclosed scaffolding, ADDENDUM-gr2-1)."""
    vals = G2.cell_values(text, spans)
    n, N = len(spans), s * s
    none_score = sum(lp[0] for lp in logp)
    score = [0.0] + [NEG] * N
    back = [[None] * (N + 1) for _ in range(n)]
    for t in range(n):
        new = [NEG] * (N + 1)
        bt, v = back[t], vals[t]
        for j in range(N + 1):
            if score[j] == NEG:
                continue
            o = score[j] + logp[t][0]
            if o > new[j]:
                new[j], bt[j] = o, (j, 0)
            if v is not None and v <= s and j < N:
                tag = 1 if j % s == 0 else 2
                c = score[j] + logp[t][tag]
                if c > new[j + 1]:
                    new[j + 1], bt[j + 1] = c, (j, tag)
        score = new
    if score[N] <= none_score:
        return None
    tags, j = [0] * n, N
    for t in range(n - 1, -1, -1):
        pj, tag = back[t][j]
        tags[t], j = tag, pj
    return G1.decode(text, spans, tags)


def size_of(size_head, H):
    import torch
    x = pooled(H)[size_head["layer_index"]]
    return CLASSES[int((((x - size_head["mu"]) / size_head["sd"]) @ size_head["W"] + size_head["b"]).argmax())]


def read_all(size_head, tok_head, text, H, spans):
    """(gr-3 reading, gr-2 reading, gr-1 per-token reading) from one forward pass"""
    logp = G2.logprobs(tok_head, H)
    s = size_of(size_head, H)
    g3 = None if s is None else decode_at(text, spans, logp, s)
    return g3, G2.joint_decode(text, spans, logp), G1.decode(text, spans, G1.predict(tok_head, H))


# ------------------------------------------------------------------ features and fit
def feats(a) -> None:
    import torch
    import claude_rt02g as G
    d = torch.load(a.gr1_feats)
    X = [pooled(H) for H in d["H"]]
    y = [label_of(m["grid"]) for m in d["meta"]]
    src = ["gr1_" + m["kind"] for m in d["meta"]]
    tabs = [json.loads(x) for x in Path(a.tables).read_text().splitlines()]
    tabs = [r for r in tabs if r["keep"]]
    one_b = G.load_one_b(a.model)
    tab_meta = []
    for r in tabs:
        H, spans = G1.encode(one_b, r["text"])
        X.append(pooled(H))
        y.append(0 if r["size"] is None else CLASSES.index(r["size"]))
        src.append("table")
        tab_meta.append({"text": r["text"], "spans": spans, "H": H, "size": r["size"]})
    torch.save({"X": torch.stack(X), "y": torch.tensor(y), "src": src, "tables": tab_meta}, a.out)
    print(json.dumps({"n": len(y), "by_label": dict(Counter(y)), "tables": len(tab_meta),
                      "tables_with_square": sum(r["size"] is not None for r in tabs)}))


def _fit(X, y, l2, steps=300):
    import torch
    mu, sd = X.mean(0), X.std(0) + 1e-4
    Z = (X - mu) / sd
    W = torch.zeros(Z.shape[1], len(CLASSES), requires_grad=True)
    b = torch.zeros(len(CLASSES), requires_grad=True)
    opt = torch.optim.LBFGS([W, b], max_iter=steps, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(Z @ W + b, y) + l2 * (W * W).sum()
        loss.backward()
        return loss
    opt.step(closure)
    return {"mu": mu, "sd": sd, "W": W.detach().clone(), "b": b.detach().clone()}


def fit(a) -> None:
    import torch
    d = torch.load(a.feats)
    X, y, src = d["X"], d["y"], d["src"]
    n = len(y)
    fold = [i % 5 for i in range(n)]
    best = None
    for li, layer in enumerate(G1.LAYERS):
        for l2 in (1e-3, 1e-2, 1e-1):
            pred = torch.zeros(n, dtype=torch.long)
            for f in range(5):
                tr = [i for i in range(n) if fold[i] != f]
                te = [i for i in range(n) if fold[i] == f]
                h = _fit(X[tr, li], y[tr], l2)
                pred[te] = (((X[te, li] - h["mu"]) / h["sd"]) @ h["W"] + h["b"]).argmax(1)
            ok = int((pred == y).sum())
            false_sq = int(((y == 0) & (pred != 0)).sum())
            missed = int(((y != 0) & (pred == 0)).sum())
            print(f"layer {layer} l2 {l2:g}: cv size right {ok}/{n}, none->square {false_sq}, square->none {missed}",
                  flush=True)
            if best is None or ok > best[0]:
                best = (ok, li, l2, pred.clone())
    ok, li, l2, pred = best
    by = Counter()
    for i in range(n):
        by[src[i] + "_n"] += 1
        by[src[i] + "_right"] += int(pred[i] == y[i])
    head = {**_fit(X[:, li], y, l2), "layer_index": li, "layer": G1.LAYERS[li], "l2": l2, "cv_right": ok, "n": n}
    torch.save(head, a.head)
    print(json.dumps({"layer": G1.LAYERS[li], "l2": l2, "cv_right": ok, "n": n, "cv_by_source": dict(sorted(by.items()))}))


# ------------------------------------------------------------------ dev (dev data only; report)
def dev(a) -> None:
    import claude_blurt2 as B2
    import claude_rsn358b2_bridge as B
    import claude_rt02d as RT
    import claude_rt02g as G
    import torch
    one_b = G.load_one_b(a.model)
    sh, th = torch.load(a.head), torch.load(TOK_HEAD)
    items = []
    sm = ROOT / "artifacts/claude-panel-rsn358b3-smoke-20260926"
    ans = {r["id"]: r for r in map(json.loads, (sm / "answers.jsonl").read_text().splitlines())}
    items += [("smoke", r["message"], ans[r["id"]]["puz"]) for r in map(json.loads, (sm / "panel.jsonl").read_text()
                                                                         .splitlines())]
    for s in (4, 5, 6, 7):
        items += [("fresh", q["text"], q["puz"]) for q in B.make_requests(487000 + s, 6, s, False)]
    prac = json.loads((ROOT / "artifacts/claude-rt02e-20260926/practice/wordings_practice.json").read_text())
    ps = B2.puzzles(4881, len(prac["puzzle_templates"]))
    texts = [t for t, _ in RT.dev_cases()]
    texts += [t.replace("{L}", ", ".join(map(str, p["nums"]))).replace("{T}", str(p["target"]))
              for t, p in zip(prac["puzzle_templates"], ps)] + prac["negatives"]
    items += [("nosquare", t, None) for t in texts]
    st = Counter()
    for kind, text, truth in items:
        H, spans = G1.encode(one_b, text)
        for arm, g in zip(("gr3", "gr2", "gr1"), read_all(sh, th, text, H, spans)):
            st[f"{kind}_{arm}_exact"] += int(g == truth)
            st[f"{kind}_{arm}_wrong"] += int(g is not None and g != truth)
        st[kind + "_n"] += 1
    print(json.dumps(dict(sorted(st.items()))))


# ------------------------------------------------------------------ registered run and score
def _load(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def run(a) -> None:
    import claude_dl1_nights as D1
    import claude_rt02g as G
    import torch
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"L_{a.task}.jsonl"
    if path.exists():
        raise SystemExit(f"gr3: {path} exists (each run is launched once)")
    if a.task == "general":
        items = [{"id": "gen-%03d" % i, "text": it["q"]} for i, it in enumerate(D1.harm_panel())]
    else:
        items = _load(Path(a.panel_dir) / f"{a.task}.jsonl")
    sh, th = torch.load(a.head), torch.load(TOK_HEAD)
    one_b = G.load_one_b(a.model)
    rows = []
    for it in items:
        t0 = time.time()
        H, spans = G1.encode(one_b, it["text"])
        g3, g2, g1 = read_all(sh, th, it["text"], H, spans)
        rows.append({"id": it["id"], "grid": g3, "grid_gr2": g2, "grid_pertoken": g1, "size_said": size_of(sh, H),
                     "ms": round((time.time() - t0) * 1000, 1)})
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"task": a.task, "rows": len(rows), "read_as_square": sum(r["grid"] is not None for r in rows)}))


def score(a) -> None:
    import claude_dl1_nights as D1
    import claude_puzzle_reader as R
    out, pd = Path(a.out), Path(a.panel_dir)
    panel = {t: _load(pd / f"{t}.jsonl") for t in ("squares", "lookalikes", "unseen")}
    got = {t: {r["id"]: r for r in _load(out / f"L_{t}.jsonl")} for t in ("squares", "lookalikes", "unseen", "general")}
    for t in ("squares", "lookalikes", "unseen"):
        assert set(got[t]) == {r["id"] for r in panel[t]}
    assert len(got["general"]) == 300
    field = {"L": "grid", "G2": "grid_gr2", "P": "grid_pertoken"}
    gen_code = sum(int(R.read_latin(it["q"]) is not None) for it in D1.harm_panel())
    res = {}
    for arm in ("L", "G2", "P", "C"):
        rd = (lambda t, r: (R.read_latin(r["text"]) or {}).get("grid")) if arm == "C" else \
             (lambda t, r, f=field[arm]: got[t][r["id"]][f])
        x = {}
        for t in ("squares", "unseen"):
            g = {r["id"]: rd(t, r) for r in panel[t]}
            x[t + "_exact"] = sum(int(g[r["id"]] == r["grid"]) for r in panel[t])
            x[t + "_wrong"] = sum(int(g[r["id"]] is not None and g[r["id"]] != r["grid"]) for r in panel[t])
            x[t + "_none"] = sum(int(g[r["id"]] is None) for r in panel[t])
            by = Counter()
            for r in panel[t]:
                e = int(g[r["id"]] == r["grid"])
                by[f"size{r['size']}"] += e
                by["broken" if r["broken"] else "whole"] += e
                by[f"layout_{r['layout']}" if t == "squares" else f"format_{r['format_id']:02d}"] += e
            x[t + "_exact_by"] = dict(sorted(by.items()))
        x["lookalikes_false_square"] = sum(int(r["square"] is None and rd("lookalikes", r) is not None)
                                           for r in panel["lookalikes"])
        x["general_read_as_square"] = (gen_code if arm == "C" else
                                       sum(int(r[field[arm]] is not None) for r in got["general"].values()))
        res[arm] = x
    L = res["L"]
    res["size_said_right_squares"] = sum(int(got["squares"][r["id"]]["size_said"] == r["size"]) for r in panel["squares"])
    res["size_said_right_unseen"] = sum(int(got["unseen"][r["id"]]["size_said"] == r["size"]) for r in panel["unseen"])
    res["size_said_none_lookalikes_truth_none"] = sum(int(got["lookalikes"][r["id"]]["size_said"] is None)
                                                      for r in panel["lookalikes"] if r["square"] is None)
    res["lookalikes_truth_square"] = sum(int(r["square"] is not None) for r in panel["lookalikes"])
    res["unseen_token_clash"] = sum(int(r["token_clash"]) for r in panel["unseen"])
    res["ms_median"] = sorted(r["ms"] for r in got["general"].values())[150]
    res["marks"] = {"R1": L["squares_exact"] >= 97, "R2": L["lookalikes_false_square"] <= 1,
                    "R3": L["squares_wrong"] <= 1, "R4": L["general_read_as_square"] == 0,
                    "U1": L["unseen_exact"] >= 48, "U2": L["unseen_wrong"] <= 2}
    res["gr3_pass"] = all(res["marks"][k] for k in ("R1", "R2", "R3", "R4"))
    res["gr3U_pass"] = res["marks"]["U1"] and res["marks"]["U2"]
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "gr3_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if not kk.endswith("_by")} if k in ("L", "G2", "P", "C")
                          else v) for k, v in res.items()}))


def selftest() -> None:
    import math
    import claude_rsn358b2_bridge as B
    n = 0
    L = math.log
    for layout in G1.LAYOUTS:
        for s in (3, 5, 7):
            puz = B.make_requests(489200 + s, 1, s, False)[0]["puz"]
            txt, cells = G1.render(puz, layout, s)
            text = "Please fill this in.\n" + txt
            cells = [(c + 21, r, cc) for c, r, cc in cells]
            spans = [(i, i + 1) for i in range(len(text))]
            tags, _ = G1.token_tags(spans, cells)
            lp = [[L(0.9) if k == t else L(0.05) for k in range(3)] for t in tags]
            assert decode_at(text, spans, lp, s) == puz
            assert decode_at(text, spans, lp, s + 1 if s < 9 else s - 1) != puz          # the wrong size cannot read it
            assert decode_at(text, spans, lp, s) == G2.joint_decode(text, spans, lp)      # same as gr-2 at the right size
            n += 1
    assert [label_of(None), label_of([[1] * 5] * 5)] == [0, 3]
    n += 1
    print(f"gr3 selftest {n}/{n}")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["feats", "fit", "dev", "run", "score"])
    for k in ("model", "tables", "gr1-feats", "out", "feats", "head", "task", "panel-dir", "score"):
        ap.add_argument("--" + k, default="")
    a = ap.parse_args()
    {"feats": feats, "fit": fit, "dev": dev, "run": run, "score": score}[a.cmd](a)


if __name__ == "__main__":
    main()
