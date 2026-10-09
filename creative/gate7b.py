"""Roadmap 7b "Notebook gate (D6)": does a tiny LEARNED gate replace the hand gate (theta 0.9, the 0.99 skills quantile, c = 50) of arm M without losing its gain or adding harm? CPU.
Reads skills TRAIN rows (gate training + replay), C2 pool / warm rows (night records, the 512 old notes), C2 DEV and skills DEV (MEASURE only); C2 test / labelled never opened.
  python3 -m creative.gate7b run --nprime ~/c7d/s100/Nprime.pt ~/c7d/s101/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --out DIR --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --threads 1
  python3 -m creative.gate7b report --out DIR --parents s100 s101

Three models share N' 's weights: none (N' alone), H (today's gate: fastsleep.m_knn with MEMORY_C2B), L (the learned gate). The notebook is arm M's: k 16, tau 0.05, answer note off,
night-1 W records + 512 practised-kind old notes. Per write step the hand gate and boost are replaced by  w = softplus(MLP(features))  and
  op / a / b logits += w x (softmax-weighted one-hot votes of the 16 nearest notes)
Features (26): the 16 top cosine similarities (descending), the largest entry of each of the op / a / b vote vectors (vote shares), and the step number ONE-HOT (7). The 19 continuous
features are standardised with the training set's mean / std; nothing is compared with a similarity and nothing is a fixed boost on the gate's path.
Training: only the gate (449 weights) trains; every base weight is frozen, so the base op / pointer logits and the vote vectors are cached once per (row, step) and the loss is the head
loss (cross-entropy on the op, marginal NLL on the a / b slot sets, the same targets and weights as fastsleep.head_loss) of the boosted logits. Two sets, equal size: (1) the night's records,
each queried with itself left out of the notebook (its own entries masked); (2) as many skills TRAIN rows as records, their gold steps, nothing masked. DEV is never used for training."""
import argparse, ast, copy, inspect, json, math, os, random, textwrap, time
import torch
import torch.nn as nn
import torch.nn.functional as F
from creative import c2_stones, fewshot, legal, rules_real as R, sleep, stones
from creative import fastsleep as fs
from creative.night7d import _w1_records
from creative.repair7d import subsample
from creative.sleep7d import DATA, _cached, _h, _hstate, _limit, _log, _sha_file, greedy_rows, pyfit
from creative import sampler
from custom_io.data import load_rows
from custom_io.evalx import CHAIN5, evaluate, is_hit
from custom_io.models import progparse as pp

K, TAU, OLD, N_STEPS = 16, 0.05, 512, pp.N_RES              # arm M's notebook: k 16, tau 0.05, 512 old notes; 7 write steps
N_FEAT = K + 3 + N_STEPS                                      # 16 sims + 3 vote shares + step one-hot = 26
N_CONT = K + 3                                                # the continuous features (standardised)
HIDDEN = 16
TRAIN = dict(steps=600, lr=0.03, seed=0, hidden=HIDDEN)       # full-batch Adam on the cached rows; fixed by the roadmap's D6 ruling 10-09 (no tuning on DEV or after a result)
HAND = dict(fs.MEMORY_C2B[1])                                 # H = today's gate (c 50, theta 0.9, cal 0.99, old 512, ans 0)

MARKS = {
    'gain': '(1) gain kept: C2 DEV pooled greedy first try, L - none >= 0.9 x (H - none), both parents',
    'harm': "(2) no more harm: L's hurt rows (right -> wrong vs none) on the two skills sets together (6,800 rows) <= H's + 7, AND harm vs none <= 2.0 points on each set separately (1,000 chain-5; 5,800 non-chain)",
    'recall': "(3) practised recall: L's practised reach@32 (256 fresh add/mult questions) >= H's - 2 points",
    'audit': '(4) audit: no hand constant (theta, theta_t, c) is read or compared with a similarity and no fixed boost is on the learned gate path; boost = gate(features) x votes (code check + unit tests)',
    'proved_wrong': "on BOTH parents: L keeps under 0.5 x of H's C2 DEV gain AND L's hurt count (the 6,800 skills rows) is not below H's"}
GAIN_FRAC, HURT_SLACK, HARM_POINTS, RECALL_POINTS, WRONG_FRAC = 0.9, 7, 2.0, 2.0, 0.5
CHAIN5_N, NONCHAIN_N = 1000, 5800


