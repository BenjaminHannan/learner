"""Point 3: Fragility analysis of std_ok on THROWAWAY Crafter worlds ONLY (not dev, not sealed).

Generates 10 independent 16-world throwaway splits (world_id = 9000..9159, 100% disjoint from
legacy train 0..159, dev 1000..1015, sealed 2000..2015, and train_dn 3000..3079) using the exact
policy & 16x16 pooling of record_v5.py, kept purely in RAM.

Measures:
  1. For every action q in 0..16 (especially a=5, 6, 8, 9 and rare 0, 7..16):
     - How often the action is active (std_real >= 0.02) across 16-world draws
     - Exact count of sleep wake-ups (both ground-truth Crafter env._player.sleeping transitions
       split into energy-9 wakes vs hurt wakes, and purely visual wakes)
     - Genuine crafting-table / furnace placement counts
     - Top-1 event SSE share, wake-up SSE share, Kish n_eff = (sum e_i)^2 / sum(e_i^2)
  2. Exact leave-one-wake-out / miss-one-wake-up std_ratio variance on a=8, a=9, and all rare actions.
  3. False-FAIL rate of realistic 2-frame models & rejection rate of collapsed 0-wake models under:
     - Old ruler (scorer.py current)
     - Candidate amended rulers (pooling rare / low-n_eff actions)
  4. Separate check at end: saved Rank 6 (s42, s43) dev verdict under old vs candidate amended rulers
     (verifying action 5, n=733, still fails -> zero verdict flip).
"""
from __future__ import annotations

import os
import sys
import time
import crafter
import numpy as np

BASE = os.path.expanduser("~/learner-ops/seven-problems-m3/PROBLEM-7")
sys.path.insert(0, os.path.join(BASE, "wm6"))
import scorer

MOVES = (1, 2, 3, 4)
OTHER = tuple(a for a in range(17) if a not in MOVES and a != 5)
PER_WORLD = 350
MAX_EPISODE = 350
N_SPLITS = 10
WORLDS_PER_SPLIT = 16
START_WORLD = 9000  # Disjoint from 0..159, 1000..1015, 2000..2015, 3000..3079


def pool(o):
    return o.reshape(16, 4, 16, 4, 3).mean((1, 3)).astype(np.float64) / 255.0


def policy_step(rng):
    r = rng.random()
    if r < 0.50:
        return int(rng.integers(1, 5)), int(rng.integers(1, 5))
    if r < 0.75:
        return 5, 1
    return int(OTHER[rng.integers(len(OTHER))]), 1


def record_throwaway_split(worlds, rng):
    """Record 16 throwaway worlds in RAM with exact ground-truth sleep/wake & table/furnace flags."""
    frames, actions, eid, wid, tid = [], [], [], [], []
    # Per-transition ground-truth metadata
    gt_asleep_pre, gt_wake, gt_wake_e9, gt_wake_hurt = [], [], [], []
    gt_placed_table, gt_placed_furnace = [], []
    next_ep = 0
    for world in worlds:
        got, ep_idx = 0, 0
        while got < PER_WORLD:
            env = crafter.Env(seed=world * 1000 + ep_idx)
            obs = env.reset()
            ep_fr = [pool(obs)]
            ep_act = []
            budget = min(MAX_EPISODE, PER_WORLD - got)
            done = False
            while len(ep_act) < budget and not done:
                action, hold = policy_step(rng)
                for _ in range(hold):
                    if len(ep_act) >= budget:
                        break
                    pl = env._player
                    slp_pre = bool(pl.sleeping)
                    en_pre = int(pl.inventory.get("energy", 9))
                    hl_pre = int(pl.inventory.get("health", 9))
                    wd_pre = int(pl.inventory.get("wood", 0))
                    st_pre = int(pl.inventory.get("stone", 0))

                    obs, _, done, _ = env.step(action)

                    slp_post = bool(pl.sleeping)
                    hl_post = int(pl.inventory.get("health", 9))
                    wd_post = int(pl.inventory.get("wood", 0))
                    st_post = int(pl.inventory.get("stone", 0))

                    woke = slp_pre and (not slp_post)
                    woke_e9 = woke and (en_pre >= 9)
                    woke_hurt = woke and (not woke_e9) and (hl_post < hl_pre or en_pre < 9)
                    # Genuine table placement (a=8 consumes 2 wood while awake)
                    p_tab = (action == 8) and (not slp_pre) and (wd_post == wd_pre - 2)
                    # Genuine furnace placement (a=9 consumes 4 stone while awake)
                    p_fur = (action == 9) and (not slp_pre) and (st_post == st_pre - 4)

                    ep_fr.append(pool(obs))
                    ep_act.append(action)
                    gt_asleep_pre.append(slp_pre)
                    gt_wake.append(woke)
                    gt_wake_e9.append(woke_e9)
                    gt_wake_hurt.append(woke_hurt)
                    gt_placed_table.append(p_tab)
                    gt_placed_furnace.append(p_fur)
                    if done:
                        break
            n = len(ep_act)
            frames.append(np.stack(ep_fr).astype(np.float16))
            actions.append(np.asarray(ep_act, dtype=np.int64))
            eid.append(np.full(n + 1, next_ep, dtype=np.int64))
            wid.append(np.full(n + 1, world, dtype=np.int64))
            tid.append(np.arange(n + 1, dtype=np.int64))
            got += n
            next_ep += 1
            ep_idx += 1
    return {
        "frames": np.concatenate(frames),
        "actions": np.concatenate(actions),
        "episode_id": np.concatenate(eid),
        "world_id": np.concatenate(wid),
        "t_index": np.concatenate(tid),
        "gt_asleep_pre": np.asarray(gt_asleep_pre, dtype=bool),
        "gt_wake": np.asarray(gt_wake, dtype=bool),
        "gt_wake_e9": np.asarray(gt_wake_e9, dtype=bool),
        "gt_wake_hurt": np.asarray(gt_wake_hurt, dtype=bool),
        "gt_placed_table": np.asarray(gt_placed_table, dtype=bool),
        "gt_placed_furnace": np.asarray(gt_placed_furnace, dtype=bool),
    }


