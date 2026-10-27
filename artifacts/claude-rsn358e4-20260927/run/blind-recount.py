"""Blind recount of rsn-358e4 from raw result.json files and the marks
(PASSMARKS.md, ADDENDUM-1.md, ADDENDUM-2.md, ADDENDUM-3-wording.md) only."""
import json, os

ROOT = "/home/user/learner/artifacts/claude-rsn358e4-20260927/runs"
SEEDS = [3, 4, 5, 6, 7, 8]
ARMS = ["dense-replayall", "eq-replayall"]
SEALED_W = {"dense-replayall": 1646750, "eq-replayall": 1654446}
SEALED_REPLAY_B = {"sums": {"grids": 250}, "mazes": {}}
SEALED_REPLAY_C = {"sums": {"grids": 250}, "mazes": {"grids": 75, "sums": 75}}

R, raw = {}, {}
for arm in ARMS:
    for s in SEEDS:
        p = os.path.join(ROOT, f"{arm}-s{s}", "result.json")
        d = json.load(open(p)); raw[arm, s] = d
        ph = d["phases"]
        assert d["arm"] == arm and d["seed"] == s, (p, d["arm"], d["seed"])
        g5A = ph["after_grids"]["grids5"]["right"]
        s4B = ph["after_sums"]["sums4"]["right"]
        g5C = ph["after_mazes"]["grids5"]["right"]
        s4C = ph["after_mazes"]["sums4"]["right"]
        m7C = ph["after_mazes"]["maze7"]["right"]
        R[arm, s] = dict(g5A=g5A, s4B=s4B, g5C=g5C, s4C=s4C, m7C=m7C,
                         T=g5C + s4C + m7C, K=g5C + s4C, L=m7C)

def mean(xs): return sum(xs) / len(xs)

print("== Integrity checks")
torches = set()
for (arm, s), d in sorted(raw.items()):
    ph = d["phases"]
    rb, rc = ph["after_sums"].get("replayed"), ph["after_mazes"].get("replayed")
    okw = d["weights"] == SEALED_W[arm]
    okb, okc = rb == SEALED_REPLAY_B, rc == SEALED_REPLAY_C
    torches.add(d["torch"])
    print(f"{arm:16s} s{s}: weights={d['weights']} ({'ok' if okw else 'MISMATCH'}) torch={d['torch']} device={d['device']} "
          f"size={d['size']} replay_B={rb} ({'ok' if okb else 'MISMATCH'}) replay_C={rc} ({'ok' if okc else 'MISMATCH'}) "
          f"minutes={d.get('minutes')}")
print("torch versions seen:", torches, "(one version)" if len(torches) == 1 else "(MIXED)")

print("\n== Per-seed numbers (right of 200; T,K of 600/400)")
hdr = f"{'arm':16s} {'seed':>4} {'g5@A':>5} {'s4@B':>5} {'g5@C':>5} {'s4@C':>5} {'m7@C':>5} {'T':>4} {'K':>4} {'L':>4}"
print(hdr)
for arm in ARMS:
    for s in SEEDS:
        r = R[arm, s]
        print(f"{arm:16s} {s:>4} {r['g5A']:>5} {r['s4B']:>5} {r['g5C']:>5} {r['s4C']:>5} {r['m7C']:>5} {r['T']:>4} {r['K']:>4} {r['L']:>4}")
print("\n== Means")
M = {}
for arm in ARMS:
    M[arm] = {k: mean([R[arm, s][k] for s in SEEDS]) for k in ["g5A", "s4B", "g5C", "s4C", "m7C", "T", "K", "L"]}
    print(f"{arm:16s} " + " ".join(f"{k}={v:.2f}" for k, v in M[arm].items()))
for k in ["T", "K", "L"]:
    print(f"gap {k} (eq - dense) = {M['eq-replayall'][k] - M['dense-replayall'][k]:.2f}")

print("\n== Per-seed comparisons (eq vs dense)")
gt = lt = 0
for s in SEEDS:
    te, td = R["eq-replayall", s]["T"], R["dense-replayall", s]["T"]
    le, ld = R["eq-replayall", s]["L"], R["dense-replayall", s]["L"]
    ke, kd = R["eq-replayall", s]["K"], R["dense-replayall", s]["K"]
    rel = ">" if te > td else ("<" if te < td else "=")
    gt += te > td; lt += te < td
    print(f"s{s}: T_eq={te} {rel} T_dense={td} (diff {te - td:+d}); K diff {ke - kd:+d}; L diff {le - ld:+d}")
print(f"T_eq > T_dense on {gt} of 6; T_eq < T_dense on {lt} of 6")

mTe, mTd = M["eq-replayall"]["T"], M["dense-replayall"]["T"]
mLe, mLd = M["eq-replayall"]["L"], M["dense-replayall"]["L"]

print("\n== V (ADDENDUM-1, unchanged from PASSMARKS)")
v1 = all(R[a, s]["g5A"] >= 120 for a in ARMS for s in SEEDS)
v2 = all(R["dense-replayall", s]["s4B"] >= 120 for s in SEEDS)
for a in ARMS:
    print(f"  grids5 after A >= 120, {a}: " + ", ".join(f"s{s}={R[a, s]['g5A']}{'' if R[a, s]['g5A'] >= 120 else '(FAIL)'}" for s in SEEDS))
