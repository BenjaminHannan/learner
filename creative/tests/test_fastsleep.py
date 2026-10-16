"""python3 -m creative.tests.test_fastsleep   (CPU, seconds) the nightly recall guard: chain-5 harm above the limit switches recall off."""
from creative import fastsleep as fs


def _fake(harm_by_model):
    calls = []

    def method(N, recs, replay, vocab, device, n_w, seed=0, **kw):
        calls.append(kw)
        return 'M', dict(kw=kw)

    def skills5(m, skills_data, device):
        return 0.99 - harm_by_model[m] / 100
    return method, skills5, calls


def _run(harm_m, limit=2.0):
    method, sk5, calls = _fake({'N': 0.0, 'M': harm_m})
    old_m, old_s = fs.METHODS['knn'], fs.skills5
    fs.METHODS['knn'], fs.skills5 = method, sk5
    try:
        return fs.nightly_recall('N', [1, 2, 3], [], None, 'cpu', None, limit=limit, log_fn=lambda *a: None) + (calls,)
    finally:
        fs.METHODS['knn'], fs.skills5 = old_m, old_s


def test_guard():
    m, rep, calls = _run(0.5)
    assert m == 'M' and rep['recall_on'] and abs(rep['chain5_harm_points'] - 0.5) < 1e-9
    m, rep, _ = _run(2.0)
    assert m == 'M' and rep['recall_on']                       # at the limit is allowed (harm <= 2)
    m, rep, _ = _run(3.9)
    assert m == 'N' and not rep['recall_on']                   # over the limit: tonight's model keeps no recall
    assert calls[0] == dict(c=50.0, theta=0.9, cal=0.99, old=512, ans=0)   # the frozen arm M (answer note off)


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'):
            v()
            print('ok', k)