def kish_neff(per_win_e: np.ndarray) -> float:
    s1 = float(per_win_e.sum())
    s2 = float((per_win_e ** 2).sum())
    if s2 <= 1e-30:
        return 0.0
    return (s1 * s1) / s2


def eval_std_rulers(dP: np.ndarray, dY: np.ndarray, a0: np.ndarray, active_thresh: float = 0.02):
    """Evaluate old ruler and candidate amended rulers on (dP, dY, a0) at k=1.
    dP, dY: [N, 768] float64.
    """
    per_win_e = (dY ** 2).mean(axis=1)  # [N]
    per_act = {}
    for q in range(17):
        sel = a0 == q
        cnt = int(sel.sum())
        if cnt < 20:
            continue
        sp = float(dP[sel].std())
        sr = float(dY[sel].std())
        ratio = 1.0 if (sr < 1e-12 and sp < 1e-12) else float(sp / (sr + 1e-12))
        e_q = per_win_e[sel]
        neff = kish_neff(e_q)
        top1 = float(e_q.max() / max(e_q.sum(), 1e-30))
        n_rms02 = int((np.sqrt(e_q) >= 0.02).sum())
        n_rms05 = int((np.sqrt(e_q) >= 0.05).sum())
        per_act[q] = {
            "n": cnt, "std_pred": sp, "std_real": sr, "ratio": ratio,
            "active": bool(sr >= active_thresh), "neff": neff, "top1": top1,
            "n_rms02": n_rms02, "n_rms05": n_rms05,
        }

    tot_n = sum(v["n"] for v in per_act.values())
    fw = float(sum(v["n"] * v["ratio"] for v in per_act.values()) / max(tot_n, 1))
    fw_ok = (0.25 <= fw <= 2.0)

    # Old ruler
    old_active = {q: v["ratio"] for q, v in per_act.items() if v["active"]}
    old_ok = bool(old_active and all(0.25 <= r <= 2.0 for r in old_active.values()) and fw_ok)

    # Candidate A(T): Individual gate for actions with n>=20, active, AND kish_neff >= T;
    # pool ALL other n>=20 actions with kish_neff < T into one 'rare_concentrated' bucket!
    def _neff_rule(T: float):
        indiv = {q: v["ratio"] for q, v in per_act.items() if v["active"] and v["neff"] >= T}
        pool_qs = [q for q, v in per_act.items() if v["neff"] < T]
        pool_ratio, pool_sr, pool_neff, pool_active = None, 0.0, 0.0, False
        if pool_qs:
            psel = np.isin(a0, pool_qs)
            sp = float(dP[psel].std())
            sr = float(dY[psel].std())
            pool_ratio = 1.0 if (sr < 1e-12 and sp < 1e-12) else float(sp / (sr + 1e-12))
            pool_sr = sr
            pool_neff = kish_neff(per_win_e[psel])
            pool_active = bool(sr >= active_thresh)
        ok = bool(
            indiv
            and all(0.25 <= r <= 2.0 for r in indiv.values())
            and ((not pool_active) or (0.25 <= pool_ratio <= 2.0))
            and fw_ok
        )
        return {
            "ok": ok, "indiv_qs": sorted(indiv.keys()), "indiv_fail": [q for q, r in indiv.items() if not (0.25 <= r <= 2.0)],
            "pool_qs": sorted(pool_qs), "pool_active": pool_active, "pool_sr": pool_sr,
            "pool_ratio": pool_ratio, "pool_neff": pool_neff,
        }

    # Candidate B(N_min, T_neff): Individual gate if active AND (n >= N_min OR neff >= T_neff);
    # pool all actions with (n < N_min AND neff < T_neff) into one rare_pooled bucket!
    def _count_or_neff_rule(n_min: int, T: float):
        indiv = {q: v["ratio"] for q, v in per_act.items() if v["active"] and (v["n"] >= n_min or v["neff"] >= T)}
        pool_qs = [q for q, v in per_act.items() if not (v["n"] >= n_min or v["neff"] >= T)]
        pool_ratio, pool_sr, pool_neff, pool_active = None, 0.0, 0.0, False
        if pool_qs:
            psel = np.isin(a0, pool_qs)
            sp = float(dP[psel].std())
            sr = float(dY[psel].std())
            pool_ratio = 1.0 if (sr < 1e-12 and sp < 1e-12) else float(sp / (sr + 1e-12))
            pool_sr = sr
            pool_neff = kish_neff(per_win_e[psel])
            pool_active = bool(sr >= active_thresh)
        ok = bool(
            indiv
            and all(0.25 <= r <= 2.0 for r in indiv.values())
            and ((not pool_active) or (0.25 <= pool_ratio <= 2.0))
            and fw_ok
        )
        return {
            "ok": ok, "indiv_qs": sorted(indiv.keys()), "indiv_fail": [q for q, r in indiv.items() if not (0.25 <= r <= 2.0)],
            "pool_qs": sorted(pool_qs), "pool_active": pool_active, "pool_sr": pool_sr,
            "pool_ratio": pool_ratio, "pool_neff": pool_neff,
        }

    return {
        "per_act": per_act,
        "fw": fw,
        "old": {"ok": old_ok, "active_qs": sorted(old_active.keys()),
                "fail_qs": [q for q, r in old_active.items() if not (0.25 <= r <= 2.0)]},
        "neff_8": _neff_rule(8.0),
        "neff_10": _neff_rule(10.0),
        "neff_15": _neff_rule(15.0),
        "n200_or_neff10": _count_or_neff_rule(200, 10.0),
    }


