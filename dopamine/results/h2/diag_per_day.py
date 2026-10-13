import sys, numpy as np
sys.path.insert(0, '/tmp/claude-0/h2')
from dopamine import h1_chooser as H
from dopamine import p1_sessions as P
d = sys.argv[1]
Z = P.load_cache(d)
T = H.Tables(Z, nhead_path=d + '/nhead.npz')
# instrumented copy of helper_react_actions
acts = np.zeros(T.R, int); rs = np.random.RandomState(12); x_h, rew_h = [], []; v_model = None; cnt = np.zeros((T.S, 4))
for day in list(range(1, T.D + 1)) + [0]:
    sealed = day == 0
    sess = np.where((T.Z['sess_split'] == 1) if sealed else ((T.Z['sess_split'] == 0) & (T.Z['sess_day'] == day)))[0]
    preds, nact, nr, nexp = [], 0, 0, 0
    for s in sess:
        for t in range(T.L[s]):
            r = T.first_round[s] + t
            if not T.has[r]: continue
            nr += 1
            rr = np.arange(T.ptr[r], T.ptr[r + 1]); hp = False
            if day == 1:
                c = rr[rs.randint(len(rr))] if rs.rand() < 0.5 else None; hp, pn = c is not None, 0.0
            else:
                c, pn = T.top[r], T.ptop[r]
            x = np.concatenate([[pn], T.F[T.cpid[c if c is not None else T.top[r]]], P.onehot(T.ridx[[r]])[0], cnt[s], [T.thanks_prev[r]]])[None]
            if day > 1:
                if (not sealed) and rs.rand() < 0.10: hp = True; nexp += 1
                elif v_model is not None:
                    v = v_model.predict(x)[0]; preds.append(v); hp = v > 0
            if hp:
                nact += 1; acts[r] = 2; wanted = bool(T.cwant[c] == 1)
                H.reaction_update(cnt, np.array([s]), np.array([True]), np.array([wanted]), np.array([not wanted]), np.array([T.ptype[r] == 1]), np.array([False]))
                if not sealed: x_h.append(x[0]); rew_h.append((1.0 if wanted else -T.cost[r]) - H.TOOL_COST)
    p = np.array(preds) if preds else np.zeros(1)
    print(f'day {day}: rounds {nr} acts {nact} explore {nexp} | pred mean {p.mean():+.3f} max {p.max():+.3f} >0 {np.mean(p>0):.3f} | train rows {len(x_h)} mean rew {np.mean(rew_h) if rew_h else 0:+.3f}', flush=True)
    if sealed: break
    if len(x_h) >= 5:
        v_model = P.mlp('reg', 200 + day).fit(np.array(x_h), np.array(rew_h))
        X = np.array(x_h); print('   fit: train pred >0 share %.3f, R2 %.3f; cols %d' % (np.mean(v_model.predict(X) > 0), v_model.score(X, np.array(rew_h)), X.shape[1]))
