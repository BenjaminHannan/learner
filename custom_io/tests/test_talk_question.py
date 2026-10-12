"""python3 -m custom_io.tests.test_talk_question   (CPU, a few minutes; no Gemma: test_b3's stub FrozenEG; run with OMP_NUM_THREADS=1)
G2Q (talker/G2Q-BUILD-SPEC-2026-10-12.md; cfg talk_question, off by default; B3G2 and B3AT). Ben, 11:30 PM ET 10-11: "that's fine the talker can see the question". The writer's memory is
[the thinker memory it reads today; the reader's encoding of the question + one learned vector q_type]. Never the tape, tool replies, prompt or tape ids, copy keys, feedback.
(1) switch off: loss, aux, gradients, a free run and the answers bit-identical to a model built without the key, same seed, no q_type; (2) on: Z and the question fixed, tape and replies changed
-> every writer input and every log-prob bit-identical (teacher forced and free, calls and answers, B3G2 and B3AT); (3) on: another question -> the log-probs change; (4) source check: no tape /
reply tensor is passed into any writer call, and the question enters only through typed_question(X, xm); (5) every trainable parameter gets a gradient, q_type included; (6) no_question = the
thoughts-only writer (same weights) and shuffle_state / zero_state keep each row's own question; (7) 3M count (+d) within PLAIN_BAND of g2c3s; (8) train.py end to end with the switch on for
b3g2 and b3at, every cap fault 0, the checkpoint reloads with talk_question True."""
import ast, inspect, json, os, subprocess, sys, tempfile
import torch
from custom_io.data import EOS
from custom_io.tests import test_b3g2 as T2, test_b3at_core as TA
from custom_io.tests.test_b3 import batch_of, rows
from custom_io.tests.test_b3g2 import V, Script
from custom_io.tests.test_reader_rule import fixed_z, loud, noisy_writer
from custom_io.models.writer import ByteWriter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KINDS = ('b3g2', 'b3at')


def make(kind, seed=0, **kw):
    m = (T2.make if kind == 'b3g2' else TA.make)(seed, **kw)
    return m


def zero_names(m):
    """(parameters without a finite gradient, parameters whose gradient is exactly 0 and are not in the usual untrained-at-this-size list)."""
    bad, zero = [], []
    for n, p in m.named_parameters():
        if not p.requires_grad:
            continue
        if p.grad is None or not torch.isfinite(p.grad).all():
            bad.append(n)
        elif not p.grad.abs().sum() > 0 and not n.startswith(('tape_emb', 'step_emb', 'reader.pos', 'reader.place', 'ctrl', 'src', 'ln_eg')):
            zero.append(n)
    return bad, zero


class Rec:
    """Records, for every writer call, the tensors it is given (the memory, its mask, the context, the mode, the input bytes) and the head's output probabilities."""

    def __init__(self, m):
        self.calls, self.p = [], []
        real_head, real_greedy = ByteWriter.head.__get__(m.writer), m.writer.greedy

        def head(R, Xc, cmask, cids, nocopy, ckeys):
            out = real_head(R, Xc, cmask, cids, nocopy, ckeys)
            self.p.append(out[0].detach().clone())
            return out

        def greedy(Z, zmask, Xc, cmask, cids, mode, *a, **k):
            self.calls.append(('greedy', Z.detach().clone(), zmask.clone(), Xc.clone(), cmask.clone(), cids.clone(), mode.clone()))
            return real_greedy(Z, zmask, Xc, cmask, cids, mode, *a, **k)
        self.hook = m.writer.register_forward_pre_hook(lambda mod, a: self.calls.append(('forward', a[0].detach().clone(), a[1].clone(), a[2].clone(), a[3].clone(), a[4].clone(), a[5].clone(), a[6].clone())))
        m.writer.head, m.writer.greedy, self.m, self.real = head, greedy, m, (real_head, real_greedy)

    def close(self):
        self.hook.remove()
        del self.m.writer.head
        self.m.writer.greedy = self.real[1]


