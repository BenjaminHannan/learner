#!/usr/bin/env python3
"""Exp 213 — EARS WRITE SAFETY MAP + GATE RESCORE (Muse BUILD, scorer side only).

No training. Verdict/decode code is reused VERBATIM by import (S47.decode,
S47.verdict_single, G119 K=1 decode + RelCondEars loader, E119 remap, L64
tail/CP bound); Part A adds a write layer on top, Part B a Learn-then-Test
gate on the rendered item.

Modes:
    --probe CASES --out OUT        A1: table render on fictional probe cases
                                   (pure function, no model/torch needed).
    --smoke --snapshot S --out OUT Mac CPU pilot: random-init RelCondEars +
                                   real encoder, 20 self-built rows (NOT cal).
    --wave (GPU, director-run)     full registered wave for one model, with
      --model {119g,119h} --runs R --snapshot S --panels47 P --panel94 A
      --panel94b B --taus-old O --expect47 E --taus-out T --out RPT
      Phase 1 (A2): recompute 47-rule taus + per-panel verdict counts,
                    compare EXACTLY to the sealed report (E).
      Phase 2 (Part B cal): per-seed LTT taus for alpha in {0.01,0.02,0.05}
                    (one-sided 95% CP bound on the rendered-item wrong-write
                    rate), sealed to T BEFORE any test panel is opened
                    (enforced in-process: test loaders assert the seal flag).
      Phase 3: score t_seen / t_new / reading94 / reading94b at the sealed
                    taus AND the old tau side by side (executed / correct /
                    wrong on the rendered item, per seed, per alpha).
                    Reading panels: aggregate counts ONLY, no sentence text.

Additive only: everything else imported read-only, never edited.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears213_relmap as R213  # noqa: E402 (light: no torch)

SEEDS = (11911, 11912, 11913)
ALPHAS = (0.01, 0.02, 0.05)
DELTA = 0.05          # one-sided 95% Clopper-Pearson bound
PANELS47 = ("cal", "t_seen", "t_new", "t_far", "t_trap", "t_hard",
            "wneg", "wpos", "wclosed", "wnewrel")
TEST47 = ("t_seen", "t_new")

_TAU_SEALED = {"done": False}


# ------------------------------------------------------------------ A1 probe
def run_probe(cases_path: Path) -> dict:
    import fable_ears47_data as D
    import fable_ears47_score as S47
    import fable_listening_english as LE
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    assert len(cases) >= 40, f"probe needs >=40 cases, got {len(cases)}"
    rows, invented = [], 0
    old_wrong = 0
    for c in cases:
        sent = c["sentence"]
        chspans = [(i, i + 1) for i in range(len(sent))]  # char-level spans
        si = sent.find(c["subj"])
        assert si >= 0, f"subj not found: {c['id']}"
        subj = (si, si + len(c["subj"]) - 1)
        obj = None
        if c.get("obj"):
            oi = sent.find(c["obj"])
            assert oi >= 0, f"obj not found: {c['id']}"
            obj = (oi, oi + len(c["obj"]) - 1)
        frame = {"act": c.get("act", "STATE"), "rel": c["class"],
                 "subj": subj, "obj": obj, "dir": D.DIR_FORWARD}
        got = R213.render(frame, sent, chspans)
        exp = c["expected"]
        if exp is None:
            ok = got is None
            got_rel = None
        else:
            ok = (got is not None and (got["relation_path"] or [None])[0] == exp)
            got_rel = (got["relation_path"] or [None])[0] if got else None
            if got_rel is not None and got_rel not in R213.NOTEBOOK_RELATIONS:
                invented += 1
                ok = False
        # descriptive: what the OLD content-word fallback would have emitted
        old_rel = LE.canonical_relation(S47.pick_surface(c["class"], sent))
        if old_rel != exp or (old_rel not in R213.NOTEBOOK_RELATIONS
                              and exp is not None):
            old_wrong += 1
        rows.append({"id": c["id"], "expected": exp, "got": got_rel,
                     "pass": ok, "old_fallback_relation": old_rel})
    n_pass = sum(1 for r in rows if r["pass"])
    return {"n": len(rows), "pass": n_pass, "invented": invented,
            "mark_A1_pass": bool(n_pass == len(rows) and invented == 0),
            "old_fallback_wrong_descriptive": old_wrong, "rows": rows}


# ------------------------------------------------- shared LTT (Part B cal)
def ltt_taus(eligible: list[tuple[float, bool]]) -> dict:
    """Per-seed fixed-sequence LTT, most-conservative tau first, per alpha.

    Grid (L76-style, label-free): G=15 target acceptance counts linspace
    (M_MIN(alpha), N), tau_j = the m_j-th largest eligible confidence, most
    conservative first; ties only raise m. M_MIN(alpha) = the zero-error
    certifiable mass ceil(ln(DELTA)/ln(1-alpha)) (L64 L2 arithmetic), so the
    first hypothesis can accept; N < M_MIN -> ABSTAIN-ALL. Tests use the
    exact binomial tail at level DELTA with the CP-bound duality assert
    (L64). tau_hat = last accepted = smallest certifiable tau.
    eligible: (conf, wrong) for label-free-eligible rows."""
    import math
    import numpy as np
    import fable_abstain64_ltt as L64
    G = 15
    confs = sorted((c for c, _ in eligible), reverse=True)
    N = len(confs)
    out = {}
    for alpha in ALPHAS:
        m_min = math.ceil(math.log(DELTA) / math.log1p(-alpha))
        if N < m_min:
            out[str(alpha)] = {"tau_hat": None, "m": 0, "k": 0,
                               "bound": 1.0, "n_grid": 0, "m_min": m_min,
                               "n_eligible": N}
            continue
        counts = sorted({int(round(v)) for v in
                         np.linspace(m_min, N, G)})
        counts = [c for c in counts if m_min <= c <= N]
        grid: list[float] = []
        for mj in counts:
            t = confs[mj - 1]
            if not grid or t != grid[-1]:
                grid.append(t)
        last, detail = None, []
        for tau in grid:
            m = sum(1 for c, _ in eligible if c >= tau)
            k = sum(1 for c, w in eligible if c >= tau and w)
            assert m >= 1
            p = L64.binom_tail(k, m, alpha)
            b = L64.cp_upper(k, m, DELTA)
            accept = bool(p <= DELTA)
            assert accept == bool(b <= alpha + 1e-12), \
                f"tail/CP duality violated at tau={tau}: p={p} b={b}"
            detail.append({"tau": tau, "m": m, "k": k, "p": p,
                           "bound": b, "accept": accept})
            if accept:
                last = tau
            else:
                break
        tail = [d for d in detail if d["accept"]][-1] if last is not None \
            else None
        out[str(alpha)] = {"tau_hat": last,
                           "m": tail["m"] if tail else 0,
                           "k": tail["k"] if tail else 0,
                           "bound": tail["bound"] if tail else 1.0,
                           "n_grid": len(grid), "m_min": m_min,
                           "n_eligible": N, "detail": detail}
    return out


def cal_eligible_and_labels(rows, encs, parses) -> list[tuple[float, bool]]:
    """Label-free eligibility first (verdict path only), labels after.
    eligible = EXECUTE verdict at tau 0 (ok4&ok5&not-forced) + STATE/RETRACT
    act + class in RELMAP. wrong = rendered item vs gold47 expectation."""
    import fable_ears47_score as S47
    elig: list[tuple[float, bool]] = []
    for i, row in enumerate(rows):
        p = parses[i]
        if p is None or encs[i] is None:
            continue
        v, fr = S47.verdict_single(p, 0.0)
        if v != "EXECUTE" or fr is None:
            continue
        if fr.get("act") not in R213.WRITE_ACTS:
            continue
        if fr.get("rel") not in R213.RELMAP:
            continue                      # ECHO-only: never executed
        rendered = R213.render(fr, D_row_text(row), encs[i]["chspans"])
        expected = R213.expected_from_gold47(row)
        wrong = not R213.judge(rendered, expected)
        elig.append((float(p["conf"]), wrong))
    return elig


def D_row_text(row):
    import fable_ears47_data as D
    return D.row_text(row)


# --------------------------------------------------------------- Mac smoke
SMOKE_ROWS = [
    # (text, subj, obj, act, rel, rep) — all fictional, self-built (NOT cal)
    ("Aldric Venmore lives in Oslo.", "Aldric Venmore", "Oslo", "STATE",
     "residence", True),
    ("Sella Marwick is a Norvish pianist.", "Sella Marwick", "pianist",
     "STATE", "occupation", True),
    ("Maelis Thornton was born on 3 April 1968.", "Maelis Thornton",
     "3 April 1968", "STATE", "date of birth", True),
    ("Osric Dall died on 19 November 2019.", "Osric Dall",
     "19 November 2019", "STATE", "date of death", True),
    ("Quillan Abernathy's place of birth is Bergen.", "Quillan Abernathy",
     "Bergen", "STATE", "place of birth", True),
    ("Bramwell Okafor's father is Tomas Okafor.", "Bramwell Okafor",
     "Tomas Okafor", "STATE", "father", True),
    ("Tilda Fernsby works for Halden Mills.", "Tilda Fernsby",
     "Halden Mills", "STATE", "employer", True),
    ("Milo Fernsby is 7 years old.", "Milo Fernsby", "7", "STATE",
     "age", True),
    ("Sella Marwick is a Norvish citizen.", "Sella Marwick", "Norvish",
     "STATE", "country of citizenship", True),
    ("Bramwell Okafor's spouse is Elena Okafor.", "Bramwell Okafor",
     "Elena Okafor", "STATE", "spouse", True),
    ("Osric Dall created the Meridian Engine.", "Osric Dall",
     "the Meridian Engine", "STATE", "creator", True),
    ("Bergen is the capital of Norvay.", "Bergen", "Norvay", "STATE",
     "capital of", True),
    ("Petra Lund's friend is Sella Marwick.", "Petra Lund", "Sella Marwick",
     "STATE", "friend", True),
    ("Tilda Fernsby's sibling is Jonas Fernsby.", "Tilda Fernsby",
     "Jonas Fernsby", "STATE", "sibling", True),
    ("Maelis Thornton is 34 years old.", "Maelis Thornton", "34", "STATE",
     "age", True),
    ("Quillan Abernathy plays for the Northern Stars.", "Quillan Abernathy",
     "the Northern Stars", "STATE", "member of sports team", True),
    ("Forget where Sella Marwick lives.", "Sella Marwick", None, "RETRACT",
     "residence", True),
    ("Forget what Osric Dall created.", "Osric Dall", None, "RETRACT",
     "creator", True),
    ("Where does Aldric Venmore live?", "Aldric Venmore", None, "ASK",
     "residence", True),
    ("Zorblatt quix flarn.", None, None, "UNSURE", "UNSURE", False),
]


def run_smoke(snapshot: str) -> dict:
    import torch
    import fable_ears47_data as D
    import fable_ears47_encoder as ENC
    import fable_ears47_score as S47
    import fable_ears119g_model as M119g
    device = torch.device("cpu")
    torch.manual_seed(213)
    enc0, tok, _ = ENC.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    rows = []
    for t, s, o, act, rel, rep in SMOKE_ROWS:
        g = {"act": act, "rel": rel, "subj": None, "obj": None,
             "dir": D.DIR_FORWARD, "rep": rep}
        if s:
            i = t.find(s)
            assert i >= 0, s
            g["subj"] = [i, i + len(s)]
        if o:
            i = t.find(o)
            assert i >= 0, o
            g["obj"] = [i, i + len(o)]
        rows.append({"text": t, "gold47": g})
    encs = [D.encode_row(r, tok) for r in rows]
    assert sum(e is not None for e in encs) >= 18, "too many unencodable"
    enc, _, _ = ENC.load(snapshot)   # fresh encoder for the random head
    model = M119g.RelCondEars(enc, D.N_REL).eval().to(device)
    P = S47.probs_for_model(model, encs, device)
    parses = [S47.decode(rows[i], encs[i], P[i], unk_ids)
              for i in range(len(rows))]
    rendered_rels = set()
    exec_old = 0
    for i, row in enumerate(rows):
        if encs[i] is None or P[i] is None:
            continue
        v, fr = S47.verdict_single(parses[i], 0.5)
        r = R213.render(fr, D.row_text(row), encs[i]["chspans"])
        if r is not None:
            rendered_rels.add((r["relation_path"] or [None])[0])
        if v == "EXECUTE" and r is not None:
            exec_old += 1
    assert rendered_rels <= R213.NOTEBOOK_RELATIONS, rendered_rels
    elig = cal_eligible_and_labels(rows, encs, parses)
    taus = ltt_taus(elig)
    # synthetic LTT check: exercises the non-empty fixed sequence path
    # (the random-init model abstains, so real eligible is empty here).
    synth = [(0.50 + 0.50 * i / 400, False) for i in range(400)]
    synth[10] = (synth[10][0], True)   # one wrong at low conf
    staus = ltt_taus(synth)
    for al in ("0.01", "0.02", "0.05"):
        assert staus[al]["tau_hat"] is not None, al
        assert staus[al]["bound"] <= float(al) + 1e-12, (al, staus[al])
    return {"n": len(rows), "encodable": sum(e is not None for e in encs),
            "eligible": len(elig),
            "rendered_relations": sorted(rendered_rels),
            "exec_at_0.5": exec_old, "ltt": taus,
            "synth_ltt_taus": {al: staus[al]["tau_hat"] for al in staus},
            "smoke_ok": True}


# --------------------------------------------------------------- GPU wave
def load_model(runs: Path, seed: int, snapshot: str, device):
    import fable_ears119g_score as G119
    return G119.load_model_g(runs, seed, snapshot, device)


def decode_k1(model, rows, encs, device, unk_ids):
    import fable_ears47_score as S47
    P = S47.probs_for_model(model, encs, device)
    return [S47.decode(rows[i], encs[i], P[i], unk_ids)
            for i in range(len(rows))]


def phase_a2(models, panels47: Path, snapshot: str, device,
             taus_old: dict, expect: dict) -> dict:
    """Recompute 47-rule taus + verdict counts (remapped golds, verbatim
    decode) and compare EXACTLY to the sealed report."""
    import fable_ears47_data as D
    import fable_ears47_encoder as ENC
    import fable_ears47_score as S47
    import fable_ears119e_score as E119
    enc0, tok, _ = ENC.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    panels, encs = {}, {}
    for name in PANELS47:
        rows = json.loads((panels47 / f"{name}.json").read_text(
            encoding="utf-8"))
        panels[name] = rows
        encs[name] = [D.encode_row(r, tok) for r in rows]
    parses = {}
    for s in SEEDS:
        parses[s] = {n: decode_k1(models[s], panels[n], encs[n], device,
                                  unk_ids) for n in PANELS47}
    golds = {n: [E119.remap_gold_frame(S47.gold_frame_of(e))
                 if e is not None else None for e in encs[n]]
             for n in PANELS47}
    tau0_ens = S47.tau0_from_cal(
        golds["cal"], [parses[s]["cal"] for s in SEEDS], ensemble=True)
    tau_ens = 1 - (1 - tau0_ens) / 2
    tau_single = {}
    for s in SEEDS:
        t0 = S47.tau0_from_cal(golds["cal"], [parses[s]["cal"]],
                               ensemble=False)
        tau_single[s] = 1 - (1 - t0) / 2
    taus_equal = (
        tau0_ens == taus_old["tau0_ens"]
        and tau_ens == taus_old["tau_exec_ens"]
        and all(tau_single[s] == taus_old["seeds"][str(s)]["tau_exec_single"]
                for s in SEEDS))
    panels_cmp, all_eq = {}, True
    for n in PANELS47:
        sc = S47.score_panel(panels[n], encs[n],
                             [parses[s][n] for s in SEEDS], tau_ens,
                             golds[n], ensemble=True)
        ce = sc["correct"] == expect["ens_correct"][n]
        ee = sc["executed"] == expect["ens_executed"][n]
        panels_cmp[n] = {"correct": sc["correct"],
                         "sealed_correct": expect["ens_correct"][n],
                         "executed": sc["executed"],
                         "sealed_executed": expect["ens_executed"][n],
                         "equal": bool(ce and ee)}
        all_eq &= bool(ce and ee)
    # descriptive: rendered-item wrong writes among old-tau EXECUTEs on cal
    cal_wrong = {}
    for s in SEEDS:
        ex = wr = 0
        for i, row in enumerate(panels["cal"]):
            if encs["cal"][i] is None:
                continue
            v, fr = S47.verdict_single(parses[s]["cal"][i], tau_single[s])
            if v != "EXECUTE" or fr is None:
                continue
            r = R213.render(fr, D.row_text(row), encs["cal"][i]["chspans"])
            if r is None:
                continue                    # ECHO-only: not a write
            ex += 1
            if not R213.judge(r, R213.expected_from_gold47(row)):
                wr += 1
        cal_wrong[str(s)] = {"executed_rendered": ex, "wrong": wr}
    return {"taus_equal": bool(taus_equal),
            "tau0_ens": tau0_ens, "tau_exec_ens": tau_ens,
            "tau_single": {str(s): tau_single[s] for s in SEEDS},
            "panels": panels_cmp,
            "mark_A2_pass": bool(taus_equal and all_eq),
            "cal_rendered_wrong_at_old_tau_descriptive": cal_wrong,
            "_cache": (panels, encs, parses)}


def phase_test(models, cache, panels47: Path, p94: Path, p94b: Path,
               taus213: dict, taus_old: dict, device, snapshot: str) -> dict:
    assert _TAU_SEALED["done"], "test panels opened before tau seal"
    import fable_ears47_data as D
    import fable_ears47_encoder as ENC
    import fable_ears47_score as S47
    import fable_read106_score as R106
    panels, encs, parses = cache
    out: dict = {}
    # chat-style panels (gold47 available; per-row records WITHOUT utterances)
    for name in TEST47:
        out[name] = {}
        for s in SEEDS:
            old_tau = float(taus_old["seeds"][str(s)]["tau_exec_single"])
            arms = {a: taus213[str(s)][a]["tau_hat"] for a in
                    ("0.01", "0.02", "0.05")}
            arms["old"] = old_tau
            out[name][str(s)] = {}
            for key, tau in arms.items():
                ex = co = wr = un = 0
                for i, row in enumerate(panels[name]):
                    if encs[name][i] is None:
                        un += 1
                        continue
                    if tau is None:
                        continue      # ABSTAIN-ALL: nothing executes
                    v, fr = S47.verdict_single(parses[s][name][i], tau)
                    if v != "EXECUTE" or fr is None:
                        continue
                    r = R213.render(fr, D.row_text(row),
                                    encs[name][i]["chspans"])
                    if r is None:
                        continue
                    ex += 1
                    if R213.judge(r, R213.expected_from_gold47(row)):
                        co += 1
                    else:
                        wr += 1
                out[name][str(s)][key] = {"executed": ex, "correct": co,
                                          "wrong": wr, "unscorable": un}
    # reading panels: aggregate counts ONLY (never sentences, never spans)
    enc0, tok, _ = ENC.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    for tag, path in (("reading94", p94), ("reading94b", p94b)):
        rpows = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines()]
        gold_sets = [R106.gold_set(r) for r in rpows]
        text_rows = [{"text": r["sentence"],
                      "gold47": {"act": "NO_FACT", "rel": "UNSURE",
                                 "subj": None, "obj": None, "dir": 0,
                                 "rep": False}} for r in rpows]
        rencs = [D.encode_row(r, tok) for r in text_rows]
        assert all(e is not None for e in rencs), f"{tag}: unencodable row"
        out[tag] = {}
        for s in SEEDS:
            pp = decode_k1(models[s], text_rows, rencs, device, unk_ids)
            old_tau = float(taus_old["seeds"][str(s)]["tau_exec_single"])
            arms = {a: taus213[str(s)][a]["tau_hat"] for a in
                    ("0.01", "0.02", "0.05")}
            arms["old"] = old_tau
            out[tag][str(s)] = {}
            for key, tau in arms.items():
                ex = co = wr = 0
                for i in range(len(rpows)):
                    if tau is None:
                        continue
                    v, fr = S47.verdict_single(pp[i], tau)
                    if v != "EXECUTE" or fr is None:
                        continue
                    # rendered triple only; compared, never stored/printed
                    r = R213.render(fr, text_rows[i]["text"],
                                    rencs[i]["chspans"])
                    if r is None:
                        continue
                    ex += 1
                    if R213.judge_against_reading_gold(r, gold_sets[i]):
                        co += 1
                    else:
                        wr += 1
                out[tag][str(s)][key] = {"executed": ex, "correct": co,
                                         "wrong": wr}
        del rpows, gold_sets, text_rows, rencs
    return out


def run_wave(model_tag: str, runs: Path, snapshot: str, panels47: Path,
             p94: Path, p94b: Path, taus_old_p: Path, expect_p: Path,
             taus_out: Path, out_p: Path) -> dict:
    import torch
    import fable_ears47_encoder as ENC
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    taus_old = json.loads(taus_old_p.read_text(encoding="utf-8"))
    expect = json.loads(expect_p.read_text(encoding="utf-8"))
    enc0, tok, _ = ENC.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    models = {}
    for s in SEEDS:
        models[s], _ = load_model(runs, s, snapshot, device)
    a2 = phase_a2(models, panels47, snapshot, device, taus_old, expect)
    panels, encs, parses = a2.pop("_cache")
    # Part B cal-only LTT, per seed; sealed to file BEFORE test scoring
    taus213 = {}
    for s in SEEDS:
        elig = cal_eligible_and_labels(panels["cal"], encs["cal"],
                                       parses[s]["cal"])
        taus213[str(s)] = ltt_taus(elig)
    taus_out.write_text(json.dumps(taus213, indent=1), encoding="utf-8")
    _TAU_SEALED["done"] = True
    test = phase_test(models, (panels, encs, parses), panels47, p94, p94b,
                      taus213, taus_old, device, snapshot)
    for s in SEEDS:
        del models[s]
    rep = {"model": model_tag, "seeds": list(SEEDS),
           "alphas": list(ALPHAS), "delta": DELTA,
           "a2": a2, "taus213": taus213,
           "taus_old_single": {str(s): taus_old["seeds"][str(s)][
               "tau_exec_single"] for s in SEEDS},
           "test": test}
    out_p.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


# ---------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--wave", action="store_true")
    ap.add_argument("--model", default=None)
    ap.add_argument("--runs", default=None)
    ap.add_argument("--panels47", default=None)
    ap.add_argument("--panel94", default=None)
    ap.add_argument("--panel94b", default=None)
    ap.add_argument("--taus-old", default=None)
    ap.add_argument("--expect47", default=None)
    ap.add_argument("--taus-out", default=None)
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.probe:
        errs = R213.check_table()
        assert not errs, errs
        rep = run_probe(Path(a.probe))
        Path(a.out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
        print(json.dumps({k: v for k, v in rep.items() if k != "rows"},
                         indent=1))
        return
    if a.smoke:
        assert a.snapshot, "--smoke needs --snapshot"
        rep = run_smoke(a.snapshot)
        Path(a.out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
        print(json.dumps(rep, indent=1))
        return
    if a.wave:
        need = {"model": a.model, "runs": a.runs, "panels47": a.panels47,
                "panel94": a.panel94, "panel94b": a.panel94b,
                "taus-old": a.taus_old, "expect47": a.expect47,
                "taus-out": a.taus_out, "snapshot": a.snapshot}
        missing = [k for k, v in need.items() if not v]
        assert not missing, f"--wave needs {missing}"
        rep = run_wave(a.model, Path(a.runs), a.snapshot, Path(a.panels47),
                       Path(a.panel94), Path(a.panel94b), Path(a.taus_old),
                       Path(a.expect47), Path(a.taus_out), Path(a.out))
        print(json.dumps({"model": rep["model"],
                          "A2": rep["a2"]["mark_A2_pass"],
                          "taus213": {s: {al: v["tau_hat"]
                                          for al, v in d.items()
                                          if al in ("0.01", "0.02", "0.05")}
                                      for s, d in rep["taus213"].items()}},
                         indent=1))
        return
    raise SystemExit("need --probe, --smoke, or --wave")


if __name__ == "__main__":
    main()
