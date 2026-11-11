"""Day/night loop for one arm and one seed.

This module must NOT import hidden_score (nor oracle/eval, which do). The measurement callback
(`evaluator`) and arm O's scoring function (`oracle_scores`) are passed in by run.py.
"""
import time
from types import SimpleNamespace
import numpy as np
import torch

from .paint import parse, render, encode_batch, CTX, canonical
from .maker import Maker, train_steps
from .copyguard import CopyGuard
from . import critic as critic_mod

MAX_TRIES = 16
N_TOK = CTX - 1


def request_noise(seed, day, n_requests):
    """Shared random streams keyed by (seed, day, request index): token uniforms for up to 16
    tries, and one uniform for tie-breaking / random picks."""
    u_tok = np.empty((n_requests, MAX_TRIES, N_TOK), dtype=np.float64)
    u_pick = np.empty(n_requests)
    for i in range(n_requests):
        rng = np.random.default_rng([seed, day, i])
        u_tok[i] = rng.random((MAX_TRIES, N_TOK))
        u_pick[i] = rng.random()
    return SimpleNamespace(u_tok=u_tok, u_pick=u_pick)


def make_tries(maker, seed, day, n_req, n_tries, temp, guard):
    noise = request_noise(seed, day, n_req)
    u = noise.u_tok[:, :n_tries].reshape(n_req * n_tries, N_TOK)
    toks = maker.sample(n_req * n_tries, temp, u)
    n = len(toks)
    grids = np.zeros((n, 12, 12), dtype=np.int8)
    ncmd = np.zeros(n, dtype=np.int64)
    parsed = np.zeros(n, dtype=bool)
    for i, t in enumerate(toks):
        cmds = parse(t)
        if cmds is not None:
            parsed[i] = True
            ncmd[i] = len(cmds)
            grids[i] = render(cmds)
    valid = parsed & grids.reshape(n, -1).any(1)           # the checkable part
    copy = np.zeros(n, dtype=bool)
    if valid.any():
        copy[valid] = guard.distances(grids[valid]) <= guard.k
    passing = valid & ~copy
    sh = (n_req, n_tries)
    return SimpleNamespace(tokens=toks, grids=grids, ncmd=ncmd.reshape(sh), parsed=parsed,
                           valid=valid.reshape(sh), copy=copy.reshape(sh), passing=passing.reshape(sh),
                           u_pick=noise.u_pick, n_req=n_req, n_tries=n_tries)


def mirror_mismatch(grids):
    """Mismatched cell pairs about the picture's own column centre (bounding box of coloured cells)."""
    n = len(grids)
    colany = (grids != 0).any(1)                      # (n, 12)
    has = colany.any(1)
    l = np.where(has, colany.argmax(1), 0)
    r = np.where(has, 11 - colany[:, ::-1].argmax(1), 0)
    cols = np.arange(12)[None, :]
    cm = (l + r)[:, None] - cols                      # mirrored column
    inr = (cm >= 0) & (cm < 12)
    mirrored = np.take_along_axis(grids, np.clip(cm, 0, 11)[:, None, :].repeat(grids.shape[1], 1), 2)
    bad = (grids != mirrored) & inr[:, None, :] & (cols < cm)[:, None, :]
    bad_out = (grids != 0) & (~inr)[:, None, :]
    return bad.reshape(n, -1).sum(1) + bad_out.reshape(n, -1).sum(1)


def select(key, u):
    """Row-wise argmin of key (inf = not allowed); ties broken uniformly using u in [0,1). -1 if none."""
    mn = key.min(1)
    has = np.isfinite(mn)
    ties = (key == mn[:, None]) & has[:, None]
    cnt = ties.sum(1)
    target = np.minimum((u * cnt).astype(np.int64), np.maximum(cnt - 1, 0))
    idx = (np.cumsum(ties, 1) > target[:, None]).argmax(1)
    idx[~has] = -1
    return idx


def pick_keys(arm, tb, n_use, critic_logits=None, oracle_scores=None):
    """Lower key = preferred. Restricted to the first n_use tries; non-passing tries get +inf."""
    sh = (tb.n_req, tb.n_tries)
    passing = tb.passing[:, :n_use]
    if arm in ("C", "B"):
        key = -critic_logits.reshape(sh)[:, :n_use].astype(np.float64)
    elif arm in ("R", "R07"):
        key = np.zeros(passing.shape)
    elif arm == "H":
        mm = mirror_mismatch(tb.grids).reshape(sh)[:, :n_use]
        key = tb.ncmd[:, :n_use] * 1000.0 + mm
    elif arm == "O":
        key = -oracle_scores.reshape(sh)[:, :n_use]
    else:
        raise ValueError(arm)
    return np.where(passing, key, np.inf)


def pick_distinct(keys, grids, n_tries, u):
    """TC-1b variety guard: requests in order; each takes its best try (ties broken by u) whose folded
    picture is not already kept tonight, else nothing. -1 = no pick."""
    seen, out = set(), np.full(len(keys), -1, dtype=np.int64)
    for i, row in enumerate(keys):
        order = np.random.default_rng(int(u[i] * 2**32)).permutation(len(row))
        order = order[np.argsort(row[order], kind="stable")]
        for j in order:
            if not np.isfinite(row[j]):
                break
            c = canonical(grids[i * n_tries + j])
            if c not in seen:
                seen.add(c)
                out[i] = j
                break
    return out


