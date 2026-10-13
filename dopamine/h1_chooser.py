"""H-1: a learned help chooser that reads the person and decides itself whether to use the tool
(DESIGN-AND-MARKS-2026-10-10.md, section "H-1"; marks sealed there; this file only implements them).

  python -m dopamine.h1_chooser cache --seed 200 --ckpt CKPT --out DIR [--threads N] [--smoke]
  python -m dopamine.h1_chooser run --dir DIR [--threads N]

Sessions are p1_sessions' (same builder, same cache layout) with two extras, both drawn from a SEPARATE per-session RNG
(so the sessions themselves are exactly p1_sessions.make_session(seed, index)): the person type (easygoing: an unwanted
extra costs 0.25; tidy: 1.0; 50/50, never shown to any arm) and a "thanks" flag on 30% of rounds (random; changes no reward).
Training: 20 days x 150 sessions, person seed 93006. Sealed: 400 sessions, person seed 93005.
--smoke uses 5 days x 40 training + 40 sealed sessions drawn from OTHER person seeds (94006 / 94005), so a smoke run never
touches the sealed sessions.

Per-round rewards of an extra (the candidate is always N's top guess): wanted and right +1, wanted and wrong -1, unwanted
-cost(person); the tool value is always right; a tool call costs 0.02. Effort = L - sum(rewards) (= L - sum(extra rewards)
+ 0.02 per tool call). The chooser sees the person's reactions as four counts so far this session: accepted (wanted, right), removed (unwanted, tidy
person removes it), left (unwanted, easygoing person leaves it), corrected (wanted but wrong).
Arms: NONE, EAGER-TOOL, HELPER-TOOL (P3's top-1 rule, V learned on the training days), CHOOSER, ORACLE (a wanted candidate
exists: saves 1, no tool call charged).
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
import warnings

import numpy as np

from dopamine import p1_sessions as P

# ---------- constants (fixed before any full run; chosen on a smoke run, training reward only; see report) ----------
TRAIN_SEED, SEALED_SEED = 93006, 93005
SMOKE_TRAIN_SEED, SMOKE_SEALED_SEED = 94006, 94005
DAYS, PER_DAY, N_SEALED = 20, 150, 400
SMOKE_DAYS, SMOKE_PER_DAY, SMOKE_SEALED = 5, 40, 40
COST = {0: 0.25, 1: 1.0}          # person type 0 easygoing, 1 tidy
P_THANKS = 0.30
TOOL_COST = 0.02
HIDDEN = 32
LR = 2e-3
EPOCHS_PER_DAY = 8
ENT_W = 0.05
CHOOSER_SEED = 7
ACTIONS = ['quiet', 'own answer', 'tool']


# ---------- sessions ----------

def make_h1_session(person_seed, index):
    """p1_sessions' session plus (person type, thanks flags per round) from a separate RNG."""
    s = P.make_session(person_seed, index)
    r = random.Random(person_seed * 7919 + index * 104729 + 17)
    ptype = r.randrange(2)
    thanks = [int(r.random() < P_THANKS) for _ in range(s['L'])]
    return s, ptype, thanks


def all_h1_sessions(smoke=False):
    """[(split, day, index_in_split, session, ptype, thanks)]; split 0 training (days 1..D), 1 sealed (day 0)."""
    if smoke:
        days, per, sealed, ts, ss = SMOKE_DAYS, SMOKE_PER_DAY, SMOKE_SEALED, SMOKE_TRAIN_SEED, SMOKE_SEALED_SEED
    else:
        days, per, sealed, ts, ss = DAYS, PER_DAY, N_SEALED, TRAIN_SEED, SEALED_SEED
    out = []
    for d in range(days):
        for j in range(per):
            out.append((0, d + 1, d * per + j, *make_h1_session(ts, d * per + j)))
    for j in range(sealed):
        out.append((1, 0, j, *make_h1_session(ss, j)))
    return out


def code_sha(path=None):
    return hashlib.sha256(open(path or os.path.abspath(__file__), 'rb').read()).hexdigest()


# ---------- cache step (same layout as p1_sessions.do_cache, plus person type and thanks) ----------

