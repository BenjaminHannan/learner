import math, random
from contextlib import nullcontext
from learnlab.metrics import ContinualMatrix, bootstrap_ci, expected_calibration_error, steps_to_threshold, recall_at_k, mean
from learnlab.ablation import Component, judge_component

# Forgetting: Chaudhry et al. 2018 f_j = max_{l in 1..T-1} a_{l,j} - a_{T,j} (all earlier stages, incl. before task j was trained)
rows = [[0.2, 0.9, 0.1], [0.1, 0.6, 0.2], [0.1, 0.5, 0.9]]   # task1 scored 0.9 *before* training (forward transfer), then fell
m = ContinualMatrix(3)
for i, r in enumerate(rows):
    for j, v in enumerate(r): m.record(i, j, v)
chaudhry = mean([max(rows[l][j] for l in range(0, 2)) - rows[2][j] for j in range(2)])
print(f"forgetting: learnlab={m.forgetting():.3f}  chaudhry(max over all l<T)={chaudhry:.3f}")
print(f"BWT={m.backward_transfer():.3f} (Lopez-Paz: ((0.1-0.2)+(0.5-0.6))/2=-0.1)  FWT(untrained=0)={m.forward_transfer([0,0,0]):.3f} (expected (0.9+0.2)/2=0.55)")

# negative indices silently accepted
m = ContinualMatrix(3); m.record(-1, 0, 0.5); print("record(-1,0) wrote to stage", [i for i, r in enumerate(m.scores) if r[0] is not None])

# bootstrap percentile indices
s, a = 2000, 0.05
print("bootstrap order stats used (0-based):", math.floor(a/2*(s-1)), math.ceil((1-a/2)*(s-1)), "of", s)
print("bootstrap n=1:", bootstrap_ci([1.0]))
# coverage of percentile bootstrap for small n (binary p=0.9)
cover = 0; T = 300
for t in range(T):
    r = random.Random(t); x = [1.0 if r.random() < 0.9 else 0.0 for _ in range(15)]
    _, lo, hi = bootstrap_ci(x, samples=500, seed=t); cover += lo <= 0.9 <= hi
print(f"95% percentile-bootstrap coverage, n=15, p=0.9: {cover/T:.2%}")

# judge_component with a single item passes
v = judge_component(Component("c", nullcontext), (lambda it=iter([[1.0], [0.0]]): next(it)), {"b": [0.0]})
print("judge on ONE item: passed =", v.passed, v.lesion_drop)

# ECE edges
print("ECE conf=1.0 all correct:", expected_calibration_error([1.0]*4, [True]*4))
print("ECE conf 0.3 -> bin", min(int(0.3*10), 9), "; conf 0.7 -> bin", min(int(0.7*10), 9), "; conf 0.6 -> bin", min(int(0.6*10), 9))
try: expected_calibration_error([float('nan')], [True]); print("ECE accepts NaN confidence silently")
except ValueError as e: print("ECE rejects NaN:", e)

# steps_to_threshold: unsorted and single noisy crossing
print("unsorted curve:", steps_to_threshold([(30, 0.95), (10, 0.2), (20, 0.9)], 0.9), "(first sorted crossing is 20)")
print("single spike:", steps_to_threshold([(10, 0.2), (20, 0.91), (30, 0.4), (40, 0.5), (90, 0.92), (100, 0.93)], 0.9), "(sustained crossing at 90)")
