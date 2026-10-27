#!/usr/bin/env python3
"""Exp 119h — Mac-CPU smoke (Muse BUILD, NOT a registered run).

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \\
      python -B scripts/fable_ears119h_smoke.py --snapshot <scibert> \\
      --out artifacts/fable-ears119h-20260922/smoke.json

With the REAL SciBERT encoder (fp32, CPU) at MAX_LEN 192:
  (1) the generator is deterministic (same seed -> same rows sha);
  (2) EXACTLY 5,000 rows; per-relation counts printed;
  (3) span asserts re-verified on every row (subj text, obj text, forward
      dir, registered relation; occupation objects hold the first job only);
  (4) novelty OK vs the OLD panel (zero sentence overlap, zero name hits;
      reading94b never opened);
  (5) 50 teacher-forced training steps run on the new rows (same loss_fn,
      same AdamW lr 3e-5); reports step losses.
NO scores (no panel files, no gold comparison, no taus).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402
import fable_ears119h_data as D119h  # noqa: E402
import fable_ears47_encoder as E  # noqa: E402
import fable_ears119g_model as M119g  # noqa: E402
import fable_ears47_model as M  # noqa: E402

SMOKE_SEED = 11910
SMOKE_STEPS = 50
SMOKE_BATCH = 4

assert D.MAX_LEN == D119h.B.MAX119 == 192


def pack_of(sub, L):
    ids = torch.zeros(len(sub), L, dtype=torch.long)
    mask = torch.zeros(len(sub), L, dtype=torch.bool)
    for i, r in enumerate(sub):
        n = len(r["ids"])
        ids[i, :n] = torch.tensor(r["ids"])
        mask[i, :n] = True
    return {"ids": ids, "mask": mask,
            "act": torch.tensor([r["act"] for r in sub]),
            "rel": torch.tensor([r["rel"] for r in sub]),
            "subj": torch.tensor([r["subj"] for r in sub]),
            "obj": torch.tensor([r["obj"] for r in sub]),
            "dir": torch.tensor([r["dir"] for r in sub]),
            "flags": torch.tensor([r["flags"] for r in sub],
                                  dtype=torch.float)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    torch.set_num_threads(1)
    torch.manual_seed(SMOKE_SEED)
    t0 = time.time()
    res: dict = {"seed": SMOKE_SEED}

    enc, tok, info = E.load(a.snapshot)
    print(f"encoder params {info['params']:,} max_len {D.MAX_LEN}", flush=True)

    # (1) determinism: same seed -> same sha of the rows.
    rows_a = D119h.occ_rows()
    rows_b = D119h.occ_rows(random.Random(D119h.RNG_OCC))
    sha_a, sha_b = D119h.rows_sha(rows_a), D119h.rows_sha(rows_b)
    print(f"rows sha: {sha_a[:16]} vs {sha_b[:16]}", flush=True)
    assert sha_a == sha_b, "generator is not deterministic"
    res["deterministic_sha"] = sha_a[:16]

    # (2) exactly 5,000 rows; per-relation counts.
    assert len(rows_a) == D119h.N_REPLACE == 5000, len(rows_a)
    per_rel: dict[str, int] = {}
    for r in rows_a:
        per_rel[r["gold47"]["rel"]] = per_rel.get(r["gold47"]["rel"], 0) + 1
    print(f"rows=5000 per-relation={per_rel}", flush=True)
    assert per_rel.get("occupation", 0) >= 1500, per_rel
    res["rows"] = len(rows_a)
    res["rows_per_relation"] = per_rel
    res["shape_measured"] = {k: v for k, v in D119h.OCC_STATS.items()
                             if k != "rows_per_relation"
                             and k != "citizenship_convention"}

    # (3) span asserts on every row.
    occ_idx = D.CLASSES["classes"].index("occupation")
    for r in rows_a:
        t, g = r["text"], r["gold47"]
        assert g["act"] == "STATE" and g["rep"] is True
        assert g["rel"] in D.CLASSES["classes"], g["rel"]
        subj_txt = t[g["subj"][0]:g["subj"][1]]
        obj_txt = t[g["obj"][0]:g["obj"][1]]
        assert subj_txt and obj_txt, (t, g)
        assert g["subj"][0] == 0, (t, g)
        assert g["dir"] == D.DIR_FORWARD == D._dir_of(g["subj"], g["obj"])
        if g["rel"] == "occupation":
            # First job only: never a list remainder.
            assert " and " not in obj_txt and "," not in obj_txt, (t, obj_txt)
    print("span asserts OK on 5000 rows", flush=True)
    res["span_asserts"] = "OK-5000"

    # (4) novelty vs the OLD panel (reading94b never opened).
    nov = D119h.check_novelty(rows_a)
    assert nov["sentence_overlap"] == [], nov["sentence_overlap"][:5]
    assert nov["name_hits"] == [], nov["name_hits"][:10]
    print(f"novelty OK: {nov['occ_sentences']} sentences, "
          f"{nov['panel94_sentences']} panel94 sentences", flush=True)
    res["novelty"] = {"occ_sentences": nov["occ_sentences"],
                      "sentence_overlap": [], "name_hits": []}

    # (5) 50 teacher-forced steps on the new rows (mixed relations).
    rng = random.Random(SMOKE_SEED)
    cand = []
    for row in rows_a:
        e = D.encode_row(row, tok)
        if e is None:
            continue
        e.pop("chspans", None)
        cand.append(e)
    assert len(cand) >= 64, f"only {len(cand)} rows encoded"
    rng.shuffle(cand)
    sub = cand[:64]
    rels = {r["rel"] for r in sub}
    assert occ_idx in rels and len(rels) >= 3, rels
    Ls = max(len(r["ids"]) for r in sub)
    pack = pack_of(sub, Ls)
    model = M119g.RelCondEars(enc, D.N_REL)
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=3e-5, weight_decay=0.01)
    losses = []
    t_train = time.time()
    order = list(range(len(sub)))
    for step in range(1, SMOKE_STEPS + 1):
        random.Random(SMOKE_SEED + step).shuffle(order)
        idx = torch.tensor(order[:SMOKE_BATCH])
        b = {k: v[idx] for k, v in pack.items()}
        o = model(b["ids"], b["mask"], rel_override=b["rel"])
        loss = M.loss_fn(o, b)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        losses.append(float(loss.detach()))
        if step in (1, 25, 50):
            print(f"smoke step {step}/{SMOKE_STEPS} loss {losses[-1]:.4f}",
                  flush=True)
    assert losses[-1] < losses[0], (losses[0], losses[-1])
    res.update({"train_rows": len(sub), "train_relations": len(rels),
                "loss_step1": losses[0], "loss_step25": losses[24],
                "loss_step50": losses[49],
                "train_sec_per_step": (time.time() - t_train) / SMOKE_STEPS})

    res["elapsed_sec"] = time.time() - t0
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