def same(a, b):
    assert len(a.calls) == len(b.calls) > 0 and len(a.p) == len(b.p) > 0, (len(a.calls), len(b.calls), len(a.p), len(b.p))
    for x, y in zip(a.calls, b.calls):
        assert x[0] == y[0] and all(torch.equal(u, v) for u, v in zip(x[1:], y[1:])), 'a writer input changed'
    return all(torch.equal(x, y) for x, y in zip(a.p, b.p))


def prep(kind, **kw):
    """A loud model (the Gemma term and the writer have structure) whose thinker is a function of Z alone (Z fixed whatever the prompt, tape or replies)."""
    m = fixed_z(noisy_writer(loud(make(kind, 21, talk_question=True, **kw))))
    m.eval()
    return m


def other_prompts(rs):
    return [dict(r, prompt=r['prompt'][::-1] + ' zzz qqq', id=r['id'] + 'x') for r in rs]


# ---- (1) off ----
def test_off_is_bit_identical():
    b = batch_of(rows(8), V)
    for kind in KINDS:
        outs = []
        for kw in ({}, dict(talk_question=False)):
            m = make(kind, 3, **kw)
            m.train()
            torch.manual_seed(11)
            loss, aux = m.loss(b)
            loss.backward()
            grads = {n: p.grad.clone() for n, p in m.named_parameters() if p.grad is not None}
            m.eval()
            with torch.no_grad():
                o = m.run(b)
                st = m.state_of(o)
                ans = m.talk(st, b)
                les = [m.generate(b, lesion=x) for x in (None, 'zero_state', 'shuffle_state', 'no_question', 'loops:3')]
            assert not hasattr(m, 'q_type') and not m.talk_question and len(st) == 4 and 'q' not in o
            assert 'no_question' in m.LESIONS and les[3] == les[0], 'no_question must be a no-op without the switch'
            outs.append((loss.detach(), aux, grads, o['records'], ans, les, {k: v.clone() for k, v in m.state_dict().items()}))
        a, c = outs
        assert torch.equal(a[0], c[0]) and all(torch.equal(torch.as_tensor(a[1][k]), torch.as_tensor(c[1][k])) for k in a[1]), 'loss / aux'
        assert a[2].keys() == c[2].keys() and all(torch.equal(a[2][k], c[2][k]) for k in a[2]), 'gradients'
        assert a[3] == c[3] and a[4] == c[4] and a[5] == c[5] and all(torch.equal(a[6][k], c[6][k]) for k in a[6])
        print(f'ok {kind} talk_question off (default and explicit): loss, aux, gradients, free run, answers, lessons and weights bit-identical; no q_type; no_question is a no-op')


# ---- (2) and (3) ----
def tf_log(kind, m, b, golds):
    rec = Rec(m)
    torch.manual_seed(5)
    with torch.no_grad():
        if kind == 'b3g2':
            m._loss(b, golds)
        else:
            m._turns(b, golds, 4, count=False)
    rec.close()
    return rec


def free_log(kind, m, b, reply):
    rec = Rec(m)
    if kind == 'b3g2':
        texts = [['add 7 5', 'sub 12 3'], ['mul 2 2'], ['note hi'], [], ['add 1 1'], [], ['add 4 4', 'add 1 2'], ['sub 9 1']]
        sc = Script(m, texts)
        with torch.no_grad():
            o = m.run(b, loops=4, oracle=lambda i, t, c: reply)
            m.talk(m.state_of(o), b)
        m.writer.greedy = rec.real[1]
    else:
        real_tools, real_is_call, bias = m.tools, m.is_call, m.writer.bias.data.clone()
        m.tools, m.is_call = TA.AnyTool(reply), (lambda line: True)
        m.writer.bias.data[EOS] = 50.0                      # every line is '' (EOS first), the run goes on for all 17 turns
        with torch.no_grad():
            m.run(b, loops=1)
        m.tools, m.is_call = real_tools, real_is_call
        m.writer.bias.data.copy_(bias)
    rec.close()
    return rec