# ---------------------------------------------------------------- pure marks
def compare(none_hits, hits, none_ans, ans):
    """Pure. One model against none on the same rows. changed = the answer differs from none's; helped = wrong -> right; hurt = right -> wrong. -> dict."""
    n = len(none_hits)
    assert n == len(hits) == len(none_ans) == len(ans)
    helped = sum(1 for a, b in zip(none_hits, hits) if not a and b)
    hurt = sum(1 for a, b in zip(none_hits, hits) if a and not b)
    changed = sum(1 for x, y in zip(none_ans, ans) if x != y)
    right_none, right = sum(map(int, none_hits)), sum(map(int, hits))
    return dict(n=n, right_none=right_none, right=right, helped=helped, hurt=hurt, changed=changed, coverage=changed / max(n, 1), net_points=100 * (right - right_none) / max(n, 1))


def parent_marks(x):
    """Pure. x = dict(gain_H, gain_L (C2 DEV first-try points vs none), hurt_H, hurt_L (rows, the two skills sets together), harm_L = {set: points vs none},
    reach_H, reach_L (practised reach@32, points), audit (bool)). -> the four marks and proved_wrong on one parent."""
    r6 = lambda v: round(v, 6)
    gain = r6(x['gain_L']) >= r6(GAIN_FRAC * x['gain_H'])
    harm = x['hurt_L'] <= x['hurt_H'] + HURT_SLACK and all(r6(v) <= HARM_POINTS for v in x['harm_L'].values())
    recall = r6(x['reach_L']) >= r6(x['reach_H'] - RECALL_POINTS)
    audit = bool(x['audit'])
    wrong = r6(x['gain_L']) < r6(WRONG_FRAC * x['gain_H']) and x['hurt_L'] >= x['hurt_H']
    return dict(gain=bool(gain), harm=bool(harm), recall=bool(recall), audit=audit, passes=bool(gain and harm and recall and audit), proved_wrong=bool(wrong))


def verdict(per_parent, n_expected=2):
    """Pure. per_parent {parent: parent_marks dict}. PROVED WRONG when proved_wrong on every parent; PASS when every mark holds on every parent; else FAIL (incomplete when parents are missing)."""
    if len(per_parent) < n_expected:
        return f'incomplete ({len(per_parent)} of {n_expected})'
    if all(m['proved_wrong'] for m in per_parent.values()):
        return 'PROVED WRONG'
    return 'PASS' if all(m['passes'] for m in per_parent.values()) else 'FAIL'


# ---------------------------------------------------------------- features and votes (the ONLY place similarities are used; no threshold)
def neighbour_votes(z, keys, op, a, b, t, k=K, tau=TAU, n_ops=len(pp.OPS), n_slots=pp.M, drop=None):
    """Query states z [B,d] against one step's notebook (keys [E,d] unit, forced op / a-slot / b-slot ids [E]). drop = optional bool [B,E] of entries left out (leave-one-out).
    -> feats [B, N_FEAT], vop [B,n_ops], va / vb [B,n_slots]: top-k similarities descending (padded with -1), vote shares (the largest vote entries), step one-hot; and the
    softmax(sim / tau)-weighted one-hot votes (each row sums to 1)."""
    sim = F.normalize(z.float(), dim=-1) @ keys.T
    sim = sim if drop is None else sim.masked_fill(drop, -1.0)
    top, ix = sim.topk(min(k, sim.shape[1]), -1)
    w = (top / tau).softmax(-1)
    vote = lambda vals, n: torch.zeros(w.shape[0], n).scatter_add_(1, vals[ix], w)
    vop, va, vb = vote(op, n_ops), vote(a, n_slots), vote(b, n_slots)
    sims = F.pad(top, (0, k - top.shape[1]), value=-1.0)
    onehot = F.one_hot(torch.full((w.shape[0],), t), N_STEPS).float()
    feats = torch.cat([sims, vop.max(-1, keepdim=True).values, va.max(-1, keepdim=True).values, vb.max(-1, keepdim=True).values, onehot], -1)
    return feats, vop, va, vb


class Gate(nn.Module):
    """w = softplus(MLP(standardised features)) >= 0. No threshold, no constant boost. 26 -> 16 -> 1 (449 weights)."""

    def __init__(self, hidden=HIDDEN):
        super().__init__()
        self.register_buffer('mu', torch.zeros(N_FEAT))
        self.register_buffer('sd', torch.ones(N_FEAT))
        self.net = nn.Sequential(nn.Linear(N_FEAT, hidden), nn.ReLU(), nn.Linear(hidden, 1))

    def fit_stats(self, feats):
        f = feats.reshape(-1, N_FEAT)[:, :N_CONT]
        self.mu[:N_CONT] = f.mean(0)
        self.sd[:N_CONT] = f.std(0).clamp(min=1e-4)

    def forward(self, feats):
        return F.softplus(self.net((feats - self.mu) / self.sd)).squeeze(-1)


def boost(gate, feats, vop, va, vb):
    """The learned boost: gate(features) x votes. -> (op, a, b) logit additions and the weight."""
    w = gate(feats)
    return w[..., None] * vop, w[..., None] * va, w[..., None] * vb, w


