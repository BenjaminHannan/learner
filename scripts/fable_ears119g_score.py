#!/usr/bin/env python3
"""Exp 119g — scorer: K=1 old decode + relation-conditioned multi-fact decode.

    # step 0: re-score the EXISTING 119f checkpoints (K=1 old decode only)
    python fable_ears119g_score.py --step0 --runs119f <ears119f/runs> \\
        --taus119f <taus119f.json> --snapshot <scibert> \\
        --panel94b <panel94b.jsonl> --out step0_119f.json
    # 47 panels on the 119g checkpoints (K=1, 119e logic, taus by 47 rule)
    python fable_ears119g_score.py --score47g --runs <runs> \\
        --panels47 <panels> --snapshot <scibert> --out report47g.json \\
        --taus-out taus119g.json
    # reading panels on the 119g checkpoints (K=1 AND K=chosen)
    python fable_ears119g_score.py --score-panel --runs <runs> \\
        --taus <taus119g.json> --snapshot <scibert> --panel <panel.jsonl> \\
        --panel-tag 94b --k 3 --floor 0.10 --out report119g_94b.json

--step0 records the comparison baseline on reading94b with the UNCHANGED old
decode: per-seed ungated emitted triples, exact, precision (= exact/emitted),
occupation exact, plus gated writes at the 119f taus. M3 compares against the
ungated precision (the 119f gated writes were 0/0/0, so gated precision is
undefined; ungated precision is well-defined).

--score-panel: act head unchanged (one act per sentence). For STATE frames,
relations are taken in order of calibrated probability, up to K with
p >= FLOOR, and subject/object are decoded for EACH relation with its own
conditioned pointers; duplicate triples are dropped. K=1 is ALWAYS reported
with the verbatim old decode (S47.decode); K=chosen uses forced-rel frames
that mirror S47.decode line-for-line except the relation is fixed and the
confidence uses that relation's own calibrated probability. Verdicts are
S47.verdict_single per frame at the seed's tau_exec_single. 106 normaliser
by import. No test.pt anywhere; panels are scoring-only.

Additive only: decode core, verdicts, tau rule, REMAP, and the 106
normaliser by import. The loader builds RelCondEars and loads with
strict=False so 119f FrameEars checkpoints score identically (missing
rel_emb/U keep their init; U=0 is never used on the K=1 path).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears119e_score as E119  # noqa: E402  (score47e + REMAP logic)
import fable_ears119b_score as B119  # noqa: E402  (seed namespace 11911-11913)
import fable_ears47_data as D  # noqa: E402
import fable_ears119_data as D119  # noqa: E402  (MAX_LEN = 192 override)
import fable_ears47_encoder as ENC  # noqa: E402
import fable_ears47_score as S47  # noqa: E402
import fable_ears119_score as S119  # noqa: E402  (PANELS47, executable_state_n)
import fable_ears119g_model as M119g  # noqa: E402
import fable_read106_score as R106  # noqa: E402

SEEDS = list(B119.S119.SEEDS119)
assert tuple(SEEDS) == (11911, 11912, 11913), SEEDS


def load_model_g(runs: Path, seed: int, snapshot: str, device):
    """RelCondEars; strict=False so 119f FrameEars checkpoints load as-is."""
    ck = torch.load(runs / f"w-{seed}" / "ear.pt", map_location="cpu",
                    weights_only=False)
    enc, _, _ = ENC.load(snapshot)
    m = M119g.RelCondEars(enc, D.N_REL, freeze_layers=ck.get("freeze_layers", 0))
    m.load_state_dict(ck["state"], strict=False)
    return m.eval().to(device), ck


def decode_all_k1(model, rows, encs, device, unk_ids, batch=64):
    """Verbatim old single decode (S47.decode)."""
    P = S47.probs_for_model(model, encs, device, batch=batch)
    return [S47.decode(rows[i], encs[i], P[i], unk_ids) for i in range(len(rows))]


def decode_forced_rel(row, enc, P, ptr_r, rel_i: int, p_rel: float,
                      unk_ids: set[int]):
    """One STATE frame for a FIXED relation; mirrors S47.decode exactly.

    Same act head, same span rules (S47._span), same direction rule, same
    brakes 4/5, same conf=min rule — except the relation is the candidate
    (not argmax) and mins uses that relation's own calibrated probability.
    Non-STATE acts are never passed here (act head is unchanged: one act per
    sentence; only STATE fans out over relations).
    """
    import fable_listening_english as LE
    utt = D.row_text(row)
    n = P["n"]
    act_i = int(P["act"].argmax())
    act = D.ACTS[act_i]
    assert act == "STATE", f"forced-rel decode needs STATE, got {act}"
    p_act = float(P["act"][act_i])
    rel_str = D.CLASSES["classes"][rel_i]
    flags = P["flags"]
    chspans = enc["chspans"]
    P_r = dict(P, ptr=ptr_r)
    mins = [p_act, p_rel]
    subj, p_subj = S47._span(P_r, 0, 1, n)
    if subj is None or subj == "bad":
        return {"frame": {"act": act, "rel": rel_str, "subj": None, "obj": None,
                          "dir": None},
                "conf": 0.0, "ok4": False, "ok5": False, "forced_echo": True,
                "reason": "bad_subj", "flags": flags}
    mins.append(p_subj)
    obj, p_obj = S47._span(P_r, 2, 3, n)
    if obj is None or obj == "bad":
        return {"frame": {"act": act, "rel": rel_str, "subj": tuple(subj),
                          "obj": None, "dir": None},
                "conf": 0.0, "ok4": False, "ok5": False, "forced_echo": True,
                "reason": "bad_obj", "flags": flags}
    mins.append(p_obj)
    d = D.DIR_FORWARD if S47._wp_start(chspans, subj) <= S47._wp_start(
        chspans, obj) else D.DIR_REVERSE
    mins.append(float(P["dir"][d]))
    mins.append(1.0 - max(float(flags[1]), float(flags[2]), float(flags[3])))
    ids = enc["ids"][:n]
    covered = set(range(subj[0], subj[1] + 1))
    covered.update(range(obj[0], obj[1] + 1))
    leftover = [i for i in range(1, n - 1) if ids[i] in unk_ids
                and i not in covered]
    ok4 = not leftover
    ok5, reason = True, ""
    forced_echo = rel_str == "OPEN"
    cs, ce = S47._wp_char(chspans, subj)
    subj_txt = utt[cs:ce]
    low = subj_txt.casefold()
    if low in S47.PRON_BAD:
        return {"frame": {"act": act, "rel": rel_str, "subj": tuple(subj),
                          "obj": tuple(obj), "dir": d},
                "conf": 0.0, "ok4": False, "ok5": False, "forced_echo": True,
                "reason": "who_is_pronoun", "flags": flags}
    if low in S47.PRON_BEN:
        subj_txt = "Ben"
    elif low in S47.PRON_SELF:
        subj_txt = "self"
    item_act = "correct" if LE._has_correction_cue(utt) else "teach"
    surface = S47.pick_surface(rel_str, utt)
    path = [LE.canonical_relation(surface)]
    vs, ve = S47._wp_char(chspans, obj)
    val_txt = utt[vs:ve]
    item = LE.blank_item(
        item_act, 1.0, subject=subj_txt, relation_path=path,
        relation_surface=[surface], value=val_txt,
        value_kind="person" if rel_str in D.PERSON_CLASSES else "literal")
    if rel_str != "OPEN":
        try:
            LE.validate_model_output(
                {"items": [item], "unsure": False, "unsure_reason": ""},
                utt, None)
            ok5 = True
        except Exception:
            ok5 = False
            reason = "validator:" + "error"
    else:
        ok5 = True
    frame = {"act": act, "rel": rel_str,
             "subj": tuple(subj), "obj": tuple(obj), "dir": d}
    conf = min(mins) if mins else 0.0
    if not ok4:
        reason = reason or "leftover_words"
    return {"frame": frame, "conf": conf, "ok4": ok4, "ok5": ok5,
            "forced_echo": forced_echo, "reason": reason, "flags": flags}


def candidates_of(rel_probs, K: int, FLOOR: float):
    """Top-K relation indices with calibrated p >= FLOOR, desc order."""
    order = sorted(range(len(rel_probs)), key=lambda r: -float(rel_probs[r]))
    return [r for r in order[:K] if float(rel_probs[r]) >= FLOOR]


def decode_all_multi(model, rows, encs, device, unk_ids, K: int,
                     FLOOR: float, batch=64):
    """Per row: one act; STATE fans out over <=K relations (deduped frames).

    Non-STATE rows use the verbatim old single decode. Returns a list per
    row of parse dicts (length 1 for non-STATE, >= 1 for STATE).
    """
    base_P = S47.probs_for_model(model, encs, device, batch=batch)
    out: list[list[dict]] = []
    # batch the (row, relation) pointer computations
    pairs: list[tuple[int, int]] = []
    for i in range(len(rows)):
        if encs[i] is None or base_P[i] is None:
            continue
        act = D.ACTS[int(base_P[i]["act"].argmax())]
        if act != "STATE":
            continue
        for r in candidates_of(base_P[i]["rel"], K, FLOOR):
            pairs.append((i, r))
    ptr_of: dict[tuple[int, int], torch.Tensor] = {}
    for s in range(0, len(pairs), batch):
        chunk = pairs[s:s + batch]
        L = max(int(base_P[i]["n"]) for i, _ in chunk)
        ids = torch.zeros(len(chunk), L, dtype=torch.long)
        mask = torch.zeros(len(chunk), L, dtype=torch.bool)
        rel = torch.tensor([r for _, r in chunk])
        for j, (i, _) in enumerate(chunk):
            n = int(base_P[i]["n"])
            ids[j, :n] = torch.tensor(encs[i]["ids"][:n])
            mask[j, :n] = True
        pp = M119g.conditioned_ptr_probs(
            model, ids.to(device), mask.to(device), rel.to(device))
        for j, key in enumerate(chunk):
            n = int(base_P[key[0]]["n"])
            ptr_of[key] = pp[j, :, :n].cpu()
    for i in range(len(rows)):
        if encs[i] is None or base_P[i] is None:
            out.append([S47.decode(rows[i], encs[i], base_P[i], unk_ids)])
            continue
        act = D.ACTS[int(base_P[i]["act"].argmax())]
        if act != "STATE":
            out.append([S47.decode(rows[i], encs[i], base_P[i], unk_ids)])
            continue
        frames = []
        seen = set()
        for r in candidates_of(base_P[i]["rel"], K, FLOOR):
            p = decode_forced_rel(
                rows[i], encs[i], base_P[i], ptr_of[(i, r)], r,
                float(base_P[i]["rel"][r]), unk_ids)
            key = S47.frame_key(p["frame"])
            if key in seen:
                continue
            seen.add(key)
            frames.append(p)
        if not frames:
            frames = [S47.decode(rows[i], encs[i], base_P[i], unk_ids)]
        out.append(frames)
    return out


def triples_of_row(parses_row, text, chspans) -> list[tuple[str, str, str]]:
    """Ungated triples from a row's frames, duplicates dropped, order kept."""
    out = []
    for p in parses_row:
        wt = R106.r2_triple_of(p["frame"], text, chspans)
        if wt is not None and wt not in out:
            out.append(wt)
    return out


