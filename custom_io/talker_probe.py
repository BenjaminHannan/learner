"""R4, the answer-in-thoughts linear probe, and the TK-2 readings (talker thread, G2f; talker/G2F-BUILD-SPEC-2026-10-11.md sec. 5; marks: talker/MARKS-TALKER-CHECKS-2026-10-11.md). Read-only: the model is never trained.
With talk_question on, the probe still reads the thinker part only (writer_view), on purpose: TK-2 asks whether the answer is in the THOUGHTS.

Ben's design note (sec. 6) names the check: "a linear probe on the thoughts when the talker is wrong". On a b3g2 or b3at checkpoint (any model whose state_of(run(batch)) holds what its
talker reads: its writer_view(state) when it has one, else state[0]) a LINEAR probe is fit on the state the final line was written from, flattened: what the writer reads (talk_rounds='last': the last round's Z; 'all': the memory of all rounds run, masked blocks zeroed, zero-padded to the longest valid memory; [n vectors x d] -> n * d numbers; standardised on the train rows), to
predict the gold answer's first 8 bytes: one softmax per byte position, 8 positions, the answer EOS-padded (a shorter answer is followed by the EOS class), a longer one cut at 8.
The probe is fit on TRAIN rows (the model's own free run on them, learned stop) with weight decay chosen on a held-out 10% of those rows (early stopping on the same split), and scored on DEV rows.
A dev row is READ when the probe's argmax is the gold 8-byte target at all 8 positions (a byte the train rows never showed cannot be predicted: a miss).
The talker is RIGHT on a row when its own free-run final line is a hit under evalx's scoring (is_hit). Reported (all rates in percent of the rows named):
  right_read    the share of talker-RIGHT dev rows the probe reads (validity: a probe that cannot read an answer the talker demonstrably wrote from these thoughts is too weak to say anything).
  wrong_read    K, the share of talker-WRONG dev rows the probe reads: "the thinker knew, the talker failed".
  control       the shuffled-state control: the same probe on ANOTHER row's state (rolled by one inside the row's family; a one-row family borrows from the next family), scored against the row's
                own gold answer; it can only succeed by answer collision. Reported on all dev rows and on the right rows, with the answer-collision baseline of the same rows (the chance that a
                random other row of the family has the same first-8-byte target).
  each of these pooled, per family and by gold answer length in bytes (1-2, 3-4, 5-8, 9+; 9+ is read on its first 8 bytes).
Readings (marks file, written before any model trained). TK-2a (the probe is strong enough): right_read >= 80% AND control (all dev rows) <= collision baseline + 5. If TK-2a fails, TK-2b is
VOID and is reported as void, never read. TK-2b (a routing rule, not a pass/fail): K >= 50%: the thinker knew and the talker failed (next single change in the talker: talk_rounds='all' first, then a
bigger talker); K <= 20%: the answer is not in the last round's thoughts (next change on the thinker side); between: every-round reading first (built, cheapest).
CLI: python -m custom_io.talker_probe --run RUN_DIR --data DIR [--n-train 3000] [--splits in_dist] [--max N] [--caps CAPS.json]"""
import argparse, contextlib, json, os
import numpy as np
import torch
import torch.nn.functional as F
from custom_io.data import DEFAULT_DATA, DEV_SPLITS, load_rows
from custom_io.evalx import is_hit, norm, subsample
from custom_io.talker_report import _batches, _nullamp, collision, dev_rows, load_checkpoint

NB = 8                          # answer bytes read
EOSC = 256                      # the EOS class after the answer's last byte
BUCKETS = (('1-2', 0, 2), ('3-4', 3, 4), ('5-8', 5, 8), ('9+', 9, 10 ** 9))
RIGHT_MIN = 80.0                # TK-2a: the probe reads at least this share of talker-right rows
CTRL_SLACK = 5.0                # TK-2a: control <= collision baseline + this
K_HIGH, K_LOW = 50.0, 20.0      # TK-2b: K >= 50 talker failed, K <= 20 not in the thoughts


def target_of(answer):
    """The gold answer -> its NB target classes: the utf-8 bytes cut at NB, then EOS (class 256) to fill (an answer of NB bytes or more has no EOS class)."""
    b = list(answer.encode('utf-8'))[:NB]
    return b + [EOSC] * (NB - len(b))


