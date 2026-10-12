"""python3 -m custom_io.tests.test_b3at_toy   (CPU, a few minutes; no data files, no Gemma: test_b3's stub FrozenEG; run with OMP_NUM_THREADS=2)
The sealed AT-0 checks that need a TRAINED model (architecture/AT-BUILD-SPEC-2026-10-11.md sec. 6 checks 3 and 4; big-run PLAN sixth Addendum item 4, AT-0 (iii) and (iv)), on a toy task
whose gold program is two calculator calls and then the answer: 'x = a + b; y = x - c. y?' -> 'add a b', 'sub x c', 'y' (plus a few one-call rows 'x = a + b. x?' -> 'add a b', 'x').
  (iii) teacher forcing vs the free run: a tiny b3at is trained on CPU until the teacher-forced line of every turn is right and the stop head is right on its 'settled' labels, then the
        teacher-forced argmax line of every (row, turn) (calls and answers) is compared with the line the FREE greedy run writes (the learned stop per turn, every reply from the real
        calculator through read_texts). At least 99% of LINES must match (and the rows' answers are scored too).
  (iv)  the model uses the tool: calculator-off (the `noexec` lesion: every reply '?') and an oracle reply swap (every calculator reply is replaced by a wrong number) each change the outputs
        (the later call lines and the final answers) of the trained model, and an unchanged re-run does not (each is measured twice: with the learned stop, and with TCAP forced rounds).
Also, because it is the first trained b3at: extra_evals runs end to end on a tiny dev dir (per-turn call accuracy, free-run program accuracy, the agreement table, extra['talker'], extra['at'] with
rounds and lines per turn and per family) and every counter that is a fault reads 0.
What the first trained toy showed (reported, not hidden): with KS_T = (3, 6) the teacher-forced loop and a free run on the same forced rounds agree on 100% of lines, but the free run with the LEARNED
stop agrees on only ~74%. The talker is trained to be right at every round, so the 'settled' label is already 1 at round 1 and the stop fires at round 1 in every turn; a turn then hands the next
turn a Z that is one round old, while teacher forcing only ever hands over a Z that is R >= 3 rounds old (R is one per batch), so later lines drift. With B3AT_TOY_KS=1,3,6 (the toy also trains on
one-round turns) the same comparison is 100%. The learned-stop gate below is therefore left failing on the default schedule: it is the sealed check, not weakened.
Toy-scale settings, the only departures from the real model (all printed): TCAP = 6 rounds per turn and KS_T = (3, 6) (the module constants; the real 32 and (4, 8, 16, 32) cost too much on a CPU, and
the stop head trains only on batches whose R is TCAP, so the toy keeps one of the two draws at TCAP); d = 32; the stub Gemma (deterministic random states per text, so a reply is a fingerprint of its
string, not a number the toy can read; the toy memorises its rows). The code paths are the real ones."""
import contextlib
import json
import os
import tempfile
import time
import torch
from custom_io import capcount
from custom_io.data import DEV_SPLITS
from custom_io.models import b3at as M
from custom_io.tests.test_b3 import batch_of
from custom_io.tests.test_b3at_core import FAULTS, V, make

SEED, MAX_STEPS = 0, 4000
CONSEC = 20             # training stops only after line_acc_all == 1.0 on this many consecutive updates (and the eval criteria below)
TOY_TCAP = 6
TOY_KS = tuple(int(x) for x in os.environ.get('B3AT_TOY_KS', '3,6').split(','))      # rounds per turn drawn per training batch (the default is the toy's version of (4, 8, 16, 32))