print("  sums4 after B >= 120, dense: " + ", ".join(f"s{s}={R['dense-replayall', s]['s4B']}{'' if R['dense-replayall', s]['s4B'] >= 120 else '(FAIL)'}" for s in SEEDS))
V = v1 and v2
print(f"  V1 (grids5@A>=120 both arms, every seed) = {v1}")
print(f"  V2 (sums4@B>=120 dense, every seed)      = {v2}")
print(f"  V = {V}")

print("\n== PASS (ADDENDUM-1 + ADDENDUM-2)")
p1 = mTe >= mTd + 40
p2 = gt >= 5
p3 = mLe >= 100
p4 = mLe >= mLd - 20
print(f"  P1 mean T_eq {mTe:.2f} >= mean T_dense + 40 = {mTd + 40:.2f}: {p1}")
print(f"  P2 T_eq > T_dense on >= 5 of 6 (got {gt}): {p2}")
print(f"  P3 mean L_eq {mLe:.2f} >= 100: {p3}")
print(f"  P4 mean L_eq {mLe:.2f} >= mean L_dense - 20 = {mLd - 20:.2f}: {p4}")
PASS = p1 and p2 and p3 and p4
print(f"  PASS = {PASS}")

print("\n== Proved wrong (ADDENDUM-1, unchanged in ADDENDUM-2)")
w1 = mTe <= mTd - 40
w2 = lt >= 5
print(f"  W1 mean T_eq {mTe:.2f} <= mean T_dense - 40 = {mTd - 40:.2f}: {w1}")
print(f"  W2 T_eq < T_dense on >= 5 of 6 (got {lt}): {w2}")
WRONG = w1 and w2
print(f"  PROVED WRONG = {WRONG}")

if not V: verdict = "INCONCLUSIVE"
elif PASS: verdict = "PASS"
elif WRONG: verdict = "PROVED WRONG"
else: verdict = "FAIL (not proved wrong)"
print(f"\n== VERDICT: {verdict}")
if V and PASS and WRONG: print("  WARNING: PASS and PROVED WRONG both fire")
if not V:
    print(f"  (had V been met: PASS={PASS}, PROVED WRONG={WRONG})")

print("\n== ADDENDUM-3: tested the routing (eq only)")
N, tested = 0, []
for s in SEEDS:
    ph = raw["eq-replayall", s]["phases"]
    sb = ph["after_sums"]["expert_share"]["sums4"]
    mc = ph["after_mazes"]["expert_share"]["maze7"]
    newB = [sum(blk[4:8]) for blk in sb]
    newC = [sum(blk[8:12]) for blk in mc]
    okB = any(x >= 0.05 for x in newB)
    okC = any(x >= 0.05 for x in newC)
    t = okB and okC
    N += t
    if t: tested.append(s)
    print(f"  s{s}: sums4@B new-group(4-7) share per block = {[round(x, 3) for x in newB]} -> {okB}; "
          f"maze7@C new-group(8-11) share per block = {[round(x, 3) for x in newC]} -> {okC}; tested={t}")
    print(f"       n experts per block: B {[len(b) for b in sb]}, C {[len(b) for b in mc]}; block sums B {[round(sum(b), 3) for b in sb]}, C {[round(sum(b), 3) for b in mc]}")
print(f"  N tested the routing = {N} of 6 (seeds {tested})")
if verdict == "PROVED WRONG":
    print("  Wording branch:", "N >= 4 (small trainable share, suggested)" if N >= 4 else "N <= 3 (says little about separate experts)")

print("\n== Robustness (report only, not a mark)")
# (a) routing count if 'the new group got >= 5%' were read per single expert instead of group sum
N2, t2 = 0, []
for s in SEEDS:
    ph = raw["eq-replayall", s]["phases"]
    okB = any(max(b[4:8]) >= 0.05 for b in ph["after_sums"]["expert_share"]["sums4"])
    okC = any(max(b[8:12]) >= 0.05 for b in ph["after_mazes"]["expert_share"]["maze7"])
    if okB and okC: N2 += 1; t2.append(s)
print(f"  (a) per-single-expert reading of the 5% rule: N = {N2} (seeds {t2})")
# (b) verdict if the score field were r16 or any instead of right
for fld in ["r16", "any"]:
    T = {(a, s): sum(raw[a, s]["phases"]["after_mazes"][k][fld] for k in ["grids5", "sums4", "maze7"]) for a in ARMS for s in SEEDS}
    me, md = mean([T["eq-replayall", s] for s in SEEDS]), mean([T["dense-replayall", s] for s in SEEDS])
    nl = sum(T["eq-replayall", s] < T["dense-replayall", s] for s in SEEDS)
    print(f"  (b) field={fld}: mean T_eq={me:.2f}, mean T_dense={md:.2f}, T_eq<T_dense on {nl}/6 -> proved-wrong conditions {me <= md - 40 and nl >= 5}")
# (c) original PASSMARKS marks (seeds 3-6, bar 30, >=3 of 4), superseded by addendum 1
S4 = [3, 4, 5, 6]
me, md = mean([R["eq-replayall", s]["T"] for s in S4]), mean([R["dense-replayall", s]["T"] for s in S4])
print(f"  (c) superseded PASSMARKS rule, seeds 3-6: mean T_eq={me:.2f}, mean T_dense={md:.2f}; proved wrong (<= -30) = {me <= md - 30}")
# (d) ties
print(f"  (d) seeds with T_eq == T_dense: {[s for s in SEEDS if R['eq-replayall', s]['T'] == R['dense-replayall', s]['T']]}")