def golds_of(kind, m, rs, other_tape=False):
    g = m.plain_golds(rs)
    if other_tape:
        g = [dict(x, tape=[f'{t} = {1000 + 7 * i + k}' if ' ' in t and not t.startswith('note') else t + ' (other)' for k, t in enumerate(x['tape'])]) for i, x in enumerate(g)]
    return g


def test_tape_and_replies_never_reach_the_writer():
    rs = rows(8)
    b = batch_of(rs, V)
    for kind in KINDS:
        m = prep(kind)
        a = tf_log(kind, m, b, golds_of(kind, m, rs))
        c = tf_log(kind, m, b, golds_of(kind, m, rs, other_tape=True))
        assert any(x['tape'] != y['tape'] for x, y in zip(golds_of(kind, m, rs), golds_of(kind, m, rs, True))), 'the replies must differ'
        assert same(a, c) and all(torch.equal(x, y) for x, y in zip(a.p, c.p)), f'{kind}: teacher forced, a line changed with the tape / replies'
        fa, fc = free_log(kind, m, b, 'r1'), free_log(kind, m, b, 'r2 other reply')
        assert same(fa, fc), f'{kind}: free run, a line changed with the replies'
        qpos = [x for x in fa.calls if x[0] == 'forward' or x[0] == 'greedy']
        n_z = m.ctrl.weight.shape[0] + 9
        T = m.read(b, talker=True)[0].shape[1]
        assert all(x[1].shape[1] == n_z + T for x in qpos), 'the writer memory is the thoughts plus the question positions'
        print(f'ok {kind} talk_question on: Z and the question fixed, tape and replies changed -> bit-identical writer inputs and line log-probs (teacher forced %d calls / %d heads, free run %d / %d)' % (len(a.calls), len(a.p), len(fa.calls), len(fa.p)))


def test_question_changes_the_lines():
    rs = rows(8)
    b, b2 = batch_of(rs, V), batch_of(other_prompts(rs), V)
    for kind in KINDS:
        m = prep(kind)
        g = golds_of(kind, m, rs)
        a, c = tf_log(kind, m, b, g), tf_log(kind, m, b2, g)
        assert len(a.p) == len(c.p) > 0 and all(not torch.equal(x, y) for x, y in zip(a.p, c.p)), f'{kind}: another question left a line unchanged'
        # the same two questions with the switch off change nothing (the old rule)
        off = fixed_z(noisy_writer(loud(make(kind, 21)))).eval()
        a0, c0 = tf_log(kind, off, b, g), tf_log(kind, off, b2, g)
        assert len(a0.p) == len(c0.p) > 0 and all(torch.equal(x, y) for x, y in zip(a0.p, c0.p)), f'{kind}: switch off, a line changed with the question'
        print(f'ok {kind} talk_question on: another question changes every teacher-forced line ({len(a.p)} heads); off, it changes none')


# ---- (4) ----
def test_source_check():
    forbid = {'X', 'xm', 'Xt', 'idt', 'mt', 'vis', 'pids', 'batch', 'ckeys', 'ck', 'shown', 'c', 'kvt', 'kvs', 'texts', 'tape', 'replies', 'reply'}
    import custom_io.models.b3g2 as M2, custom_io.models.b3at as MA
    sinks = ('call_pass', 'call_greedy', 'ans_pass', 'write_lines', 'line_logp', 'answer_teacher', 'with_q')
    n_calls, n_q = {}, {}
    for mod in (M2, MA):
        tree = ast.parse(inspect.getsource(mod))
        k = q = 0
        for fn in [x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef)]:
            for c in [x for x in ast.walk(fn) if isinstance(x, ast.Call)]:
                f = ast.unparse(c.func)
                args = c.args + [kw.value for kw in c.keywords]
                if f == 'self.typed_question':
                    q += 1
                    assert ast.unparse(c) in ('self.typed_question(X, xm)', "self.typed_question(c['X'], c['xm'])"), ast.unparse(c)      # the question's own encoding, nothing else
                    continue
                if not (f == 'self.writer' or (f.startswith('self.writer.') and f.split('.')[-1] in ('greedy', 'run', 'forward', 'head')) or f.split('.')[-1] in sinks):
                    continue
                k += 1
                names = {x.id for a in args for x in ast.walk(a) if isinstance(x, ast.Name)}
                attrs = {x.attr for a in args for x in ast.walk(a) if isinstance(x, ast.Attribute)}
                assert not names & forbid and not attrs & {'prompt_ids', 'ckeys'}, (mod.__name__, fn.name, f, names, attrs)
        n_calls[mod.__name__], n_q[mod.__name__] = k, q
        assert q >= 1 and k >= 4, (mod.__name__, k, q)
    print('ok source check: no tape / reply / prompt tensor is passed into any writer call (%s); the question enters only through typed_question(X, xm) (%s call sites)'
          % (', '.join(f'{k.split(".")[-1]} {v} calls' for k, v in n_calls.items()), '+'.join(str(v) for v in n_q.values())))