def score_panel_multi(runs: Path, taus: dict, snapshot: str, out: Path,
                      device, panel_path: Path, panel_tag: str,
                      K: int, FLOOR: float) -> dict:
    panel = [json.loads(l) for l in panel_path.read_text(
        encoding="utf-8").splitlines()]
    assert len(panel) == 400, f"{panel_tag}: {len(panel)} sentences != 400"
    gold_sets = [R106.gold_set(r) for r in panel]
    n_gold = sum(len(g) for g in gold_sets)
    occ_gold_idx = {i: {t for t in gold_sets[i] if t[0] == "occupation"}
                    for i in range(len(panel))}
    n_occ = sum(len(v) for v in occ_gold_idx.values())
    enc0, tok, _ = ENC.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    text_rows = [{"text": r["sentence"],
                  "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None,
                             "obj": None, "dir": 0, "rep": False}}
                 for r in panel]
    encs = [D.encode_row(r, tok) for r in text_rows]
    assert all(e is not None for e in encs)

    def score_k(parses_all, tau_map, label: str) -> dict:
        rep = {}
        for s in SEEDS:
            tau_op = float(tau_map["seeds"][str(s)]["tau_exec_single"])
            parses = parses_all[s]
            emitted = exact = occ = 0
            for i in range(len(panel)):
                for wt in triples_of_row(parses[i], text_rows[i]["text"],
                                         encs[i]["chspans"]):
                    emitted += 1
                    if wt in gold_sets[i]:
                        exact += 1
                        if wt in occ_gold_idx[i]:
                            occ += 1
            writes = wrong = correct = 0
            for i in range(len(panel)):
                seen_w = set()
                for p in parses[i]:
                    v, fr = S47.verdict_single(p, tau_op)
                    if v != "EXECUTE" or fr is None:
                        continue
                    wt = R106.r2_triple_of(fr, text_rows[i]["text"],
                                           encs[i]["chspans"])
                    if wt is None or wt in seen_w:
                        continue
                    seen_w.add(wt)
                    writes += 1
                    if wt in gold_sets[i]:
                        correct += 1
                    else:
                        wrong += 1
            rate = (wrong / writes) if writes else None
            prec = (exact / emitted) if emitted else None
            rep[str(s)] = {
                "seed": s, "tau_op": tau_op, "emitted": emitted,
                "raw_exact": exact, "precision": prec,
                "occ_exact": occ, "occ_gold": n_occ,
                "nonocc_exact": exact - occ,
                "W2_writes": writes, "W2_wrong": wrong,
                "W2_correct": correct, "W2_wrong_rate": rate}
            print(f"[{panel_tag} {label}] seed {s}: exact={exact} "
                  f"emitted={emitted} prec={prec} occ={occ}/{n_occ} "
                  f"W2={correct}c/{wrong}w/{writes}t rate={rate}")
        return rep

    parses_k1, parses_kc = {}, {}
    for s in SEEDS:
        model, _ = load_model_g(runs, s, snapshot, device)
        parses_k1[s] = decode_all_k1(model, text_rows, encs, device, unk_ids)
        parses_kc[s] = decode_all_multi(model, text_rows, encs, device,
                                        unk_ids, K, FLOOR)
        del model
    rep = {"panel": panel_tag, "sentences": len(panel),
           "n_gold_triples": n_gold, "n_occ_gold": n_occ, "K": K,
           "FLOOR": FLOOR,
           "K1": score_k(parses_k1, taus, "K=1"),
           "Kchosen": score_k(parses_kc, taus, f"K={K}")}
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    return rep


