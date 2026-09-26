#!/usr/bin/env python3
"""gr-5: the reader 1B is trained to copy the square (Plain-English puzzles thread, 2026-09-26).

gr-4 (NOTE e51d7f347) showed that the plain 1B, asked to copy the square under a grammar, reads 3 or 4 of 20 practice
squares and either invents squares or says "none" for real ones. The plainest well-known fix for a small model that
must turn text into a structure is supervised fine-tuning. The one change from gr-4: a LoRA adapter on the 1B
(claude_blurt2.add_lora, the sleep recipe: rank 16 on q/k/v/o, 3 epochs, lr 2e-4, batch 8), trained with the loss on
the answer only. The prompt, the grammar and the greedy decode are gr-4's, unchanged.

Training rows (no Claude text, no GLM text, no test item): gr-1's 860 practice messages
(artifacts/claude-gr1-20260926/train/train.jsonl: code-made squares in 8 layouts inside the 1B's own wrappers, and
the 1B's own no-square messages) and gr-3's 58 kept 1B number tables (artifacts/claude-gr3-20260926/train/
table_drafts_1b.jsonl). The target is printed by code: the square one row per line with "_" for a blank, or the
single word "none". Every fifth row of each kind is held out as a dev split.

  python -B scripts/claude_gr5.py --selftest
  python -B scripts/claude_gr5.py build --out ROWS.jsonl
  python -B scripts/claude_gr5.py time --model BASE --rows ROWS.jsonl --n 8
  python -B scripts/claude_gr5.py train --model BASE --rows ROWS.jsonl --adapter ADAPTER.pt
  python -B scripts/claude_gr5.py dev --model BASE --rows ROWS.jsonl --adapter ADAPTER.pt
  python -B scripts/claude_gr5.py run --task squares|lookalikes|unseen|general --arm L|P0 --model BASE \
      --adapter ADAPTER.pt --panel-dir PD --out OUT
  python -B scripts/claude_gr5.py score --out OUT --panel-dir PD --score SCOREDIR
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_gr4 as G4  # noqa: E402

ROOT = SCRIPTS.parent
SEED = 4990
EPOCHS, LR, BATCH = 3, 2e-4, 8                       # claude_dl1_nights.S_RECIPE and train_copy's batch
GR1_TRAIN = ROOT / "artifacts/claude-gr1-20260926/train/train.jsonl"
GR3_TABLES = ROOT / "artifacts/claude-gr3-20260926/train/table_drafts_1b.jsonl"


def target_of(grid) -> str:
    if grid is None:
        return "none"
    return "\n".join(" ".join(str(v) if v else "_" for v in row) for row in grid)


def _load(p: Path):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


# ------------------------------------------------------------------ training rows
def build(a) -> None:
    import claude_puzzle_reader as R
    rows = [{"kind": r["kind"], "text": r["text"], "grid": r["grid"]} for r in _load(GR1_TRAIN)]
    for r in _load(GR3_TABLES):
        if r["keep"]:
            sq = R.read_latin(r["text"])
            rows.append({"kind": "table", "text": r["text"], "grid": None if sq is None else sq["grid"]})
    seen = Counter()
    for r in rows:
        r["split"] = "dev" if seen[r["kind"]] % 5 == 4 else "train"
        seen[r["kind"]] += 1
        r["target"] = target_of(r["grid"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    c = Counter((r["split"], "square" if r["grid"] is not None else "none") for r in rows)
    print(json.dumps({"rows": len(rows), **{f"{k[0]}_{k[1]}": v for k, v in sorted(c.items())}}))


# ------------------------------------------------------------------ the 1B, its adapter and the copy
def load(model: str, adapter: str | None):
    import os
    import claude_rt02g as G
    import claude_sleep02c as SL
    import torch
    if os.environ.get("SLEEP02C_ADAPTER"):
        raise SystemExit("gr5: unset SLEEP02C_ADAPTER (the reader starts from the plain 1B)")
    one_b = G.load_one_b(model)                     # the LoRA layers are added as identity (B = 0)
    mods = SL.lora_mods(one_b.model)
    if adapter:
        state = torch.load(adapter, map_location="cpu")
        if len(state) != len(mods):
            raise SystemExit(f"gr5: adapter has {len(state)} layers, model has {len(mods)}")
        for m, (A, B) in zip(mods, state):
            m.A.data.copy_(A.to(m.A.device))
            m.B.data.copy_(B.to(m.B.device))
    return one_b


def prompt_ids(one_b, text):
    tok = one_b.tok
    p = tok.apply_chat_template([{"role": "user", "content": G4.PROMPT.format(req=text)}], tokenize=False,
                                add_generation_prompt=True, enable_thinking=False)
    return tok(p, return_tensors="pt").input_ids[0]


class Copier5(G4.Copier):
    """gr-4's constrained greedy copy; the only difference is that the LoRA scales are left as they are."""

    def __init__(self, one_b, plain: bool):
        super().__init__(one_b)
        self.plain = plain

    def copy(self, text):
        if self.plain:
            return super().copy(text)               # gr-4 exactly: every LoRA scale 0 during the copy
        torch = self.torch
        ids = prompt_ids(self.one_b, text).unsqueeze(0).to(self.one_b.dev)
        out, m, past = [], G4.Machine(), None
        with torch.no_grad():
            cur = ids
            for step in range(G4.MAX_NEW):
                r = self.model(input_ids=cur, past_key_values=past, use_cache=True)
                past, logits = r.past_key_values, r.logits[0, -1]
                if m.mode == "none":
                    break
                opts = self.allowed(m, step == 0)
                cand = list(opts)
                if m.can_end():
                    cand.append(self.eos)
                if not cand:
                    break
                idx = torch.tensor(cand, device=logits.device)
                pick = cand[int(logits[idx].argmax())]
                if pick == self.eos:
                    break
                m = opts[pick]
                out.append(pick)
                cur = torch.tensor([[pick]], device=ids.device)
        raw = self.tok.decode(out)
        raw = raw.lower() if m.mode == "none" else raw
        return {"raw": raw, "grid": G4.parse(raw) if (m.mode == "none" or m.can_end()) else None,
                "complete": m.mode == "none" or m.can_end()}