def bucket_of(answer):
    n = len(answer.encode('utf-8'))
    return next(name for name, lo, hi in BUCKETS if lo <= n <= hi)


MAX_FLOATS = 2e8                # collect(): rows x features above this and the rows are subsampled evenly (about 800 MB of float32)


@torch.no_grad()
def collect(model, rows, batch_size=64, device=None, amp=None, max_floats=MAX_FLOATS):
    """The free run (model.run, learned stop) then model.talk on its state, in no_grad batches -> dict(Z [N, F] float32 cpu, what the WRITER reads, flattened, in the order of `rows`;
    ans [N] the talker's final lines; hit [N] bool, is_hit under evalx's scoring; idx [N] the positions in `rows` the entries are (all of them unless subsampled); note None, or the sentence
    saying the rows were subsampled).
    What is read is model.writer_view(state): under talk_rounds='last' (and for a model with no writer_view) the state's Z, [n vectors x d] -> n * d numbers, exactly as before; under
    talk_rounds='all' the writer reads the MEMORY (the thinker's vectors of rounds 0..its stop round, with the mask that hides the rest), so the probe reads the memory with its masked blocks
    zeroed, flattened, and zero-padded to the longest VALID memory among the collected rows (longest valid rounds x n_z x d numbers; not to the cap). A probe fed the last round's Z alone
    would be reading something the writer never saw.
    Only the RETURNED array is bounded: every row's features are materialised first (as a list of tensors) and only then subsampled, so the peak during collection is the full set. If rows x
    features would exceed `max_floats` (about 2e8) the returned rows are subsampled evenly (the linspace rule of evalx.subsample) and `note` says so (a caller scoring against the rows must
    use rows[i] for i in idx). probe_report pads train and dev to one shared width (see pack)."""
    return pack(*gather(model, rows, batch_size, device, amp), max_floats=max_floats)


@torch.no_grad()
def gather(model, rows, batch_size=64, device=None, amp=None):
    """collect's first half -> (Z list of per-row 1-D tensors at their own widths, ans, hit)."""
    device = device or next(model.parameters()).device
    was = model.training
    model.eval()
    amp = amp or _nullamp
    Z, ans = [None] * len(rows), [None] * len(rows)
    view = getattr(model, 'writer_view', None)
    for idx, b in _batches(model, rows, batch_size, device):
        with amp():
            o = model.run(b)
            st = model.state_of(o)
            a = model.talk(st, b)
            v, m = view(st) if view else (st[0], None)
        v = v.float()
        if m is None:
            z = v.flatten(1).cpu()
        else:       # masked blocks zeroed; trimmed to this batch's longest valid memory (the valid part of a row is a prefix: rounds 0..stop round)
            z = (v * m[..., None].to(v.dtype))[:, :int(m.sum(1).max())].flatten(1).cpu()
        for j, i in enumerate(idx):
            Z[i], ans[i] = z[j], a[j]
    model.train(was)
    hit = torch.tensor([is_hit(a, r) for a, r in zip(ans, rows)], dtype=torch.bool)
    return Z, ans, hit