def do_cache(a):
    import torch
    torch.set_num_threads(a.threads)
    from custom_io.models import load_model
    from domain.mode import greedy
    from dopamine.motivator import reader_features
    out = a.out
    os.makedirs(out, exist_ok=True)
    sess = all_h1_sessions(a.smoke)
    P.log(f'{len(sess)} sessions built')
    pid, prompts, value = {}, [], {}

    def PI(p):
        if p not in pid:
            pid[p] = len(prompts)
            prompts.append(p)
        return pid[p]
    s_day, s_split, s_L, s_ptype, r_thanks = [], [], [], [], []
    r_sess, r_idx, r_cur, r_next = [], [], [], []
    c_ptr, c_pid, c_kind, c_wanted = [0], [], [], []
    cand_set = set()
    with open(os.path.join(out, 'sessions.jsonl'), 'w') as f:
        for si, (split, day, ix, s, ptype, thanks) in enumerate(sess):
            s_day.append(day), s_split.append(split), s_L.append(s['L']), s_ptype.append(ptype)
            for t, (req, menu) in enumerate(zip(s['requests'], s['menus'])):
                nxt = s['requests'][t + 1][2] if t + 1 < s['L'] else None
                r_sess.append(si), r_idx.append(t), r_cur.append(PI(req[2])), r_next.append(PI(nxt) if nxt else -1)
                r_thanks.append(thanks[t])
                for k, p, v in menu:
                    c_pid.append(PI(p)), c_kind.append(P.KINDS.index(k)), c_wanted.append(int(p == nxt))
                    cand_set.add(p)
                    value[p] = v
                c_ptr.append(len(c_pid))
            f.write(json.dumps({'split': split, 'day': day, 'index': ix, 'L': s['L'], 'ptype': ptype, 'thanks': thanks,
                                'grid': s['grid'], 'requests': [[r[0], list(r[1]), r[2], r[3]] for r in s['requests']],
                                'menus': [[list(m) for m in mn] for mn in s['menus']]}) + '\n')
    P.log(f'{len(prompts)} distinct prompts, {len(cand_set)} distinct candidates, {len(c_pid)} menu entries, {len(r_sess)} rounds')
    model = load_model(a.ckpt).eval()
    t = time.time()
    F = []
    for s in range(0, len(prompts), 128):
        F.append(reader_features(model, prompts[s:s + 128]).astype(np.float32))
        if (s // 128) % 20 == 0:
            P.log(f'features {min(s + 128, len(prompts))}/{len(prompts)}  {time.time() - t:.0f}s')
    F = np.concatenate(F)
    tf = time.time() - t
    P.log(f'features done {F.shape} in {tf:.0f}s')
    cands = [p for p in prompts if p in cand_set]
    correct = np.full(len(prompts), -1, np.int8)
    t = time.time()
    for s in range(0, len(cands), 256):
        chunk = cands[s:s + 256]
        for p, (_, ans) in zip(chunk, greedy(model, chunk)):
            correct[pid[p]] = int(ans == value[p])
        if (s // 256) % 10 == 0:
            P.log(f'answers {min(s + 256, len(cands))}/{len(cands)}  {time.time() - t:.0f}s')
    tg = time.time() - t
    P.log(f'answers done {len(cands)} in {tg:.0f}s; overall right {correct[correct >= 0].mean():.3f}')
    np.savez_compressed(os.path.join(out, 'cache.npz'), prompts=np.array(prompts), feats=F, correct=correct,
                        sess_day=np.array(s_day), sess_split=np.array(s_split), sess_L=np.array(s_L),
                        sess_ptype=np.array(s_ptype), round_thanks=np.array(r_thanks),
                        round_sess=np.array(r_sess), round_idx=np.array(r_idx), round_cur=np.array(r_cur),
                        round_next=np.array(r_next), cand_ptr=np.array(c_ptr), cand_pid=np.array(c_pid),
                        cand_kind=np.array(c_kind), cand_wanted=np.array(c_wanted, np.int8),
                        seed=np.array(a.seed), ckpt=np.array(a.ckpt), smoke=np.array(bool(a.smoke)),
                        code_sha256=np.array(code_sha()))
    json.dump({'seed': a.seed, 'ckpt': a.ckpt, 'smoke': a.smoke, 'code_sha256': code_sha(),
               'p1_sessions_sha256': code_sha(P.__file__), 'feature_secs': tf, 'answer_secs': tg,
               'n_candidate_answers': len(cands), 'n_prompts': len(prompts), 'n_sessions': len(sess)},
              open(os.path.join(out, 'cache_info.json'), 'w'))
    P.log('cache saved')


# ---------- per-round tables ----------

class Tables:
    """Everything the arms need, per round, from a cache dict Z (N head fitted day by day exactly as in p1_sessions)."""

    def __init__(self, Z, n_seed_base=100, nhead_path=None):
        warnings.simplefilter('ignore')
        self.Z = Z
        F, ptr, cpid, cwant = Z['feats'], Z['cand_ptr'], Z['cand_pid'], Z['cand_wanted']
        self.R = R = len(Z['round_sess'])
        self.S = len(Z['sess_L'])
        self.ptr, self.cpid, self.cwant = ptr, cpid, cwant
        n_per = np.diff(ptr)
        row_round = np.repeat(np.arange(R), n_per)
        ridx = Z['round_idx']
        self.ridx = ridx
        self.round_day = np.where(Z['sess_split'][Z['round_sess']] == 1, 0, Z['sess_day'][Z['round_sess']])
        self.D = int(Z['sess_day'].max())
        cand_day = self.round_day[row_round]
        self.first_round = np.zeros(self.S, int)
        self.first_round[Z['round_sess'][::-1]] = np.arange(R)[::-1]
        # N head, refit after each training day on all past days; day d is scored by the model fitted on days < d
        pn_all = None
        self.N_secs = []
        if nhead_path and os.path.exists(nhead_path):
            z = np.load(nhead_path)
            if z['pn_all'].shape == (len(cwant),) and int(z['n_rounds']) == R and int(z['n_base']) == n_seed_base:
                pn_all = z['pn_all']
        if pn_all is None:
            Xn = np.concatenate([F[Z['round_cur']][row_round], F[cpid], P.onehot(ridx[row_round])], 1)
            pn_all = np.zeros(len(cwant))
            n_model = None
            for day in list(range(1, self.D + 1)) + [0]:
                rows_d = np.where(cand_day == day)[0]
                if len(rows_d) == 0:
                    continue
                if n_model is not None:
                    pn_all[rows_d] = n_model.predict_proba(Xn[rows_d])[:, 1] if len(n_model.classes_) == 2 else 0.0
                if day == 0:
                    break
                t = time.time()
                n_model = P.mlp('clf', n_seed_base + day).fit(Xn[(cand_day >= 1) & (cand_day <= day)],
                                                               cwant[(cand_day >= 1) & (cand_day <= day)])
                self.N_secs.append(time.time() - t)
            if nhead_path:
                np.savez_compressed(nhead_path, pn_all=pn_all, n_rounds=R, n_base=n_seed_base)
        self.pn_all = pn_all
        # top guess per round (day 1: random candidate, N not fitted yet)
        rs = np.random.RandomState(21)
        self.has = n_per > 0
        self.top = np.full(R, -1)
        self.ptop = np.zeros(R)
        for r in range(R):
            if not self.has[r]:
                continue
            rr = np.arange(ptr[r], ptr[r + 1])
            if self.round_day[r] == 1:
                self.top[r] = rr[rs.randint(len(rr))]
            else:
                self.top[r] = rr[np.argmax(pn_all[rr])]
                self.ptop[r] = pn_all[self.top[r]]
        tp = np.maximum(self.top, 0)
        self.wt = (cwant[tp] == 1) & self.has                                   # top guess is wanted
        self.rt = (Z['correct'][cpid[tp]] == 1) & self.has                      # model's own answer is right
        self.fcand = F[cpid[tp]]
        self.ptype = Z['sess_ptype'][Z['round_sess']]
        self.cost = np.where(self.ptype == 0, COST[0], COST[1])
        self.thanks_prev = np.zeros(R)
        for r in range(R):
            if ridx[r] > 0:
                self.thanks_prev[r] = Z['round_thanks'][r - 1]
        self.L = Z['sess_L']
        self.F = F

    def rew(self, a, r=None):
        """Round reward of action a (0 quiet, 1 own answer, 2 tool) for rounds r (array) given actions a (array)."""
        r = np.arange(self.R) if r is None else r
        a = np.where(self.has[r], a, 0)
        own = np.where(self.wt[r], np.where(self.rt[r], 1.0, -1.0), -self.cost[r])
        tool = np.where(self.wt[r], 1.0, -self.cost[r]) - TOOL_COST
        return np.where(a == 1, own, np.where(a == 2, tool, 0.0))


# ---------- HELPER-TOOL (P3's top-1 rule under the H-1 environment) ----------

def helper_tool_actions(T):
    """Actions (0/2) per round. Rule of p1_sessions.simulate(helper='top1', tool_values=True): day 1 adds a random
    candidate with prob 0.5; later days explore (10%, N's top) else add N's top iff the help-value head V (MLP on
    [N prob, reader mean of the candidate, round one-hot]) predicts > 0; V refit after each day on all of HELPER's own
    extras (reward = tool reward under the new person mix, incl. the 0.02); sealed: no exploration, frozen."""
    acts = np.zeros(T.R, int)
    rs = np.random.RandomState(12)
    rows_h, pn_h, rew_h = [], [], []
    v_model = None
    for day in list(range(1, T.D + 1)) + [0]:
        sealed = day == 0
        for r in np.where(T.round_day == day)[0]:
            if not T.has[r]:
                continue
            rr = np.arange(T.ptr[r], T.ptr[r + 1])
            hp = False
            if day == 1:
                c = rr[rs.randint(len(rr))] if rs.rand() < 0.5 else None
                hp, pn = c is not None, 0.0
            else:
                c, pn = T.top[r], T.ptop[r]
                if (not sealed) and rs.rand() < 0.10:
                    hp = True
                elif v_model is not None:
                    Xv = np.concatenate([[[pn]], T.F[T.cpid[[c]]], P.onehot(T.ridx[[r]])], 1)
                    hp = v_model.predict(Xv)[0] > 0
            if hp:
                acts[r] = 2
                if not sealed:
                    rows_h.append((r, c)), pn_h.append(pn)
                    rew_h.append((1.0 if T.cwant[c] == 1 else -T.cost[r]) - TOOL_COST)
        if sealed:
            break
        if len(rows_h) >= 5:
            rr_, cc_ = np.array([x[0] for x in rows_h]), np.array([x[1] for x in rows_h])
            Xv = np.concatenate([np.array(pn_h)[:, None], T.F[T.cpid[cc_]], P.onehot(T.ridx[rr_])], 1)
            v_model = P.mlp('reg', 200 + day).fit(Xv, np.array(rew_h))
    return acts


def reaction_update(cnt, s_ids, shown, accepted, unwanted, tidy, corrected):
    """In place: counts [accepted, removed, left, corrected] of sessions s_ids after a round."""
    cnt[s_ids, 0] += shown & accepted
    cnt[s_ids, 1] += shown & unwanted & tidy
    cnt[s_ids, 2] += shown & unwanted & ~tidy
    cnt[s_ids, 3] += corrected


def helper_react_actions(T):
    """HELPER-REACT (H-2): HELPER-TOOL with the value head's inputs extended by the four reaction counts so far this session
    and "thanks" last round. Played session by session in round order (the counts depend on its own earlier actions), on
    training days and on the sealed day. Everything else as helper_tool_actions (same RNG stream order, MLP regressor and
    seeds, tool value, 0.02 cost, 10% exploration on training days only, refit per day on all past rounds it acted on)."""
    acts = np.zeros(T.R, int)
    rs = np.random.RandomState(12)
    rows_h, x_h, rew_h = [], [], []
    v_model = None
    cnt = np.zeros((T.S, 4))
    for day in list(range(1, T.D + 1)) + [0]:
        sealed = day == 0
        sess = np.where((T.Z['sess_split'] == 1) if sealed else ((T.Z['sess_split'] == 0) & (T.Z['sess_day'] == day)))[0]
        for s in sess:
            for t in range(T.L[s]):
                r = T.first_round[s] + t
                if not T.has[r]:
                    continue
                rr = np.arange(T.ptr[r], T.ptr[r + 1])
                hp = False
                if day == 1:
                    c = rr[rs.randint(len(rr))] if rs.rand() < 0.5 else None
                    hp, pn = c is not None, 0.0
                else:
                    c, pn = T.top[r], T.ptop[r]
                x = np.concatenate([[pn], T.F[T.cpid[c if c is not None else T.top[r]]], P.onehot(T.ridx[[r]])[0], cnt[s],
                                    [T.thanks_prev[r]]])[None]
                if day != 1:  # later training days and the sealed day (day 0)
                    if (not sealed) and rs.rand() < 0.10:
                        hp = True
                    elif v_model is not None:
                        hp = v_model.predict(x)[0] > 0
                if hp:
                    acts[r] = 2
                    wanted = bool(T.cwant[c] == 1)
                    reaction_update(cnt, np.array([s]), np.array([True]), np.array([wanted]), np.array([not wanted]),
                                    np.array([T.ptype[r] == 1]), np.array([False]))
                    if not sealed:
                        x_h.append(x[0]), rew_h.append((1.0 if wanted else -T.cost[r]) - TOOL_COST)
        if sealed:
            break
        if len(x_h) >= 5:
            v_model = P.mlp('reg', 200 + day).fit(np.array(x_h), np.array(rew_h))
    return acts


def prev_reaction_rates(T, acts, rounds):
    """Extras rate in rounds >= 2 after a 'removed' vs after a 'left' reaction (previous round: tool extra, unwanted)."""
    prev = rounds - 1
    later = T.ridx[rounds] > 0
    shown_prev = acts[np.maximum(prev, 0)] > 0
    unw = shown_prev & ~T.wt[np.maximum(prev, 0)] & later
    rem, lef = unw & (T.ptype[np.maximum(prev, 0)] == 1), unw & (T.ptype[np.maximum(prev, 0)] == 0)
    now = acts[rounds] > 0
    f = lambda m: (float(now[m].mean()) if m.any() else None, int(m.sum()))
    return {'after_removed': f(rem), 'after_left': f(lef)}



# ---------- CHOOSER ----------

def build_inputs(T, rounds, cnt):
    """cnt: [n, 4] counts so far this session: accepted, removed, left, corrected."""
    return np.concatenate([T.ptop[rounds][:, None], T.fcand[rounds], P.onehot(T.ridx[rounds]), cnt,
                           T.thanks_prev[rounds][:, None]], 1).astype(np.float32)


def play(T, sessions, act_fn):
    """Play the given sessions round by round (all sessions in step). act_fn(X_raw, rounds) -> actions in {0,1,2}.
    Returns (actions per round [R], recorded raw inputs, actions, round index rows)."""
    acts = np.zeros(T.R, int)
    cnt = np.zeros((T.S, 4))
    recX, recA, recR = [], [], []
    for t in range(4):
        s_t = sessions[T.L[sessions] > t]
        if len(s_t) == 0:
            continue
        rounds = T.first_round[s_t] + t
        ok = T.has[rounds]
        s_t, rounds = s_t[ok], rounds[ok]
        if len(s_t) == 0:
            continue
        X = build_inputs(T, rounds, cnt[s_t])
        a = act_fn(X, rounds)
        acts[rounds] = a
        recX.append(X), recA.append(a), recR.append(rounds)
        shown = a > 0
        wt = T.wt[rounds]
        good = wt & ((a == 2) | T.rt[rounds])
        # reactions: accepted (wanted, right); unwanted -> tidy removes it, easygoing leaves it; wanted but wrong -> corrected
        reaction_update(cnt, s_t, shown, good, ~wt, T.ptype[rounds] == 1, shown & wt & ~good)
    return acts, (np.concatenate(recX) if recX else None), (np.concatenate(recA) if recA else None), \
        (np.concatenate(recR) if recR else None)


def train_chooser(T, log=print):
    import torch
    from torch import nn
    torch.manual_seed(CHOOSER_SEED)
    rs = np.random.RandomState(CHOOSER_SEED)
    d_in = 1 + T.fcand.shape[1] + 4 + 4 + 1
    pol = nn.Sequential(nn.Linear(d_in, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, 3))
    cri = nn.Sequential(nn.Linear(d_in, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, 1))
    opt = torch.optim.Adam(list(pol.parameters()) + list(cri.parameters()), lr=LR)
    seen = []                              # raw inputs of all training days so far (for the standardiser)
    curve = []
    stats = None
    for day in range(1, T.D + 1):
        sess = np.where((T.Z['sess_split'] == 0) & (T.Z['sess_day'] == day))[0]
        if stats is None:                                  # day 1: nothing seen yet, so uniform random actions, raw inputs
            fn = lambda X, rounds: rs.randint(0, 3, len(X))
        else:
            mu, sd = stats

            def fn(X, rounds, mu=mu, sd=sd):
                with torch.no_grad():
                    p = torch.softmax(pol(torch.from_numpy((X - mu) / sd)), 1).numpy()
                u = rs.rand(len(X), 1)
                return np.minimum((p.cumsum(1) < u).sum(1), 2)
        acts, X, a, rounds = play(T, sess, fn)
        r = T.rew(a, rounds).astype(np.float32)
        seen.append(X)
        allX = np.concatenate(seen)
        if stats is None:
            stats = (allX.mean(0), np.maximum(allX.std(0), 1e-3))     # day 1's own, applied to its update only
            use = stats
        else:
            use = stats                                                # stats the day was played with
        Xt = torch.from_numpy(((X - use[0]) / use[1]).astype(np.float32))
        at, rt_ = torch.from_numpy(a.astype(np.int64)), torch.from_numpy(r)
        for _ in range(EPOCHS_PER_DAY):
            logits = pol(Xt)
            lp = torch.log_softmax(logits, 1)
            v = cri(Xt)[:, 0]
            adv = (rt_ - v).detach()
            ent = -(lp.exp() * lp).sum(1).mean()
            loss = -(lp.gather(1, at[:, None])[:, 0] * adv).mean() - ENT_W * ent + 0.5 * ((v - rt_) ** 2).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
        stats = (allX.mean(0), np.maximum(allX.std(0), 1e-3))          # all training data seen so far -> next day
        shares = np.bincount(a, minlength=3) / len(a)
        curve.append({'day': day, 'mean_reward_per_round': float(r.mean()), 'share_quiet': float(shares[0]),
                      'share_own': float(shares[1]), 'share_tool': float(shares[2]), 'entropy': float(ent)})
        log(f'day {day}: reward/round {r.mean():+.4f}  quiet {shares[0]:.2f} own {shares[1]:.2f} tool {shares[2]:.2f}  ent {ent:.3f}')

    def greedy_fn(X, rounds):
        with torch.no_grad():
            return pol(torch.from_numpy(((X - stats[0]) / stats[1]).astype(np.float32))).argmax(1).numpy()
    return greedy_fn, curve


# ---------- run ----------

def run_h2(Z, T, ht_acts=None, log=print):
    """H-2: HELPER-REACT vs HELPER-TOOL on the sealed sessions (no CHOOSER)."""
    t0 = time.time()
    ht_acts = helper_tool_actions(T) if ht_acts is None else ht_acts
    re_acts = helper_react_actions(T)
    sealed = np.where(Z['sess_split'] == 1)[0]
    eager = np.where(T.has, 2, 0)
    rounds_s = np.where(T.round_day == 0)[0]
    sidx = {s_: i for i, s_ in enumerate(sealed)}
    pos = np.array([sidx[s_] for s_ in Z['round_sess'][rounds_s]])
    Ls = T.L[sealed].astype(float)

    def effort(acts):
        return Ls - np.bincount(pos, weights=T.rew(acts[rounds_s], rounds_s), minlength=len(sealed))
    arms = {'NONE': Ls.copy(), 'EAGER-TOOL': effort(eager), 'HELPER-TOOL': effort(ht_acts), 'HELPER-REACT': effort(re_acts)}
    pt = Z['sess_ptype'][sealed]
    h2 = {'mean_effort': {'all': {k: float(v.mean()) for k, v in arms.items()},
                          'easygoing': {k: float(v[pt == 0].mean()) for k, v in arms.items()},
                          'tidy': {k: float(v[pt == 1].mean()) for k, v in arms.items()}}}
    d = arms['HELPER-REACT'] - arms['HELPER-TOOL']
    lo, hi = P.boot(d)
    h2['HELPER-REACT-HELPER-TOOL'] = {'diff': float(d.mean()), 'ci95': [lo, hi]}
    h2['H2-1'] = {'verdict': 'PASS' if (d.mean() <= -0.05 and hi < 0) else ('PROVED WRONG (on this seed)' if d.mean() >= 0 else 'neither pass nor wrong'),
                  'rule': 'pass: HELPER-REACT - HELPER-TOOL <= -0.05 and CI upper < 0; wrong: diff >= 0 on either seed'}
    sh = re_acts[rounds_s] > 0
    later, th = T.ridx[rounds_s] > 0, T.thanks_prev[rounds_s] == 1
    a_t, a_p = sh[later & th], sh[later & ~th]
    gap = 100 * (a_t.mean() - a_p.mean()) if len(a_t) and len(a_p) else float('nan')
    h2['H2-3'] = {'offer_rate_after_thanks': float(a_t.mean()), 'offer_rate_after_plain': float(a_p.mean()), 'n_after_thanks': int(len(a_t)),
                  'n_after_plain': int(len(a_p)), 'gap_points': float(gap),
                  'verdict': 'PASS' if abs(gap) <= 3 else ('PROVED WRONG (on this seed)' if abs(gap) > 5 else 'neither pass nor wrong'),
                  'rule': 'pass: |gap| <= 3 points; wrong: |gap| > 5 points'}
    h2['H2_pass_this_seed'] = bool(h2['H2-1']['verdict'] == 'PASS' and h2['H2-3']['verdict'] == 'PASS')
    h2['extras_rate_after_reaction'] = {'HELPER-REACT': prev_reaction_rates(T, re_acts, rounds_s),
                                        'HELPER-TOOL': prev_reaction_rates(T, ht_acts, rounds_s)}
    a = re_acts[rounds_s]
    h2['HELPER-REACT_extras'] = {'extras_per_session': float((a > 0).sum() / len(sealed)),
                                 'wanted_share': float(T.wt[rounds_s][a > 0].mean()) if (a > 0).any() else None}
    h2['n_by_person'] = {'easygoing': int((pt == 0).sum()), 'tidy': int((pt == 1).sum())}
    h2['model_seed'], h2['ckpt'], h2['smoke'] = int(Z['seed']), str(Z['ckpt']), bool(Z['smoke'])
    h2['secs'] = round(time.time() - t0, 1)
    return h2, ht_acts


def run_all(Z, log=print, nhead_path=None):
    t0 = time.time()
    T = Tables(Z, nhead_path=nhead_path)
    log(f'N head fitted ({len(T.N_secs)} fits, {sum(T.N_secs):.0f}s); {T.D} training days')
    greedy_fn, curve = train_chooser(T, log)
    sealed = np.where(Z['sess_split'] == 1)[0]
    ch_acts, _, _, _ = play(T, sealed, lambda X, rounds: greedy_fn(X, rounds))
    h2, ht_acts = run_h2(Z, T, None, log)
    eager = np.where(T.has, 2, 0)
    rounds_s = np.where(T.round_day == 0)[0]
    sidx = {s: i for i, s in enumerate(sealed)}
    pos = np.array([sidx[s] for s in Z['round_sess'][rounds_s]])
    Ls = T.L[sealed].astype(float)

    def effort(acts):
        saved = np.bincount(pos, weights=T.rew(acts[rounds_s], rounds_s), minlength=len(sealed))
        return Ls - saved
    oracle_save = np.bincount(pos, weights=_any_wanted(T, rounds_s).astype(float),
                              minlength=len(sealed))
    arms = {'NONE': Ls.copy(), 'EAGER-TOOL': effort(eager), 'HELPER-TOOL': effort(ht_acts), 'CHOOSER': effort(ch_acts),
            'ORACLE': Ls - oracle_save}
    ptype_s = Z['sess_ptype'][sealed]
    res = {'n_sealed_sessions': int(len(sealed)), 'model_seed': int(Z['seed']), 'ckpt': str(Z['ckpt']),
           'smoke': bool(Z['smoke']), 'mean_L': float(Ls.mean()), 'n_training_days': T.D,
           'constants': {'HIDDEN': HIDDEN, 'LR': LR, 'EPOCHS_PER_DAY': EPOCHS_PER_DAY, 'ENT_W': ENT_W, 'CHOOSER_SEED': CHOOSER_SEED,
                         'TRAIN_SEED': TRAIN_SEED, 'SEALED_SEED': SEALED_SEED, 'TOOL_COST': TOOL_COST, 'COST': COST,
                         'P_THANKS': P_THANKS},
           'mean_effort': {'all': {k: float(v.mean()) for k, v in arms.items()},
                           'easygoing': {k: float(v[ptype_s == 0].mean()) for k, v in arms.items()},
                           'tidy': {k: float(v[ptype_s == 1].mean()) for k, v in arms.items()}},
           'n_by_person': {'easygoing': int((ptype_s == 0).sum()), 'tidy': int((ptype_s == 1).sum())},
           'training_curve': curve}
    for name, d in (('CHOOSER-HELPER-TOOL', arms['CHOOSER'] - arms['HELPER-TOOL']),
                    ('CHOOSER-EAGER-TOOL', arms['CHOOSER'] - arms['EAGER-TOOL'])):
        lo, hi = P.boot(d)
        res[name] = {'diff': float(d.mean()), 'ci95': [lo, hi]}
    r1, r2 = res['CHOOSER-HELPER-TOOL'], res['CHOOSER-EAGER-TOOL']
    res['H1-1'] = {'verdict': 'PASS' if (r1['diff'] <= -0.10 and r1['ci95'][1] < 0) else
                   ('PROVED WRONG (on this seed)' if r1['diff'] >= 0 else 'neither pass nor wrong'),
                   'rule': 'pass: CHOOSER - HELPER-TOOL <= -0.10 and CI upper < 0; wrong: diff >= 0 on either seed'}
    res['H1-2'] = {'verdict': 'PASS' if (r2['diff'] <= -0.05 and r2['ci95'][1] < 0) else 'not passed (reported)',
                   'rule': 'pass: CHOOSER - EAGER-TOOL <= -0.05 and CI upper < 0'}
    # offer rate after a "thanks" round vs after a plain round (rounds with a previous round), chooser, sealed
    sh = (ch_acts[rounds_s] > 0)
    later = T.ridx[rounds_s] > 0
    th = T.thanks_prev[rounds_s] == 1
    after_th, after_plain = sh[later & th], sh[later & ~th]
    gap = 100 * (after_th.mean() - after_plain.mean()) if len(after_th) and len(after_plain) else float('nan')
    res['H1-3'] = {'offer_rate_after_thanks': float(after_th.mean()), 'offer_rate_after_plain': float(after_plain.mean()),
                   'n_after_thanks': int(len(after_th)), 'n_after_plain': int(len(after_plain)), 'gap_points': float(gap),
                   'verdict': 'PASS' if abs(gap) <= 3 else ('PROVED WRONG (on this seed)' if abs(gap) > 5 else 'neither pass nor wrong'),
                   'rule': 'pass: |gap| <= 3 points; wrong: |gap| > 5 points'}
    n_shown, n_tool = int(sh.sum()), int((ch_acts[rounds_s] == 2).sum())
    share = n_tool / n_shown if n_shown else float('nan')
    res['H1-4'] = {'shown_extras': n_shown, 'used_tool': n_tool, 'share_tool': share,
                   'verdict': 'meets 90%' if share >= 0.9 else 'below 90% (reported)', 'rule': 'reported; >= 90% of shown extras used the tool'}
    res['H1-1_to_3_all_pass_this_seed'] = bool(res['H1-1']['verdict'] == 'PASS' and res['H1-2']['verdict'] == 'PASS'
                                               and res['H1-3']['verdict'] == 'PASS')
    # chooser action shares by person type and by position
    ca = ch_acts[rounds_s]
    pt_r = T.ptype[rounds_s]
    has_r = T.has[rounds_s]

    def shares(mask):
        m = mask & has_r
        n = int(m.sum())
        return {'n_rounds_with_candidate': n, **{ACTIONS[i]: float((ca[m] == i).mean()) if n else None for i in range(3)}}
    res['chooser_shares'] = {'all': shares(np.ones(len(rounds_s), bool)),
                             'easygoing': shares(pt_r == 0), 'tidy': shares(pt_r == 1),
                             **{f'position {t + 1}': shares(T.ridx[rounds_s] == t) for t in range(4)}}
    # per-arm extras summary (sealed)
    def arm_stats(acts):
        a = acts[rounds_s]
        m = a > 0
        good = T.wt[rounds_s] & ((a == 2) | T.rt[rounds_s])
        return {'extras_per_session': float(m.sum() / len(sealed)), 'tool_calls_per_session': float((a == 2).sum() / len(sealed)),
                'wanted_share': float(T.wt[rounds_s][m].mean()) if m.any() else None,
                'accepted_share': float(good[m].mean()) if m.any() else None}
    res['arm_extras'] = {'EAGER-TOOL': arm_stats(eager), 'HELPER-TOOL': arm_stats(ht_acts), 'CHOOSER': arm_stats(ch_acts)}
    res['oracle_saving_per_session'] = float(oracle_save.mean())
    res['h2'] = h2
    res['run_secs'] = round(time.time() - t0, 1)
    return res


def _any_wanted(T, rounds):
    """ORACLE: a wanted candidate exists on the menu (the tool makes it right)."""
    out = np.zeros(len(rounds), bool)
    for i, r in enumerate(rounds):
        out[i] = T.cwant[T.ptr[r]:T.ptr[r + 1]].any()
    return out


def h2_md(h2):
    e = h2['mean_effort']
    md = ['', '## H-2: HELPER-REACT (HELPER-TOOL + reaction counts and thanks in the value head)', '',
          '| Arm | all | easygoing | tidy |', '|---|---|---|---|']
    md += [f"| {k} | {e['all'][k]:.4f} | {e['easygoing'][k]:.4f} | {e['tidy'][k]:.4f} |" for k in e['all']]
    d, g = h2['HELPER-REACT-HELPER-TOOL'], h2['H2-3']
    md += ['', f"HELPER-REACT - HELPER-TOOL: {d['diff']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}] (10,000 resamples, seed 0)", '',
           f"H2-1: {h2['H2-1']['verdict']}  ({h2['H2-1']['rule']})",
           f"H2-3: {g['verdict']}  offer rate after thanks {100 * g['offer_rate_after_thanks']:.1f}% (n {g['n_after_thanks']}) vs after plain "
           f"{100 * g['offer_rate_after_plain']:.1f}% (n {g['n_after_plain']}), gap {g['gap_points']:+.2f} points  ({g['rule']})",
           f"H-2 passes on this seed: {h2['H2_pass_this_seed']} (H-2 passes only if so on both seeds)", '',
           '| Extras rate in the next round | after removed | after left |', '|---|---|---|']
    fm = lambda t: f'{100 * t[0]:.1f}% (n {t[1]})' if t[0] is not None else f'- (n {t[1]})'
    for k, v in h2['extras_rate_after_reaction'].items():
        md.append(f"| {k} | {fm(v['after_removed'])} | {fm(v['after_left'])} |")
    return md


def write_h2_outputs(h2, out):
    h2 = dict(h2)
    h2['h1_chooser_py_sha256'] = code_sha()
    h2['p1_sessions_py_sha256'] = code_sha(P.__file__)
    json.dump(h2, open(os.path.join(out, 'RESULT-H2.json'), 'w'), indent=1)
    md = [f"# H-2 results, model seed {h2['model_seed']}{' (SMOKE)' if h2['smoke'] else ''}", f"checkpoint: {h2['ckpt']}",
          f"sealed sessions by person: {h2['n_by_person']}"] + h2_md(h2) + ['', f"h1_chooser.py sha256: {h2['h1_chooser_py_sha256']}",
                                                                         f"p1_sessions.py sha256: {h2['p1_sessions_py_sha256']}"]
    open(os.path.join(out, 'RESULT-H2.md'), 'w').write('\n'.join(md) + '\n')
    return '\n'.join(md)


def write_outputs(res, out):
    res = dict(res)
    res['h1_chooser_py_sha256'] = code_sha()
    res['p1_sessions_py_sha256'] = code_sha(P.__file__)
    json.dump(res, open(os.path.join(out, 'RESULT.json'), 'w'), indent=1)
    e = res['mean_effort']
    arms = list(e['all'])
    md = [f"# H-1 learned help chooser, model seed {res['model_seed']}{' (SMOKE)' if res['smoke'] else ''}", '',
          f"checkpoint: {res['ckpt']}", f"sealed sessions: {res['n_sealed_sessions']} "
          f"(easygoing {res['n_by_person']['easygoing']}, tidy {res['n_by_person']['tidy']}), mean requests {res['mean_L']:.3f}, "
          f"training days {res['n_training_days']}", '',
          '| Arm | all | easygoing | tidy |', '|---|---|---|---|']
    md += [f"| {k} | {e['all'][k]:.4f} | {e['easygoing'][k]:.4f} | {e['tidy'][k]:.4f} |" for k in arms]
    md += ['', 'Mean effort = person actions per session + 0.02 per tool call (lower is better).', '',
           '| Paired difference | mean | 95% interval (10,000 resamples, seed 0) |', '|---|---|---|']
    for n in ('CHOOSER-HELPER-TOOL', 'CHOOSER-EAGER-TOOL'):
        md.append(f"| {n} | {res[n]['diff']:+.4f} | [{res[n]['ci95'][0]:+.4f}, {res[n]['ci95'][1]:+.4f}] |")
    h3, h4 = res['H1-3'], res['H1-4']
    md += ['', f"H1-1: {res['H1-1']['verdict']}  ({res['H1-1']['rule']})", f"H1-2: {res['H1-2']['verdict']}  ({res['H1-2']['rule']})",
           f"H1-3: {h3['verdict']}  offer rate after thanks {100 * h3['offer_rate_after_thanks']:.1f}% (n {h3['n_after_thanks']}) vs after plain "
           f"{100 * h3['offer_rate_after_plain']:.1f}% (n {h3['n_after_plain']}), gap {h3['gap_points']:+.2f} points  ({h3['rule']})",
           f"H1-4: {h4['verdict']}  {h4['used_tool']} of {h4['shown_extras']} shown extras used the tool ({100 * h4['share_tool']:.1f}%)",
           f"H1-1..3 all pass on this seed: {res['H1-1_to_3_all_pass_this_seed']} (H-1 passes only if so on both seeds)", '',
           '| CHOOSER action shares (sealed, rounds with a candidate) | rounds | quiet | own answer | tool |', '|---|---|---|---|---|']
    for k, v in res['chooser_shares'].items():
        md.append(f"| {k} | {v['n_rounds_with_candidate']} | " + ' | '.join(f"{v[a]:.3f}" if v[a] is not None else '-' for a in ACTIONS) + ' |')
    md += ['', '| Arm | extras/session | tool calls/session | wanted share | accepted share |', '|---|---|---|---|---|']
    for k, v in res['arm_extras'].items():
        f = lambda x: f'{x:.3f}' if x is not None else '-'
        md.append(f"| {k} | {v['extras_per_session']:.3f} | {v['tool_calls_per_session']:.3f} | {f(v['wanted_share'])} | {f(v['accepted_share'])} |")
    md += ['', f"ORACLE saving per session: {res['oracle_saving_per_session']:.4f}", '',
           '| Training day | reward/round | quiet | own | tool | entropy |', '|---|---|---|---|---|---|']
    md += [f"| {c['day']} | {c['mean_reward_per_round']:+.4f} | {c['share_quiet']:.2f} | {c['share_own']:.2f} | {c['share_tool']:.2f} | "
           f"{c['entropy']:.3f} |" for c in res['training_curve']]
    md += h2_md(res['h2'])
    md += ['', f"constants: {json.dumps(res['constants'])}", f"h1_chooser.py sha256: {res['h1_chooser_py_sha256']}",
           f"p1_sessions.py sha256: {res['p1_sessions_py_sha256']}"]
    open(os.path.join(out, 'RESULT.md'), 'w').write('\n'.join(md) + '\n')
    return '\n'.join(md)


def do_run(a):
    import torch
    torch.set_num_threads(a.threads)
    Z = P.load_cache(a.dir)
    nh = os.path.join(a.dir, 'nhead.npz')
    if a.arms == 'h2':
        T = Tables(Z, nhead_path=nh)
        h2, _ = run_h2(Z, T, None, P.log)
        print(write_h2_outputs(h2, a.out or a.dir))
        return
    res = run_all(Z, P.log, nhead_path=nh)
    print(write_outputs(res, a.out or a.dir))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('cache')
    c.add_argument('--seed', type=int, required=True)
    c.add_argument('--ckpt', required=True)
    c.add_argument('--out', required=True)
    c.add_argument('--threads', type=int, default=1)
    c.add_argument('--smoke', action='store_true')
    r = sub.add_parser('run')
    r.add_argument('--dir', required=True)
    r.add_argument('--out', default=None)
    r.add_argument('--threads', type=int, default=1)
    r.add_argument('--arms', choices=['all', 'h2'], default='all',
                   help='h2: only NONE/EAGER-TOOL/HELPER-TOOL/HELPER-REACT (no CHOOSER training); writes RESULT-H2.*')
    a = ap.parse_args(argv)
    do_cache(a) if a.cmd == 'cache' else do_run(a)


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