def _example(one_b, row):
    import torch
    pr = prompt_ids(one_b, row["text"])
    an = one_b.tok(row["target"], add_special_tokens=False, return_tensors="pt").input_ids[0]
    full = torch.cat([pr, an, torch.tensor([one_b.tok.eos_token_id])])
    lab = full.clone()
    lab[:len(pr)] = -100
    return full, lab


def _steps(one_b, rows, epochs, seed, opt=None, limit=0):
    import torch
    m = one_b.model
    rng = random.Random(seed)
    torch.manual_seed(seed)
    m.train()
    done, per_epoch = 0, []
    for ep in range(epochs):
        ex = list(rows)
        rng.shuffle(ex)
        tot, n = 0.0, 0
        for i in range(0, len(ex), BATCH):
            batch = ex[i:i + BATCH]
            for row in batch:
                full, lab = _example(one_b, row)
                loss = m(input_ids=full.unsqueeze(0).to(one_b.dev), labels=lab.unsqueeze(0).to(one_b.dev)).loss
                (loss / len(batch)).backward()
                tot, n = tot + float(loss.detach()), n + 1
                done += 1
            if opt is not None:
                opt.step()
            opt_zero(m, opt)
            if limit and done >= limit:
                m.eval()
                return per_epoch, done
        per_epoch.append(round(tot / max(1, n), 4))
    m.eval()
    return per_epoch, done


def opt_zero(m, opt):
    if opt is not None:
        opt.zero_grad()
    else:
        for p in m.parameters():
            p.grad = None


def time_steps(a) -> None:
    one_b = load(a.model, None)
    rows = [r for r in _load(a.rows) if r["split"] == "train"]
    n = int(a.n or 8)
    t0 = time.time()
    _steps(one_b, rows, 1, SEED, None, limit=n)
    dt = (time.time() - t0) / n
    print(json.dumps({"device": one_b.dev, "seconds_per_example": round(dt, 2), "train_rows": len(rows),
                      "estimated_hours": round(dt * len(rows) * EPOCHS / 3600, 2)}))