def toy_rows(n2=14, n1=4, base=0):
    rs = []
    for i in range(n2):
        a, b, c = 11 + 7 * i, 23 + 5 * i, 1 + i % 9
        rs.append(dict(id=f'toy2_{base + i}', family='toy2', prompt=f'x = {a} + {b}; y = x - {c}. y?', answer=str(a + b - c), accepted=[str(a + b - c)], level=2, variant='v', stage=9,
                       steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}']))
    for i in range(n1):
        a, b = 31 + 9 * i, 17 + 4 * i
        rs.append(dict(id=f'toy1_{base + i}', family='toy1', prompt=f'x = {a} + {b}. x?', answer=str(a + b), accepted=[str(a + b)], level=2, variant='v', stage=9, steps=[f'{a} + {b} = {a + b}']))
    return rs


def toy_model(seed=SEED):
    return make(seed, d=32)


def tf_lines(m, b, golds):
    """The teacher-forced argmax line of every (row, turn): R = TCAP rounds, the gold tape, the line read at the turn's last round -> ({(row, turn): line}, line accuracy, stop accuracy)."""
    with torch.no_grad():
        _, aux, info = m._turns(b, golds, M.TCAP, count=False, names=True)
    return info['pred'], aux['line_acc'], float(aux['stop_acc'])


def free_lines(o, i):
    """The lines the free run wrote for row i: its tool lines then its final line (None when the run never wrote a final line)."""
    return [x[1] for x in o['records'][i]] + [o['answers'][i]]


def agreement(m, b, golds, loops=None):
    """Teacher-forced argmax lines (R = TCAP rounds, the gold tape) vs the free greedy run's lines (loops=None: the learned stop per turn; loops=K: K forced rounds in every turn)."""
    pred, line_acc, stop_acc = tf_lines(m, b, golds)
    with torch.no_grad():
        o = m.run(b, loops=loops)
    n = agree = 0
    bad = []
    for i, g in enumerate(golds):
        fl = free_lines(o, i)
        for j in range(len(g['texts']) + 1):
            n += 1
            ok = j < len(fl) and fl[j] == pred[(i, j)]
            agree += ok
            if not ok:
                bad.append((i, j, pred[(i, j)], fl[j] if j < len(fl) else None))
    return dict(lines=n, agree=agree, rate=agree / max(n, 1), bad=bad, tf_line_acc=line_acc, stop_acc=stop_acc, free=o)


def matched(m, b, golds, o):
    """Matched-rounds comparison: teacher forcing where each (row, turn) runs exactly the rounds the free run (learned stop) used for that pair, the Z carried after those rounds, the line read at that
    round, vs the free run's own line -> dict(lines, agree, rate, bad). The code-consistency number under the learned stop."""
    T = torch.zeros(len(golds), max(len(g['texts']) for g in golds) + 1, dtype=torch.long)
    for i, tr in enumerate(o['turn_rounds']):
        for j, u in enumerate(tr[:T.shape[1]]):
            T[i, j] = u
    with torch.no_grad():
        _, _, info = m._turns(b, golds, M.TCAP, count=False, names=True, rounds=T)
    n = agree = 0
    bad = []
    for i, g in enumerate(golds):
        fl = free_lines(o, i)
        for j in range(len(g['texts']) + 1):
            n += 1
            ok = j < len(fl) and fl[j] == info['pred'][(i, j)]
            agree += ok
            if not ok:
                bad.append((i, j, info['pred'][(i, j)], fl[j] if j < len(fl) else None))
    return dict(lines=n, agree=agree, rate=agree / max(n, 1), bad=bad)


def train(m, rs, b, golds):
    """Train until (a) line_acc_all (measured each update on the plain golds with the loss's own random R and carry draws; drilled rows are not scored) (every (row, turn, round) pair with a target, teacher forced, so round 1 too) was 1.0 on CONSEC consecutive updates, and (b) on the
    eval-mode model every turn's last-round line is right and the stop head is right on its labels (checked every 100 updates and whenever (a) holds), at most MAX_STEPS.
    -> (steps, seconds, last eval, the last run of consecutive line_acc_all == 1.0 updates)."""
    torch.manual_seed(SEED)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-3, betas=(0.9, 0.95), weight_decay=0.0)
    t0, res, run = time.time(), None, 0
    for s in range(MAX_STEPS + 1):
        if s % 100 == 0 or run >= CONSEC:
            m.eval()
            _, la, sa = tf_lines(m, b, golds)
            res = (la, sa)
            if s % 100 == 0:
                print('   step %d: teacher-forced line accuracy %.3f, stop accuracy %.3f, consecutive line_acc_all==1 updates %d (%.0fs)' % (s, la, sa, run, time.time() - t0), flush=True)
            if la == 1.0 and sa >= 0.98 and run >= CONSEC:
                return s, time.time() - t0, res, run
            if s == MAX_STEPS:
                break
        m.train()
        with torch.no_grad():       # the same loss on the PLAIN golds (no answer drill: a drilled row's answer is a drawn number, not what the criterion is about), random R and carry draws, the model before this update
            _, aux = m._loss(b, golds)
        run = run + 1 if float(aux['line_acc_all']) == 1.0 else 0
        loss, aux = m.loss(b)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
    return s, time.time() - t0, res, run


