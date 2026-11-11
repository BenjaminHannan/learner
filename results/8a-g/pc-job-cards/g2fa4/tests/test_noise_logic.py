"""Pure logic test of the noise-aware comparison in overlay-tests/test_ckpt_b3g2.py (no training, a second).
Run:  PYTHONPATH=<tree holding custom_io with tests/test_ckpt.py> python3 tests/test_noise_logic.py
A machine with noise: the unmodified train.py run twice differs a little. Checks: noise-sized differences pass; a shifted random stream (rounds, plan_*) fails exactly;
a loss shifted by 1% fails; a bit-reproducible machine (noise 0) demands bit-for-bit equality."""
import copy, importlib.util, os, random, sys
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('tb', os.path.join(HERE, '..', 'overlay-tests', 'test_ckpt_b3g2.py'))
tb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tb)


def trace(n=40, seed=0, noise=0.0):
    r = random.Random(seed)
    out = []
    for s in range(1, n + 1):
        L = 40.0 / (1 + 0.2 * s)
        out.append(dict(event='train', step=s, loss=round(L + r.uniform(-noise, noise), 5), lr=0.003, cap_hits=0, prog=round(L - 2, 5), call=round(L - 2, 5), ans=2.1, stop=0.6,
                        stop_y=1.0, stop_acc=0.9, right_last=0.0, rounds=float(r.choice([4, 8, 12])), copy_share=0.0, stop_w=0.0, call_acc=0.5, eos_acc=1.0, plan_rows=4.75, plan_gapped=1.0,
                        plan_fallback=0.0, drill_share=0.25))
    return out


def sd(seed, eps=0.0):
    g = torch.Generator().manual_seed(seed)
    return {'w': torch.randn(5, 5, generator=g) + eps * torch.randn(5, 5), 'n': torch.arange(3)}


def bumped(t, f):
    t = copy.deepcopy(t)
    f(t)
    return t


def raises(fn):
    try:
        fn()
    except AssertionError:
        return True
    return False


# bit-reproducible machine
A = trace()
ex = tb.Noise(A, copy.deepcopy(A), sd(1), sd(1))
assert ex.exact
ex.check(A, copy.deepcopy(A), 'same'); ex.check_w(sd(1), sd(1), 'same')
assert raises(lambda: ex.check(A, bumped(A, lambda t: t[10].update(loss=t[10]['loss'] + 1e-5)), 'tiny'))      # exact mode: nothing allowed
assert raises(lambda: ex.check_w(sd(1), sd(1, 1e-7), 'tiny'))
print('ok exact mode: bit for bit demanded')

# a noisy machine: noise 3e-4 on the loss terms (grows with the update), 2e-6 on weights
B1 = trace(noise=0.0)
B2 = trace(noise=0.0)
for i, e in enumerate(B2):
    d = 3e-4 * (i + 1) / 40
    for k in ('loss', 'prog', 'call'):
        e[k] = round(e[k] + d, 5)
nz = tb.Noise(B1, B2, sd(1), sd(1, 2e-6))
assert not nz.exact and nz.w > 0
# within-noise differences pass
C = copy.deepcopy(B1)
for i, e in enumerate(C):
    e['loss'] = round(e['loss'] + 2e-4 * (i + 1) / 40, 5)
nz.check(B1, C, 'within noise'); nz.check_w(sd(1), sd(1, 3e-6), 'within noise')
# an accuracy-type flip (one row of 64) passes, 20 rows does not
nz.check(B1, bumped(B1, lambda t: t[7].update(stop_acc=0.9 - 1 / 64)), 'flip')
assert raises(lambda: nz.check(B1, bumped(B1, lambda t: t[7].update(stop_acc=0.5)), 'big flip'))
# shifted random stream: rounds differs at one update / plan_rows differs: fails exactly
assert raises(lambda: nz.check(B1, bumped(B1, lambda t: t[20].update(rounds=t[20]['rounds'] + 4)), 'rounds'))
assert raises(lambda: nz.check(B1, bumped(B1, lambda t: t[3].update(plan_rows=5.0)), 'plan'))
# loss off by 1% at one late update, or by 0.05 anywhere: fails
assert raises(lambda: nz.check(B1, bumped(B1, lambda t: t[30].update(loss=t[30]['loss'] * 1.01)), 'loss 1%'))
assert raises(lambda: nz.check(B1, bumped(B1, lambda t: t[1].update(loss=t[1]['loss'] + 0.05)), 'loss +0.05'))
# nan fails
assert raises(lambda: nz.check(B1, bumped(B1, lambda t: t[5].update(loss=float('nan'))), 'nan'))
# different update lists fail
assert raises(lambda: nz.check(B1, B1[:-1], 'length'))
# weights off by 1e-3 fail
assert raises(lambda: nz.check_w(sd(1), sd(1, 1e-3), 'weights'))
print('ok noisy mode: noise-sized differences pass; a shifted random stream, a 1% loss shift, a NaN and a weight shift fail')
print('ALL OK')
