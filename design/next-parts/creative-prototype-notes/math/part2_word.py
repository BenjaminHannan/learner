"""Part 2: word problems with one correct call (two literals a, b; the right call is ADD or SUB in a
fixed order). Random policy as in Part 1. Exact enumeration over 4 loops for an ASSUMED operand
distribution (a, b in 10..89, right answer in 10..99, a > b for SUB); usable results 0..99."""
import json
from fractions import Fraction as Fr
import numpy as np

def exact_any_loop(a, b, op, pointer="distinct", umax=99):
    """P(the exact right call (op, literal order a->b) is made in at least one of 4 loops),
    P(right VALUE is produced by some OK call), P(first non-NONE call is exactly right)."""
    right_val = a + b if op == "ADD" else a - b
    def rec(refs, L):
        # returns (P_exact_call_ever, P_value_ever)
        if L == 0:
            return Fr(0), Fr(0)
        n = len(refs)
        pairs = [(i, j) for i in range(n) for j in range(n) if pointer == "independent" or i != j]
        w = Fr(1, 3) / len(pairs)
        pe0, pv0 = rec(refs, L - 1)
        pe, pv = Fr(1, 3) * pe0, Fr(1, 3) * pv0
        for act in ("ADD", "SUB"):
            for i, j in pairs:
                if i == j:
                    pe += w * pe0; pv += w * pv0; continue
                r = refs[i] + refs[j] if act == "ADD" else refs[i] - refs[j]
                exact = act == op and i == 0 and j == 1
                okr = 0 <= r <= umax
                if exact:
                    pe += w; pv += w; continue
                if not okr:
                    pe += w * pe0; pv += w * pv0; continue
                if r == right_val:   # e.g. ADD in the other order, or any OK call that lands on the value
                    a_, _ = rec(refs + [r], L - 1); pe += w * a_; pv += w; continue
                a_, b_ = rec(refs + [r], L - 1)
                pe += w * a_; pv += w * b_
        return pe, pv
    return rec([a, b], 4)

if __name__ == "__main__":
    rng = np.random.default_rng(3)
    res = {}
    for pointer, npairs in (("distinct", 2), ("independent", 4)):
        first_exact = Fr(1, 3) * Fr(1, npairs)
        res[pointer] = {
            "loop0_exact_call": float(first_exact),
            "loop0_right_value_ADD": float(Fr(1, 3) * Fr(2, npairs)),
            "loop0_right_value_SUB": float(first_exact),
            "first_nonNONE_call_exact": float(sum(Fr(1, 3) ** t * first_exact for t in range(4))),
        }
    # any loop, assumed operand distribution
    for pointer in ("distinct", "independent"):
        for op in ("ADD", "SUB"):
            pe, pv = [], []
            while len(pe) < 60:
                a, b = map(int, rng.integers(10, 90, size=2))
                if a == b: continue
                if op == "ADD" and not (10 <= a + b <= 99): continue
                if op == "SUB" and not (a > b and a - b >= 10): continue
                x, y = exact_any_loop(a, b, op, pointer)
                pe.append(float(x)); pv.append(float(y))
            res[pointer]["any_loop_exact_call_%s_mean" % op] = float(np.mean(pe))
            res[pointer]["any_loop_right_value_%s_mean" % op] = float(np.mean(pv))
    # pass@k floors
    def pk(p, k): return 1 - (1 - p) ** k
    floors = {}
    for name, p in (("call_exact_loop0", 1 / 6), ("final_shelf27_answer_on_shelf", 1 / 27),
                    ("final_shelf27_answer_off_shelf", 0.0), ("final_uniform_0_99", 1 / 100),
                    ("call_and_final_shelf27_on_shelf", 1 / 6 / 27), ("call_and_final_uniform_0_99", 1 / 6 / 100)):
        floors[name] = {"p": p, "pass@1": p, "pass@8": pk(p, 8), "pass@32": pk(p, 32)}
    # a fresh set where half the right answers are off the shelf (like F1: 64 of 128)
    floors["final_shelf27_half_off_shelf_set_average"] = {"p": 0.5 / 27, "pass@1": 0.5 / 27,
                                                          "pass@8": 0.5 * pk(1 / 27, 8), "pass@32": 0.5 * pk(1 / 27, 32)}
    res["pass_floors"] = floors
    json.dump(res, open("part2_word.json", "w"), indent=1)
    print(json.dumps(res, indent=1))
