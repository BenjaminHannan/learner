"""posctrl.py -- run custom_io.train in-process with (a) emulated GPU nondeterminism and (b) an optional restore FAULT applied right after --resume loads its checkpoint.

    POSCTRL_TREE=<dir holding custom_io/>  NOISE_EPS=1e-3  FAULT=opt_reset  OMP_NUM_THREADS=1  python3 posctrl.py <train.py arguments...>

NOISE_EPS (float, default 0): after EVERY micro-batch backward, every param.grad gets  eps * rms(param.grad) * N(0,1)  added (float32), the normals coming from a numpy
    Generator seeded from os.urandom (never from the python / numpy / torch GLOBAL streams, which are checkpointed streams of the run). Each process gets its own noise.
    (rms is taken over the grad accumulated so far in this update, i.e. including the earlier micro-batches.) 0 = nothing is patched.
FAULT (default none), applied ONLY in a process that resumes, in the one place where train.py has just loaded model + optimizer (restore_model_streams is called right after
    model.load_state_dict, opt.load_state_dict and restore_global_streams):
    none | opt_reset | opt_moments_zero | data_shift | rng_noreset | lr_step_off | weights_eps | rng_global_noreset | rng_model_noreset
      opt_reset         opt.state = defaultdict(dict)  (AdamW moments AND step counts gone)
      opt_moments_zero  keep AdamW 'step', zero exp_avg and exp_avg_sq
      data_shift        data-order position +1 batch (batches_from(skip + 1))
      rng_noreset       skip restore_global_streams AND the model's own random.Random restore (streams stay as they are after seeding + model build)
      rng_global_noreset / rng_model_noreset   only the global streams / only the model's own streams are left unrestored
      lr_step_off       lr = lr_at(step + 1, ...) for every update of the resumed process
      weights_eps       every weight w -> w * (1 + WEIGHTS_EPS * N(0,1)) (env WEIGHTS_EPS, default 1e-3), fixed seed (partial-weights-corruption stand-in)
"""
import collections, os, sys
import numpy as np
import torch

sys.path.insert(0, os.environ['POSCTRL_TREE'])
import custom_io.train as T                                                                 # noqa: E402

EPS = float(os.environ.get('NOISE_EPS', '0') or 0)
FAULT = os.environ.get('FAULT', 'none') or 'none'
FAULTS = ('none', 'opt_reset', 'opt_moments_zero', 'data_shift', 'rng_noreset', 'lr_step_off', 'weights_eps', 'rng_global_noreset', 'rng_model_noreset')
assert FAULT in FAULTS, FAULT
ST = {}

if EPS > 0:
    NOISE = np.random.default_rng(int.from_bytes(os.urandom(16), 'little'))                # own stream: no global RNG is touched
    _build, _bw = T.build, torch.Tensor.backward

    def build(*a, **k):
        ST['model'] = m = _build(*a, **k)
        return m
    T.build = build

    def backward(self, *a, **k):
        r = _bw(self, *a, **k)
        if 'model' in ST:
            with torch.no_grad():
                for p in ST['model'].parameters():
                    g = p.grad
                    if g is not None and g.numel():
                        rms = float(g.pow(2).mean().sqrt())
                        g.add_(torch.from_numpy(NOISE.standard_normal(tuple(g.shape)).astype(np.float32)), alpha=EPS * rms)
        return r
    torch.Tensor.backward = backward

if FAULT != 'none':
    _AdamW = torch.optim.AdamW

    def adamw(*a, **k):
        ST['opt'] = o = _AdamW(*a, **k)
        return o
    torch.optim.AdamW = adamw

    _rgs, _rms, _bf, _lr = T.restore_global_streams, T.restore_model_streams, T.batches_from, T.lr_at

    def rgs(g, device):
        if FAULT in ('rng_noreset', 'rng_global_noreset'):
            return None
        return _rgs(g, device)

    def rms(model, rngs, stats):
        if FAULT not in ('rng_noreset', 'rng_model_noreset'):
            _rms(model, rngs, stats)
        opt = ST['opt']
        if FAULT == 'opt_reset':
            opt.state = collections.defaultdict(dict)
        elif FAULT == 'opt_moments_zero':
            for st in opt.state.values():
                st['exp_avg'].zero_()
                st['exp_avg_sq'].zero_()
        elif FAULT == 'weights_eps':
            g = np.random.default_rng(4242)
            with torch.no_grad():
                for p in model.parameters():
                    p.mul_(1 + float(os.environ.get('WEIGHTS_EPS', '1e-3')) * torch.from_numpy(g.standard_normal(tuple(p.shape)).astype(np.float32)))
        ST['loaded'] = True
        print('{"event": "posctrl_fault", "fault": "%s", "noise_eps": %g}' % (FAULT, EPS), flush=True)

    def bf(ds, batch_size, order='shuffled', seed=0, skip=0):
        return _bf(ds, batch_size, order, seed, skip + (1 if FAULT == 'data_shift' else 0))

    def lr_at(step, *a, **k):
        return _lr(step + (1 if FAULT == 'lr_step_off' and ST.get('loaded') else 0), *a, **k)
    T.restore_global_streams, T.restore_model_streams, T.batches_from, T.lr_at = rgs, rms, bf, lr_at

if __name__ == '__main__':
    T.main(sys.argv[1:])