# ---- (5) ----
def test_every_parameter_gets_a_gradient():
    b = batch_of(rows(8), V)
    for kind in KINDS:
        for mode in ('last', 'all'):
            m = make(kind, 2, talk_question=True, talk_rounds=mode)
            m.train()
            loss, aux = m.loss(b)
            loss.backward()
            bad, zero = zero_names(m)
            assert not bad and not zero, (kind, mode, bad, zero)
            assert m.q_type.grad is not None and m.q_type.grad.abs().sum() > 0 and 'q_type' in dict(m.named_parameters())
            base = make(kind, 2, talk_rounds=mode)
            base.train()
            base.loss(b)[0].backward()
            assert set(zero_names(base)[1]) == set(zero) and {n for n, _ in base.named_parameters()} | {'q_type'} == {n for n, _ in m.named_parameters()}
        print(f'ok {kind} talk_question on: every trainable parameter ({sum(1 for _ in m.parameters())} tensors) gets a gradient, q_type included, talk_rounds last and all; exactly one new parameter')


# ---- (6) ----
def test_lesions_and_no_question():
    rs = rows(8)
    b = batch_of(rs, V)
    for kind in KINDS:
        for mode in ('last', 'all'):
            m = noisy_writer(loud(make(kind, 21, talk_question=True, talk_rounds=mode))).eval()
            off = make(kind, 21, talk_rounds=mode)
            missing = off.load_state_dict(m.state_dict(), strict=False)
            assert not missing.missing_keys and missing.unexpected_keys == ['q_type'], missing
            off.eval()
            with torch.no_grad():
                st = m.state_of(m.run(b))
                core, (xq, qm) = st[:-2], st[-2:]
                les = {n: m.lesioned(st, n) for n in ('zero_state', 'shuffle_state', 'no_question')}
                assert all(torch.equal(les[n][-2], xq) for n in les), 'the lesions never touch the question vectors'
                assert torch.equal(les['zero_state'][-1], qm) and torch.equal(les['shuffle_state'][-1], qm) and not les['no_question'][-1].any() and qm.any()
                assert torch.equal(les['shuffle_state'][0], core[0].roll(1, 0)) and not les['zero_state'][0].any() and torch.equal(les['no_question'][0], core[0])
                ra, rb = Rec(m), Rec(off)
                a = m.talk(les['no_question'], b)
                c = off.talk(core, b)
                ra.close(); rb.close()
                assert a == c and len(ra.p) == len(rb.p) and all(torch.allclose(x, y, atol=1e-6, rtol=1e-5) for x, y in zip(ra.p, rb.p)), 'no_question != the thoughts-only writer fed the same weights'      # masked keys add exact zeros to the softmax; only the summation order can differ
                if kind == 'b3g2':
                    fa, fc = m.forced_answer(les['no_question'], b, [r['answer'] for r in rs]), off.forced_answer(core, b, [r['answer'] for r in rs])
                    assert all(torch.allclose(x.float(), y.float(), atol=1e-4, rtol=1e-4) for x, y in zip(fa, fc))
                full = Rec(m)
                m.talk(st, b)
                full.close()
                assert not torch.equal(full.p[-1], ra.p[-1]), 'with the question visible the line must differ from the question-masked one (noisy writer)'
                sh = Rec(m)
                m.talk(les['shuffle_state'], b)
                sh.close()
                Zin, zmin = sh.calls[-1][1], sh.calls[-1][2]
                n_mem = core[0].shape[1] if mode == 'last' else core[4].shape[1]
                thoughts = core[0] if mode == 'last' else core[4]
                assert torch.equal(Zin[:, :n_mem], thoughts.roll(1, 0)) and torch.equal(Zin[:, n_mem:], xq) and torch.equal(zmin[:, n_mem:], qm), 'shuffle_state: each row keeps its OWN question'
                names = [m.generate(b, lesion=x) for x in ('zero_state', 'shuffle_state', 'no_question')]
                assert [len(x) for x in names] == [len(rs)] * 3
        print(f'ok {kind}: no_question == the thoughts-only writer with the same weights (answers, log-probs{", forced answers" if kind == "b3g2" else ""}); zero_state / shuffle_state scramble the thoughts only, every row keeps its own question; talk_rounds last and all')