# ---------------------------------------------------------------- the notebook and the frozen-logit cache
@torch.no_grad()
def build_notebook(m, recs, old_recs, vocab, device):
    """Arm M's notebook on frozen weights: per write step (keys, op, a slot, b slot) over the records that have a program, the night's records first, then the old notes
    (same entries as fastsleep.build_memory on recs + old). -> (steps, f_rec = head_inputs of recs, has_rec = bool per record)."""
    f_rec = fs.head_inputs(m, recs, vocab, device)
    f_old = fs.head_inputs(m, old_recs, vocab, device) if old_recs else None
    first = lambda mask: mask.float().argmax(-1)
    steps = []
    for t in range(N_STEPS):
        parts = [(f['z'][f['has'], t], f['op'][f['has'], t], first(f['a'][f['has'], t]), first(f['b'][f['has'], t])) for f in (f_rec, f_old) if f is not None]
        steps.append(tuple(torch.cat([p[i] for p in parts], 0) for i in range(4)))
    return steps, f_rec, f_rec['has'].clone()


def loo_drop(group_q, group_e):
    """Leave-one-out mask [Q,E]: query i drops notebook entry j when they share a group id (group -1 = never dropped). Pure."""
    gq, ge = torch.as_tensor(group_q), torch.as_tensor(group_e)
    return (gq[:, None] == ge[None, :]) & (gq[:, None] >= 0)


@torch.no_grad()
def build_cache(m, f, steps, group_q=None, group_e=None, k=K, tau=TAU, bs=128):
    """Frozen-weight cache for query rows f (head_inputs): per (row, step) the base op / a / b logits exactly as the live model computes them (op_head(z), ptr(q(z), k_slot(S), ok)),
    the features and vote vectors against the notebook `steps`, and the gold targets. group_q / group_e (ids; -1 = none) drop the matching notebook entries (leave-one-out)."""
    n = f['z'].shape[0]
    drop = loo_drop(group_q, group_e) if group_q is not None else None
    n_ops = m.op_head.out_features
    out = {k_: [] for k_ in ('feats', 'vop', 'va', 'vb', 'lop', 'la', 'lb')}
    for s in range(0, n, bs):
        z, S, ok = f['z'][s:s + bs], f['S'][s:s + bs], f['ok'][s:s + bs]
        Kk = m.k_slot(S)
        per = {k_: [] for k_ in out}
        for t in range(N_STEPS):
            ke, o, a, b = steps[t]
            ft, vo, va, vb = neighbour_votes(z[:, t], F.normalize(ke, dim=-1), o, a, b, t, k, tau, n_ops, pp.M, None if drop is None else drop[s:s + bs][:, :ke.shape[0]])
            for name, v in (('feats', ft), ('vop', vo), ('va', va), ('vb', vb), ('lop', m.op_head(z[:, t]).float()),
                            ('la', m.ptr(m.q_a(z[:, t]), Kk[:, t], ok[:, t])), ('lb', m.ptr(m.q_b(z[:, t]), Kk[:, t], ok[:, t]))):
                per[name].append(v)
        for k_ in out:
            out[k_].append(torch.stack(per[k_], 1))
    c = {k_: torch.cat(v, 0) for k_, v in out.items()}
    c.update(op=f['op'], A=f['a'], B=f['b'], has=f['has'])
    return c


def boosted_loss(c, w, w_noop, idx=None):
    """fastsleep.head_loss restricted to its op and operand terms, on cached base logits + w x votes (w [n,7]). Same targets and row weights."""
    sel = (lambda x: x) if idx is None else (lambda x: x[idx])
    lop_, la_, lb_, vop, va, vb = (sel(c[k_]) for k_ in ('lop', 'la', 'lb', 'vop', 'va', 'vb'))
    w = sel(w)
    op, A, Bm, has = sel(c['op']), sel(c['A']), sel(c['B']), sel(c['has'])
    B = op.shape[0]
    w_row = torch.where(has, 1.0, w_noop)
    comm = torch.isin(op, torch.tensor(pp.COMM))
    lop = lptr = 0.0
    for s in range(N_STEPS):
        ws = w[:, s, None]
        lg = lop_[:, s] + ws * vop[:, s]
        lop = lop + (F.cross_entropy(lg, op[:, s], reduction='none') * w_row).mean()
        pa, pb = (la_[:, s] + ws * va[:, s]).log_softmax(-1), (lb_[:, s] + ws * vb[:, s]).log_softmax(-1)
        ga, gb = A[:, s], Bm[:, s]
        lab = torch.logsumexp(pa.masked_fill(~ga, -1e9), -1) + torch.logsumexp(pb.masked_fill(~gb, -1e9), -1)
        lba = torch.logsumexp(pa.masked_fill(~gb, -1e9), -1) + torch.logsumexp(pb.masked_fill(~ga, -1e9), -1)
        nll = -torch.where(comm[:, s], torch.logaddexp(lab, lba), lab)
        lptr = lptr + (nll * (op[:, s] > 0)).sum() / B
    return lop + lptr


