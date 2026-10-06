"""C1 and C2b marks and ordered verdicts (roadmap sections 6 and 7), from per-parent results. Points = percentage points (inputs are shares in 0..1).
Intervals are 95% t-intervals over parents on paired differences. Nothing here reads a model.

parents: list (one per parent) of dict arm -> metrics; arms N, W, R, H, Hw, PC. Metrics used: luck, reach4, reach32, stop_luck, aim, first_try,
skills (pooled-5 practised skills, share), donor_luck, rules_floor, unresolved. Flags in `flags`: checkers_disagree, gate_pass, placebo_too_close."""
import math

T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
        13: 2.160, 14: 2.145, 15: 2.131, 20: 2.086, 30: 2.042}


def t_crit(df):
    """Two-sided 95% t value; between table entries the larger (smaller-df) value, so intervals are never too narrow."""
    return T975[max(k for k in T975 if k <= max(df, 1))]


def paired(parents, a, b, metric):
    """-> (mean difference a - b in points, lo, hi, every_parent_a_above_b). One parent gives a degenerate interval (lo = hi = mean)."""
    d = [100 * (p[a][metric] - p[b][metric]) for p in parents]
    n = len(d)
    m = sum(d) / n
    if n < 2:
        return m, m, m, all(x > 0 for x in d)
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1))
    h = t_crit(n - 1) * sd / math.sqrt(n)
    return m, m - h, m + h, all(x > 0 for x in d)


def c1_marks(parents):
    P = lambda a, b, k: paired(parents, a, b, k)
    m = {}
    wn, wr = P('W', 'N', 'luck'), P('W', 'R', 'luck')
    m['L1'] = wn[0] >= 10 and wn[3]
    m['L2'] = wr[0] >= 8 and wr[1] > 0
    gr, gn = P('W', 'R', 'aim'), P('W', 'N', 'aim')
    m['G0'] = gr[0] >= 5 and gr[1] > 0 and gn[1] > 0
    m['G1'] = not (P('W', 'N', 'reach4')[2] < -2)
    m['G2'] = P('W', 'R', 'stop_luck')[0] >= 4
    m['G3'] = all(100 * (p['N']['skills'] - p['W']['skills']) <= 2 for p in parents)
    f_n, f_r = P('W', 'N', 'first_try'), P('W', 'R', 'first_try')
    m['F1'] = f_n[0] >= 5 and f_n[1] > 0 and f_r[0] >= 5 and f_r[1] > 0
    m['lesion_donor'] = all(p['W']['donor_luck'] <= p['W']['rules_floor'] for p in parents)
    m['PC'] = P('PC', 'N', 'luck')[0] >= 10
    hw, hh = P('H', 'W', 'reach32'), P('H', 'Hw', 'reach32')
    m['H_question'] = hw[0] >= 5 and hw[1] > 0 and hh[0] > 0
    m['_diffs'] = dict(W_N_luck=wn[:3], W_R_luck=wr[:3], W_R_aim=gr[:3], W_N_aim=gn[:3], W_N_reach4=P('W', 'N', 'reach4')[:3],
                       W_R_stop=P('W', 'R', 'stop_luck')[:3], W_N_first=f_n[:3], W_R_first=f_r[:3], PC_N_luck=P('PC', 'N', 'luck')[:3],
                       H_W_reach32=hw[:3], H_Hw_reach32=hh[:3])
    return m


def c1_verdict(parents, flags):
    """Ordered verdicts: void -> gate stop -> placebo too close -> PASS (named) -> rules only -> gain with harm -> proved wrong -> not shown."""
    m = c1_marks(parents)
    unres = max(max(p[a].get('unresolved', 0) for a in p) for p in parents)
    if flags.get('checkers_disagree') or unres > 0.01 or not m['lesion_donor']:
        return 'void', m
    if not flags.get('gate_pass', True):
        return 'gate stop', m
    if flags.get('placebo_too_close'):
        return 'placebo too close', m
    if all(m[k] for k in ('L1', 'L2', 'G0', 'G1', 'G2', 'G3')):
        return ('PASS with first answers' if m['F1'] else 'PASS, search only'), m
    if m['L1'] and not m['G0']:
        return 'rules only', m
    if not m['G3'] and m['L1'] and m['L2']:
        return 'gain with harm', m
    d = m['_diffs']
    if m['PC'] and d['W_R_luck'][2] < 5 and d['W_R_aim'][2] < 3:
        return 'proved wrong', m
    return 'not shown', m


def c2b_verdict(parents):
    """C2b (sleep on held-out rule kinds, no keys). parents: arm -> dict(first_try, reach4, skills). Pass: first try W-N >= +15 and W-R >= +10
    (intervals above 0), reach@4 and practised skills each within 2 points of N. Proved wrong: W-R upper end below +3."""
    wn, wr = paired(parents, 'W', 'N', 'first_try'), paired(parents, 'W', 'R', 'first_try')
    m = dict(first_W_N=wn[:3], first_W_R=wr[:3],
             reach4_ok=all(100 * (p['N']['reach4'] - p['W']['reach4']) <= 2 for p in parents),
             skills_ok=all(100 * (p['N']['skills'] - p['W']['skills']) <= 2 for p in parents))
    if wn[0] >= 15 and wn[1] > 0 and wr[0] >= 10 and wr[1] > 0 and m['reach4_ok'] and m['skills_ok']:
        return 'PASS', m
    if wr[2] < 3:
        return 'proved wrong', m
    return 'not shown', m
