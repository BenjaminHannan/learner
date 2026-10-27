#!/usr/bin/env python3
"""Exp 119g — Mac-CPU smoke (Muse BUILD, NOT a registered run).

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \\
      python -B scripts/fable_ears119g_smoke.py --snapshot <scibert> \\
      --out artifacts/fable-ears119g-20260922/smoke.json

With the REAL SciBERT encoder (fp32, CPU) at MAX_LEN 192:
  (1) U=0 identity: RelCondEars (U zeroed) gives outputs identical to
      FrameEars with the same weights on 5 rows (reports max abs diff per
      head; must be 0.0).
  (2) 50 teacher-forced training steps run through the 119g trainer module
      path (same loss_fn, same AdamW lr 3e-5) on a tiny mixed subset that
      INCLUDES synth-occ rows; reports step losses.
  (3) multi-decode returns >= 2 frames on a hand-made 2-fact sentence with
      fictional names after a tiny overfit (2 single-fact sentences, same
      fictional person, occupation + date of birth).
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
import fable_ears119b_data as D119b  # noqa: E402  (REMAP)
import fable_ears119f_data as D119f  # noqa: E402  (occupation rows)
import fable_ears47_encoder as E  # noqa: E402
import fable_ears47_model as M  # noqa: E402
import fable_ears119g_model as M119g  # noqa: E402
import fable_ears119g_score as G119  # noqa: E402
import fable_ears47_score as S47  # noqa: E402

SMOKE_SEED = 11910
SMOKE_STEPS = 50
SMOKE_BATCH = 4

assert D.MAX_LEN == D119b.MAX119 == 192

# Fictional names only (invented here; never panel names).
PERSON_A = "Aldric Ashdown"
PERSON_B = "Beatrix Broadbent"


def encode_texts(texts, tok):
    rows = [{"text": t,
             "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None,
                        "obj": None, "dir": 0, "rep": False}} for t in texts]
    encs = [D.encode_row(r, tok) for r in rows]
    assert all(e is not None for e in encs), "smoke texts must encode"
    return rows, encs


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
    occ_idx = D.CLASSES["classes"].index("occupation")
    dob_idx = D.CLASSES["classes"].index("date of birth")

    # (1) U=0 identity on 5 rows (mixed: occ, dob, hearsay-free STATE, ASK).
    occ = D119f.occ_rows()[:3]
    probe_texts = [occ[0]["text"], occ[1]["text"],
                   f"{PERSON_A} was born on 4 March 1901.",
                   f"Where was {PERSON_B} born?",
                   f"{PERSON_B} was a Brazilian chemist."]
    probe_rows, probe_encs = encode_texts(probe_texts, tok)
    base = M.FrameEars(enc, D.N_REL).eval()
    g = M119g.RelCondEars(enc, D.N_REL).eval()
    g.load_state_dict(base.state_dict(), strict=False)  # U stays 0
    assert float(g.U.weight.detach().abs().max()) == 0.0
    L = max(len(e["ids"]) for e in probe_encs)
    ids = torch.zeros(len(probe_encs), L, dtype=torch.long)
    mask = torch.zeros(len(probe_encs), L, dtype=torch.bool)
    for i, e in enumerate(probe_encs):
        ids[i, :len(e["ids"])] = torch.tensor(e["ids"])
        mask[i, :len(e["ids"])] = True
    with torch.no_grad():
        ob = base(ids, mask)
        og = g(ids, mask)
    diffs = {k: float((ob[k] - og[k]).abs().max())
             for k in ("act", "rel", "direction", "flags", "ptr")}
    print(f"U=0 identity max-abs-diffs: {diffs}", flush=True)
    assert all(v == 0.0 for v in diffs.values()), diffs
    res["u0_identity_max_abs_diff"] = diffs

    # (2) 50 teacher-forced steps on a tiny mixed subset incl. synth-occ.
    rng = random.Random(SMOKE_SEED)
    pool = []
    for r in D119f.occ_rows(random.Random(D119f.RNG_OCC))[:24]:
        r = dict(r)
        r["gold47"] = D119b.remap_gold(r["gold47"])
        pool.append(r)
    for r in D.synth_pool_rows(tok, random.Random(D.POOL_SEED + 7))[:120]:
        r = dict(r)
        r["gold47"] = D119b.remap_gold(r["gold47"])
        pool.append(r)
    rng.shuffle(pool)
    occ_c, other_c = [], []
    for row in pool:
        e = D.encode_row(row, tok)
        if e is None:
            continue
        e.pop("chspans", None)
        (occ_c if row.get("source") == "synth-occ" else other_c).append(e)
    assert len(occ_c) >= 8, f"only {len(occ_c)} occ rows encoded"
    assert len(other_c) >= 24, f"only {len(other_c)} other rows"
    cand = occ_c[:8] + other_c[:24]
    rng.shuffle(cand)
    sub = cand[:32]
    assert sum(1 for r in sub if r["rel"] == occ_idx) == 8
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
    res.update({"train_rows": len(sub), "loss_step1": losses[0],
                "loss_step25": losses[24], "loss_step50": losses[49],
                "train_sec_per_step": (time.time() - t_train) / SMOKE_STEPS})

    # (3) tiny overfit -> multi-decode >= 2 frames on a 2-fact sentence.
    fit_texts = [f"{PERSON_A} was an American baker.",
                 f"{PERSON_A} was born on 4 March 1901."]
    fit_golds = [
        {"act": "STATE", "rel": "occupation",
         "subj": [0, len(PERSON_A)],
         "obj": [fit_texts[0].index("baker"),
                 fit_texts[0].index("baker") + len("baker")],
         "dir": 0, "rep": True},
        {"act": "STATE", "rel": "date of birth",
         "subj": [0, len(PERSON_A)],
         "obj": [fit_texts[1].index("4 March 1901"),
                 fit_texts[1].index("4 March 1901") + len("4 March 1901")],
         "dir": 0, "rep": True},
    ]
    fit_enc = []
    for t, gl in zip(fit_texts, fit_golds):
        e = D.encode_row({"text": t, "source": "smoke-fit", "gold47": gl},
                         tok)
        assert e is not None
        e.pop("chspans", None)
        fit_enc.append(e)
    Lf = max(len(r["ids"]) for r in fit_enc)
    fpack = pack_of(fit_enc, Lf)
    m2 = M119g.RelCondEars(enc, D.N_REL)
    m2.train()
    opt2 = torch.optim.AdamW(m2.parameters(), lr=3e-5, weight_decay=0.01)
    for step in range(60):
        idx = torch.tensor([step % 2])
        b = {k: v[idx] for k, v in fpack.items()}
        loss = M.loss_fn(m2(b["ids"], b["mask"], rel_override=b["rel"]), b)
        opt2.zero_grad(set_to_none=True)
        loss.backward()
        opt2.step()
    m2.eval()
    two_fact = (f"{PERSON_A} was an American baker born on 4 March 1901.")
    trows, tencs = encode_texts([two_fact], tok)
    unk_ids = {tok.unk}
    frames = G119.decode_all_multi(m2, trows, tencs, torch.device("cpu"),
                                   unk_ids, K=2, FLOOR=0.0)[0]
    P0 = S47.probs_for_model(m2, tencs, torch.device("cpu"))[0]
    rels = [D.CLASSES["classes"][r] for r in
            G119.candidates_of(P0["rel"], 2, 0.0)]
    print(f"2-fact decode: {len(frames)} frames, rels={rels}", flush=True)
    for f in frames:
        print(f"  frame={f['frame']} conf={f['conf']:.3f}", flush=True)
    assert len(frames) >= 2, f"only {len(frames)} frames"
    res.update({"two_fact_frames": len(frames), "two_fact_rels": rels,
                "two_fact_text": two_fact})

    res["elapsed_sec"] = time.time() - t0
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
