import random, math
from contextlib import contextmanager
from learnlab.ablation import Component, judge_component
from learnlab.metrics import paired_difference_ci

N = 300
state = {"on": True}
@contextmanager
def toggle():
    state["on"] = False
    try: yield
    finally: state["on"] = True

def show(tag, v, expect_pass):
    ok = "OK  " if v.passed == expect_pass else "BAD "
    print(f"{ok}{tag}: passed={v.passed} beats={v.beats_baselines} removes={v.lesion_removes_gain} full={v.full:.3f} lesioned={v.lesioned:.3f} drop={tuple(round(x,3) for x in v.lesion_drop)} margins={{{', '.join(f'{k}: {tuple(round(x,3) for x in m)}' for k,m in v.baseline_margins.items())}}}")

# 1. noise-level win: full and baseline agree except 4 of 300 items (4-0 discordant, McNemar exact p=0.125)
rng = random.Random(0)
base = [1.0 if rng.random() < 0.6 else 0.0 for _ in range(N)]
wrong = [i for i, b in enumerate(base) if b == 0.0][:4]
full = list(base)
for i in wrong: full[i] = 1.0
ev = lambda: full if state["on"] else base
show("4/300 discordant win (+1.3 pts) vs strong baseline", judge_component(Component("c", toggle), ev, {"strong": base}), False)
print("   exact McNemar/sign-test two-sided p for 4-0 =", 2 * 0.5 ** 4)

# 2. destructive lesion: component adds +5 pts over baseline, lesion wrecks the co-adapted system to 0%
rng = random.Random(1)
base = [1.0 if rng.random() < 0.85 else 0.0 for _ in range(N)]
full = [1.0 if (b or rng.random() < 0.35) else 0.0 for b in base]
ev = lambda: full if state["on"] else [0.0] * N
show("destructive lesion (full 0.90 vs base 0.85; lesion -> 0)", judge_component(Component("c", toggle), ev, {"core": base}), False)

# 3. lesion that does not restore state
broken = {"on": True}
@contextmanager
def leaky_lesion():
    broken["on"] = False; yield   # forgets to restore
evb = lambda: [1.0] * N if broken["on"] else [0.0] * N
v = judge_component(Component("c", leaky_lesion), evb, {"weak": [0.0] * 150 + [1.0] * 150})
show("lesion never restored", v, True)
print("   system after judging (should be restored):", "ON" if broken["on"] else "STILL LESIONED")

# 4. partial contributor: lesion removes only 40% of the gain in expectation; point-estimate check passes by noise
passes = 0; trials = 200
for t in range(trials):
    r = random.Random(100 + t)
    b = [1.0 if r.random() < 0.5 else 0.0 for _ in range(N)]
    f = [1.0 if (x or r.random() < 0.4) else 0.0 for x in b]                 # full gains +20 pts
    les = [fi if (fi == bi or r.random() < 0.6) else bi for fi, bi in zip(f, b)]  # lesion removes 40% of that gain
    state["on"] = True
    ev = (lambda f=f, les=les: f if state["on"] else les)
    passes += judge_component(Component("c", toggle), ev, {"b": b}, seed=t).passed
print(f"partial contributor (true fraction 0.40 < 0.50): passed {passes}/{trials}")

# 5. evaluate() not deterministic: each call scores a freshly reshuffled item order -> pairing broken, undetected
rng = random.Random(2)
items = [1.0 if rng.random() < 0.7 else 0.0 for _ in range(N)]
calls = {"n": 0}
def ev5():
    calls["n"] += 1; r = random.Random(calls["n"]); s = list(items); r.shuffle(s); return s
v = judge_component(Component("noop", lambda: toggle()), ev5, {"b": [0.0] * N})
print(f"no-op component, unpaired evaluate(): drop CI={tuple(round(x,3) for x in v.lesion_drop)} (width shows lost pairing; no error raised)")

# 6. baseline scored on different items of the same length -> accepted silently
v = judge_component(Component("c", toggle), lambda: [1.0]*N if state["on"] else [0.0]*N, {"other-items": [0.0]*N})
print("baseline scored on other items: accepted (no item ids to check) ->", v.passed)