def pack(Z, ans, hit, max_floats=MAX_FLOATS, width=None):
    """collect's second half: zero-pad the rows to `width` (default: the longest of them; a wider shared width must be >= that) and subsample evenly if rows x width > max_floats."""
    if not Z:
        return dict(Z=torch.zeros(0, 0), ans=ans, hit=hit, idx=[], note=None)
    width = max(max(len(z) for z in Z), width or 0)                   # the longest valid memory x d (under 'last': n * d)
    keep, note = list(range(len(Z))), None
    if len(Z) * width > max_floats:
        k = max(1, int(max_floats // width))
        keep = np.linspace(0, len(Z) - 1, k).astype(int).tolist() if k < len(Z) else keep
        note = f'subsampled to {len(keep)} of {len(Z)} rows ({len(keep)} x {width} = {len(keep) * width:.3g} floats; limit {max_floats:.3g})'
    out = torch.zeros(len(keep), width)
    for r, i in enumerate(keep):
        out[r, :len(Z[i])] = Z[i]
    return dict(Z=out, ans=[ans[i] for i in keep], hit=hit[keep], idx=keep, note=note)


class Probe:
    """A linear probe: standardise the flattened state, then one linear map to NB softmaxes over the byte classes the train targets showed (+ EOS)."""

    def __init__(self, mean, std, W, b, classes):
        self.mean, self.std, self.W, self.b, self.classes = mean, std, W, b, classes     # W [F, NB * C], classes [C] byte values (256 = EOS)

    def logits(self, Z):
        return (((Z - self.mean) / self.std) @ self.W + self.b).view(Z.shape[0], NB, -1)

    @torch.no_grad()
    def read(self, Z, answers):
        """-> bool [N]: the probe's argmax is the gold 8-byte target of `answers` at all positions (a gold byte outside the train classes is a miss)."""
        if not len(Z):
            return torch.zeros(0, dtype=torch.bool)
        pred = self.classes[self.logits(Z).argmax(-1)]
        return (pred == torch.tensor([target_of(a) for a in answers])).all(1)


def fit_probe(Z, answers, wds=(1e-3, 1e-1), epochs=150, lr=3e-2, patience=8, seed=0, holdout=0.1):
    """Fit the linear probe on the train states Z [N, F] and their gold answers. A held-out `holdout` (10%) of the rows is split off first (a seeded permutation). For each weight decay in `wds`
    (an explicit L2 penalty wd * |W|^2 / 2 in the loss) Adam runs full batch for up to `epochs` steps, stopping when the held-out loss has not improved for `patience` evaluations (every 5
    steps) and keeping the best weights; the weight decay with the lowest held-out loss wins. Cross-entropy is the mean over the NB byte positions. -> (Probe, dict(wd, heldout_loss,
    epochs, n_fit, n_heldout, n_classes)). Cheap: no model forward, only a [N, F] x [F, NB * C] product."""
    g = torch.Generator().manual_seed(seed)
    N = len(Z)
    perm = torch.randperm(N, generator=g)
    nh = max(1, int(round(holdout * N))) if N >= 10 else 0
    ho, tr = perm[:nh], perm[nh:]
    T = torch.tensor([target_of(a) for a in answers])
    cls = torch.unique(T[tr] if len(tr) else T)
    cmap = torch.full((EOSC + 1,), -1, dtype=torch.long)
    cmap[cls] = torch.arange(len(cls))
    Y = cmap[T]                                         # [N, NB], -1 = a class no fit row showed
    mean, std = Z[tr].mean(0), Z[tr].std(0).clamp(min=1e-5) if len(tr) > 1 else torch.ones(Z.shape[1])
    X = (Z - mean) / std
    C = len(cls)

    def loss_of(W, b, idx, wd):
        lg = (X[idx] @ W + b).view(len(idx), NB, C)
        y = Y[idx]
        ok = y >= 0
        ce = F.cross_entropy(lg[ok], y[ok]) if ok.any() else lg.sum() * 0
        return ce + 0.5 * wd * (W ** 2).sum()

    best = None
    for wd in wds:
        torch.manual_seed(seed)
        W = torch.zeros(Z.shape[1], NB * C, requires_grad=True)
        b = torch.zeros(NB * C, requires_grad=True)
        opt = torch.optim.Adam([W, b], lr=lr)
        bw, bl, bad, ep = (W.detach().clone(), b.detach().clone()), float('inf'), 0, 0
        for ep in range(1, epochs + 1):
            opt.zero_grad()
            loss_of(W, b, tr, wd).backward()
            opt.step()
            if ep % 5 == 0 or ep == epochs:
                with torch.no_grad():
                    hl = float(loss_of(W, b, ho if nh else tr, 0.0))
                if hl < bl - 1e-5:
                    bw, bl, bad = (W.detach().clone(), b.detach().clone()), hl, 0
                else:
                    bad += 1
                    if bad >= patience:
                        break
        if best is None or bl < best[0]:
            best = (bl, wd, bw, ep)
    bl, wd, (W, b), ep = best
    return Probe(mean, std, W, b, cls), dict(wd=wd, heldout_loss=bl, epochs=ep, n_fit=int(len(tr)), n_heldout=int(nh), n_classes=int(C))


def _roll_in_family(rows):
    """For every row the index of ANOTHER row's state: the next row of its family (cyclic); a one-row family takes the next row of the next family. A single row takes itself."""
    n = len(rows)
    by = {}
    for i, r in enumerate(rows):
        by.setdefault(r['family'], []).append(i)
    donor = list(range(n))
    solo = []
    for idx in by.values():
        if len(idx) > 1:
            for k, i in enumerate(idx):
                donor[i] = idx[(k + 1) % len(idx)]
        else:
            solo.append(idx[0])
    for i in solo:
        donor[i] = (i + 1) % n
    return donor


def _rate(mask, sel):
    n = int(sel.sum())
    return None if n == 0 else 100 * float((mask & sel).sum()) / n


def _target_collision(rows):
    """The collision baseline on the first-8-byte targets (not the normalised answers): -> {family: baseline % or None}, and the pooled mean weighted by rows (families with a baseline only)."""
    fake = [dict(family=r['family'], answer=' '.join(map(str, target_of(r['answer'])))) for r in rows]
    c = collision(fake, norm=lambda s: s)
    live = [v for v in c.values() if v['baseline'] is not None]          # a family of one row has no baseline (None): out of the pooled weighting
    n = sum(v['n'] for v in live)
    return {f: v['baseline'] for f, v in c.items()}, (sum(v['baseline'] * v['n'] for v in live) / n if n else None)


def read_dev(probe, dev, rows):
    """Score a fitted probe on collected dev states -> the R4 report dict (see the module docstring): n, right_n, wrong_n, right_read, wrong_read (K), control / control_right
    (shuffled-state, on all rows / talker-right rows), collision (pooled baseline), by_family and by_length ({name: same keys}), tk2a, tk2b."""
    Z, hit = dev['Z'], dev['hit']
    ans = [r['answer'] for r in rows]
    rd = probe.read(Z, ans)
    donor = _roll_in_family(rows)
    ctl = probe.read(Z[donor], ans) if len(Z) else rd
    cfam, cpool = _target_collision(rows)
    fams = np.array([r['family'] for r in rows])
    lens = np.array([bucket_of(a) for a in ans])
    right, wrong = hit, ~hit

    def cell(sel):
        sel = torch.from_numpy(sel) if isinstance(sel, np.ndarray) else sel
        return dict(n=int(sel.sum()), right_n=int((sel & right).sum()), wrong_n=int((sel & wrong).sum()), right_read=_rate(rd, sel & right), wrong_read=_rate(rd, sel & wrong),
                    read=_rate(rd, sel), control=_rate(ctl, sel), control_right=_rate(ctl, sel & right))
    allm = torch.ones(len(rows), dtype=torch.bool)
    out = cell(allm)
    out['collision'] = cpool
    out['by_family'] = {f: dict(cell(fams == f), collision=cfam[f]) for f in sorted(set(fams.tolist()))}
    out['by_length'] = {name: cell(lens == name) for name, _, _ in BUCKETS}
    out['tk2a'] = tk2a(out)
    out['tk2b'] = tk2b(out)
    return out


def tk2a(rep):
    """TK-2a: the probe reads all of the first 8 answer bytes on at least 80% of the talker-right dev rows AND the shuffled-state control (all dev rows) is at most the collision baseline + 5.
    -> dict(reading 'PASS' / 'FAIL' / 'n/a', right_read, control, collision)."""
    rr, ct, co = rep['right_read'], rep['control'], rep['collision']
    if rr is None or ct is None or co is None:
        reading = 'n/a'
    else:
        reading = 'PASS' if rr >= RIGHT_MIN and ct <= co + CTRL_SLACK else 'FAIL'
    return dict(reading=reading, right_read=rr, control=ct, collision=co)


def tk2b(rep):
    """TK-2b, the routing rule, only if TK-2a passed (else 'VOID', never read): K = wrong_read. K >= 50: 'talker failed' (the thinker knew; change the talker: talk_rounds='all' first, then a
    bigger talker); K <= 20: 'not in the thoughts' (change the thinker side); between: 'between' (every-round reading first). -> dict(reading, K, n_wrong)."""
    K = rep['wrong_read']
    if (rep['tk2a'] if 'tk2a' in rep else tk2a(rep))['reading'] != 'PASS':
        return dict(reading='VOID', K=K, n_wrong=rep['wrong_n'])
    if K is None:
        return dict(reading='n/a (the talker got no dev row wrong)', K=None, n_wrong=0)
    return dict(reading='talker failed' if K >= K_HIGH else 'not in the thoughts' if K <= K_LOW else 'between', K=K, n_wrong=rep['wrong_n'])


def train_rows(data, n, seed=0):
    """n train rows (DATA/train.jsonl) spread evenly over the file (evalx.subsample); fewer if the file is shorter."""
    return subsample(load_rows(os.path.join(data, 'train.jsonl')), n)


def probe_report(model, train, dev, batch_size=64, device=None, amp=None, **fit_kw):
    """R4 end to end: collect the model's states on `train` and `dev` rows, fit the probe on the train states, score it on the dev states -> read_dev's dict plus fit=dict(wd, heldout_loss, ...),
    n_train and the talker's own dev accuracy (talker_exact, %)."""
    gt, gd = gather(model, train, batch_size, device, amp), gather(model, dev, batch_size, device, amp)
    width = max([len(z) for z in gt[0] + gd[0]] or [0])               # train and dev share one width (zero blocks are what a masked memory already looks like)
    tr = pack(*gt, width=width)
    probe, info = fit_probe(tr['Z'], [train[i]['answer'] for i in tr['idx']], **fit_kw)
    dv = pack(*gd, width=width)
    dev_used = [dev[i] for i in dv['idx']]
    rep = read_dev(probe, dv, dev_used)
    rep.update(fit=info, n_train=len(tr['idx']), talker_exact=100 * float(dv['hit'].float().mean()) if len(dev_used) else None, n_features=int(tr['Z'].shape[1]),
               subsampled=[x for x in (tr['note'] and 'train ' + tr['note'], dv['note'] and 'dev ' + dv['note']) if x])
    return rep


def format_report(rep):
    f = lambda x: '  n/a' if x is None else f'{x:5.1f}'
    L = [f'R4 answer-in-thoughts probe: {rep["n"]} dev rows ({rep["right_n"]} talker right, {rep["wrong_n"]} wrong), train rows {rep.get("n_train")}, fit {rep.get("fit")}',
         f'  probe reads all 8 bytes: on talker-right rows {f(rep["right_read"])}%   on talker-wrong rows (K) {f(rep["wrong_read"])}%   all rows {f(rep["read"])}%',
         f'  shuffled-state control: all rows {f(rep["control"])}%  right rows {f(rep["control_right"])}%   collision baseline {f(rep["collision"])}%',
         f'  TK-2a {rep["tk2a"]["reading"]}   TK-2b {rep["tk2b"]["reading"]} (K {f(rep["tk2b"]["K"])}, n wrong {rep["tk2b"]["n_wrong"]})',
         f'  {"":22s}{"n":>6}{"right":>6}{"wrong":>6}{"r.read":>8}{"K":>8}{"ctrl":>8}{"collide":>8}']
    L += [f'  NOTE {x}' for x in rep.get('subsampled', [])]
    for title, d in (('by family', rep['by_family']), ('by answer length (bytes)', rep['by_length'])):
        L.append(f'  [{title}]')
        for k, c in d.items():
            L.append(f'  {k:22s}{c["n"]:6d}{c["right_n"]:6d}{c["wrong_n"]:6d}{f(c["right_read"]):>8}{f(c["wrong_read"]):>8}{f(c["control"]):>8}{f(c.get("collision")):>8}')
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', required=True, help='run dir (with checkpoint.pt) or a checkpoint.pt path')
    ap.add_argument('--data', default=DEFAULT_DATA)
    ap.add_argument('--n-train', type=int, default=3000)
    ap.add_argument('--splits', default='in_dist')
    ap.add_argument('--max', type=int, help='cap rows per dev split')
    ap.add_argument('--caps', help='caps.json the checkpoint was trained under (default: the one the run directory records, see talker_report.caps_of_run)')
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--json', help='write the report here')
    a = ap.parse_args(argv)
    m = load_checkpoint(a.run, a.device, a.caps)
    splits = DEV_SPLITS if a.splits == 'all' else a.splits.split(',')
    rep = probe_report(m, train_rows(a.data, a.n_train), dev_rows(a.data, splits, a.max), a.batch, a.device)
    print(format_report(rep))
    if a.json:
        json.dump(rep, open(a.json, 'w'), indent=1)
    return rep


if __name__ == '__main__':
    main()
