#!/usr/bin/env python3
"""gr-2: the learned grid reader reads the grid as a whole (Plain-English puzzles thread, 2026-09-26).

gr-1 (registered FAIL, artifacts/claude-gr1-20260926/VERIFY-gr1.md) tags each token of the echoed message O / B / I on
its own and rejects the reading unless it forms a square; one slipped token loses the whole grid. Brain first: a person
reads a grid as a whole, expecting every row to have the same number of cells and looking again at a short row. The one
change here: the same head, with the same features and the same sealed weights (artifacts/claude-gr1-20260926/head.pt),
gives each token its probabilities, and code finds the most probable tagging among (a) every tagging that forms an
s x s square (3 <= s <= 9, values 1..s or blank, not all blank) and (b) the tagging with no cells at all. No threshold.

  python -B scripts/claude_gr2.py --selftest
  python -B scripts/claude_gr2.py cv --feats FEATS.pt                  (practice CV with gr-1's folds; report)
  python -B scripts/claude_gr2.py dev --model BASE --head HEAD.pt       (dev data only; report)
  python -B scripts/claude_gr2.py run --task squares|lookalikes|unseen|general --model BASE --head HEAD.pt --panel-dir PD --out OUT
  python -B scripts/claude_gr2.py score --out OUT --panel-dir PD --score SCOREDIR
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

NEG = float("-inf")


def cell_values(text, spans):
    """each token's cell value (0 = blank) if it holds exactly one digit or "_", else None"""
    out = []
    for a, b in spans:
        m = G1._CELL.findall(text[a:b])
        out.append(None if len(m) != 1 else (0 if m[0] == "_" else int(m[0])))
    return out


def joint_decode(text, spans, logp):
    """logp: [n][3] log-probabilities of O, B, I. Returns the grid of the most probable tagging that is a square, or
    None when the tagging with no cells is more probable (or no square is possible)."""
    vals = cell_values(text, spans)
    n = len(spans)
    none_score = sum(lp[0] for lp in logp)
    best = (none_score, None)
    for s in range(3, 10):
        N = s * s
        score = [0.0] + [NEG] * N                      # score[j] = best path with j cells placed so far
        back = [[None] * (N + 1) for _ in range(n)]    # back[t][j] = (previous j, tag) at token t
        for t in range(n):
            new = [NEG] * (N + 1)
            bt = back[t]
            v = vals[t]
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
        if score[N] <= best[0]:
            continue
        tags, j = [0] * n, N                           # walk back
        for t in range(n - 1, -1, -1):
            pj, tag = back[t][j]
            tags[t], j = tag, pj
        grid = G1.decode(text, spans, tags)
        if grid is not None:
            best = (score[N], grid)
    return best[1]


def logprobs(head, H):
    import torch
    x = H[:, head["layer_index"]].float()
    return torch.log_softmax(((x - head["mu"]) / head["sd"]) @ head["W"] + head["b"], dim=1).tolist()


def read_grid(one_b, head, text):
    H, spans = G1.encode(one_b, text)
    return joint_decode(text, spans, logprobs(head, H))


def cv(a) -> None:
    """gr-1's 5-fold CV over the practice messages, layer and L2 as sealed; each held-out message read both ways"""
    import torch
    d = torch.load(a.feats)
    Hs, T, meta = d["H"], d["T"], d["meta"]
    n = len(meta)
    fold = [i % 5 for i in range(n)]
    li, l2 = 0, 1e-3                                   # gr-1's pick: layer 8 (index 0), L2 0.001
    st = Counter()
    for f in range(5):
        tr = [i for i in range(n) if fold[i] != f]
        h = {**G1._fit(torch.cat([Hs[i][:, li].float() for i in tr]), torch.cat([T[i] for i in tr]), l2),
             "layer_index": li}
        for i in (i for i in range(n) if fold[i] == f):
            m = meta[i]
            g1 = G1.decode(m["text"], m["spans"], G1.predict(h, Hs[i]))
            g2 = joint_decode(m["text"], m["spans"], logprobs(h, Hs[i]))
            k = "square" if m["grid"] is not None else "nosquare"
            st[k + "_n"] += 1
            for arm, g in (("gr1", g1), ("gr2", g2)):
                st[f"{k}_{arm}_exact"] += int(g == m["grid"])
                st[f"{k}_{arm}_wrong"] += int(g is not None and g != m["grid"])
    print(json.dumps(dict(sorted(st.items()))))


def dev(a) -> None:
    """the dev sets of claude_gr1.dev, read by gr-1 (per token) and gr-2 (whole grid) from one forward pass each"""
    import claude_blurt2 as B2
    import claude_rsn358b2_bridge as B
    import claude_rt02d as RT
    import claude_rt02g as G
    import torch
    one_b = G.load_one_b(a.model)
    head = torch.load(a.head)
    root = SCRIPTS.parent
    items = []
    sm = root / "artifacts/claude-panel-rsn358b3-smoke-20260926"
    ans = {r["id"]: r for r in map(json.loads, (sm / "answers.jsonl").read_text().splitlines())}
    items += [("smoke", r["message"], ans[r["id"]]["puz"]) for r in map(json.loads, (sm / "panel.jsonl").read_text()
                                                                         .splitlines())]
    for s in (4, 5, 6, 7):
        items += [("fresh", q["text"], q["puz"]) for q in B.make_requests(487000 + s, 6, s, False)]
    prac = json.loads((root / "artifacts/claude-rt02e-20260926/practice/wordings_practice.json").read_text())
    ps = B2.puzzles(4881, len(prac["puzzle_templates"]))
    texts = [t for t, _ in RT.dev_cases()]
    texts += [t.replace("{L}", ", ".join(map(str, p["nums"]))).replace("{T}", str(p["target"]))
              for t, p in zip(prac["puzzle_templates"], ps)] + prac["negatives"]
    items += [("nosquare", t, None) for t in texts]
    st = Counter()
    t0 = time.time()
    for kind, text, truth in items:
        H, spans = G1.encode(one_b, text)
        g1 = G1.decode(text, spans, G1.predict(head, H))
        g2 = joint_decode(text, spans, logprobs(head, H))
        st[kind + "_n"] += 1
        for arm, g in (("gr1", g1), ("gr2", g2)):
            st[f"{kind}_{arm}_exact"] += int(g == truth)
            st[f"{kind}_{arm}_wrong"] += int(g is not None and g != truth)
    st["seconds"] = round(time.time() - t0)
    print(json.dumps(dict(sorted(st.items()))))