def pick(arm, tb, n_use=None, critic_logits=None, oracle_scores=None):
    n_use = n_use or tb.n_tries
    return select(pick_keys(arm, tb, n_use, critic_logits, oracle_scores), tb.u_pick)


def night_train(maker, rows, pool, cfg, seed, day):
    """rows: list of token lists (exactly requests of them). Fresh AdamW, constant lr."""
    x = torch.from_numpy(encode_batch(rows))
    n, kb = len(rows), cfg.night_kept
    opt = torch.optim.AdamW(maker.parameters(), lr=cfg.night_lr, weight_decay=cfg.weight_decay)
    rng = np.random.default_rng([seed, day, 31337])
    order = np.concatenate([rng.permutation(n)[:(n // kb) * kb] for _ in range(cfg.night_visits)])
    steps = len(order) // kb
    ridx = rng.integers(0, len(pool), (steps, cfg.night_replay))

    def batch_fn(s):
        return torch.cat([x[torch.from_numpy(order[s * kb:(s + 1) * kb])], pool[torch.from_numpy(ridx[s])]])

    last = train_steps(maker, opt, batch_fn, steps, grad_clip=cfg.grad_clip)
    return {"steps": steps, "final_loss": last}


def run_arm(arm, seed, cfg, data, k, state, pool, evaluator=None, oracle_scores=None, log=print):
    """Returns (result dict, kept_rows per day). `state`: day-0 maker weights shared by all arms."""
    t0 = time.time()
    maker = Maker()
    maker.load_state_dict(state)
    maker.eval()
    guard = CopyGuard(data.critic, k)
    temp = 0.7 if arm == "R07" else cfg.temp
    cr = critic_mod.Critic(seed, cfg.critic_lr) if arm == "C" else None
    blank = critic_mod.Critic(seed + 77, cfg.critic_lr) if arm == "B" else None
    buffer = []
    result = {"days": [], "evals": []}
    kept_log = []
    if evaluator:
        result["evals"].append(evaluator(maker, 0))
        log(f"[{arm} s{seed}] night 0 eval done ({time.time() - t0:.0f}s)")
    for day in range(1, cfg.days + 1):
        if arm == "N":
            if evaluator:
                ev = dict(result["evals"][0])
                ev["reused_from_night_0"] = True
                result["evals"].append(ev)
            continue
        td = time.time()
        tb = make_tries(maker, seed, day, cfg.requests, cfg.tries, temp, guard)
        rec = {"day": day, "tries": int(tb.valid.size), "parsed": int(tb.parsed.sum()),
               "valid": int(tb.valid.sum()), "copies": int(tb.copy.sum()), "passes": int(tb.passing.sum()),
               "requests_with_pass": int(tb.passing.any(1).sum()), "t_sample": time.time() - td}
        logits = None
        if arm == "C":
            buffer.append(tb.grids[tb.passing.reshape(-1)])
            tc = time.time()
            rec["critic_train"] = critic_mod.daily_train(
                cr, data.critic, np.concatenate(buffer), cfg.critic_steps, cfg.critic_batch,
                cfg.r1_weight, np.random.default_rng([seed, 7000 + day]))
            rec["critic_exam"] = critic_mod.critic_exam(cr, data, tb.grids[tb.passing.reshape(-1)])
            rec["buffer_size"] = int(sum(len(b) for b in buffer))
            rec["t_critic"] = time.time() - tc
            logits = cr.logits(tb.grids)
        elif arm == "B":
            logits = blank.logits(tb.grids)
        osc = None
        if arm == "O":
            osc = np.zeros(tb.grids.shape[0])
            m = tb.passing.reshape(-1)
            osc[m] = oracle_scores(tb.grids[m])
        if cfg.distinct:
            idx = pick_distinct(pick_keys(arm, tb, tb.n_tries, logits, osc), tb.grids, tb.n_tries, tb.u_pick)
        else:
            idx = pick(arm, tb, None, logits, osc)
        flat = tb.tokens
        kept = [flat[i * tb.n_tries + j] for i, j in enumerate(idx) if j >= 0]
        n_none = int((idx < 0).sum())
        if kept and n_none:
            fill = np.random.default_rng([seed, day, 99991]).integers(0, len(kept), n_none)
            kept = kept + [kept[i] for i in fill]
        rec["filled"] = n_none
        rec["distinct_kept"] = len(set(tuple(r) for r in kept))
        rec["rows_trained"] = len(kept)
        rec["kept_mean_ncmd"] = float(np.mean([sum(1 for t in r if t in (3, 4, 5)) for r in kept])) if kept else None
        kept_log.append([tuple(r) for r in kept])
        if kept:
            tn = time.time()
            rec["night"] = night_train(maker, kept, pool, cfg, seed, day)
            rec["t_night"] = time.time() - tn
        if evaluator:
            result["evals"].append(evaluator(maker, day))
        rec["t_day_total"] = time.time() - td
        result["days"].append(rec)
        log(f"[{arm} s{seed}] day {day}: passes {rec['passes']} copies {rec['copies']} "
            f"rows {rec['rows_trained']} ({rec['t_day_total']:.0f}s)")
    result["wall_time"] = time.time() - t0
    return result, kept_log
