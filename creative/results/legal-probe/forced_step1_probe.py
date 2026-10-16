import sys, collections, torch, json
sys.path.insert(0, '/home/user/learner')
from creative import puzzles, sampler, sleep, legal
from creative.programs import R0
torch.set_num_threads(2)
m, vocab, _ = sleep.load_parent(sys.argv[1]); m.eval()
dev = puzzles.load_split('/home/user/learner/creative/data/c1', 'dev')
g = sampler.greedy_tries(m, dev, vocab, 'cpu')
tab = collections.Counter(); s1 = collections.Counter()
for r, x in zip(dev, g):
    t = x.t
    p1 = tuple(sorted((t.a[0], t.b[0])))
    s1[p1] += 1
    o2 = tuple(sorted((t.a[1], t.b[1])))
    tab[(p1, o2)] += 1
print('step-1 operand pairs', s1.most_common())
print('step-1 pair -> step-2 operand pair (greedy, 128 DEV)')
for k, v in tab.most_common(20): print(k, v)
# step-2 pointer distribution conditioned on the GOLD-style legal first step: force each legal pair, read step-2 b-head mass on spent vs fresh
from creative.programs import ADD
res = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0])
for pair in ((0, 1), (0, 2), (1, 2)):
    fresh = ({0, 1, 2} - set(pair)).pop()
    first = tuple(torch.full((len(dev),), v).long() for v in (ADD, pair[0], pair[1]))
    b = sampler.make_batch(dev, vocab, 'cpu')
    # run with step 1 forced, then get step-2 logits by forcing step 1 and stopping: reuse masked runner at level 0 is sample_run; emulate by greedy run
    out = sampler.sample_run(m, b, greedy=True, first=first)
    a2, b2 = out['a'][:, 1].tolist(), out['b'][:, 1].tolist()
    for x, y in zip(a2, b2):
        ops = {x, y}
        res[pair][0] += R0 in ops; res[pair][1] += fresh in ops; res[pair][2] += bool(ops & set(pair)); res[pair][3] += 1
for pair, (r0, fr, sp, n) in res.items():
    print(f'forced step1 ADD{pair}: step-2 greedy reads R0 {r0/n:.2f}, the fresh number {fr/n:.2f}, a spent number {sp/n:.2f}')