def score47g(runs: Path, panels47: Path, snapshot: str, out: Path,
             taus_out: Path, device, K: int, FLOOR: float) -> dict:
    """119e score47e logic with the 119g loader (K=1 old decode, remapped
    golds, unchanged 47 tau rule on CAL only). Gate47 reported, not gating.
    Plus a descriptive CAL multi-emission histogram at K=chosen."""
    import fable_ears47_encoder as ENC2
    import fable_ears47_data as D2
    enc0, tok, _ = ENC2.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    panels, encs = {}, {}
    for name in S119.PANELS47:
        rows = json.loads((panels47 / f"{name}.json").read_text(encoding="utf-8"))
        panels[name] = rows
        encs[name] = [D2.encode_row(r, tok) for r in rows]
    parses = {}
    for s in SEEDS:
        model, _ = load_model_g(runs, s, snapshot, device)
        parses[s] = {name: decode_all_k1(model, panels[name], encs[name],
                                         device, unk_ids)
                     for name in S119.PANELS47}
        del model
    golds = {name: [E119.remap_gold_frame(S47.gold_frame_of(e))
                    if e is not None else None for e in encs[name]]
             for name in S119.PANELS47}
    n_remap_cal = sum(1 for e in encs["cal"]
                      if S47.gold_frame_of(e) is not None
                      and S47.gold_frame_of(e).get("rel") in E119.REMAP)
    assert n_remap_cal == 346, f"CAL remapped golds {n_remap_cal} != 346"

    tau0_ens = S47.tau0_from_cal(
        golds["cal"], [parses[s]["cal"] for s in SEEDS], ensemble=True)
    tau_ens = 1 - (1 - tau0_ens) / 2
    tau_single = {}
    for s in SEEDS:
        t0 = S47.tau0_from_cal(golds["cal"], [parses[s]["cal"]], ensemble=False)
        tau_single[s] = 1 - (1 - t0) / 2
    taus = {"tau0_ens": tau0_ens, "tau_exec_ens": tau_ens,
            "seeds": {str(s): {"tau0": S47.tau0_from_cal(
                golds["cal"], [parses[s]["cal"]], ensemble=False),
                "tau_exec_single": tau_single[s]} for s in SEEDS}}
    taus_out.write_text(json.dumps(taus, indent=1), encoding="utf-8")

    ens = {name: S47.score_panel(
        panels[name], encs[name], [parses[s][name] for s in SEEDS],
        tau_ens, golds[name], ensemble=True) for name in S119.PANELS47}
    import math as _m
    need_exec_seen = S119.executable_state_n(panels["t_seen"])
    assert need_exec_seen == 654, f"executable SEEN rows {need_exec_seen} != 654"
    marks = {
        "SAFE": ens["t_seen"]["silent_wrong_write"]
        + ens["t_new"]["silent_wrong_write"]
        + ens["t_trap"]["silent_wrong_write"]
        + ens["t_hard"]["silent_wrong_write"] == 0,
        "NEG": ens["wneg"]["written"] / 2092 <= 0.02,
        "SEEN_correct": ens["t_seen"]["correct"] >= 1940,
        "SEEN_exec": sum(1 for k, r in enumerate(panels["t_seen"])
                         if S47.verdict_ensemble(
                             [parses[s]["t_seen"][k] for s in SEEDS],
                             tau_ens)[0] == "EXECUTE"
                         and r["gold47"]["act"] == "STATE"
                         and r["gold47"].get("rel") not in ("OPEN", "UNSURE"))
        >= _m.ceil(0.90 * need_exec_seen),
        "NEW_correct": ens["t_new"]["correct"] >= 2400,
        "NEW_exec": ens["t_new"]["exec_state_gold"] >= 784,
        "NAMES": ens["t_hard"]["correct"] >= 300,
        "ASK": ens["t_seen"]["wrong_exec_ask"]
        + ens["t_new"]["wrong_exec_ask"] <= 25,
        "WEB_exec": ens["wclosed"]["executed"] >= 28,
        "WEB_exact": (ens["wclosed"]["exec_correct"] / ens["wclosed"]["executed"]
                      >= 0.85) if ens["wclosed"]["executed"] else False,
        "NEWREL": sum(1 for k, r in enumerate(panels["wnewrel"])
                      if (lambda vv: vv[0] == "EXECUTE" and vv[1] is not None
                          and vv[1].get("rel") not in ("OPEN", "UNSURE", None))(
                          S47.verdict_ensemble(
                              [parses[s]["wnewrel"][k] for s in SEEDS],
                              tau_ens))) / 1500 <= 0.01,
    }
    w1 = {"executed": ens["wclosed"]["executed"],
          "silent": ens["wclosed"]["silent_wrong_write"],
          "pass": ens["wclosed"]["executed"] >= 23
          and ens["wclosed"]["silent_wrong_write"] == 0}
    gate47 = all(marks[k] for k in ("SAFE", "NEG", "SEEN_correct", "SEEN_exec",
                                    "NEW_correct", "NEW_exec", "NAMES", "ASK",
                                    "WEB_exec", "WEB_exact", "NEWREL"))
    # Descriptive only: CAL multi-emission at K=chosen (never tuned on).
    cal_multi = {}
    for s in SEEDS:
        model, _ = load_model_g(runs, s, snapshot, device)
        mp = decode_all_multi(model, panels["cal"], encs["cal"], device,
                              unk_ids, K, FLOOR)
        del model
        hist = {}
        for row_p in mp:
            n_fr = len(row_p)
            hist[n_fr] = hist.get(n_fr, 0) + 1
        cal_multi[str(s)] = {"n_frames_hist": hist, "n_rows": len(mp)}
    rep = {"taus": taus, "marks47_reported": marks, "gate47_reported": gate47,
           "W1_reported": w1, "K": K, "FLOOR": FLOOR,
           "cal_multi_emission_descriptive": cal_multi,
           "ens_correct": {n: ens[n]["correct"] for n in S119.PANELS47},
           "ens_executed": {n: ens[n]["executed"] for n in S119.PANELS47}}
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print(json.dumps({"gate47_reported": gate47, "W1": w1,
                      "cal_multi": cal_multi}, indent=1))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step0", action="store_true")
    ap.add_argument("--score47g", action="store_true")
    ap.add_argument("--score-panel", action="store_true")
    ap.add_argument("--runs", default=None)
    ap.add_argument("--runs119f", default=None)
    ap.add_argument("--taus119f", default=None)
    ap.add_argument("--panels47", default=None)
    ap.add_argument("--taus", default=None)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--taus-out", default=None)
    ap.add_argument("--panel", default=None)
    ap.add_argument("--panel94b", default=None)
    ap.add_argument("--panel-tag", default="94b")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--floor", type=float, default=0.10)
    a = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if a.step0:
        assert a.runs119f and a.taus119f and a.panel94b, \
            "--step0 needs --runs119f --taus119f --panel94b"
        taus = json.loads(Path(a.taus119f).read_text(encoding="utf-8"))
        rep = score_panel_multi(Path(a.runs119f), taus, a.snapshot,
                                Path(a.out), device, Path(a.panel94b),
                                "94b-step0-K1", 1, 0.0)
        rep["note"] = ("119f-checkpoint baseline, K=1 old decode; "
                       "M3 baseline = K1 precision per seed")
        Path(a.out).write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                               encoding="utf-8")
    elif a.score47g:
        assert a.runs and a.panels47 and a.taus_out, \
            "--score47g needs --runs --panels47 --taus-out"
        score47g(Path(a.runs), Path(a.panels47), a.snapshot, Path(a.out),
                 Path(a.taus_out), device, a.k, a.floor)
    elif a.score_panel:
        assert a.runs and a.taus and a.panel, \
            "--score-panel needs --runs --taus --panel"
        taus = json.loads(Path(a.taus).read_text(encoding="utf-8"))
        score_panel_multi(Path(a.runs), taus, a.snapshot, Path(a.out),
                          device, Path(a.panel), a.panel_tag, a.k, a.floor)
    else:
        raise SystemExit("need --step0, --score47g, or --score-panel")


if __name__ == "__main__":
    main()
