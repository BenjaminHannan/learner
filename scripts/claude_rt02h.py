#!/usr/bin/env python3
"""rt-02h registered run and score (Plain-English puzzles thread, 2026-09-26). New file only.

Marks: artifacts/claude-rt02h-20260926/PASSMARKS-rt02h.md (sealed before any head was trained). Blind TEST-ONLY panel:
artifacts/claude-panel-rt02g-20260926. Only `run` and `score` read it. They print counts only, never panel text.

Arm H, at reading level: a message with 4-5 whole numbers goes to the learned head. The head reads the plain 1B's
hidden state for claude_rt02h_probe.ASK (every LoRA scale 0) and decides. If its score reaches the head's cut, the 1B
copies the numbers and target (claude_puzzle_reader.copy_arith), and code accepts the copy only if it matches the
message's whole numbers exactly. Arms D (rt-02d parse_puzzle) and E (rt-02e fires) are code, computed in `score`.

  python -B scripts/claude_rt02h.py --selftest --head HEAD.pt
  python -B scripts/claude_rt02h.py run --task puzzles|negatives --model BASE --head HEAD.pt --panel-dir PD --out OUT
  python -B scripts/claude_rt02h.py score --out OUT --panel-dir PD --score SCOREDIR
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


def _load(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def decide_and_copy(one_b, head, text: str) -> dict:
    import claude_puzzle_reader as R
    import claude_rt02g as G
    import claude_rt02h_probe as PR
    if not G.pre_gate(text):
        return {"gate": False, "score": None, "yes": False, "parsed": None}
    sc = PR.head_score(head, PR.features(one_b, text))
    yes = sc >= head["cut"]
    got = R.copy_arith(one_b, text) if yes else None
    parsed = {"nums": got["nums"], "target": got["target"]} if got else None
    return {"gate": True, "score": round(sc, 4), "yes": bool(yes), "parsed": parsed}


def run(a) -> None:
    import torch
    import claude_rt02g as G
    import claude_rt02h_probe as PR
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"H_{a.task}.jsonl"
    if path.exists():
        raise SystemExit(f"rt02h: {path} exists (each run is launched once)")
    items = _load(Path(a.panel_dir) / {"puzzles": "chat_puzzles.jsonl", "negatives": "negatives.jsonl"}[a.task])
    head = PR.load_head(a.head)
    one_b = G.load_one_b(a.model)
    torch.manual_seed(0)
    rows = []
    for it in items:
        t0 = time.time()
        r = decide_and_copy(one_b, head, it["text"])
        rows.append({"id": it["id"], **r, "ms": round((time.time() - t0) * 1000, 1)})
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"task": a.task, "rows": len(rows), "gated": sum(r["gate"] for r in rows),
                      "yes": sum(r["yes"] for r in rows), "fired": sum(r["parsed"] is not None for r in rows)}))


def score(a) -> None:
    import claude_dl1_nights as D1
    import claude_rt02d as RT
    import claude_rt02e as RE
    import claude_rt02g as G
    out, pd = Path(a.out), Path(a.panel_dir)
    truth = _load(pd / "chat_puzzles.jsonl")
    negs = _load(pd / "negatives.jsonl")
    want = {t["id"]: {"nums": sorted(t["nums"]), "target": t["target"]} for t in truth}
    hp = {r["id"]: r for r in _load(out / "H_puzzles.jsonl")}
    hn = {r["id"]: r for r in _load(out / "H_negatives.jsonl")}
    assert set(hp) == set(want) and set(hn) == {n["id"] for n in negs}
    res = {"exact_reads": {}, "fires_negatives": {}, "wrong_puzzle": {}, "per_wording_exact": {}}
    reading = {"H": {i: r["parsed"] for i, r in hp.items()},
               "D": {t["id"]: RT.parse_puzzle(t["text"]) for t in truth},
               "E": {t["id"]: RE.fires(t["text"]) for t in truth}}
    for arm, rd in reading.items():
        res["exact_reads"][arm] = sum(int(rd[i] == want[i]) for i in want)
        res["wrong_puzzle"][arm] = sum(int(rd[i] is not None and rd[i] != want[i]) for i in want)
        wd = Counter()
        for t in truth:
            wd[t["wording_id"]] += int(rd[t["id"]] == want[t["id"]])
        res["per_wording_exact"][arm] = dict(sorted(wd.items()))
    res["fires_negatives"] = {"H": sum(int(r["parsed"] is not None) for r in hn.values()),
                              "D": sum(int(RT.parse_puzzle(n["text"]) is not None) for n in negs),
                              "E": sum(int(RE.fires(n["text"]) is not None) for n in negs)}
    res["H_gated"] = {"puzzles": sum(r["gate"] for r in hp.values()), "negatives": sum(r["gate"] for r in hn.values())}
    res["H_yes"] = {"puzzles": sum(r["yes"] for r in hp.values()), "negatives": sum(r["yes"] for r in hn.values())}
    res["H_scores"] = {k: sorted(round(r["score"], 2) for r in v.values() if r["score"] is not None)
                       for k, v in (("puzzles", hp), ("negatives", hn))}
    res["H_ms_median"] = sorted(r["ms"] for r in list(hp.values()) + list(hn.values()))[100]
    res["general_items_reaching_head"] = sum(int(G.pre_gate(it["q"])) for it in D1.harm_panel())
    e, n = res["exact_reads"], res["fires_negatives"]
    res["marks"] = {"H1": e["H"] >= 85 and e["H"] >= e["D"] - 2,
                    "H2": n["H"] <= 2,
                    "H3": res["wrong_puzzle"]["H"] <= 2,
                    "H4": res["general_items_reaching_head"] == 0}
    res["pass"] = all(res["marks"].values())
    res["replace_rules"] = res["pass"] and n["H"] <= n["E"]
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "rt02h_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("exact_reads", "fires_negatives", "wrong_puzzle", "marks", "pass",
                                          "replace_rules")}))


def selftest(head_path: str) -> None:
    import claude_dl1_nights as D1
    import claude_rt02g as G
    import claude_rt02h_probe as PR
    n = 0
    head = PR.load_head(head_path)
    for k in ("mu", "sd", "w", "b", "cut", "layer", "layer_index"):
        assert k in head, k
    n += 1
    assert PR.LAYERS[head["layer_index"]] == head["layer"] and head["w"].shape == head["mu"].shape; n += 1
    assert sum(G.pre_gate(it["q"]) for it in D1.harm_panel()) == 0; n += 1
    import torch
    f = torch.zeros(len(PR.LAYERS), head["w"].shape[0])
    assert isinstance(PR.head_score(head, f), float); n += 1
    print(f"rt02h selftest {n}/{n}")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        ap = argparse.ArgumentParser()
        ap.add_argument("--selftest", action="store_true")
        ap.add_argument("--head", required=True)
        selftest(ap.parse_args().head)
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score"])
    ap.add_argument("--task", default="puzzles")
    ap.add_argument("--model", default="")
    ap.add_argument("--head", default="")
    ap.add_argument("--panel-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--score", default="")
    a = ap.parse_args()
    {"run": run, "score": score}[a.cmd](a)


if __name__ == "__main__":
    main()