def train_gate(caches, w_noop, cfg=TRAIN, log=_log):
    """Train ONLY the gate on the cached rows (dict name -> cache, equal sizes). Full-batch Adam; base weights never enter (the cache holds their logits). -> (gate, info)."""
    t0 = time.time()
    torch.manual_seed(cfg['seed'])
    names = list(caches)
    cat = {k_: torch.cat([caches[nm][k_] for nm in names], 0) for k_ in caches[names[0]]}
    sizes = [caches[nm]['op'].shape[0] for nm in names]
    gate = Gate(cfg['hidden'])
    gate.fit_stats(cat['feats'])
    opt = torch.optim.Adam(gate.parameters(), lr=cfg['lr'])
    zero = torch.zeros(cat['op'].shape[0], N_STEPS)
    loss_none = float(boosted_loss(cat, zero, w_noop))
    curve = []
    for step in range(cfg['steps']):
        loss = boosted_loss(cat, gate(cat['feats']), w_noop)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step % 50 == 0 or step == cfg['steps'] - 1:
            curve.append((step, round(float(loss.detach()), 4)))
    with torch.no_grad():
        w = gate(cat['feats'])
        final = float(boosted_loss(cat, w, w_noop))
        per_set, a = {}, 0
        for nm, sz in zip(names, sizes):
            sl = slice(a, a + sz)
            a += sz
            cs = {k_: v[sl] for k_, v in cat.items()}
            per_set[nm] = dict(rows=sz, loss_none=float(boosted_loss(cs, zero[sl], w_noop)), loss_gate=float(boosted_loss(cs, w[sl], w_noop)),
                               mean_weight_by_step=[round(float(x), 3) for x in w[sl].mean(0)])
    info = dict(cfg=dict(cfg), params=sum(p.numel() for p in gate.parameters()), loss_none=loss_none, loss_final=final, loss_curve=curve, per_set=per_set, seconds=time.time() - t0,
                note='loss = op CE + operand NLL summed over 7 steps (no mode / answer terms); full batch')
    log('gate trained', {k_: info[k_] for k_ in ('params', 'loss_none', 'loss_final')}, {nm: (round(v['loss_none'], 3), round(v['loss_gate'], 3)) for nm, v in per_set.items()})
    return gate, info


# ---------------------------------------------------------------- the live wrapper (mirrors fastsleep.Memory / m_knn)
class GateMemory:
    """Per write step t (call order, as fastsleep.Memory): the reader pre-hook resets, op_head runs once per write step and the two operand pointers right after it.
    op logits += w x vop; operand pointer logits += w x va / vb, with w = gate(neighbour_votes features). The answer pointer is never touched (answer note off)."""

    def __init__(self, steps, gate, n_ops=len(pp.OPS), n_slots=pp.M, k=K, tau=TAU):
        self.steps = [dict(keys=F.normalize(ke, dim=-1), op=o, a=a, b=b) for ke, o, a, b in steps]
        self.gate, self.n_ops, self.n_slots, self.k, self.tau = gate, n_ops, n_slots, k, tau
        self.t, self.pending = 0, []
        self.wsum, self.wn = [0.0] * len(steps), [0] * len(steps)

    def reset(self, *_):
        self.t, self.pending = 0, []

    @torch.no_grad()
    def op_bias(self, z):
        t = min(self.t, len(self.steps) - 1)
        e = self.steps[t]
        self.t += 1
        feats, vop, va, vb = neighbour_votes(z, e['keys'], e['op'], e['a'], e['b'], t, self.k, self.tau, self.n_ops, self.n_slots)
        bop, ba, bb, w = boost(self.gate, feats, vop, va, vb)
        self.wsum[t] += float(w.sum())
        self.wn[t] += w.numel()
        self.pending = [ba, bb]
        return bop.to(z.dtype)

    def wrap_ptr(self, ptr):
        def f(q, k, ok):
            out = ptr(q, k, ok)
            if self.pending and out.shape[-1] == self.n_slots:
                out = out + self.pending.pop(0).to(out.dtype)
            return out
        return f

    def mean_weights(self):
        return [round(s / n, 3) if n else None for s, n in zip(self.wsum, self.wn)]


