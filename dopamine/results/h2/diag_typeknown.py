"""Post-hoc diagnostic for H-2 (reported only, not a mark): headroom from knowing the person.
TYPE-KNOWN = HELPER-TOOL whose value inputs gain the true person type (0 easygoing, 1 tidy) from round 1.
Everything else as helper_react_actions after the sealed-day fix (same RNG stream, MLP, seeds, exploration, refits)."""
import sys, json, numpy as np
sys.path.insert(0, '/tmp/claude-0/h2')
from dopamine import h1_chooser as H
from dopamine import p1_sessions as P

def typeknown_actions(T):
    acts = np.zeros(T.R, int); rs = np.random.RandomState(12); x_h, rew_h = [], []; v_model = None
    for day in list(range(1, T.D + 1)) + [0]:
        sealed = day == 0
        sess = np.where((T.Z['sess_split'] == 1) if sealed else ((T.Z['sess_split'] == 0) & (T.Z['sess_day'] == day)))[0]
        for s in sess:
            for t in range(T.L[s]):
                r = T.first_round[s] + t
                if not T.has[r]: continue
                rr = np.arange(T.ptr[r], T.ptr[r + 1]); hp = False
                if day == 1:
                    c = rr[rs.randint(len(rr))] if rs.rand() < 0.5 else None; hp, pn = c is not None, 0.0
                else:
                    c, pn = T.top[r], T.ptop[r]
                x = np.concatenate([[pn], T.F[T.cpid[c if c is not None else T.top[r]]], P.onehot(T.ridx[[r]])[0], [float(T.ptype[r] == 1)]])[None]
                if day != 1:
                    if (not sealed) and rs.rand() < 0.10: hp = True
                    elif v_model is not None: hp = v_model.predict(x)[0] > 0
                if hp:
                    acts[r] = 2
                    if not sealed: x_h.append(x[0]); rew_h.append((1.0 if T.cwant[c] == 1 else -T.cost[r]) - H.TOOL_COST)
        if sealed: break
        if len(x_h) >= 5: v_model = P.mlp('reg', 200 + day).fit(np.array(x_h), np.array(rew_h))
    return acts

d = sys.argv[1]
Z = P.load_cache(d); T = H.Tables(Z, nhead_path=d + '/nhead.npz')
sealed = np.where(Z['sess_split'] == 1)[0]; rounds_s = np.where(T.round_day == 0)[0]
sidx = {s: i for i, s in enumerate(sealed)}; pos = np.array([sidx[s] for s in Z['round_sess'][rounds_s]]); Ls = T.L[sealed].astype(float)
eff = lambda a: Ls - np.bincount(pos, weights=T.rew(a[rounds_s], rounds_s), minlength=len(sealed))
ht, tk = H.helper_tool_actions(T), typeknown_actions(T)
e_ht, e_tk = eff(ht), eff(tk); pt = Z['sess_ptype'][sealed]
dd = e_tk - e_ht; lo, hi = P.boot(dd)
out = {'seed': int(Z['seed']), 'HELPER-TOOL': {'all': e_ht.mean(), 'easygoing': e_ht[pt == 0].mean(), 'tidy': e_ht[pt == 1].mean()},
       'TYPE-KNOWN': {'all': e_tk.mean(), 'easygoing': e_tk[pt == 0].mean(), 'tidy': e_tk[pt == 1].mean()},
       'TYPE-KNOWN-HELPER-TOOL': {'diff': dd.mean(), 'ci95': [lo, hi]},
       'extras_per_session': {'HELPER-TOOL': {k: float((ht[rounds_s][pt[pos] == v] > 0).sum() / (pt == v).sum()) for k, v in (('easygoing', 0), ('tidy', 1))},
                              'TYPE-KNOWN': {k: float((tk[rounds_s][pt[pos] == v] > 0).sum() / (pt == v).sum()) for k, v in (('easygoing', 0), ('tidy', 1))}}}
out = json.loads(json.dumps(out, default=float))
json.dump(out, open(d + '/DIAG-TYPEKNOWN.json', 'w'), indent=1); print(json.dumps(out, indent=1))