def train(a) -> None:
    import claude_sleep02c as SL
    import torch
    one_b = load(a.model, None)
    rows = [r for r in _load(a.rows) if r["split"] == "train"]
    params = [p for p in one_b.model.parameters() if p.requires_grad]
    assert params and len(params) == 2 * len(SL.lora_mods(one_b.model)), "gr5: only the LoRA A and B may train"
    opt = torch.optim.AdamW(params, lr=LR)
    t0 = time.time()
    per_epoch, done = _steps(one_b, rows, EPOCHS, SEED, opt)
    torch.save([(m.A.detach().cpu(), m.B.detach().cpu()) for m in SL.lora_mods(one_b.model)], a.adapter)
    print(json.dumps({"device": one_b.dev, "train_rows": len(rows), "examples_seen": done,
                      "mean_loss_by_epoch": per_epoch, "minutes": round((time.time() - t0) / 60, 1)}))


# ------------------------------------------------------------------ dev (practice only; report)
def dev(a) -> None:
    import claude_rsn358b2_bridge as B
    import claude_rt02d as RT
    one_b = load(a.model, a.adapter or None)
    cp = Copier5(one_b, plain=not a.adapter)
    items = []
    sm = ROOT / "artifacts/claude-panel-rsn358b3-smoke-20260926"
    ans = {r["id"]: r for r in map(json.loads, (sm / "answers.jsonl").read_text().splitlines())}
    items += [("smoke", r["message"], ans[r["id"]]["puz"]) for r in map(json.loads, (sm / "panel.jsonl").read_text()
                                                                         .splitlines())][:10]
    for s in (4, 5, 6, 7):
        items += [("fresh", q["text"], q["puz"]) for q in B.make_requests(487000 + s, 6, s, False)]
    items = items[:10] + [it for it in items[10:] if it[0] == "fresh"][:10]
    items += [("nosquare", t, None) for t, _ in RT.dev_cases()][:10]
    items += [("heldout_" + ("square" if r["grid"] is not None else "none"), r["text"], r["grid"])
              for r in _load(a.rows) if r["split"] == "dev"]
    st = Counter()
    t0 = time.time()
    for kind, text, truth in items:
        r = cp.copy(text)
        st[kind + "_n"] += 1
        st[kind + "_exact"] += int(r["grid"] == truth)
        st[kind + "_wrong"] += int(r["grid"] is not None and r["grid"] != truth)
    st["seconds_per_message"] = round((time.time() - t0) / max(1, len(items)), 1)
    if a.adapter:                                   # PASSMARKS-gr5 stop rule, on the held-out split only
        st["dev_gate"] = "PASS" if (st["heldout_square_exact"] >= 65 and st["heldout_none_wrong"] == 0) else "FAIL"
    print(json.dumps(dict(sorted(st.items()))))


# ------------------------------------------------------------------ registered run and score
def run(a) -> None:
    import claude_dl1_nights as D1
    if a.arm not in ("L", "P0"):
        raise SystemExit("gr5: --arm is L (the trained reader) or P0 (the plain 1B, gr-4)")
    if a.arm == "L" and not a.adapter:
        raise SystemExit("gr5: arm L needs --adapter")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{a.arm}_{a.task}.jsonl"
    if path.exists():
        raise SystemExit(f"gr5: {path} exists (each run is launched once)")
    if a.task == "general":
        items = [{"id": "gen-%03d" % i, "text": it["q"]} for i, it in enumerate(D1.harm_panel())]
    else:
        items = _load(Path(a.panel_dir) / f"{a.task}.jsonl")
    cp = Copier5(load(a.model, a.adapter if a.arm == "L" else None), plain=a.arm == "P0")
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            t0 = time.time()
            r = cp.copy(it["text"])
            f.write(json.dumps({"id": it["id"], "grid": r["grid"], "complete": r["complete"],
                                "ms": round((time.time() - t0) * 1000, 1)}) + "\n")
            f.flush()
    rows = _load(path)
    print(json.dumps({"arm": a.arm, "task": a.task, "rows": len(rows),
                      "read_as_square": sum(r["grid"] is not None for r in rows)}))