def m_learned(N, gate, steps, vocab=None, device='cpu', k=K, tau=TAU):
    """N + learned-gate notebook, hooked as m_knn does (_MemOp on op_head, wrap_ptr on ptr, reader pre-hook reset); no answer hook. -> (model, info)."""
    m = copy.deepcopy(N)
    mem = GateMemory(steps, gate.eval(), m.op_head.out_features, pp.M, k, tau)
    m.reader.register_forward_pre_hook(mem.reset)
    m.op_head = fs._MemOp(m.op_head, mem)
    m.ptr = mem.wrap_ptr(m.ptr)
    m._mem = mem
    return m, dict(memory=int(steps[0][0].shape[0]), k=k, tau=tau, gate_params=sum(p.numel() for p in gate.parameters()), ans=0)


def check_cache_live(N, gate, steps, rows, vocab, device, k=K, tau=TAU):
    """Cached boosted logits (base cache + gate x votes) against the wrapped live model's own step logits under teacher forcing, on `rows` (nothing masked).
    -> max abs difference over op / a / b logits that are not masked (-1e9 entries excluded)."""
    f = fs.head_inputs(N, rows, vocab, device)
    c = build_cache(N, f, steps, None, None, k, tau)
    with torch.no_grad():
        o, a, b, _ = boost(gate, c['feats'], c['vop'], c['va'], c['vb'])
    m, _ = m_learned(N, gate, steps, vocab, device, k, tau)
    from custom_io.data import Dataset, collate, to_device
    diff = 0.0
    with torch.no_grad():
        bt = to_device(collate([Dataset(rows, vocab, strict=False)[i] for i in range(len(rows))]), device)
        run = m.run(bt, gold=m.gold(rows, device))
    for s, (lop, la, lb) in enumerate(run['steps']):
        for live, base, add in ((lop, c['lop'][:, s], o[:, s]), (la, c['la'][:, s], a[:, s]), (lb, c['lb'][:, s], b[:, s])):
            want = base + add
            keep = base > -1e8
            diff = max(diff, float((live.float() - want)[keep].abs().max()))
    return diff


# ---------------------------------------------------------------- audit of the gate path
GATE_PATH = (neighbour_votes, Gate.forward, boost, GateMemory.reset, GateMemory.op_bias, GateMemory.wrap_ptr)
FORBIDDEN = {'theta', 'theta_t', 'theta_ans', 'c', 'cal', 'thr', 'threshold', 'cutoff', 'MEMORY_C2B', 'HAND', 'agree', 'row_fired'}


def audit_gate_path():
    """Static audit of the learned gate's code path: no hand constant by name (theta, theta_t, c, cal, ...), no comparison except `is None` / shape-size checks, no `>=` against anything.
    -> dict(ok, problems)."""
    problems = []
    for fn in GATE_PATH:
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        for node in ast.walk(tree):
            names = [node.id] if isinstance(node, ast.Name) else [node.attr] if isinstance(node, ast.Attribute) else [node.arg] if isinstance(node, ast.arg) else \
                [kw.arg for kw in node.keywords] if isinstance(node, ast.Call) else []
            problems += [f'{fn.__qualname__}: uses {n}' for n in names if n in FORBIDDEN]
            if isinstance(node, ast.Compare):
                src = ast.unparse(node)
                if not all(isinstance(o, (ast.Is, ast.IsNot)) for o in node.ops) and not (fn is GateMemory.wrap_ptr and 'shape' in src):
                    problems.append(f'{fn.__qualname__}: comparison {src}')
            if isinstance(node, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) and fn is not GateMemory.wrap_ptr:
                problems.append(f'{fn.__qualname__}: ordering comparison')
    return dict(ok=not problems, problems=problems, functions=[fn.__qualname__ for fn in GATE_PATH])


# ---------------------------------------------------------------- scoring
def greedy_answers(model, rows, vocab, device):
    """sleep7d.greedy_rows (the helper night7d uses) plus the answer each first try gives: per row dict(kind, fit, right, written, cone, ans). ans = the accepted program's answer, else None."""
    from creative.programs import cone
    out = []
    for r, g in zip(rows, sampler.greedy_tries(model, rows, vocab, device)):
        p = fewshot.parse(r['prompt'])
        fit = right = False
        ans = None
        if pyfit(p, g.t):
            v = fewshot.verdict(p, g.t)
            fit = v[0] == 'accept'
            right = fit and str(v[2]) in r['accepted']
            ans = str(v[2]) if fit else None
        out.append(dict(kind=r['kind'], fit=fit, right=right, written=sum(1 for o in g.t.ops if o), cone=len(cone(g.t) or []), ans=ans))
    return out


def skills_scores(model, rows, device):
    """Greedy exact per skills row and the answer given (evaluate + is_hit, as harm_look.skills_hits). -> dict(hits, preds)."""
    model.eval()
    e = evaluate(model, rows, 128, device, return_preds=True)
    return dict(hits=[int(is_hit(e['preds'][r['id']], r)) for r in rows], preds=[str(e['preds'][r['id']]) for r in rows])