def changed(a, b_, rows):
    """Rows whose outputs differ between two free runs: any line (the tool lines or the answer), the later tool lines only (turn >= 1), the final answer only."""
    anyl = sum(free_lines(a, i) != free_lines(b_, i) for i in range(rows))
    later = sum([x[1] for x in a['records'][i]][1:] != [x[1] for x in b_['records'][i]][1:] for i in range(rows))
    ans = sum(a['answers'][i] != b_['answers'][i] for i in range(rows))
    return dict(any_line=anyl, later_calls=later, answers=ans, n=rows)


def test_toy_at0():
    saved = (M.TCAP, M.KS_T)
    M.TCAP, M.KS_T = TOY_TCAP, TOY_KS
    try:
        _toy()
    finally:
        M.TCAP, M.KS_T = saved


def _toy():
    capcount.reset()
    rs = toy_rows()
    m = toy_model()
    b = batch_of(rs, V)
    golds = m.plain_golds(rs)
    assert [len(g['texts']) for g in golds] == [2] * 14 + [1] * 4, [g['texts'] for g in golds[:2]]
    print('   toy task: %d rows (%d two-call, %d one-call); gold lines of row 0: %s + answer %r; %d trained parameters; TCAP %d, KS_T %s' % (
        len(rs), 14, 4, golds[0]['texts'], golds[0]['ans'], sum(p.numel() for p in m.parameters() if p.requires_grad), M.TCAP, M.KS_T))
    ck = os.environ.get('B3AT_TOY_CKPT')            # optional cache of the trained toy (a development aid: the test trains from scratch when it is unset or missing)
    if ck and os.path.exists(ck):
        m.load_state_dict(torch.load(ck))
        m.eval()
        steps, secs, res, run = 0, 0.0, tf_lines(m, b, golds)[1:], -1
    else:
        steps, secs, res, run = train(m, rs, b, golds)
        if ck:
            torch.save(m.state_dict(), ck)
    m.eval()
    assert res[0] == 1.0 and run >= CONSEC, 'the toy did not reach teacher-forced line accuracy 1.0 with line_acc_all == 1.0 on %d consecutive updates in %d updates: %s (run %d)' % (CONSEC, steps, res, run)
    print('   training took %d updates (line_acc_all == 1.0 on the last %d consecutive updates)' % (steps, run))

    # ---- AT-0 (iii): teacher-forced argmax lines vs the free greedy run ----
    # The sealed check is the free run as the model runs it: the learned stop per turn. The same comparison with K = TCAP forced rounds per turn is printed beside it: it isolates the
    # machinery (teacher-forced loop vs free run on identical rounds) from the stop. Every failure is collected and raised at the end, so the later checks still run.
    fails = []
    ag = agreement(m, b, golds)
    o = ag['free']
    agf = agreement(m, b, golds, loops=M.TCAP)
    mt = matched(m, b, golds, o)
    print('   matched-rounds (each pair runs the rounds the free run used, %d..%d): teacher-forced argmax vs the free run: %d of %d lines = %.1f%% (first disagreements %s)' % (
        min(u for r_ in o['turn_rounds'] for u in r_), max(u for r_ in o['turn_rounds'] for u in r_), mt['agree'], mt['lines'], 100 * mt['rate'], mt['bad'][:4]))
    gold_prog = sum(free_lines(o, i) == g['texts'] + [g['ans']] for i, g in enumerate(golds))
    ans_ok = sum(o['answers'][i] == g['ans'] for i, g in enumerate(golds))
    print('   trained %d updates in %.0fs: teacher-forced line accuracy %.3f, stop accuracy %.3f' % (steps, secs, ag['tf_line_acc'], ag['stop_acc']))
    print('   free run (learned stop): %d/%d rows write exactly the gold program and answer, %d/%d answers right; lines per row %s; rounds per turn of the first rows %s' % (
        gold_prog, len(rs), ans_ok, len(rs), o['turns'], o['turn_rounds'][:3]))
    assert agf['rate'] >= 0.99, 'AT-0 (iii) machinery: teacher-forced vs a free run with the same %d forced rounds per turn: %.3f (%d/%d); first disagreements (row, turn, teacher-forced, free): %s' % (
        M.TCAP, agf['rate'], agf['agree'], agf['lines'], agf['bad'][:6])
    print('ok AT-0 (iii), same rounds: teacher-forced argmax vs the free greedy run with %d forced rounds per turn: %d of %d lines match = %.1f%%' % (M.TCAP, agf['agree'], agf['lines'], 100 * agf['rate']))
    print('   summary of AT-0 (iii): sealed (learned stop) %.1f%%, matched-rounds %.1f%%, forced-%d-rounds %.1f%%, updates %d' % (100 * ag['rate'], 100 * mt['rate'], M.TCAP, 100 * agf['rate'], steps))
    if ag['rate'] >= 0.99:
        print('ok AT-0 (iii) teacher-forced vs free run (learned stop): %d of %d lines (calls and answers) match = %.1f%% (needs >= 99%%); %d/%d free-run programs are the gold program' % (
            ag['agree'], ag['lines'], 100 * ag['rate'], gold_prog, len(rs)))
    else:
        fails.append('AT-0 (iii) teacher-forced vs free run (learned stop): %d of %d lines match = %.1f%% (needs >= 99%%); rounds per turn of the free run: %s; first disagreements (row, turn, '
                     'teacher-forced, free): %s' % (ag['agree'], ag['lines'], 100 * ag['rate'], sorted({u for r_ in o['turn_rounds'] for u in r_}), ag['bad'][:6]))
        print('FAIL ' + fails[-1])

    # ---- AT-0 (iv): the tool is used ----
    n = len(rs)
    for mode, loops in (('learned stop', None), ('%d forced rounds' % M.TCAP, M.TCAP)):
        with torch.no_grad():
            base = m.run(b, loops=loops)
            again = m.run(b, loops=loops)
            off = m.run(b, loops=loops, lesion='noexec')
            swap = m.run(b, loops=loops, oracle=lambda i, t, x: str((int(x[1]) + int(x[2]) if x[0] == 'add' else int(x[1]) - int(x[2])) + 1))
        ch_again, ch_off, ch_swap = changed(base, again, n), changed(base, off, n), changed(base, swap, n)
        assert ch_again == dict(any_line=0, later_calls=0, answers=0, n=n), ('a re-run of the same model changed its outputs', ch_again)
        assert all(rec[2] == '?' for r_ in off['records'] for rec in r_), 'noexec must reply ? to every call'
        okr = lambda out: sum(out['answers'][i] == g['ans'] for i, g in enumerate(golds))
        msg = ('AT-0 (iv) the tool is used (%s): of %d rows, calculator-off (noexec) changes the lines of %d rows (%d later call lines, %d final answers; answers right %d -> %d), the oracle reply swap '
               'changes %d rows (%d later call lines, %d final answers; answers right %d -> %d); an unchanged re-run changes 0' % (
                   mode, n, ch_off['any_line'], ch_off['later_calls'], ch_off['answers'], okr(base), okr(off), ch_swap['any_line'], ch_swap['later_calls'], ch_swap['answers'], okr(base), okr(swap)))
        if ch_off['any_line'] > 0 and ch_swap['any_line'] > 0:
            print('ok ' + msg)
        else:
            fails.append(msg)
            print('FAIL ' + msg)
    with torch.no_grad():
        zero_ans = m.generate(b, lesion='zero_state')
    print('   for reference, zero_state (Z zeroed before the final line) changes %d final answers of the learned-stop run (answers right %d -> %d)' % (
        sum(zero_ans[i] != o['answers'][i] for i in range(n)), ans_ok, sum(zero_ans[i] == g['ans'] for i, g in enumerate(golds))))

    # ---- the trained model's counters and the extra evals on a tiny dev dir ----
    snap = capcount.snapshot()
    assert all(snap[k] == 0 for k in FAULTS), {k: snap[k] for k in FAULTS}
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, 'dev'))
    dev = toy_rows(6, 2, base=100) + rs[:6] + rs[-2:]
    for sp in list(DEV_SPLITS) + ['in_dist']:
        with open(os.path.join(d, 'dev', f'{sp}.jsonl'), 'w') as f:
            for r in dev:
                f.write(json.dumps(dict(r, id=r['id'] + sp)) + '\n')
    ctx = dict(data=d, big=None, device=torch.device('cpu'), batch_size=8, amp=contextlib.nullcontext)
    ex = m.extra_evals(ctx)
    for k in ('op_acc', 'call_text', 'at_lines', 'g2', 'talker', 'at', 'noexec', 'opswap', 'h1', 'b3'):
        assert k in ex, k
    oa = ex['op_acc']
    assert set(oa) == {'teacher_forced', 'free_run', 'n'} and set(oa['free_run']) == {'op', 'call', 'program', 'answer'}
    assert oa['teacher_forced']['program'] >= 99.0 and 0 <= oa['free_run']['program'] <= 100, oa
    # call_evals' free-run program accuracy is the independent count above (every tool line equals the gold line, no extra tool line), the answer accuracy too
    own = {}
    with torch.no_grad():
        m.call_evals(own, rs, lambda sl: iter([batch_of(sl, V)]), ctx)
    exp_prog = 100 * sum([x[1] for x in o['records'][i]] == g['texts'] for i, g in enumerate(golds)) / n
    exp_ans = 100 * sum(o['answers'][i] == g['ans'] for i, g in enumerate(golds)) / n
    assert abs(own['op_acc']['free_run']['program'] - exp_prog) < 1e-6 and abs(own['op_acc']['free_run']['answer'] - exp_ans) < 1e-6, (own['op_acc'], exp_prog, exp_ans)
    assert set(ex['at_lines']['by_turn']) == {'0', '1', '2'} and ex['at_lines']['by_turn']['0']['n'] > ex['at_lines']['by_turn']['2']['n']
    ag2 = ex['g2']['agreement']
    assert ag2['n'] > 0 and 0 <= ag2['agree'] <= 100 and ag2['cells'] and 'copy_share' in ag2
    at = ex['at']
    assert set(at['by_family']) == {'toy1', 'toy2'} and {'0', '1', '2'} <= set(at['rounds_by_turn']) and at['tcap'] == M.TCAP, at['by_family']
    fam_lines = sum(v['lines_per_row'] * v['n'] for v in at['by_family'].values())            # lines per family agree with the per-row line counts of the same runs
    assert abs(fam_lines - sum(int(k) * v for k, v in at['lines_per_row'].items())) < 1e-6 and sum(v['n'] for v in at['by_family'].values()) == at['n'], (at['by_family'], at['lines_per_row'])
    assert isinstance(ex['talker'], dict) and ex['talker']
    snap = capcount.snapshot()
    assert all(snap[k] == 0 for k in FAULTS), {k: snap[k] for k in FAULTS}
    print('ok extra_evals on the trained toy: op_acc %s; agreement table %s (teacher-forced right %.0f%%, greedy right %.0f%%); lines per row by family %s; rounds per turn %s; extra keys %s; fault counters all 0 (turn_cap %d reported)' % (
        json.dumps(oa), ag2['cells'], ag2['tf_right'], ag2['greedy_right'], {k: round(v['lines_per_row'], 2) for k, v in at['by_family'].items()},
        {k: round(v['mean'], 2) for k, v in at['rounds_by_turn'].items()}, sorted(ex['talker'])[:6], capcount.snapshot()['reported']['turn_cap']))
    assert not fails, 'FAILED:\n  ' + '\n  '.join(fails)


if __name__ == '__main__':
    torch.set_num_threads(2)
    t = time.time()
    test_toy_at0()
    print('ALL OK (%.0fs)' % (time.time() - t))