# ---- donor swaps (F1) ----
def test_donor_swap_keeps_own_question():
    from custom_io.evalx import donor_eval
    rs = rows(8)
    b = batch_of(rs, V)
    d = batch_of(rs[::-1], V)          # another set of rows as the donor batch (same padded width)
    for kind in KINDS:
        for mode in ('last', 'all'):
            m = noisy_writer(loud(make(kind, 21, talk_question=True, talk_rounds=mode))).eval()
            with torch.no_grad():
                cur_st, don_st = m.state_of(m.run(b)), m.state_of(m.run(d))
                sw = m.swap_thoughts(don_st, cur_st)
                assert len(sw) == len(don_st) and all(torch.equal(x, y) for x, y in zip(sw[:-2], don_st[:-2]))
                assert torch.equal(sw[-2], cur_st[-2]) and torch.equal(sw[-1], cur_st[-1]) and not torch.equal(cur_st[-2], don_st[-2]), 'donor thoughts + CURRENT question'
                rec = Rec(m)
                m.talk(sw, b)
                rec.close()
                Zin, zmin = rec.calls[-1][1], rec.calls[-1][2]
                thoughts = don_st[0] if mode == 'last' else don_st[4]
                n = thoughts.shape[1]
                assert torch.equal(Zin[:, :n], thoughts) and torch.equal(Zin[:, n:], cur_st[-2] ) and torch.equal(zmin[:, n:], cur_st[-1]), 'the writer memory = donor thoughts + current question'
            # the real donor path (evalx.donor_eval) goes through swap_thoughts
            calls = []
            real = m.swap_thoughts
            m.swap_thoughts = lambda a, c: calls.append(1) or real(a, c)
            rr = [dict(r, accepted=[r['answer']], level=1) for r in rows(8)]
            donor_eval(m, rr, batch_size=4, device='cpu', pairs=([(0, 1), (1, 2), (2, 3), (3, 0)], 0))
            assert calls, 'donor_eval did not splice the current question'
            del m.swap_thoughts
        # switch off: unchanged (the donor state goes through as it is)
        off = make(kind, 21)
        st = off.state_of(off.run(b))
        assert off.swap_thoughts(st, st) is st
        print(f'ok {kind}: donor swap = donor thoughts + the CURRENT row\'s own question (tensors checked, last and all); donor_eval splices; switch off hands the donor state through unchanged')