def practised(model, fresh, vocab, device, seed=0, n=32):
    """c2_pilot's prac(): n plain samples at temperature 1 per fresh add/mult question, reach@32. -> dict(reach32 [fraction], per_question [0/1])."""
    smp = legal.raw_samples(model, fresh, vocab, device, n=n, temperature=1.0, level=0, seed=seed)
    sc = fewshot.score_samples(fresh, smp, ks=(1, 4, 32))
    return dict(reach32=sc['reach32'], reach1=sc['reach1'], per_question=[d['reach32'] for d in sc['per_question']])


def skills_sets(rows):
    """Row indices of the two skills sets of in_dist: the chain-5 rows (the nightly guard's set) and everything else."""
    c5 = [i for i, r in enumerate(rows) if r['family'] in CHAIN5]
    return c5, [i for i, r in enumerate(rows) if r['family'] not in CHAIN5]


# ---------------------------------------------------------------- one parent
def gate_parent(nprime, out, s1dir, s3dir, skills_train, skills_data, seed=0, dev_limit=None, skills_limit=None, max_records=None, practised_limit=None, device='cpu', name=None,
                resume=True, log=_log, loo='question', train_cfg=TRAIN, old=OLD):
    """One parent's screen. DIR/<name>/gate.json is written after every stage; the gate, each model's scores and the practised reach are cached (pickles keyed on N's hash, the limits and the
    gate's weights), so a rerun resumes. Smoke-only limits (dev_limit, skills_limit, max_records, practised_limit) are recorded in the JSON."""
    nprime = os.path.expanduser(nprime)
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s3d = os.path.join(out, name), os.path.join(s3dir, name)
    os.makedirs(pdir, exist_ok=True)
    t00, c00, secs = time.time(), time.process_time(), {}
    s3 = json.load(open(os.path.join(s3d, 's3.json')))
    a3 = s3['args']
    seed0 = s3['seed']
    res = dict(nprime=nprime, name=name, spec=__doc__.split('\n')[0], marks_rules=MARKS, secs=secs, hand_gate=HAND,
               args=dict(seed=seed, night_seed=seed0, k=K, tau=TAU, old=old, loo=loo, train=dict(train_cfg), dev_limit=dev_limit, skills_limit=skills_limit, max_records=max_records,
                         practised_limit=practised_limit, s1=s1dir, s3=s3dir, skills_train=skills_train, skills_data=skills_data, threads=torch.get_num_threads()),
               smoke=bool(dev_limit or skills_limit or max_records or practised_limit),
               note='C2 pool / warm rows / DEV and skills train / DEV only; test / labelled / K_new never opened; DEV never trains the gate')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'gate.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, a3['replay_n'], seed0)
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), a3['pool_limit']))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    fresh, _ = stones.fresh_practised(256, 1, 'fresh-check')
    fresh = c2_stones._with_nums(fresh)[:practised_limit]
    srows = load_rows(os.path.join(skills_data, 'dev', 'in_dist.jsonl'))
    srows = subsample(srows, skills_limit) if skills_limit else srows
    c5, nc = skills_sets(srows)
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    for p in N.parameters():
        p.requires_grad_(False)
    shaN = _sha_file(nprime)
    res['audit'] = audit_gate_path()
    # 1. night-1 records
    t0 = time.time()
    recs, res['records'] = _w1_records(nprime, name, s1dir, s3, pool, N, vocab, device)
    secs['records'] = time.time() - t0
    if max_records:
        recs = recs[:max_records]
        res['records']['smoke_truncated_to'] = len(recs)
    save()
    # 2. notebook (frozen weights: one forward per record and per old note) and the gate's two training sets
    t0 = time.time()
    warm_old = R.warm_records(R.load_split(DATA, 'warm'))[:old]
    steps, f_rec, has = build_notebook(N, recs, warm_old, vocab, device)
    sibs = {}
    for r in recs:
        sibs[r['source']] = sibs.get(r['source'], 0) + 1
    res['records']['with_same_question_sibling'] = sum(1 for r in recs if sibs[r['source']] > 1)
    gid = [int(i) for i in range(len(recs))] if loo == 'self' else [sorted(sibs).index(r['source']) for r in recs]     # self: its own entries; question: all notes of its question
    g_e = torch.tensor([gid[i] for i in range(len(recs)) if bool(has[i])] + [-1] * (steps[0][0].shape[0] - int(has.sum())))
    g_q = torch.tensor(gid)
    secs['notebook'] = time.time() - t0
    t0 = time.time()
    n_sk = min(len(recs), len(replay))
    skills_train_rows = random.Random(seed).sample(replay, n_sk)
    gkey = _h('gate7b-gate', shaN, len(recs), res['records']['W1_night'], seed0, seed, n_sk, loo, old, dict(train_cfg), K, TAU)

    def fit():
        f_sk = fs.head_inputs(N, skills_train_rows, vocab, device)
        caches = dict(night_loo=build_cache(N, f_rec, steps, g_q, g_e), skills_train=build_cache(N, f_sk, steps, None, None))
        del f_sk
        g, info = train_gate(caches, N.w_noop, train_cfg, log)
        return dict(state={k_: v.clone() for k_, v in g.state_dict().items()}, info=info)
    got = _cached(os.path.join(pdir, 'gate.pkl'), gkey, fit, resume, log, 'gate')
    gate = Gate(train_cfg['hidden'])
    gate.load_state_dict(got['state'])
    gate.eval()
    gsha = _hstate(got['state'])
    res['gate'] = dict(got['info'], sha=gsha, features=f'{K} top sims (desc) + 3 vote shares + step one-hot ({N_STEPS}) = {N_FEAT}', architecture=f'standardise -> Linear({N_FEAT},{train_cfg["hidden"]}) -> ReLU -> Linear -> softplus')
    secs['gate'] = time.time() - t0
    res['check_cache_vs_live_maxdiff'] = check_cache_live(N, gate, steps, skills_train_rows[:16], vocab, device)
    log('cache vs live max |diff|', res['check_cache_vs_live_maxdiff'])
    save()
    # 3. models: none, H, L (lazy: built only when a score is not cached)
    cfgs = dict(none=None, H=dict(HAND), L=dict(gate=gsha))
    models = {}

    def get(label):
        if label not in models:
            if label == 'none':
                models[label] = N
            elif label == 'H':
                models[label] = fs.m_knn(N, recs, replay, vocab, device, len(recs), **HAND)[0]
            else:
                models[label] = m_learned(N, gate, steps, vocab, device)[0]
        return models[label]
    c2, sk, prac = {}, {}, {}
    res['weights_live'] = {}

    def meas(label, what, path, key, fn):
        """cached score; for L the live gate's mean weight per step during a fresh (uncached) scoring is recorded per scoring set (report only)."""
        mem = getattr(models.get(label), '_mem', None)
        if mem is not None and hasattr(mem, 'wsum'):
            mem.wsum, mem.wn = [0.0] * N_STEPS, [0] * N_STEPS
        v = _cached(path, key, fn, resume, log, f'{what} {label}')
        mem = getattr(models.get(label), '_mem', None)
        if mem is not None and hasattr(mem, 'mean_weights'):
            res['weights_live'].setdefault(label, {})[what] = mem.mean_weights()
        return v
    for label in cfgs:
        t0 = time.time()
        key = lambda what, *x: _h('gate7b', what, label, shaN, cfgs[label], seed0, len(recs), old, K, TAU, loo, *x)
        pj = lambda what: os.path.join(pdir, f'{what}_{label}.pkl')
        if label == 'L':
            get(label)                                  # build first so the weight stats are collected
        c2[label] = meas(label, 'c2', pj('c2'), key('c2', dev_limit), lambda: greedy_answers(get(label), dev, vocab, device))
        sk[label] = meas(label, 'skills', pj('skills'), key('skills', skills_data, skills_limit), lambda: skills_scores(get(label), srows, device))
        prac[label] = meas(label, 'practised', pj('practised'), key('prac', practised_limit, seed), lambda: practised(get(label), fresh, vocab, device, seed))
        secs[f'measure_{label}'] = time.time() - t0
        res.setdefault('scores', {})[label] = dict(c2_first_try=sum(d['right'] for d in c2[label]) / len(dev), skills_chain5=sum(sk[label]['hits'][i] for i in c5) / max(len(c5), 1),
                                                   skills_nonchain=sum(sk[label]['hits'][i] for i in nc) / max(len(nc), 1), practised_reach32=prac[label]['reach32'])
        log('measure', label, res['scores'][label])
        save()
    # greedy_answers must equal the helper night7d uses (checked on a few rows each run: cheap)
    ck = greedy_rows(N, dev[:8], vocab, device)
    res['greedy_helper_check'] = all(a['right'] == b['right'] and a['fit'] == b['fit'] for a, b in zip(ck, c2['none'][:8]))
    # 4. comparisons, marks
    sets = {}
    for label in ('H', 'L'):
        sets[label] = dict(
            c2_dev=compare([int(d['right']) for d in c2['none']], [int(d['right']) for d in c2[label]], [d['ans'] for d in c2['none']], [d['ans'] for d in c2[label]]),
            chain5=compare(*(lambda ix: ([sk['none']['hits'][i] for i in ix], [sk[label]['hits'][i] for i in ix], [sk['none']['preds'][i] for i in ix], [sk[label]['preds'][i] for i in ix]))(c5)),
            nonchain=compare(*(lambda ix: ([sk['none']['hits'][i] for i in ix], [sk[label]['hits'][i] for i in ix], [sk['none']['preds'][i] for i in ix], [sk[label]['preds'][i] for i in ix]))(nc)))
    res['vs_none'] = sets
    num = dict(gain_H=sets['H']['c2_dev']['net_points'], gain_L=sets['L']['c2_dev']['net_points'],
               hurt_H=sets['H']['chain5']['hurt'] + sets['H']['nonchain']['hurt'], hurt_L=sets['L']['chain5']['hurt'] + sets['L']['nonchain']['hurt'],
               harm_L={s: 0.0 - sets["L"][s]["net_points"] for s in ('chain5', 'nonchain')}, reach_H=100 * prac['H']['reach32'], reach_L=100 * prac['L']['reach32'], audit=res['audit']['ok'])
    res['numbers'] = num
    res['marks'] = parent_marks(num)
    res['set_sizes'] = dict(chain5=len(c5), nonchain=len(nc), c2_dev=len(dev), practised=len(fresh), full_size_expected=dict(chain5=CHAIN5_N, nonchain=NONCHAIN_N))
    secs['total'] = time.time() - t00
    res['cpu_seconds'] = dict(process=time.process_time() - c00, wall=secs['total'])
    save()
    log('MARKS', res['marks'], {k_: (round(v, 2) if isinstance(v, float) else v) for k_, v in num.items() if k_ != 'harm_L'})
    return res