def score(a) -> None:
    import claude_dl1_nights as D1
    import claude_puzzle_reader as R
    out, pd = Path(a.out), Path(a.panel_dir)
    panel = {t: _load(pd / f"{t}.jsonl") for t in ("squares", "lookalikes", "unseen")}
    got = {arm: {t: {r["id"]: r for r in _load(out / f"{arm}_{t}.jsonl")} for t in ("squares", "lookalikes", "unseen")}
           for arm in ("L", "P0")}
    got["L"]["general"] = {r["id"]: r for r in _load(out / "L_general.jsonl")}
    for arm in ("L", "P0"):
        for t in ("squares", "lookalikes", "unseen"):
            assert set(got[arm][t]) == {r["id"] for r in panel[t]}, (arm, t)
    assert len(got["L"]["general"]) == 300
    res = {}
    for arm in ("L", "P0", "C"):
        rd = (lambda t, r: (R.read_latin(r["text"]) or {}).get("grid")) if arm == "C" else \
             (lambda t, r, arm=arm: got[arm][t][r["id"]]["grid"])
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
        if arm == "L":
            x["general_read_as_square"] = sum(int(r["grid"] is not None) for r in got["L"]["general"].values())
        elif arm == "C":
            x["general_read_as_square"] = sum(int(R.read_latin(it["q"]) is not None) for it in D1.harm_panel())
        res[arm] = x
    L = res["L"]
    res["incomplete_L"] = sum(int(not r["complete"]) for t in got["L"] for r in got["L"][t].values())
    res["lookalikes_truth_square"] = sum(int(r["square"] is not None) for r in panel["lookalikes"])
    res["ms_median_squares_L"] = sorted(r["ms"] for r in got["L"]["squares"].values())[50]
    res["marks"] = {"R1": L["squares_exact"] >= 97, "R2": L["lookalikes_false_square"] <= 1,
                    "R3": L["squares_wrong"] <= 1, "R4": L["general_read_as_square"] == 0,
                    "U1": L["unseen_exact"] >= 48, "U2": L["unseen_wrong"] <= 2}
    res["gr5_pass"] = all(res["marks"][k] for k in ("R1", "R2", "R3", "R4"))
    res["gr5U_pass"] = res["marks"]["U1"] and res["marks"]["U2"]
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "gr5_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if not kk.endswith("_by")} if k in ("L", "P0", "C")
                          else v) for k, v in res.items()}))


def selftest() -> None:
    n = 0
    for grid in ([[1, 0, 3], [3, 1, 0], [0, 3, 1]], [[0, 0, 0, 4], [1, 2, 3, 4], [4, 0, 0, 1], [2, 0, 0, 0]]):
        t = target_of(grid)
        m = G4.Machine().feed(t)
        assert m is not None and m.can_end() and G4.parse(t) == grid, t        # every target is inside the grammar
        n += 1
    assert target_of(None) == "none" and G4.parse("none") is None
    n += 1
    rows = _load(GR1_TRAIN)
    bad = [r for r in rows if r["grid"] is not None and G4.parse(target_of(r["grid"])) != r["grid"]]
    assert not bad, f"{len(bad)} practice squares do not round-trip through the grammar's parser"
    n += 1
    print(f"gr5 selftest {n}/{n}")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "time", "train", "dev", "run", "score"])
    for k in ("model", "rows", "adapter", "out", "n", "task", "arm", "panel-dir", "score"):
        ap.add_argument("--" + k, default="")
    a = ap.parse_args()
    {"build": build, "time": time_steps, "train": train, "dev": dev, "run": run, "score": score}[a.cmd](a)


if __name__ == "__main__":
    main()