def main():
    t0 = time.time()
    rng = np.random.default_rng(99001)
    splits = []
    print(f"Generating {N_SPLITS} disjoint 16-world throwaway splits (worlds {START_WORLD}..{START_WORLD + N_SPLITS*WORLDS_PER_SPLIT - 1})...", flush=True)
    for s_idx in range(N_SPLITS):
        ws = list(range(START_WORLD + s_idx * WORLDS_PER_SPLIT, START_WORLD + (s_idx + 1) * WORLDS_PER_SPLIT))
        sp = record_throwaway_split(ws, rng)
        splits.append(sp)
        if (s_idx + 1) % 2 == 0:
            print(f"  split {s_idx+1}/{N_SPLITS} done ({time.time()-t0:.1f}s)", flush=True)

    print(f"\n=== 1. PER-ACTION ANATOMY ACROSS {N_SPLITS} THROWAWAY 16-WORLD SPLITS (5,600 trans/split) ===")
    hdr = (
        f"{'act':>3} | {'n_mean':>6} | {'act%':>5} | {'sr_min..max':>13} | "
        f"{'wk_cnt dist (0/1/2/3+)':>22} | {'wk_e9/hurt':>10} | {'wk_SSE%':>7} | "
        f"{'top1_SSE%':>9} | {'neff_med(min)':>13} | {'sr_noWk':>7}"
    )
    print(hdr)
    print("-" * len(hdr))

    # Collect per-split stats
    split_records = []
    for sp in splits:
        xi1, ai1, _, _, _ = scorer.windows(sp, 1)
        x0 = sp["frames"][xi1].astype(np.float64)
        x1 = sp["frames"][xi1 + 1].astype(np.float64)
        dY = (x1 - x0).reshape(len(xi1), -1)
        a0 = sp["actions"][ai1]
        per_e = (dY ** 2).mean(axis=1)
        split_records.append((dY, a0, per_e, sp["gt_wake"], sp["gt_wake_e9"], sp["gt_wake_hurt"], sp["gt_placed_table"], sp["gt_placed_furnace"]))

    for q in range(17):
        ns, srs, act_flags, wk_cnts, e9_cnts, hu_cnts, wk_shares, top1s, neffs, sr_nowks = [], [], [], [], [], [], [], [], [], []
        for dY, a0, per_e, wk, e9, hu, ptab, pfur in split_records:
            sel = a0 == q
            ns.append(int(sel.sum()))
            sr = float(dY[sel].std())
            srs.append(sr)
            act_flags.append(sr >= 0.02)
            w_q = wk[sel]
            wk_cnts.append(int(w_q.sum()))
            e9_cnts.append(int(e9[sel].sum()))
            hu_cnts.append(int(hu[sel].sum()))
            e_q = per_e[sel]
            tot_e = float(e_q.sum())
            wk_shares.append(float(e_q[w_q].sum() / max(tot_e, 1e-12)))
            top1s.append(float(e_q.max() / max(tot_e, 1e-12)))
            neffs.append(kish_neff(e_q))
            sr_nowks.append(float(dY[sel & (~wk)].std()) if (sel & (~wk)).any() else 0.0)
        d0 = sum(c == 0 for c in wk_cnts)
        d1 = sum(c == 1 for c in wk_cnts)
        d2 = sum(c == 2 for c in wk_cnts)
        d3 = sum(c >= 3 for c in wk_cnts)
        print(
            f"{q:3d} | {np.mean(ns):6.1f} | {100*np.mean(act_flags):4.0f}% | "
            f"{min(srs):.4f}..{max(srs):.4f} | {f'{d0}/{d1}/{d2}/{d3}':>22} | "
            f"{f'{sum(e9_cnts)}/{sum(hu_cnts)}':>10} | {100*np.mean(wk_shares):6.1f}% | "
            f"{100*np.mean(top1s):8.1f}% | {np.median(neffs):6.1f}({min(neffs):5.1f}) | {np.mean(sr_nowks):7.4f}"
        )

    # Genuine table & furnace placement counts across all 160 throwaway worlds!
    tot_tab = sum(int(r[6].sum()) for r in split_records)
    tot_fur = sum(int(r[7].sum()) for r in split_records)
    tab_per = [int(r[6].sum()) for r in split_records]
    fur_per = [int(r[7].sum()) for r in split_records]
    print(f"\nGenuine placements across {N_SPLITS}x16={N_SPLITS*16} throwaway worlds (56,000 trans):")
    print(f"  place_table (a=8): total={tot_tab}, per 16-world split={tab_per}")
    print(f"  place_furnace (a=9): total={tot_fur}, per 16-world split={fur_per}")

    # =========================================================================
    # 2. EXACT EVENT-BY-EVENT FRAGILITY OF ACTIONS 8 & 9 (AND ALL RARE 0,7..16)
    # =========================================================================
    print(f"\n=== 2. EXACT MISS-1-WAKE-UP FRAGILITY ON ACTIONS 8 & 9 ACROSS {N_SPLITS} THROWAWAY SPLITS ===")
    # Model a realistic 2-frame predictor:
    #   - On moves/sleep: predicts ~0.90 * true dY (std_ratio ~ 0.90)
    #   - On any wake-up it catches: predicts alpha_wk * true dY (e.g., alpha_wk = 0.70, matching 2-frame Ridge/NN amplitude)
    #   - Elsewhere on rare actions: predicts small background noise std = 0.0030 (matching saved Rank 6!)
    ALPHA_WK = 0.70
    BG_STD = 0.0030

    for q, qname in [(8, "place_table"), (9, "place_furnace"), (5, "do")]:
        print(f"\n  Action {q} ({qname}):")
        r_miss0_list, r_miss1_list, r_only_e9_list, r_nowk_list = [], [], [], []
        n_active_splits = 0
        for s_idx, (dY, a0, per_e, wk, e9, hu, ptab, pfur) in enumerate(split_records):
            sel = a0 == q
            sr = float(dY[sel].std())
            active = sr >= 0.02
            w_idx = np.flatnonzero(wk[sel])
            e9_idx = np.flatnonzero(e9[sel])
            hu_idx = np.flatnonzero(hu[sel])
            e_q = per_e[sel]
            n_q = int(sel.sum())
            neff = kish_neff(e_q)
            top1 = float(e_q.max() / max(e_q.sum(), 1e-12))

            # Helper: predicted std given subset of predicted wake indices (at amplitude ALPHA_WK) + background BG_STD
            def _pred_ratio(pred_w_mask):
                # Variance of dP over all (n_q * 768) entries:
                # predicted wake windows contribute (ALPHA_WK^2 * e_i), others contribute BG_STD^2
                var_i = np.where(pred_w_mask, (ALPHA_WK ** 2) * e_q, BG_STD ** 2)
                sp = float(np.sqrt(var_i.mean()))
                return sp / sr

            m_all_wk = wk[sel]
            m_e9_only = e9[sel]
            m_none = np.zeros(n_q, dtype=bool)
            r_all = _pred_ratio(m_all_wk)
            r_e9 = _pred_ratio(m_e9_only)
            r_none = _pred_ratio(m_none)

            # Worst-case miss-1-wake-up (drop the largest wake-up from m_all_wk)
            if len(w_idx) >= 1:
                m_miss1 = m_all_wk.copy()
                largest_w = w_idx[np.argmax(e_q[w_idx])]
                m_miss1[largest_w] = False
                r_miss1 = _pred_ratio(m_miss1)
            else:
                r_miss1 = r_all

            if active:
                n_active_splits += 1
                r_miss0_list.append(r_all)
                r_miss1_list.append(r_miss1)
                r_only_e9_list.append(r_e9)
                r_nowk_list.append(r_none)

            print(
                f"    split {s_idx}: n={n_q:3d} sr={sr:.4f} active={str(active):<5} "
                f"wk={len(w_idx)}(e9={len(e9_idx)},hurt={len(hu_idx)}) neff={neff:5.1f} top1={top1*100:4.1f}% | "
                f"r(all_wk@0.7)={r_all:.3f} r(e9_only@0.7)={r_e9:.3f} r(miss1_wk)={r_miss1:.3f} r(0_wk)={r_none:.3f}"
            )
        if n_active_splits:
            print(
                f"    SUMMARY (active in {n_active_splits}/{N_SPLITS} splits): "
                f"r(all_wk)={np.mean(r_miss0_list):.3f}±{np.std(r_miss0_list):.3f} (FAIL<0.25: {sum(r<0.25 for r in r_miss0_list)}/{n_active_splits}) | "
                f"r(e9_only)={np.mean(r_only_e9_list):.3f}±{np.std(r_only_e9_list):.3f} (FAIL<0.25: {sum(r<0.25 for r in r_only_e9_list)}/{n_active_splits}) | "
                f"r(miss1_wk)={np.mean(r_miss1_list):.3f}±{np.std(r_miss1_list):.3f} (FAIL<0.25: {sum(r<0.25 for r in r_miss1_list)}/{n_active_splits})"
            )

    # =========================================================================
    # 3. FULL 17-ACTION RULER COMPARISON ACROSS 10 THROWAWAY SPLITS
    # =========================================================================
    print(f"\n=== 3. FULL 17-ACTION std_ok FALSE-FAIL RATE (GOOD 2-FRAME MODEL) vs REJECTION RATE (COLLAPSED 0-WAKE MODEL) ===")
    # Test 4 synthetic predictor regimes across all 10 throwaway splits:
    #   (i)   2f_oracle_e9_only : perfect on moves/sleep (0.90), catches 100% of energy 8->9 wakes at 0.70 amp, misses hurt wakes (unobservable!)
    #   (ii)  2f_realistic_85   : same, plus 15% random miss on 8->9 wakes (averaged over 50 Monte Carlo draws/split = 500 draws!)
    #   (iii) 1f_bayes_like     : catches only 12.5% amplitude on e9 wakes (like saved Rank 6 1-frame) -> MUST FAIL!
    #   (iv)  collapsed_nowk    : moves/sleep good (0.90), all non-move/non-sleep shrunk to BG_STD=0.003 -> MUST FAIL!
    ruler_names = ["old", "neff_8", "neff_10", "neff_15", "n200_or_neff10"]

    def make_sim_dP(dY, a0, wk, e9, mode, rng_m):
        dP = rng_m.normal(0.0, BG_STD, size=dY.shape)
        mv_slp = np.isin(a0, [1, 2, 3, 4, 6])
        dP[mv_slp] = 0.90 * dY[mv_slp]
        if mode == "2f_oracle_e9":
            dP[e9] = ALPHA_WK * dY[e9]
        elif mode == "2f_realistic_85":
            catch = e9 & (rng_m.random(len(e9)) < 0.85)
            dP[catch] = ALPHA_WK * dY[catch]
        elif mode == "2f_realistic_80_amp60":
            catch = e9 & (rng_m.random(len(e9)) < 0.80)
            dP[catch] = 0.60 * dY[catch]
        elif mode == "1f_bayes_like":
            dP[e9] = 0.125 * dY[e9]
        elif mode == "collapsed_nowk":
            pass
        return dP

    for mode, n_mc in [
        ("2f_oracle_e9", 1),
        ("2f_realistic_85", 20),
        ("2f_realistic_80_amp60", 20),
        ("1f_bayes_like", 1),
        ("collapsed_nowk", 1),
    ]:
        rng_m = np.random.default_rng(1234)
        pass_cnts = {rn: 0 for rn in ruler_names}
        tot = N_SPLITS * n_mc
        fail_act_counts = {}
        for dY, a0, per_e, wk, e9, hu, ptab, pfur in split_records:
            for _ in range(n_mc):
                dP = make_sim_dP(dY, a0, wk, e9, mode, rng_m)
                out = eval_std_rulers(dP, dY, a0)
                for rn in ruler_names:
                    if out[rn]["ok"]:
                        pass_cnts[rn] += 1
                if not out["old"]["ok"]:
                    for fq in out["old"]["fail_qs"]:
                        fail_act_counts[fq] = fail_act_counts.get(fq, 0) + 1
        row = " | ".join(f"{rn}={pass_cnts[rn]:3d}/{tot} ({100*pass_cnts[rn]/tot:5.1f}%)" for rn in ruler_names)
        print(f"  {mode:<22}: {row}")
        if fail_act_counts:
            top_f = sorted(fail_act_counts.items(), key=lambda kv: -kv[1])[:8]
            print(f"     old-ruler failing action counts (out of {tot}): {top_f}")

    # =========================================================================
    # 4. SAVED RANK 6 (s42 & s43) DEV VERDICT UNDER OLD vs AMENDED RULERS
    # =========================================================================
    print("\n=== 4. SAVED RANK 6 (s42 & s43) DEV VERDICT UNDER OLD vs AMENDED RULERS (NO FLIP CHECK) ===")
    he = scorer.load_split(os.path.join(BASE, "wm-harness/data/heldout.npz"))
    xi1, ai1, _, _, _ = scorer.windows(he, 1)
    x0 = he["frames"][xi1].astype(np.float64)
    x1 = he["frames"][xi1 + 1].astype(np.float64)
    dY_he = (x1 - x0).reshape(len(xi1), -1)
    a0_he = he["actions"][ai1]

    for seed in (42, 43):
        fc = np.load(os.path.join(BASE, f"wm6/run_r6_s{seed}/forecasts_dev.npz"))
        P1 = fc["pred_k1"].astype(np.float64)
        dP_he = (P1 - x0).reshape(len(xi1), -1)
        out = eval_std_rulers(dP_he, dY_he, a0_he)
        print(f"\n  Saved Rank 6 s{seed} (dev heldout, k=1):")
        for q in (1, 2, 3, 4, 5, 6, 8, 9):
            v = out["per_act"][q]
            print(f"    a={q:2d}: n={v['n']:3d} sr={v['std_real']:.4f} ratio={v['ratio']:.3f} neff={v['neff']:6.1f} top1={v['top1']*100:4.1f}% active={v['active']}")
        for rn in ruler_names:
            r = out[rn]
            if rn == "old":
                print(f"    [{rn:<14}] std_ok={r['ok']} (active={r['active_qs']}, fail={r['fail_qs']})")
            else:
                print(
                    f"    [{rn:<14}] std_ok={r['ok']} (indiv={r['indiv_qs']}, indiv_fail={r['indiv_fail']}, "
                    f"pool_qs={r['pool_qs']}, pool_sr={r['pool_sr']:.4f}, pool_ratio={r['pool_ratio']:.3f}, pool_neff={r['pool_neff']:.1f})"
                )

    print(f"\n[THROWAWAY FRAGILITY DONE in {time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