def run(nprimes, out, s1dir, s3dir, **kw):
    return {os.path.basename(os.path.dirname(os.path.abspath(os.path.expanduser(p)))): gate_parent(p, out, s1dir, s3dir, **kw) for p in nprimes}


def report(out, parents):
    """<out>/gate-report.json: per-parent marks (recomputed from the stored numbers), report-only numbers, and the verdict."""
    per, rows = {}, {}
    for p in parents:
        path = os.path.join(out, p, 'gate.json')
        if not os.path.exists(path):
            continue
        r = json.load(open(path))
        if 'numbers' not in r:
            continue
        per[p] = parent_marks(r['numbers'])
        rows[p] = dict(smoke=r['smoke'], numbers=r['numbers'], marks=per[p], vs_none=r['vs_none'], scores=r['scores'], gate_mean_weight_by_step=dict(
            train_night_loo=r['gate']['per_set']['night_loo']['mean_weight_by_step'], train_skills=r['gate']['per_set']['skills_train']['mean_weight_by_step'], live=r.get('weights_live', {}).get('L')),
            training=dict(loss_none=r['gate']['loss_none'], loss_final=r['gate']['loss_final'], curve=r['gate']['loss_curve'], per_set={k_: {a: b for a, b in v.items() if a != 'mean_weight_by_step'} for k_, v in r['gate']['per_set'].items()}),
            cpu_seconds=r['cpu_seconds'], audit=r['audit'], records=r['records'].get('rebuilt'), with_same_question_sibling=r['records'].get('with_same_question_sibling'))
    rep = dict(parents=rows, marks_rules=MARKS, verdict=verdict(per, len(parents)), pooled_marks={m: all(v[m] for v in per.values()) for m in ('gain', 'harm', 'recall', 'audit', 'passes', 'proved_wrong')} if per else None)
    json.dump(rep, open(os.path.join(out, 'gate-report.json'), 'w'), indent=1)
    return rep


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('run'); q.add_argument('--nprime', nargs='+', required=True); q.add_argument('--s1', required=True); q.add_argument('--s3', required=True)
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True)
    q.add_argument('--dev-limit', type=int, help='smoke only'); q.add_argument('--skills-limit', type=int, help='smoke only'); q.add_argument('--max-records', type=int, help='smoke only')
    q.add_argument('--practised-limit', type=int, help='smoke only'); q.add_argument('--loo', default='question', choices=['question', 'self'], help='question (roadmap D6 ruling 10-09): drop every note of the record\'s source question; self: only its own entries')
    q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true'); q.add_argument('--seed', type=int, default=0)
    q = sub.add_parser('report'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    a = a.parse_args()
    if getattr(a, 'threads', None):
        torch.set_num_threads(a.threads)
    if a.cmd == 'report':
        print(json.dumps(report(a.out, tuple(a.parents)), indent=1))
    else:
        ex = os.path.expanduser
        run(a.nprime, a.out, ex(a.s1), ex(a.s3), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), dev_limit=a.dev_limit, skills_limit=a.skills_limit, max_records=a.max_records,
            practised_limit=a.practised_limit, device=a.device, resume=not a.no_resume, loo=a.loo, seed=a.seed)