# ---- (7) ----
def test_3m_count():
    from custom_io.g8a import caps as CP, configs as C
    here = os.path.join(ROOT, 'custom_io', 'g8a')
    CP.apply(json.load(open(os.path.join(here, 'caps_b3g2.json'))))
    line = []
    for name, fn, model in (('B3G2', C.b3g2_cfg, 'b3g2'), ('B3AT', C.b3at_cfg, 'b3at')):
        off, on = fn('3M', {'eg_embed': True}), fn('3M', {'eg_embed': True, 'talk_question': True})
        n0, n1 = C.n(model, off), C.n(model, on)
        assert on['talk_question'] is True and 'talk_question' not in off and n1 - n0 == on['d'] == 256, (n0, n1, on['d'])
        assert abs(n1 / C.G2C3S - 1) <= C.PLAIN_BAND and on['writer_mlp'] == off['writer_mlp'] and on['mlp'] == off['mlp'], 'no re-solve expected'
        assert C.b3g2_breakdown(on, model)['total'] == n1
        line.append(f'{name} {n1:,} ({100 * (n1 / C.G2C3S - 1):+.3f}% from g2c3s {C.G2C3S:,}; switch off {n0:,}; writer_mlp {on["writer_mlp"]})')
    print('ok 3M count with talk_question on: ' + '; '.join(line))


# ---- (8) ----
def test_train_py():
    from custom_io.tests import test_b3g2_run as R
    from custom_io import capcount
    for kind in KINDS:
        d, big = tempfile.mkdtemp(), tempfile.mkdtemp()
        for root in (d, big):
            os.makedirs(os.path.join(root, 'dev'))
        with open(os.path.join(d, 'train.jsonl'), 'w') as f:
            for r in R.rows(24):
                f.write(json.dumps(r) + '\n')
        for root in (d, big):
            for s in ['in_dist', 'answer', 'frame', 'vocab', 'variant', 'family']:
                with open(os.path.join(root, 'dev', s + '.jsonl'), 'w') as f:
                    for r in R.rows(6, 100):
                        f.write(json.dumps(dict(r, id=r['id'] + s)) + '\n')
        caps = os.path.join(d, 'caps.json')
        json.dump(dict(max_prompt=400, max_ans=12, n_num=16, w_max=80, n_res=11, n_reg=13, plain_target=64, le=95), open(caps, 'w'))
        out = os.path.join(d, 'out')
        cfg = dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0, n_loops=12, label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.25, any_round=True,
                   gap_p=0.25 if kind == 'b3g2' else 0, no_slots=True, no_place=True, bytes=True, as_written=True, writer_inner=24, talk_question=True)
        cmd = [sys.executable, '-m', 'custom_io.train', '--model', kind, '--cfg', json.dumps(cfg), '--data', d, '--big-data', big, '--steps', '20', '--batch', '8', '--lr', '3e-3', '--warmup', '5',
               '--log-every', '2', '--final-eval', '--eval-batch', '8', '--eval-max', '6', '--caps', caps, '--out', out, '--seed', '1']
        p = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, PYTHONPATH=ROOT, OMP_NUM_THREADS='1'), capture_output=True, text=True)
        assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-4000:]
        res = json.load(open(os.path.join(out, 'RESULT.json')))
        assert res['status'] == 'ok' and res['steps'] == 20 and 'extra_error' not in res, res.get('extra_error')
        assert 'no_question' in res['lesions'] and 'zero_state' in res['lesions'] and 'shuffle_state' in res['lesions'], list(res['lesions'])
        cap = res['cap_hits']
        assert all(cap[k] == 0 for k in capcount.NAMES), cap
        from custom_io.g8a import caps as CP
        from custom_io.models import load_model
        CP.apply(json.load(open(caps)))
        m = load_model(os.path.join(out, 'checkpoint.pt'))
        assert m.talk_question is True and m.q_type.shape == (48,) and type(m).__name__ == ('B3G2' if kind == 'b3g2' else 'B3AT')
        print(f'ok train.py --model {kind} with talk_question: 20 steps, final eval + lesions (no_question included), every cap counter 0, checkpoint reloads with talk_question True (n_params {res["n_params"]})')


if __name__ == '__main__':
    torch.set_num_threads(1)
    test_off_is_bit_identical()
    test_tape_and_replies_never_reach_the_writer()
    test_question_changes_the_lines()
    test_source_check()
    test_every_parameter_gets_a_gradient()
    test_lesions_and_no_question()
    test_donor_swap_keeps_own_question()
    test_3m_count()
    test_train_py()
    print('ALL OK')