def _load(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def run(a) -> None:
    """one forward pass per message; L = whole-grid reading (gr-2), P = gr-1's per-token reading (report only)"""
    import claude_dl1_nights as D1
    import claude_rt02g as G
    import torch
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"L_{a.task}.jsonl"
    if path.exists():
        raise SystemExit(f"gr2: {path} exists (each run is launched once)")
    if a.task == "general":
        items = [{"id": "gen-%03d" % i, "text": it["q"]} for i, it in enumerate(D1.harm_panel())]
    else:
        items = _load(Path(a.panel_dir) / f"{a.task}.jsonl")
    head = torch.load(a.head)
    one_b = G.load_one_b(a.model)
    rows = []
    for it in items:
        t0 = time.time()
        H, spans = G1.encode(one_b, it["text"])
        g2 = joint_decode(it["text"], spans, logprobs(head, H))
        rows.append({"id": it["id"], "grid": g2, "grid_pertoken": G1.decode(it["text"], spans, G1.predict(head, H)),
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
    code = lambda r: (R.read_latin(r["text"]) or {}).get("grid")
    arms = {"L": lambda t, r: got[t][r["id"]]["grid"], "P": lambda t, r: got[t][r["id"]]["grid_pertoken"],
            "C": lambda t, r: code(r)}
    gen_code = sum(int(R.read_latin(it["q"]) is not None) for it in D1.harm_panel())
    res = {}
    for arm, rd in arms.items():
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
        x["unseen_exact_without_token_clash"] = sum(int(rd("unseen", r) == r["grid"]) for r in panel["unseen"]
                                                    if not r["token_clash"])
        x["lookalikes_false_square"] = sum(int(r["square"] is None and rd("lookalikes", r) is not None)
                                           for r in panel["lookalikes"])
        x["general_read_as_square"] = (gen_code if arm == "C" else
                                       sum(int(r["grid" if arm == "L" else "grid_pertoken"] is not None)
                                           for r in got["general"].values()))
        res[arm] = x
    L = res["L"]
    res["lookalikes_truth_square"] = sum(int(r["square"] is not None) for r in panel["lookalikes"])
    res["unseen_token_clash"] = sum(int(r["token_clash"]) for r in panel["unseen"])
    res["ms_median"] = sorted(r["ms"] for r in got["general"].values())[150]
    res["marks"] = {"R1": L["squares_exact"] >= 97, "R2": L["lookalikes_false_square"] <= 1,
                    "R3": L["squares_wrong"] <= 1, "R4": L["general_read_as_square"] == 0,
                    "U1": L["unseen_exact"] >= 48, "U2": L["unseen_wrong"] <= 2}
    res["gr2_pass"] = all(res["marks"][k] for k in ("R1", "R2", "R3", "R4"))
    res["gr2U_pass"] = res["marks"]["U1"] and res["marks"]["U2"]
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "gr2_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if not kk.endswith("_by")} if k in ("L", "P", "C") else v)
                      for k, v in res.items()}))


def selftest() -> None:
    import math
    import claude_rsn358b2_bridge as B
    n = 0
    L = math.log
    for layout in G1.LAYOUTS:
        for s in (3, 5, 7):
            puz = B.make_requests(489100 + s, 1, s, False)[0]["puz"]
            txt, cells = G1.render(puz, layout, s)
            text = "Please fill this in.\n" + txt
            cells = [(c + 21, r, cc) for c, r, cc in cells]
            spans = [(i, i + 1) for i in range(len(text))]
            tags, _ = G1.token_tags(spans, cells)
            # a confident head, then one slipped cell (its true tag given only 0.3): per-token argmax fails, joint wins
            lp = [[L(0.9) if k == t else L(0.05) for k in range(3)] for t in tags]
            assert joint_decode(text, spans, lp) == puz
            slip = next(i for i, t in enumerate(tags) if t == 2)
            lp[slip] = [L(0.4), L(0.3), L(0.3)]
            assert G1.decode(text, spans, [max(range(3), key=lambda k: x[k]) for x in lp]) is None
            assert joint_decode(text, spans, lp) == puz, (layout, s)
            n += 1
    text = "call me at 5 or 6 today"
    spans = [(i, i + 1) for i in range(len(text))]
    assert joint_decode(text, spans, [[math.log(0.8), math.log(0.1), math.log(0.1)]] * len(text)) is None
    n += 1
    print(f"gr2 selftest {n}/{n}")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cv", "dev", "run", "score"])
    for k in ("feats", "model", "head", "task", "panel-dir", "out", "score"):
        ap.add_argument("--" + k, default="")
    a = ap.parse_args()
    {"cv": cv, "dev": dev, "run": run, "score": score}[a.cmd](a)


if __name__ == "__main__":
    main()
